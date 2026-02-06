# 1. Deployments

Step-by-step deployment for **Payment Analysis**. **One-click run links:** [5_DEMO_SETUP](5_DEMO_SETUP.md).

## Prerequisites

Databricks workspace (Unity Catalog), SQL Warehouse, CLI configured. Python 3.10+ with `uv`, Node 18+ with `bun`. Permissions: jobs, **Lakeflow**, model serving; write to `ahs_demos_catalog`; deploy to `/Workspace/Users/<your_email>/payment-analysis` (or `var.workspace_folder`).

## Quick Start

**Before every deploy** (so dashboards and the Gold Views job use the same catalog/schema):

```bash
./scripts/validate_bundle.sh dev    # dev: prepares .build/dashboards and .build/transform, then validates
# or: uv run python scripts/prepare_dashboards.py   then  databricks bundle validate -t dev
databricks bundle deploy -t dev
```

For prod with different catalog/schema, run `./scripts/validate_bundle.sh prod` (prepares with prod catalog/schema). Then run jobs/pipelines per [5_DEMO_SETUP](5_DEMO_SETUP.md). Dashboards read from `.build/dashboards/`; the **Create Gold Views** job runs `.build/transform/gold_views.sql` (with `USE CATALOG`/`USE SCHEMA`) so views are created in the same catalog.schema and dashboards find them.

## Steps at a glance

| # | Step | Where | Action |
|---|------|--------|--------|
| 1 | Deploy bundle | CLI | `./scripts/deploy.sh dev` (or prepare dashboards, then validate, then deploy) |
| 2 | Data ingestion | App **Setup & Run** or Workflows | Run **Transaction Stream Simulator**; output `raw_payment_events` |
| 3 | ETL (Lakeflow) | App **Setup & Run** or Lakeflow | Start **Payment Analysis ETL** pipeline; Bronze → Silver → Gold |
| 4 | Gold views | App **Setup & Run** or Workflows | Run **Create Payment Analysis Gold Views**; verify `v_executive_kpis` |
| 5 | Lakehouse tables (SQL) | SQL Warehouse / Notebook | Run in order: `app_config.sql`, `vector_search_and_recommendations.sql`, `approval_rules.sql`, `online_features.sql` (same catalog/schema) |
| 6 | Train ML models | App **Setup & Run** or Workflows | Run **Train Payment Approval ML Models** (~10–15 min); 4 models in UC |
| 7 | Dashboards & app | — | 12 dashboards in bundle; app: `.env` + `uv run apx dev` or deploy |
| 8 | Model serving | After step 6 | Redeploy bundle (model_serving.yml) or already included |
| 9 | AI agents (optional) | Workflows | Run **Orchestrator** or other agents in `agents.yml`; Genie optional |
| 10 | Verify | App + Workspace | KPIs on **Dashboard**; **Rules**, **Decisioning**, **ML Models**; 4 models in UC. All jobs/pipelines have one-click Run and Open in **Setup & Run** (steps 1–7 and 6b; Quick links for Stream processor and Test Agent Framework). |

## Steps (detail)

