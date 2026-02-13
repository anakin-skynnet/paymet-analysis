# Payment Analysis — Documentation Index

Single entry point for all documentation. Use this page to find where each topic lives and get a consolidated summary.

---

## At a glance

| Item | Summary |
|------|---------|
| **Goal** | Accelerate payment approval rates; reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities. |
| **Stack** | Databricks (Lakeflow, Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie, AgentBricks Supervisor), Lakebase (Postgres), FastAPI + React app, 7 AI agents, 12 dashboards (3 unified in bundle). |
| **Schema** | Always **`payment_analysis`** (same in dev and prod). DAB schema prefixing disabled via `experimental.skip_name_prefix_for_schema: true`. |
| **Deploy** | Two-phase: `./scripts/bundle.sh deploy dev` (phase 1: all except App) → run jobs 5 & 6 → `./scripts/bundle.sh deploy app dev` (phase 2: App with all resources). Use `--skip-build`, `--skip-clean`, `--skip-publish` flags for incremental deploys. |
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
- **Incremental:** Use `--skip-build`, `--skip-clean`, `--skip-publish` flags on `bundle.sh` for faster deploys.
- **Steps (in order):** 1 Create Data Repositories → 2 Simulate Events → (Pipeline: ETL) → 3 Initialize Ingestion → 4 Deploy Dashboards → 5 Train Models → 6 Deploy Agents → 7 Genie Sync (optional).
- **Details:** [DEPLOYMENT.md](DEPLOYMENT.md).

### Schema & catalog

- **Fixed name:** Schema **`payment_analysis`** (dev and prod). Catalog/schema set via Setup & Run → Save catalog & schema.
- **Details:** [DEPLOYMENT.md](DEPLOYMENT.md) § Schema consistency, [SCHEMA_TABLES_VIEWS.md](SCHEMA_TABLES_VIEWS.md).

### Databricks & agents

- **Validation:** [REFERENCE.md](REFERENCE.md) — bundle, UC, Lakeflow, jobs, app, Lakebase, Genie, Model Serving, dashboards.
- **Agent runtime:** Orchestrator chat uses Model Serving when **ORCHESTRATOR_SERVING_ENDPOINT** is set (e.g. in `app.yml`), else Job 6 (custom Python). AgentBricks (LangGraph) used for registration; deploy orchestrator to Model Serving for production.
- **AgentBricks Supervisor Agent (GA Feb 2026):** Managed orchestration layer that can replace the custom LangGraph orchestrator. Coordinates Genie Spaces, UC functions, Knowledge Assistant endpoints, and MCP servers. Built-in ALHF and OBO auth. See [REFERENCE.md](REFERENCE.md) § AgentBricks Supervisor.
- **Model serving & UC functions:** [REFERENCE.md](REFERENCE.md) — 5 endpoints (names without `-dev` suffix), 11 UC functions, creation and app permissions.

### Commands

| Purpose | Command |
|--------|--------|
| Check (TS + Python) | `uv run apx dev check` |
| Verify (build, smoke, dashboards, bundle, jobs, pipelines) | `./scripts/bundle.sh verify [dev\|prod]` |
| Build | `uv run apx build` |
| Deploy (resources) | `./scripts/bundle.sh deploy [dev\|prod]` |
| Deploy (app) | `./scripts/bundle.sh deploy app [dev\|prod]` |
| Deploy (incremental, skip build) | `./scripts/bundle.sh deploy [dev\|prod] --skip-build` |
| Prepare dashboards/SQL | `uv run python scripts/dashboards.py prepare [--catalog X] [--schema Y]` |

### Troubleshooting (quick)

