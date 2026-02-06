# 4. Technical

Platform architecture and implementation reference.

---

## Architecture

- **Databricks:** Transaction simulator → Lakeflow DLT (Bronze → Silver → Gold) → Unity Catalog (12+ views, 4 models). MLflow, Model Serving, AI Gateway, Genie. 10 AI/BI dashboards, SQL Warehouse.
- **Application:** FastAPI backend (analytics, decisioning, notebooks, agents) ↔ React frontend (dashboard, dashboards gallery, notebooks, ML models, AI agents, decisioning, experiments, declines).

---

## Data layer

- **Bronze:** Raw events + `_ingested_at`; DLT from stream/change feed.
- **Silver:** Quality checks, `risk_tier`, `amount_bucket`, `is_cross_border`, `composite_risk_score`, time columns.
- **Gold:** 12+ views (e.g. `v_executive_kpis`, `v_approval_trends_hourly`, `v_top_decline_reasons`, `v_solution_performance`, `v_retry_performance`).

**Unity Catalog:** `ahs_demos_catalog.ahs_demo_payment_analysis_dev` — tables, views, ML models. Governance: grants, lineage, audit.

---

## ML layer

- **Models:** Approval propensity (RF, ~92%), risk scoring (~88%), smart routing (RF, ~75%), smart retry (~81%). Trained in MLflow, registered in Unity Catalog.
- **Serving:** REST invocations; &lt;50ms p95; scale-to-zero; traffic routes.
- **Lifecycle:** Experiment → register → serve → monitor/drift → retrain.

---

## AI agents (summary)

- **Genie (2):** Approval Optimizer, Decline Insights — natural language over gold views.
- **Model serving (3):** Approval propensity, smart routing, smart retry — real-time APIs.
- **AI Gateway (2):** Payment Intelligence Assistant, Risk Assessment Advisor — Llama 3.1 70B.  
Details: [3_AGENTS_VALUE](3_AGENTS_VALUE.md).

---

## Analytics

- **AI/BI dashboards:** 10 `.lvdash.json` in `dashboards/`; default catalog/schema `ahs_demos_catalog.ahs_demo_payment_analysis_dev`; warehouse from bundle (`var.warehouse_id` = deployed SQL warehouse in dev).
- **Genie:** Spaces use `catalog`/`schema`; sample questions and instructions in `genie_spaces.yml`.

---

## Application layer

**Backend (FastAPI):**  
`/api/analytics/*` (KPIs, trends, declines, solutions, geography), `/api/decisioning/*` (auth, retry, routing), `/api/notebooks/*`, `/api/agents/*` (list, by id, workspace URL). Unity Catalog via Databricks SQL connector.

**Frontend (React + TanStack Router):**  
Routes: dashboard, dashboards, notebooks, models, ai-agents, decisioning, experiments, declines. Components: KPI cards, trend charts, dashboard embed, agent cards. API client in `lib/api.ts`.

**Stack:** Delta Lake, Unity Catalog, Lakeflow Declarative Pipelines (DLT), SQL Warehouse, MLflow, Model Serving, AI/BI Dashboards, Genie, AI Gateway, FastAPI, React, TypeScript, Bun, TailwindCSS, Databricks Asset Bundles.

---

## Bundle and deploy

- **Config:** `databricks.yml`; variables `catalog`, `schema`, `environment`, `warehouse_id`; include pipelines, jobs, unity_catalog, (optional) dashboards, model_serving, genie_spaces, ai_gateway, streaming_simulator.
- **Commands:** `databricks bundle validate --target dev`; `databricks bundle deploy --target dev`; run jobs/start pipelines per [5_DEMO_SETUP](5_DEMO_SETUP.md).
- **App:** `.env` for `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`; `uv run apx dev` or `apx build` + deploy.

---

**See also:** [0_BUSINESS_CHALLENGES](0_BUSINESS_CHALLENGES.md) · [1_DEPLOYMENTS](1_DEPLOYMENTS.md) · [2_DATA_FLOW](2_DATA_FLOW.md) · [3_AGENTS_VALUE](3_AGENTS_VALUE.md) · [5_DEMO_SETUP](5_DEMO_SETUP.md)
