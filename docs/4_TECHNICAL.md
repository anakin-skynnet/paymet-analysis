# 4. Technical

Architecture and implementation reference.

## Architecture

- **Databricks:** Simulator → **Lakeflow** (Bronze → Silver → Gold) → Unity Catalog (12+ views, 4 models). MLflow, Model Serving, Mosaic AI Gateway, Genie. 11 AI/BI dashboards, SQL Warehouse.
- **App:** FastAPI (analytics, decisioning, notebooks, dashboards, agents) ↔ React (dashboard, dashboards, notebooks, models, ai-agents, decisioning, experiments, declines).

## Data Layer

Bronze: raw + `_ingested_at`. Silver: quality, `risk_tier`, `amount_bucket`, `composite_risk_score`. Gold: 12+ views. UC: `ahs_demos_catalog.ahs_demo_payment_analysis_dev` — governance, lineage, audit.

**Lakehouse recommendations & Vector Search:** `vector_search_and_recommendations.sql` defines `transaction_summaries_for_search` (Delta, source for Vector Search index), `approval_recommendations`, and view `v_recommendations_from_lakehouse`. The app’s **Decisioning** page shows a “Similar cases & recommendations (Lakehouse)” card fed by `GET /api/analytics/recommendations`, which reads from this view to accelerate approval decisions (e.g. similar transactions, retry suggestions). Vector Search index (`resources/vector_search.yml`) syncs from the search table using `databricks-bge-large-en`; when populated, it can power similar-transaction lookups and RAG for agents.

**Approval rules (Lakehouse):** `approval_rules.sql` defines `approval_rules` and view `v_approval_rules_active`. The app **Rules** page (sidebar) lets users create, edit, and delete rules stored in this table. ML and AI agents (e.g. Smart Routing, Smart Retry, Orchestrator) can read from `catalog.schema.approval_rules` or `v_approval_rules_active` to apply business rules and accelerate approval rates alongside model outputs. API: `GET/POST /api/rules`, `PATCH/DELETE /api/rules/{id}`.

**Online features (Lakehouse):** `online_features.sql` defines `online_features` and view `v_online_features_latest`. Features from ML and AI processes are stored here; the app **Dashboard** shows them in the "Online features (Lakehouse)" card. API: `GET /api/analytics/online-features` (optional `source=ml|agent`, `limit`). Populate from decisioning, model serving, or agent jobs.

## ML Layer

Models: approval propensity (RF ~92%), risk (~88%), routing (RF ~75%), retry (~81%). MLflow → UC Registry → Serving (<50ms p95, scale-to-zero). Lifecycle: experiment → register → serve → monitor → retrain.

## AI Agents (Summary)

Genie 2, Model serving 3, Mosaic AI Gateway (LLM) 2. Agent jobs: [agents.yml](../resources/agents.yml). Details: [3_AGENTS_VALUE](3_AGENTS_VALUE.md).

## Analytics

11 dashboards are defined in `resources/dashboards.yml` and sourced from `src/payment_analysis/dashboards/*.lvdash.json`; default catalog/schema; warehouse from bundle `var.warehouse_id`. Genie: spaces use catalog/schema; see `genie_spaces.yml`.

## Application Layer

**Backend:** `/api/analytics`, `/api/decisioning`, `/api/notebooks`, `/api/dashboards`, `/api/agents`, `/api/rules`, `/api/setup`. UC via Databricks SQL. **Frontend:** React + TanStack Router; `lib/api.ts`. **Stack:** Delta, UC, Lakeflow, SQL Warehouse, MLflow, Serving, Dashboards, Genie, Mosaic AI Gateway, FastAPI, React, TypeScript, Bun, TailwindCSS, Databricks Asset Bundles.

## Bundle & Deploy

`databricks.yml`: variables `catalog`, `schema`, `environment`, `warehouse_id`; include pipelines, jobs, unity_catalog, vector_search, dashboards, model_serving, genie_spaces, agents, ai_gateway, streaming_simulator. Agent jobs in `resources/agents.yml`; Mosaic AI Gateway in `resources/ai_gateway.yml` (and on endpoints in model_serving.yml). Dashboard JSONs from `src/payment_analysis/dashboards/`. Commands: `databricks bundle validate -t dev`, `databricks bundle deploy -t dev`. For prod catalog/schema in dashboards use `./scripts/validate_bundle.sh prod`. App: `.env` (DATABRICKS_HOST, TOKEN, WAREHOUSE_ID, CATALOG, SCHEMA); `uv run apx dev` or `apx build` + deploy.

## Workspace components ↔ UI mapping

