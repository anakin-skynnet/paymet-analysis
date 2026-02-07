# Resources Built in This Solution

Complete list of Databricks resources created by the Payment Analysis bundle, and which are used for **UI / end-user interaction** (showing results or user actions in the app or workspace).

---

## 1. Resources used via the UI (end-user interaction / showing results)

These are the resources that the app or workspace UI surfaces to users for viewing or interacting.

| Resource type | Resource key / name | Where it appears | Purpose |
|--------------|--------------------|------------------|---------|
| **App** | `payment_analysis_app` → name **payment-analysis** | Workspace → Apps | Main React + FastAPI UI: Dashboard, Dashboards, AI Agents, Setup & Run, Rules, Experiments, Incidents, Decisioning, ML Models, Notebooks, etc. |
| **Dashboards** (12) | `executive_overview`, `decline_analysis`, `realtime_monitoring`, `fraud_risk_analysis`, `merchant_performance`, `routing_optimization`, `daily_trends`, `authentication_security`, `financial_impact`, `performance_latency`, `streaming_data_quality`, `global_coverage` | App **Dashboard** / **Dashboards** pages; Workspace → SQL → Dashboards | AI/BI dashboards: KPIs, trends, decline analysis, real-time monitoring, fraud, routing, 3DS, financial impact, world map, etc. User opens a card → opens Databricks dashboard in a new tab. |
| **Lakebase (database)** | `payment_analysis_db` (instance), `payment_analysis_lakebase_catalog` (UC catalog) | App **Rules**, **Experiments**, **Incidents**; backend CRUD | Postgres-backed DB for rules, A/B experiments, incidents. App uses **PGAPPNAME**; bound to app as resource `database`. |
| **SQL warehouse** | `payment_analysis_warehouse` | App analytics, **Setup & Run** (gold views job), dashboards, app_config | Runs SQL for gold views, KPIs, trends, recommendations, catalog/schema. Bound to app as resource `sql-warehouse`. |
| **Genie** | Genie space (synced by `genie_sync_job`) | App **AI Agents** / **Setup & Run** → “Open Genie”; Workspace Genie UI | Natural language analytics over payment data. User opens Genie from app or workspace. |
| **Model serving** (optional) | `approval_propensity_endpoint`, `risk_scoring_endpoint`, `smart_routing_endpoint`, `smart_retry_endpoint` | App **Decisioning**, **ML Models** | Real-time inference for approval, risk, routing, retry. Used when model_serving.yml is included after ML training. |
| **Vector Search** (manual) | `payment_similar_transactions` (endpoint), `similar_transactions_index` | App **Recommendations** / analytics | Similar-transaction lookup. Not in bundle schema; create manually from `resources/vector_search.yml` if needed. |

**App API surface (what the UI calls):**

- **/api/dashboards** – list dashboards, get dashboard URL (open in workspace).
- **/api/agents** – list agents, open in Databricks / Genie.
- **/api/setup** – defaults (job/pipeline IDs, workspace_host), run job, run pipeline, save catalog/schema.
- **/api/rules** – CRUD approval rules (Lakebase).
- **/api/experiments** – CRUD and start/stop A/B experiments (Lakebase).
- **/api/incidents** – CRUD incidents (Lakebase).
- **/api/decision** – policy/retry/routing decisions (can call model serving).
- **/api/analytics** – KPIs, trends, recommendations, models, online features, etc. (SQL warehouse + optional model serving).
- **/api/notebooks** – list notebooks and open-in-workspace URLs.

---

## 2. All resources built by the bundle (full list)

### Unity Catalog (`resources/unity_catalog.yml`)

| Type | Key | Name / reference |
|------|-----|-------------------|
| Schema | `payment_analysis_schema` | `${var.schema}` in `${var.catalog}` |
| Volume | `raw_data_volume` | `raw_data` |
| Volume | `checkpoints_volume` | `checkpoints` |
| Volume | `ml_artifacts_volume` | `ml_artifacts` |
| Volume | `reports_volume` | `reports` |

### Lakebase (`resources/lakebase.yml`)

| Type | Key | Name / reference |
|------|-----|-------------------|
| Database instance | `payment_analysis_db` | `${var.lakebase_instance_name}` (e.g. payment-analysis-db-dev) |
| Database catalog | `payment_analysis_lakebase_catalog` | `${var.lakebase_uc_catalog_name}` → `${var.lakebase_database_name}` |

### SQL warehouse (`resources/sql_warehouse.yml`)

| Type | Key | Name |
|------|-----|------|
| SQL warehouse | `payment_analysis_warehouse` | [env] Payment Analysis Warehouse |

### Pipelines (`resources/pipelines.yml`)

