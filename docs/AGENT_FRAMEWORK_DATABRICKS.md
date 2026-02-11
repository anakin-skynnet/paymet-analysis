# Databricks AgentBricks — Payment Analysis (Full Conversion)

This guide converts **all** payment analysis Python agents (`agent_framework.py`) to **Mosaic AI Agent Framework (AgentBricks)**: same five specialists and orchestrator, implemented with **MLflow + LangGraph**, tools as **Unity Catalog functions**, deployable to **Model Serving**. The **Multi-Agent Supervisor** (workspace Agents UI) replaces the Python `OrchestratorAgent`.

---

## Current agent architecture (before conversion)

**Type:** Custom Python class-based agents — **not** AgentBricks yet.

| Component | Description |
|-----------|-------------|
| **BaseAgent** | Custom class with LLM calls (WorkspaceClient), SQL execution, and tool management |
| **SmartRoutingAgent** | Payment routing optimization |
| **SmartRetryAgent** | Retry decision logic |
| **DeclineAnalystAgent** | Decline pattern analysis |
| **RiskAssessorAgent** | Fraud/risk assessment |
| **PerformanceRecommenderAgent** | Overall optimization |
| **OrchestratorAgent** | Multi-agent coordinator |

**Current approach:** Direct LLM endpoint calls via WorkspaceClient; custom tool execution; manual conversation history; in-memory state. No MLflow tracing, no UC-registered tools, no Model Serving endpoints.

---

## AgentBricks type classification (Mosaic AI Agent Framework)

Each Python agent maps to a specific AgentBricks pattern:

| Agent | AgentBricks type | Framework | Key feature |
|-------|------------------|-----------|-------------|
| **Smart Routing** | Tool-Calling Agent | LangGraph ReAct | UC function tools (get_route_performance, get_cascade_recommendations) |
| **Decline Analyst** | Tool-Calling Agent | LangGraph ReAct | UC function tools (get_decline_trends, get_decline_by_segment) |
| **Risk Assessor** | Tool-Calling Agent | LangGraph ReAct | UC function tools (get_high_risk_transactions, get_risk_distribution) |
| **Performance Recommender** | Tool-Calling Agent | LangGraph ReAct | UC function tools (get_kpi_summary, get_optimization_opportunities, get_trend_analysis) |
| **Smart Retry** | Tool-Calling Agent | LangGraph ReAct | UC function tools (get_retry_success_rates, get_recovery_opportunities) |
| **Orchestrator** | Multi-Agent System (Compound) | LangGraph StateGraph / Workspace Multi-Agent Supervisor | Routes to specialists; synthesizes results |

**Pattern 1 — Tool-Calling Agents (all 5 specialists):** User query → LLM decides which tools to call → Execute UC SQL tools → LLM synthesizes answer. Implemented with **LangGraph `create_react_agent`** + LLM with function calling + tools as Unity Catalog functions.

**Pattern 2 — Multi-Agent System (Orchestrator):** User query → Orchestrator routes to specialist(s) → Specialists respond → Orchestrator synthesizes. Implemented via **Workspace Multi-Agent Supervisor** (or LangGraph StateGraph with conditional routing).

All are **conversational agents** (chat interface) with tool-calling and **MLflow tracing** when deployed via AgentBricks/Model Serving.

---

## Conversion steps (high level)

| Step | What | Outcome |
|------|------|--------|
| **1** | Refactor each specialist as MLflow LangChain/LangGraph model (e.g. `mlflow.pyfunc` / `mlflow.langchain`) | Loggable, versioned agent |
| **2** | Register tools as Unity Catalog functions | `get_decline_trends`, `get_route_performance`, etc. in `catalog.schema` |
| **3** | Log each agent to MLflow; register to Unity Catalog | `catalog.agents.decline_analyst`, etc. |
| **4** | Deploy each agent as Model Serving endpoint | Scalable, production-ready specialist endpoints |
| **5** | Convert orchestrator to Multi-Agent System | Workspace Multi-Agent Supervisor (or LangGraph StateGraph) calling specialist endpoints |

**Key benefits after conversion:** MLflow tracing; Unity Catalog integration (tools + models); Model Serving scaling and monitoring; evaluation framework; governance and lineage; no in-app agent process for specialists.

**Migration priority:** Start with **Decline Analyst** (simplest); test end-to-end (create UC tools → log → register → deploy → query); then migrate the other four specialists; finally update the orchestrator to call serving endpoints and add evaluation (e.g. Mosaic AI Agent Evaluation).

---

## Python agents → AgentBricks mapping (implementation)

| Python agent (agent_framework.py) | AgentBricks specialist | UC tools | LangGraph builder |
|----------------------------------|------------------------|----------|--------------------|
| **SmartRoutingAgent** | Smart Routing | get_route_performance, get_cascade_recommendations | create_smart_routing_agent |
| **SmartRetryAgent** | Smart Retry | get_retry_success_rates, get_recovery_opportunities | create_smart_retry_agent |
| **DeclineAnalystAgent** | Decline Analyst | get_decline_trends, get_decline_by_segment | create_decline_analyst_agent |
| **RiskAssessorAgent** | Risk Assessor | get_high_risk_transactions, get_risk_distribution | create_risk_assessor_agent |
| **PerformanceRecommenderAgent** | Performance Recommender | get_kpi_summary, get_optimization_opportunities, get_trend_analysis | create_performance_recommender_agent |
| **OrchestratorAgent** | Multi-Agent Supervisor | (routes to above) | Workspace → Agents → Multi-Agent Supervisor |

