# Data Flow and Intelligence — Detailed Description

This document describes **all data flow** in the Payment Analysis solution, the **intelligence applied at each step**, and **how each Databricks resource is used**. For architecture overview see [Technical Solution](TECHNICAL_SOLUTION.md); for deployment see [Reference Guide](REFERENCE_GUIDE.md).

---

## 1. End-to-end flow (summary)

```
[Data sources] → [Ingestion] → [Medallion processing] → [Intelligence layer] → [Application]
                     │                    │                        │                    │
              Job 2 / Kafka         Lakeflow pipelines      ML + VS + Rules      FastAPI + React
              payments_stream_input   Bronze→Silver→Gold     + Agents             + Dashboards
                     │                    │                        │                    │
              Delta + CDF             Unity Catalog            Model Serving        Lakeview embed
                                     + Vector Search           + Lakebase          + Genie
```

- **Data sources:** Transaction simulator (Job 2) or, in production, Kafka/Event Hubs/Auto Loader.
- **Ingestion:** Events land in a Delta table with Change Data Feed (CDF).
- **Medallion:** Two Lakeflow pipelines (ETL + Real-Time) build Bronze → Silver → Gold in Unity Catalog; real-time metrics and behavioral features are computed in stream.
- **Intelligence:** ML models (4 endpoints), Vector Search (similar transactions), configurable rules and config from Lakebase, streaming features, and AI agents (ResponsesAgent + Genie) that read/write recommendations and propose config.
- **Application:** FastAPI backend serves analytics, decisioning, dashboards, agents, and rules; React UI and embedded Lakeview dashboards consume it; Genie provides natural-language data queries.

---

## 2. Step-by-step data flow and Databricks resources

### Phase A: Bootstrap and data repositories (one-time / occasional)

| Step | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Job 1 – ensure_catalog_schema** | Creates Unity Catalog catalog and schema if they do not exist. | None. | **Unity Catalog** (CREATE CATALOG / CREATE SCHEMA). |
| **Job 1 – create_lakebase_autoscaling** | Creates Lakebase Autoscaling project, branch, and read-write endpoint (Postgres). | None. | **Lakebase (Postgres)** — Databricks managed Postgres; SDK `postgres.create_*` APIs. |
| **Job 1 – lakebase_data_init** | Connects to Lakebase and seeds tables: `app_config`, `approval_rules`, `online_features`, `app_settings`, and related schema. | None. | **Lakebase** — INSERT into Postgres tables; app later reads/writes rules, config, experiments, incidents, recommendations. |
| **Job 1 – lakehouse_bootstrap** | Runs `lakehouse_bootstrap.sql`: creates/ seeds base tables and views in Unity Catalog (e.g. `approval_recommendations`, `approval_rules`, `countries`, `incidents_lakehouse`, `app_config` in Lakehouse when used as fallback). | None. | **Unity Catalog** (tables/views in catalog.schema); **SQL Warehouse** (Statement Execution API to run bootstrap SQL). |
| **Job 1 – create_vector_search_index** | Creates Vector Search endpoint and a **delta-sync index** on table `transaction_summaries_for_search` (embedding model e.g. `databricks-bge-large-en`). Index is kept in sync with Delta. | None (index creation only). | **Vector Search** (endpoint + delta-sync index); **Unity Catalog** (source table); pipeline_type CONTINUOUS for sync. |

**Resources in this phase:** Unity Catalog, Lakebase (Postgres), SQL Warehouse (for bootstrap SQL), Vector Search (endpoint + index). Jobs run on **Databricks Jobs** (serverless or classic).

---

### Phase B: Event generation and ingestion

| Step | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Job 2 – transaction_simulator** | Generates synthetic payment events (e.g. 1000/sec) and **appends** them to Delta table `payments_stream_input`. Table has CDF enabled. | None (synthetic data generation only). | **Unity Catalog** (Delta table `payments_stream_input` in catalog.schema); **Databricks Jobs** (run simulator notebook). |
| **Production alternative** | In production, events would come from Kafka, Event Hubs, or Auto Loader (cloudFiles) into the same or a similar Delta table with CDF. | N/A. | **External streaming** + Delta with CDF. |

**Resources:** Unity Catalog (Delta table), Jobs.

---

### Phase C: Medallion processing (Bronze → Silver → Gold)

Two **Lakeflow** pipelines run continuously (or are started by the user). Both consume from `payments_stream_input` (or equivalent) and write into the same catalog.schema.

#### Pipeline 8 — Payment Analysis ETL (main medallion)

