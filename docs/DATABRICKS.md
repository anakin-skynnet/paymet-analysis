# Databricks: Validation, Implementation & Agents

Single reference for **Databricks feature alignment**, **implementation review** (custom vs native), and **AgentBricks conversion**. Use for deployment readiness, upgrade reviews, and agent migration.

**References:** [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/), [Lakeflow](https://docs.databricks.com/en/lakeflow/index.html), [Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/), [Databricks Apps](https://docs.databricks.com/en/apps/index.html), [Mosaic AI](https://docs.databricks.com/en/generative-ai/index.html).

---

## Part 1 — Feature validation

Validates that the solution is **Databricks-native** and aligned with **current product naming and APIs**.

### 1.1 Bundle (DAB)

| Item | Status | Notes |
|------|--------|--------|
| Bundle structure | OK | Single bundle `payment-analysis`; `databricks.yml` at root. |
| Workspace root | OK | `workspace.root_path` per user; sync and app use same root. |
| Experimental | OK | `experimental.skip_name_prefix_for_schema: true` so schema stays `payment_analysis` in dev. |
| Sync | OK | `.build`, `src/payment_analysis/*` uploaded for jobs and app. |
| Targets | OK | `default` and `dev`/`prod`; variables overridden per target. |

### 1.2 Unity Catalog, SQL Warehouse, Lakeflow, Jobs, App, Lakebase, Genie, Model Serving, Dashboards

- **Unity Catalog:** Catalog/schema from variables; single schema `payment_analysis` for data, views, ML, tools. Volumes: `raw_data`, `checkpoints`, `ml_artifacts`, `reports`.
- **SQL Warehouse:** `warehouse_type: "PRO"`, `enable_serverless_compute: true`. Dashboards, ad-hoc SQL, gold view SQL task.
- **Lakeflow:** Pipelines are **Lakeflow**; code uses `dlt`. Two pipelines: ETL (Bronze→Silver→Gold) and Real-time. `serverless: true`, `continuous: true`, `photon: true`.
- **Jobs:** `resources/ml_jobs.yml`, `agents.yml`, etc.; serverless compute default for notebook, Python wheel, SQL. Jobs 1–7 and pipelines 8–9 documented in [DEPLOYMENT.md](DEPLOYMENT.md).
- **Databricks App:** `resources/fastapi_app.yml`; bindings for SQL warehouse, jobs 1–7. OBO when opened from Compute → Apps. Lakebase env: LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID.
- **Lakebase:** **Lakebase Autoscaling** only. Job 1 task `create_lakebase_autoscaling` creates project/branch/endpoint; `lakebase_data_init` seeds app_config, approval_rules, online_features, app_settings.
- **Genie:** **Genie** (Mosaic AI Genie). Job 7 syncs space config and sample questions. Optional app binding.
- **Model Serving & Mosaic AI Gateway:** Endpoints in `model_serving.yml`. `serving_endpoints.query()` for chat and model inference. ChatDatabricks in LangGraph agents.
- **Dashboards:** **Lakeview** (`.lvdash.json`). `scripts/dashboards.py prepare` → `.build/dashboards/`. Job 4 publishes with embed credentials.

### 1.3 Agents & AI (summary)

| Item | Status |
|------|--------|
| LLM | All agent LLM calls use **Mosaic AI** (Model Serving) via `serving_endpoints.query()` or ChatDatabricks. |
| Production path | **Custom** Python framework (Job 6): `agent_framework.py`; in-app-style tools via Statement Execution; no MLflow tracing, no agent Model Serving. |
| AgentBricks path | **Available:** `langgraph_agents.py` — LangGraph + ChatDatabricks + UCFunctionToolkit; MLflow log/register; deployable to Model Serving. See **Part 3** below. |
| UC agent tools | `uc_agent_tools.sql`; **Job 3** task `create_uc_agent_tools` creates them in catalog.schema after gold views. |

### 1.4 SDK & dependencies

- **Databricks SDK:** `databricks-sdk==0.86.0` (pinned). WorkspaceClient for jobs, pipelines, SQL, serving. OBO from request or env.
- **Recommendation:** Re-run this validation when adding resources or upgrading SDK. Prefer AgentBricks for new agent work (see Part 2 and Part 3).

---

## Part 2 — Implementation review

**What is already Databricks-native:** DAB, Lakeflow, Unity Catalog, Delta, CDF, dlt, serverless SQL, MLflow, UC model registry, Model Serving (ML + LLM), Vector Search, Lakebase, Genie, Lakeview dashboards, OBO auth.

**Gap: Custom AI framework vs AgentBricks + Mosaic AI**

- **Current:** App calls Job 6 → custom `agent_framework.py`. LLM = Databricks Model Serving (Mosaic AI) ✓. Tools = Statement Execution ✓. Rules = Lakebase ✓. **Runtime = custom Python** (no MLflow tracing, no UC-registered agent models, no Model Serving endpoints for agents).
- **AgentBricks path:** `langgraph_agents.py` — LangGraph + ChatDatabricks + UCFunctionToolkit; same prompts and tool semantics; can be deployed as Model Serving endpoints and orchestrated by **Workspace Multi-Agent Supervisor**.

**Recommendation**

1. **Use AgentBricks (LangGraph + UC tools + Mosaic AI) as primary:** Same schema as data (`payment_analysis`) for UC functions. Run `create_uc_agent_tools` as part of Job 3. Option A: Add task/job to build agents from `langgraph_agents.py`, log to MLflow, register to UC, deploy to Model Serving; then have app call agent endpoints instead of Job 6. Option B: Use **Workspace Multi-Agent Supervisor** so all agent traffic goes through Databricks Agents + Model Serving. See [Part 3](#part-3--agent-framework-agentbricks).
2. Keep custom framework only as fallback or for local/dev.
3. **Mosaic AI Gateway:** Use for governed LLM (rate limits, guardrails) where required.

**Other considerations**

| Area | Current | Recommendation |
|------|---------|----------------|
| Feature Store | Not used | Optional: Databricks Feature Store for shared/real-time features. |
| Agent evaluation | None | Optional: Mosaic AI Agent Evaluation with AgentBricks. |
| UC functions for tools | Job 3 `create_uc_agent_tools` | Done. |
| Orchestrator as Model Serving | Runs as job (notebook) | Deploy orchestrator/Multi-Agent Supervisor as Model Serving for lower latency and scaling. |

---

## Part 3 — Agent framework (AgentBricks)

Converts payment analysis Python agents to **Mosaic AI Agent Framework (AgentBricks)**: same five specialists and orchestrator, implemented with **MLflow + LangGraph**, tools as **Unity Catalog functions**, deployable to **Model Serving**. **Multi-Agent Supervisor** replaces the Python `OrchestratorAgent`.

### Current vs AgentBricks

| Python agent | AgentBricks type | UC tools (examples) |
|--------------|-----------------|---------------------|
| SmartRoutingAgent | Tool-Calling (LangGraph ReAct) | get_route_performance, get_cascade_recommendations |
| SmartRetryAgent | Tool-Calling | get_retry_success_rates, get_recovery_opportunities |
| DeclineAnalystAgent | Tool-Calling | get_decline_trends, get_decline_by_segment |
| RiskAssessorAgent | Tool-Calling | get_high_risk_transactions, get_risk_distribution |
| PerformanceRecommenderAgent | Tool-Calling | get_kpi_summary, get_optimization_opportunities, get_trend_analysis |
| OrchestratorAgent | Multi-Agent Supervisor | Routes to above specialists |

**Best practice:** This project uses the **same schema as data** (`payment_analysis`) for agent tool functions. Use a dedicated schema (e.g. `agent_tools`) only if you need strict least-privilege.

### Conversion steps (high level)

1. **UC functions for tools** — In `catalog.schema` (e.g. `payment_analysis`). Source: `src/payment_analysis/agents/uc_tools/uc_agent_tools.sql`; placeholders `__CATALOG__`/`__SCHEMA__` replaced at run. Job 3 task `create_uc_agent_tools` creates them after gold views.
2. **LangGraph agents** — All five in `src/payment_analysis/agents/langgraph_agents.py` (create_decline_analyst_agent, create_smart_routing_agent, etc.). Use `get_all_agent_builders()` for one-loop register/deploy.
3. **Log and register to UC** — MLflow LangChain flavor; register to `{catalog}.agents.{name}`.
4. **Deploy to Model Serving** — Per-agent endpoint or via Agents API / UI.
5. **Multi-Agent Supervisor** — Workspace → Agents → Multi-Agent Supervisor; add all five as subagents; use its endpoint in the app.

### Hybrid architecture (recommended)

- **App:** UI/UX, orchestration logic (route query → supervisor/agent), business rules, dashboards, jobs.
- **Agents:** Specialists and Multi-Agent Supervisor on **Model Serving**; app calls endpoints. Benefits: independent scaling, update agents without app redeploy, MLflow tracing, reuse endpoints across apps.

### References

- [Integrate LangChain with Databricks Unity Catalog tools](https://docs.databricks.com/en/generative-ai/agent-framework/langchain-uc-integration)
- [Create AI agent tools using Unity Catalog functions](https://docs.databricks.com/en/generative-ai/agent-framework/create-custom-tool)
- [Log and load LangChain models with MLflow](https://mlflow.org/docs/latest/python_api/mlflow.langchain.html)
