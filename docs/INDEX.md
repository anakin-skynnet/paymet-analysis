# Payment Analysis — Documentation Index

Single entry point for all documentation. Use this page to find where each topic lives and get a consolidated summary.

---

## At a glance

| Item | Summary |
|------|---------|
| **Goal** | Accelerate payment approval rates; reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities. |
| **Stack** | Databricks (Lakeflow, Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie), Lakebase (Postgres), FastAPI + React app, 7 AI agents, 12 dashboards. |
| **Schema** | Always **`payment_analysis`** (same in dev and prod). DAB schema prefixing is disabled via `experimental.skip_name_prefix_for_schema: true`. |
| **Deploy** | `./scripts/bundle.sh deploy dev` (prepare + build + deploy). Then run jobs 1→7 from the app **Setup & Run**. |
| **App env** | `LAKEBASE_PROJECT_ID`, `LAKEBASE_BRANCH_ID`, `LAKEBASE_ENDPOINT_ID`, `DATABRICKS_WAREHOUSE_ID`; optional `DATABRICKS_HOST`, `DATABRICKS_TOKEN`. |
| **Check** | `uv run apx dev check` (TS + Python). Full verify: `./scripts/bundle.sh verify dev`. |

---

## Document map

| Document | Purpose | When to use |
|----------|---------|-------------|
| **[README.md](../README.md)** | Project intro, quick start, doc links. | First open; share with others. |
| **[BUSINESS_AND_SOLUTION.md](BUSINESS_AND_SOLUTION.md)** | **Payment services context and requirement map.** Getnet services, data foundation, Smart Checkout / Reason Codes / Smart Retry context, Brazil focus, entry systems. **Map: Business requirement → Solution → Description.** | Business context and how each requirement is met. |
| **[GUIDE.md](GUIDE.md)** | **What** the platform does, **how** it’s built. Business overview, use cases, technology map, component impact on approval rates, architecture, project structure, workspace ↔ UI mapping, data sources, control panel, best practices, verification. | Understand scope, architecture, and where things live. |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | **Deploy & operate.** Prerequisites, quick start, 7 steps, app config and paths, version alignment, schema consistency (`payment_analysis`), troubleshooting, scripts, job inventory, fixes (Lakebase, catalog/schema, PAT, UI, dashboards). | Deploy, configure env, fix errors. |
| **[DATABRICKS_VALIDATION.md](DATABRICKS_VALIDATION.md)** | **Databricks feature alignment.** Checklist that the solution uses current Databricks naming and capabilities (Lakeflow, UC, PRO warehouse, Lakebase, App, Genie, Model Serving, Lakeview). Use when adding resources or upgrading SDK. | Validate Databricks-native design; upgrade reviews. |
| **[DATABRICKS_IMPLEMENTATION_REVIEW.md](DATABRICKS_IMPLEMENTATION_REVIEW.md)** | **Implementation review.** What is Databricks-native vs custom; prefer AgentBricks + Mosaic AI over custom AI framework; UC agent tools, Feature Store, agent evaluation. | Ensure agents and ML use Databricks-native features. |
| **[AGENT_FRAMEWORK_DATABRICKS.md](AGENT_FRAMEWORK_DATABRICKS.md)** | **AgentBricks.** Convert Python agents to MLflow + LangGraph + UC functions; single schema for tools (`payment_analysis`); log/register, deploy to Model Serving, Multi-Agent Supervisor; custom vs AgentBricks comparison; best practice (same schema as data). | Use or migrate to AgentBricks. |
| **[AGENTS.md](../AGENTS.md)** | **AI agent (Cursor) rules.** Solution scope, do’s and don’ts, package management, project structure, models & API, frontend rules, dev commands, version alignment, MCP reference. For the AI working on the repo. | When editing code; align with project rules. |

---

## Consolidated summary by topic