System prompts and tool behavior match the Python agents 1:1.

### Specialist behavior (Tool-Calling pattern)

| Specialist | Tools | Behavior |
|------------|-------|----------|
| Smart Routing | get_route_performance, get_cascade_recommendations | Analyzes data → Recommends optimal payment route |
| Decline Analyst | get_decline_trends, get_decline_by_segment | Investigates declines → Identifies root causes |
| Risk Assessor | get_high_risk_transactions, get_risk_distribution | Assesses risk → Flags suspicious transactions |
| Performance Recommender | get_kpi_summary, get_optimization_opportunities, get_trend_analysis | Reviews metrics → Provides recommendations |
| Smart Retry | get_retry_success_rates, get_recovery_opportunities | Evaluates failed transactions → Recommends retry strategy |
| Orchestrator | (calls specialists) | Understands query → Routes to specialists → Synthesizes results |

### Best practice: agent tools in their own schema vs same schema as data

| Approach | Use when | Pros | Cons |
|----------|----------|------|------|
| **Dedicated schema** (e.g. `agent_tools`) | Multiple teams, strict governance, or you want least-privilege for callers | Clear boundary between “data” and “tools”; grant `EXECUTE` on the tools schema only so callers don’t need direct `SELECT` on tables; easier to audit and hand off agent tool lifecycle | One extra schema to create and maintain; functions reference `catalog.data_schema.*` in SQL |
| **Same schema as data** (e.g. `payment_analysis`) | Single team, simpler setup, or you prefer all analytics assets in one place | One schema for tables, views, and functions; fewer objects to manage; no cross-schema references in DDL | Callers need both `SELECT` and `EXECUTE` on the same schema; tools and data are mixed for discovery |

**Recommendation:** This project uses the **same schema as data** (`payment_analysis`) for agent tool functions: one schema for tables, views, volumes, and UC functions. Use a dedicated schema (e.g. `agent_tools`) only if you need strict least-privilege or separate governance for agent tools.

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
| 1 | UC functions for tools (in `catalog.schema`, e.g. `ahs_demos_catalog.payment_analysis`) | `src/payment_analysis/agents/uc_tools/` |
| 2 | LangGraph agents (all 5) | `src/payment_analysis/agents/langgraph_agents.py` |
| 3 | Log & register all to UC | Notebook using get_all_agent_builders() |
| 4 | Deploy all to Model Serving | Per-agent or loop |
| 5 | Multi-Agent Supervisor | Workspace → Agents → Multi-Agent Supervisor |

---

## Step 1: Unity Catalog Functions (Tools)

Create all agent tool functions in the **same schema as your data** (`payment_analysis`). The SQL substitutes `__CATALOG__` and `__SCHEMA__`; functions are created in `{catalog}.{schema}` and read from `{catalog}.{schema}.payments_enriched_silver` and gold views (e.g. `v_top_decline_reasons`).

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
- Placeholders `__CATALOG__` and `__SCHEMA__` are replaced with your data catalog and schema (e.g. `ahs_demos_catalog`, `payment_analysis`).
- Creates in `{catalog}.{schema}`: `get_decline_trends`, `get_decline_by_segment`, `get_route_performance`, `get_cascade_recommendations`, `get_retry_success_rates`, `get_recovery_opportunities`, `get_high_risk_transactions`, `get_risk_distribution`, `get_kpi_summary`, `get_optimization_opportunities`, `get_trend_analysis`.

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
agent = create_decline_analyst_agent(catalog, llm_endpoint="databricks-meta-llama-3-3-70b-instruct")
result = agent.invoke({"messages": [HumanMessage(content="What are the top decline reasons?")]})
```

---

## Step 3: Log and Register All Agents to Unity Catalog

Log all five agents with MLflow LangChain flavor and register to UC in one loop using **get_all_agent_builders()**.

```python
import mlflow
from payment_analysis.agents.langgraph_agents import get_all_agent_builders

mlflow.set_registry_uri("databricks-uc")
catalog = "ahs_demos_catalog"  # or var.catalog (same as data catalog)
model_registry_schema = "agents"  # Bundle creates this schema (unity_catalog.yml agents_schema)
llm_endpoint = "databricks-meta-llama-3-3-70b-instruct"

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
            name=f"{catalog}.{model_registry_schema}.{name}",
        )
```

Registered names: `{catalog}.agents.decline_analyst`, `.agents.smart_routing`, `.agents.smart_retry`, `.agents.risk_assessor`, `.agents.performance_recommender`. Job 6 passes `model_registry_catalog` and `model_registry_schema` (default: same catalog, schema `agents`). The bundle creates the `agents` schema in the catalog (resources/unity_catalog.yml).

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

- **Mosaic AI Agent Framework (AgentBricks):** Tool-Calling agents (LangGraph ReAct) + Multi-Agent Supervisor; MLflow tracing, UC tools, Model Serving.
- [Integrate LangChain with Databricks Unity Catalog tools](https://docs.databricks.com/en/generative-ai/agent-framework/langchain-uc-integration)
- [Create AI agent tools using Unity Catalog functions](https://docs.databricks.com/en/generative-ai/agent-framework/create-custom-tool)
- [Log and load LangChain models with MLflow](https://mlflow.org/docs/latest/python_api/mlflow.langchain.html)
- **AgentBricks:** **Multi-Agent Supervisor** in the workspace **Agents** UI; optional **Mosaic AI Agent Evaluation** for evaluation suite.
