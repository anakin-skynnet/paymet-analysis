# 1. Deployments

Step-by-step deployment for the Payment Approval Optimization Platform. **One-click run links:** [5_DEMO_SETUP](5_DEMO_SETUP.md).

## Prerequisites

Databricks workspace (Unity Catalog), SQL Warehouse, CLI configured. Python 3.10+ with `uv`, Node 18+ with `bun`. Permissions: jobs, **Lakeflow Declarative Pipelines**, model serving; write to `ahs_demos_catalog`; deploy to `/Workspace/Users/<your_email>/`.

## Quick Start

```bash
databricks bundle validate
databricks bundle deploy --target dev
```

Then run jobs/pipelines per [5_DEMO_SETUP](5_DEMO_SETUP.md); optionally [Step 6: Import dashboards](#step-6-import-dashboards).

## Steps

| Step | Purpose | Action |
|------|---------|--------|
| **1** | Deploy bundle | `databricks bundle validate` then `databricks bundle deploy -t dev` |
| **2** | Generate data | Workflows → “Transaction Stream Simulator” or run `transaction_simulator.py`; output `raw_payment_events` |
| **3** | Lakeflow Declarative Pipelines | Lakeflow → “Payment Analysis ETL” → Start; Bronze → Silver → Gold |
| **4** | Gold views | Workflows → “Create Payment Analysis Gold Views”; verify `v_executive_kpis` etc. |
| **5** | ML models | Workflows → “Train Payment Approval ML Models”; ~10–15 min; 4 models in UC |
| **6** | Dashboards | Bundle includes dashboards (default catalog/schema; warehouse from resource). Or SQL → Import `.lvdash.json` from `src/payment_analysis/dashboards/` |
| **7** | Genie (optional) | SQL → Genie Spaces → Create “Payment Approval Analytics” / “Decline Analysis”; attach gold views; run `genie_sync_job` |
| **7** | Model serving (optional) | After Step 5: uncomment `resources/model_serving.yml` in `databricks.yml`, redeploy |
| **7** | AI agents (optional) | Verify Llama endpoint; `databricks bundle run orchestrator_agent_job -t dev`; agents in `ai_gateway.yml` (PAUSED) |
| **8** | Web app | `.env`: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`. `uv run apx dev` or `apx build` + deploy |
| **9** | Verify | Data in bronze/silver; 4 models; 10 dashboards; app routes load |

## Schema Consistency

Use one catalog/schema everywhere (defaults: `ahs_demos_catalog`, `ahs_demo_payment_analysis_dev`). Bundle: `var.catalog`, `var.schema`; backend: `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`.

## Troubleshooting

| Issue | Actions |
|-------|---------|
| Lakeflow pipeline fails | Pipeline logs; confirm `raw_payment_events`; UC permissions; `pipelines reset` if needed |
| Dashboards empty | Gold views + data; warehouse running; warehouse_id in config |
| ML training fails | Silver data; ML runtime; UC model registry; MLflow logs |
| App won’t start | Ports 8000/5173; `uv sync`, `bun install`; `.env` |

**Estimated time:** 45–60 min.
