# Deployment

How to deploy and configure the Payment Analysis app and **Databricks Asset Bundle (DAB)** (Databricks Apps, Lakebase, jobs, dashboards). This project uses [Databricks Asset Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/) for IaC and CI/CD. For architecture and project structure see [Guide](GUIDE.md).

## Prerequisites

Databricks workspace (Unity Catalog), SQL Warehouse, CLI configured. **Catalog and schema:** Either (1) create the **catalog** (default `ahs_demos_catalog`) under **Data → Catalogs** before deploy so the bundle can create the **schema** and volumes, or (2) deploy and run **Job 1** first — its first task creates the catalog and schema if they do not exist (requires metastore admin or CREATE_CATALOG/CREATE_SCHEMA). If you use different names, deploy with `--var catalog=<your_catalog> --var schema=<your_schema>`. Python 3.10+ with `uv`, Node 18+ with `bun`. `package.json` engines `>=22.0.0`. Permissions: jobs, Lakeflow, model serving; write to catalog; deploy to `/Workspace/Users/<you>/payment-analysis`. **Databricks App:** Only `requirements.txt` and `package.json` deps; no system packages. See [Guide](GUIDE.md).

## Quick start

Deployment is **two-phase**: deploy all resources first (no App), then deploy the App after its dependencies (model serving endpoints) exist.

### Phase 1 — deploy resources (no App)

```bash
./scripts/bundle.sh deploy dev
```

This runs **build** (frontend + wheel), **clean** (removes existing BI dashboards to avoid duplicates), **prepare** (writes `.build/dashboards/` and `.build/transform/*.sql` with catalog/schema), **deploy** (jobs, pipelines, dashboards, UC — everything except the App and model serving), and **publish** (embed credentials). Model serving and app serving bindings are temporarily excluded.

Output: *"all resources deployed except the App. Run jobs 5 and 6. After completion, write the prompt `deploy app`"*.

After phase 1, run **Job 5 (Train Models)** and **Job 6 (Deploy Agents)** from the app **Setup & Run** so ML models and agent registrations exist in UC.

### Phase 2 — deploy app

```bash
./scripts/bundle.sh deploy app dev
```

This **validates** that all app dependencies exist (runs `toggle_app_resources.py --check-app-deployable`), **uncomments** `model_serving.yml` in `databricks.yml` and serving endpoint bindings in `fastapi_app.yml`, **validates** the bundle, then **deploys** the App with all resources assigned.

Output: *"App deployed with all dependencies and resources assigned and uncommented."*

### Automated two-phase deploy

```bash
./scripts/deploy_with_dependencies.sh dev
```

Runs phase 1, automatically executes Job 5 and Job 6 and waits for completion, then runs phase 2. Single command for the full flow.

### Validate without deploying

```bash
./scripts/bundle.sh validate dev
```

**ORCHESTRATOR_SERVING_ENDPOINT** can be set in **`app.yml`** at project root (e.g. `payment-analysis-orchestrator`); redeploy to apply. You can also override in **Compute → Apps → payment-analysis → Edit → Environment**.

## Steps at a glance

Jobs are consolidated into **7 numbered steps** (prefix in job name). Run in order: **1 → 2 → 3 → 4 → 5 → 6 → 7**. Pipelines (Lakeflow ETL and Real-time) are separate resources; start them when needed.

| # | Job (step) | Action |
|---|------------|--------|
| 0 | Deploy bundle | `./scripts/bundle.sh deploy dev` (includes prepare; no missing files) |
| 1 | **1. Create Data Repositories** | **Setup & Run** → Run job 1 (ensure catalog & schema → **create Lakebase Autoscaling** project/branch/endpoint → **Lakebase data init** — app_config, approval_rules, online_features, app_settings → lakehouse bootstrap → vector search). Run once. Creates everything needed for later jobs and the app. |
| 2 | **2. Simulate Transaction Events** | **Setup & Run** → Run **Transaction Stream Simulator** (producer; events ingested later by pipelines) |
| — | **Pipeline (before Step 3)** | Start **Payment Analysis ETL** (Lakeflow) at least once so it creates `payments_enriched_silver` (and `payments_raw_bronze`) in the catalog/schema. Step 3 (Gold Views) depends on this table. |
| 3 | **3. Initialize Ingestion** | **Setup & Run** → Run job 3 (create gold views → **create UC agent tools** → sync vector search; requires pipeline so `payments_enriched_silver` exists) |
| 4 | **4. Deploy Dashboards** | **Setup & Run** → Run job 4 (prepare assets → publish dashboards with embed credentials) |
| 5 | **5. Train Models & Model Serving** | **Setup & Run** → Run **Train Payment Approval ML Models** (~10–15 min); then uncomment `model_serving.yml`, redeploy |
| 6 | **6. Deploy Agents** | **Setup & Run** → Run **Deploy Agents** (same job: 3 tasks — `run_agent_framework`, `register_responses_agent`, `register_agentbricks`) |
| 7 | **7. Genie Space Sync** | **Setup & Run** → Run **Genie Space Sync** (optional; syncs Genie space config and sample questions for natural language analytics) |
| — | Pipelines | **Setup & Run** → Start **Payment Analysis ETL** (required before Step 3) and/or **Real-Time Stream** (Lakeflow; when needed) |
| — | Dashboards & app | 3 unified dashboards + app deployed by bundle |
| — | Verify | **Dashboard**, **Rules**, **Decisioning**, **ML Models** in app |