Every Databricks workspace component (bundle resource) is linked from the app so users can run or open it with one click.

| Workspace component | Bundle resource | UI location | One-click action |
|---------------------|-----------------|-------------|------------------|
| Transaction Stream Simulator | `streaming_simulator.transaction_stream_simulator` | **Setup & Run** step 1 | Run simulator / Open job (run) |
| Payment Analysis ETL (Lakeflow) | `pipelines.payment_analysis_etl` | **Setup & Run** step 2 | Start ETL pipeline / Open pipeline |
| Create Gold Views | `ml_jobs.create_gold_views_job` | **Setup & Run** step 3 | Run gold views job / Open job (run) |
| Lakehouse tables (SQL) | — | **Setup & Run** step 4 | Open SQL Warehouse / Explore schema |
| Train ML Models | `ml_jobs.train_ml_models_job` | **Setup & Run** step 5 | Run ML training / Open job (run) |
| Orchestrator Agent | `jobs.orchestrator_agent_job` (agents.yml) | **Setup & Run** step 6 | Run orchestrator / Open job (run) |
| Specialist agents (5) | `jobs.smart_routing_agent_job` etc. (agents.yml) | **Setup & Run** step 6b | Run Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender / Open job each |
| Real-time pipeline | `pipelines.payment_realtime_pipeline` | **Setup & Run** step 7 | Start real-time pipeline / Open pipeline |
| Continuous Stream Processor | `streaming_simulator.continuous_stream_processor` | **Setup & Run** Quick links | Stream processor (run) |
| Test Agent Framework | `ml_jobs.test_agent_framework_job` | **Setup & Run** Quick links (if job ID set) | Test Agent Framework / All jobs |
| 11 Dashboards | `dashboards.*` | **Dashboards** page | List from `GET /api/dashboards`; click card opens in workspace |
| Notebooks | workspace files | **Notebooks** page + Decisioning / Models / Setup | List from `GET /api/notebooks`; open folder/notebook URL |
| AI agents (catalog) | — | **AI Agents** page | List from `GET /api/agents/agents`; Open Genie, Open agents folder |
| ML models (UC) | Model Registry (post–train job) | **ML Models** page | List from `GET /api/analytics/models`; open Model Registry / MLflow |
| Rules (Lakehouse) | UC table `approval_rules` | **Rules** page | CRUD via `GET/POST/PATCH/DELETE /api/rules` |
| Recommendations / Online features | UC views/tables | **Dashboard**, **Decisioning** | `GET /api/analytics/recommendations`, `GET /api/analytics/online-features` |
| SQL Warehouse | `sql_warehouse.payment_analysis_warehouse` | **Setup** params + Quick links | SQL Warehouse link; warehouse_id in run params |
| Genie | `genie_spaces` (optional) | **AI Agents** | Open Genie to chat |

Job and pipeline IDs in the app come from `GET /api/setup/defaults` (backend `DEFAULT_IDS` or env). Set `DATABRICKS_JOB_ID_TEST_AGENT_FRAMEWORK` after deploy to enable the Test Agent Framework quick link.

## UI & verification checklist

- **Setup & Run:** Steps 1–7 and 6b; every job and pipeline has a **Run** and **Open** (or equivalent) one-click action. Quick links: Jobs, Pipelines, SQL Warehouse, Explore schema, Genie, Stream processor, Test Agent Framework (if configured), All jobs.
- **Dashboards:** 11 dashboards; list from `GET /api/dashboards`; click card opens dashboard in workspace.
- **AI Agents:** Genie + agent list; Open Genie, Open agents folder.
- **ML Models:** Four models; list from backend; cards open Model Registry or MLflow.
- **Other UI:** Dashboard home, Decisioning, Rules, Notebooks, Declines, Reason codes, Smart checkout, Smart retry; each links to relevant workspace resource or API. Incidents → Real-Time Monitoring; Experiments → MLflow. Profile stays app-only.
- **Verify:** `GET /api/setup/defaults`, `GET /api/dashboards`, `GET /api/analytics/models`, `GET /api/agents/agents`, `GET /api/rules`. Frontend: set `VITE_DATABRICKS_HOST` for Open-in-Databricks links.

---

**See also:** [0_BUSINESS_CHALLENGES](0_BUSINESS_CHALLENGES.md) · [1_DEPLOYMENTS](1_DEPLOYMENTS.md) · [2_DATA_FLOW](2_DATA_FLOW.md) · [3_AGENTS_VALUE](3_AGENTS_VALUE.md) · [5_DEMO_SETUP](5_DEMO_SETUP.md)
