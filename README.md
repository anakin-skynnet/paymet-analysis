# Payment Analysis

Databricks-powered payment approval optimization: real-time analytics, ML models, and AI agents.

## Overview

**Challenge:** Declined legitimate transactions mean lost revenue — false declines, static rules, suboptimal routing.

**Solution:** Real-time ML per transaction, smart routing, intelligent retry, 7 AI agents, Genie. Data flow: simulator → Lakeflow (Bronze → Silver → Gold) → Unity Catalog → FastAPI + React app.

| Initiative | Scope | Deliverables |
|------------|--------|--------------|
| Smart Checkout | Payment links, Brazil | 3DS funnel, antifraud attribution |
| Reason Codes | E-commerce, Brazil | Consolidated declines, unified taxonomy |
| Smart Retry | Brazil | Reattempt success rate, effectiveness |

**AI agents (7):** Genie (2), Model Serving (3), [Mosaic AI Gateway](https://learn.microsoft.com/en-us/azure/databricks/ai-gateway/) (2). See [Deployment guide](docs/DEPLOYMENT_GUIDE.md) and [Architecture & reference](docs/ARCHITECTURE_REFERENCE.md).

## Documentation

| Document | Purpose |
|----------|---------|
| [Deployment guide](docs/DEPLOYMENT_GUIDE.md) | Deploy steps, app config, env vars, troubleshooting, scripts |
| [Architecture & reference](docs/ARCHITECTURE_REFERENCE.md) | Architecture, data flow, bundle resources, app compliance |
| [Data sources](docs/DATA_SOURCES.md) | Where app data comes from (Databricks, Lakehouse tables, fallbacks) |
| [Version alignment](docs/VERSION_ALIGNMENT.md) | Pinned dependency versions and Databricks App compatibility |

## Quick start

1. **Deploy:** `./scripts/bundle.sh deploy dev` (runs dashboard prepare and deploys bundle).
2. **Setup & Run (in order):** In the app, run the 6 jobs in order: **1** Create Data Repositories (Lakehouse, Vector Search), **2** Simulate Transaction Events, **3** Initialize Ingestion (Gold views, Vector Search sync), **4** Deploy Dashboards (Prepare & Publish), **5** Train Models & Model Serving, **6** Deploy AgentBricks Agents. Optionally run Genie Space Sync and start Lakeflow pipelines when needed.
3. **App environment:** **Workspace → Apps** → payment-analysis → Edit → set `PGAPPNAME`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN`.

See [Deployment guide](docs/DEPLOYMENT_GUIDE.md) for full steps and troubleshooting.

## Before commit (optional)

To always build the app before each commit (so `__dist__` stays in sync and deploy has a fresh UI), install the pre-commit hook:

```bash
cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

After that, every `git commit` runs `uv run apx build` first; if the build fails, the commit is aborted.