All jobs and pipelines can be run from the UI. To connect: use your credentials (open app from **Compute → Apps**) or set **DATABRICKS_TOKEN** (PAT) in the app environment. When you open the app from Compute → Apps (or with PAT set), the Setup & Run page resolves job and pipeline IDs from the workspace by name so you can run steps without setting `DATABRICKS_JOB_ID_*` / `DATABRICKS_PIPELINE_ID_*`. See **Setup & Run → Connect to Databricks**.

## Required resources and scopes for the app

The app is configured in the bundle with the following so it can be deployed and used for approval-rate analysis:

| What | Where | Purpose |
|------|--------|--------|
| **SQL warehouse** | `resources/fastapi_app.yml` → `sql-warehouse` | Analytics, app_config, gold views; permission CAN_USE. |
| **Jobs 1–7** | `resources/fastapi_app.yml` → `job-1-data-repositories` … `job-7-genie` | Setup & Run from the app; each CAN_MANAGE_RUN. |
| **User authorization scopes** | `resources/fastapi_app.yml` → `user_api_scopes` | When users open the app from Compute → Apps: `sql`, `dashboards.genie`, `files.files`, `serving.serving-endpoints`, `vectorsearch.vector-search-indexes`, `catalog.connections`, `catalog.catalogs:read`, `catalog.schemas:read`, `catalog.tables:read` so the app can run SQL, Genie, files, model serving, vector search, and Unity Catalog on their behalf. |
| **Unity Catalog** | `resources/unity_catalog.yml` | Schema and volumes used by pipelines, jobs, and dashboards. |
| **Lakebase** | Job 1 + app env `LAKEBASE_*` | Postgres for app_config, approval_rules, online_features; app connects via env vars. |
| **Dashboards** | `resources/dashboards.yml` | Three unified dashboards (Data & Quality, ML & Optimization, Executive & Trends). |

**App resources in the bundle** (`resources/fastapi_app.yml`): SQL warehouse, UC volume (reports). Model serving endpoint bindings are **commented out** by default; uncomment after endpoints exist (two-phase deploy or manual). See [REFERENCE.md](REFERENCE.md) for model serving and UC functions. **Genie** is commented out (set `--var genie_space_id=<uuid>` to uncomment). For **full configuration**, add in **Compute → Apps → payment-analysis → Edit → Configure → App resources**: **UC function** (all 11 agent tools, Can execute), **Vector search index** (Can select), **MLflow experiment** (Can read), **Database** (Lakebase), **UC connection** (Use connection).

**App environment:** Defaults and app-specific vars (e.g. **LAKEBASE_***, **ORCHESTRATOR_SERVING_ENDPOINT**) are defined in **`app.yml`** at project root; redeploy the bundle to apply changes. You can **override** in **Compute → Apps → payment-analysis → Edit → Environment** (e.g. DATABRICKS_WAREHOUSE_ID, DATABRICKS_TOKEN). If you use **user authorization (OBO)**, open the app from **Compute → Apps** so the user token is forwarded (see **User token (OBO)** in the table section below); the bundle configures user API scopes in `fastapi_app.yml`.

## Deploy app as a Databricks App

**Deploy into Databricks App** (create/update the app in the workspace and make the UI available):

1. **Deploy bundle:** Run `./scripts/bundle.sh deploy dev`. This runs prepare (generates `.build/dashboards/`, `.build/transform/gold_views.sql`, `.build/transform/lakehouse_bootstrap.sql`), builds the UI (`uv run apx build` via `artifacts.default.build`), and deploys. All job SQL files exist after deploy.
2. **Start the app:** In the workspace go to **Compute → Apps → payment-analysis → Start**, or run `databricks bundle run payment_analysis_app -t dev`. The app runs in Databricks (not on your machine). Logs showing **"Uvicorn running on http://0.0.0.0:8000"** are expected: the app binds to that address inside the container and the Databricks platform proxies external traffic to it.
3. **App URL:** Open the app from the Apps page or use the URL from **databricks bundle summary**.
4. **Required env (Workspace → Apps → payment-analysis → Edit → Environment):**

