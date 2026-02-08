# Deployment Guide

How to deploy and configure the Payment Analysis app and bundle (Databricks Apps, Lakebase, jobs, dashboards).

## Prerequisites

Databricks workspace (Unity Catalog), SQL Warehouse, CLI configured. Python 3.10+ with `uv`, Node 18+ with `bun`. `package.json` engines `>=22.0.0`. Permissions: jobs, Lakeflow, model serving; write to catalog; deploy to `/Workspace/Users/<you>/payment-analysis`. **Databricks App:** Only `requirements.txt` and `package.json` deps; no system packages. See [Architecture & reference](ARCHITECTURE_REFERENCE.md#databricks-app-deploy).

## Quick start

One command deploys the bundle and generates all required files (dashboards and SQL for jobs):

```bash
./scripts/bundle.sh deploy dev
```

This runs **prepare** (writes `.build/dashboards/` and `.build/transform/gold_views.sql` + `lakehouse_bootstrap.sql` with catalog/schema) then deploys. After deploy, run steps 1–10 from the app **Setup & Run** in order. To validate without deploying: `./scripts/bundle.sh validate dev`.

## Steps at a glance

Execution order is **logical**: foundation first (Lakehouse, Vector Search, gold views, simulator), then optional real-time streaming, then ingestion ETL, ML, Genie, agents, and dashboards.

| # | Step | Action |
|---|------|--------|
| 1 | Deploy bundle | `./scripts/bundle.sh deploy dev` (includes prepare; no missing files) |
| 2 | Lakehouse bootstrap | **Setup & Run** → Run **Lakehouse Bootstrap** (app_config, rules, recommendations; run once) |
| 3 | Vector Search index | **Setup & Run** → Run **Create Vector Search Index** (similar-transaction lookup; run after bootstrap) |
| 4 | Gold views | **Setup & Run** → Run **Create Gold Views** (data repos / analytical views) |
| 5 | Events producer | **Setup & Run** → Run **Transaction Stream Simulator** (produces streaming data) |
| 6 | Optional streaming | **Setup & Run** → Start **Real-time** pipeline and/or **Continuous stream processor** |
| 7 | Ingestion ETL | **Setup & Run** → Start **Payment Analysis ETL** pipeline (Bronze → Silver → Gold, feeds Vector Search) |
| 8 | ML models | **Setup & Run** → Run **Train Payment Approval ML Models** (~10–15 min); registers in Unity Catalog |
| 9 | Genie space | **Setup & Run** → Run **Genie Space Sync** (create/prepare Genie space) |
| 10 | AI agents | **Setup & Run** → Run **Orchestrator** and specialist agents |
| 11 | Publish dashboards | **Setup & Run** → Run **Publish Dashboards** (embed credentials so app can embed Lakeview) |
| — | Dashboards & app | 12 dashboards + app deployed by bundle |
| — | Model serving | After step 8 (ML): uncomment `resources/model_serving.yml`, redeploy |
| — | Verify | **Dashboard**, **Rules**, **Decisioning**, **ML Models** in app |

All jobs and pipelines can be run from the UI. To connect: use your credentials (open app from **Compute → Apps**) or set **DATABRICKS_TOKEN** (PAT) in the app environment. When you open the app from Compute → Apps (or with PAT set), the Setup & Run page resolves job and pipeline IDs from the workspace by name so you can run steps without setting `DATABRICKS_JOB_ID_*` / `DATABRICKS_PIPELINE_ID_*`. See **Setup & Run → Connect to Databricks**.

## Deploy app as a Databricks App

**Deploy into Databricks App** (create/update the app in the workspace and make the UI available):

1. **Deploy bundle:** Run `./scripts/bundle.sh deploy dev`. This runs prepare (generates `.build/dashboards/`, `.build/transform/gold_views.sql`, `.build/transform/lakehouse_bootstrap.sql`), builds the UI (`uv run apx build` via `artifacts.default.build`), and deploys. All job SQL files exist after deploy.
3. **Start the app:** In the workspace go to **Compute → Apps → payment-analysis → Start**, or run `databricks bundle run payment_analysis_app -t dev`. The app runs in Databricks (not on your machine). Logs showing **"Uvicorn running on http://0.0.0.0:8000"** are expected: the app binds to that address inside the container and the Databricks platform proxies external traffic to it.
4. **App URL:** Open the app from the Apps page or use the URL from **databricks bundle summary**.
5. **Required env (Workspace → Apps → payment-analysis → Edit → Environment):**

| Variable | Purpose |
|----------|---------|
| **PGAPPNAME** | Required. Lakebase instance (e.g. `payment-analysis-db-dev`). |
| **DATABRICKS_WAREHOUSE_ID** | Required for SQL/analytics. SQL Warehouse ID (from bundle or sql-warehouse binding). |
| **DATABRICKS_HOST** | Optional when opened from **Compute → Apps** (workspace URL derived from request). Set when not using OBO. |
| **DATABRICKS_TOKEN** | Optional when using OBO. Open from **Compute → Apps** so your token is forwarded; do not set in env. Set only for app-only use; then do **not** set DATABRICKS_CLIENT_ID/SECRET. |
| **LAKEBASE_SCHEMA** | Optional. Postgres schema for app tables (default `app`). Use when the app has no CREATE on `public`. |

**Use your credentials (recommended):** Open the app from **Workspace → Compute → Apps → payment-analysis**. The platform forwards your token; no DATABRICKS_TOKEN or DATABRICKS_HOST is required in the app environment. The app then uses that logged-in user token for all Databricks resources (SQL Warehouse, jobs, dashboards). The main page shows “Use your Databricks credentials” when no token is present; open the workspace to sign in. Enable user authorization (OBO) and add scopes **sql**, **Jobs**, and **Pipelines** (if needed) in **Edit → Configure → Authorization scopes**. If you see 403 Invalid scope, add **sql** and restart. If Run stays disabled, click **Refresh job IDs** on the Setup page.

6. **Optional — override job/pipeline IDs:** Set `DATABRICKS_JOB_ID_*`, `DATABRICKS_PIPELINE_ID_*`, `DATABRICKS_WORKSPACE_ID` per [Architecture & reference](ARCHITECTURE_REFERENCE.md#workspace-components--ui-mapping).

App resource: `resources/fastapi_app.yml`. Runtime spec: `app.yml` at project root. See [App spec error](#app-spec-error).

## App configuration and resource paths

**Bundle root:** Directory containing `databricks.yml`. **App source:** `source_code_path` in `resources/fastapi_app.yml` is `${workspace.file_path}` (e.g. `.../payment-analysis/files`), i.e. the folder where bundle sync uploads files. The app runs from that folder so `src/payment_analysis/__dist__` is found for the web UI.

**Included resources** (order in `databricks.yml`): `unity_catalog`, `lakebase`, `pipelines`, `sql_warehouse`, `ml_jobs`, `agents`, `streaming_simulator`, `genie_spaces`, `dashboards`, `fastapi_app`. Optional: `model_serving` (uncomment after training models).

**Paths:**  
- Workspace root: `/Workspace/Users/${user}/${var.workspace_folder}` (default folder: `payment-analysis`).  
- Notebooks/jobs: `${workspace.file_path}/src/payment_analysis/...` (e.g. `ml/train_models`, `streaming/transaction_simulator`, `agents/agent_framework`).  
- SQL for jobs: `${workspace.file_path}/.build/transform/gold_views.sql` and `lakehouse_bootstrap.sql` (both generated by `scripts/dashboards.py prepare` with USE CATALOG/SCHEMA).  
- Dashboards: `file_path` in `resources/dashboards.yml` is `../.build/dashboards/*.lvdash.json` (relative to `resources/`).  
- Sync (uploaded to workspace): `.build`, `src/payment_analysis/ml`, `streaming`, `transform`, `agents`, `genie`.

**App bindings:** database (Lakebase), sql-warehouse (`payment_analysis_warehouse`), jobs in execution order (lakehouse bootstrap, Vector Search, gold views, simulator, optional streaming, ETL, train ML, genie sync, agents, publish dashboards). Optional: genie-space, model serving endpoints (see comments in `fastapi_app.yml`).

Validate before deploy: `./scripts/bundle.sh validate dev` (runs dashboard prepare then `databricks bundle validate`).

**Version alignment:** All dependency references use **exactly the same versions** everywhere (no ranges). See **[VERSION_ALIGNMENT.md](VERSION_ALIGNMENT.md)** for the full table and Databricks App compatibility. Python: `pyproject.toml` (pinned `==`) → `uv.lock` → `requirements.txt` via `scripts/sync_requirements_from_lock.py`. Frontend: `package.json` has exact versions only (no `^`); `bun.lock` holds resolved versions. **Databricks App runtime:** Python 3.11, Node.js 22.16; the pinned versions in this repo are compatible. After changing `pyproject.toml` run `uv lock` then `uv run python scripts/sync_requirements_from_lock.py`. After changing `package.json` run `uv run apx bun install`. If you see "error installing packages" on deploy, check **Compute → Apps → your app → Logs** for the exact `pip` error.

**Version verification (same versions everywhere):**

| Stack | Source of truth | Generated / lock | Aligned? |
|-------|-----------------|------------------|----------|
| Python app | `pyproject.toml` (pinned `==`) | `uv.lock` → `requirements.txt` via `scripts/sync_requirements_from_lock.py` | Yes: direct deps (databricks-sdk 0.84.0, fastapi 0.128.0, uvicorn 0.40.0, pydantic-settings 2.6.1, sqlmodel 0.0.27, psycopg 3.2.3) match in all three. |
| Frontend | `package.json` (exact versions, no `^`) | `bun.lock` | Yes: all deps pinned to exact versions (e.g. vite 7.3.1, react 19.2.3) matching `bun.lock`. |
| Runtime | `.python-version` = 3.11 | `pyproject.toml` `requires-python = ">=3.11"` | Yes. |
| Jobs/Pipelines | N/A (Spark/Lakeflow) | `resources/*.yml` use `spark_version` (e.g. 15.4.x) for clusters only; not app deps. | N/A. |

## Schema consistency

One catalog/schema (defaults: `ahs_demos_catalog`, `payment_analysis`). Effective catalog/schema from Lakehouse `app_config`; set via **Setup & Run** → **Save catalog & schema**. See [Architecture & reference](ARCHITECTURE_REFERENCE.md#catalog-and-schema-verification).

## Resources in the workspace

By default: Workspace folder, Lakebase, Jobs (lakehouse bootstrap, Vector Search, gold views, simulator, optional streaming, ETL, ML, Genie sync, agents, publish dashboards), 2 pipelines, SQL warehouse, Unity Catalog, 12 dashboards, Databricks App. **Optional:** Uncomment `resources/model_serving.yml` after Step 8 (ML training); create Vector Search manually from `resources/vector_search.yml`.

## Where to find resources

- **Workspace:** **Workspace** → **Users** → you → **payment-analysis**
- **Jobs:** **Workflow** → `[dev …]` job names
- **Lakeflow:** **Lakeflow** → ETL and Real-Time Stream
- **SQL Warehouse:** **SQL** → **Warehouses**
- **Catalog / Dashboards:** **Data** → Catalogs; **SQL** → **Dashboards**

**Dashboard TABLE_OR_VIEW_NOT_FOUND:** Run **Create Gold Views** (and **Lakehouse Bootstrap** if Rules/Decisioning are empty) in the same catalog.schema as prepare. Validate: `uv run python scripts/dashboards.py validate-assets --catalog X --schema Y`.

## Databricks Apps compatibility

**Environment (official):** Python 3.11, Ubuntu 22.04 LTS, Node.js 22.16. [Pre-installed Python libraries](https://docs.databricks.com/en/dev-tools/databricks-apps/system-env#pre-installed-python-libraries) include:

| Library | Pre-installed version |
|---------|------------------------|
| databricks-sdk | 0.33.0 |
| fastapi | 0.115.0 |
| uvicorn[standard] | 0.30.6 |
| (others) | streamlit, dash, flask, etc. |

**Our `requirements.txt`:** Overrides three pre-installed packages (databricks-sdk → 0.84.0, fastapi → 0.128.0, uvicorn → 0.40.0) and adds pydantic-settings, sqlmodel, psycopg[binary] plus transitive pins. Overriding is supported; pinning exact versions in `requirements.txt` is recommended by Databricks. Our overrides are within the same major/minor line and are tested.

**If you see "error installing packages":**

1. **Check the real error:** **Compute → Apps → your app → Logs** (or **Environment** tab) for the exact `pip` or install failure.
2. Regenerate from lock:
   ```bash
   uv run python scripts/sync_requirements_from_lock.py
   ```
   then redeploy.

**Supported and compatible:** Databricks App system environment uses **Python 3.11** and **Node.js 22.16**. Our `.python-version` (3.11) and `package.json` `engines.node` (>=22.0.0) are compatible. All Python packages in `requirements.txt` use exact versions and have manylinux-compatible wheels or are pure Python. We use `psycopg[binary]` so the app has a working PostgreSQL driver without the system libpq (not in the container). `requirements.txt` is generated from `uv.lock` by `scripts/sync_requirements_from_lock.py`; do not edit by hand.

## Why the web UI was not found (references: apps-cookbook, apx, ai-dev-kit)

**Root cause:** The app runs from a **working directory** that must be the same place where the bundle **sync** uploaded your code and the built UI. Per [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/settings) and [apx](https://github.com/databricks-solutions/apx):

- **Sync** uploads to **`workspace.file_path`** (default: `.../payment-analysis/files`), not the bundle root.
- If the app’s **`source_code_path`** pointed to the parent folder (`.../payment-analysis`), the process **cwd** was that parent, so `src/payment_analysis/__dist__` was not under cwd and the UI build was not found.
- [Apps Cookbook](https://apps-cookbook.dev/docs/intro) and [ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit) use the same idea: the app must run from the folder that contains the deployed files (including the built frontend).

**Fix applied in this repo:**

1. **`source_code_path`** in `resources/fastapi_app.yml` is set to **`${workspace.file_path}`** so the app runs from the same path where sync uploads (the `files/` subfolder).
2. **`workspace.file_path`** in `databricks.yml` is set explicitly to `.../${var.workspace_folder}/files` so it matches the sync destination.
3. **Build before deploy:** `artifacts.default.build: uv run apx build` creates `src/payment_analysis/__dist__`; **`sync.include`** lists `src/payment_analysis/__dist__` so it is uploaded even though it’s in `.gitignore`.
4. At runtime the app tries several path candidates (including `cwd/src/payment_analysis/__dist__` and `cwd/files/...`) and logs **"UI dist candidate"** in app Logs for diagnostics.

After any change to the app or bundle config, **redeploy** and **restart** the app so the new paths and files are used.

## Troubleshooting

| Issue | Action |
|-------|--------|
| Database instance STARTING | Wait, then redeploy |
| Don't see resources | Redeploy; run `./scripts/bundle.sh validate dev` |
| Registered model does not exist | Run Step 8 (Train ML models), then uncomment `model_serving.yml`, redeploy |
| Lakebase "Instance name is not unique" | Use unique `lakebase_instance_name` via `--var` or target |
| Error installing packages (app deploy) | Check **Logs** for the exact pip error. Ensure `requirements.txt` is up to date: run `uv lock` then `uv run python scripts/sync_requirements_from_lock.py`. See [Databricks Apps compatibility](#databricks-apps-compatibility). |
| **permission denied for schema public** | App tables use schema `app` by default. Set **LAKEBASE_SCHEMA** (e.g. `app`) in the app environment if needed; the app creates the schema if it has permission. |
| **Databricks credentials not configured; cannot update app_config** | Either enable **user authorization (OBO)** and open the app from Compute → Apps (so your token is used), or set **DATABRICKS_HOST**, **DATABRICKS_WAREHOUSE_ID**, and optionally **DATABRICKS_TOKEN** in the app environment. **Compute → Apps → payment-analysis → Edit → Environment**; add variables, Save, then restart the app. |
| **Error loading app spec from app.yml** | Ensure **`app.yml`** exists at project root (runtime spec for the app container). Redeploy. |
| **Web UI shows "API only" / fallback page** | The app could not find `src/payment_analysis/__dist__`. Ensure `source_code_path` is `${workspace.file_path}` (so the app runs from the synced `files/` folder). (1) Run **`uv run apx build`** then **`databricks bundle deploy -t dev`** so `__dist__` is built and synced. (2) Restart the app from **Compute → Apps**. (3) Check app **Logs** for "UI dist candidate" to see which paths were tried. (4) If needed, set **UI_DIST_DIR** in the app Environment to the full path of the `__dist__` folder. |
| **Logs show "Uvicorn running on http://0.0.0.0:8000"** | This is **expected** when the app runs as a Databricks App. The process binds to `0.0.0.0:8000` inside the app container; the platform proxies requests to it. You are not running on localhost — the app is deployed in Databricks. |
| **Provided OAuth token does not have required scopes** | PAT lacks permissions or OAuth env vars conflict. See [Fix: PAT / token scopes](#fix-pat--token-scopes) below. |
| **403 Forbidden / Invalid scope** (SQL or Setup) | User token from Compute → Apps lacks the **sql** scope. In **Compute → Apps → payment-analysis → Edit → Configure → Authorization scopes**, add **sql**, then **Save** and **restart** the app. See [Use your credentials (no token)](#deploy-app-as-a-databricks-app) above. |
| **Failed to export ... type=mlflowExperiment** | An old MLflow experiment exists under the app path. Delete it in the workspace, then redeploy. See [Fix: export mlflowExperiment](#fix-failed-to-export--typemlflowexperiment) below. |

### Fix: PAT / token scopes

**Error:** `Provided OAuth token does not have required scopes` (with `auth_type=pat`, `DATABRICKS_HOST`, `DATABRICKS_TOKEN` set; sometimes `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` are also set).

The app uses your **PAT** (`DATABRICKS_TOKEN`) or the forwarded user token (when you open from **Compute → Apps**) for jobs, SQL, and `app_config`. If **DATABRICKS_CLIENT_ID** and **DATABRICKS_CLIENT_SECRET** are set in the app environment, the SDK may still apply OAuth scope checks and fail even when using a PAT or forwarded token.

**Fix:**

1. **Remove OAuth client vars when using PAT or OBO**  
   When you open the app from **Compute → Apps** (user token) or use **DATABRICKS_TOKEN** (PAT), do **not** set **DATABRICKS_CLIENT_ID** or **DATABRICKS_CLIENT_SECRET** in the app environment. In **Compute → Apps → payment-analysis → Edit → Environment**, **remove** (or leave empty) **DATABRICKS_CLIENT_ID** and **DATABRICKS_CLIENT_SECRET**. Keep **DATABRICKS_HOST**, **DATABRICKS_WAREHOUSE_ID**, and optionally **DATABRICKS_TOKEN**. Then **Save** and **restart** the app.

2. **Create a new PAT with sufficient scope**  
   In the workspace: **Settings** → **Developer** → **Access tokens** → **Generate new token**.  
   - Ensure your user has token permission **“CAN USE”** (or “CAN MANAGE”) — an admin sets this under **Settings** → **Identity and access** → **Token permissions**.  
   - Create the token with a lifetime you accept.  
   - Set the new token as **DATABRICKS_TOKEN** in the app environment, then **Save** and **restart** the app.

3. **If the app runs as a service principal**  
   An admin must grant that SP token permissions (e.g. via **Set token permissions** or workspace UI), then create a PAT for that SP and set it as **DATABRICKS_TOKEN**.

### Fix: Failed to export … type=mlflowExperiment

The error means an MLflow experiment was created at a path inside the app’s source folder (e.g. `…/payment-analysis/src/payment_analysis/dashboards/payment_analysis_models`). The training notebook was updated so **new** runs use `…/mlflow_experiments/payment_analysis_models` (outside the app path) — see `src/payment_analysis/ml/train_models.py`.

If you still see the error, an old experiment is left in the workspace. Delete it manually:  
**Workspace** → **Users** → **&lt;your-user&gt;** → **payment-analysis** (or your workspace folder) → **src** → **payment_analysis** → **dashboards** → right‑click **payment_analysis_models** → **Delete**. Then redeploy or export again.

### App spec error

Runtime loads **`app.yml`** at deployed app root (command, env). After edits run `./scripts/bundle.sh deploy dev`. **Logs:** **Compute → Apps** → **payment-analysis** → Start → **Logs**.

## Scripts

| Script | Purpose |
|--------|---------|
| **bundle.sh** | `./scripts/bundle.sh deploy [dev\|prod]` — runs prepare (dashboards + `gold_views.sql` + `lakehouse_bootstrap.sql` in `.build/transform/`) then deploy. `validate` / `verify` for checks. |
| **dashboards.py** | **prepare** (by bundle.sh): writes `.build/dashboards/`, `.build/transform/gold_views.sql`, `.build/transform/lakehouse_bootstrap.sql` with catalog/schema. **validate-assets**, **publish** (optional). Run: `uv run python scripts/dashboards.py` |
| **sync_requirements_from_lock.py** | Generate `requirements.txt` from `uv.lock` for the Databricks App. Run after `uv lock`: `uv run python scripts/sync_requirements_from_lock.py` |

## Demo setup & one-click run

1. **Deploy once:** `./scripts/bundle.sh deploy dev` (prepare + build + deploy; all job files present).
2. **Run in order from the app:** Open the app → **Setup & Run** → run step 1 (Lakehouse Bootstrap), step 2 (Vector Search), step 3 (Gold views), step 4 (Simulator), step 5 (Optional real-time streaming), step 6 (ETL pipeline), step 7 (Train ML), step 8 (Genie sync), step 9 (Agents), step 10 (Publish dashboards).
3. **Optional:** Set `DATABRICKS_JOB_ID_*` in the app environment to job IDs from **Workflows** if Run uses a different workspace.

**Estimated time:** 45–60 min. Job/pipeline IDs: **Workflows** / **Lakeflow** or `databricks bundle run <job_name> -t dev`.

## Job inventory and duplicate check

All bundle jobs have been reviewed for duplicates or overlapping functionality. **There are no repeated jobs.** Each job has a single, distinct purpose.

| Job (bundle resource) | Purpose | Notes |
|----------------------|---------|--------|
| **ml_jobs.yml** | | |
| `lakehouse_bootstrap_job` | Run `lakehouse_bootstrap.sql`: app_config, rules, recommendations, online_features | SQL task; run once. |
| `vector_search_index_job` | Create Vector Search endpoint and index from `transaction_summaries_for_search` | Notebook; run after bootstrap. |
| `create_gold_views_job` | Run `gold_views.sql`: 12+ analytical views | SQL task; distinct from bootstrap. |
| `train_ml_models_job` | Train 4 ML models (approval, risk, routing, retry); register in UC | Single notebook. |
| `prepare_dashboards_job` | Generate `.build/dashboards/` and `.build/transform/*.sql` with catalog/schema | Run when catalog/schema or source dashboards change; not in Setup & Run UI. |
| `publish_dashboards_job` | Publish dashboards with embed credentials (Lakeview API) for app embedding | Does not run prepare; run after deploy. |
| `test_agent_framework_job` | Verify agent framework (test_mode); CI/smoke | Same notebook as agents but test-only; not production run. |
| **agents.yml** | | |
| `orchestrator_agent_job` | Run orchestrator (coordinates all agents) | One notebook, role `orchestrator`. |
| `smart_routing_agent_job` | Run smart routing agent only | Same notebook, role `smart_routing`; separate for scheduling. |
| `smart_retry_agent_job` | Run smart retry agent only | Same notebook, role `smart_retry`. |
| `decline_analyst_agent_job` | Run decline analyst only | Same notebook, role `decline_analyst`. |
| `risk_assessor_agent_job` | Run risk assessor only | Same notebook, role `risk_assessor`. |
| `performance_recommender_agent_job` | Run performance recommender only | Same notebook, role `performance_recommender`. |
| **streaming_simulator.yml** | | |
| `transaction_stream_simulator` | Generate synthetic payment events (e.g. 1000/s) | Producer only. |
| `continuous_stream_processor` | Process streaming events continuously | Consumer; different notebook. |
| **genie_spaces.yml** | | |
| `genie_sync_job` | Sync Genie space configuration and sample questions | Single purpose. |

**Why agent jobs are not merged:** The six specialist jobs and the orchestrator all call the same notebook (`agent_framework`) with different `agent_role` (and the orchestrator coordinates them). They are kept as separate jobs so each can have its own schedule (e.g. risk assessor every 2h, decline analyst daily) and so the UI can run individual agents or the orchestrator on demand. Merging them into one multi-task job would remove per-agent scheduling and one-off runs.

**Dashboard jobs:** `prepare_dashboards_job` (generate assets) and `publish_dashboards_job` (publish to Lakeview) are different: prepare writes files; publish calls the API. Both are used; neither is redundant.

## Jobs and notebook/SQL reference

All job notebook and SQL paths are relative to the workspace `file_path` (where the bundle syncs). Each path below is verified to exist in the repo (`.py` or generated under `.build/`).

| Bundle resource (YAML key) | App/backend key | Notebook or SQL path | Source file |
|----------------------------|-----------------|----------------------|-------------|
| `lakehouse_bootstrap_job` | `lakehouse_bootstrap` | `.build/transform/lakehouse_bootstrap.sql` | Generated by prepare |
| `vector_search_index_job` | `vector_search_index` | `src/payment_analysis/vector_search/create_index` | `create_index.py` |
| `create_gold_views_job` | `create_gold_views` | `.build/transform/gold_views.sql` | Generated by prepare |
| `transaction_stream_simulator` | `transaction_stream_simulator` | `src/payment_analysis/streaming/transaction_simulator` | `transaction_simulator.py` |
| `train_ml_models_job` | `train_ml_models` | `src/payment_analysis/ml/train_models` | `train_models.py` |
| `genie_sync_job` | `genie_sync` | `src/payment_analysis/genie/sync_genie_space` | `sync_genie_space.py` |
| `orchestrator_agent_job` | `orchestrator_agent` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| `smart_routing_agent_job` | `smart_routing_agent` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| `smart_retry_agent_job` | `smart_retry_agent` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| `decline_analyst_agent_job` | `decline_analyst_agent` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| `risk_assessor_agent_job` | `risk_assessor_agent` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| `performance_recommender_agent_job` | `performance_recommender_agent` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| `test_agent_framework_job` | `test_agent_framework` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| `publish_dashboards_job` | `publish_dashboards` | `src/payment_analysis/transform/publish_dashboards` | `publish_dashboards.py` |
| `continuous_stream_processor` | `continuous_stream_processor` | `src/payment_analysis/streaming/continuous_processor` | `continuous_processor.py` |
| `prepare_dashboards_job` | (not in Setup UI) | `src/payment_analysis/transform/prepare_dashboards` | `prepare_dashboards.py` |

**Pipelines** (not jobs): `payment_analysis_etl` uses notebooks `streaming/bronze_ingest`, `transform/silver_transform`, `transform/gold_views`. `payment_realtime_pipeline` uses `streaming/realtime_pipeline`. Sync includes `src/payment_analysis/ml`, `streaming`, `transform`, `agents`, `genie`, `vector_search`, so all referenced notebooks are uploaded.

---

**See also:** [Architecture & reference](ARCHITECTURE_REFERENCE.md)
