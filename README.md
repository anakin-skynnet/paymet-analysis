# Payment Analysis

Databricks-powered payment approval optimization: **accelerate approval rates** with smart retry, smart checkout, risk analysis, fraud detection, and AI-backed decisioning.

## Business overview & impact

**Goal:** Reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities.

**How:** Real-time ML (approval propensity, risk, routing, retry), 7 AI agents, Genie, rules engine, and Vector Search — unified in a single decision layer and control panel.

For use cases, technology map, and **impact on accelerating approval rates**, see **[docs/GUIDE.md](docs/GUIDE.md)**.

---

## Map for business users

| Business purpose | Technical solution | What you get (plain language) |
|------------------|--------------------|--------------------------------|
| **One trusted data base for all initiatives** | Medallion pipelines (Bronze → Silver → Gold), gold views, single catalog | Everyone works from the same numbers; Smart Checkout, Reason Codes, and Smart Retry share one clean, up-to-date picture. |
| **See why payments fail and where to act** | Reason Codes, decline dashboards, top-decline and recovery views, Decline Analyst agent | Declines from all channels in one place, with clear reasons and where recovery or routing changes will help most. |
| **Optimize payment-link performance (e.g. Brazil)** | Smart Checkout UI, 3DS funnel, solution performance and routing dashboards, Smart Routing agent | You see how each path (Antifraud, 3DS, Network Token, etc.) performs and how to balance security, friction, and approvals. |
| **Recover more from retries and recurring payments** | Smart Retry UI, retry performance views, Smart Retry agent, decisioning API | You see which failed payments are worth retrying, when and how to retry, and the impact on approval rates (e.g. 1M+ such transactions per month in Brazil). |
| **Get clear next steps, not just reports** | Decisioning API, Recommendations UI, orchestrator + 5 AI agents, rules engine | You get recommended actions and expected impact; rules, models, and AI work together in one place so decisions stay consistent. |
| **Learn from what we do and improve over time** | Experiments, incidents, rules management, model retraining jobs | You track which actions were taken and what happened, run A/B tests, and keep improving how we approve and route payments. |
| **Keep insights reliable** | Experiments, validation workflow, False Insights metric | You balance speed and accuracy; experts can flag bad or non-actionable insights so the system gets better. |
| **Focus on the regions that matter (e.g. Brazil)** | Catalog/schema and country filters, geography dashboards | You filter by country or region; Brazil’s share of volume is visible by default so local teams see what’s relevant. |
| **See performance across all entry channels** | Entry-system distribution analytics, gold views and dashboards | You see how each channel (Checkout, PD, WS, SEP) performs without double-counting or mixing definitions. |
| **Monitor performance in real time and over time** | 12 dashboards (executive, trends, declines, routing, retry, risk, etc.), real-time views | You have KPIs, trends, and reason codes for both live monitoring and historical analysis. |
| **One place to run and control everything** | FastAPI + React app: Setup & Run, Dashboards, Rules, Decisioning, Reason Codes, Smart Checkout, Smart Retry, AI agents | You run jobs, manage rules, view dashboards and recommendations, and operate the full stack from a single control panel. |
| **Ask in plain language and get recommendations** | 7 AI agents (orchestrator + 5 specialists), Genie | You ask questions in natural language and get answers and recommendations on routing, retries, declines, risk, and performance. |

## Documentation

| Purpose | Document |
|--------|----------|
| **All docs (index)** | [docs/INDEX.md](docs/INDEX.md) — Start here: document map and consolidated summary |
| **Guide** | [docs/GUIDE.md](docs/GUIDE.md) — What the platform does, architecture, project structure, data sources & code guidelines, control panel |
| **Deploy & operate** | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Deploy steps, env vars, version alignment, troubleshooting |
| **Business context** | [docs/BUSINESS_AND_SOLUTION.md](docs/BUSINESS_AND_SOLUTION.md) — Payment services context, requirement → solution map |
| **Databricks & agents** | [docs/DATABRICKS.md](docs/DATABRICKS.md) — Feature validation, implementation review, AgentBricks conversion |

## Quick start

1. **Deploy:** `./scripts/bundle.sh deploy dev` (runs dashboard prepare and deploys bundle).
2. **Setup & Run (in order):** In the app, run the 6 jobs in order: **1** Create Data Repositories, **2** Simulate Transaction Events, **3** Initialize Ingestion, **4** Deploy Dashboards, **5** Train Models & Model Serving, **6** Deploy Agents. Optionally run Genie Space Sync and start Lakeflow pipelines when needed.
3. **App environment:** **Workspace → Apps** → payment-analysis → Edit → set `LAKEBASE_PROJECT_ID`, `LAKEBASE_BRANCH_ID`, `LAKEBASE_ENDPOINT_ID` (same as Job 1), `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN`.

The project is deployed as a [Databricks Asset Bundle (DAB)](https://docs.databricks.com/aws/en/dev-tools/bundles/). See [Deployment](docs/DEPLOYMENT.md) for full steps and troubleshooting.

## References (best practices)

This solution follows patterns from [**databricks-solutions**](https://github.com/databricks-solutions):

- **[Databricks Apps Cookbook](https://apps-cookbook.dev/docs/intro)** — FastAPI recipes, healthcheck, tables, error handling for Databricks Apps.
- **[apx](https://github.com/databricks-solutions/apx)** — Toolkit for building Databricks Apps (develop, build, deploy).
- **[AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit)** — Databricks patterns, skills, and MCP tools for AI-assisted development.

## Before commit (optional)

To always build the app before each commit:

```bash
cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

After that, every `git commit` runs `uv run apx build` first; if the build fails, the commit is aborted.
