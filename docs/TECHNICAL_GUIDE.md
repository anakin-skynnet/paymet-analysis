# Technical Guideline

Single technical reference: architecture, project structure, deployment summary, version alignment, and best practices. For business purpose and impact on approval rates, see [Overview](OVERVIEW.md).

---

## Architecture

- **Platform:** Databricks — Lakeflow (Bronze → Silver → Gold), Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie. 12 dashboards.
- **App:** FastAPI (analytics, decisioning, dashboards, agents, rules, setup) + React (TanStack Router, shadcn/ui). API prefix `/api` for Databricks Apps token-based auth.
- **Stack:** Delta, Unity Catalog, Lakeflow, SQL Warehouse, Lakebase (Postgres for rules/experiments/incidents), MLflow, FastAPI, React, TypeScript, Vite, Bun, Databricks Asset Bundles.

## Data flow

**Ingestion** → **Processing** (Bronze → Silver → Gold, &lt;5s) → **Intelligence** (ML + 7 AI agents) → **Analytics** (12 dashboards, Genie) → **Application** (FastAPI + React).

Medallion: Bronze `payments_raw_bronze`, Silver `payments_enriched_silver`, Gold 12+ views. Lakehouse bootstrap creates `app_config`, rules, recommendations, and related views (see [Deployment guide](DEPLOYMENT_GUIDE.md)).

## Project structure (logical)

| Area | Path | Purpose |
|------|------|---------|
| Backend | `src/payment_analysis/backend/` | FastAPI app, config, dependencies, routes (analytics, decision, dashboards, agents, rules, setup, experiments, incidents, notebooks), services, Lakebase config |
| Frontend | `src/payment_analysis/ui/` | React app: routes, components (apx, layout, ui), lib (API client), config, hooks |
| Transform | `src/payment_analysis/transform/` | Lakehouse SQL, gold views, lakehouse bootstrap, prepare/publish dashboards |
| Streaming | `src/payment_analysis/streaming/` | Bronze ingest, real-time pipeline, transaction simulator |
| ML | `src/payment_analysis/ml/` | Model training (approval, risk, routing, retry) |
| Agents | `src/payment_analysis/agents/` | Orchestrator + specialist agents |
| Bundle | `resources/` | Unity Catalog, Lakebase, pipelines, sql_warehouse, ml_jobs, agents, dashboards, fastapi_app |
| Scripts | `scripts/` | bundle.sh (validate/deploy/verify), dashboards.py (prepare/validate-assets), sync_requirements_from_lock.py |

## Bundle resources

| Category | Resources |
|----------|-----------|
| UC | Schema + volumes (raw_data, checkpoints, ml_artifacts, reports) |
| Lakebase | Instance + UC catalog (rules, experiments, incidents) |
| SQL warehouse | Payment Analysis Warehouse |
| Pipelines | ETL, Real-Time Stream |
| Jobs | 6 steps (repositories, simulator, ingestion, dashboards, ML, agents) + Genie sync, etc. |
| Dashboards | 12 |
| App | payment-analysis (FastAPI + React) |
| Optional | model_serving.yml (after training); Vector Search from `resources/vector_search.yml` |

## Deployment (summary)

- **One command:** `./scripts/bundle.sh deploy dev` — runs prepare (dashboards, SQL), build (UI + wheel), then bundle deploy. Overwrites existing resources with `--force --auto-approve`.
- **App env (required):** `PGAPPNAME`, `DATABRICKS_WAREHOUSE_ID`. Optional: `DATABRICKS_HOST`, `DATABRICKS_TOKEN` (or open from **Compute → Apps** for user token).
- **Full steps, env vars, troubleshooting:** [Deployment guide](DEPLOYMENT_GUIDE.md).

## Version alignment (summary)

- **Python:** `pyproject.toml` (exact `==`) → `uv.lock` → `requirements.txt` via `scripts/sync_requirements_from_lock.py`. Do not change versions unless instructed.
- **Frontend:** `package.json` exact versions only (no `^`/`~`) → `bun.lock`. Run `uv run apx bun install` after changes.
- **Runtime:** Python 3.11, Node ≥22 (Databricks App: 22.16). See [VERSION_ALIGNMENT.md](VERSION_ALIGNMENT.md) for the full table.

## Best practices (summary)

- **API:** All routes use `response_model` and `operation_id` for OpenAPI client generation. API prefix `/api`. Health: `/api/v1/healthcheck`, `/api/v1/health/database`.
- **References:** [Apps Cookbook](https://apps-cookbook.dev/docs/intro), [apx](https://github.com/databricks-solutions/apx), [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit). Full compliance review: [BEST_PRACTICES_ALIGNMENT.md](BEST_PRACTICES_ALIGNMENT.md).

## Verification

```bash
uv run apx dev check          # TypeScript + Python
./scripts/bundle.sh verify dev # Build, smoke test, dashboards, bundle validate
```

## See also

| Doc | Purpose |
|-----|---------|
| [OVERVIEW.md](OVERVIEW.md) | Business purpose and impact on approval rates |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Deploy steps, env vars, troubleshooting |
| [ARCHITECTURE_REFERENCE.md](ARCHITECTURE_REFERENCE.md) | Data sources (UI ↔ backend), workspace ↔ UI mapping |
| [CONTROL_PANEL_UI.md](CONTROL_PANEL_UI.md) | Setup & Run, dashboards, Genie, agents in the UI |
| [VERSION_ALIGNMENT.md](VERSION_ALIGNMENT.md) | Pinned versions and Databricks App compatibility |
| [BEST_PRACTICES_ALIGNMENT.md](BEST_PRACTICES_ALIGNMENT.md) | Cookbook, apx, AI Dev Kit compliance |
