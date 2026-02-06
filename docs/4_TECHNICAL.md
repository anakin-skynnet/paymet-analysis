# 4. Technical

Architecture and implementation reference.

## Architecture

- **Databricks:** Simulator → **Lakeflow Declarative Pipelines** (Bronze → Silver → Gold) → Unity Catalog (12+ views, 4 models). MLflow, Model Serving, AI Gateway, Genie. 10 AI/BI dashboards, SQL Warehouse.
- **App:** FastAPI (analytics, decisioning, notebooks, dashboards, agents) ↔ React (dashboard, dashboards, notebooks, models, ai-agents, decisioning, experiments, declines).

## Data Layer

Bronze: raw + `_ingested_at`. Silver: quality, `risk_tier`, `amount_bucket`, `composite_risk_score`. Gold: 12+ views. UC: `ahs_demos_catalog.ahs_demo_payment_analysis_dev` — governance, lineage, audit.

## ML Layer

Models: approval propensity (RF ~92%), risk (~88%), routing (RF ~75%), retry (~81%). MLflow → UC Registry → Serving (<50ms p95, scale-to-zero). Lifecycle: experiment → register → serve → monitor → retrain.

## AI Agents (Summary)

Genie 2, Model serving 3, AI Gateway 2. Details: [3_AGENTS_VALUE](3_AGENTS_VALUE.md).

## Analytics

10 dashboards are defined in `resources/dashboards.yml` and sourced from `src/payment_analysis/dashboards/*.lvdash.json`; default catalog/schema; warehouse from bundle `var.warehouse_id`. Genie: spaces use catalog/schema; see `genie_spaces.yml`.

## Application Layer

**Backend:** `/api/analytics`, `/api/decisioning`, `/api/notebooks`, `/api/dashboards`, `/api/agents`. UC via Databricks SQL. **Frontend:** React + TanStack Router; `lib/api.ts`. **Stack:** Delta, UC, Lakeflow Declarative Pipelines, SQL Warehouse, MLflow, Serving, Dashboards, Genie, AI Gateway, FastAPI, React, TypeScript, Bun, TailwindCSS, Databricks Asset Bundles.

## Bundle & Deploy

`databricks.yml`: variables `catalog`, `schema`, `environment`, `warehouse_id`; include pipelines, jobs, unity_catalog, dashboards, (optional) model_serving, genie_spaces, ai_gateway, streaming_simulator. Commands: `databricks bundle validate -t dev`, `databricks bundle deploy -t dev`. App: `.env` (DATABRICKS_HOST, TOKEN, WAREHOUSE_ID, CATALOG, SCHEMA); `uv run apx dev` or `apx build` + deploy.

---

**See also:** [0_BUSINESS_CHALLENGES](0_BUSINESS_CHALLENGES.md) · [1_DEPLOYMENTS](1_DEPLOYMENTS.md) · [2_DATA_FLOW](2_DATA_FLOW.md) · [3_AGENTS_VALUE](3_AGENTS_VALUE.md) · [5_DEMO_SETUP](5_DEMO_SETUP.md)