| Step | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Bronze – payments_raw_bronze** | `readStream` from `payments_stream_input` with **readChangeFeed: true**; filter insert/update_postimage; drop CDF columns; add `_ingested_at`. DLT expectations drop invalid rows (e.g. null transaction_id, amount ≤ 0). | **Data quality:** DLT expect_all_or_drop. | **Lakeflow** (DLT pipeline); **Unity Catalog** (source Delta table, target Bronze table); **Photon** (serverless). |
| **Bronze – merchants_dim_bronze** | Static dimension: 100 merchants, 8 segments (Travel, Retail, Gaming, etc.). No stream. | None. | **Lakeflow**; **Unity Catalog** (Bronze table). |
| **Silver – payments_enriched_silver** | Joins raw payments with merchants; adds canonical keys, decline taxonomy, retry scenario, service path, and other derived columns. Core table for gold views and ML. | **Enrichment logic** (business rules for segments, reason codes, etc.). | **Lakeflow**; **Unity Catalog** (Silver table); **Delta** (optimize, autoCompact). |
| **Silver – other** | `merchant_visible_attempts_silver`, `reason_code_taxonomy_silver` (seed), `insight_feedback_silver`, `smart_checkout_decisions_silver`, `decision_log_silver` as defined in silver_transform. | Taxonomy and feedback semantics. | **Lakeflow**; **Unity Catalog**. |
| **Gold – DLT tables** | Lakeflow materializes gold DLT tables: e.g. `v_retry_performance`, `v_3ds_funnel_br`, `v_reason_codes_br`, `v_reason_code_insights_br`, `v_entry_system_distribution_br`, `v_dedup_collision_stats`, `v_false_insights_metric`, `v_smart_checkout_*`. | Aggregations and analytics. | **Lakeflow**; **Unity Catalog** (Gold tables). |

**Resources:** **Lakeflow** (single pipeline, continuous, serverless, Photon), **Unity Catalog** (catalog, schema, Delta tables).

#### Pipeline 9 — Real-time stream

| Step | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Bronze – payments_stream_bronze** | Same as ETL: readStream + CDF from `payments_stream_input`. | DLT expect_or_drop. | **Lakeflow**; **Unity Catalog**. |
| **Silver – payments_stream_silver** | Lightweight enrichment: event_date, event_hour, event_minute, risk_tier (from thresholds), amount_bucket, etc. | **Risk tier** from configurable thresholds (aligned with Lakebase decision config). | **Lakeflow**; **Unity Catalog**. |
| **Downstream** | 10-second windowed aggregations (counts, approval rate, latency, etc.) and optional alerts; behavioral features for online feature store. | **Streaming aggregations** and **behavioral features** (e.g. approval_rate_5m, txn_velocity_1m) for real-time decisions. | **Lakeflow**; **Unity Catalog** (e.g. `payments_realtime_metrics`, online feature table). |

**Resources:** **Lakeflow** (second pipeline, continuous), **Unity Catalog**.

---

### Phase D: Gold views and Vector Search sync (Job 3)

| Step | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Job 3 – run_gold_views** | Executes `gold_views.sql` to create **24 SQL views** (e.g. `v_executive_kpis`, `v_approval_trends_hourly`, `v_top_decline_reasons`, `v_retry_success_by_reason`, `v_performance_by_geography`, data quality views, etc.). Views read from `payments_enriched_silver` and other silver/gold objects. | **Analytical definitions** (KPIs, trends, reason codes, recovery opportunities, retry by reason). | **SQL Warehouse** (Statement Execution API); **Unity Catalog** (views in catalog.schema). **Databricks Jobs**. |
| **Job 3 – create_uc_agent_tools** | Creates **Unity Catalog functions** (17 individual + 5 consolidated) in catalog.schema. Functions query gold views, Lakebase (via connector or proxy), and Vector Search. | **Agent tool semantics** (what agents can read/write). | **Unity Catalog** (CREATE FUNCTION); **SQL Warehouse** (run DDL); **Lakebase** (read by UC functions); **Vector Search** (search_similar_transactions). |
| **Job 3 – sync_vector_search** | Ensures **Vector Search index** is populated/synced from `transaction_summaries_for_search` (fed from silver via MERGE or pipeline). | None (sync only). | **Vector Search** (delta-sync index); **Unity Catalog** (source table). **Databricks Jobs**. |

**Resources:** **SQL Warehouse**, **Unity Catalog** (views + functions), **Vector Search**, **Lakebase** (for UC functions that read rules/incidents/outcomes), **Jobs**.

