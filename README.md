# Payment Analysis

Databricks-powered payment approval optimization: **accelerate approval rates** with smart retry, smart checkout, risk analysis, fraud detection, and AI-backed decisioning.

## Overview

**Goal:** Reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities.

**How:** Real-time ML (approval propensity, risk, routing, retry), 7 AI agents, Genie, rules engine, Vector Search for similar-case recommendations. Data flow: simulator → Lakeflow (Bronze → Silver → Gold) → Unity Catalog → FastAPI + React app.

| Use case | Deliverables |
|----------|----------------|
| **Smart Retry** | Retry performance, ML retry model, Smart Retry agent, similar-case recommendations |
| **Smart Checkout** | 3DS funnel, service-path performance, antifraud attribution (Brazil payment links) |
| **Reason codes** | Consolidated declines, unified taxonomy, recovery opportunities |
| **Risk & fraud** | Risk tier, fraud score, risk signals, Fraud Risk dashboard, Risk Assessor agent |
| **Routing** | Routing performance, Smart Routing agent, model serving |

See [Architecture & reference](docs/ARCHITECTURE_REFERENCE.md#business-purpose--use-cases) for the full use-case map.

## Documentation

| Document | Purpose |
|----------|---------|
| [Deployment guide](docs/DEPLOYMENT_GUIDE.md) | Deploy steps, app config, env vars, troubleshooting, scripts |
| [Architecture & reference](docs/ARCHITECTURE_REFERENCE.md) | Business use cases, architecture, data flow, data sources, UI↔backend wiring |
| [Control panel & UI](docs/CONTROL_PANEL_UI.md) | Run jobs, dashboards, Genie, agents, ML, Lakebase tables in the UI |
| [Version alignment](docs/VERSION_ALIGNMENT.md) | Pinned dependency versions and Databricks App compatibility |
| [Docs index](docs/README.md) | Documentation and project structure overview |

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
