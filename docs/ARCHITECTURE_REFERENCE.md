# Architecture Reference

Technical reference for **data sources** (UI ↔ backend ↔ Databricks), **workspace ↔ UI mapping**, and **Databricks App compliance**. For business purpose and impact on approval rates, see [Overview](OVERVIEW.md). For architecture summary, project structure, and deployment, see [Technical guide](TECHNICAL_GUIDE.md).

---

## Workspace components ↔ UI mapping

Execution order in **Setup & Run** follows: foundation (Lakehouse, Vector Search, gold views, simulator), then optional streaming, ETL, ML, Genie, agents, dashboards.

| Component | Setup & Run step | One-click |
|-----------|------------------|-----------|
| Lakehouse Bootstrap | Step 1 | Run job (app_config, rules, recommendations) |
| Vector Search index | Step 1 (same job) | Run job (similar-transaction lookup) |
| Create Gold Views | Step 3 | Run job (`.build/transform/gold_views.sql`) |
| Transaction Stream Simulator | Step 2 | Run simulator |
| Pipelines (ETL, Real-Time) | — | Start pipeline from Setup & Run |
| Train ML Models | Step 5 | Run ML training |
| Genie Space Sync | Optional | Run Genie sync |
| Orchestrator + 5 agents | Step 6 | Run / Open |
| Publish Dashboards | Step 4 | Run job (embed credentials) |
| 12 Dashboards | Dashboards page | Card opens in workspace |
| Rules, Experiments, Incidents | Rules, Experiments, Incidents | CRUD via API |

Job/pipeline IDs: `GET /api/setup/defaults`; env overrides: [Deployment guide](DEPLOYMENT_GUIDE.md).

## Data sources (UI ↔ Backend ↔ Databricks)

All UI data goes through the FastAPI backend. No direct Lakebase or Databricks calls from the frontend.

| Area | Backend API | Source |
|------|-------------|--------|
| KPIs, trends, reason codes, declines, Smart Checkout, Smart Retry, recommendations, online features, models, countries | `GET /api/analytics/*` | Databricks (Unity Catalog, SQL Warehouse); fallback to app DB when unavailable |
| Rules | `GET/POST/PATCH/DELETE /api/rules` | Lakebase (if configured) or Lakehouse |
| Setup defaults, config, settings | `GET /api/setup/*`, `PATCH /api/setup/config` | Lakebase app_config/app_settings + workspace job/pipeline resolution |
| Dashboards list & embed URL | `GET /api/dashboards/*` | Static registry + workspace URL for embed |
| Agents list & URLs | `GET /api/agents/*` | Backend → WorkspaceClient |
| Experiments, incidents, decision logs | `GET/POST /api/experiments`, `/api/incidents` | Lakebase (Postgres) |

**Credentials:** When the app is opened from **Compute → Apps**, the platform forwards the user token (`X-Forwarded-Access-Token`). The backend uses it for Databricks; otherwise `DATABRICKS_TOKEN` from the app environment. Catalog/schema come from `app_config` (Lakebase or Lakehouse), loaded at startup or on first request.

## Databricks App compliance checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| Runtime spec at root | OK | `app.yml` |
| Command | OK | `uvicorn payment_analysis.backend.app:app` |
| API prefix `/api` | OK | Router `prefix="/api"` |
| requirements.txt | OK | Exact versions from pyproject.toml/uv.lock |
| No system packages | OK | Pure Python deps; psycopg[binary] for DB |
| Config from env | OK | DATABRICKS_*, PGAPPNAME |
| Bundle app resource | OK | `resources/fastapi_app.yml` |
| Node/frontend | OK | engines `>=22.0.0`; TanStack overrides |

## Catalog and schema

**Bundle:** `var.catalog`, `var.schema`. **Backend:** env + `app_config`. **Dashboards:** catalog.schema from `scripts/dashboards.py prepare`. **Notebooks:** job `base_parameters`. Effective catalog/schema from Lakehouse `app_config`; set via **Setup & Run** → **Save catalog & schema**.

## Alignment with Databricks patterns

- [Apps Cookbook](https://apps-cookbook.dev/docs/intro) — FastAPI, `/api`, healthcheck at `/api/v1/healthcheck`.
- [apx](https://github.com/databricks-solutions/apx) — Full-stack toolkit, OpenAPI client, `apx dev check` / `apx build`.
- [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit) — SDK, MCP, bundle-based deploy.

Full compliance: [BEST_PRACTICES_ALIGNMENT.md](BEST_PRACTICES_ALIGNMENT.md).

---

**See also:** [Overview](OVERVIEW.md), [Technical guide](TECHNICAL_GUIDE.md), [Deployment guide](DEPLOYMENT_GUIDE.md), [Control panel & UI](CONTROL_PANEL_UI.md), [Version alignment](VERSION_ALIGNMENT.md)
