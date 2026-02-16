# Payment Analysis

Databricks-powered payment approval optimization: **accelerate approval rates** with smart retry, smart checkout, risk analysis, fraud detection, and AI-backed decisioning.

## Business overview & impact

**Goal:** Reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities.

**How:** Real-time ML (4 HistGradientBoosting models with 14 engineered features), 7 AI agents (all with write-back tools), Genie, rules engine, Vector Search, streaming features, and Lakebase — unified in a closed-loop decision engine and control panel. All compute is serverless. 4 ML model serving endpoints + 3 agent endpoints (managed by Job 6), 3 unified AI/BI dashboards, 16+ gold views (including `v_retry_success_by_reason`), 7 orchestrated jobs, 13 resources bound to the app. Decision routes use `DecisionEngine` with parallel ML + Vector Search enrichment (asyncio.gather), streaming real-time features, thread-safe caching, and outcome recording for continuous improvement.

**Recent enhancements (20 QA recommendations implemented):**
- **Closed feedback loop:** POST /api/decision/outcome records actual outcomes; policies use VS approval rates and agent confidence to adjust borderline decisions
- **Feature parity:** ML features built with `_build_ml_features()` matching exact training schema (14 features including temporal, merchant/solution rates, network encoding, risk interactions)
- **Parallel enrichment:** ML model calls and Vector Search run concurrently; thread-safe config caching with `threading.Lock`
- **Streaming features:** Real-time behavioral features (approval_rate_5m, txn_velocity_1m) feed into authentication decisions
- **Agent write-back:** Decline Analyst and Risk Assessor agents can write recommendations and propose config changes directly to Lakebase
- **Actionable UI:** Top-3 actions on Command Center, 90% target reference lines, contextual guidance on Smart Checkout, preset scenarios and actionable recommendations on Decisioning, inline expert review on Reason Codes, recovery gap analysis on Smart Retry

For use cases, technology map, and **impact on accelerating approval rates**, see **[docs/GUIDE.md](docs/GUIDE.md)**.

---

## Map for business users

| Business purpose | Technical solution | What you get (plain language) |
|------------------|--------------------|--------------------------------|
| **One trusted data base for all initiatives** | Medallion pipelines (Bronze → Silver → Gold), gold views, single catalog | Everyone works from the same numbers; Smart Checkout, Reason Codes, and Smart Retry share one clean, up-to-date picture. |
| **See why payments fail and where to act** | Reason Codes, decline dashboards, top-decline and recovery views, Decline Analyst agent | Declines from all channels in one place, with clear reasons and where recovery or routing changes will help most. |
| **Optimize payment-link performance (e.g. Brazil)** | Smart Checkout UI, 3DS funnel, solution performance and routing dashboards, Smart Routing agent | You see how each path (Antifraud, 3DS, Network Token, etc.) performs and how to balance security, friction, and approvals. |
| **Recover more from retries and recurring payments** | Smart Retry UI, retry performance views, Smart Retry agent, decisioning API | You see which failed payments are worth retrying, when and how to retry, and the impact on approval rates (e.g. 1M+ such transactions per month in Brazil). |
| **Get clear next steps, not just reports** | Top-3 actions, contextual guidance, preset scenarios, inline expert review, recovery gap, agent write-back | You get recommended actions with expected impact at every level; agents write recommendations directly to Lakebase. |
| **Learn from what we do and improve over time** | Outcome feedback loop (POST /outcome), experiments, incidents, agent write-back, streaming features | Decision outcomes are recorded; agents propose config changes; the system continuously improves with every decision. |
| **Keep insights reliable** | Inline expert review (Valid/Invalid/Non-Actionable), experiments, False Insights metric | Experts flag bad insights directly from Reason Codes; the system learns from every review. |
| **Focus on the regions that matter (e.g. Brazil)** | Catalog/schema and country filters, geography dashboards | You filter by country or region; Brazil’s share of volume is visible by default so local teams see what’s relevant. |
| **See performance across all entry channels** | Entry-system distribution analytics, gold views and dashboards | You see how each channel (Checkout, PD, WS, SEP) performs without double-counting or mixing definitions. |
| **Monitor performance in real time and over time** | 3 unified dashboards (Data & Quality, ML & Optimization, Executive & Trends), real-time views | You have KPIs, trends, and reason codes for both live monitoring and historical analysis. |
| **One place to run and control everything** | FastAPI + React app: Setup & Run, Dashboards, Rules, Decisioning, Reason Codes, Smart Checkout, Smart Retry, AI agents | You run jobs, manage rules, view dashboards and recommendations, and operate the full stack from a single control panel. |
| **Ask in plain language and get recommendations** | 7 AI agents (orchestrator + 5 specialists), Genie | You ask questions in natural language and get answers and recommendations on routing, retries, declines, risk, and performance. |

