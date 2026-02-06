# 1. Deployments

Step-by-step deployment for the Payment Approval Optimization Platform. **One-click run links:** [5_DEMO_SETUP](5_DEMO_SETUP.md).

## Prerequisites

Databricks workspace (Unity Catalog), SQL Warehouse, CLI configured. Python 3.10+ with `uv`, Node 18+ with `bun`. Permissions: jobs, **Lakeflow**, model serving; write to `ahs_demos_catalog`; deploy to `/Workspace/Users/<your_email>/`.

## Quick Start

```bash
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

For prod with different catalog/schema in dashboards, run `./scripts/validate_bundle.sh prod` (uses `prepare_dashboards.py`). Then run jobs/pipelines per [5_DEMO_SETUP](5_DEMO_SETUP.md).

## Steps

| Step | Purpose | Action |
|------|---------|--------|
| **1** | Prepare dashboards | `uv run python scripts/prepare_dashboards.py` (for prod add `--catalog prod_catalog --schema ahs_demo_payment_analysis_prod`) |
| **1** | Deploy bundle | `databricks bundle validate -t dev` then `databricks bundle deploy -t dev` |
| **2** | Generate data | Workflows → “Transaction Stream Simulator” or run `transaction_simulator.py`; output `raw_payment_events` |
| **3** | Lakeflow | Lakeflow → “Payment Analysis ETL” → Start; Bronze → Silver → Gold |
| **4** | Gold views | Workflows → “Create Payment Analysis Gold Views”; verify `v_executive_kpis` etc. |
| **4b** | Vector Search + Lakehouse | Run `vector_search_and_recommendations.sql` (same schema) to create `transaction_summaries_for_search`, `approval_recommendations`, and `v_recommendations_from_lakehouse`. Bundle includes `resources/vector_search.yml` (endpoint + DELTA_SYNC index on the search table). Populate the tables (e.g. from gold/silver) so the index and app recommendations are useful. |
| **4c** | Approval rules (Lakehouse) | Run `approval_rules.sql` (same schema) to create `approval_rules` and `v_approval_rules_active`. The app **Rules** page writes rules here; ML and AI agents read them to accelerate approval rates. |
| **4d** | Online features (Lakehouse) | Run `online_features.sql` (same schema) to create `online_features` and `v_online_features_latest`. ML and AI jobs can write features here; the app **Dashboard** shows them in the "Online features (Lakehouse)" card. |
| **5** | ML models | Workflows → “Train Payment Approval ML Models”; ~10–15 min; registers 4 models in UC (approval_propensity_model, risk_scoring_model, smart_routing_policy, smart_retry_policy). |
| **6** | Dashboards | Bundle includes 11 dashboards (source: `src/payment_analysis/dashboards/`); warehouse from `var.warehouse_id`. |
| **7** | Genie (optional) | SQL → Genie Spaces → Create “Payment Approval Analytics” / “Decline Analysis”; attach gold views; run `genie_sync_job` |
| **7** | Model serving & UI | After Step 5, redeploy deploys model serving. ML Models UI shows models via backend (set DATABRICKS_CATALOG/SCHEMA). |
| **7** | AI agents (optional) | Verify Llama endpoint; `databricks bundle run orchestrator_agent_job -t dev`; agents in `ai_gateway.yml` (PAUSED) |
| **8** | Web app | `.env`: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`. `uv run apx dev` or `apx build` + deploy |
| **9** | Verify | Data in bronze/silver; 4 models in UC; model serving endpoints; 11 dashboards; app **ML Models** page shows list and links to Model Registry/MLflow |

## Schema Consistency

Use one catalog/schema everywhere (defaults: `ahs_demos_catalog`, `ahs_demo_payment_analysis_dev`). Bundle: `var.catalog`, `var.schema`; backend: `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`.

## Where to find resources in the workspace

After a **successful** `databricks bundle deploy -t dev`, look for:

- **Workspace:** **Workspace** → **Users** → your user → **getnet_approval_rates_v3** (files, dashboards folder).
- **Jobs:** **Workflow** (Jobs) → names like `[dev …] Train Payment Approval ML Models`, `[dev …] Transaction Stream Simulator`.
- **Lakeflow:** **Lakeflow** → `[dev] Payment Analysis ETL`, `[dev] Payment Real-Time Stream`.
- **SQL Warehouse:** **SQL** → **Warehouses** → `[dev] Payment Analysis Warehouse`.
- **Catalog:** **Catalog** → `ahs_demos_catalog` → schema `ahs_demo_payment_analysis_dev`.
- **Dashboards:** **SQL** → **Dashboards** (or under the workspace folder above).

If deploy **failed** (e.g. at model serving), some resources will be missing. Comment out `model_serving.yml` in `databricks.yml` and run `databricks bundle deploy -t dev` again. Confirm workspace/user with `databricks bundle validate -t dev`. **Vector Search** deploy can fail if the source table `transaction_summaries_for_search` does not exist (run `vector_search_and_recommendations.sql` first) or if the embedding model `databricks-bge-large-en` is not available in the workspace; you can comment out `resources/vector_search.yml` in `databricks.yml` to skip it.

## Troubleshooting

| Issue | Actions |
|-------|---------|
| Don't see resources | Redeploy after commenting out `model_serving.yml` if deploy failed; check workspace/user matches `databricks bundle validate -t dev`. |
| Lakeflow fails | Pipeline logs; confirm `raw_payment_events`; UC permissions; `pipelines reset` if needed |
| Dashboards empty | Gold views + data; warehouse running; warehouse_id in config |
| ML training fails | Silver data; ML runtime; UC model registry; MLflow logs |
| App won’t start | Ports 8000/5173; `uv sync`, `bun install`; `.env` |

## Scripts

- **validate_bundle.sh** — For **prod** (or when dashboards use a different catalog/schema): runs `prepare_dashboards.py` with optional `--catalog`/`--schema`, then `databricks bundle validate -t <target>`. For **dev**, `databricks bundle validate -t dev` and `databricks bundle deploy -t dev` work without this script.
- **prepare_dashboards.py** — Run once per prod deploy: copies dashboard JSONs to `.build/dashboards/` and optionally substitutes catalog/schema. Dev uses source files in `src/payment_analysis/dashboards/` directly.

**Estimated time:** 45–60 min.