| Variable | Purpose |
|----------|---------|
| **LAKEBASE_PROJECT_ID** | Lakebase Autoscaling project ID (same as Job 1; e.g. `payment-analysis-db`). Not needed if using **LAKEBASE_CONNECTION_STRING**. |
| **LAKEBASE_BRANCH_ID** | Lakebase Autoscaling branch (e.g. `production`). Not needed if using LAKEBASE_CONNECTION_STRING. |
| **LAKEBASE_ENDPOINT_ID** | Lakebase Autoscaling endpoint (e.g. `primary`). Not needed if using LAKEBASE_CONNECTION_STRING. |
| **LAKEBASE_CONNECTION_STRING** | Optional. Direct Postgres URL (e.g. `postgresql://user%40domain@ep-xxx.database.region.azuredatabricks.net/databricks_postgres?sslmode=require`). When set, app uses this instead of project/branch/endpoint discovery. |
| **LAKEBASE_OAUTH_TOKEN** | Required when **LAKEBASE_CONNECTION_STRING** is set. OAuth token used as Postgres password. **Never commit this value**; set only in the app Environment (Compute → Apps → Edit → Environment). Token expires (e.g. ~1h); refresh or use project/branch/endpoint + SDK credential for long-lived runs. |
| **DATABRICKS_WAREHOUSE_ID** | Required for SQL/analytics. SQL Warehouse ID (from bundle or sql-warehouse binding). |
| **DATABRICKS_HOST** | Optional when opened from **Compute → Apps** (workspace URL derived from request). Set when not using OBO. |
| **DATABRICKS_TOKEN** | Optional when using OBO. Open from **Compute → Apps** so your token is forwarded; do not set in env. Set only for app-only use; then do **not** set DATABRICKS_CLIENT_ID/SECRET. |
| **ORCHESTRATOR_SERVING_ENDPOINT** | Optional. When set (e.g. `payment-analysis-orchestrator`), the app’s Orchestrator chat calls this Model Serving endpoint (AgentBricks/Supervisor) instead of Job 6. Can be set in `app.yml` or App Environment. See [REFERENCE.md](REFERENCE.md). |
| **LAKEBASE_SCHEMA** | Optional. Postgres schema for app tables (default `payment_analysis`). Use when the app has no CREATE on `public`. |

**User token (OBO):** When the app is opened from **Compute → Apps**, Databricks forwards the user token in the **X-Forwarded-Access-Token** header. The backend reads it in `src/payment_analysis/backend/dependencies.py` via `_get_obo_token(request)` and uses it for warehouse queries and run job. No DATABRICKS_TOKEN is required in the app environment when using OBO.

**Use your credentials (recommended):** Open the app from **Workspace → Compute → Apps → payment-analysis**. The platform forwards your token; no DATABRICKS_TOKEN or DATABRICKS_HOST is required in the app environment. The app then uses that logged-in user token for all Databricks resources (SQL Warehouse, Genie, files, model serving, vector search, Unity Catalog, jobs, dashboards). The bundle configures **user authorization scopes** in `resources/fastapi_app.yml`; if your workspace uses different scope names, add or adjust them in **Edit → Configure → User authorization**. If you see 403 Invalid scope, ensure the required scope (e.g. **sql**) is in the list and restart. If Run stays disabled, click **Refresh job IDs** on the Setup page.