### Business & architecture
- **Goal:** Accelerate approval rates; reduce false declines, suboptimal routing, missed retries.
- **Approach:** Real-time ML (approval, risk, routing, retry), rules engine, 7 AI agents, Vector Search, 12 dashboards, one decision layer and control panel.
- **Flow:** Simulator or pipelines → Lakeflow (Bronze → Silver → Gold) → Unity Catalog → ML + rules + agents → FastAPI + React app.
- **Details:** [BUSINESS_AND_SOLUTION.md](BUSINESS_AND_SOLUTION.md) (payment context, requirement map), [GUIDE.md §1–2, §1b](GUIDE.md) (use cases, technology map, component impact, architecture).

### Project structure
- **Backend:** `src/payment_analysis/backend/` (FastAPI, routes, config, Lakebase).
- **Frontend:** `src/payment_analysis/ui/` (React, TanStack Router, shadcn/ui).
- **Transform:** `src/payment_analysis/transform/` (gold views, bootstrap, dashboards).
- **Streaming:** `src/payment_analysis/streaming/` (bronze ingest, simulator, pipelines).
- **ML:** `src/payment_analysis/ml/` (train 4 models).
- **Agents:** `src/payment_analysis/agents/` (Python framework + UC tools + LangGraph).
- **Bundle:** `resources/` (UC, Lakebase, pipelines, jobs, dashboards, app).
- **Details:** [GUIDE.md §3](GUIDE.md).

### Deployment & steps
- **One command:** `./scripts/bundle.sh deploy dev` (prepare + build + deploy).
- **Steps (in order):** 1 Create Data Repositories → 2 Simulate Events → (Pipeline: ETL) → 3 Initialize Ingestion (gold views) → 4 Deploy Dashboards → 5 Train Models → 6 Deploy Agents → 7 Genie Sync (optional).
- **App:** Compute → Apps → payment-analysis; set LAKEBASE_* and DATABRICKS_WAREHOUSE_ID (and optionally DATABRICKS_HOST, DATABRICKS_TOKEN).
- **Details:** [DEPLOYMENT.md](DEPLOYMENT.md) (full steps, env, troubleshooting).

