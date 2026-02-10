# Databricks AgentBricks — Payment Analysis (Full Conversion)

This guide converts **all** payment analysis Python agents (`agent_framework.py`) to **Databricks AgentBricks**: same five specialists and orchestrator, implemented with **MLflow + LangGraph/LangChain**, tools as **Unity Catalog functions**, deployable to **Model Serving**. The **Multi-Agent Supervisor** (workspace Agents UI) replaces the Python `OrchestratorAgent`.

## Python agents → AgentBricks mapping

| Python agent (agent_framework.py) | AgentBricks specialist | UC tools | LangGraph builder |
|----------------------------------|------------------------|----------|--------------------|
| **SmartRoutingAgent** | Smart Routing | get_route_performance, get_cascade_recommendations | create_smart_routing_agent |
| **SmartRetryAgent** | Smart Retry | get_retry_success_rates, get_recovery_opportunities | create_smart_retry_agent |
| **DeclineAnalystAgent** | Decline Analyst | get_decline_trends, get_decline_by_segment | create_decline_analyst_agent |
| **RiskAssessorAgent** | Risk Assessor | get_high_risk_transactions, get_risk_distribution | create_risk_assessor_agent |
| **PerformanceRecommenderAgent** | Performance Recommender | get_kpi_summary, get_optimization_opportunities, get_trend_analysis | create_performance_recommender_agent |
| **OrchestratorAgent** | Multi-Agent Supervisor | (routes to above) | Workspace → Agents → Multi-Agent Supervisor |

System prompts and tool behavior match the Python agents 1:1.

---

## Key differences: Custom Python agents vs AgentBricks

| Aspect | Custom Python agents (current) | AgentBricks agents |
|--------|----------------------------------|---------------------|
| **Deployment** | Embedded in app / job notebook | Separate Model Serving endpoints |
| **Scaling** | Limited by app or job compute | Independent auto-scaling per endpoint |
| **Updates** | Requires app or job redeployment | Update endpoint / model version independently |
| **Monitoring** | Manual (logs, job runs) | Built-in MLflow tracing and Model Serving metrics |
| **Cost** | App compute only (or job cluster) | App compute + endpoint compute (pay per endpoint) |
| **Latency** | Lower (in-process in same job/app) | Higher (network call to Model Serving) |

### Recommended architecture: hybrid approach

- **Deploy specialists to Model Serving** (AgentBricks or Agent Framework).
- **Keep orchestration and UI in the Databricks App**: routing, business rules, and user experience.
- **App calls agent endpoints** for AI reasoning and data analysis; agents do not run inside the app process.

```
┌─────────────────────────────────────────────────────────┐
│  Databricks App (FastAPI + React)                      │
│  - UI/UX (Setup & Run, Rules, Decisioning, Agents)      │
│  - Orchestration logic (route query → supervisor/agent) │
│  - Business rules, dashboards, jobs                     │
└──────────────────────────┬─────────────────────────────┘
                           │ API calls
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Multi-Agent     │ │ Decline Analyst │ │ Smart Routing    │
│ Supervisor      │ │ Agent Endpoint  │ │ Agent Endpoint   │
│ (Model Serving) │ │ (Model Serving) │ │ (Model Serving)  │
└────────┬────────┘ └─────────────────┘ └─────────────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
   Smart Retry   Risk Assessor   Performance   (other specialists)
   Endpoint      Endpoint        Recommender
```

**Benefits of the hybrid approach**

- Agents scale independently of the app.
- Update or A/B test agents without redeploying the app.
- Built-in monitoring and tracing (MLflow, Model Serving).
- Reuse the same agent endpoints across multiple apps or jobs.
- Clear separation: app = UI + orchestration + rules; agents = AI reasoning and data analysis.

---

## Overview

| Step | What | Where |
|------|------|--------|
| 1 | UC functions for tools | `src/payment_analysis/agents/uc_tools/` |
| 2 | LangGraph agents (all 5) | `src/payment_analysis/agents/langgraph_agents.py` |
| 3 | Log & register all to UC | Notebook using get_all_agent_builders() |
| 4 | Deploy all to Model Serving | Per-agent or loop |
| 5 | Multi-Agent Supervisor | Workspace → Agents → Multi-Agent Supervisor |

