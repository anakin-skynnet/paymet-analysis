# Deployment & Execution Guide

Step-by-step instructions to deploy and run the Payment Approval Optimization Platform.

---

## 📋 Prerequisites

Before starting, ensure you have:

- ✅ Databricks workspace (Azure or AWS)
- ✅ Unity Catalog enabled
- ✅ SQL Warehouse created and running
- ✅ Databricks CLI installed and configured (`databricks configure`)
- ✅ Python 3.10+ and `uv` package manager
- ✅ Node.js 18+ and `bun` package manager
- ✅ Git repository cloned locally

### Required Databricks Permissions
- Workspace Admin or sufficient permissions to:
  - Create jobs, DLT pipelines, model serving endpoints
  - Write to Unity Catalog (`main` catalog)
  - Deploy bundles to `/Workspace/Users/<your_email>/`

---

## 🚀 Quick Start (Automated)

If you just want to deploy everything at once:

```bash
# Step 1: Validate and deploy all resources
databricks bundle validate
databricks bundle deploy --target dev

# Step 2: The bundle will automatically create:
# - DLT pipeline (auto-starts)
# - ML training job
# - Transaction simulator job
# - Agent jobs
# - SQL Warehouse (if specified)
```

Then jump to [Step 6: Import Dashboards](#step-6-import-dashboards) below.

---

## 📖 Detailed Step-by-Step Guide

Follow these steps for a controlled, incremental deployment:

---

## Step 1: Deploy Infrastructure with Databricks Asset Bundles

**Purpose:** Deploy all Databricks resources (jobs, pipelines, warehouses) to your workspace.

```bash
# Navigate to project root
cd /path/to/paymet-analysis

# Validate bundle configuration
databricks bundle validate

# Deploy to development environment
databricks bundle deploy --target dev
```

**Expected Output:**
```
✓ Deployed jobs
✓ Deployed pipelines
✓ Created Unity Catalog schema: main.payment_analysis_dev
```

**Resources Created:**
- Schema: `main.payment_analysis_dev`
- DLT Pipeline: `payment_analysis_dlt_pipeline`
- Jobs: Transaction Simulator, ML Training, Agent Jobs, View Creation

**Deployment Location:** `/Workspace/Users/<your_email>/getnet_approval_rates_v2/`

---

## Step 2: Start Transaction Stream Simulator

**Purpose:** Generate synthetic payment transaction data for testing and demonstration.

**Job Name:** `Payment Transaction Stream Simulator`

### Option A: Via Databricks UI
1. Navigate to **Workflows** → **Jobs**
2. Find job: `Payment Transaction Stream Simulator`
3. Click **Run now**
4. Monitor execution in real-time

### Option B: Via CLI
```bash
# Get job ID
databricks jobs list --output json | grep "Payment Transaction Stream Simulator"

# Run the job (replace JOB_ID)
databricks jobs run-now --job-id <JOB_ID>
```

### Option C: Via Workspace
1. Open: `/Workspace/Users/<your_email>/getnet_approval_rates_v2/files/src/payment_analysis/streaming/transaction_simulator.py`
2. Attach to cluster
3. Click **Run All**

**Expected Output:**
- Generates 1,000+ transactions per minute
- Writes to: `main.payment_analysis_dev.raw_payment_events` (Bronze table)

**Duration:** Continuous (runs for 1 hour by default, or until stopped)

**⏱️ Wait Time:** Let run for 2-3 minutes to generate initial data

---

## Step 3: Start Delta Live Tables Pipeline

**Purpose:** Process raw transactions through Bronze → Silver → Gold layers.

**Pipeline Name:** `Payment Analysis DLT Pipeline`

### Option A: Via Databricks UI
1. Navigate to **Delta Live Tables**
2. Find pipeline: `Payment Analysis DLT Pipeline`
3. Click **Start**
4. Select mode: **Continuous** (for real-time) or **Triggered** (for batch)

### Option B: Via CLI
```bash
# Get pipeline ID
databricks pipelines list --output json | grep "Payment Analysis DLT Pipeline"

# Start the pipeline (replace PIPELINE_ID)
databricks pipelines start --pipeline-id <PIPELINE_ID>
```

**Expected Output:**
- Bronze Layer: `raw_payment_events` → `payments_bronze`
- Silver Layer: `payments_bronze` → `payments_enriched_silver`
- Gold Layer: `payments_enriched_silver` → gold tables/views

**Tables Created:**
- `main.payment_analysis_dev.payments_bronze`
- `main.payment_analysis_dev.payments_enriched_silver`
- 12+ gold views (see Step 4)

**Duration:** 
- Initial run: 5-10 minutes
- Continuous mode: Ongoing

**⏱️ Wait Time:** Wait for pipeline to reach **RUNNING** state and process initial batch (~5 minutes)

---

## Step 4: Create Gold Layer Analytics Views

**Purpose:** Create aggregated views optimized for dashboards and analytics.

**Job Name:** `Create Payment Analysis Gold Views`

### Option A: Via Databricks UI
1. Navigate to **Workflows** → **Jobs**
2. Find job: `Create Payment Analysis Gold Views`
3. Click **Run now**

### Option B: Via Workspace
1. Open: `/Workspace/Users/<your_email>/getnet_approval_rates_v2/files/src/payment_analysis/transform/gold_views.sql`
2. Attach to SQL Warehouse
3. Run all cells sequentially

**Views Created (12 total):**
1. `v_executive_kpis` - High-level KPIs
2. `v_approval_trends_hourly` - Hourly approval trends
3. `v_daily_trends` - Daily performance metrics
4. `v_top_decline_reasons` - Decline reason analysis
5. `v_decline_recovery_opportunities` - Recovery potential
6. `v_retry_performance` - Retry success metrics
7. `v_solution_performance` - Payment solution stats
8. `v_card_network_performance` - Network performance
9. `v_merchant_segment_performance` - Segment analysis
10. `v_performance_by_geography` - Geographic performance
11. `v_active_alerts` - Real-time alert monitoring
12. `v_fraud_risk_summary` - Fraud risk aggregations

**Duration:** 2-3 minutes

**⏱️ Wait Time:** Verify views are created before proceeding

**Verification:**
```sql
-- Check views exist
SHOW VIEWS IN main.payment_analysis_dev;

-- Test a view
SELECT * FROM main.payment_analysis_dev.v_executive_kpis LIMIT 10;
```

---

## Step 5: Train ML Models

**Purpose:** Train 4 ML models for approval prediction and optimization.

**Job Name:** `Train Payment Approval ML Models`

### Option A: Via Databricks UI
1. Navigate to **Workflows** → **Jobs**
2. Find job: `Train Payment Approval ML Models`
3. Click **Run now**
4. Monitor MLflow experiments

### Option B: Via Workspace
1. Open: `/Workspace/Users/<your_email>/getnet_approval_rates_v2/files/src/payment_analysis/ml/train_models.py`
2. Attach to ML Runtime cluster
3. Click **Run All**

**Models Trained:**
1. **Approval Propensity Model** (~92% accuracy)
   - Registered as: `main.payment_analysis_dev.approval_propensity_model`
2. **Risk Scoring Model** (~88% accuracy)
   - Registered as: `main.payment_analysis_dev.risk_scoring_model`
3. **Smart Routing Policy** (~75% accuracy)
   - Registered as: `main.payment_analysis_dev.smart_routing_policy`
4. **Smart Retry Policy** (~81% accuracy)
   - Registered as: `main.payment_analysis_dev.smart_retry_policy`

**Duration:** 10-15 minutes

**⏱️ Wait Time:** Wait for all 4 models to complete training

**Verification:**
1. Navigate to **Machine Learning** → **Models**
2. Verify 4 models registered in Unity Catalog
3. Check MLflow experiment: `/Users/<your_email>/payment_analysis_models`

---

## Step 6: Import Dashboards

**Purpose:** Import 10 Lakeview dashboards for analytics and monitoring.

### Prerequisites
- ✅ Gold views created (Step 4)
- ✅ SQL Warehouse running
- ✅ Dashboard files in: `resources/dashboards/*.lvdash.json`

### Import Method A: Via Databricks CLI (Recommended)

**Note:** First, you need to uncomment the dashboards in `databricks.yml`:

```bash
# Edit databricks.yml
# Uncomment this line:
# include:
#   - resources/dashboards.yml

# Then deploy
databricks bundle deploy --target dev
```

### Import Method B: Via Databricks UI (Manual)

For each dashboard file in `resources/dashboards/`:

1. Navigate to **SQL** → **Dashboards**
2. Click **Create dashboard** → **Import dashboard**
3. Select JSON file:
   - `executive_overview.lvdash.json`
   - `decline_analysis.lvdash.json`
   - `realtime_monitoring.lvdash.json`
   - `fraud_risk_analysis.lvdash.json`
   - `merchant_performance.lvdash.json`
   - `routing_optimization.lvdash.json`
   - `daily_trends.lvdash.json`
   - `authentication_security.lvdash.json`
   - `financial_impact.lvdash.json`
   - `performance_latency.lvdash.json`
4. Select SQL Warehouse
5. Click **Import**

**Dashboards Created (10 total):**
1. **Executive Overview** - High-level KPIs for leadership
2. **Decline Analysis** - Deep-dive into decline patterns
3. **Real-Time Monitoring** - Live transaction monitoring
4. **Fraud & Risk Analysis** - Fraud detection and risk metrics
5. **Merchant Performance** - Merchant segment analysis
6. **Routing Optimization** - Payment routing performance
7. **Daily Trends** - Historical trends (90 days)
8. **Authentication & Security** - 3DS adoption and security
9. **Financial Impact** - Revenue and ROI analysis
10. **Performance & Latency** - Technical performance metrics

**Duration:** 5-10 minutes (for all 10 dashboards)

**Verification:**
- Navigate to **SQL** → **Dashboards**
- Verify all 10 dashboards are listed
- Open each dashboard and verify data loads

---

## Step 7: Set Up AI Agents (Optional)

**Purpose:** Configure Databricks AI capabilities for intelligent insights.

### 7a. Set Up Genie Spaces

1. Navigate to **Genie** in Databricks workspace
2. Create space: **"Payment Approval Analytics"**
   - Add Unity Catalog: `main.payment_analysis_dev`
   - Enable: All gold views (`v_*`)
3. Create space: **"Decline Analysis"**
   - Add specific views: `v_top_decline_reasons`, `v_retry_performance`

**Duration:** 5 minutes

### 7b. Enable Model Serving (Optional)

For real-time predictions:

```bash
# Deploy models to serving endpoints
databricks model-serving create-endpoint \
  --name approval_propensity_serving \
  --model-name main.payment_analysis_dev.approval_propensity_model \
  --model-version 1
```

**Note:** This requires Model Serving enabled in your workspace.

### 7c. Configure AI Gateway

1. Navigate to **AI Gateway** in Databricks
2. Verify endpoint: `databricks-meta-llama-3-1-70b-instruct`
3. Configure rate limits and cost controls

**Duration:** 10 minutes

---

## Step 8: Deploy Web Application

**Purpose:** Deploy the FastAPI + React application for user access.

### 8a. Install Dependencies

```bash
# Python dependencies
uv sync

# Frontend dependencies
bun install
```

### 8b. Configure Environment

Create `.env` file in project root:

```bash
# Databricks Configuration
DATABRICKS_HOST=https://adb-XXXXXXXXX.XX.azuredatabricks.net
DATABRICKS_TOKEN=dapi********************************
DATABRICKS_WAREHOUSE_ID=3fef3d3419b56344
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=payment_analysis_dev

# Application
APP_ENV=development
```

### 8c. Run Application Locally

```bash
# Development mode (auto-reload)
uv run apx dev

# Or separately:
# Backend (port 8000)
uv run uvicorn payment_analysis.backend.main:app --reload

# Frontend (port 5173)
cd src/payment_analysis/ui
bun run dev
```

### 8d. Deploy to Production

```bash
# Build frontend
bun run build

# Deploy to Databricks Apps (if available)
databricks apps deploy

# Or deploy to your preferred hosting (AWS, Azure, GCP)
```

**Access Application:**
- Local: `http://localhost:5173`
- Production: `https://<your-databricks-app-url>`

**Duration:** 5 minutes (local), 15-20 minutes (production)

---

## Step 9: Verify End-to-End Flow

**Purpose:** Ensure all components are working together.

### 9a. Check Data Flow

```sql
-- 1. Verify transactions are being generated
SELECT COUNT(*), MAX(event_timestamp) 
FROM main.payment_analysis_dev.payments_bronze;

-- 2. Verify silver enrichment
SELECT COUNT(*), AVG(approval_rate_pct) 
FROM main.payment_analysis_dev.payments_enriched_silver;

-- 3. Verify gold views
SELECT * FROM main.payment_analysis_dev.v_executive_kpis;
```

### 9b. Check ML Models

1. Navigate to **Machine Learning** → **Models**
2. Verify all 4 models show "Production" version
3. Test inference:

```python
from databricks import sql
import mlflow

# Load model
model = mlflow.sklearn.load_model("models:/main.payment_analysis_dev.approval_propensity_model/1")

# Test prediction
test_data = [[199.99, 0.15, 0.92, 0, 0, 1]]
prediction = model.predict(test_data)
print(f"Approval probability: {prediction[0]}")
```

### 9c. Check Dashboards

1. Open each of the 10 dashboards
2. Verify data is loading
3. Check for any empty widgets or errors

### 9d. Test Application

1. Open web application
2. Navigate through all sections:
   - ✅ Dashboard (KPIs loading)
   - ✅ Analytics Dashboards (10 dashboards listed)
   - ✅ Notebooks (9 notebooks listed)
   - ✅ ML Models (4 models displayed)
   - ✅ AI Agents (7 agents listed)
   - ✅ Decisioning (test predictions)
   - ✅ Experiments (list experiments)
   - ✅ Incidents (list incidents)
   - ✅ Declines (decline summary)

---

## 🔄 Ongoing Operations

### Daily Operations

```bash
# Check pipeline health
databricks pipelines list --output json | grep "Payment Analysis"

# Monitor job runs
databricks jobs runs list --limit 10

# Check recent data
SELECT COUNT(*), MAX(event_timestamp) 
FROM main.payment_analysis_dev.payments_enriched_silver
WHERE DATE(event_timestamp) = CURRENT_DATE();
```

### Weekly Maintenance

1. **Retrain ML Models:**
   - Run job: `Train Payment Approval ML Models`
   - Verify improved metrics in MLflow

2. **Review Dashboards:**
   - Check for data quality issues
   - Update thresholds and alerts

3. **Update Genie Spaces:**
   - Add new views as needed
   - Review popular queries

### Monthly Tasks

1. **Performance Optimization:**
   - Optimize DLT pipeline
   - Review warehouse size
   - Clean up old model versions

2. **Business Review:**
   - Present dashboard insights to stakeholders
   - Identify new optimization opportunities
   - Update target metrics

---

## 🛠️ Troubleshooting

### Issue: DLT Pipeline Fails

**Symptoms:** Pipeline shows errors, data not flowing

**Solutions:**
1. Check pipeline error logs in DLT UI
2. Verify source table exists: `main.payment_analysis_dev.raw_payment_events`
3. Ensure cluster has sufficient resources
4. Check Unity Catalog permissions

```bash
# Reset pipeline (clears state)
databricks pipelines reset --pipeline-id <PIPELINE_ID>
```

### Issue: Dashboards Show No Data

**Symptoms:** Dashboard widgets are empty

**Solutions:**
1. Verify gold views have data:
   ```sql
   SELECT COUNT(*) FROM main.payment_analysis_dev.v_executive_kpis;
   ```
2. Check SQL Warehouse is running
3. Refresh dashboard: Click **Refresh** button
4. Verify warehouse ID in dashboard JSON matches your warehouse

### Issue: ML Training Fails

**Symptoms:** Job fails with error

**Solutions:**
1. Check if silver table has data:
   ```sql
   SELECT COUNT(*) FROM main.payment_analysis_dev.payments_enriched_silver;
   ```
2. Ensure cluster has ML runtime (13.3 LTS ML or higher)
3. Verify Unity Catalog permissions for model registry
4. Check MLflow experiment logs

### Issue: Application Won't Start

**Symptoms:** Port conflicts, import errors

**Solutions:**
```bash
# Check ports
lsof -i :8000  # Backend
lsof -i :5173  # Frontend

# Reinstall dependencies
uv sync --reinstall
bun install --force

# Check environment variables
cat .env
```

---

## 📊 Success Metrics

After completing all steps, you should see:

| Metric | Expected Value |
|--------|---------------|
| **Transactions Generated** | 1,000+/minute |
| **DLT Pipeline Status** | RUNNING |
| **Silver Table Rows** | 100,000+ |
| **Gold Views Created** | 12 |
| **ML Models Trained** | 4 |
| **Dashboards Imported** | 10 |
| **Application Status** | Running |
| **Approval Rate (Mock)** | 85-90% |

---

## 🎯 Next Steps

1. **Customize Configuration:**
   - Update merchant segments in `silver_transform.py`
   - Adjust fraud score thresholds
   - Configure alert rules

2. **Connect Real Data:**
   - Replace transaction simulator with real payment events
   - Configure streaming ingestion from Kafka/EventHub
   - Set up change data capture (CDC)

3. **Expand ML Models:**
   - Add customer segmentation model
   - Implement time-series forecasting
   - Train deep learning models for fraud detection

4. **Production Hardening:**
   - Set up monitoring and alerting
   - Configure auto-scaling
   - Implement disaster recovery
   - Add authentication and authorization

---

## 📞 Support

For issues or questions:
- Check: [Technical Documentation](./TECHNICAL_DOCUMENTATION.md)
- Review: [Data Flow Guide](./DATA_FLOW.md)
- AI Agents: [AI Agents Guide](./AI_AGENTS_GUIDE.md)

---

**Last Updated:** February 5, 2026  
**Version:** 1.0  
**Estimated Total Deployment Time:** 45-60 minutes
