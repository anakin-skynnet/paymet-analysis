# 4. Technical

Architecture and implementation reference.

## Architecture

- **Databricks:** Simulator → **Lakeflow** (Bronze → Silver → Gold) → Unity Catalog (12+ views, 4 models). MLflow, Model Serving, AI Gateway, Genie. 11 AI/BI dashboards, SQL Warehouse.
- **App:** FastAPI (analytics, decisioning, notebooks, dashboards, agents) ↔ React (dashboard, dashboards, notebooks, models, ai-agents, decisioning, experiments, declines).

## Data Layer

Bronze: raw + `_ingested_at`. Silver: quality, `risk_tier`, `amount_bucket`, `composite_risk_score`. Gold: 12+ views. UC: `ahs_demos_catalog.ahs_demo_payment_analysis_dev` — governance, lineage, audit.

**Lakehouse recommendations & Vector Search:** `vector_search_and_recommendations.sql` defines `transaction_summaries_for_search` (Delta, source for Vector Search index), `approval_recommendations`, and view `v_recommendations_from_lakehouse`. The app’s **Decisioning** page shows a “Similar cases & recommendations (Lakehouse)” card fed by `GET /api/analytics/recommendations`, which reads from this view to accelerate approval decisions (e.g. similar transactions, retry suggestions). Vector Search index (`resources/vector_search.yml`) syncs from the search table using `databricks-bge-large-en`; when populated, it can power similar-transaction lookups and RAG for agents.

**Approval rules (Lakehouse):** `approval_rules.sql` defines `approval_rules` and view `v_approval_rules_active`. The app **Rules** page (sidebar) lets users create, edit, and delete rules stored in this table. ML and AI agents (e.g. Smart Routing, Smart Retry, Orchestrator) can read from `catalog.schema.approval_rules` or `v_approval_rules_active` to apply business rules and accelerate approval rates alongside model outputs. API: `GET/POST /api/rules`, `PATCH/DELETE /api/rules/{id}`.

**Online features (Lakehouse):** `online_features.sql` defines `online_features` and view `v_online_features_latest`. Features from ML and AI processes are stored here; the app **Dashboard** shows them in the "Online features (Lakehouse)" card. API: `GET /api/analytics/online-features` (optional `source=ml|agent`, `limit`). Populate from decisioning, model serving, or agent jobs.

## ML Layer

Models: approval propensity (RF ~92%), risk (~88%), routing (RF ~75%), retry (~81%). MLflow → UC Registry → Serving (<50ms p95, scale-to-zero). Lifecycle: experiment → register → serve → monitor → retrain.

## AI Agents (Summary)

Genie 2, Model serving 3, AI Gateway 2. Details: [3_AGENTS_VALUE](3_AGENTS_VALUE.md).

## Analytics

11 dashboards are defined in `resources/dashboards.yml` and sourced from `src/payment_analysis/dashboards/*.lvdash.json`; default catalog/schema; warehouse from bundle `var.warehouse_id`. Genie: spaces use catalog/schema; see `genie_spaces.yml`.

## Application Layer

**Backend:** `/api/analytics`, `/api/decisioning`, `/api/notebooks`, `/api/dashboards`, `/api/agents`. UC via Databricks SQL. **Frontend:** React + TanStack Router; `lib/api.ts`. **Stack:** Delta, UC, Lakeflow, SQL Warehouse, MLflow, Serving, Dashboards, Genie, AI Gateway, FastAPI, React, TypeScript, Bun, TailwindCSS, Databricks Asset Bundles.

## Bundle & Deploy

`databricks.yml`: variables `catalog`, `schema`, `environment`, `warehouse_id`; include pipelines, jobs, unity_catalog, vector_search, dashboards, model_serving, genie_spaces, ai_gateway, streaming_simulator. Dashboard JSONs from `src/payment_analysis/dashboards/`. Commands: `databricks bundle validate -t dev`, `databricks bundle deploy -t dev`. For prod catalog/schema in dashboards use `./scripts/validate_bundle.sh prod`. App: `.env` (DATABRICKS_HOST, TOKEN, WAREHOUSE_ID, CATALOG, SCHEMA); `uv run apx dev` or `apx build` + deploy.

## UI & verification checklist

- **Setup & Run:** Steps 1–6 + Quick links; each card opens job/pipeline in Databricks. Run triggers job/pipeline; Open opens in new tab.
- **Dashboards:** 11 dashboards (stream ingestion, data quality, analytics); list from `GET /api/dashboards`; click card opens dashboard in workspace. Real-Time Monitoring, Streaming & Data Quality, Executive, Decline, Daily Trends, etc.
- **Ask Data (Genie):** AI Agents page — sample prompts, "Open Genie to chat" opens Genie in workspace.
- **ML Models:** Approval propensity, risk scoring, smart routing, smart retry + combined business impact; data from backend (catalog/schema); cards open Model Registry or MLflow.
- **Other UI:** Dashboard home, Decisioning, Notebooks, Declines, Reason codes, Smart checkout, Smart retry — cards open related dashboard/notebook/workspace. Incidents → Real-Time Monitoring; Experiments → MLflow. Profile stays app-only (no workspace link).
- **Verify:** `GET /api/setup/defaults`, `GET /api/dashboards`, `GET /api/analytics/models`, `GET /api/agents/agents`. Frontend: set `VITE_DATABRICKS_HOST` for Open-in-Databricks links.

---

**See also:** [0_BUSINESS_CHALLENGES](0_BUSINESS_CHALLENGES.md) · [1_DEPLOYMENTS](1_DEPLOYMENTS.md) · [2_DATA_FLOW](2_DATA_FLOW.md) · [3_AGENTS_VALUE](3_AGENTS_VALUE.md) · [5_DEMO_SETUP](5_DEMO_SETUP.md)