---

## Step 1: Unity Catalog Functions (Tools)

Create the `agent_tools` schema and all tool functions in your catalog. Data is read from `{catalog}.{schema}.payments_enriched_silver` and gold views (e.g. `v_top_decline_reasons`).

### Option A: Run from a job

1. Add a job task that runs the Python runner with catalog/schema parameters:

```yaml
# Example task for resources/ml_jobs.yml or a dedicated agents job
- task_key: create_uc_agent_tools
  python_wheel_task:
    package_name: payment_analysis
    entry_point: run_create_uc_agent_tools
    parameters: ["--catalog", "${var.catalog}", "--schema", "${var.schema}"]
  # Or use a notebook that calls:
  # from payment_analysis.agents.uc_tools.run_create_uc_agent_tools import run
  # run(dbutils.widgets.get("catalog"), dbutils.widgets.get("schema"))
```

2. Ensure the **Create gold views** job has run first (so `payments_enriched_silver` and `v_*` views exist).

### Option B: Run from a notebook

```python
# In a Databricks notebook (Python)
dbutils.widgets.text("catalog", "ahs_demos_catalog")
dbutils.widgets.text("schema", "payment_analysis")

from payment_analysis.agents.uc_tools.run_create_uc_agent_tools import run
run(dbutils.widgets.get("catalog"), dbutils.widgets.get("schema"))
```

### SQL source

- **File:** `src/payment_analysis/agents/uc_tools/uc_agent_tools.sql`
- Placeholders `__CATALOG__` and `__SCHEMA__` are replaced with your data catalog and schema.
- Creates: `{catalog}.agent_tools.get_decline_trends`, `get_decline_by_segment`, `get_route_performance`, `get_cascade_recommendations`, `get_retry_success_rates`, `get_recovery_opportunities`, `get_high_risk_transactions`, `get_risk_distribution`, `get_kpi_summary`, `get_optimization_opportunities`, `get_trend_analysis`.

---

## Step 2: LangGraph Agents (all five)

All five specialists are implemented in `src/payment_analysis/agents/langgraph_agents.py` with the same system prompts as the Python agents:

- **create_decline_analyst_agent(catalog, ...)** — Decline Analyst
- **create_smart_routing_agent(catalog, ...)** — Smart Routing & Cascading
- **create_smart_retry_agent(catalog, ...)** — Smart Retry
- **create_risk_assessor_agent(catalog, ...)** — Risk Assessor
- **create_performance_recommender_agent(catalog, ...)** — Performance Recommender

Helper **get_all_agent_builders()** returns `[(create_fn, model_suffix), ...]` for one-loop register/deploy. Each agent uses `ChatDatabricks`, `UCFunctionToolkit`, and LangGraph’s `create_react_agent`.

### Dependencies (notebook or job cluster)

```python
%pip install databricks-langchain unitycatalog-langchain[databricks] langgraph langchain-core
dbutils.library.restartPython()
```

### Example: Build and invoke Decline Analyst

```python
from payment_analysis.agents.langgraph_agents import create_decline_analyst_agent
from langchain_core.messages import HumanMessage

catalog = "ahs_demos_catalog"  # or from widget/var
agent = create_decline_analyst_agent(catalog, llm_endpoint="databricks-meta-llama-3-1-70b-instruct")
result = agent.invoke({"messages": [HumanMessage(content="What are the top decline reasons?")]})
```

---

## Step 3: Log and Register All Agents to Unity Catalog

Log all five agents with MLflow LangChain flavor and register to UC in one loop using **get_all_agent_builders()**.

```python
import mlflow
from payment_analysis.agents.langgraph_agents import get_all_agent_builders

mlflow.set_registry_uri("databricks-uc")
catalog = "ahs_demos_catalog"  # or var
model_catalog = "payment_analysis_uc"  # UC catalog for registered models
llm_endpoint = "databricks-meta-llama-3-1-70b-instruct"

for create_fn, name in get_all_agent_builders():
    with mlflow.start_run():
        agent = create_fn(catalog, llm_endpoint=llm_endpoint)
        logged = mlflow.langchain.log_model(
            lc_model=agent,
            artifact_path="agent",
            input_example={"messages": [{"role": "user", "content": "Summarize key metrics."}]},
        )
        mlflow.register_model(
            model_uri=logged.model_uri,
            name=f"{model_catalog}.agents.{name}",
        )
```

