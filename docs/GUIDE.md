# Payment Analysis — Guide

Single reference for **what** the platform does, **how** it is built, and how it aligns with best practices. For deploy steps, env vars, and troubleshooting see [Deployment](DEPLOYMENT.md).

---

## 1. Business overview & impact

**Primary goal:** Accelerate payment approval rates and reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities.

**Approach:** Real-time ML, rules, AI agents, and unified analytics so every decision (auth, retry, routing) is data-driven and consistent with business policy.

### Use cases and impact on approval rates

| Use case | What it does | Impact on accelerating approval rates |
|----------|----------------|---------------------------------------|
| **Smart Retry** | Retry logic, timing, cohorts; ML retry model; similar-case recommendations | Surfaces recoverable declines and recommends when/how to retry. |
| **Smart Checkout** | 3DS funnel, service-path performance, Brazil payment links, antifraud attribution | Balances friction vs risk; optimizes auth and routing. |
| **Reason codes & declines** | Unified decline taxonomy, recovery opportunities | Identifies top decline reasons and recoverable share. |
| **Risk & fraud** | Risk tier, fraud score, Risk Assessor agent | Enables risk-based auth and routing. |
| **Routing optimization** | Routing performance, Smart Routing agent, model serving | Routes transactions to the best-performing solution/network. |
| **Decisioning** | Real-time auth, retry, routing via API; rules + ML + Vector Search | Unifies all signals into one decision layer. |

### Technology map

| Technology | Role | How it accelerates approval rates |
|------------|------|-----------------------------------|
| **Lakeflow (Bronze → Silver → Gold)** | Ingestion and transforms | Clean, timely data for ML and analytics. |
| **Unity Catalog** | Tables, governance, gold views | Single source of truth for KPIs and model inputs. |
| **ML models** (approval, risk, routing, retry) | Real-time scores per transaction | Decisions based on predicted likelihood and risk. |
| **Rules engine** (Lakebase/Lakehouse) | Configurable business rules | Operators tune approve/decline/retry without code. |
| **Vector Search** | Similar-transaction lookup | “Similar cases” for retry and routing. |
| **7 AI agents** | Natural-language analytics and recommendations | Explains patterns and suggests actions. |
| **12 dashboards** | KPIs, funnels, reason codes | Visibility into what drives approvals/declines. |
| **FastAPI + React app** | Decision API and control panel | Single place to run jobs, view dashboards, manage rules. |

**High-level flow:** Simulator or real pipelines → Lakeflow → Unity Catalog. Intelligence: ML + rules + Vector Search + AI agents. Application: FastAPI backend + React UI (Setup & Run, dashboards, rules, decisioning).

---

## 2. Architecture

- **Platform:** Databricks — Lakeflow, Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie. 12 dashboards.
- **App:** FastAPI (analytics, decisioning, dashboards, agents, rules, setup) + React (TanStack Router, shadcn/ui). API prefix `/api` for token-based auth.
- **Stack:** Delta, Unity Catalog, Lakeflow, SQL Warehouse, Lakebase (Postgres for rules/experiments/incidents), MLflow, FastAPI, React, TypeScript, Vite, Bun, Databricks Asset Bundles.

**Data flow:** Ingestion → Processing (Bronze → Silver → Gold, &lt;5s) → Intelligence (ML + 7 AI agents) → Analytics (12 dashboards, Genie) → Application (FastAPI + React).

Medallion: Bronze `payments_raw_bronze`, Silver `payments_enriched_silver`, Gold 12+ views. Lakehouse bootstrap creates `app_config`, rules, recommendations, and related views (see [Deployment](DEPLOYMENT.md)).

---

## 3. Project structure

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

### Bundle resources

| Category | Resources |
|----------|-----------|
| UC | Schema + volumes (raw_data, checkpoints, ml_artifacts, reports) |
| Lakebase | Instance + UC catalog (rules, experiments, incidents) |
| SQL warehouse | Payment Analysis Warehouse |
| Pipelines | ETL, Real-Time Stream |
| Jobs | 6 steps (repositories, simulator, ingestion, dashboards, ML, agents) + Genie sync |
| Dashboards | 12 |
| App | payment-analysis (FastAPI + React) |
| Optional | model_serving.yml (after training); Vector Search from `resources/vector_search.yml` |

---

## 4. Workspace components ↔ UI mapping

Execution order in **Setup & Run:** foundation (Lakehouse, Vector Search, gold views, simulator), then optional streaming, ETL, ML, Genie, agents, dashboards.

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

Job/pipeline IDs: `GET /api/setup/defaults`; env overrides: [Deployment](DEPLOYMENT.md).

---

## 5. Data sources (UI ↔ Backend ↔ Databricks)

All UI data goes through the FastAPI backend. No direct Lakebase or Databricks calls from the frontend.

