# Payment Analysis — Documentation Index

Single entry point for all documentation. Use this page to find where each topic lives and get a consolidated summary.

---

## At a glance

| Item | Summary |
|------|---------|
| **Goal** | Accelerate payment approval rates; reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities. |
| **Stack** | Databricks (Lakeflow, Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie), Lakebase (Postgres), FastAPI + React app, 7 AI agents, 3 unified dashboards. |
| **Schema** | Always **`payment_analysis`** (same in dev and prod). DAB schema prefixing disabled via `experimental.skip_name_prefix_for_schema: true`. |
| **Deploy** | Two-phase: `./scripts/bundle.sh deploy dev` (phase 1: all except App) → run jobs 5 & 6 → `./scripts/bundle.sh deploy app dev` (phase 2: App with all resources). Or automated: `./scripts/deploy_with_dependencies.sh dev`. |
| **App env** | Defaults in **`app.yml`** at project root (LAKEBASE_*, ORCHESTRATOR_SERVING_ENDPOINT); override in **Compute → Apps → Edit → Environment** (e.g. DATABRICKS_WAREHOUSE_ID, DATABRICKS_TOKEN). |
| **Check** | `uv run apx dev check` (TS + Python). Full verify: `./scripts/bundle.sh verify dev`. |

---

## Document map

| Document | Purpose | When to use |
|----------|---------|-------------|
| **[README.md](../README.md)** | Project intro, quick start, doc links. | First open; share with others. |
| **[GUIDE.md](GUIDE.md)** | **What** the platform does, **how** it's built. Business overview, payment services context (Getnet), use cases, technology map, architecture, project structure, workspace ↔ UI mapping, **where artifacts are used**, two chatbots, data sources & code guidelines, control panel, verification. | Understand scope, architecture, business context, and where things live. |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | **Deploy & operate.** Prerequisites, quick start, two-phase deploy, steps 1–7, app config (`app.yml` + UI), paths, version alignment, schema consistency, troubleshooting, scripts, job inventory. | Deploy, configure env, fix errors. |
| **[REFERENCE.md](REFERENCE.md)** | **Databricks** feature validation, **agent stack** (runtime vs AgentBricks), **model serving & UC functions**, **approval optimization** summary, user token (OBO). | Validate Databricks-native design; configure agents and model serving; OBO/auth. |
| **[SCHEMA_TABLES_VIEWS.md](SCHEMA_TABLES_VIEWS.md)** | **Catalog/schema reference.** Tables and views in `payment_analysis`: required vs optional, where used, why empty, schema cleansing. | Audit schema; fix empty dashboards; remove unused objects. |
| **[AGENTS.md](../AGENTS.md)** | **AI agent (Cursor) rules.** Solution scope, do's and don'ts, package management, project structure, models & API, frontend rules, dev commands, MCP reference. For the AI working on the repo. | When editing code; align with project rules. |

---

## Consolidated summary by topic

### Business & architecture

- **Goal:** Accelerate approval rates; reduce false declines, suboptimal routing, missed retries.
- **Approach:** Real-time ML, rules engine, 7 AI agents, Vector Search, 3 unified dashboards, one decision layer and control panel.
- **Flow:** Simulator or pipelines → Lakeflow (Bronze → Silver → Gold) → Unity Catalog → ML + rules + agents → FastAPI + React app.
- **Payment context:** Getnet services (Antifraud, 3DS, Network Token, etc.); Smart Checkout, Reason Codes, Smart Retry; Brazil focus; entry systems (Checkout, PD, WS, SEP). See [GUIDE.md](GUIDE.md) §1c.

### Deployment & steps

- **Phase 1 — resources:** `./scripts/bundle.sh deploy dev` deploys everything except the App. Output: *"all resources deployed except the App. Run jobs 5 and 6. After completion, write the prompt `deploy app`"*.
- **Phase 2 — app:** `./scripts/bundle.sh deploy app dev` validates dependencies, uncomments model_serving and serving bindings, deploys the App.
- **Automated:** `./scripts/deploy_with_dependencies.sh dev` runs phase 1 → jobs 5 & 6 → phase 2.
- **Steps (in order):** 1 Create Data Repositories → 2 Simulate Events → (Pipeline: ETL) → 3 Initialize Ingestion → 4 Deploy Dashboards → 5 Train Models → 6 Deploy Agents → 7 Genie Sync (optional).
- **Details:** [DEPLOYMENT.md](DEPLOYMENT.md).

### Schema & catalog

- **Fixed name:** Schema **`payment_analysis`** (dev and prod). Catalog/schema set via Setup & Run → Save catalog & schema.
- **Details:** [DEPLOYMENT.md](DEPLOYMENT.md) § Schema consistency, [SCHEMA_TABLES_VIEWS.md](SCHEMA_TABLES_VIEWS.md).

### Databricks & agents

- **Validation:** [REFERENCE.md](REFERENCE.md) — bundle, UC, Lakeflow, jobs, app, Lakebase, Genie, Model Serving, dashboards.
- **Agent runtime:** Orchestrator chat uses Model Serving when **ORCHESTRATOR_SERVING_ENDPOINT** is set (e.g. in `app.yml`), else Job 6 (custom Python). AgentBricks (LangGraph) used for registration; deploy orchestrator to Model Serving for production.
- **Model serving & UC functions:** [REFERENCE.md](REFERENCE.md) — 5 endpoints, 11 UC functions, creation and app permissions.

### Commands

| Purpose | Command |
|--------|--------|
| Check (TS + Python) | `uv run apx dev check` |
| Verify (build, smoke, dashboards, bundle, jobs, pipelines) | `./scripts/bundle.sh verify [dev\|prod]` |
| Build | `uv run apx build` |
| Deploy (resources) | `./scripts/bundle.sh deploy [dev\|prod]` |
| Deploy (app) | `./scripts/bundle.sh deploy app [dev\|prod]` |
| Deploy (automated two-phase) | `./scripts/deploy_with_dependencies.sh [dev\|prod]` |
| Prepare dashboards/SQL | `uv run python scripts/dashboards.py prepare [--catalog X] [--schema Y]` |

### Troubleshooting (quick)

- **Catalog/schema not found:** Create catalog in Data → Catalogs, or run Job 1. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Lakebase not found:** Create Lakebase project (Compute → Lakebase) or run create_lakebase_autoscaling. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Web UI not found:** Ensure `uv run apx build` then deploy; `source_code_path` = `${workspace.root_path}`. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Gold views / TABLE_OR_VIEW_NOT_FOUND:** Run ETL pipeline first so `payments_enriched_silver` exists, then Job 3. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Empty tables/views:** See [SCHEMA_TABLES_VIEWS.md](SCHEMA_TABLES_VIEWS.md) and [DEPLOYMENT.md](DEPLOYMENT.md) § Why tables and views may be empty.
- **Endpoint does not exist (app deploy):** Model serving and app serving bindings are commented out by default. Run phase 1 (`./scripts/bundle.sh deploy dev`), then jobs 5 & 6, then phase 2 (`./scripts/bundle.sh deploy app dev`). Or use `./scripts/deploy_with_dependencies.sh dev`.

---

Use **INDEX.md** (this file) as the entry point; drill into the linked docs for full detail.
