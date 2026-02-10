# Deployment

How to deploy and configure the Payment Analysis app and **Databricks Asset Bundle (DAB)** (Databricks Apps, Lakebase, jobs, dashboards). This project uses [Databricks Asset Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/) for IaC and CI/CD. For architecture and project structure see [Guide](GUIDE.md).

## Prerequisites

Databricks workspace (Unity Catalog), SQL Warehouse, CLI configured. **Catalog and schema:** Either (1) create the **catalog** (default `ahs_demos_catalog`) under **Data → Catalogs** before deploy so the bundle can create the **schema** and volumes, or (2) deploy and run **Job 1** first — its first task creates the catalog and schema if they do not exist (requires metastore admin or CREATE_CATALOG/CREATE_SCHEMA). If you use different names, deploy with `--var catalog=<your_catalog> --var schema=<your_schema>`. Python 3.10+ with `uv`, Node 18+ with `bun`. `package.json` engines `>=22.0.0`. Permissions: jobs, Lakeflow, model serving; write to catalog; deploy to `/Workspace/Users/<you>/payment-analysis`. **Databricks App:** Only `requirements.txt` and `package.json` deps; no system packages. See [Guide](GUIDE.md).

## Quick start

One command deploys the bundle and generates all required files (dashboards and SQL for jobs):

```bash
./scripts/bundle.sh deploy dev
```

This runs **prepare** (writes `.build/dashboards/` and `.build/transform/gold_views.sql` + `lakehouse_bootstrap.sql` with catalog/schema) then deploys. After deploy, run steps 1–10 from the app **Setup & Run** in order. To validate without deploying: `./scripts/bundle.sh validate dev`.

## Steps at a glance

Jobs are consolidated into **7 numbered steps** (prefix in job name). Run in order: **1 → 2 → 3 → 4 → 5 → 6 → 7**. Pipelines (Lakeflow ETL and Real-time) are separate resources; start them when needed.

| # | Job (step) | Action |
|---|------------|--------|
| 0 | Deploy bundle | `./scripts/bundle.sh deploy dev` (includes prepare; no missing files) |
| 1 | **1. Create Data Repositories** | **Setup & Run** → Run job 1 (ensure catalog & schema → **create Lakebase Autoscaling** project/branch/endpoint → **Lakebase data init** — app_config, approval_rules, online_features, app_settings → lakehouse bootstrap → vector search). Run once. Creates everything needed for later jobs and the app. |
| 2 | **2. Simulate Transaction Events** | **Setup & Run** → Run **Transaction Stream Simulator** (producer; events ingested later by pipelines) |
| — | **Pipeline (before Step 3)** | Start **Payment Analysis ETL** (Lakeflow) at least once so it creates `payments_enriched_silver` (and `payments_raw_bronze`) in the catalog/schema. Step 3 (Gold Views) depends on this table. |
| 3 | **3. Initialize Ingestion** | **Setup & Run** → Run **Create Gold Views** or **Continuous Stream Processor** (same job: gold views + vector search sync; requires pipeline to have run so `payments_enriched_silver` exists) |
| 4 | **4. Deploy Dashboards** | **Setup & Run** → Run job 4 (prepare assets → publish dashboards with embed credentials) |
| 5 | **5. Train Models & Model Serving** | **Setup & Run** → Run **Train Payment Approval ML Models** (~10–15 min); then uncomment `model_serving.yml`, redeploy |
| 6 | **6. Deploy AgentBricks Agents** | **Setup & Run** → Run **Orchestrator**, any specialist agent, or **Test Agent Framework** (same job: all 7 tasks) |
| 7 | **7. Genie Space Sync** | **Setup & Run** → Run **Genie Space Sync** (optional; syncs Genie space config and sample questions for natural language analytics) |
| — | Pipelines | **Setup & Run** → Start **Payment Analysis ETL** (required before Step 3) and/or **Real-Time Stream** (Lakeflow; when needed) |
| — | Dashboards & app | 12 dashboards + app deployed by bundle |
| — | Verify | **Dashboard**, **Rules**, **Decisioning**, **ML Models** in app |

All jobs and pipelines can be run from the UI. To connect: use your credentials (open app from **Compute → Apps**) or set **DATABRICKS_TOKEN** (PAT) in the app environment. When you open the app from Compute → Apps (or with PAT set), the Setup & Run page resolves job and pipeline IDs from the workspace by name so you can run steps without setting `DATABRICKS_JOB_ID_*` / `DATABRICKS_PIPELINE_ID_*`. See **Setup & Run → Connect to Databricks**.

