# Reference: Databricks, Agents, Model Serving & Approval Optimization

Technical reference for **Databricks feature alignment**, **agent architecture**, **model serving and UC functions**, and **approval-rate optimization**. For deploy and troubleshooting see [DEPLOYMENT.md](DEPLOYMENT.md); for architecture and business context see [GUIDE.md](GUIDE.md).

---

## 1. Databricks feature validation

The solution is Databricks-native and aligned with current product naming (Lakeflow, Unity Catalog, PRO serverless SQL, Lakebase Autoscaling, Databricks App, Genie, Model Serving, Lakeview dashboards). **All compute is serverless** — jobs, pipelines, SQL warehouse, and model serving endpoints use serverless compute.

| Area | Status | Notes |
|------|--------|--------|
| **Bundle** | OK | Single bundle; `workspace.root_path`; sync and app use same root; `experimental.skip_name_prefix_for_schema: true` → schema `payment_analysis`. |
| **Unity Catalog** | OK | Catalog/schema from variables; volumes: raw_data, checkpoints, ml_artifacts, reports. Schemas: `payment_analysis` (data) and `agents` (ML models). |
| **SQL Warehouse** | OK | PRO, serverless; dashboards and gold-view SQL. |
| **Lakeflow** | OK | ETL and Real-time pipelines; serverless, continuous, Photon. |
| **Jobs** | OK | 7 serverless jobs; tasks use `environment_key` for custom dependencies. |
| **App** | OK | `resources/fastapi_app.yml`; bindings for SQL warehouse, jobs 1–7, serving endpoints; OBO when opened from Compute → Apps. |
| **Lakebase** | OK | Autoscaling Postgres; Job 1 creates project/branch/endpoint; app env: LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID. Used for rules, experiments, incidents, online features, app config. |
| **Vector Search** | OK | Delta-sync index (`similar_transactions_index`) on `transaction_summaries_for_search`; embedding model `databricks-bge-large-en`. Agents use `VECTOR_SEARCH()` SQL function for similar-transaction lookup. |
| **Genie** | OK | Job 7 syncs space; optional app binding. |
| **Model Serving** | OK | 7 endpoints in `model_serving.yml` (3 agents + 4 ML models); app binds after endpoints exist (two-phase deploy). Scale-to-zero enabled. |
| **Dashboards** | OK | 3 unified Lakeview dashboards; prepare → `.build/dashboards/`; Job 4 or bundle.sh publishes with embed credentials. Embed uses `/embed/dashboardsv3/` path prefix. |

**User token (OBO):** When the app is opened from **Compute → Apps**, Databricks forwards the user token in **X-Forwarded-Access-Token**. The backend reads it in `dependencies.py` via `_get_obo_token(request)` and uses it for `get_workspace_client` / `get_databricks_service`. For other frameworks: FastAPI `request.headers.get("X-Forwarded-Access-Token")`; Flask/Gradio/Streamlit/Shiny use the same header name.

**SDK:** `databricks-sdk==0.88.0` pinned in `pyproject.toml`. Re-validate when adding resources or upgrading.

---

## 2. Agent architecture

The solution uses three agent patterns, each optimized for a different use case:

| Pattern | Implementation | When used |
|---------|---------------|-----------|
| **ResponsesAgent** (MLflow) | `agent.py` — single OpenAI Responses API agent with UC function tools | Registered by Job 6 task 2; lightweight single-agent endpoint. |
| **LangGraph multi-agent** (AgentBricks) | `langgraph_agents.py` — orchestrator + 5 specialists (LangGraph StateGraph) | Registered by Job 6 task 3; deployed as `payment-analysis-orchestrator` and `decline-analyst` endpoints. |
| **Custom Python framework** | `agent_framework.py` — orchestrator + specialists with direct SQL tools | Run by Job 6 task 1; fallback when Model Serving unavailable. |

**Agent tools — Lakebase and Vector Search integration:**

| Tool category | Implementation | Data source |
|---------------|---------------|-------------|
| **UC SQL functions** (12 tools) | Created by Job 3 from `uc_agent_tools.sql` | Unity Catalog gold views |
| **Vector Search** | `VECTOR_SEARCH()` TVF in `search_similar_transactions` UC function | `similar_transactions_index` |
| **Lakebase queries** | `get_active_approval_rules`, `get_recent_incidents`, `get_decision_outcomes` | Lakebase Postgres via UC functions |
| **Python exec** | `system.ai.python_exec` for write-back (recommendations) | Spark SQL |

