# 1. Deployments

Step-by-step deployment and validation for the Payment Approval Optimization Platform.

**→ One-click run links:** [5_DEMO_SETUP](5_DEMO_SETUP.md).

---

## Prerequisites

- Databricks workspace (Azure or AWS), Unity Catalog enabled
- SQL Warehouse created and running
- Databricks CLI configured (`databricks configure`)
- Python 3.10+ with `uv`, Node 18+ with `bun`
- Permissions: create jobs, DLT pipelines, model serving; write to Unity Catalog (`ahs_demos_catalog`); deploy to `/Workspace/Users/<your_email>/`

---

## Quick Start

```bash
databricks bundle validate
databricks bundle deploy --target dev
```

Then run jobs/pipelines in order (see [5_DEMO_SETUP](5_DEMO_SETUP.md)) and optionally [Step 6: Import dashboards](#step-6-import-dashboards).

---

## Step 1: Deploy bundle

```bash
cd /path/to/paymet-analysis
databricks bundle validate
databricks bundle deploy --target dev
```

**Created:** Schema `ahs_demos_catalog.ahs_demo_payment_analysis_dev`, DLT pipeline, jobs (simulator, ML training, agents, gold views).  
**Location:** `/Workspace/Users/<your_email>/getnet_approval_rates_v3/`

---

## Step 2: Transaction simulator

**Purpose:** Generate synthetic payment data.

- **UI:** Workflows → Jobs → “Payment Transaction Stream Simulator” → Run now  
- **Workspace:** Run `src/payment_analysis/streaming/transaction_simulator.py`  
- **Output:** `ahs_demos_catalog.ahs_demo_payment_analysis_dev.raw_payment_events`  
- **Wait:** 2–3 minutes for initial data

---

## Step 3: DLT pipeline

**Purpose:** Bronze → Silver → Gold.

- **UI:** Lakeflow Declarative Pipelines → “Payment Analysis DLT Pipeline” → Start  
- **Tables:** `payments_bronze`, `payments_enriched_silver`, 12+ gold views  
- **Wait:** Pipeline RUNNING and first batch (~5 min)

---

## Step 4: Gold views

**Purpose:** Create analytical views for dashboards.

- **UI:** Workflows → “Create Payment Analysis Gold Views” → Run now  
- **Workspace:** Run `src/payment_analysis/transform/gold_views.sql` (or `.py`)  
- **Verify:** `SHOW VIEWS IN ahs_demos_catalog.ahs_demo_payment_analysis_dev;`  
- **Test:** `SELECT * FROM ahs_demos_catalog.ahs_demo_payment_analysis_dev.v_executive_kpis LIMIT 10;`

---

## Step 5: Train ML models

**Purpose:** Train 4 models (approval propensity, risk, routing, retry).

- **UI:** Workflows → “Train Payment Approval ML Models” → Run now  
- **Duration:** ~10–15 min  
- **Registered:** `ahs_demos_catalog.ahs_demo_payment_analysis_dev.{approval_propensity_model, risk_scoring_model, smart_routing_policy, smart_retry_policy}`  
- **Verify:** ML → Models; MLflow experiment `/Users/<user>/payment_analysis_models`

---

## Step 6: Import dashboards

**Purpose:** 10 AI/BI dashboards. Gold views must exist first (Steps 3–4).

- **Option A (bundle):** Uncomment `resources/dashboards.yml` in `databricks.yml`. Then run variable substitution and deploy with a valid SQL warehouse ID:
  ```bash
  uv run python scripts/substitute_dashboard_vars.py
  BUNDLE_VAR_warehouse_id=$(databricks warehouses list -o json | jq -r '.[0].id') databricks bundle deploy -t dev --auto-approve
  ```
- **Option B:** SQL → Dashboards → Create → Import; select each `.lvdash.json` from `resources/dashboards/` (manually set catalog/schema/warehouse in each).
- **Files:** executive_overview, decline_analysis, realtime_monitoring, fraud_risk_analysis, merchant_performance, routing_optimization, daily_trends, authentication_security, financial_impact, performance_latency

---

## Step 7: AI agents (optional)

### 7a. Genie Spaces

Create two Genie Spaces for natural-language analytics:

1. **Payment Approval Analytics**
   - Go to **SQL** → **Genie Spaces** → **Create**
   - Name: `Payment Approval Analytics`
   - Attach tables from `ahs_demos_catalog.ahs_demo_payment_analysis_dev`:
     - `v_executive_kpis`, `v_approval_trends_hourly`, `v_solution_performance`, `v_performance_by_geography`, `payments_enriched_silver`
   - Add sample questions: "What is the current approval rate?", "Compare approval rates by country", "Which payment solution performs best?"
   - Instructions: "Approval rate = approved / total × 100. Risk tiers: low (<0.3), medium (0.3–0.7), high (>0.7)."

2. **Decline Analysis**
   - Name: `Decline Analysis`
   - Attach: `v_top_decline_reasons`, `v_decline_patterns`, `v_reason_code_taxonomy`, `payments_enriched_silver`
   - Sample questions: "Show me top decline reasons", "What are the most recoverable decline codes?"

- **Sync job:** `databricks bundle run genie_sync_job -t dev` (runs weekly, PAUSED by default)
- **Verify:** Open each Genie Space and ask a sample question

### 7b. Model Serving Endpoints

After ML models are trained (Step 5):

1. Uncomment `resources/model_serving.yml` in `databricks.yml`:
   ```yaml
   include:
     # ...existing...
     - resources/model_serving.yml
   ```
2. Redeploy: `databricks bundle deploy --target dev`
3. **Endpoints created:**
   - `approval-propensity-dev` — approval likelihood predictions
   - `risk-scoring-dev` — real-time risk assessment
   - `smart-routing-dev` — optimal processor routing
   - `smart-retry-dev` — retry strategy recommendations
4. **Verify:** Serving → Endpoints → check status is "Ready"; test with sample payload

### 7c. AI Gateway (LLM Agents)

The agent framework uses Databricks Foundation Model APIs:

1. **Verify** the `databricks-meta-llama-3-1-70b-instruct` endpoint is available in your workspace (Serving → Foundation Model APIs)
2. **Run the orchestrator** to test all agents:
   ```bash
   databricks bundle run orchestrator_agent_job -t dev
   ```
3. **Individual agents** (all PAUSED by default, enable as needed):
   - Smart Routing Agent — every 6 hours
   - Smart Retry Agent — every 4 hours
   - Decline Analyst — daily at 8 AM
   - Risk Assessor — every 2 hours
   - Performance Recommender — daily at 6 AM
4. **Rate limits:** 100–200 calls/min per endpoint (configurable in `ai_gateway.yml`)

---

## Step 8: Web application

```bash
uv sync && bun install
```

Create `.env`:

```
DATABRICKS_HOST=https://adb-xxx.azuredatabricks.net
DATABRICKS_TOKEN=dapi***
DATABRICKS_WAREHOUSE_ID=<id>
DATABRICKS_CATALOG=ahs_demos_catalog
DATABRICKS_SCHEMA=ahs_demo_payment_analysis_dev
APP_ENV=development
```

- **Local:** `uv run apx dev` (or uvicorn + frontend dev server)  
- **Production:** `uv run apx build` then `databricks apps deploy` or your host

---

## Step 9: Verification

- **Data:** Counts and latest timestamp on `payments_bronze`, `payments_enriched_silver`; query `v_executive_kpis`  
- **Models:** 4 models in Unity Catalog with Production version; test inference via MLflow load or serving  
- **App:** Dashboard, Dashboards gallery, Notebooks, ML Models, AI Agents, Decisioning, Experiments, Incidents, Declines all load

---

## Pre-deployment validation

| Area | Check |
|------|--------|
| **Simulator** | Job in `streaming_simulator.yml`; notebook writes to `{catalog}.{schema}.raw_payment_events`; params from `${var.catalog}`, `${var.schema}` |
| **ETL** | Pipelines in `pipelines.yml`; `schema: ${var.schema}`; bronze/silver/gold notebooks; continuous + serverless |
| **Unity Catalog** | Schema and volumes use `${var.schema}`, `${var.catalog}` |
| **Dashboards** | `dashboards.yml`; uncomment in `databricks.yml` when ready |
| **Genie** | Sync job in `genie_spaces.yml`; params catalog/schema |
| **Agents** | `agent_framework.py`; jobs in `ai_gateway.yml`; catalog/schema/agent_role/query |
| **Model serving** | `model_serving.yml`; entity `${var.catalog}.${var.schema}.<model>`; uncomment after training |
| **App** | `app.yml`; backend `payment_analysis.backend.app:app`; env vars for host, token, warehouse, catalog, schema |

**Recommended order:** Deploy bundle → Run simulator → Start ETL → Gold views job → ML training → Uncomment dashboards/model_serving and redeploy → Configure Genie → Deploy app → Run orchestrator/agents as needed.

---

## Schema consistency

Use one catalog and schema everywhere (defaults: `ahs_demos_catalog`, `ahs_demo_payment_analysis_dev`):

- **Bundle:** `var.catalog`, `var.schema`  
- **Simulator, DLT, ML jobs, agent jobs, Genie sync:** base_parameters / config use `${var.catalog}`, `${var.schema}`  
- **Model serving:** `entity_name`, `schema_name`, `catalog_name`  
- **Backend:** `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA` (or defaults in code)

---

## Troubleshooting

| Issue | Actions |
|-------|--------|
| **DLT fails** | Check pipeline logs; confirm `raw_payment_events` exists; check UC permissions; `databricks pipelines reset --pipeline-id <id>` if needed |
| **Dashboards empty** | Verify gold views have data; warehouse running; refresh dashboard; check warehouse ID in dashboard JSON |
| **ML training fails** | Check silver table has data; cluster has ML runtime (16.x LTS ML+); UC model registry permissions; MLflow logs |
| **App won’t start** | Check ports 8000/5173; `uv sync --reinstall`, `bun install --force`; validate `.env` |

---

## Success metrics (post-deploy)

| Metric | Expected |
|--------|----------|
| Transactions | 1,000+/min |
| DLT | RUNNING |
| Silver rows | 100,000+ |
| Gold views | 12 |
| ML models | 4 |
| Dashboards | 10 |
| Approval rate (mock) | 85–90% |

**Estimated deployment time:** 45–60 minutes.
