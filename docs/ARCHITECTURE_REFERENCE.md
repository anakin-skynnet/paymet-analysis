# Architecture & Reference

Payment Analysis — architecture, data flow, bundle resources, and technical reference.

## Architecture

- **Databricks:** Simulator → Lakeflow (Bronze → Silver → Gold) → Unity Catalog (12+ views, 4 models). MLflow, Model Serving, Genie. 12 dashboards, SQL Warehouse.
- **App:** FastAPI (analytics, decisioning, dashboards, agents) ↔ React (dashboard, models, decisioning, experiments, declines).

## Data flow

**Ingestion** (1,000/s → Delta) → **Processing** (Bronze → Silver → Gold, <5s) → **Intelligence** (ML + 7 AI agents) → **Analytics** (12 dashboards, Genie) → **Application** (FastAPI + React). Medallion: Bronze `payments_raw_bronze`, Silver `payments_enriched_silver`, Gold 12+ views. See [Deployment guide](DEPLOYMENT_GUIDE.md) and [Bundle & deploy](#bundle--deploy).

## Data layer

Bronze: raw + `_ingested_at`. Silver: quality, risk_tier, amount_bucket, composite_risk_score. Gold: 12+ views. UC default: `ahs_demos_catalog.ahs_demo_payment_analysis_dev`.

**Lakehouse bootstrap:** Run `lakehouse_bootstrap.sql` once (same catalog/schema as gold views). Creates: `app_config`, `transaction_summaries_for_search`, `approval_recommendations`, `approval_rules`, `online_features` and views. Enables Rules, Decisioning, Dashboard. Vector Search: create from `resources/vector_search.yml` after bootstrap.

**Catalog and schema (app_config):** Effective catalog/schema in `app_config`. Bootstrap from `DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA`. UI: **Setup & Run** → **Save catalog & schema** (`PATCH /api/setup/config`).

## Catalog and schema verification

**Bundle:** `var.catalog`, `var.schema`. **Backend:** env + `app_config`. **Dashboards:** catalog.schema from `scripts/dashboards.py prepare`. **Notebooks:** job `base_parameters`. No hardcoded catalog/schema in parameterized paths.

## ML layer

Models: approval propensity (RF ~92%), risk (~88%), routing (~75%), retry (~81%). MLflow → UC Registry → Serving. Lifecycle: experiment → register → serve → retrain.

## AI agents

Genie 2, Model serving 3, Mosaic AI Gateway 2. Jobs: `resources/agents.yml`.

## Analytics

12 dashboards in `resources/dashboards.yml`; deployed from `.build/dashboards/` (from `scripts/dashboards.py prepare`). Gold Views job runs `.build/transform/gold_views.sql`. Validate: `uv run python scripts/dashboards.py validate-assets`.

## Application layer

**Backend:** `/api/analytics`, `/api/decision`, `/api/notebooks`, `/api/dashboards`, `/api/agents`, `/api/rules`, `/api/setup`. **Frontend:** React, TanStack Router, `lib/api.ts`. **Stack:** Delta, UC, Lakeflow, SQL Warehouse, MLflow, FastAPI, React, TypeScript, Bun, TailwindCSS, Databricks Asset Bundles.

## Resources built by the bundle

| Category | Resources |
|----------|-----------|
| UC | Schema + 4 volumes (raw_data, checkpoints, ml_artifacts, reports) |
| Lakebase | Instance + UC catalog (rules, experiments, incidents) |
| SQL warehouse | Payment Analysis Warehouse |
| Pipelines | ETL, Real-Time Stream |
| Jobs | 12 (ML, gold views, agents, streaming, Genie sync) |
| Dashboards | 12 |
| App | payment-analysis (FastAPI + React) |
| Optional | model_serving.yml (4 endpoints); Vector Search from `resources/vector_search.yml` |

**App API:** `/api/dashboards`, `/api/agents`, `/api/setup`, `/api/rules`, `/api/experiments`, `/api/incidents`, `/api/decision`, `/api/analytics`, `/api/notebooks`.

## Verification

```bash
./scripts/bundle.sh verify [dev|prod]
```

Runs: build, backend smoke test, dashboard validate-assets, bundle validate.

## Lakebase

Managed Postgres for rules, experiments, incidents. Bundle: `resources/lakebase.yml`. Set app env **PGAPPNAME** to instance name (dev: `payment-analysis-db-dev`).

## Databricks App compliance checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| Runtime spec at root | OK | `app.yaml` and `app.yml` (same content) |
| Command | OK | `uvicorn payment_analysis.backend.app:app` |
| API prefix `/api` | OK | Router `prefix="/api"` |
| requirements.txt | OK | Exact versions from pyproject.toml/uv.lock (fastapi, uvicorn, pydantic, sqlmodel, psycopg[binary], etc.) |
| No system packages | OK | Pure Python deps |
| Config from env | OK | DATABRICKS_*, PGAPPNAME |
| Bundle app resource | OK | `resources/fastapi_app.yml` |
| Node/frontend | OK | engines `>=22.0.0`; TanStack 1.158.1 overrides |

## Databricks App (deploy)

**Pre-installed (Databricks Apps):** databricks-sdk 0.33.0, fastapi 0.115.0, uvicorn 0.30.6, etc. **requirements.txt:** Generated from `uv.lock` by `scripts/sync_requirements_from_lock.py`; same versions everywhere (pyproject.toml → uv lock → requirements.txt). psycopg[binary] for DB (no system libpq in container). **Compatibility:** Python 3.11, Node 22.16, Ubuntu 22.04. Frontend: package.json and bun.lock with exact versions; TanStack **1.158.1**. See [Deployment guide](DEPLOYMENT_GUIDE.md#troubleshooting).

## Bundle & deploy

**Included:** unity_catalog, lakebase, pipelines, sql_warehouse, ml_jobs, agents, streaming_simulator, genie_spaces, dashboards, app. **Optional:** model_serving.yml (uncomment after Step 6). **Not in bundle:** Vector Search — create from `resources/vector_search.yml`. **Variables:** catalog, schema, environment, warehouse_id, lakebase_*, workspace_folder. Commands: [Deployment guide](DEPLOYMENT_GUIDE.md#quick-start).

## Workspace components ↔ UI mapping

| Component | UI location | One-click |
|-----------|-------------|-----------|
| Transaction Stream Simulator | Setup & Run step 1 | Run simulator |
| Payment Analysis ETL | Setup & Run step 2 | Start ETL |
| Create Gold Views | Setup & Run step 3 | Run job |
| Train ML Models | Setup & Run step 5 | Run ML training |
| Orchestrator + 5 agents | Setup & Run step 6/6b | Run / Open |
| 12 Dashboards | Dashboards page | Card opens in workspace |
| Rules, Experiments, Incidents | Rules, Experiments, Incidents | CRUD via API |

Job/pipeline IDs: `GET /api/setup/defaults`; env overrides: [Deployment guide](DEPLOYMENT_GUIDE.md).

---

**See also:** [Deployment guide](DEPLOYMENT_GUIDE.md)
