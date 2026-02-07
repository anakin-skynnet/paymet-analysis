# Deployment Guide

How to deploy and configure the Payment Analysis app and bundle (Databricks Apps, Lakebase, jobs, dashboards).

## Prerequisites

Databricks workspace (Unity Catalog), SQL Warehouse, CLI configured. Python 3.10+ with `uv`, Node 18+ with `bun`. `package.json` engines `>=22.0.0`. Permissions: jobs, Lakeflow, model serving; write to catalog; deploy to `/Workspace/Users/<you>/payment-analysis`. **Databricks App:** Only `requirements.txt` and `package.json` deps; no system packages. See [Architecture & reference](ARCHITECTURE_REFERENCE.md#databricks-app-deploy).

## Quick start

Before every deploy (same catalog/schema for dashboards and Gold Views job):

```bash
./scripts/bundle.sh validate dev
databricks bundle deploy -t dev
```

Or: `uv run python scripts/dashboards.py prepare` then `databricks bundle validate -t dev` and `databricks bundle deploy -t dev`. For prod use `./scripts/bundle.sh validate prod` then deploy.

## Steps at a glance

| # | Step | Action |
|---|------|--------|
| 1 | Deploy bundle | `./scripts/bundle.sh deploy dev` |
| 2 | Data ingestion | **Setup & Run** → Run **Transaction Stream Simulator** |
| 3 | ETL | **Setup & Run** → Start **Payment Analysis ETL** pipeline |
| 4 | Gold views | **Setup & Run** → Run **Create Payment Analysis Gold Views** |
| 5 | Lakehouse SQL | Run `lakehouse_bootstrap.sql` (same catalog/schema) |
| 6 | ML models | **Setup & Run** → Run **Train Payment Approval ML Models** (~10–15 min) |
| 7 | Dashboards & app | 12 dashboards + app deployed by bundle |
| 8 | Model serving | After step 6: uncomment `resources/model_serving.yml`, redeploy |
| 9 | AI agents (optional) | Run **Orchestrator** / agents from **Setup & Run** |
| 10 | Verify | **Dashboard**, **Rules**, **Decisioning**, **ML Models** in app |

## Deploy app as a Databricks App

1. **Build:** `uv run apx build`
2. **Deploy:** `./scripts/bundle.sh deploy dev`
3. **Run:** `databricks bundle run payment_analysis_app -t dev` or **Workspace → Apps** → **payment-analysis** → Start
4. **App URL:** From bundle summary or app detail.
5. **Required env (Workspace → Apps → payment-analysis → Edit → Environment):**

| Variable | Purpose |
|----------|---------|
| **PGAPPNAME** | Lakebase instance (e.g. `payment-analysis-db-dev`) |
| **DATABRICKS_HOST** | Workspace URL |
| **DATABRICKS_WAREHOUSE_ID** | SQL Warehouse ID (from bundle summary) |
| **DATABRICKS_TOKEN** | API access (PAT or OAuth) |
| **LAKEBASE_SCHEMA** | Optional. Postgres schema for app tables (default `app`). Use when the app has no CREATE on `public`. |

6. **Optional — override job/pipeline IDs:** Set `DATABRICKS_JOB_ID_*`, `DATABRICKS_PIPELINE_ID_*`, `DATABRICKS_WORKSPACE_ID` per [Architecture & reference](ARCHITECTURE_REFERENCE.md#workspace-components--ui-mapping).

App resource: `resources/fastapi_app.yml`. Runtime spec: `app.yml` at project root. See [App spec error](#app-spec-error).

## App configuration and resource paths

**Bundle root:** Directory containing `databricks.yml`. **App source:** `source_code_path: .` (bundle root) in `resources/fastapi_app.yml`.

**Included resources** (order in `databricks.yml`): `unity_catalog`, `lakebase`, `pipelines`, `sql_warehouse`, `ml_jobs`, `agents`, `streaming_simulator`, `genie_spaces`, `dashboards`, `fastapi_app`. Optional: `model_serving` (uncomment after training models).

**Paths:**  
- Workspace root: `/Workspace/Users/${user}/${var.workspace_folder}` (default folder: `payment-analysis`).  
- Notebooks/jobs: `${workspace.file_path}/src/payment_analysis/...` (e.g. `ml/train_models`, `streaming/transaction_simulator`, `agents/agent_framework`).  
- Gold views SQL: `${workspace.file_path}/.build/transform/gold_views.sql` (from `scripts/dashboards.py prepare`).  
- Dashboards: `file_path` in `resources/dashboards.yml` is `../.build/dashboards/*.lvdash.json` (relative to `resources/`).  
- Sync (uploaded to workspace): `.build`, `src/payment_analysis/ml`, `streaming`, `transform`, `agents`, `genie`.

**App bindings:** database (Lakebase), sql-warehouse (`payment_analysis_warehouse`), 12 jobs (simulator, stream processor, gold views, train ML, test agent, 6 agent jobs, genie sync). Optional: genie-space, model serving endpoints (see comments in `fastapi_app.yml`).

Validate before deploy: `./scripts/bundle.sh validate dev` (runs dashboard prepare then `databricks bundle validate`).

**Version alignment:** All dependency references use exactly the same versions everywhere (no ranges). Python: `pyproject.toml` (pinned `==`) → `uv.lock` → `requirements.txt` via `scripts/sync_requirements_from_lock.py`. Frontend: `package.json` and `bun.lock` use exact versions only (no `^`). After changing `pyproject.toml` run `uv lock` then `uv run python scripts/sync_requirements_from_lock.py`. If you see "error installing packages" on deploy, check **Compute → Apps → your app → Logs** for the exact `pip` error.

**Version verification (same versions everywhere):**

| Stack | Source of truth | Generated / lock | Aligned? |
|-------|-----------------|------------------|----------|
| Python app | `pyproject.toml` (pinned `==`) | `uv.lock` → `requirements.txt` via `scripts/sync_requirements_from_lock.py` | Yes: direct deps (databricks-sdk 0.84.0, fastapi 0.128.0, uvicorn 0.40.0, pydantic-settings 2.6.1, sqlmodel 0.0.27, psycopg 3.2.3) match in all three. |
| Frontend | `package.json` (exact versions, no `^`) | `bun.lock` | Yes: workspace deps in `bun.lock` match `package.json`. |
| Runtime | `.python-version` = 3.11 | `pyproject.toml` `requires-python = ">=3.11"` | Yes. |
| Jobs/Pipelines | N/A (Spark/Lakeflow) | `resources/*.yml` use `spark_version` (e.g. 15.4.x) for clusters only; not app deps. | N/A. |

## Schema consistency

One catalog/schema (defaults: `ahs_demos_catalog`, `ahs_demo_payment_analysis_dev`). Effective catalog/schema from Lakehouse `app_config`; set via **Setup & Run** → **Save catalog & schema**. See [Architecture & reference](ARCHITECTURE_REFERENCE.md#catalog-and-schema-app_config).

## Resources in the workspace

By default: Workspace folder, Lakebase, Jobs (simulator, gold views, ML, agents, stream, Genie sync), 2 pipelines, SQL warehouse, Unity Catalog, 12 dashboards, Databricks App. **Optional:** Uncomment `resources/model_serving.yml` after Step 6; create Vector Search manually from `resources/vector_search.yml`.

## Where to find resources

- **Workspace:** **Workspace** → **Users** → you → **payment-analysis**
- **Jobs:** **Workflow** → `[dev …]` job names
- **Lakeflow:** **Lakeflow** → ETL and Real-Time Stream
- **SQL Warehouse:** **SQL** → **Warehouses**
- **Catalog / Dashboards:** **Data** → Catalogs; **SQL** → **Dashboards**

**Dashboard TABLE_OR_VIEW_NOT_FOUND:** Run **Create Gold Views** in the same catalog.schema as `dashboards.py prepare`. Validate: `uv run python scripts/dashboards.py validate-assets --catalog X --schema Y`.

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

**Supported and compatible:** App runtime is Python 3.11 and Node.js 22.16; our `.python-version` (3.11) and `package.json` `engines.node` (>=22.0.0) match. All Python packages in `requirements.txt` have manylinux-compatible wheels or are pure Python. We use `psycopg[binary]` so the app has a working PostgreSQL driver without needing the system libpq library (the container does not provide it). `requirements.txt` is generated from `uv.lock` by `scripts/sync_requirements_from_lock.py`.

## Troubleshooting

| Issue | Action |
|-------|--------|
| Database instance STARTING | Wait, then redeploy |
| Don't see resources | Redeploy; run `./scripts/bundle.sh validate dev` |
| Registered model does not exist | Run Step 6, then uncomment `model_serving.yml`, redeploy |
| Lakebase "Instance name is not unique" | Use unique `lakebase_instance_name` via `--var` or target |
| Error installing packages (app deploy) | Check **Logs** for the exact pip error. Ensure `requirements.txt` is up to date: run `uv lock` then `uv run python scripts/sync_requirements_from_lock.py`. See [Databricks Apps compatibility](#databricks-apps-compatibility). |
| **permission denied for schema public** | App tables use schema `app` by default. Set **LAKEBASE_SCHEMA** (e.g. `app`) in the app environment if needed; the app creates the schema if it has permission. |
| **Error loading app spec from app.yml** | Ensure **`app.yml`** exists at project root (runtime spec for the app container). Redeploy. |
| **Web UI shows "API only" / fallback page** | The UI build was not in the deployed app. Run **`uv run apx build`** then **`databricks bundle deploy -t dev`** (or `./scripts/bundle.sh deploy dev`). The bundle runs the build and syncs `src/payment_analysis/__dist__` so the app can serve the UI. |
| **Failed to export ... type=mlflowExperiment** | An old MLflow experiment exists under the app path. Delete it in the workspace, then redeploy. See [Fix: export mlflowExperiment](#fix-failed-to-export--typemlflowexperiment) below. |

### Fix: Failed to export … type=mlflowExperiment

The error means an MLflow experiment was created at a path inside the app’s source folder (e.g. `…/payment-analysis/src/payment_analysis/dashboards/payment_analysis_models`). The training notebook was updated so **new** runs use `…/mlflow_experiments/payment_analysis_models` (outside the app path) — see `src/payment_analysis/ml/train_models.py`.

If you still see the error, an old experiment is left in the workspace. Delete it manually:  
**Workspace** → **Users** → **&lt;your-user&gt;** → **payment-analysis** (or your workspace folder) → **src** → **payment_analysis** → **dashboards** → right‑click **payment_analysis_models** → **Delete**. Then redeploy or export again.

### App spec error

Runtime loads **`app.yml`** at deployed app root (command, env). After edits run `./scripts/bundle.sh deploy dev`. **Logs:** **Compute → Apps** → **payment-analysis** → Start → **Logs**.

## Scripts

| Script | Purpose |
|--------|---------|
| **bundle.sh** | `./scripts/bundle.sh deploy [dev\|prod]` — prepare dashboards then deploy. `validate` / `verify` for checks. |
| **dashboards.py** | **prepare** (by bundle.sh), **validate-assets**, **publish** (optional). Run: `uv run python scripts/dashboards.py` |
| **sync_requirements_from_lock.py** | Generate `requirements.txt` from `uv.lock` for the Databricks App. Run after `uv lock`: `uv run python scripts/sync_requirements_from_lock.py` |

## Demo setup & one-click run

Order: (1) Deploy bundle (2) Simulator (3) ETL pipeline (4) Gold views job (5) `lakehouse_bootstrap.sql` (6) Train ML (7–8) Optional real-time pipeline, agents. **Estimated time:** 45–60 min. Job/pipeline IDs: **Workflows** / **Lakeflow** or `databricks bundle run <job_name> -t dev`.

---

**See also:** [Architecture & reference](ARCHITECTURE_REFERENCE.md)
