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

6. **Optional — override job/pipeline IDs:** Set `DATABRICKS_JOB_ID_*`, `DATABRICKS_PIPELINE_ID_*`, `DATABRICKS_WORKSPACE_ID` per [Architecture & reference](ARCHITECTURE_REFERENCE.md#workspace-components--ui-mapping).

App resource: `resources/fastapi_app.yml`. Runtime spec: `app.yaml` and `app.yml` at project root (keep in sync). See [App spec error](#app-spec-error).

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

## Troubleshooting

| Issue | Action |
|-------|--------|
| Database instance STARTING | Wait, then redeploy |
| Don't see resources | Redeploy; run `./scripts/bundle.sh validate dev` |
| Registered model does not exist | Run Step 6, then uncomment `model_serving.yml`, redeploy |
| Lakebase "Instance name is not unique" | Use unique `lakebase_instance_name` via `--var` or target |
| Error installing packages | TanStack **1.158.1** with overrides; use `bun.lock`. See [Architecture & reference](ARCHITECTURE_REFERENCE.md#databricks-app-deploy) |
| **Error loading app spec from app.yml** | Ensure **`app.yaml`** and **`app.yml`** exist at project root with same content. Redeploy. |
| **Failed to export ... type=mlflowExperiment** | MLflow experiment was under the app source path. Training job now uses `.../mlflow_experiments/payment_analysis_models`. If export still fails, in **Workspace** delete the experiment at `.../src/payment_analysis/dashboards/payment_analysis_models` (or the path in the error); then redeploy/export. |

### App spec error

Runtime loads **`app.yml`** at deployed app root; **`app.yaml`** is the main spec. Keep both in sync. After edits run `./scripts/bundle.sh deploy dev`. **Logs:** **Compute → Apps** → **payment-analysis** → Start → **Logs**.

## Scripts

| Script | Purpose |
|--------|---------|
| **bundle.sh** | `./scripts/bundle.sh deploy [dev\|prod]` — prepare dashboards then deploy. `validate` / `verify` for checks. |
| **dashboards.py** | **prepare** (by bundle.sh), **validate-assets**, **publish** (optional). Run: `uv run python scripts/dashboards.py` |

## Demo setup & one-click run

Order: (1) Deploy bundle (2) Simulator (3) ETL pipeline (4) Gold views job (5) `lakehouse_bootstrap.sql` (6) Train ML (7–8) Optional real-time pipeline, agents. **Estimated time:** 45–60 min. Job/pipeline IDs: **Workflows** / **Lakeflow** or `databricks bundle run <job_name> -t dev`.

---

**See also:** [Architecture & reference](ARCHITECTURE_REFERENCE.md)