- **Catalog/schema not found:** Create catalog in Data → Catalogs, or run Job 1. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Lakebase not found:** Create Lakebase project (Compute → Lakebase) or run create_lakebase_autoscaling. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Web UI not found:** Ensure `uv run apx build` then deploy; `source_code_path` = `${workspace.root_path}`. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Gold views / TABLE_OR_VIEW_NOT_FOUND:** Run ETL pipeline first so `payments_enriched_silver` exists, then Job 3. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Empty tables/views:** See [SCHEMA_TABLES_VIEWS.md](SCHEMA_TABLES_VIEWS.md) and [DEPLOYMENT.md](DEPLOYMENT.md) § Why tables and views may be empty.
- **Endpoint does not exist (app deploy):** Model serving and app serving bindings are commented out by default. Run phase 1 (`./scripts/bundle.sh deploy dev`), then jobs 5 & 6, then phase 2 (`./scripts/bundle.sh deploy app dev`).

---

## Latest changes (Feb 2026)

### End-to-end flow verification
- Verified all connections from stream producer → Bronze → Silver → Gold → ML models → Agents → App.
- **Fixed ML endpoint naming mismatch:** Backend was calling `approval-propensity-dev` but DAB deploys `approval-propensity` (no environment suffix). Fixed in `databricks_service.py`.
- **Wired up unused gold views:** Added backend routes for `getDeclineRecoveryOpportunities`, `getCardNetworkPerformance`, `getMerchantSegmentPerformance`, `getDailyTrends` in `analytics.py`.

### AgentBricks Supervisor Agent (GA Feb 10, 2026)
- Documented migration path from custom LangGraph orchestrator to managed Supervisor Agent.
- Supervisor can use 11 UC functions as tools + Genie Space as sub-agent.
- Backend code works with Supervisor endpoint with zero changes (same `ws.serving_endpoints.query()`).
- See [REFERENCE.md](REFERENCE.md) § AgentBricks Supervisor.

### Lakebase integration
- Documented Lakebase usage, benefits, and role in accelerating approval rates.
- Lakebase provides low-latency OLTP for rules, config, features; Lakehouse provides analytical depth.
- See [GUIDE.md](GUIDE.md) § Lakebase integration.

### UI/UX overhaul
- Redesigned for CEO-level clarity: initiative-specific pages (Smart Checkout, Reason Codes, Smart Retry).
- Home page: initiative cards with descriptions, data foundation context, Brazil focus.
- Sidebar: intuitive grouping (Overview, Initiatives, Intelligence, Operations, Settings).
- Setup & Run: reordered execution steps (1-10) for logical flow, "Open in Databricks" buttons open new tabs.
- CSS: moved inline styles to utility classes in `globals.css`.

### Backend hardening
- **SQL injection prevention:** Enhanced `_escape_sql_string`, added `_validate_identifier`, `_validated_full_schema`.
- **Error propagation:** `execute_non_query` now raises `RuntimeError` with Databricks error messages instead of returning `False`.
- **Save catalog & schema fix:** Backend creates `app_config` table if it doesn't exist (no more silent failures).
- **Async safety:** Wrapped 5 Databricks SDK calls in `asyncio.to_thread()` to prevent event-loop blocking.

### Data pipeline fixes
- `continuous_processor.py`: Changed checkpoint from `/tmp/` to durable Volumes-based path.
- `gold_views.sql`: Fixed `event_time` → `event_timestamp` in 5 views.
- `train_models.py`: Added `MAX_TRAINING_ROWS = 100_000` limit to prevent driver OOM.
- `transaction_simulator.py`: Replaced deprecated `datetime.utcnow()`.

### Deployment optimization
- `bundle.sh`: Parallel pre-deploy tasks, `--skip-build`/`--skip-clean`/`--skip-publish` flags, timing instrumentation, cached workspace path.
- `run_and_validate_jobs.py`: Added `--jobs KEY1 KEY2 ...` flag for running specific jobs.
- Removed deprecated `deploy_with_dependencies.sh`.

### Frontend reliability
- Replaced `Math.random()` React keys with deterministic keys.
- Replaced native `confirm()` dialog with Shadcn `AlertDialog`.
- Job/pipeline ID resolution from workspace (buttons disabled when not configured).

### Model serving parameterization
- Added 6 `*_model_version` variables to `databricks.yml` for model entity versions.
- Replaced hardcoded `entity_version` values in `model_serving.yml` with `${var.*_model_version}`.

---

Use **INDEX.md** (this file) as the entry point; drill into the linked docs for full detail.
