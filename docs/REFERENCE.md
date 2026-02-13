# Reference: Databricks, Agents, Model Serving & Approval Optimization

Single reference for **Databricks feature alignment**, **agent runtime vs AgentBricks**, **model serving and UC functions**, and **approval-rate optimization**. For deploy and troubleshooting see [DEPLOYMENT.md](DEPLOYMENT.md); for architecture and business context see [GUIDE.md](GUIDE.md).

---

## 1. Databricks feature validation

The solution is Databricks-native and aligned with current product naming (Lakeflow, Unity Catalog, PRO serverless SQL, Lakebase Autoscaling, Databricks App, Genie, Model Serving, Lakeview dashboards).

| Area | Status | Notes |
|------|--------|--------|
| **Bundle** | OK | Single bundle; `workspace.root_path`; sync and app use same root; `experimental.skip_name_prefix_for_schema: true` → schema `payment_analysis`. |
| **Unity Catalog** | OK | Catalog/schema from variables; volumes: raw_data, checkpoints, ml_artifacts, reports. |
| **SQL Warehouse** | OK | PRO, serverless; dashboards and gold-view SQL. |
| **Lakeflow** | OK | ETL and Real-time pipelines; serverless, continuous, Photon. |
| **App** | OK | `resources/fastapi_app.yml`; bindings for SQL warehouse, jobs 1–7; OBO when opened from Compute → Apps. |
| **Lakebase** | OK | Autoscaling only; Job 1 creates project/branch/endpoint; app env: LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID. |
| **Genie** | OK | Job 7 syncs space; optional app binding. |
| **Model Serving** | OK | Endpoints in `model_serving.yml`; app can bind after endpoints exist (two-phase deploy). |
| **Dashboards** | OK | Lakeview `.lvdash.json`; prepare → `.build/dashboards/`; Job 4 or bundle.sh publishes with embed credentials. |

**User token (OBO):** When the app is opened from **Compute → Apps**, Databricks forwards the user token in **X-Forwarded-Access-Token**. The backend reads it in `dependencies.py` via `_get_obo_token(request)` and uses it for `get_workspace_client` / `get_databricks_service`. For other frameworks: FastAPI `request.headers.get("X-Forwarded-Access-Token")`; Flask/Gradio/Streamlit/Shiny use the same header name from their request/session object.

**SDK:** `databricks-sdk` pinned in `pyproject.toml`. Re-validate when adding resources or upgrading.

---

## 2. Agent stack: runtime vs AgentBricks

| Question | Answer |
|----------|--------|
| **Orchestrator chat in the app** | If **ORCHESTRATOR_SERVING_ENDPOINT** is set (e.g. in `app.yml` or App Environment), the app calls that **Model Serving** endpoint (AgentBricks/Supervisor). Otherwise it falls back to **Job 6** (custom Python `agent_framework.py`). |
| **AgentBricks (LangGraph)** | Used to **build and register** agents to Unity Catalog (Job 6, task 2). The registered **orchestrator** is deployed as **payment-analysis-orchestrator** when `model_serving.yml` is included. |
| **AI Framework PySpark** | **Not used.** Tools run SQL via Databricks (Statement Execution or UC functions); agent logic is Python (custom) or LangGraph. |

**To use AgentBricks orchestrator in the app:** (1) Run Job 6 so `catalog.agents.orchestrator` exists. (2) Include `resources/model_serving.yml` and deploy so **payment-analysis-orchestrator** endpoint exists. (3) Set **ORCHESTRATOR_SERVING_ENDPOINT** = `payment-analysis-orchestrator` in `app.yml` or App Environment. The app’s Orchestrator chat will then call that endpoint instead of Job 6.

**No-code Supervisor:** Workspace → Agents → Supervisor Agent can combine Genie, UC functions, and other agents. Deploy it as a serving endpoint and set **ORCHESTRATOR_SERVING_ENDPOINT** to that endpoint name to use it from the app.

### AgentBricks Supervisor Agent (GA Feb 2026)

AgentBricks Supervisor Agent is now **Generally Available** (Feb 10, 2026). It provides a managed orchestration layer that can replace or complement the custom LangGraph orchestrator.

| Feature | Current (LangGraph) | AgentBricks Supervisor |
|---------|---------------------|----------------------|
| Creation | Code-based (Python) | **UI-based** (Agents > Supervisor Agent > Build) |
| Routing | Custom LLM router node | **Managed** (Databricks handles routing) |
| Sub-agents | In-process LangGraph nodes | Genie Spaces, Knowledge Assistant endpoints, UC functions, MCP servers (up to 10) |
| Improvement | Change code, redeploy | **ALHF** (Agent Learning on Human Feedback from SMEs) |
| Auth | Custom config | **OBO** (On-Behalf-Of, Unity Catalog governed) |
| SDK creation | N/A | Not yet available (UI only) |

**Migration path:** (1) Create a Supervisor Agent in the workspace UI. (2) Add the 11 UC functions as tools and the Genie Space as a sub-agent. (3) Set instructions for payment analysis routing. (4) Update `ORCHESTRATOR_SERVING_ENDPOINT` in `app.yml` to point to the new Supervisor endpoint. The existing backend code (`_query_orchestrator_endpoint`) works with the Supervisor endpoint with zero changes. Keep the LangGraph orchestrator as Job 6 fallback.