| Type | Key | Name |
|------|-----|------|
| Pipeline | `payment_analysis_etl` | [env] Payment Analysis ETL |
| Pipeline | `payment_realtime_pipeline` | [env] Payment Real-Time Stream |

### Jobs – ML & analytics (`resources/ml_jobs.yml`)

| Type | Key | Name |
|------|-----|------|
| Job | `train_ml_models_job` | [env] Train Payment Approval ML Models |
| Job | `create_gold_views_job` | [env] Create Payment Analysis Gold Views |
| Job | `test_agent_framework_job` | [env] Test AI Agent Framework |

### Jobs – AI agents (`resources/agents.yml`)

| Type | Key | Name |
|------|-----|------|
| Job | `smart_routing_agent_job` | [env] Smart Routing Agent |
| Job | `smart_retry_agent_job` | [env] Smart Retry Agent |
| Job | `decline_analyst_agent_job` | [env] Decline Analyst Agent |
| Job | `risk_assessor_agent_job` | [env] Risk Assessor Agent |
| Job | `performance_recommender_agent_job` | [env] Performance Recommender Agent |
| Job | `orchestrator_agent_job` | [env] Payment Analysis Orchestrator |

### Jobs – streaming (`resources/streaming_simulator.yml`)

| Type | Key | Name |
|------|-----|------|
| Job | `transaction_stream_simulator` | [env] Transaction Stream Simulator |
| Job | `continuous_stream_processor` | [env] Continuous Stream Processor |

### Jobs – Genie (`resources/genie_spaces.yml`)

| Type | Key | Name |
|------|-----|------|
| Job | `genie_sync_job` | [env] Genie Space Sync |

### AI Gateway (`resources/ai_gateway.yml`)

| Type | Key | Notes |
|------|-----|--------|
| model_serving_endpoints | (empty map) | AI Gateway is configured on endpoints in model_serving.yml when that file is included. |

### Dashboards (`resources/dashboards.yml`)

| Type | Key | Display name (pattern) |
|------|-----|------------------------|
| Dashboard | `executive_overview` | [env] Executive Overview - Payment Analysis |
| Dashboard | `decline_analysis` | [env] Decline Analysis & Recovery |
| Dashboard | `realtime_monitoring` | [env] Real-Time Payment Monitoring |
| Dashboard | `fraud_risk_analysis` | [env] Fraud & Risk Analysis |
| Dashboard | `merchant_performance` | [env] Merchant Performance & Segmentation |
| Dashboard | `routing_optimization` | [env] Smart Routing & Optimization |
| Dashboard | `daily_trends` | [env] Daily Trends & Historical Analysis |
| Dashboard | `authentication_security` | [env] 3DS Authentication & Security Analysis |
| Dashboard | `financial_impact` | [env] Financial Impact & ROI Analysis |
| Dashboard | `performance_latency` | [env] Technical Performance & Latency Analysis |
| Dashboard | `streaming_data_quality` | [env] Streaming & Data Quality |
| Dashboard | `global_coverage` | [env] Global Coverage - World Map by Country |

### App (`resources/app.yml`)

| Type | Key | Name |
|------|-----|------|
| App | `payment_analysis_app` | **payment-analysis** |

### Model serving (`resources/model_serving.yml` – optional, commented in bundle)

| Type | Key | Name (pattern) |
|------|-----|----------------|
| Model serving endpoint | `approval_propensity_endpoint` | approval-propensity-[env] |
| Model serving endpoint | `risk_scoring_endpoint` | risk-scoring-[env] |
| Model serving endpoint | `smart_routing_endpoint` | smart-routing-[env] |
| Model serving endpoint | `smart_retry_endpoint` | smart-retry-[env] |

### Vector Search (`resources/vector_search.yml` – not in bundle schema; create manually)

| Type | Key | Name (pattern) |
|------|-----|----------------|
| Vector search endpoint | `payment_similar_transactions` | payment-similar-transactions-[env] |
| Vector search index | `similar_transactions_index` | [catalog].[schema].similar_transactions_index |

---

## 3. Summary counts (default deploy, without model_serving)

| Category | Count |
|----------|--------|
| Unity Catalog schema | 1 |
| UC volumes | 4 |
| Lakebase instance + catalog | 1 + 1 |
| SQL warehouses | 1 |
| Pipelines | 2 |
| Jobs | 3 (ML) + 6 (agents) + 2 (streaming) + 1 (Genie) = **12** |
| Dashboards | **12** |
| Apps | **1** (payment-analysis) |
| Model serving endpoints (optional) | 4 |
| Vector Search (manual) | 1 endpoint + 1 index |

**Resources meant for UI / end-user interaction:** App (1), Dashboards (12), Lakebase (DB + catalog), SQL warehouse, Genie (space synced by job), optional model serving (4), optional Vector Search (1 endpoint + 1 index).