**Orchestrator in the app:** When `ORCHESTRATOR_SERVING_ENDPOINT` is set (e.g. `payment-analysis-orchestrator` in `app.yml`), the app calls that Model Serving endpoint. Otherwise it falls back to Job 6 (custom Python).

**To deploy agents to Model Serving:** (1) Run Job 6 to register models in UC. (2) Include `resources/model_serving.yml` and deploy. (3) Set `ORCHESTRATOR_SERVING_ENDPOINT` in `app.yml`.

---

## 3. Model serving endpoints (7)

| Endpoint name | Entity (UC) | Purpose | Workload |
|---------------|-------------|---------|----------|
| **payment-analysis-orchestrator** | `{catalog}.agents.orchestrator` | Multi-agent orchestrator (LangGraph); routes to specialists | Small, CPU, scale-to-zero |
| **decline-analyst** | `{catalog}.agents.decline_analyst` | Decline analysis specialist (LangGraph) | Small, CPU, scale-to-zero |
| **payment-response-agent** | `{catalog}.agents.response_agent` | ResponsesAgent (single-agent, OpenAI Responses API) | Small, CPU, scale-to-zero |
| **approval-propensity** | `{catalog}.{schema}.approval_propensity_model` | Approval probability prediction | Small, CPU, scale-to-zero |
| **risk-scoring** | `{catalog}.{schema}.risk_scoring_model` | Fraud risk scoring | Small, CPU, scale-to-zero |
| **smart-routing** | `{catalog}.{schema}.smart_routing_policy` | Optimal route selection (standard, 3DS, token, passkey) | Small, CPU, scale-to-zero |
| **smart-retry** | `{catalog}.{schema}.smart_retry_policy` | Retry success prediction and timing | Small, CPU, scale-to-zero |

**AI Gateway rate limits:** ML model endpoints have 100–200 req/min/user. Agent endpoints use environment variables for catalog, schema, and tiered LLM endpoints.

**ML model signatures:** All 4 ML models use explicit `ModelSignature` with `ColSpec` for named input features, ensuring correct feature handling during serving.

### UC functions (12 agent tools)

Created by **Job 3** task `create_uc_agent_tools` from `uc_agent_tools.sql`:

| Function | Purpose | Data source |
|----------|---------|-------------|
| `get_kpi_summary` | Executive KPIs | Gold views |
| `get_decline_trends` | Decline patterns by reason | Gold views |
| `get_route_performance` | Routing performance by solution | Gold views |
| `get_recovery_opportunities` | Recoverable decline segments | Gold views |
| `get_retry_success_rates` | Retry success by scenario | Gold views |
| `get_high_risk_transactions` | High fraud-score transactions | Gold views |
| `get_risk_distribution` | Risk tier distribution | Gold views |
| `get_optimization_opportunities` | Segments with improvement potential | Gold views |
| `get_trend_analysis` | Approval rate trends | Gold views |
| `get_decline_by_segment` | Decline breakdown by segment | Gold views |
| `search_similar_transactions` | Vector similarity search | Vector Search index |
| `get_active_approval_rules` | Business rules from Lakebase | Lakebase (via UC) |

---

## 4. Approval optimization summary

**Artifacts:** 4 ML models (approval propensity, risk, routing, retry) + 3 agent models (orchestrator, decline analyst, response agent); 12 UC functions; 3 unified dashboards.

**How each component accelerates approval rates:**

| Component | Mechanism |
|-----------|-----------|
| **Approval propensity model** | Predicts approval likelihood to avoid declining likely-good transactions |
| **Risk scoring model** | Enables risk-based auth (step-up for high risk, frictionless for low risk) |
| **Smart routing policy** | Routes to solution maximizing approval rate for the segment |
| **Smart retry policy** | Predicts retry success and optimal timing to recover otherwise-lost approvals |
| **Orchestrator agent** | Coordinates specialists to provide unified, actionable recommendations |
| **Decline analyst agent** | Identifies decline patterns and recovery opportunities |
| **Vector Search** | "Similar cases" for retry and routing recommendations |
| **Rules engine** | Configurable business rules; operators tune without code |

---

## 5. References

- [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/)
- [Agent Bricks: Supervisor Agent](https://docs.databricks.com/en/generative-ai/agent-bricks/multi-agent-supervisor)
- [Create AI agent tools using Unity Catalog functions](https://docs.databricks.com/en/generative-ai/agent-framework/create-custom-tool)
- [Manage dashboard embedding](https://docs.databricks.com/en/ai-bi/admin/embed)
- **Config:** `resources/model_serving.yml`, `resources/fastapi_app.yml`, `app.yml` (project root)
