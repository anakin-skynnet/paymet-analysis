# Payment Analysis — Documentation Index

Single entry point for all documentation. Use this page to find where each topic lives and get a consolidated summary.

---

## At a glance

| Item | Summary |
|------|---------|
| **Goal** | Accelerate payment approval rates; reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities. |
| **Stack** | Databricks (Lakeflow, Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie), Lakebase (Postgres), FastAPI + React app, 7 AI agents, 12 dashboards. |
| **Schema** | Always **`payment_analysis`** (same in dev and prod). DAB schema prefixing disabled via `experimental.skip_name_prefix_for_schema: true`. |
| **Deploy** | `./scripts/bundle.sh deploy dev` (prepare + build + deploy). Then run jobs 1→7 from the app **Setup & Run**. |
| **App env** | `LAKEBASE_PROJECT_ID`, `LAKEBASE_BRANCH_ID`, `LAKEBASE_ENDPOINT_ID`, `DATABRICKS_WAREHOUSE_ID`; optional `DATABRICKS_HOST`, `DATABRICKS_TOKEN`. |
| **Check** | `uv run apx dev check` (TS + Python). Full verify: `./scripts/bundle.sh verify dev`. |

---

## Document map (5 docs)

| Document | Purpose | When to use |
|----------|---------|-------------|
| **[README.md](../README.md)** | Project intro, quick start, doc links. | First open; share with others. |
| **[GUIDE.md](GUIDE.md)** | **What** the platform does, **how** it's built. Business overview, use cases, technology map, architecture, project structure, workspace ↔ UI mapping, **data sources & code guidelines** (§10), control panel, best practices, verification. | Understand scope, architecture, data sources, and where things live. |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | **Deploy & operate.** Prerequisites, quick start, 7 steps, app config and paths, version alignment, schema consistency, troubleshooting, scripts, job inventory, fixes. | Deploy, configure env, fix errors. |
| **[BUSINESS_AND_SOLUTION.md](BUSINESS_AND_SOLUTION.md)** | **Payment services context and requirement map.** Getnet services, data foundation, Smart Checkout / Reason Codes / Smart Retry context, Brazil focus, entry systems. **Map: Business requirement → Solution → Description.** | Business context and how each requirement is met. |
| **[DATABRICKS.md](DATABRICKS.md)** | **Databricks alignment & agents.** Part 1: Feature validation (bundle, UC, Lakeflow, jobs, app, Lakebase, Genie, Model Serving, dashboards). Part 2: Implementation review (custom vs AgentBricks, recommendations). Part 3: Agent framework (AgentBricks conversion, UC tools, LangGraph, Model Serving, Multi-Agent Supervisor). | Validate Databricks-native design; upgrade reviews; agent migration. |
| **[AGENTS.md](../AGENTS.md)** | **AI agent (Cursor) rules.** Solution scope, do's and don'ts, package management, project structure, models & API, frontend rules, dev commands, MCP reference. For the AI working on the repo. | When editing code; align with project rules. |

---

## Consolidated summary by topic

### Business & architecture

- **Goal:** Accelerate approval rates; reduce false declines, suboptimal routing, missed retries.
- **Approach:** Real-time ML, rules engine, 7 AI agents, Vector Search, 12 dashboards, one decision layer and control panel.
- **Flow:** Simulator or pipelines → Lakeflow (Bronze → Silver → Gold) → Unity Catalog → ML + rules + agents → FastAPI + React app.
- **Details:** [BUSINESS_AND_SOLUTION.md](BUSINESS_AND_SOLUTION.md), [GUIDE.md](GUIDE.md) §1–2, §10 (data sources).

### Project structure

- **Backend:** `src/payment_analysis/backend/` (FastAPI, routes, config, Lakebase).
- **Frontend:** `src/payment_analysis/ui/` (React, TanStack Router, shadcn/ui).
- **Transform:** `src/payment_analysis/transform/` (gold views, bootstrap, dashboards).
- **Streaming, ML, Agents, Bundle:** See [GUIDE.md](GUIDE.md) §3.

### Deployment & steps

- **One command:** `./scripts/bundle.sh deploy dev`.
- **Steps (in order):** 1 Create Data Repositories → 2 Simulate Events → (Pipeline: ETL) → 3 Initialize Ingestion → 4 Deploy Dashboards → 5 Train Models → 6 Deploy Agents → 7 Genie Sync (optional).
- **Details:** [DEPLOYMENT.md](DEPLOYMENT.md).

### Schema & catalog

- **Fixed name:** Schema **`payment_analysis`** (dev and prod). Catalog/schema set via Setup & Run → Save catalog & schema.
- **Details:** [DEPLOYMENT.md](DEPLOYMENT.md) § Schema consistency.

### Databricks & agents

- **Validation:** [DATABRICKS.md](DATABRICKS.md) Part 1 — bundle, UC, Lakeflow, jobs, app, Lakebase, Genie, Model Serving, dashboards.
- **Implementation:** [DATABRICKS.md](DATABRICKS.md) Part 2 — prefer AgentBricks + Mosaic AI for agents.
- **AgentBricks:** [DATABRICKS.md](DATABRICKS.md) Part 3 — UC tools, LangGraph, Model Serving, Multi-Agent Supervisor.

### Commands

| Purpose | Command |
|--------|--------|
| Check (TS + Python) | `uv run apx dev check` |
| Verify (build, smoke, dashboards, bundle, jobs, pipelines) | `./scripts/bundle.sh verify [dev\|prod]` |
| Build | `uv run apx build` |
| Deploy | `./scripts/bundle.sh deploy [dev\|prod]` |
| Prepare dashboards/SQL | `uv run python scripts/dashboards.py prepare [--catalog X] [--schema Y]` |

### Troubleshooting (quick)

- **Catalog/schema not found:** Create catalog in Data → Catalogs, or run Job 1. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Lakebase not found:** Create Lakebase project (Compute → Lakebase) or run `create_lakebase_autoscaling.py`. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Web UI not found:** Ensure `uv run apx build` then deploy; `source_code_path` = `${workspace.root_path}`. See [DEPLOYMENT.md](DEPLOYMENT.md).
- **Gold views / TABLE_OR_VIEW_NOT_FOUND:** Run ETL pipeline first so `payments_enriched_silver` exists, then Job 3 (Gold Views). See [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Cross-references

- **BUSINESS_AND_SOLUTION** → GUIDE (architecture), DEPLOYMENT (deploy).
- **GUIDE** → BUSINESS_AND_SOLUTION (payment context), DEPLOYMENT (steps, env), §10 (data sources & code guidelines).
- **DEPLOYMENT** → GUIDE (architecture), DATABRICKS (feature alignment, agents).
- **DATABRICKS** → DEPLOYMENT (schema, Job 3), GUIDE (overview).

Use **INDEX.md** (this file) as the entry point; drill into the linked docs for full detail.