## Deploy app as a Databricks App

**Deploy into Databricks App** (create/update the app in the workspace and make the UI available):

1. **Deploy bundle:** Run `./scripts/bundle.sh deploy dev`. This runs prepare (generates `.build/dashboards/`, `.build/transform/gold_views.sql`, `.build/transform/lakehouse_bootstrap.sql`), builds the UI (`uv run apx build` via `artifacts.default.build`), and deploys. All job SQL files exist after deploy.
2. **Start the app:** In the workspace go to **Compute → Apps → payment-analysis → Start**, or run `databricks bundle run payment_analysis_app -t dev`. The app runs in Databricks (not on your machine). Logs showing **"Uvicorn running on http://0.0.0.0:8000"** are expected: the app binds to that address inside the container and the Databricks platform proxies external traffic to it.
3. **App URL:** Open the app from the Apps page or use the URL from **databricks bundle summary**.
4. **Required env (Workspace → Apps → payment-analysis → Edit → Environment):**

| Variable | Purpose |
|----------|---------|
| **LAKEBASE_PROJECT_ID** | Required. Lakebase Autoscaling project ID (same as Job 1 create_lakebase_autoscaling; e.g. `payment-analysis-db`). |
| **LAKEBASE_BRANCH_ID** | Required. Lakebase Autoscaling branch (e.g. `production`). |
| **LAKEBASE_ENDPOINT_ID** | Required. Lakebase Autoscaling endpoint (e.g. `primary`). |
| **DATABRICKS_WAREHOUSE_ID** | Required for SQL/analytics. SQL Warehouse ID (from bundle or sql-warehouse binding). |
| **DATABRICKS_HOST** | Optional when opened from **Compute → Apps** (workspace URL derived from request). Set when not using OBO. |
| **DATABRICKS_TOKEN** | Optional when using OBO. Open from **Compute → Apps** so your token is forwarded; do not set in env. Set only for app-only use; then do **not** set DATABRICKS_CLIENT_ID/SECRET. |
| **LAKEBASE_SCHEMA** | Optional. Postgres schema for app tables (default `payment_analysis`). Use when the app has no CREATE on `public`. |

**Use your credentials (recommended):** Open the app from **Workspace → Compute → Apps → payment-analysis**. The platform forwards your token; no DATABRICKS_TOKEN or DATABRICKS_HOST is required in the app environment. The app then uses that logged-in user token for all Databricks resources (SQL Warehouse, jobs, dashboards). The main page shows "Use your Databricks credentials" when no token is present; open the workspace to sign in. Enable user authorization (OBO) and add scopes **sql**, **Jobs**, and **Pipelines** (if needed) in **Edit → Configure → Authorization scopes**. If you see 403 Invalid scope, add **sql** and restart. If Run stays disabled, click **Refresh job IDs** on the Setup page.