---

### Phase E: ML training and model serving (Job 5)

| Step | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Job 5 – train_models** | Reads `payments_enriched_silver`; builds **14 engineered features** (temporal, merchant/solution approval rates, network encoding, log_amount, risk–amount interaction); trains **4 models** (HistGradientBoosting): approval propensity, risk scoring, smart routing policy, smart retry policy. Registers models in Unity Catalog. | **Supervised ML** — same feature builder used at training and inference for parity. | **Unity Catalog** (silver table, ML model registry in catalog.schema); **MLflow** (tracking, model registry); **Databricks Jobs** (serverless). |
| **Job 5 – deploy endpoints** | Creates or updates **4 Model Serving endpoints**: `approval-propensity`, `risk-scoring`, `smart-routing`, `smart-retry`. Each serves the latest model version from UC. | **Real-time inference** — low-latency scoring for decisions. | **Model Serving** (4 endpoints); **Unity Catalog** (entity_name/entity_version); **AI Gateway** (rate limits, usage tracking when configured). |

**Resources:** **Unity Catalog** (data + ML registry), **MLflow**, **Model Serving**, **Jobs**, optionally **AI Gateway**.

---

### Phase F: Agents (Job 6)

| Step | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Job 6 – run_agent_framework** | Validates/runs the **custom Python agent framework** (orchestrator + 5 specialists). Used as **Path 3** fallback when Model Serving and AI Gateway are unavailable. | **Multi-agent orchestration** + specialist tools (SQL, Lakebase write-back, config proposals). | **Databricks Jobs**; **Unity Catalog** (gold views, functions); **Lakebase** (rules, recommendations, config proposals); **Vector Search** (via UC function). |
| **Job 6 – register_responses_agent** | Registers the **ResponsesAgent** (MLflow, OpenAI Responses API) with **10 UC tools** + `python_exec` to `catalog.agents.payment_analysis_agent` and creates/updates **Model Serving** endpoint `payment-response-agent`. | **Single agent with 10 tools** (5 consolidated analytics + 5 operational, including Lakebase and Vector Search); **write-back** via python_exec to `approval_recommendations`. | **Model Serving** (payment-response-agent); **Unity Catalog** (agents schema, registered model); **MLflow**; **Unity Catalog functions** (tools); **Lakebase** (read/write via UC + python_exec); **Vector Search** (search_similar_transactions). **AI Gateway** (optional fallback LLM). |

**Resources:** **Model Serving** (agent endpoint), **Unity Catalog** (agents schema, UC functions), **Lakebase**, **Vector Search**, **Jobs**, **AI Gateway** (fallback).

---

### Phase G: Dashboards and Genie (Jobs 4 and 7)

| Step | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Job 4 – prepare + publish** | Prepares dashboard JSON from templates (catalog/schema substitution); **publishes** 3 unified Lakeview dashboards (Data & Quality, ML & Optimization, Executive & Trends) with **embed credentials**. | **BI semantics** (widgets, datasets, filters). | **Lakeview / DBSQL** (dashboards); **SQL Warehouse** (dashboard queries); **Unity Catalog** (datasets = gold views/tables). **Databricks Jobs**; **Workspace** (dashboard definitions). |
| **Job 7 – Genie sync** | Syncs **Genie space** configuration and sample questions so users can ask natural-language questions over the lakehouse. | **Genie** (natural-language to SQL, semantic layer). | **Genie** (space, conversation API); **Unity Catalog** (tables/views); **SQL Warehouse** (executed queries). **Databricks Jobs**. |

**Resources:** **Lakeview** (dashboards), **SQL Warehouse**, **Unity Catalog**, **Genie**, **Jobs**.

---

### Phase H: Application runtime (FastAPI app)

The Databricks **App** runs the FastAPI backend (and serves the React frontend). Every API call that needs data or intelligence uses one or more Databricks resources.

