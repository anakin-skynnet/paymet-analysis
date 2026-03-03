# Payment Analysis — Overview

Executive summary and quick reference for the Databricks-powered payment approval optimization platform.

---

## At a glance

| Item | Summary |
|------|---------|
| **Goal** | Accelerate payment approval rates; reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities. |
| **Platform** | Databricks — 100% serverless (Lakeflow, Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie, Vector Search, Lakebase). |
| **ML** | 4 HistGradientBoosting models (14 engineered features) — approval propensity, risk scoring, smart routing, smart retry. |
| **AI Agents** | ResponsesAgent (10 UC tools + python_exec) with 3-tier fallback + 5 specialist agents with write-back tools. |
| **Data** | Medallion (Bronze → Silver → Gold), 24 gold SQL views + 9 gold DLT tables, streaming features, Vector Search. |
| **Dashboards** | 3 unified AI/BI Lakeview dashboards (merged from 10 source dashboards), embeddable in the app. |
| **App** | FastAPI + React (16-page control panel), 8 resources bound, closed-loop DecisionEngine. |
| **Schema** | Always `payment_analysis` (same in dev and prod). DAB schema prefixing disabled. |
| **Deploy** | Two-phase: `./scripts/bundle.sh deploy dev` (phase 1: resources) → run jobs 5 & 6 → `./scripts/bundle.sh deploy app dev` (phase 2: App). Or automated: `./scripts/deploy_with_dependencies.sh dev`. |
| **Check** | `uv run apx dev check` (TS + Python). |

---

## Key metrics

| Metric | Value |
|--------|-------|
| ML models | 4 (approval, risk, routing, retry) |
| AI agents | 6 (orchestrator + 5 specialists) |
| UC functions | 17 individual + 5 consolidated |
| Model Serving endpoints | 4 ML + 1 agent (`payment-response-agent`) |
| Gold SQL views | 24 (including `v_retry_success_by_reason`) |
| Gold DLT tables | 9 |
| AI/BI dashboards | 3 unified (from 10 sources) |
| App pages | 16 |
| App resource bindings | 8 (SQL warehouse, UC volume, Genie space, 5 serving endpoints) |
| Orchestrated jobs | 7 |
| Pipelines | 2 (ETL, Real-Time Stream) |
| Merchants in simulator | 100 (8 segments) |

---

## Document map

| Document | Purpose | When to use |
|----------|---------|-------------|
| [README.md](../README.md) | Project intro, business map, quick start | First open; share with others |
| **[OVERVIEW.md](OVERVIEW.md)** | Executive summary, key metrics, testing status, quick reference | Quick orientation |
| [BUSINESS_REQUIREMENTS.md](BUSINESS_REQUIREMENTS.md) | Business context, use cases, payment platform context, impact on approval rates | Understand scope and business value |
| [TECHNICAL_SOLUTION.md](TECHNICAL_SOLUTION.md) | Architecture, data flow, ML, agents, UI, testing & validation, SDK usage, troubleshooting | Understand how it's built, review testing results |
| [REFERENCE_GUIDE.md](REFERENCE_GUIDE.md) | Deployment, configuration, schema, version alignment, troubleshooting | Deploy, configure, fix errors, audit schema |
| [AGENTS.md](../AGENTS.md) | AI agent (Cursor) rules, project conventions, dev commands | When editing code; align with project rules |

---

## Testing & Validation Status

**Status:** ✅ **PRODUCTION-READY** (February 17, 2026)

All components have been thoroughly tested and validated:
- ✅ All 5 ML serving endpoints in READY state
- ✅ All 3 Lakeview dashboards accessible
- ✅ All 24 gold views verified with real data
- ✅ All UI components functional and connected to Databricks
- ✅ All end-to-end flows tested (AI Chat, Genie, Dashboards, Decision Engine)
- ✅ Code quality verified (TypeScript + Python, no errors)
- ✅ All critical issues fixed

**Key Fixes Applied:**
- Missing `X-Data-Source` header added to analytics endpoints
- Mock data format consistency (approval rates standardized to 0-100 scale)

For detailed testing results, see [Technical Solution — Testing & Validation](TECHNICAL_SOLUTION.md#9-testing--validation).

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

### AI Chat 3-tier fallback

1. **Path 1** — ResponsesAgent (`payment-response-agent`) with 10 UC tools + python_exec (Claude Sonnet 4.5)
2. **Path 2** — AI Gateway direct LLM call (Claude Opus 4.6)
3. **Path 3** — Job 6 agent framework (custom Python orchestrator + 5 specialists)

### Troubleshooting (common)

| Issue | Action |
|-------|--------|
| Catalog/schema not found | Create catalog in Data → Catalogs, or run Job 1. |
| Gold views / TABLE_OR_VIEW_NOT_FOUND | Run ETL pipeline first, then Job 3. |
| Empty tables/views | See [Reference Guide — Schema](REFERENCE_GUIDE.md#schema-tables-and-views). |
| Endpoint does not exist (app deploy) | Run phase 1, jobs 5 & 6, then phase 2. |
| Dashboard "refused to connect" | Settings → Security → Embed dashboards → Allow. |
| Web UI not found | Run `uv run apx build` then redeploy. |
| SDK errors in scripts | See [Technical Solution — SDK Usage](TECHNICAL_SOLUTION.md#11-sdk-usage--troubleshooting). |

---

## References (best practices)

- **[Databricks Apps Cookbook](https://apps-cookbook.dev/docs/intro)** — FastAPI recipes, healthcheck, tables, error handling.
- **[apx](https://github.com/databricks-solutions/apx)** — Toolkit for building Databricks Apps (develop, build, deploy).
- **[AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit)** — Databricks patterns, skills, and MCP tools for AI-assisted development.
- **[Databricks Asset Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/)** — Infrastructure as Code for Databricks.
