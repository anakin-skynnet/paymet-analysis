# Payment Analysis

Databricks-powered payment approval optimization: **accelerate approval rates** with smart retry, smart checkout, risk analysis, fraud detection, and AI-backed decisioning.

## Business overview & impact

**Goal:** Reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities.

**How:** Real-time ML (approval propensity, risk, routing, retry), 7 AI agents, Genie, rules engine, and Vector Search — unified in a single decision layer and control panel.

For use cases, technology map, and **impact on accelerating approval rates**, see **[docs/OVERVIEW.md](docs/OVERVIEW.md)**.

## Documentation (logical grouping)

| Purpose | Document |
|--------|----------|
| **Business & impact** | [Overview](docs/OVERVIEW.md) — Business purpose, use cases, how technologies accelerate approval rates |
| **Technical guideline** | [Technical guide](docs/TECHNICAL_GUIDE.md) — Architecture, structure, deployment summary, version & best practices |
| **Deploy & operate** | [Deployment guide](docs/DEPLOYMENT_GUIDE.md) — Deploy steps, env vars, troubleshooting |
| **Architecture reference** | [Architecture reference](docs/ARCHITECTURE_REFERENCE.md) — Data sources (UI↔backend), workspace↔UI mapping |
| **Control panel** | [Control panel & UI](docs/CONTROL_PANEL_UI.md) — Setup & Run, dashboards, Genie, agents in the UI |
| **Reference** | [Version alignment](docs/VERSION_ALIGNMENT.md) · [Best practices alignment](docs/BEST_PRACTICES_ALIGNMENT.md) |
| **Doc index** | [docs/README.md](docs/README.md) |

## Quick start

1. **Deploy:** `./scripts/bundle.sh deploy dev` (runs dashboard prepare and deploys bundle).
2. **Setup & Run (in order):** In the app, run the 6 jobs in order: **1** Create Data Repositories, **2** Simulate Transaction Events, **3** Initialize Ingestion, **4** Deploy Dashboards, **5** Train Models & Model Serving, **6** Deploy AgentBricks Agents. Optionally run Genie Space Sync and start Lakeflow pipelines when needed.
3. **App environment:** **Workspace → Apps** → payment-analysis → Edit → set `PGAPPNAME`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN`.

The project is deployed as a [Databricks Asset Bundle (DAB)](https://docs.databricks.com/aws/en/dev-tools/bundles/). See [Deployment guide](docs/DEPLOYMENT_GUIDE.md) for full steps and troubleshooting.

## References (best practices)

- **[Databricks Apps Cookbook](https://apps-cookbook.dev/docs/intro)** — FastAPI recipes, healthcheck, tables, error handling for Databricks Apps.
- **[apx](https://github.com/databricks-solutions/apx)** — Toolkit for building Databricks Apps (develop, build, deploy).
- **[AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit)** — Databricks patterns, skills, and MCP tools for AI-assisted development.

## Before commit (optional)

To always build the app before each commit:

```bash
cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

After that, every `git commit` runs `uv run apx build` first; if the build fails, the commit is aborted.
