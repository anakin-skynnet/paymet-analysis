# Payment Approval Optimization Platform

Databricks-powered solution to maximize payment approval rates via real-time analytics, ML, and AI.

## Documentation

| Doc | Audience | Description |
|-----|----------|-------------|
| [0. Business Challenges](docs/0_BUSINESS_CHALLENGES.md) | C-Suite / Business | Challenges, solution, initiatives, ROI |
| [1. Deployments](docs/1_DEPLOYMENTS.md) | DevOps / Engineering | **Step-by-step deployment** (start here) |
| [2. Data Flow](docs/2_DATA_FLOW.md) | Data Engineers | 5-stage flow: ingestion → application |
| [3. Agents & Value](docs/3_AGENTS_VALUE.md) | ML / Data Science | 7 AI agents and business value |
| [4. Technical](docs/4_TECHNICAL.md) | Engineers / Architects | Architecture, stack, bundle |
| [5. Demo Setup](docs/5_DEMO_SETUP.md) | Everyone | **One-click run links and CLI** |

## Quick Start

```bash
uv sync && bun install
databricks bundle validate -t dev && databricks bundle deploy -t dev
uv run apx dev
```

See [1_DEPLOYMENTS](docs/1_DEPLOYMENTS.md) and [5_DEMO_SETUP](docs/5_DEMO_SETUP.md) for full steps and one-click runs.

## App URL

- **Local:** After `uv run apx dev`, open **http://localhost:8000** (backend serves the app and API at `/api`).
- **Databricks Apps:** If you deploy the app as a Databricks App, the URL is shown in the Apps UI (e.g. `https://<workspace>/apps/<app-id>`).