| Step | Purpose | Action |
|------|---------|--------|
| **1** | Deploy bundle | Run `./scripts/deploy.sh dev` (or for prod: `./scripts/deploy.sh prod`). For manual steps: run `uv run python scripts/prepare_dashboards.py` (prod: add `--catalog`/`--schema`), then `databricks bundle validate -t dev` and `databricks bundle deploy -t dev`. |
| **2** | Generate data | **Setup & Run** → “Run simulator” or Workflows → “Transaction Stream Simulator”; output `raw_payment_events`. |
| **3** | Lakeflow ETL | **Setup & Run** → “Start ETL pipeline” or Lakeflow → “Payment Analysis ETL” → Start; Bronze → Silver → Gold. |
| **4** | Gold views | **Setup & Run** → “Run gold views job” or Workflows → “Create Payment Analysis Gold Views”; verify `v_executive_kpis` etc. |
| **5** | Lakehouse (SQL) | In SQL Warehouse or a notebook (same catalog/schema), run in order: (a) `app_config.sql` — single-row table for app catalog/schema (used by UI and all Lakehouse operations); (b) `vector_search_and_recommendations.sql` — Vector Search source + recommendations; (c) `approval_rules.sql` — Rules table for app + agents; (d) `online_features.sql` — Online features for ML/AI in the app. Scripts live in `src/payment_analysis/transform/`. |
| **6** | ML models | **Setup & Run** → “Run ML training” or Workflows → “Train Payment Approval ML Models”; ~10–15 min; registers 4 models in UC. |
| **7** | Dashboards & app | Bundle deploys 12 dashboards; warehouse from `var.warehouse_id`. App: set `.env` (DATABRICKS_HOST, TOKEN, WAREHOUSE_ID, and optionally DATABRICKS_CATALOG, DATABRICKS_SCHEMA for bootstrap); run locally with `uv run apx dev`, or deploy as a Databricks App (see **Deploy app as a Databricks App** below). Effective catalog/schema can be set in the UI via **Setup & Run** → **Save catalog & schema**. |
| **8** | Model serving | After step 6, model serving deploys with bundle (or redeploy). **ML Models** page in app shows catalog/schema models. |
| **9** | Genie / AI agents | Optional: Genie Spaces; run **Orchestrator** or other agent jobs from **Setup & Run** or Workflows. |
| **10** | Verify | **Dashboard**: KPIs, online features, decisions. **Rules**: add/edit rules (Lakehouse). **Decisioning**: recommendations + policy test. **ML Models**: list and links to Registry/MLflow. Workspace: bronze/silver data; 4 models in UC. |

## Deploy app as a Databricks App

The same app you run at **http://localhost:8000** (FastAPI + React UI) can be deployed to Databricks Apps via the bundle.

1. **Build** the frontend and wheel (so the app serves the UI):  
   `uv run apx build`
2. **Deploy** the bundle (this creates/updates the app in the workspace):  
   `./scripts/deploy.sh dev`  
   If deploy fails with *"The maximum number of apps for your workspace... is 200"*, delete unused apps in **Workspace → Apps** and redeploy.
3. **Run** the app and get the URL:
   - From the CLI: `databricks bundle run payment_analysis_app -t dev`
   - Or in the workspace: **Apps** → find **payment-analysis** → open and start the app.
4. **App URL** is shown after starting (e.g. `https://<workspace-host>/apps/payment-analysis?o=...`). You can also run `databricks bundle summary -t dev` to see the app and its URL.

The app resource is defined in `resources/app.yml`; runtime is configured in `app.yaml` (uvicorn, PYTHONPATH=src). Python dependencies for the Apps container are in `requirements.txt` at the project root (Databricks installs these during app deployment).

## Schema Consistency

Use one catalog/schema everywhere (defaults: `ahs_demos_catalog`, `ahs_demo_payment_analysis_dev`). Bundle: `var.catalog`, `var.schema`; backend: bootstrap from `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA` (used to locate the `app_config` table). The **effective** catalog/schema for all app operations (analytics, rules, ML, agents) is read from the Lakehouse `app_config` table at startup; you can change it via **Setup & Run** → **Save catalog & schema** (`PATCH /api/setup/config`). See [4_TECHNICAL](4_TECHNICAL.md) (“Catalog and schema (app_config)”).

## Will I see all resources in my workspace?

**Yes, if you follow the steps and deploy succeeds.** The bundle deploys:

- **Workspace** folder and synced files (notebooks, transform SQL) under **Workspace → Users → &lt;you&gt; → payment-analysis** (`var.workspace_folder`)
- **Lakebase** (managed Postgres) instance + UC catalog for app rules/experiments/incidents; set app env **PGAPPNAME** to the instance name (e.g. `payment-analysis-db`)
- **Workflow (Jobs):** simulator, gold views, ML training, test agent, 6 AI agents, stream processor, Genie sync
- **Lakeflow:** 2 pipelines (ETL, real-time)
- **SQL** warehouse, **Unity Catalog** (schema + volumes), **12 dashboards**, **Databricks App**
- **Model serving** (4 endpoints) when models exist in UC (run Step 6 first)

**Model serving** can fail until you run **Step 6** (Train Payment Approval ML Models) so the 4 models exist in Unity Catalog. If deploy fails at model serving, comment out `resources/model_serving.yml` in `databricks.yml`, run `./scripts/deploy.sh dev` again, then run Step 6 and redeploy to add model serving.

