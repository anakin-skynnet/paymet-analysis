# Payment Analysis

Databricks-powered payment approval optimization: real-time analytics, ML models, and AI agents.

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/README](docs/README.md) | Documentation index |
| [OVERVIEW](docs/OVERVIEW.md) | Business challenges, initiatives, AI agents, value & ROI |
| [DEPLOYMENT](docs/DEPLOYMENT.md) | Deploy steps, app config, env vars, troubleshooting |
| [TECHNICAL](docs/TECHNICAL.md) | Architecture, data flow, bundle resources, app compatibility |

## Quick Start

1. **Deploy:** `./scripts/bundle.sh deploy dev` (prepares dashboards, then deploys).
2. **Run pipeline:** Use app **Setup & Run** (steps 2–6) or [DEPLOYMENT](docs/DEPLOYMENT.md#demo-setup--one-click-run): data ingestion → ETL → gold views → Lakehouse SQL → ML training → agents.
3. **App:** Open from **Workspace → Apps**; set PGAPPNAME, DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_TOKEN in app environment.

See [DEPLOYMENT](docs/DEPLOYMENT.md) and [TECHNICAL](docs/TECHNICAL.md) for details.