5. **Optional — override job/pipeline IDs:** Set `DATABRICKS_JOB_ID_*`, `DATABRICKS_PIPELINE_ID_*`, `DATABRICKS_WORKSPACE_ID` per [Guide — Workspace ↔ UI mapping](GUIDE.md#4-workspace-components--ui-mapping).

App resource: `resources/fastapi_app.yml`. Runtime spec: `app.yml` at project root. See [App spec error](#app-spec-error).

## App configuration and resource paths

**Bundle root:** Directory containing `databricks.yml`. **App source:** `source_code_path` in `resources/fastapi_app.yml` is `${workspace.root_path}` (e.g. `.../payment-analysis`). Sync uploads to the same root path; the app runs from there so `src/payment_analysis/__dist__` is found for the web UI.

**Included resources** (order in `databricks.yml`): `unity_catalog`, `lakebase`, `pipelines`, `sql_warehouse`, `ml_jobs`, `agents`, `streaming_simulator`, `genie_spaces`, `dashboards`, `fastapi_app`. **Commented by default:** `model_serving` (uncomment after Step 5; use two-phase deploy if app bindings are enabled); serving endpoint blocks in `fastapi_app.yml` (uncomment when endpoints exist). **Dashboard overwrite:** `bundle.sh deploy` cleans existing BI dashboards in the workspace (except `dbdemos*`) before deploy to avoid duplicates.

**Paths:**  
- Workspace root: `/Workspace/Users/${user}/${var.workspace_folder}` (default folder: `payment-analysis`).  
- Notebooks/jobs: `${workspace.root_path}/src/payment_analysis/...` (e.g. `ml/train_models`, `streaming/transaction_simulator`, `agents/agent_framework`).
- SQL for jobs: `${workspace.root_path}/.build/transform/gold_views.sql` and `lakehouse_bootstrap.sql` (both generated by `scripts/dashboards.py prepare` with USE CATALOG/SCHEMA).
- Dashboards: `file_path` in `resources/dashboards.yml` is `../.build/dashboards/*.lvdash.json` (relative to `resources/`).  
- Sync (uploaded to workspace): `.build`, `src/payment_analysis/ml`, `streaming`, `transform`, `agents`, `genie`.

**App bindings:** sql-warehouse (`payment_analysis_warehouse`), jobs 1–7 in execution order (create repos, simulator, ingestion, deploy dashboards, train ML, agents, Genie sync). Lakebase: use Autoscaling only; set LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID in app Environment (Job 1 create_lakebase_autoscaling creates the project). Optional: genie-space, model serving endpoints (see comments in `fastapi_app.yml`).

Validate before deploy: `./scripts/bundle.sh validate dev` (runs dashboard prepare then `databricks bundle validate`).

#### Databricks feature alignment

The solution is built entirely on Databricks-native features and current product naming (Lakeflow, Unity Catalog, PRO serverless SQL warehouse, Lakebase Autoscaling, Databricks App, Genie, Model Serving, Lakeview dashboards). A full checklist and recommendations are in [REFERENCE.md](REFERENCE.md). Re-check when adding resources or upgrading the Databricks SDK.

#### Dashboard visuals not showing?

Following the [dbdemos](https://github.com/databricks-demos/dbdemos) pattern, dashboards must be **prepared**, **deployed**, and **published** so that visuals and embeds work:

1. **Prepare** (writes `.build/dashboards/*.lvdash.json` and `.build/transform/*.sql` with catalog/schema):  
   Run **before** every bundle validate/deploy:  
   `uv run python scripts/dashboards.py prepare` (or `--catalog X --schema Y` for prod).  
   The bundle reads dashboard definitions from `.build/dashboards/`; if these files are missing, deploy fails with "failed to read serialized dashboard from file_path".

2. **Deploy** with dashboards included: `resources/dashboards.yml` is included by default. **`./scripts/bundle.sh deploy dev`** cleans existing BI dashboards in the workspace (except `dbdemos*`) then deploys so the 3 unified dashboards are created/overwritten without "Node named '...' already exists" errors.

3. **Publish** (embed credentials): After deploy, run  
   `uv run python scripts/dashboards.py publish`  
   so each dashboard is published with **embed credentials**. Without this, iframes in the app may load but show no visuals. The deploy script runs publish automatically; if it was skipped, run it manually.

4. **Data**: Gold views and Lakeflow tables must exist and have data. Run **Job 3** (Initialize Ingestion / Create Gold Views) and the **Lakeflow ETL pipeline** so `v_executive_kpis`, `payments_enriched_silver`, etc. exist in the catalog/schema used by the dashboards. Empty or missing tables produce empty charts.

5. **Embedded dashboards show "refused to connect"**: The app embeds dashboards in an iframe pointing at your workspace (e.g. `https://adb-<workspace-id>.<region>.azuredatabricks.net/...`). The workspace **Embed dashboards** policy must allow that. Have a workspace admin: go to **Settings → Security**, scroll to **External access → Embed dashboards**, and set the policy to **Allow** or **Allow approved domains** and add the app domain (e.g. `*.azure.databricksapps.com` or `*.cloud.databricksapps.com`). See [Manage dashboard embedding](https://docs.databricks.com/aws/en/ai-bi/admin/embed).

### Why tables and views may be empty

Tables and views in `ahs_demos_catalog.payment_analysis` (or your catalog/schema) are populated by **jobs** and **Lakeflow pipelines**. If dashboards or the app show no data:

- **Silver tables** (e.g. `payments_enriched_silver`, `merchant_visible_attempts_silver`): Created by the **Payment Analysis ETL** Lakeflow pipeline. They stay empty until the pipeline runs and source bronze data exists. Run the pipeline from **Setup & Run** (step 8) or `uv run python scripts/run_and_validate_jobs.py --run-pipelines`.
- **Gold views** (e.g. `v_executive_kpis`, `v_top_decline_reasons`): Created by **Job 3** (Initialize Ingestion). They read from `payments_enriched_silver`; if silver is empty, views return no rows. Run Job 3 **after** the ETL pipeline has produced silver.
- **Streaming views** (e.g. `v_streaming_ingestion_by_second`, `v_silver_processed_by_second`): Depend on `payments_raw_bronze`. Job 3 creates a stub bronze table if missing, but rows appear only when the **Real-Time** pipeline and ingestion (e.g. transaction simulator) run.
- **Bootstrap views** (e.g. `v_recommendations_from_lakehouse`, `v_approval_rules_active`): Created by **Job 1** (Create Data Repositories, task `lakehouse_bootstrap`). Base tables are seeded (e.g. approval_rules, countries) when empty.

For a full list of tables/views, whether each is required, where it is used, and schema cleansing options, see **[Schema: Tables and Views Reference](SCHEMA_TABLES_VIEWS.md)**.

### Workspace layout: root vs files/

Databricks Asset Bundles use two workspace path concepts:

| Concept | Purpose | In this bundle |
|--------|----------|----------------|
| **`workspace.root_path`** | Path used by **jobs** (notebook_path), **pipelines** (path), **app** (source_code_path), and **dashboards** (parent_path). All resource paths are under `root_path`. | `/Workspace/Users/<user>/payment-analysis` |
| **`workspace.file_path`** | Path where the CLI **syncs** (uploads) bundle files when you run `databricks bundle deploy`. If unset, the CLI defaults to `root_path/files`, which creates a second copy. | Set to **`${workspace.root_path}`** so sync writes to the same folder as jobs and the app. |

**Which files are used at runtime?**

- **Jobs and pipelines** run notebooks from **`${workspace.root_path}/src/payment_analysis/...`** (e.g. `agents/agentbricks_register`, `ml/train_models`).
- The **Databricks App** runs with **`source_code_path: ${workspace.root_path}`**, so it sees `src/payment_analysis/__dist__`, `src/payment_analysis/backend`, etc., at the root.
- **Sync** (from `databricks bundle deploy`) uploads everything in `sync.include` to **`file_path`**. With `file_path: ${workspace.root_path}`, that content lands in the same folder, so there is a single tree and no duplicate `files/` copy.

If you see both a root folder and a `files/` folder with the same content, the CLI was using the default (sync to `root_path/files`) while jobs and app point at `root_path`. The **code that runs** is always the one under **`root_path`** (e.g. `.../payment-analysis/src/...`). To avoid duplication, this bundle sets **`file_path: ${workspace.root_path}`** so sync and runtime use the same path.

### Why one databricks.yml

- **Source of truth:** The file at **repo root** `databricks.yml` is the only one used for `databricks bundle validate -t dev` and `databricks bundle deploy -t dev`. The bundle CLI runs from the project root and reads only the root `databricks.yml`.
- **Workspace path:** In root `databricks.yml`, `workspace.root_path` is the workspace folder (e.g. `.../payment-analysis`). **`workspace.file_path`** is set to **`${workspace.root_path}`** so bundle sync uploads to the same path as jobs and the app (no separate `files/` copy). Jobs, pipelines, and the app all reference **`root_path`** (e.g. `root_path/src/payment_analysis/agents/agent_framework`). See [Workspace layout: root vs files/](#workspace-layout-root-vs-files) below.
- **No duplicate config:** Do not commit workspace mirrors. If you previously had a `files/` subfolder from an older DAB default, you can remove it after setting `file_path: ${workspace.root_path}` and redeploying.

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

**Direct dependencies (exact versions):** databricks-sdk 0.88.0, fastapi 0.129.0, uvicorn 0.40.0, pydantic-settings 2.6.1, sqlmodel 0.0.27, psycopg[binary,pool] 3.2.3. Dev: ty 0.0.14, apx 0.2.6. Transitive versions are fixed in `uv.lock` and reflected in `requirements.txt` by the sync script.

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

## Schema consistency

Schema name is always **`payment_analysis`** — the same in dev and prod. DAB schema prefixing is disabled via `experimental.skip_name_prefix_for_schema: true` in `databricks.yml`.

| Where | How it's set |
|-------|--------------|
| Bundle `var.schema` (root default) | **`payment_analysis`** |
| Bundle `var.schema` (dev target) | **`payment_analysis`** |
| Bundle `var.schema` (prod target) | **`payment_analysis`** |
| Job notebook params | `${var.schema}` → always `payment_analysis` |
| Lakebase Postgres | `lakebase_schema: "payment_analysis"` in job params; `LAKEBASE_SCHEMA` env default `payment_analysis` |
| Backend | `get_default_schema()`: uses `DATABRICKS_SCHEMA` if set; else **`payment_analysis`** |
| Dashboard prepare | Placeholder **`__CATALOG__.__SCHEMA__`**; `bundle.sh` passes `payment_analysis` to prepare |
| Notebook widget defaults | **`payment_analysis`** (jobs override via params) |

Effective catalog/schema for the app come from Lakehouse `app_config`; set via **Setup & Run** → **Save catalog & schema**. Save with schema = **`payment_analysis`** so dashboards and jobs align.

## Resources in the workspace

By default: Workspace folder, Lakebase, Jobs (7 steps: create repositories, simulate events, initialize ingestion, deploy dashboards, train models, deploy agents, Genie sync), 2 pipelines, SQL warehouse, Unity Catalog, 3 unified dashboards, Databricks App. **Optional:** Uncomment `resources/model_serving.yml` after Step 5 (Train ML models); create Vector Search manually from `resources/vector_search.yml` if not in bundle.

## Where to find resources

- **Workspace:** **Workspace** → **Users** → you → **payment-analysis**
- **Jobs:** **Workflow** → `[dev …]` job names
- **Lakeflow:** **Lakeflow** → ETL and Real-Time Stream
- **SQL Warehouse:** **SQL** → **Warehouses**
- **Catalog / Dashboards:** **Data** → Catalogs; **SQL** → **Dashboards**

**Dashboard TABLE_OR_VIEW_NOT_FOUND:** Run **Create Gold Views** (and **Lakehouse Bootstrap** if Rules/Decisioning are empty) in the same catalog.schema as prepare. Validate: `uv run python scripts/dashboards.py validate-assets --catalog X --schema Y`.

## Databricks Apps compatibility

**Environment (official):** Python 3.11, Ubuntu 22.04 LTS, Node.js 22.16. [Pre-installed Python libraries](https://docs.databricks.com/en/dev-tools/databricks-apps/system-env#pre-installed-python-libraries) include databricks-sdk 0.33.0, fastapi 0.115.0, uvicorn[standard] 0.30.6, and others (streamlit, dash, flask, etc.).

**Our `requirements.txt`:** Overrides three pre-installed packages (databricks-sdk → 0.88.0, fastapi → 0.129.0, uvicorn → 0.40.0) and adds pydantic-settings, sqlmodel, psycopg[binary] plus transitive pins. Overriding is supported; pinning exact versions is recommended by Databricks. Our overrides are within the same major/minor line and are tested.

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
| **403 Forbidden / Invalid scope** (SQL or Setup) | User token from Compute → Apps lacks a required scope. In **Compute → Apps → payment-analysis → Edit → Configure → User authorization**, ensure the needed scope (e.g. **sql**) is listed, then **Save** and **restart** the app. See [Deploy app as a Databricks App](#deploy-app-as-a-databricks-app) above. |
| **Failed to export ... type=mlflowExperiment** | An old MLflow experiment exists under the app path. Delete it in the workspace, then redeploy. See [Fix: export mlflowExperiment](#fix-failed-to-export--typemlflowexperiment) below. |
| **Node named '…' already exists** (dashboard deploy) | Run **`./scripts/bundle.sh deploy dev`** so it cleans existing BI dashboards (except `dbdemos*`) then deploys; the 3 unified dashboards are overwritten. If you run `databricks bundle deploy` directly without the script, clean dashboards manually or comment out `resources/dashboards.yml` temporarily. |

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

### Lakebase tables and Unity Catalog registration

**Tables in the Lakebase project (Postgres):** Job 1 task **lakebase_data_init** creates and seeds these in your Lakebase database (schema from `lakebase_schema`, default `payment_analysis`):

| Table | Purpose |
|-------|---------|
| **app_config** | Catalog and schema used by the app (single row). |
| **approval_rules** | Business rules for approval/retry/routing; app and agents read/write here when Lakebase is configured. |
| **online_features** | ML/AI feature output for the app. |
| **app_settings** | Key-value config (warehouse_id, default_events_per_second, etc.). |
| **countries** | Entities for the UI filter dropdown (same seed as Lakehouse). |

The app uses these when **LAKEBASE_PROJECT_ID**, **LAKEBASE_BRANCH_ID**, and **LAKEBASE_ENDPOINT_ID** are set in the app Environment. Rules and countries are read from Lakebase first, then fall back to the Lakehouse (Unity Catalog) tables if Lakebase is unavailable.

**Register the Lakebase database in Unity Catalog (optional):** To expose this Lakebase database in Catalog Explorer and query it from SQL warehouses (unified governance, dashboards, cross-source analytics), register it as a UC catalog:

1. In the workspace open **Lakehouse** → **Catalog Explorer** → **Create** → **Create catalog**.
2. Choose **Lakebase Postgres** → **Autoscaling**, then select your **project**, **branch**, and **Postgres database**.
3. Enter a catalog name (e.g. `payment_analysis_lakebase`) and create.

After registration, the catalog is read-only in UC; data is still managed in Lakebase. See [Register a Lakebase database in Unity Catalog](https://docs.databricks.com/en/oltp/projects/register-uc).

### Fix: Catalog or schema not found

**Error:** `Catalog 'ahs_demos_catalog' or schema '...' not found in this workspace.` Create the Unity Catalog and schema (see this guide), or run the job with notebook_params catalog= schema=.

The bundle creates the **schema** and volumes; it does **not** create the **catalog**. The catalog must already exist in the workspace.

**Option A — Use the default catalog name:** (1) Create the catalog in **Data** → **Catalogs** → **Create catalog** (e.g. `ahs_demos_catalog`). (2) Redeploy: `./scripts/bundle.sh deploy dev` (schema = `payment_analysis`). (3) Run jobs again from **Setup & Run**.

**Option B — Use an existing catalog:** Deploy with `./scripts/bundle.sh deploy dev --var catalog=YOUR_EXISTING_CATALOG` (schema = `payment_analysis`). In the app, **Setup & Run** → set **Catalog** and **Schema** → **Save catalog & schema**. Run jobs again.

**Option C — Let Job 1 create catalog and schema:** Job 1’s first task (`ensure_catalog_schema`) creates the Unity Catalog and schema if they do not exist. Requires metastore admin or CREATE_CATALOG/CREATE_SCHEMA. Run **Job 1** once; its first task will create the catalog and schema, then Lakebase init, lakehouse tables, and vector search.

**From the CLI (run job with custom catalog/schema):**

```bash
export DATABRICKS_CATALOG=your_catalog
export DATABRICKS_SCHEMA=payment_analysis
uv run python scripts/run_and_validate_jobs.py --job job_1_create_data_repositories
```

### Fix: payments_enriched_silver not found (Job 3)

**Error:** `The table payments_enriched_silver was not found in <catalog>.<schema>. Gold views require the silver table from the Lakeflow pipeline.`

Job 3 (Initialize Ingestion) creates gold views from the silver table. The silver table is produced by the **Lakeflow pipeline** "8. Payment Analysis ETL", not by a job. Run the pipeline at least once before Job 3.

**Option A — From the app:** **Setup & Run** → **Pipelines** → start **8. Payment Analysis ETL**. Wait until the pipeline run completes (pipeline shows idle). Then run **Job 3** (Initialize Ingestion).

**Option B — From the CLI (run pipeline then Job 3):**

```bash
uv run python scripts/run_and_validate_jobs.py --run-pipelines --job job_3_initialize_ingestion
```

This starts the ETL pipeline, waits until it is idle (up to ~25 minutes), then runs Job 3. To run all jobs in order with the pipeline first: `uv run python scripts/run_and_validate_jobs.py --run-pipelines`.

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
| **bundle.sh** | Two-phase deploy: `deploy [target]` (phase 1: resources, no App); `deploy app [target]` (phase 2: App with model serving); `validate` / `verify` for checks. Also: `redeploy` = same as `deploy`. |
| **deploy_with_dependencies.sh** | Automated two-phase deploy: phase 1 → runs Job 5 & 6 → phase 2. Single command. |
| **toggle_app_resources.py** | Toggle serving endpoint bindings in `fastapi_app.yml`: `--enable-serving-endpoints`, `--disable-serving-endpoints`, `--check-app-deployable`. Used by bundle.sh and deploy_with_dependencies.sh. |
| **dashboards.py** | **prepare** (by bundle.sh): writes `.build/dashboards/`, `.build/transform/gold_views.sql`, `.build/transform/lakehouse_bootstrap.sql` with catalog/schema. **validate-assets**, **publish** (optional). Run: `uv run python scripts/dashboards.py` |
| **run_and_validate_jobs.py** | Run and validate bundle jobs; optional `--run-pipelines` runs ETL pipeline and waits before running jobs. `pipelines` lists pipelines. Run: `uv run python scripts/run_and_validate_jobs.py [--run-pipelines] [--job KEY]` |
| **sync_requirements_from_lock.py** | Generate `requirements.txt` from `uv.lock` for the Databricks App. Run after `uv lock`: `uv run python scripts/sync_requirements_from_lock.py` |

## Demo setup & one-click run

1. **Deploy once:** `./scripts/bundle.sh deploy dev` (prepare + build + deploy; all job files present).
2. **Run in order from the app:** Open the app → **Setup & Run** → run jobs **1** (Create Data Repositories), **2** (Simulate Transaction Events), **3** (Initialize Ingestion), **4** (Deploy Dashboards), **5** (Train Models & Model Serving), **6** (Deploy Agents), **7** (Genie Space Sync, optional). Start Lakeflow pipelines when needed.
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
| `train_models` | Train 4 ML models (approval, risk, routing, retry); register in UC | Single notebook. |
| `prepare_dashboards_job` | Generate `.build/dashboards/` and `.build/transform/*.sql` with catalog/schema | Run when catalog/schema or source dashboards change; not in Setup & Run UI. |
| `publish_dashboards_job` | Publish dashboards with embed credentials (AI/BI Dashboards API) for app embedding | Does not run prepare; run after deploy. |
| **agents.yml** | | |
| `run_agent_framework` (job 6) | Run full agent framework: orchestrator + all specialists (Smart Routing, Retry, Decline Analyst, Risk, Performance) with one query | Single task; one notebook run builds the framework and executes comprehensive analysis. |
| **streaming_simulator.yml** | | |
| `transaction_stream_simulator` | Generate synthetic payment events (e.g. 1000/s) | Producer only. |
| `continuous_stream_processor` | Process streaming events continuously | Consumer; different notebook. |
| **genie_spaces.yml** | | |
| `job_7_genie_sync` | Sync Genie space configuration and sample questions | Single purpose; optional. |

**Agent framework (job 6):** A single task `run_agent_framework` runs the notebook once. The orchestrator coordinates all five specialists (Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender) and synthesizes the response. For ad-hoc runs of a single specialist, use the same notebook with widget `agent_role` set to that specialist (e.g. `smart_routing`). To use **Databricks AgentBricks** (all five specialists + Multi-Agent Supervisor) with MLflow + LangGraph and Model Serving (UC functions as tools), see [REFERENCE.md](REFERENCE.md).

**Why don't I see agents in AgentBricks?** Job 6 runs a **Python notebook** (`agent_framework.py`) that implements the orchestrator and five specialists in code. It does **not** create or register agents in the workspace **Agents** (AgentBricks) UI. To see agents in **Agents** / AgentBricks you must follow the full conversion: create UC tool functions, build LangGraph agents, log/register with MLflow, deploy to Model Serving, and configure the **Multi-Agent Supervisor** in the workspace. See [REFERENCE.md](REFERENCE.md).

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
| `train_models` | `train_models` | `src/payment_analysis/ml/train_models` | `train_models.py` |
| job_7 task `sync_genie_config` | `genie_sync` | `src/payment_analysis/genie/sync_genie_space` | `sync_genie_space.py` (genie_spaces.yml) |
| job_6 task `run_agent_framework` | `run_agent_framework` | `src/payment_analysis/agents/agent_framework` | `agent_framework.py` |
| job_6 task `register_responses_agent` | `register_responses_agent` | `src/payment_analysis/agents/register_responses_agent` | `register_responses_agent.py` |
| job_6 task `register_agentbricks` | `register_agentbricks` | `src/payment_analysis/agents/agentbricks_register` | `agentbricks_register.py` |
| `publish_dashboards_job` | `publish_dashboards` | `src/payment_analysis/transform/publish_dashboards` | `publish_dashboards.py` |
| `continuous_stream_processor` | `continuous_stream_processor` | `src/payment_analysis/streaming/continuous_processor` | `continuous_processor.py` |
| `prepare_dashboards_job` | (not in Setup UI) | `src/payment_analysis/transform/prepare_dashboards` | `prepare_dashboards.py` |

**Pipelines** (not jobs): `payment_analysis_etl` uses notebooks `streaming/bronze_ingest`, `transform/silver_transform`, `transform/gold_views`. `payment_realtime_pipeline` uses `streaming/realtime_pipeline`. Sync includes `src/payment_analysis/ml`, `streaming`, `transform`, `agents`, `genie`, `vector_search`, so all referenced notebooks are uploaded.

---

**See also:** [Guide](GUIDE.md) — business overview, architecture, project structure, control panel, best practices.
