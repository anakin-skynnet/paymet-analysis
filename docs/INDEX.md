# Payment Analysis — Documentation Index

Central entry point for all documentation.

---

## At a glance

| Item | Summary |
|------|---------|
| **Goal** | Accelerate payment approval rates; reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities. |
| **Stack** | Databricks (Lakeflow, Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie), Lakebase (Postgres), Vector Search, FastAPI + React app, 7 AI agents, 3 unified dashboards, 4 ML model serving endpoints (+ 3 agent endpoints via Job 6). All serverless compute. DecisionEngine with ML enrichment + Lakebase config + rule evaluation on all decision routes. |
| **Schema** | Always `payment_analysis` (same in dev and prod). DAB schema prefixing disabled. |
| **Deploy** | Two-phase: `./scripts/bundle.sh deploy dev` (phase 1: all except App) → run jobs 5 & 6 → `./scripts/bundle.sh deploy app dev` (phase 2: App). Or automated: `./scripts/deploy_with_dependencies.sh dev`. |
| **App env** | Defaults in `app.yml` at project root; override in Compute → Apps → Edit → Environment. |
| **Check** | `uv run apx dev check` (TS + Python). |

---

## Document map

| Document | Purpose | When to use |
|----------|---------|-------------|
| [README.md](../README.md) | Project intro, business map, quick start | First open; share with others |
| [GUIDE.md](GUIDE.md) | Business overview, architecture, project structure, data sources, control panel | Understand scope, architecture, business context |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deploy steps, app config, env vars, version alignment, troubleshooting | Deploy, configure, fix errors |
| [REFERENCE.md](REFERENCE.md) | Databricks alignment, agent architecture, model serving, UC functions, Vector Search | Technical validation; agent and model serving config |
| [SCHEMA_TABLES_VIEWS.md](SCHEMA_TABLES_VIEWS.md) | Tables and views reference (required vs optional, where used, why empty) | Audit schema; troubleshoot empty dashboards |
| [AGENTS.md](../AGENTS.md) | AI agent (Cursor) rules, project conventions, dev commands | When editing code; align with project rules |
| [.cursor/rules/project.mdc](../.cursor/rules/project.mdc) | Cursor workspace rules (MCP, dev commands, component management) | When configuring IDE or running dev commands |

---

## Quick reference

### Deploy commands

| Purpose | Command |
|---------|---------|
| Check (TS + Python) | `uv run apx dev check` |
| Build | `uv run apx build` |
| Deploy resources (phase 1) | `./scripts/bundle.sh deploy dev` |
| Deploy app (phase 2) | `./scripts/bundle.sh deploy app dev` |
| Automated two-phase | `./scripts/deploy_with_dependencies.sh dev` |
| Validate bundle | `./scripts/bundle.sh validate dev` |

### Job execution order

1 Create Data Repositories → 2 Simulate Events → (Pipeline: ETL) → 3 Initialize Ingestion → 4 Deploy Dashboards → 5 Train Models → 6 Deploy Agents → 7 Genie Sync (optional)

### Troubleshooting

| Issue | Action |
|-------|--------|
| Catalog/schema not found | Create catalog in Data → Catalogs, or run Job 1. See [DEPLOYMENT.md](DEPLOYMENT.md). |
| Gold views / TABLE_OR_VIEW_NOT_FOUND | Run ETL pipeline first, then Job 3. |
| Empty tables/views | See [SCHEMA_TABLES_VIEWS.md](SCHEMA_TABLES_VIEWS.md). |
| Endpoint does not exist (app deploy) | Run phase 1, jobs 5 & 6, then phase 2. |
| Dashboard "refused to connect" | Settings → Security → Embed dashboards → Allow. |
| Web UI not found | Run `uv run apx build` then redeploy. |