| Flow | What happens | Intelligence | Databricks resources used |
|------|----------------|--------------|----------------------------|
| **Analytics APIs** (e.g. `/api/analytics/kpis`, trends, reason codes, declines, Smart Checkout, Smart Retry, recommendations, online features, countries) | Backend calls **DatabricksService** to run SQL against gold views and tables. Can fall back to Lakebase or mock when UC/SQL unavailable. | **Predefined analytics** (views define the metrics). | **SQL Warehouse** (Statement Execution API); **Unity Catalog** (gold views, silver/gold tables). Optionally **Lakebase** (online_features, countries). |
| **Decision APIs** (`/api/decision/authentication`, `/retry`, `/routing`, `/config`, `/outcome`) | **DecisionEngine** loads **config and rules from Lakebase** (cached); optionally enriches context with **Model Serving** (4 ML endpoints) and **Vector Search** (similar transactions) in parallel; evaluates rules; returns decision. **POST /outcome** writes outcome back to Lakebase. **GET /config** returns current thresholds. | **ML scores** (approval, risk, routing, retry); **Vector Search** (similar-case approval rates); **streaming features** (e.g. from Lakebase/online store); **rule engine** (conditions + actions); **policy functions** (combine scores + rules). | **Lakebase** (decision_config, approval_rules, retryable_decline_codes, route_performance, recommendations, outcome table); **Model Serving** (4 endpoints); **Vector Search** (via backend or UC); **SQL Warehouse** (if streaming features from Lakehouse). |
| **Rules CRUD** (`/api/rules`) | Read/write **approval_rules**; **dual-write** to Lakebase and Lakehouse so agents and UI see the same rules. | None (persistence only). | **Lakebase** (primary); **Unity Catalog** / **SQL Warehouse** (dual-write). |
| **Dashboards** (`/api/dashboards/*`) | List dashboards; resolve **embed URL** for Lakeview; optionally **fetch dashboard definition** via Lakeview API (workspace). | None. | **Workspace** (Lakeview API); **SQL Warehouse** (embed queries). |
| **Agents – orchestrator chat** (`POST /api/agents/orchestrator/chat`) | **Path 1:** Call **payment-response-agent** (Model Serving). **Path 2:** AI Gateway (e.g. Claude Opus 4.6). **Path 3:** Trigger **Job 6** agent framework. Agent uses **UC tools** (gold views, Lakebase, Vector Search) and **python_exec** (recommendation write-back). | **LLM + tools** (ResponsesAgent or fallback); **recommendations** and **config proposals** written to Lakebase. | **Model Serving** (payment-response-agent); **Unity Catalog** (UC functions); **Lakebase** (rules, incidents, outcomes, recommendations, config proposals); **Vector Search** (similar_transactions); **AI Gateway** (fallback); **Jobs** (Path 3). |
| **Agents – Genie chat** (`POST /api/agents/chat`) | Forwards to **Genie Conversation API** with user message and space ID. | **Genie** (natural-language → SQL). | **Genie** (Conversation API); **Unity Catalog**; **SQL Warehouse**. |
| **Setup & Run** (jobs, pipelines, config) | **Run job** / **Run pipeline** via Workspace APIs; **catalog/schema** and settings from Lakebase or env. | None. | **Databricks Jobs API**; **Pipelines API**; **Lakebase** (app_config, app_settings). |
| **Experiments / Incidents** | CRUD for experiments and incidents stored in **Lakebase**. | None. | **Lakebase**. |

**Resources:** **SQL Warehouse**, **Unity Catalog**, **Model Serving**, **Vector Search**, **Lakebase**, **Genie**, **Workspace** (Lakeview), **Jobs API**, **AI Gateway**.

---

## 3. Intelligence summary by component

| Component | Type of intelligence | Where it runs | Databricks resources |
|-----------|----------------------|---------------|-----------------------|
| **Medallion (Bronze/Silver/Gold)** | DQ (expectations), enrichment, aggregations | Lakeflow | Lakeflow, Unity Catalog |
| **Gold views** | Analytical definitions (KPIs, trends, reason codes, retry by reason) | SQL | SQL Warehouse, Unity Catalog |
| **Vector Search** | Similar-transaction lookup (embedding + nearest-neighbor) | Vector Search service | Vector Search, Unity Catalog |
| **4 ML models** | Approval propensity, risk score, routing policy, retry policy | Model Serving | Model Serving, Unity Catalog (registry), MLflow |
| **DecisionEngine** | Combines ML + VS + rules + config + streaming features; policy logic | FastAPI app | Model Serving, Vector Search, Lakebase, SQL Warehouse |
| **Rules engine** | Conditional rules (approve/decline/retry/routing) from Lakebase | FastAPI app | Lakebase |
| **ResponsesAgent** | LLM + 10 UC tools + write-back (recommendations, config proposals) | Model Serving (or Job 6 / AI Gateway fallback) | Model Serving, UC functions, Lakebase, Vector Search, AI Gateway |
| **Genie** | Natural-language → SQL over lakehouse | Genie service | Genie, SQL Warehouse, Unity Catalog |
| **Streaming features** | Real-time behavioral features (e.g. approval_rate_5m) | Lakeflow + optional online store | Lakeflow, Unity Catalog, Lakebase |

