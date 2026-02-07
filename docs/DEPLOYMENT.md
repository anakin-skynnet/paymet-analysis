# Deployment

Step-by-step deployment for **Payment Analysis**. **One-click run links:** [Demo setup & one-click run](#demo-setup--one-click-run) below.

## Prerequisites

Databricks workspace (Unity Catalog), SQL Warehouse, CLI configured. Python 3.10+ with `uv`, Node 18+ with `bun`. Databricks App Node runtime is 22.16; `package.json` engines should target it (e.g. `>=22.0.0`). Permissions: jobs, **Lakeflow**, model serving; write to `ahs_demos_catalog`; deploy to `/Workspace/Users/<your_email>/payment-analysis` (or `var.workspace_folder`). **Databricks App:** You cannot install system-level packages (e.g. `apt-get`, Conda); only dependencies in `requirements.txt` and `package.json` are used. See [TECHNICAL](TECHNICAL.md) (Databricks App compatibility).

## Quick Start

**Before every deploy** (so dashboards and the Gold Views job use the same catalog/schema):

```bash
./scripts/bundle.sh validate dev    # dev: prepares .build/dashboards and .build/transform, then validates
# or: uv run python scripts/dashboards.py prepare   then  databricks bundle validate -t dev
databricks bundle deploy -t dev
```

For prod with different catalog/schema, run `./scripts/bundle.sh validate prod` (prepares with prod catalog/schema). Then run jobs/pipelines per [Demo setup](#demo-setup--one-click-run) below. Dashboards read from `.build/dashboards/`; the **Create Gold Views** job runs `.build/transform/gold_views.sql` (with `USE CATALOG`/`USE SCHEMA`) so views are created in the same catalog.schema and dashboards find them.

## Steps at a glance

| # | Step | Where | Action |
|---|------|--------|--------|
| 1 | Deploy bundle | CLI | `./scripts/bundle.sh deploy dev` (or prepare dashboards, then validate, then deploy) |
| 2 | Data ingestion | App **Setup & Run** or Workflows | Run **Transaction Stream Simulator**; output `raw_payment_events` |
| 3 | ETL (Lakeflow) | App **Setup & Run** or Lakeflow | Start **Payment Analysis ETL** pipeline; Bronze → Silver → Gold |
| 4 | Gold views | App **Setup & Run** or Workflows | Run **Create Payment Analysis Gold Views**; verify `v_executive_kpis` |
| 5 | Lakehouse tables (SQL) | SQL Warehouse / Notebook | Run `lakehouse_bootstrap.sql` (same catalog/schema as gold views). Creates app_config, recommendations, approval_rules, online_features. |
| 6 | Train ML models | App **Setup & Run** or Workflows | Run **Train Payment Approval ML Models** (~10–15 min); 4 models in UC |
| 7 | Dashboards & app | — | 12 dashboards in bundle; app: deploy as Databricks App (see below) |
| 8 | Model serving | After step 6 | Redeploy bundle (model_serving.yml) or already included |
| 9 | AI agents (optional) | Workflows | Run **Orchestrator** or other agents in `agents.yml`; Genie optional |
| 10 | Verify | App + Workspace | KPIs on **Dashboard**; **Rules**, **Decisioning**, **ML Models**; 4 models in UC. All jobs/pipelines have one-click Run and Open in **Setup & Run** (steps 1–7 and 6b; Quick links for Stream processor and Test Agent Framework). |

## Steps (detail)

| Step | Purpose | Action |
|------|---------|--------|
| **1** | Deploy bundle | Run `./scripts/bundle.sh deploy dev` (or for prod: `./scripts/bundle.sh deploy prod`). For manual steps: run `uv run python scripts/dashboards.py prepare` (prod: add `--catalog`/`--schema`), then `databricks bundle validate -t dev` and `databricks bundle deploy -t dev`. |
| **2** | Generate data | **Setup & Run** → “Run simulator” or Workflows → “Transaction Stream Simulator”; output `raw_payment_events`. |
| **3** | Lakeflow ETL | **Setup & Run** → “Start ETL pipeline” or Lakeflow → “Payment Analysis ETL” → Start; Bronze → Silver → Gold. |
| **4** | Gold views | **Setup & Run** → “Run gold views job” or Workflows → “Create Payment Analysis Gold Views”; verify `v_executive_kpis` etc. |
| **5** | Lakehouse (SQL) | In SQL Warehouse or a notebook (same catalog/schema), run `lakehouse_bootstrap.sql` from `src/payment_analysis/transform/`. Creates app_config, transaction_summaries_for_search, approval_recommendations, approval_rules, online_features and their views. Enables Rules, Decisioning recommendations, and Dashboard features. |
| **6** | ML models | **Setup & Run** → “Run ML training” or Workflows → “Train Payment Approval ML Models”; ~10–15 min; registers 4 models in UC. |
| **7** | Dashboards & app | Bundle deploys 12 dashboards; warehouse from `var.warehouse_id`. Deploy the app as a Databricks App (see **Deploy app as a Databricks App** below). Effective catalog/schema can be set in the UI via **Setup & Run** → **Save catalog & schema**. |
| **8** | Model serving | After step 6, model serving deploys with bundle (or redeploy). **ML Models** page in app shows catalog/schema models. |
| **9** | Genie / AI agents | Optional: Genie Spaces; run **Orchestrator** or other agent jobs from **Setup & Run** or Workflows. |
| **10** | Verify | **Dashboard**: KPIs, online features, decisions. **Rules**: add/edit rules (Lakehouse). **Decisioning**: recommendations + policy test. **ML Models**: list and links to Registry/MLflow. Workspace: bronze/silver data; 4 models in UC. |

## Deploy app as a Databricks App

The app (FastAPI + React) is deployed to Databricks Apps via the bundle.

1. **Build** the frontend and wheel (so the app serves the UI):  
   `uv run apx build`
2. **Deploy** the bundle (this creates/updates the app in the workspace):  
   `./scripts/bundle.sh deploy dev`  
   If deploy fails with *"The maximum number of apps for your workspace... is 200"*, delete unused apps in **Workspace → Apps** and redeploy.
3. **Run** the app and get the URL:
   - From the CLI: `databricks bundle run payment_analysis_app -t dev`
   - Or in the workspace: **Apps** → find **payment-analysis** → open and start the app.
4. **App URL** is shown after starting (e.g. `https://<workspace-host>/apps/payment-analysis?o=...`). You can also run `databricks bundle summary -t dev` to see the app and its URL.
5. **Required app configuration (Workspace → Apps → payment-analysis → Edit → Environment):**
   | Variable | Purpose | Example / note |
   |----------|---------|----------------|
   | **PGAPPNAME** | Lakebase instance for rules, experiments, incidents, ML features | `payment-analysis-db-dev` (dev). Without this, Rules/Experiments/Incidents and ML features return 503. |
   | **DATABRICKS_HOST** | Workspace URL for Dashboard links, Agents, Genie, Setup & Run one-click links | Your workspace URL (e.g. `https://adb-xxx.11.azuredatabricks.net`). Backend uses this for `/api/setup/defaults` (workspace_host) and agent workspace URLs. |
   | **DATABRICKS_WAREHOUSE_ID** | SQL Warehouse for analytics, app_config, gold views | From bundle: run `databricks bundle summary -t dev` and use the SQL Warehouses URL id, or set in target. |
   | **DATABRICKS_TOKEN** | API access (run job, pipeline, read app_config); may be auto-provided by the platform per request | If the app uses OAuth, the platform may inject token via headers; otherwise set a PAT. |
   With these set, **Dashboard** (12 dashboards), **AI Agents**, **Genie** links, and **Setup & Run** one-click actions work as expected.

6. **Optional — override Setup & Run resource IDs (after deploying to a new workspace):** Job and pipeline IDs are workspace-specific. The app uses built-in defaults; to point **Setup & Run** at your deployed resources, set these env vars. Get IDs from **Workspace → Workflows** (jobs) and **Lakeflow** (pipelines), or from `databricks bundle summary -t dev`.

   | Variable | Purpose |
   |----------|---------|
   | **DATABRICKS_WORKSPACE_ID** | Workspace ID for dashboard embed URLs (query param `o`). Optional; if set, embed links work in iframes. |
   | **DATABRICKS_JOB_ID_TRANSACTION_STREAM_SIMULATOR** | Job ID for Transaction Stream Simulator |
   | **DATABRICKS_JOB_ID_CREATE_GOLD_VIEWS** | Job ID for Create Payment Analysis Gold Views |
   | **DATABRICKS_JOB_ID_TRAIN_ML_MODELS** | Job ID for Train Payment Approval ML Models |
   | **DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT** | Job ID for Orchestrator Agent |
   | **DATABRICKS_JOB_ID_SMART_ROUTING_AGENT** | Job ID for Smart Routing Agent |
   | **DATABRICKS_JOB_ID_SMART_RETRY_AGENT** | Job ID for Smart Retry Agent |
   | **DATABRICKS_JOB_ID_RISK_ASSESSOR_AGENT** | Job ID for Risk Assessor Agent |
   | **DATABRICKS_JOB_ID_DECLINE_ANALYST_AGENT** | Job ID for Decline Analyst Agent |
   | **DATABRICKS_JOB_ID_PERFORMANCE_RECOMMENDER_AGENT** | Job ID for Performance Recommender Agent |
   | **DATABRICKS_JOB_ID_CONTINUOUS_STREAM_PROCESSOR** | Job ID for Continuous Stream Processor |
   | **DATABRICKS_JOB_ID_TEST_AGENT_FRAMEWORK** | Job ID for Test AI Agent Framework |
   | **DATABRICKS_PIPELINE_ID_PAYMENT_ANALYSIS_ETL** | Pipeline ID for Payment Analysis ETL |
   | **DATABRICKS_PIPELINE_ID_PAYMENT_REALTIME_PIPELINE** | Pipeline ID for Payment Real-Time Stream |

**How the app uses deployed resources:** The bundle deploys jobs, Lakebase, pipelines, SQL warehouse, Genie sync job, dashboards, and the app. The app is *configured* to run jobs, connect to the database, open Genie, and use those resources only when the environment variables above are set. Job/pipeline IDs come from backend defaults or env overrides; after deploying to a new workspace, set warehouse and optionally job/pipeline IDs to match. See [TECHNICAL](TECHNICAL.md).

The app resource is defined in `resources/app.yml`; runtime is configured in **`app.yaml`** at project root (block-sequence `command` and `env`; uvicorn, PYTHONPATH=src, PGAPPNAME). Python dependencies for the Apps container are in `requirements.txt`. App runtime format follows [Configure app execution (app.yaml)](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/app-runtime) and [FastAPI — Databricks Apps Cookbook](https://apps-cookbook.dev/docs/fastapi/getting_started/create).

## Schema Consistency

Use one catalog/schema everywhere (defaults: `ahs_demos_catalog`, `ahs_demo_payment_analysis_dev`). Bundle: `var.catalog`, `var.schema`; backend: bootstrap from `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA` (used to locate the `app_config` table). The **effective** catalog/schema for all app operations is read from the Lakehouse `app_config` table at startup; you can change it via **Setup & Run** → **Save catalog & schema** (`PATCH /api/setup/config`). See [TECHNICAL](TECHNICAL.md) (“Catalog and schema (app_config)”).

## Will I see all resources in my workspace?

**Yes.** By default the bundle deploys (without model serving so deploy succeeds; Lakebase is included):

- **Workspace** folder and synced files under **Workspace → Users → &lt;you&gt; → payment-analysis** (`var.workspace_folder`)
- **Lakebase** (required for UI CRUD and ML features): instance name in dev is `payment-analysis-db-dev`. Set app env **PGAPPNAME** to this name in **Workspace → Apps** → app → Edit → Environment.
- **Workflow (Jobs):** simulator, gold views, ML training, test agent, 6 AI agents, stream processor, Genie sync
- **Lakeflow:** 2 pipelines (ETL, real-time)
- **SQL** warehouse, **Unity Catalog** (schema + volumes), **12 dashboards**, **Databricks App**

**Optional — enable after deploy:**

| Resource | How to enable |
|----------|----------------|
| **Model serving** (4 endpoints) | Run **Step 6** (Train Payment Approval ML Models) so the 4 models exist in UC. Then in `databricks.yml`, uncomment `resources/model_serving.yml` and run `./scripts/bundle.sh deploy dev` again. |

**Vector Search** is not in the bundle schema; create the endpoint and index manually from `resources/vector_search.yml` after running `lakehouse_bootstrap.sql`.

## Verify app configuration

After deploying the app and setting the required environment variables, confirm: **Dashboard** opens Databricks dashboards; **AI Agents** and **Genie** links use workspace URL; **Setup & Run** shows job/pipeline links and Run buttons (requires DATABRICKS_HOST). **Rules / Experiments / Incidents** require **PGAPPNAME**. **Catalog/schema** is set via **Setup & Run** → **Save catalog & schema** after running `lakehouse_bootstrap.sql`.

## Where to find resources in the workspace

- **Workspace:** **Workspace** → **Users** → your user → **payment-analysis**.
- **Jobs:** **Workflow** (Jobs) → names like `[dev …] Train Payment Approval ML Models`, `[dev …] Transaction Stream Simulator`.
- **Lakeflow:** **Lakeflow** → `[dev] Payment Analysis ETL`, `[dev] Payment Real-Time Stream`.
- **SQL Warehouse:** **SQL** → **Warehouses** → `[dev] Payment Analysis Warehouse`.
- **Catalog:** **Data** → **Catalogs** → `ahs_demos_catalog` → schema `ahs_demo_payment_analysis_dev`.
- **Dashboards:** **SQL** → **Dashboards**. Optional: `uv run python scripts/dashboards.py publish` to publish all 12 with embed credentials.

**Dashboard TABLE_OR_VIEW_NOT_FOUND:** Run **Create Payment Analysis Gold Views** in the same catalog.schema used by `dashboards.py prepare`. List required assets: `uv run python scripts/dashboards.py validate-assets --catalog X --schema Y`.

## Troubleshooting

| Issue | Actions |
|-------|---------|
| **Database instance is in STARTING state** | Wait a few minutes and redeploy. |
| Don't see resources | Redeploy after commenting out `model_serving.yml` if deploy failed; check path with `./scripts/bundle.sh validate dev`. |
| **Registered model does not exist** | Run **Step 6** (Train ML Models); then uncomment `resources/model_serving.yml` and redeploy. |
| Lakebase "Instance name is not unique" | Use unique `lakebase_instance_name` via `--var` or target variables. |
| **Error deploying app: error installing packages** | Ensure TanStack packages are **1.158.1** with **overrides** in `package.json`; use `bun.lock` only. See [TECHNICAL](TECHNICAL.md) (Databricks Apps package compatibility). |
| **Error deploying app: error loading app spec from app.yml** | Ensure **`app.yaml`** exists at project root with block-sequence `command` and `env`. If the runtime looks for `app.yml`, add a copy with the same content. Redeploy after changes. See [App spec error](#app-spec-error) below. |

## App spec error

If you see **"error loading app spec from app.yml"**: the Apps runtime loads the run spec from the **deployed app root**. Use **`app.yaml`** at project root (block-sequence `command` and `env`). Docs allow `.yaml` or `.yml`; some runtimes look for `app.yml` first — if the error persists, add **`app.yml`** with the same content as `app.yaml`. No conflict with **`resources/app.yml`** (bundle resource, different purpose). After editing, run `./scripts/bundle.sh deploy dev` so the updated file is uploaded.

## Scripts

- **bundle.sh** — `./scripts/bundle.sh deploy [dev|prod]` (prepare dashboards then deploy). `./scripts/bundle.sh validate [dev|prod]`. `./scripts/bundle.sh verify [dev|prod]` (build, backend smoke test, dashboard assets, bundle validate).
- **dashboards.py** — **prepare** (run by bundle.sh); **validate-assets** (list required tables/views); **publish** (optional): `uv run python scripts/dashboards.py publish`.

## Demo setup & one-click run

**Recommended order:** (1) Deploy bundle — `./scripts/bundle.sh deploy dev`; (2) Data ingestion — Transaction Stream Simulator; (3) ETL — Payment Analysis ETL pipeline; (4) Gold views — Create Payment Analysis Gold Views job; (5) Lakehouse SQL — run `lakehouse_bootstrap.sql` (see `src/payment_analysis/transform/`); (6) Train ML models; (7–8) Optional: real-time pipeline, AI agents.

**Quick links:** Get job/pipeline IDs from **Workflows** / **Lakeflow**. Run simulator: `<WORKSPACE_URL>/#job/<JOB_ID>/run`; ETL: `<WORKSPACE_URL>/pipelines/<PIPELINE_ID>`. **CLI:** `databricks bundle run <job_name> -t dev`.

**Estimated time:** 45–60 min.

---

**See also:** [OVERVIEW](OVERVIEW.md) · [TECHNICAL](TECHNICAL.md)