5. **Optional — override job/pipeline IDs:** Set `DATABRICKS_JOB_ID_*`, `DATABRICKS_PIPELINE_ID_*`, `DATABRICKS_WORKSPACE_ID` per [Guide — Workspace ↔ UI mapping](GUIDE.md#4-workspace-components--ui-mapping).

App resource: `resources/fastapi_app.yml`. Runtime spec: `app.yml` at project root. See [App spec error](#app-spec-error).

## App configuration and resource paths

**Bundle root:** Directory containing `databricks.yml`. **App source:** `source_code_path` in `resources/fastapi_app.yml` is `${workspace.root_path}` (e.g. `.../payment-analysis`). Sync uploads to the same root path; the app runs from there so `src/payment_analysis/__dist__` is found for the web UI.

**Included resources** (order in `databricks.yml`): `unity_catalog`, `lakebase`, `pipelines`, `sql_warehouse`, `ml_jobs`, `agents`, `streaming_simulator`, `genie_spaces`, `dashboards` (comment out if deploy fails with "Node named '…' already exists"), `fastapi_app`. Optional: `model_serving` (uncomment after training models).

**Paths:**  
- Workspace root: `/Workspace/Users/${user}/${var.workspace_folder}` (default folder: `payment-analysis`).  
- Notebooks/jobs: `${workspace.root_path}/src/payment_analysis/...` (e.g. `ml/train_models`, `streaming/transaction_simulator`, `agents/agent_framework`).
- SQL for jobs: `${workspace.root_path}/.build/transform/gold_views.sql` and `lakehouse_bootstrap.sql` (both generated by `scripts/dashboards.py prepare` with USE CATALOG/SCHEMA).
- Dashboards: `file_path` in `resources/dashboards.yml` is `../.build/dashboards/*.lvdash.json` (relative to `resources/`).  
- Sync (uploaded to workspace): `.build`, `src/payment_analysis/ml`, `streaming`, `transform`, `agents`, `genie`.

**App bindings:** sql-warehouse (`payment_analysis_warehouse`), jobs 1–7 in execution order (create repos, simulator, ingestion, deploy dashboards, train ML, agents, Genie sync). Lakebase: use Autoscaling only; set LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID in app Environment (Job 1 create_lakebase_autoscaling creates the project). Optional: genie-space, model serving endpoints (see comments in `fastapi_app.yml`).

Validate before deploy: `./scripts/bundle.sh validate dev` (runs dashboard prepare then `databricks bundle validate`).

### Why one databricks.yml

- **Source of truth:** The file at **repo root** `databricks.yml` is the only one used for `databricks bundle validate -t dev` and `databricks bundle deploy -t dev`. The bundle CLI runs from the project root and reads only the root `databricks.yml`.
- **Workspace path:** In root `databricks.yml`, `workspace.root_path` is the path in the Databricks workspace used for both **sync** (upload destination) and the **app** (`source_code_path`). One path keeps the setup simple and aligns with [Apps Cookbook](https://apps-cookbook.dev/docs/intro) and [apx](https://github.com/databricks-solutions/apx). **`file_path`** is not used (removed to avoid a `files/` subfolder).
- **No duplicate config:** The **`files/`** directory is in **`.gitignore`** and has been removed from git tracking. Do not commit workspace mirrors or sync copies under `files/`.

## Version alignment

All dependency references use **exactly the same versions** everywhere (no ranges). This section is the single reference for verified versions and Databricks App runtime compatibility.

**After changing `pyproject.toml`:** run `uv lock` then `uv run python scripts/sync_requirements_from_lock.py`. **After changing `package.json`:** run `uv run apx bun install`. If you see "error installing packages" on deploy, check **Compute → Apps → your app → Logs** for the exact `pip` error.

### Runtime (Databricks App)

| Runtime | Version | Source |
|--------|---------|--------|
| **Python** | 3.11 | `.python-version`; `pyproject.toml` `requires-python = ">=3.11"`. Databricks App runs Python 3.11. |
| **Node.js** | ≥22.0.0 | `package.json` `engines.node`. Databricks App uses Node.js 22.16; local dev should use 22.x. |

### Python (backend and scripts)

**Source of truth:** `pyproject.toml` (all direct deps use `==`). **Lock:** `uv.lock`. **App deploy:** `requirements.txt` is generated from `uv.lock` by `scripts/sync_requirements_from_lock.py`.

**Direct dependencies (exact versions):** databricks-sdk 0.85.0, fastapi 0.128.6, uvicorn 0.40.0, pydantic-settings 2.6.1, sqlmodel 0.0.27, psycopg[binary,pool] 3.2.3. Dev: ty 0.0.14, apx 0.2.6. Transitive versions are fixed in `uv.lock` and reflected in `requirements.txt` by the sync script.

### Frontend (UI)

**Source of truth:** `package.json` (exact versions only; no `^` or `~`). **Lock:** `bun.lock`. Key deps include react 19.2.3, vite 7.3.1, @tanstack/react-router 1.158.1, typescript 5.9.3, and shadcn/radix/tailwind pins; all match `bun.lock`.

### Version verification (same versions everywhere)

| Stack | Source of truth | Generated / lock | Aligned? |
|-------|-----------------|------------------|----------|
| Python app | `pyproject.toml` (pinned `==`) | `uv.lock` → `requirements.txt` via `scripts/sync_requirements_from_lock.py` | Yes |
| Frontend | `package.json` (exact versions, no `^`) | `bun.lock` | Yes |
| Runtime | `.python-version` = 3.11 | `pyproject.toml` `requires-python = ">=3.11"` | Yes |
| Jobs/Pipelines | N/A (Spark/Lakeflow) | `resources/*.yml` use `spark_version` for clusters only | N/A |

### Files that must stay aligned

| File | Role |
|------|------|
| `pyproject.toml` | Python direct deps (exact `==`); do not add ranges. |
| `uv.lock` | Resolved Python deps; run `uv lock` after changing pyproject.toml. |
| `requirements.txt` | Generated from uv.lock by `scripts/sync_requirements_from_lock.py`; do not edit by hand. |
| `package.json` | Frontend deps (exact versions only); run `uv run apx bun install` after changes. |
| `bun.lock` | Resolved frontend deps. |
| `.python-version` | 3.11 (matches Databricks App). |

## Schema consistency (parametrized; same name as DAB-deployed)

Catalog and schema are **parametrized**. In **dev** the concatenation is **`ahs_demos_catalog.dev_ariel_hdez_payment_analysis`** (same as the schema deployed by the Databricks Asset Bundle).

| Where | Value (dev) |
|-------|-------------|
| Bundle `var.schema` (dev) | `dev_ariel_hdez_payment_analysis` (`databricks.yml` dev target) |
| Job notebook params (catalog, schema) | `${var.catalog}`, `${var.schema}` → `ahs_demos_catalog`, `dev_ariel_hdez_payment_analysis` |
| Lakebase Postgres (app_config, approval_rules, etc.) | `lakebase_schema: "payment_analysis"` in job params; `LAKEBASE_SCHEMA` env default `payment_analysis` |
| Backend (Lakebase, Databricks bootstrap) | From `app_config` or `DATABRICKS_SCHEMA` default `dev_ariel_hdez_payment_analysis` |
| Dashboard prepare / source assets | Placeholder **`__CATALOG__.__SCHEMA__`** in `resources/dashboards/*.lvdash.json`; prepare replaces with `catalog.schema`. For dev, `bundle.sh` runs prepare with `--catalog ahs_demos_catalog --schema dev_ariel_hdez_payment_analysis` → **`ahs_demos_catalog.dev_ariel_hdez_payment_analysis`** |
| ML training, gold views, agents | Widget/default from job params (`var.schema`) |

Effective catalog/schema for the app come from Lakehouse `app_config`; set via **Setup & Run** → **Save catalog & schema**. For dev, use **Save catalog & schema** with catalog `ahs_demos_catalog` and schema `dev_ariel_hdez_payment_analysis` so dashboards and jobs align. Prod target uses `schema: ahs_demo_payment_analysis_prod` (see [Guide — Catalog and schema](GUIDE.md#5-data-sources-ui--backend--databricks)).

### Why `dev_ariel_hdez_payment_analysis` in dev?

In **dev** the bundle variable **`var.schema`** is set to **`dev_ariel_hdez_payment_analysis`** so that:

- The schema created by the bundle (and used by jobs/pipelines) has the **same name** as the one DAB deploys (e.g. with development-mode naming).
- **Dashboard prepare** is run with `--catalog ahs_demos_catalog --schema dev_ariel_hdez_payment_analysis`, so prepared asset names are **`ahs_demos_catalog.dev_ariel_hdez_payment_analysis.<table_or_view>`** and match the deployed catalog.schema.

In **production** (`-t prod`) the target sets `schema: ahs_demo_payment_analysis_prod`; there is no dev-style prefix.

## Resources in the workspace

By default: Workspace folder, Lakebase, Jobs (7 steps: create repositories, simulate events, initialize ingestion, deploy dashboards, train models, deploy agents, Genie sync), 2 pipelines, SQL warehouse, Unity Catalog, 12 dashboards, Databricks App. **Optional:** Uncomment `resources/model_serving.yml` after Step 5 (Train ML models); create Vector Search manually from `resources/vector_search.yml` if not in bundle.

## Where to find resources

- **Workspace:** **Workspace** → **Users** → you → **payment-analysis**
- **Jobs:** **Workflow** → `[dev …]` job names
- **Lakeflow:** **Lakeflow** → ETL and Real-Time Stream
- **SQL Warehouse:** **SQL** → **Warehouses**
- **Catalog / Dashboards:** **Data** → Catalogs; **SQL** → **Dashboards**

**Dashboard TABLE_OR_VIEW_NOT_FOUND:** Run **Create Gold Views** (and **Lakehouse Bootstrap** if Rules/Decisioning are empty) in the same catalog.schema as prepare. Validate: `uv run python scripts/dashboards.py validate-assets --catalog X --schema Y`.

## Databricks Apps compatibility

**Environment (official):** Python 3.11, Ubuntu 22.04 LTS, Node.js 22.16. [Pre-installed Python libraries](https://docs.databricks.com/en/dev-tools/databricks-apps/system-env#pre-installed-python-libraries) include databricks-sdk 0.33.0, fastapi 0.115.0, uvicorn[standard] 0.30.6, and others (streamlit, dash, flask, etc.).

**Our `requirements.txt`:** Overrides three pre-installed packages (databricks-sdk → 0.85.0, fastapi → 0.128.6, uvicorn → 0.40.0) and adds pydantic-settings, sqlmodel, psycopg[binary] plus transitive pins. Overriding is supported; pinning exact versions is recommended by Databricks. Our overrides are within the same major/minor line and are tested.

**If you see "error installing packages":** (1) Check **Compute → Apps → your app → Logs** for the exact `pip` or install failure. (2) Regenerate: `uv run python scripts/sync_requirements_from_lock.py` then redeploy.

**Supported and compatible:** Databricks App system environment uses **Python 3.11** and **Node.js 22.16**. Our `.python-version` and `package.json` `engines.node` (>=22.0.0) are compatible. We use `psycopg[binary]` so the app has a working PostgreSQL driver without the system libpq. `requirements.txt` is generated from `uv.lock` by `scripts/sync_requirements_from_lock.py`; do not edit by hand.

## Why the web UI was not found (references: apps-cookbook, apx, ai-dev-kit)

**Root cause:** The app runs from a **working directory** that must be the same place where the bundle **sync** uploaded your code and the built UI. Per [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/settings) and [apx](https://github.com/databricks-solutions/apx): **Sync** uploads to **`workspace.root_path`** (e.g. `.../payment-analysis`). The app’s **`source_code_path`** is the same path so the process **cwd** contains `src/payment_analysis/__dist__` and the web UI is found. [Apps Cookbook](https://apps-cookbook.dev/docs/intro) and [ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit) use the same idea: the app must run from the folder that contains the deployed files (including the built frontend).

**Fix applied in this repo:** (1) **`source_code_path`** in `resources/fastapi_app.yml` is set to **`${workspace.root_path}`**. (2) **`workspace.root_path`** in `databricks.yml` is the single workspace path (no `file_path` subfolder). (3) **Build before deploy:** `artifacts.default.build: uv run apx build` creates `src/payment_analysis/__dist__`; **`sync.include`** lists it so it is uploaded. (4) At runtime the app tries several path candidates and logs **"UI dist candidate"** in app Logs for diagnostics. After any change to the app or bundle config, **redeploy** and **restart** the app.

## Troubleshooting

| Issue | Action |
|-------|--------|
| Database instance STARTING | Wait, then redeploy |
| Don't see resources | Redeploy; run `./scripts/bundle.sh validate dev` |
| Registered model does not exist | Run Step 5 (Train ML models), then uncomment `model_serving.yml`, redeploy |
| Lakebase Autoscaling project/endpoint not found | Run Job 1 task **create_lakebase_autoscaling** first, or create a Lakebase project in **Compute → Lakebase** and set bundle vars `lakebase_project_id`, `lakebase_branch_id`, `lakebase_endpoint_id`. |
| **Lakebase project/endpoint not found** (`projects/…/branches/…/endpoints/…`) | The Autoscaling project does not exist. Create a Lakebase project in **Compute → Lakebase**, then set bundle variables to match. See [Fix: Lakebase project/endpoint not found](#fix-lakebase-projectendpoint-not-found) below. |
| Error installing packages (app deploy) | Check **Logs** for the exact pip error. Ensure `requirements.txt` is up to date: run `uv lock` then `uv run python scripts/sync_requirements_from_lock.py`. See [Databricks Apps compatibility](#databricks-apps-compatibility). |
| **Catalog '…' or schema '…' not found** | The catalog must exist before deploy; the bundle creates the schema. See [Fix: Catalog or schema not found](#fix-catalog-or-schema-not-found) below. |
| **permission denied for schema public** | App tables use schema `payment_analysis` by default. Set **LAKEBASE_SCHEMA** (e.g. `payment_analysis`) in the app environment if needed; the app creates the schema if it has permission. |
| **Databricks credentials not configured; cannot update app_config** | Either enable **user authorization (OBO)** and open the app from Compute → Apps (so your token is used), or set **DATABRICKS_HOST**, **DATABRICKS_WAREHOUSE_ID**, and optionally **DATABRICKS_TOKEN** in the app environment. **Compute → Apps → payment-analysis → Edit → Environment**; add variables, Save, then restart the app. |
| **Error loading app spec from app.yml** | Ensure **`app.yml`** exists at project root (runtime spec for the app container). Redeploy. |
| **Web UI shows "API only" / fallback page** | The app could not find `src/payment_analysis/__dist__`. Ensure `source_code_path` is `${workspace.root_path}`. (1) Run **`uv run apx build`** then **`databricks bundle deploy -t dev`** so `__dist__` is built and synced. (2) Restart the app from **Compute → Apps**. (3) Check app **Logs** for "UI dist candidate". (4) If needed, set **UI_DIST_DIR** in the app Environment to the full path of the `__dist__` folder. |
| **Logs show "Uvicorn running on http://0.0.0.0:8000"** | This is **expected** when the app runs as a Databricks App. The process binds to `0.0.0.0:8000` inside the app container; the platform proxies requests to it. You are not running on localhost — the app is deployed in Databricks. |
| **Provided OAuth token does not have required scopes** | PAT lacks permissions or OAuth env vars conflict. See [Fix: PAT / token scopes](#fix-pat--token-scopes) below. |
| **403 Forbidden / Invalid scope** (SQL or Setup) | User token from Compute → Apps lacks the **sql** scope. In **Compute → Apps → payment-analysis → Edit → Configure → Authorization scopes**, add **sql**, then **Save** and **restart** the app. See [Deploy app as a Databricks App](#deploy-app-as-a-databricks-app) above. |
| **Failed to export ... type=mlflowExperiment** | An old MLflow experiment exists under the app path. Delete it in the workspace, then redeploy. See [Fix: export mlflowExperiment](#fix-failed-to-export--typemlflowexperiment) below. |
| **Node named '…' already exists** (dashboard deploy) | The 12 dashboards already exist in the workspace. In **`databricks.yml`**, keep **`resources/dashboards.yml`** commented in the `include` list so the bundle does not try to create them again. Deploy will then succeed; existing dashboards are unchanged. For a **clean workspace** (first deploy), uncomment `resources/dashboards.yml` to create the dashboards. |

### Fix: Lakebase project/endpoint not found

**Error:** `Lakebase project/endpoint not found: 'projects/payment-analysis-db/branches/production/endpoints/primary'.`

The job is using the default bundle variables (`lakebase_project_id`, `lakebase_branch_id`, `lakebase_endpoint_id`), but that Lakebase Autoscaling project does not exist in your workspace (the bundle may not create it if the CLI reports "unknown field: postgres_project").

**Option A — Create programmatically (recommended):** From the repo root, authenticate with `databricks auth login`, then run:

```bash
uv run python scripts/create_lakebase_autoscaling.py
```

This creates the project, branch, and endpoint with IDs matching the bundle defaults (`payment-analysis-db`, `production`, `primary`). Job 1 parameters are already set to these in the bundle; redeploy so the job and app use them: `./scripts/bundle.sh deploy dev`. To use different IDs, pass `--project-id`, `--branch-id`, `--endpoint-id` and then redeploy with the same `--var` values. Optionally pass `--job-id <job_id>` to update the deployed job’s base_parameters without redeploying.

**Option B — Create in the UI:** (1) In the workspace go to **Compute → Lakebase** and create a Lakebase (Postgres) project, branch, and endpoint. (2) Note the **project ID**, **branch ID**, and **endpoint ID**. (3) Redeploy with those IDs:  
`./scripts/bundle.sh deploy dev --var lakebase_project_id=YOUR_PROJECT_ID --var lakebase_branch_id=YOUR_BRANCH_ID --var lakebase_endpoint_id=YOUR_ENDPOINT_ID`  
Or set them in **databricks.yml** under `targets.dev.variables`. Then run Job 1 again from **Setup & Run**. See [Lakebase projects](https://docs.databricks.com/oltp/projects/).

### Fix: Catalog or schema not found

**Error:** `Catalog 'ahs_demos_catalog' or schema 'dev_ariel_hdez_payment_analysis' not found in this workspace. Create the Unity Catalog and schema (see this guide), or run the job with notebook_params catalog= schema=.`

The bundle creates the **schema** and volumes; it does **not** create the **catalog**. The catalog must already exist in the workspace.

**Option A — Use the default catalog name:** (1) Create the catalog in **Data** → **Catalogs** → **Create catalog** (e.g. `ahs_demos_catalog`). (2) Redeploy: `./scripts/bundle.sh deploy dev` (or `--var catalog=your_catalog_name --var schema=dev_ariel_hdez_payment_analysis`). (3) Run jobs again from **Setup & Run**.

**Option B — Use an existing catalog:** Deploy with `./scripts/bundle.sh deploy dev --var catalog=YOUR_EXISTING_CATALOG --var schema=dev_ariel_hdez_payment_analysis`. In the app, **Setup & Run** → set **Catalog** and **Schema** → **Save catalog & schema**. Run jobs again.

**Option C — Let Job 1 create catalog and schema:** Job 1’s first task (`ensure_catalog_schema`) creates the Unity Catalog and schema if they do not exist. Requires metastore admin or CREATE_CATALOG/CREATE_SCHEMA. Run **Job 1** once; its first task will create the catalog and schema, then Lakebase init, lakehouse tables, and vector search.

**From the CLI (run job with custom catalog/schema):**

```bash
export DATABRICKS_CATALOG=your_catalog
export DATABRICKS_SCHEMA=dev_ariel_hdez_payment_analysis
uv run python scripts/run_and_validate_jobs.py --job job_1_create_data_repositories
```

### Fix: PAT / token scopes

**Error:** `Provided OAuth token does not have required scopes` (with `auth_type=pat`, `DATABRICKS_HOST`, `DATABRICKS_TOKEN` set; sometimes `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` are also set).

The app uses your **PAT** (`DATABRICKS_TOKEN`) or the forwarded user token (when you open from **Compute → Apps**). If **DATABRICKS_CLIENT_ID** and **DATABRICKS_CLIENT_SECRET** are set, the SDK may still apply OAuth scope checks and fail.

**Fix:** (1) **Remove OAuth client vars when using PAT or OBO** — In **Compute → Apps → payment-analysis → Edit → Environment**, remove or leave empty **DATABRICKS_CLIENT_ID** and **DATABRICKS_CLIENT_SECRET**. Keep **DATABRICKS_HOST**, **DATABRICKS_WAREHOUSE_ID**, and optionally **DATABRICKS_TOKEN**. Save and restart. (2) **Create a new PAT with sufficient scope** — **Settings** → **Developer** → **Access tokens** → **Generate new token**. Ensure your user has token permission "CAN USE" or "CAN MANAGE". Set the new token as **DATABRICKS_TOKEN** in the app environment, then Save and restart. (3) **If the app runs as a service principal** — An admin must grant that SP token permissions, then create a PAT for that SP and set it as **DATABRICKS_TOKEN**.

### Fix: Failed to export … type=mlflowExperiment

The error means an MLflow experiment was created at a path inside the app’s source folder. The training notebook was updated so **new** runs use `…/mlflow_experiments/payment_analysis_models` (outside the app path) — see `src/payment_analysis/ml/train_models.py`. If you still see the error, delete the old experiment manually: **Workspace** → **Users** → **&lt;your-user&gt;** → **payment-analysis** → **src** → **payment_analysis** → **dashboards** → right‑click **payment_analysis_models** → **Delete**. Then redeploy or export again.

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
2. **Run in order from the app:** Open the app → **Setup & Run** → run jobs **1** (Create Data Repositories), **2** (Simulate Transaction Events), **3** (Initialize Ingestion), **4** (Deploy Dashboards), **5** (Train Models & Model Serving), **6** (Deploy AgentBricks Agents), **7** (Genie Space Sync, optional). Start Lakeflow pipelines when needed.
3. **Optional:** Set `DATABRICKS_JOB_ID_*` in the app environment to job IDs from **Workflows** if Run uses a different workspace.

**Estimated time:** 45–60 min. Job/pipeline IDs: **Workflows** / **Lakeflow** or `databricks bundle run <job_name> -t dev`.

## Job inventory and duplicate check

All bundle jobs have been reviewed for duplicates or overlapping functionality. **There are no repeated jobs.** Each job has a single, distinct purpose.

| Job (bundle resource) | Purpose | Notes |
|----------------------|---------|--------|
| **ml_jobs.yml** | | |
| `ensure_catalog_schema` (job 1 task 1) | Create Unity Catalog and schema if they do not exist | First task of job 1; idempotent. Requires CREATE_CATALOG/CREATE_SCHEMA or metastore admin. |
| `create_lakebase_autoscaling` (job 1 task 2) | Create Lakebase Autoscaling project, branch, and endpoint (idempotent) | Uses job params lakebase_project_id, lakebase_branch_id, lakebase_endpoint_id (from bundle vars). Same params are passed to the next task. |
| `lakebase_data_init` (job 1 task 3) | Connect to Lakebase and insert default app_config, approval_rules, online_features table, app_settings | Run after create_lakebase_autoscaling. Backend reads these tables at startup. |
| `lakehouse_bootstrap` (job 1 task 4) | Run `lakehouse_bootstrap.sql`: app_config, rules, recommendations, countries, online_features; seeds app_config, countries, approval_rules | Run once after Lakebase init. Creates all lakehouse tables and default rules. |
| `create_vector_search_index` (job 1 task 5) | Create Vector Search endpoint and delta-sync index from `transaction_summaries_for_search`; MERGE from silver when available | Notebook; run after bootstrap. Skips MERGE if silver table missing so job 1 can complete. |
| `create_gold_views_job` | Run `gold_views.sql`: 12+ analytical views | SQL task; distinct from bootstrap. |
| `train_ml_models_job` | Train 4 ML models (approval, risk, routing, retry); register in UC | Single notebook. |
| `prepare_dashboards_job` | Generate `.build/dashboards/` and `.build/transform/*.sql` with catalog/schema | Run when catalog/schema or source dashboards change; not in Setup & Run UI. |
| `publish_dashboards_job` | Publish dashboards with embed credentials (AI/BI Dashboards API) for app embedding | Does not run prepare; run after deploy. |
| **agents.yml** | | |
| `run_agent_framework` (job 6) | Run full agent framework: orchestrator + all specialists (Smart Routing, Retry, Decline Analyst, Risk, Performance) with one query | Single task; one notebook run builds the framework and executes comprehensive analysis. |
| **streaming_simulator.yml** | | |
| `transaction_stream_simulator` | Generate synthetic payment events (e.g. 1000/s) | Producer only. |
| `continuous_stream_processor` | Process streaming events continuously | Consumer; different notebook. |
| **genie_spaces.yml** | | |
| `job_7_genie_sync` | Sync Genie space configuration and sample questions | Single purpose; optional. |

**Agent framework (job 6):** A single task `run_agent_framework` runs the notebook once. The orchestrator coordinates all five specialists (Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender) and synthesizes the response. For ad-hoc runs of a single specialist, use the same notebook with widget `agent_role` set to that specialist (e.g. `smart_routing`). To use **Databricks AgentBricks** (all five specialists + Multi-Agent Supervisor) with MLflow + LangGraph and Model Serving (UC functions as tools), see [AgentBricks — Payment Analysis](AGENT_FRAMEWORK_DATABRICKS.md).

**Dashboard jobs:** Job 4 (Deploy Dashboards) has two tasks: prepare (generate assets) and publish (AI/BI Dashboards API with embed credentials). Genie sync is a separate job (job 7 in `genie_spaces.yml`).

## Jobs and notebook/SQL reference

All job notebook and SQL paths are relative to the workspace `root_path` (where the bundle syncs). Each path below is verified to exist in the repo (`.py` or generated under `.build/`).

| Bundle resource (YAML key) | App/backend key | Notebook or SQL path | Source file |
|----------------------------|-----------------|----------------------|-------------|
| job_1 task `ensure_catalog_schema` | (task 1 of job 1) | `src/payment_analysis/transform/run_ensure_catalog_schema` | `run_ensure_catalog_schema.py` |
| job_1 task `lakebase_data_init` | (task 2 of job 1) | `src/payment_analysis/transform/run_lakebase_data_init` | `run_lakebase_data_init.py` |
| job_1 task `lakehouse_bootstrap` | `lakehouse_bootstrap` | `run_lakehouse_bootstrap` reads `lakehouse_bootstrap.sql` from workspace_path | `lakehouse_bootstrap.sql` (transform/) |
| job_1 task `create_vector_search_index` | `vector_search_index` | `src/payment_analysis/vector_search/create_index` | `create_index.py` |
| `create_gold_views_job` | `create_gold_views` | `.build/transform/gold_views.sql` | Generated by prepare |
| `transaction_stream_simulator` | `transaction_stream_simulator` | `src/payment_analysis/streaming/transaction_simulator` | `transaction_simulator.py` |
| `train_ml_models_job` | `train_ml_models` | `src/payment_analysis/ml/train_models` | `train_models.py` |
| job_7 task `sync_genie_config` | `genie_sync` | `src/payment_analysis/genie/sync_genie_space` | `sync_genie_space.py` (genie_spaces.yml) |
| job_6 task `run_agent_framework` | `run_agent_framework`, `orchestrator_agent`, `test_agent_framework` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| `publish_dashboards_job` | `publish_dashboards` | `src/payment_analysis/transform/publish_dashboards` | `publish_dashboards.py` |
| `continuous_stream_processor` | `continuous_stream_processor` | `src/payment_analysis/streaming/continuous_processor` | `continuous_processor.py` |
| `prepare_dashboards_job` | (not in Setup UI) | `src/payment_analysis/transform/prepare_dashboards` | `prepare_dashboards.py` |

**Pipelines** (not jobs): `payment_analysis_etl` uses notebooks `streaming/bronze_ingest`, `transform/silver_transform`, `transform/gold_views`. `payment_realtime_pipeline` uses `streaming/realtime_pipeline`. Sync includes `src/payment_analysis/ml`, `streaming`, `transform`, `agents`, `genie`, `vector_search`, so all referenced notebooks are uploaded.

---

**See also:** [Guide](GUIDE.md) — business overview, architecture, project structure, control panel, best practices.