| Area | Backend API | Source |
|------|-------------|--------|
| KPIs, trends, reason codes, declines, Smart Checkout, Smart Retry, recommendations, online features, models, countries | `GET /api/analytics/*` | Databricks (Unity Catalog, SQL Warehouse); fallback to app DB when unavailable |
| Rules | `GET/POST/PATCH/DELETE /api/rules` | Lakebase (if configured) or Lakehouse |
| Setup defaults, config, settings | `GET /api/setup/*`, `PATCH /api/setup/config` | Lakebase app_config/app_settings + workspace job/pipeline resolution |
| Dashboards list & embed URL | `GET /api/dashboards/*` | Static registry + workspace URL for embed |
| Agents list & URLs | `GET /api/agents/*` | Backend → WorkspaceClient |
| Experiments, incidents, decision logs | `GET/POST /api/experiments`, `/api/incidents` | Lakebase (Postgres) |

**Credentials:** When the app is opened from **Compute → Apps**, the platform forwards the user token. The backend uses it for Databricks; otherwise `DATABRICKS_TOKEN` from the app environment. Catalog/schema come from `app_config` (Lakebase or Lakehouse), loaded at startup or on first request.

### Catalog and schema

**Bundle:** `var.catalog`, `var.schema`. **Backend:** env + `app_config`. **Dashboards:** catalog.schema from `scripts/dashboards.py prepare`. Effective catalog/schema from Lakehouse `app_config`; set via **Setup & Run** → **Save catalog & schema**.

---

## 6. Control panel & UI

All data is **fetched from the Databricks backend** and is **interactive**.

### Setup & Run (Operations)

- **Run jobs** — Steps 1–6. **Run** starts the job via `POST /api/setup/run-job`; **Open** opens the job in the workspace.
- **Pipelines** — Start ETL and Real-Time via **Run** → `POST /api/setup/run-pipeline`.
- **Catalog & schema** — Form from `GET /api/setup/defaults`; **Save catalog & schema** → `PATCH /api/setup/config`.
- **Data & config** — App config & settings, countries, online features from backend (Lakebase/Lakehouse).

### Dashboards

- **List:** `GET /api/dashboards/dashboards`. **Embed URL:** `GET /api/dashboards/dashboards/{id}/url?embed=true`. Click to open in workspace or **View embedded** in the UI.

### Genie (AI agents)

- **Ask Data with Genie** — Card opens Genie in the Databricks workspace; chat happens inside Databricks.

### Agents & ML

- **AI agents** — List: `GET /api/agents/agents`. Open: `GET /api/agents/agents/{id}/url` → workspace.
- **ML models** — List: `GET /api/analytics/models` (Unity Catalog). Links to MLflow, model registry, notebooks from backend.

### Lakebase / Postgres data in the UI

| Data | Backend source | Where in UI |
|------|----------------|-------------|
| App config | Lakebase app_config / Lakehouse | Setup → Parameters + Data & config |
| App settings | Lakebase app_settings | Setup → Data & config |
| Countries | Lakehouse / UC | Setup → Data & config; country dropdowns |
| Online features | Lakebase → Lakehouse | Setup → Data & config |
| Approval rules | Lakebase → Lakehouse | Rules page (CRUD) |

---

## 7. Databricks App compliance checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| Runtime spec at root | OK | `app.yml` |
| Command | OK | `uvicorn payment_analysis.backend.app:app` |
| API prefix `/api` | OK | Router `prefix="/api"` |
| requirements.txt | OK | Exact versions from pyproject.toml/uv.lock |
| No system packages | OK | Pure Python deps; psycopg[binary] for DB |
| Config from env | OK | DATABRICKS_*, LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID |
| Bundle app resource | OK | `resources/fastapi_app.yml` |
| Node/frontend | OK | engines `>=22.0.0`; TanStack overrides |

---

## 8. Best practices alignment

**References:** [Apps Cookbook](https://apps-cookbook.dev/docs/intro), [apx](https://github.com/databricks-solutions/apx), [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit).

- **API:** All routes use `response_model` and `operation_id` for OpenAPI client generation. API prefix `/api`. Health: `/api/v1/healthcheck`, `/api/v1/health/database`.
- **Cookbook:** FastAPI layout, `/api` prefix, healthcheck at `/api/v1/healthcheck`, OAuth2/token auth.
- **apx:** Full-stack (React + FastAPI), OpenAPI client at build time, `apx dev check` / `apx build`, shadcn/ui under `src/payment_analysis/ui/components/`, uv for Python, Bun for frontend.
- **AI Dev Kit:** Databricks SDK usage (no guessing API), MCP tools, Asset Bundles, Apps as first-class.

**Unified rules (AGENTS.md / .cursor/rules):** 3-model pattern (Entity, EntityIn, EntityOut); frontend useXSuspense + Suspense + Skeleton; selector(); exact dependency versions; uv / apx bun; do not update deps unless instructed; check after changes.

---

## 9. Verification

```bash
uv run apx dev check          # TypeScript + Python
./scripts/bundle.sh verify dev # Build, smoke test, dashboards, bundle validate
```

**Deployment summary:** One command: `./scripts/bundle.sh deploy dev`. App env (required): `LAKEBASE_PROJECT_ID`, `LAKEBASE_BRANCH_ID`, `LAKEBASE_ENDPOINT_ID`, `DATABRICKS_WAREHOUSE_ID`. Optional: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`. Full steps and troubleshooting: [Deployment](DEPLOYMENT.md).
