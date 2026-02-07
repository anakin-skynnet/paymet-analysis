# Technical Reference

**Payment Analysis** — architecture, bundle resources, data flow, and deployment reference.

## Architecture

- **Databricks:** Simulator → **Lakeflow** (Bronze → Silver → Gold) → Unity Catalog (12+ views, 4 models). MLflow, Model Serving, Mosaic AI Gateway, Genie. 12 AI/BI dashboards, SQL Warehouse.
- **App:** FastAPI (analytics, decisioning, notebooks, dashboards, agents) ↔ React (dashboard, dashboards, notebooks, models, ai-agents, decisioning, experiments, declines).

## Data flow

Transaction to insight in five stages: **Ingestion** (1,000/s → Delta) → **Processing** (Bronze → Silver → Gold, <5s) → **Intelligence** (ML + 7 AI agents) → **Analytics** (12 dashboards, Genie) → **Application** (FastAPI + React). Medallion: Bronze `payments_raw_bronze`, Silver `payments_enriched_silver`, Gold 12+ views (`v_executive_kpis`, `v_approval_trends_hourly`, etc.). See [Bundle & Deploy](#bundle--deploy) and [DEPLOYMENT](DEPLOYMENT.md).

## Data Layer

Bronze: raw + `_ingested_at`. Silver: quality, `risk_tier`, `amount_bucket`, `composite_risk_score`. Gold: 12+ views. UC: `ahs_demos_catalog.ahs_demo_payment_analysis_dev` (default) — governance, lineage, audit.

**Lakehouse bootstrap:** Run `lakehouse_bootstrap.sql` once (same catalog/schema as gold views). It creates: `app_config` (catalog/schema for the app); `transaction_summaries_for_search` and `approval_recommendations` (Vector Search source + recommendations view); `approval_rules` and `v_approval_rules_active`; `online_features` and `v_online_features_latest`. Decisioning uses `GET /api/analytics/recommendations`; Rules page: CRUD via `/api/rules`; Dashboard: online features via `/api/analytics/online-features`. Vector Search index: create from `resources/vector_search.yml` manually after the bootstrap.

**Catalog and schema (app_config):** Effective catalog/schema is stored in table `app_config` (created by lakehouse_bootstrap.sql). Bootstrap from `DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA`. UI can update via **Setup & Run** → **Save catalog & schema** (`PATCH /api/setup/config`).

## Catalog and schema verification

Catalog and schema are driven by: **Bundle** — `databricks.yml` variables `var.catalog`, `var.schema` (defaults + prod overrides). **Jobs/pipelines** use `${var.catalog}`, `${var.schema}`. **Backend** — `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA` env and `app_config` table; agents and analytics use effective UC from app state. **Dashboards** — template string in JSONs is replaced by `scripts/dashboards.py prepare` with target catalog.schema. **Notebooks** — receive catalog/schema via job `base_parameters`. No hardcoded catalog/schema in code paths that should be parameterized.

## Data flow verification (ingestion → app)

**Ingestion:** Simulator writes to `payments_stream_input`; bronze ingest reads it; pipeline uses bundle catalog/schema. Silver and gold (DLT + SQL job) align. **Analytics:** Gold SQL views (`gold_views.sql`) include `approved_count` where backend/UI expect it. **AI:** ML training and agents use job params (bundle vars); agent URLs use effective UC from app_config. **App:** Backend bootstrap and `DatabricksService` use app_config or env. Setup job/pipeline IDs are overridable via env (see [DEPLOYMENT](DEPLOYMENT.md)); dashboard embed URL uses `DATABRICKS_WORKSPACE_ID` when set.

## ML Layer

Models: approval propensity (RF ~92%), risk (~88%), routing (RF ~75%), retry (~81%). MLflow → UC Registry → Serving (<50ms p95, scale-to-zero). Lifecycle: experiment → register → serve → monitor → retrain.

## AI Agents (Summary)

Genie 2, Model serving 3, Mosaic AI Gateway (LLM) 2. Agent jobs: [agents.yml](../resources/agents.yml). Details: [OVERVIEW](OVERVIEW.md#accelerating-with-agent-bricks--mosaic-ai).

## Analytics

12 dashboards in `resources/dashboards.yml`; deployed from `.build/dashboards/*.lvdash.json` (from `scripts/dashboards.py prepare`). **Create Gold Views** job runs `.build/transform/gold_views.sql` with `USE CATALOG`/`USE SCHEMA`. Validate assets: `uv run python scripts/dashboards.py validate-assets`.

## Application Layer

**Backend:** `/api/analytics`, `/api/decision`, `/api/notebooks`, `/api/dashboards`, `/api/agents`, `/api/rules`, `/api/setup`. UC via Databricks SQL. **Frontend:** React + TanStack Router; `lib/api.ts`. **Stack:** Delta, UC, Lakeflow, SQL Warehouse, MLflow, Serving, Dashboards, Genie, Mosaic AI Gateway, FastAPI, React, TypeScript, Bun, TailwindCSS, Databricks Asset Bundles.

## Resources built by the bundle

| Category | Resources |
|----------|-----------|
| **UC** | Schema + 4 volumes (raw_data, checkpoints, ml_artifacts, reports) |
| **Lakebase** | Instance + UC catalog (rules, experiments, incidents) |
| **SQL warehouse** | Payment Analysis Warehouse (PRO, serverless) |
| **Pipelines** | Payment Analysis ETL, Payment Real-Time Stream |
| **Jobs** | 3 ML (train, gold views, test agent) + 6 agents + 2 streaming + 1 Genie sync = **12** |
| **Dashboards** | **12** (executive_overview, decline_analysis, realtime_monitoring, fraud_risk_analysis, merchant_performance, routing_optimization, daily_trends, authentication_security, financial_impact, performance_latency, streaming_data_quality, global_coverage) |
| **App** | payment-analysis (FastAPI + React) |
| **Optional** | model_serving.yml (4 endpoints); Vector Search (create manually from `resources/vector_search.yml`) |

**App API:** `/api/dashboards`, `/api/agents`, `/api/setup`, `/api/rules`, `/api/experiments`, `/api/incidents`, `/api/decision`, `/api/analytics`, `/api/notebooks`.

## Verification (test, validate, verify)

```bash
./scripts/bundle.sh verify [dev|prod]
```

Runs: build, backend import smoke test, dashboard validate-assets, bundle validate. Individual steps: `uv run apx build`, `uv run python scripts/dashboards.py validate-assets`, `./scripts/bundle.sh validate dev`.

## Lakebase (managed Postgres)

[Lakebase](https://www.databricks.com/product/lakebase): managed Postgres for rules, experiments, incidents. Bundle: `resources/lakebase.yml` — instance `payment_analysis_db`, UC catalog. Set app env **PGAPPNAME** to instance name (dev: `payment-analysis-db-dev`).

## Databricks App compliance checklist

| Requirement | Status | Notes |
|-------------|--------|--------|
| **Runtime spec at project root** | OK | `app.yaml` (block-sequence `command` + `env`; add `app.yml` copy if runtime expects it) |
| **Command** | OK | `uvicorn app:app --host 0.0.0.0 --workers 1` (no shell; container binding) |
| **API prefix `/api`** | OK | Required for OAuth2 Bearer; router uses `prefix="/api"` |
| **requirements.txt** | OK | Only non–pre-installed (pydantic-settings, sqlmodel, psycopg); no fastapi/uvicorn; psycopg without `[binary]` |
| **No system packages / Conda** | OK | Pure Python deps only |
| **Auth** | OK | `X-Forwarded-Access-Token` for workspace client; platform injects when bound |
| **Config from env** | OK | `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN` from bound resources; `PGAPPNAME` in app.yaml env |
| **Database** | OK | Lakebase via `PGAPPNAME`; no localhost in production (only when `APX_DEV_DB_PORT` set) |
| **Bundle app resource** | OK | `resources/app.yml`: source_code_path, database, sql_warehouse, jobs bound |
| **Node/frontend** | OK | `package.json` engines `>=22.0.0`; TanStack 1.158.1 overrides; `apx build` before deploy populates `__dist__` |

## Databricks App (deploy)

**Pre-installed:** databricks-sql-connector, databricks-sdk, fastapi, uvicorn, etc. — do not add to requirements.txt. See [system env](https://docs.databricks.com/en/dev-tools/databricks-apps/system-env). **requirements.txt:** only `pydantic-settings`, `sqlmodel`, `psycopg` (pure Python, no `[binary]`). **Compatibility:** Python 3.11, Node 22.16, Ubuntu 22.04; no apt-get/Conda. TanStack **1.158.1** with overrides; use `bun.lock`. See [DEPLOYMENT](DEPLOYMENT.md) troubleshooting.

## Bundle & Deploy

**Included by default:** unity_catalog, lakebase, pipelines, sql_warehouse, ml_jobs, agents, streaming_simulator, genie_spaces, dashboards, app. **AI Gateway:** Configured on each model serving endpoint in `resources/model_serving.yml` (rate limits, usage tracking, guardrails; see [Configure AI Gateway on model serving endpoints](https://learn.microsoft.com/en-us/azure/databricks/ai-gateway/configure-ai-gateway-endpoints)). **Optional (commented):** model_serving.yml (uncomment after Step 6 Train ML Models). **Not in bundle:** Vector Search — create from `resources/vector_search.yml` manually.

**Variables:** `catalog`, `schema`, `environment`, `warehouse_id`, `lakebase_*`, `workspace_folder`. Commands: `./scripts/bundle.sh deploy dev` (or validate then `databricks bundle deploy -t dev`). App env: DATABRICKS_HOST, WAREHOUSE_ID, TOKEN; PGAPPNAME for Lakebase; optional DATABRICKS_WORKSPACE_ID for dashboard embed.

## Workspace components ↔ UI mapping

| Component | UI location | One-click |
|-----------|-------------|-----------|
| Transaction Stream Simulator | Setup & Run step 1 | Run simulator / Open job |
| Payment Analysis ETL | Setup & Run step 2 | Start ETL / Open pipeline |
| Create Gold Views | Setup & Run step 3 | Run job / Open job |
| Train ML Models | Setup & Run step 5 | Run ML training / Open job |
| Orchestrator + 5 specialist agents | Setup & Run step 6 / 6b | Run / Open each job |
| Continuous Stream Processor, Test Agent | Setup & Run Quick links | Run / Open |
| 12 Dashboards | Dashboards page | Card opens in workspace |
| Rules, Experiments, Incidents | Rules, Experiments, Incidents | CRUD via API (Lakebase) |
| AI Agents, Genie, ML Models | AI Agents, ML Models, Decisioning | List + open workspace links |

Job/pipeline IDs from `GET /api/setup/defaults` (env overrides: see [DEPLOYMENT](DEPLOYMENT.md)). Catalog/schema from app_config or env.

---

**See also:** [OVERVIEW](OVERVIEW.md) · [DEPLOYMENT](DEPLOYMENT.md)