---

## 4. Databricks resources — usage matrix

| Resource | Used in phase(s) | Purpose |
|----------|-------------------|---------|
| **Unity Catalog** | A, B, C, D, E, F, G, H | Catalog, schema, Delta tables (Bronze/Silver/Gold), views, ML models, UC functions, volumes. |
| **Lakeflow** | C | Two pipelines: ETL (Bronze→Silver→Gold) and Real-Time (stream + metrics + behavioral features). |
| **SQL Warehouse** | A, D, G, H | Bootstrap SQL, gold view DDL, dashboard queries, analytics API, Genie-executed SQL. |
| **Lakebase (Postgres)** | A, D, F, H | app_config, approval_rules, app_settings, online_features, experiments, incidents, decision_config, retryable_decline_codes, route_performance, approval_recommendations, outcome table, config_proposals. |
| **Vector Search** | A, D, F, H | Delta-sync index on transaction summaries; similar-transaction lookup for DecisionEngine and agents. |
| **Model Serving** | E, F, H | 4 ML endpoints (approval, risk, routing, retry) + 1 agent endpoint (payment-response-agent). |
| **MLflow** | E, F | Model tracking and registry; agent model registration. |
| **Databricks Jobs** | A–G | Job 1 (repositories), Job 2 (simulator), Job 3 (gold + UC tools + VS sync), Job 4 (dashboards), Job 5 (ML), Job 6 (agents), Job 7 (Genie); validate_all. |
| **Lakeview / DBSQL** | G, H | 3 unified dashboards; embed in app; queries use SQL Warehouse + UC. |
| **Genie** | G, H | Genie space; natural-language data queries (Genie Assistant in app). |
| **AI Gateway** | F, H | Optional fallback LLM for orchestrator chat; rate limits for ML endpoints. |
| **Workspace** | G, H | Dashboard definitions (Lakeview API); app code path. |

---

## 5. Data flow diagram (simplified)

```
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                     DATA SOURCES                                  │
                    │  Job 2 (simulator) → payments_stream_input (Delta + CDF)         │
                    │  Prod: Kafka / Event Hubs / Auto Loader → same or similar table  │
                    └─────────────────────────────────────────────────────────────────┘
                                                │
                    ┌───────────────────────────▼───────────────────────────┐
                    │              LAKEFLOW (Pipeline 8 + 9)                  │
                    │  Bronze → Silver → Gold (ETL)                          │
                    │  Real-time: stream silver + 10s metrics + features    │
                    │  Resources: Unity Catalog (Delta), Photon             │
                    └───────────────────────────┬───────────────────────────┘
                                                │
        ┌───────────────────────────────────────┼───────────────────────────────────────┐
        │                                       │                                       │
        ▼                                       ▼                                       ▼
┌───────────────┐                   ┌───────────────────┐                   ┌──────────────────┐
│ Job 3         │                   │ Job 1 / ongoing    │                   │ Job 5            │
│ Gold views    │                   │ Vector Search sync │                   │ Train ML models  │
│ UC functions  │                   │ (transaction       │                   │ Deploy 4         │
│               │                   │  summaries)        │                   │ endpoints        │
│ SQL Warehouse │                   │ Vector Search      │                   │ Model Serving     │
│ Unity Catalog │                   │ Unity Catalog      │                   │ MLflow / UC      │
└───────┬───────┘                   └─────────┬─────────┘                   └────────┬─────────┘
        │                                     │                                       │
        │     ┌───────────────────────────────┼───────────────────────────────────────┘
        │     │                               │
        ▼     ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                        INTELLIGENCE LAYER                                                    │
│  Lakebase: config, rules, codes, routes, recommendations, outcomes, experiments, incidents │
│  Model Serving: 4 ML endpoints + payment-response-agent (ResponsesAgent)                    │
│  Vector Search: similar_transactions_index                                                  │
│  UC functions: 17+5 for agents (gold views, Lakebase, Vector Search)                       │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  FASTAPI APP (Databricks App)                                                                │
│  Analytics → SQL Warehouse + UC  │  Decision → Lakebase + ML + VS + rules                   │
│  Rules CRUD → Lakebase (+ dual-write)  │  Dashboards → Lakeview embed  │  Agents → MS + Genie │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  REACT UI + Lakeview embed + Genie Assistant                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

This document is the single reference for **data flow**, **intelligence at each step**, and **Databricks resource usage** across the solution.
