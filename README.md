# Payment Analysis

Databricks-powered payment approval optimization: real-time analytics, ML models, and AI agents.

## Documentation

| Doc | Audience | Description |
|-----|----------|-------------|
| Doc | Audience | Description |
|-----|----------|-------------|
| [0. Business Challenges](docs/0_BUSINESS_CHALLENGES.md) | C-Suite / Business | Challenges, solution, initiatives, ROI |
| [2. Data Flow](docs/2_DATA_FLOW.md) | Data Engineers | 5-stage flow: ingestion → application |
| [3. Agents & Value](docs/3_AGENTS_VALUE.md) | ML / Data Science | 7 AI agents and business value |
| [4. Technical](docs/4_TECHNICAL.md) | Engineers / Architects | Architecture, bundle & deployment, stack |
| [5. Demo Setup](docs/5_DEMO_SETUP.md) | Everyone | **One-click run links and CLI** |

## Quick Start

1. **Deploy:** `./scripts/deploy.sh dev` (prepares dashboards, then deploys; or `./scripts/validate_bundle.sh dev` then `databricks bundle deploy -t dev`)
2. **Run pipeline:** Use app **Setup & Run** (steps 2–6) or [5_DEMO_SETUP](docs/5_DEMO_SETUP.md): data ingestion → ETL → gold views → Lakehouse SQL → ML training → agents.
3. **App:** `uv sync && bun install` then `uv run apx dev` (set `.env` for Databricks).

See [4_TECHNICAL](docs/4_TECHNICAL.md) (Bundle & Deploy) for variables and commands, and [5_DEMO_SETUP](docs/5_DEMO_SETUP.md) for one-click run links.

## App URL

- **Local:** After `uv run apx dev`, open **http://localhost:8000** (backend serves the app and API at `/api`).
- **Databricks Apps:** If you deploy the app as a Databricks App, the URL is shown in the Apps UI (e.g. `https://<workspace>/apps/<app-id>`).