**Vector Search** is not in the bundle schema; create the endpoint and index manually from `resources/vector_search.yml` (Vector Search UI or API) after running `vector_search_and_recommendations.sql`.

## Where to find resources in the workspace

After a **successful** `./scripts/deploy.sh dev` (or equivalent deploy), look for:

- **Workspace:** **Workspace** → **Users** → your user → **payment-analysis** (files, dashboards folder; from `var.workspace_folder`).
- **Jobs:** **Workflow** (Jobs) → names like `[dev …] Train Payment Approval ML Models`, `[dev …] Transaction Stream Simulator`. Agent jobs (Orchestrator, Smart Routing, etc.) are defined in `resources/agents.yml`.
- **Mosaic AI Gateway:** Governed LLM access is configured on the four custom endpoints in `model_serving.yml` (rate limits, usage tracking, guardrails). For pay-per-token LLM endpoints, enable AI Gateway in **Serving** → endpoint → **Edit AI Gateway**. See [AI Gateway docs](https://docs.databricks.com/aws/en/ai-gateway/).
- **Lakeflow:** **Lakeflow** → `[dev] Payment Analysis ETL`, `[dev] Payment Real-Time Stream`.
- **SQL Warehouse:** **SQL** → **Warehouses** → `[dev] Payment Analysis Warehouse`.
- **Catalog (Lakehouse database):** **Data** (Catalog Explorer) → **Catalogs** → `ahs_demos_catalog` → schema `ahs_demo_payment_analysis_dev`. Tables, views, and volumes appear under the schema.
- **Dashboards:** **SQL** → **Dashboards** (or under the workspace folder above). After deploy, run `uv run python scripts/publish_dashboards.py` to publish all 12 dashboards (embed credentials).

If deploy **failed** (e.g. at model serving), some resources will be missing. Comment out `model_serving.yml` in `databricks.yml` and run `./scripts/deploy.sh dev` again. Confirm workspace path with `./scripts/validate_bundle.sh dev`.

**Dashboard TABLE_OR_VIEW_NOT_FOUND:** Dashboards use tables/views in the catalog.schema chosen when you ran `prepare_dashboards.py`. Run **Create Payment Analysis Gold Views** in that same catalog.schema (the job uses `.build/transform/gold_views.sql`, which sets `USE CATALOG`/`USE SCHEMA`). List required assets: `uv run python scripts/validate_dashboard_assets.py --catalog X --schema Y`.

## Troubleshooting

| Issue | Actions |
|-------|---------|
| Don't see resources | Redeploy after commenting out `model_serving.yml` if deploy failed; check workspace path with `./scripts/validate_bundle.sh dev`. |
| Lakebase "Instance name is not unique" | A Lakebase instance with that name already exists in the workspace, or one is still starting. Use a different instance name in bundle vars or wait and retry. |
| Lakeflow fails | Pipeline logs; confirm `raw_payment_events`; UC permissions; `pipelines reset` if needed |
| Dashboards empty | Gold views + data; warehouse running; warehouse_id in config |
| ML training fails | Silver data; ML runtime; UC model registry; MLflow logs |
| App won’t start | Ports 8000/5173; `uv sync`, `bun install`; `.env` |

## Scripts

- **deploy.sh** — Runs `prepare_dashboards.py` then `databricks bundle deploy -t <target>`. Use for full deploy so `.build/dashboards` exists and dashboard paths are valid.
- **validate_bundle.sh** — Runs `prepare_dashboards.py` (with optional prod catalog/schema), then `databricks bundle validate -t <target>`. Use before deploy to verify the bundle.
- **verify_all.sh** — Runs lint (apx dev check), build, backend smoke test, dashboard assets list, and bundle validate. Use before committing or deploying.
- **prepare_dashboards.py** — Copies dashboard JSONs to `.build/dashboards/` and writes `.build/transform/gold_views.sql` with catalog/schema. Run by deploy.sh and validate_bundle.sh; for prod use `--catalog`/`--schema`.
- **publish_dashboards.py** — After deploy, publishes all 12 dashboards in the workspace with embed credentials. Run: `uv run python scripts/publish_dashboards.py` (optional `--path` if bundle path differs).

**Estimated time:** 45–60 min.