Registered names: `payment_analysis_uc.agents.decline_analyst`, `.agents.smart_routing`, `.agents.smart_retry`, `.agents.risk_assessor`, `.agents.performance_recommender`. Adjust `model_catalog` to your UC model catalog.

---

## Step 4: Deploy to Model Serving

Deploy each registered agent to an endpoint (e.g. for use as subagents of the Multi-Agent Supervisor).

### Option A: Databricks Agents API (if available)

```python
from databricks import agents

model_name = "payment_analysis_uc.agents.decline_analyst"
model_version = "1"  # or from mlflow.register_model result

deployment = agents.deploy(
    model_name=model_name,
    model_version=model_version,
)
print(deployment.endpoint_name)
```

### Option B: Model Serving UI

1. Go to **Workflow → Model Serving**.
2. Create **Endpoint** → **Serve model from Unity Catalog**.
3. Select the registered model (e.g. `payment_analysis_uc.agents.decline_analyst`) and version.
4. Deploy; note the **Endpoint name** for the Multi-Agent Supervisor.

Repeat for all five: decline_analyst, smart_routing, smart_retry, risk_assessor, performance_recommender.

---

## Step 5: Multi-Agent Supervisor (Orchestrator)

Use **AgentBricks → Multi-Agent Supervisor** in the workspace to route user questions to the right specialist (replaces Python `OrchestratorAgent`).

1. In the workspace sidebar, open **Agents**.
2. Create or open **Multi-Agent Supervisor** → **Build**.
3. Add **all five** deployed agents as **subagents** (one per specialist):

| Specialist | Type | Description for routing |
|------------|------|--------------------------|
| Decline Analyst | Agent Endpoint | Decline pattern analysis, recovery potential, top decline reasons. |
| Smart Routing | Agent Endpoint | Payment route performance, cascade recommendations by segment. |
| Smart Retry | Agent Endpoint | Retry success rates, recovery opportunities, retry strategy. |
| Risk Assessor | Agent Endpoint | Fraud and risk assessment, high-risk transactions. |
| Performance Recommender | Agent Endpoint | KPIs, optimization opportunities, trend analysis. |

4. Save and deploy the supervisor. Use its endpoint in your app or jobs for “AI agents” queries.

### Routing keywords (match Python OrchestratorAgent)

| User keywords | Route to |
|---------------|----------|
| "routing", "cascade", "processor", "route" | Smart Routing |
| "retry", "recovery", "reprocess", "failed" | Smart Retry |
| "decline", "reject", "fail", "denied" | Decline Analyst |
| "fraud", "risk", "suspicious", "aml" | Risk Assessor |
| "performance", "optimize", "improve", "recommend", "kpi" | Performance Recommender |
| (default if none match) | Performance Recommender |

---

## Job and App Wiring

- **Existing Job 6** (`run_agent_framework`): Runs the legacy notebook `agent_framework.py` (orchestrator + five specialists in one run). For AgentBricks, add a task that creates UC tools and/or run the MLflow register loop in a notebook; then deploy the five agents to Model Serving and configure the Multi-Agent Supervisor in the workspace.
- **App “AI agents” UX**: To use AgentBricks, point the backend to the **Multi-Agent Supervisor** endpoint (or individual agent endpoints). Use the same message format expected by the deployed LangChain/LangGraph model.

---

## References

- [Integrate LangChain with Databricks Unity Catalog tools](https://docs.databricks.com/en/generative-ai/agent-framework/langchain-uc-integration)
- [Create AI agent tools using Unity Catalog functions](https://docs.databricks.com/en/generative-ai/agent-framework/create-custom-tool)
- [Log and load LangChain models with MLflow](https://mlflow.org/docs/latest/python_api/mlflow.langchain.html)
- **AgentBricks**: **Multi-Agent Supervisor** in the workspace **Agents** UI