**Requirements:** Workspace in `us-east-1` or `us-west-2`; serverless compute; Unity Catalog; OBO authorization enabled; `databricks-gte-large-en` with AI Guardrails disabled.

**Limitation:** Only Knowledge Assistant agent endpoints are supported as sub-agents (not custom LangGraph endpoints). However, the 11 UC functions can be added directly as tools, achieving the same result.

**References:** [Agent Bricks: Supervisor Agent](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor), [Blog: Supervisor Agent GA](https://www.databricks.com/blog/agent-bricks-supervisor-agent-now-ga-orchestrate-enterprise-agents).

---

## 3. Model serving & UC functions

### Model serving endpoints (5+1)

| App resource | Endpoint name | Purpose |
|--------------|---------------|--------|
| serving-orchestrator | payment-analysis-orchestrator | Orchestrator agent (LangGraph Supervisor). |
| serving-decline-analyst | decline-analyst | Decline analyst agent (LangGraph). |
| serving-approval-prop | approval-propensity | Approval probability; Decisioning. |
| serving-risk-scoring | risk-scoring | Fraud risk; risk-based auth. |
| serving-smart-routing | smart-routing | Optimal route (standard, 3DS, token, passkey). |
| serving-smart-retry | smart-retry | Retry success likelihood and timing. |

**Note:** Endpoint names do **not** include the environment suffix (e.g. `approval-propensity`, not `approval-propensity-dev`). The backend's `databricks_service.py` was updated to remove the `-{ENVIRONMENT}` suffix to match DAB-deployed names.

**Creation:** Run **Step 5 (Train ML Models)** so models exist in UC. Then run `./scripts/bundle.sh deploy app dev` (phase 2) — it uncomments `model_serving.yml` and serving bindings and deploys.

**Business value:** Approval propensity reduces false declines; risk enables frictionless vs step-up; routing and retry improve approval rate and recovery.

### UC functions (11 agent tools)

Created by **Job 3** task **create_uc_agent_tools** from `src/payment_analysis/agents/uc_tools/uc_agent_tools.sql`. Used by the agent framework and LangGraph agents: get_kpi_summary, get_decline_trends, get_route_performance, get_recovery_opportunities, get_retry_success_rates, get_high_risk_transactions, get_risk_distribution, get_optimization_opportunities, get_trend_analysis, get_decline_by_segment, get_cascade_recommendations.

**App permission:** Add each function in **Compute → Apps → payment-analysis → Edit → Configure → App resources → Function** with **Can execute**.

---

## 4. Implementation review (custom vs AgentBricks)

**Current:** App can call Job 6 → custom `agent_framework.py` (LLM = Mosaic AI; tools = Statement Execution). **AgentBricks path:** `langgraph_agents.py` — LangGraph + ChatDatabricks + UC functions; register to UC and deploy to Model Serving.

**Recommendation:** Use AgentBricks Supervisor Agent (GA Feb 2026) as the primary orchestrator for production — managed, built-in ALHF, OBO auth, no custom code to maintain. Keep the LangGraph orchestrator (Model Serving endpoint `payment-analysis-orchestrator`) as the secondary path, and Job 6 (custom Python) as the fallback. Set **ORCHESTRATOR_SERVING_ENDPOINT** to whichever endpoint you prefer.

**Conversion paths:**
- **(A) AgentBricks Supervisor (recommended for new setups):** Create in workspace UI → add 11 UC functions + Genie Space → set `ORCHESTRATOR_SERVING_ENDPOINT` to the Supervisor endpoint.
- **(B) LangGraph + Model Serving (current):** (1) UC functions from Job 3. (2) LangGraph agents in `langgraph_agents.py`. (3) Log/register to UC via Job 6 task 2. (4) Deploy to Model Serving via `model_serving.yml`. (5) Set `ORCHESTRATOR_SERVING_ENDPOINT = payment-analysis-orchestrator`.
- **(C) Hybrid:** Supervisor as primary → LangGraph endpoint as fallback → Job 6 as last resort.

---

## 5. Approval optimization (summary)

**Artifacts:** 5 registered models (approval propensity, risk, routing, retry, decline_analyst); 11 UC functions. **Recommendations:** Serve a **Supervisor AgentBricks** (orchestrator) as one endpoint; wire **smart_retry_policy** into Decisioning retry API for ML-driven retry; add an **approval-optimization API** that calls UC functions for structured insight cards. Use the supervisor for conversational “one place” insights; use UC functions for dashboards and batch reports without going through an agent.

---

## 6. References

- [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/)
- [Agent Bricks: Supervisor Agent](https://docs.databricks.com/en/generative-ai/agent-bricks/multi-agent-supervisor)
- [Create AI agent tools using Unity Catalog functions](https://docs.databricks.com/en/generative-ai/agent-framework/create-custom-tool)
- **Config:** `resources/model_serving.yml`, `resources/fastapi_app.yml`, `app.yml` (project root)