## Documentation

| Purpose | Document |
|--------|----------|
| **Index** | [docs/INDEX.md](docs/INDEX.md) — Document map and quick reference |
| **Guide** | [docs/GUIDE.md](docs/GUIDE.md) — What the platform does, business context, architecture, project structure, control panel, data sources, verification |
| **Deploy & operate** | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Deploy steps, app env (`app.yml` + UI), two-phase deploy, version alignment, troubleshooting |
| **Reference** | [docs/REFERENCE.md](docs/REFERENCE.md) — Databricks alignment, agents (runtime vs AgentBricks), model serving & UC functions, approval optimization |
| **Schema** | [docs/SCHEMA_TABLES_VIEWS.md](docs/SCHEMA_TABLES_VIEWS.md) — Tables and views reference (required vs optional, where used, why empty) |

## Quick start

Deployment is **two-phase**: first deploy all resources except the App, then deploy the App after its dependencies exist.

1. **Phase 1 — deploy resources:** `./scripts/bundle.sh deploy dev` — builds the UI, cleans existing BI dashboards (avoids duplicates), prepares dashboards, deploys jobs/pipelines/dashboards/UC/model serving (everything **except** the App). 4 ML model serving endpoints are included; 3 agent endpoints are managed by Job 6.
2. **Run jobs 5 and 6:** In the app **Setup & Run**, run **Job 5 (Train Models)** and **Job 6 (Deploy Agents)** so ML models and agent registrations exist in UC.
3. **Phase 2 — deploy app:** `./scripts/bundle.sh deploy app dev` — validates app dependencies, then deploys the App with all 13 resources bound (1 SQL warehouse, 1 UC volume, 4 ML serving endpoints, 7 jobs).
4. **Setup & Run (in order):** Jobs **1** → **2** → (ETL pipeline) → **3** → **4** → **5** → **6** → **7** (Create Data Repositories, Simulate Events, Initialize Ingestion, Deploy Dashboards, Train Models, Deploy Agents, Genie Sync).
5. **App environment:** Defined in **`app.yml`** at project root (e.g. `LAKEBASE_PROJECT_ID`, `LAKEBASE_BRANCH_ID`, `LAKEBASE_ENDPOINT_ID`, `ORCHESTRATOR_SERVING_ENDPOINT`). Override in **Workspace → Apps → payment-analysis → Edit → Environment** (e.g. `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_HOST`, `DATABRICKS_TOKEN`). Redeploy to apply `app.yml` changes.

**Automated two-phase:** `./scripts/deploy_with_dependencies.sh dev` runs phase 1, executes jobs 5 and 6 automatically, then runs phase 2.

**Key data integration notes:**
- **Closed-loop DecisionEngine:** Decision routes (`/authentication`, `/retry`, `/routing`) use `DecisionEngine` with parallel ML + Vector Search enrichment (`asyncio.gather`), streaming real-time features (approval_rate_5m, txn_velocity_1m), Lakebase config, and rule evaluation. Policies use VS approval rates and agent confidence to adjust borderline decisions. Outcomes are recorded via POST `/api/decision/outcome` closing the feedback loop. Thread-safe config caching with `threading.Lock`. Falls back to pure-policy heuristics when Lakebase/ML is unavailable.
- **ML feature parity:** `_build_ml_features()` constructs exactly the 14 features used during training (temporal, merchant/solution approval rates, network encoding, risk-amount interaction), ensuring inference matches training schema.
- **Agent write-back:** Decline Analyst and Risk Assessor agents have write tools (`write_decline_recommendation`, `propose_decline_config`, `write_risk_recommendation`, `propose_risk_config`) to write recommendations and propose config changes to Lakebase.
- **Dual-write sync:** Approval rules synced between Lakebase (UI) and Lakehouse (agents) via BackgroundTasks.
- **Vector Search:** `similar_transactions_index` populated from `payments_enriched_silver` via MERGE, synced to `databricks-bge-large-en`.
- **17 individual + 5 consolidated UC functions** serve as agent tools. `v_retry_success_by_reason` gold view added for granular retry analysis by decline reason.
- **Actionable UI:** Top-3 actions on Command Center, 90% target reference lines, last-updated indicators, contextual Smart Checkout guidance, preset decisioning scenarios, actionable recommendation buttons, inline expert review, recovery gap analysis.
- **Error resilience:** All UI routes have `ErrorBoundary` wrappers and consistent `glass-card` styling.

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