### Schema & catalog
- **Fixed name:** Schema is always **`payment_analysis`** (dev and prod). DAB schema prefixing is disabled. Bundle variable `var.schema` defaults to `payment_analysis`.
- **Catalog/schema set via:** Setup & Run → Save catalog & schema (persisted in app_config).
- **Details:** [DEPLOYMENT.md § Schema consistency](DEPLOYMENT.md#schema-consistency-payment_analysis).

### Version alignment
- **Python:** `pyproject.toml` (==) → `uv.lock` → `requirements.txt` via `scripts/sync_requirements_from_lock.py`. Use `uv`, never `pip`.
- **Frontend:** `package.json` (exact versions, no ^) → `bun.lock`. Use `uv run apx bun install`.
- **Details:** [DEPLOYMENT.md § Version alignment](DEPLOYMENT.md#version-alignment).

### Agents
- **Current (Job 6):** Python notebook `agent_framework.py` — orchestrator + 5 specialists (Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender).
- **AgentBricks path:** UC functions in same schema as data (`payment_analysis`), LangGraph agents, MLflow register, Model Serving, Multi-Agent Supervisor. Same schema as data.
- **Details:** [AGENT_FRAMEWORK_DATABRICKS.md](AGENT_FRAMEWORK_DATABRICKS.md).

### Commands
| Purpose | Command |
|--------|--------|
| Check (TS + Python) | `uv run apx dev check` |
| Verify (build, smoke, dashboards, bundle) | `./scripts/bundle.sh verify [dev\|prod]` |
| Build | `uv run apx build` |
| Deploy | `./scripts/bundle.sh deploy [dev\|prod]` |
| Prepare dashboards/SQL | `uv run python scripts/dashboards.py prepare [--catalog X] [--schema Y]` |
| Sync requirements | `uv run python scripts/sync_requirements_from_lock.py` (after `uv lock`) |

- **Details:** [DEPLOYMENT.md § Scripts](DEPLOYMENT.md#scripts), [AGENTS.md §7](AGENTS.md).

### Troubleshooting (quick)
- **Catalog/schema not found:** Create catalog in Data → Catalogs, or run Job 1 (ensure_catalog_schema). See [DEPLOYMENT.md § Fix: Catalog or schema not found](DEPLOYMENT.md#fix-catalog-or-schema-not-found).
- **Lakebase project/endpoint not found:** Create Lakebase project (Compute → Lakebase) or run `uv run python scripts/create_lakebase_autoscaling.py`. See [DEPLOYMENT.md § Fix: Lakebase](DEPLOYMENT.md#fix-lakebase-projectendpoint-not-found).
- **Web UI not found:** Ensure `uv run apx build` then deploy; `source_code_path` = `${workspace.root_path}`. See [DEPLOYMENT.md § Web UI](DEPLOYMENT.md#web-ui-shows-api-only--fallback-page).
- **Gold views / TABLE_OR_VIEW_NOT_FOUND:** Run Payment Analysis ETL pipeline first so `payments_enriched_silver` exists, then run Create Gold Views. See [DEPLOYMENT.md](DEPLOYMENT.md).

---

## One-paragraph summaries (consolidated)

- **README.md** — Project name and goal (accelerate payment approval rates); high-level approach (ML, agents, rules, dashboards); doc table; quick start (deploy, run jobs 1–6, set app env); references (Apps Cookbook, apx, AI Dev Kit); optional pre-commit build.
- **BUSINESS_AND_SOLUTION.md** — Payment services context (Antifraud, 3DS, Network Token, etc.); data foundation; Smart Checkout / Reason Codes / Smart Retry current view; geographic focus (Brazil); entry systems (Checkout, PD, WS, SEP); counter metrics; **Business requirement → Solution → Description** map for the platform.
- **GUIDE.md** — Business overview and use cases (Smart Retry, Smart Checkout, declines, risk, routing, decisioning); technology map and component impact; architecture (Databricks, FastAPI + React); project structure and bundle resources; workspace ↔ UI mapping; data sources and catalog/schema; control panel (Setup & Run, dashboards, rules, agents); best practices and verification.
- **DEPLOYMENT.md** — Prerequisites; one-command deploy (`bundle.sh deploy dev`); 7 steps (jobs 1–7, pipelines); app env (LAKEBASE_*, DATABRICKS_WAREHOUSE_ID); version alignment (Python/frontend exact versions); schema consistency (`payment_analysis`); troubleshooting and fixes (Lakebase, catalog/schema, PAT, UI); scripts; job inventory and notebook paths.
- **AGENT_FRAMEWORK_DATABRICKS.md** — Map Python agents to AgentBricks; same schema as data (`payment_analysis`); UC functions as tools; LangGraph agents; log/register and Model Serving; Multi-Agent Supervisor; custom vs AgentBricks comparison; hybrid app + endpoints.
- **AGENTS.md** — Single source of truth for the AI agent on the repo: solution scope, do's and don'ts, package management (uv, apx bun), project structure, models & API, frontend rules, dev commands, version alignment, MCP reference; verify on main.

---

## Cross-references

- **BUSINESS_AND_SOLUTION** → GUIDE (architecture, use cases), DEPLOYMENT (deploy).
- **GUIDE** → BUSINESS_AND_SOLUTION (payment context, requirement map), Deployment (deploy steps and env), DEPLOYMENT (catalog/schema).
- **DEPLOYMENT** → Guide (architecture, structure), DATABRICKS_VALIDATION (feature alignment), DATABRICKS_IMPLEMENTATION_REVIEW (agents, AgentBricks), AGENT_FRAMEWORK_DATABRICKS (AgentBricks).
- **AGENT_FRAMEWORK_DATABRICKS** → DEPLOYMENT (schema), Guide (overview).
- **AGENTS.md** → DEPLOYMENT (version alignment, commands), .cursor/rules (project.mdc).

Use **INDEX.md** (this file) as the entry point; drill into the linked sections above for full detail.
