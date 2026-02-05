# Data Flow Summary
## From Transaction to Insight

### Quick Overview

This platform transforms payment events into intelligence through 5 stages:

```
INGESTION → PROCESSING → INTELLIGENCE → ANALYTICS → APPLICATION
   1000/s    Medallion    ML + AI      Dashboards      Web App
             Architecture   Agents        + Genie
```

---

## Stage 1: Ingestion

### Transaction Simulator
- **Rate:** 1,000 events/second
- **Output:** `payments_stream_input` Delta table with Change Data Feed
- **Schema:** Transaction ID, amount, merchant, card network, fraud score, timestamps

### Sample Event
```json
{
  "transaction_id": "txn_abc123",
  "amount": 150.00,
  "currency": "USD",
  "merchant_segment": "Retail",
  "card_network": "Visa",
  "fraud_score": 0.15,
  "uses_3ds": true,
  "event_timestamp": "2026-02-04T10:30:00Z"
}
```

**Target:** <1 second ingestion latency

---

## Stage 2: Processing (Medallion Architecture)

### Bronze Layer: Raw Capture
- **Purpose:** Ingest events as-is with minimal transformation
- **Table:** `payments_raw_bronze`
- **Features:** Audit columns (`_ingested_at`, `_source_file`)

### Silver Layer: Enrichment
- **Purpose:** Clean, validate, and derive features
- **Table:** `payments_enriched_silver`
- **Transformations:**
  - `risk_tier` (LOW/MEDIUM/HIGH based on fraud score)
  - `amount_bucket` (micro/small/medium/large)
  - `is_cross_border` (issuer country ≠ merchant country)
  - `composite_risk_score` (weighted fraud + AML + device trust)
  - `event_hour`, `event_date` for time-based analysis

### Gold Layer: Metrics
- **Purpose:** Pre-computed business metrics for dashboards
- **Views:** 12+ aggregated views optimized for analytics
- **Key Views:**
  - `v_executive_kpis` - Overall approval rate, volume, value
  - `v_approval_trends_hourly` - Time-series trends
  - `v_top_decline_reasons` - Decline analysis with recovery potential
  - `v_solution_performance` - Payment solution comparison
  - `v_risk_distribution` - Risk tier breakdown
  - `v_retry_performance` - Retry effectiveness metrics

**Target:** <5 seconds Bronze → Silver → Gold

---

## Stage 3: Intelligence

### Machine Learning Models

| Model | Accuracy | Purpose | Unity Catalog Path |
|-------|----------|---------|-------------------|
| **Approval Propensity** | ~92% | Predict approval likelihood | `main.payment_analysis_dev.approval_propensity_model` |
| **Risk Scoring** | ~88% | Fraud & AML risk classification | `main.payment_analysis_dev.risk_scoring_model` |
| **Smart Routing** | ~75% | Recommend optimal processor | `main.payment_analysis_dev.smart_routing_policy` |
| **Smart Retry** | ~81% | Identify recovery opportunities | `main.payment_analysis_dev.smart_retry_policy` |

**Model Training Flow:**
```
Silver Data → Feature Engineering → MLflow Training → Model Registry → Model Serving
```

### AI Agents (7 Databricks Agents)

| Agent | Type | Purpose | Schedule |
|-------|------|---------|----------|
| **Approval Optimizer** | Genie | Natural language approval insights | On-demand |
| **Approval Propensity Predictor** | Model Serving | Real-time approval predictions | API |
| **Risk Scoring Engine** | Model Serving | Transaction risk assessment | API |
| **Smart Router** | Model Serving | Optimal processor selection | API |
| **Payment Intelligence Assistant** | AI Gateway (Llama 3.1) | Conversational insights | On-demand |
| **Decline Insight Agent** | Genie | Root cause analysis | On-demand |
| **Real-Time Optimizer** | AI Gateway (Llama 3.1) | Performance recommendations | Every 2 hours |

**Target:** <50ms model serving latency, <30s agent response

---

## Stage 4: Analytics

### Lakeview Dashboards (10 Dashboards)

| Dashboard | Category | Key Metrics | Source Tables |
|-----------|----------|-------------|---------------|
| **Executive Overview** | Executive | Approval rate, volume, revenue | `v_executive_kpis` |
| **Decline Analysis** | Operations | Decline reasons, recovery potential | `v_top_decline_reasons` |
| **Real-Time Monitoring** | Operations | Live transactions, alerts, anomalies | `v_active_alerts` |
| **Fraud & Risk** | Technical | Fraud detection, risk tiers | `v_risk_distribution` |
| **Merchant Performance** | Operations | Segment analysis, geography | `v_performance_by_geography` |
| **Routing Optimization** | Technical | Processor performance, retry success | `v_solution_performance`, `v_retry_performance` |
| **Daily Trends** | Executive | Day-over-day comparison | `v_approval_trends_hourly` |
| **3DS & Security** | Technical | Authentication analysis | `v_3ds_performance` |
| **Financial Impact** | Executive | Revenue metrics, recovery | `v_financial_summary` |
| **Performance & Latency** | Technical | System health, processing time | `v_system_performance` |

### Genie (Natural Language Analytics)

Business users ask questions in plain English:
- "What's our approval rate today?"
- "Show me top decline reasons"
- "Compare Visa vs Mastercard performance"
- "Which merchants have declining trends?"

**Target:** >85% query success rate, 100+ monthly active users

---

## Stage 5: Application

### FastAPI Backend
REST API connecting Databricks to users:

| Endpoint | Data Source | Purpose |
|----------|-------------|---------|
| `/api/analytics/kpis/databricks` | `v_executive_kpis` | KPI cards |
| `/api/analytics/trends` | `v_approval_trends_hourly` | Trend charts |
| `/api/analytics/declines/databricks` | `v_top_decline_reasons` | Decline analysis |
| `/api/decisioning/auth` | ML models via Model Serving | Real-time decisions |
| `/api/notebooks/*` | Workspace API | Notebook metadata & URLs |
| `/api/agents/*` | Agent registry | AI agent browser |

### React Frontend
Modern web UI with 8 pages:

| Page | Features | Data Source |
|------|----------|-------------|
| **Dashboard** | KPI cards, trend charts | `/api/analytics/kpis/databricks` |
| **Dashboards Gallery** | 10 Lakeview dashboards | Embedded Lakeview |
| **Notebooks Browser** | 12 notebooks with workspace links | `/api/notebooks/notebooks` |
| **ML Models** | 4 models with metrics | Static + MLflow links |
| **AI Agents** | 7 agents with capabilities | `/api/agents/agents` |
| **Decisioning** | Test ML policies interactively | `/api/decisioning/*` |
| **Experiments** | A/B testing | `/api/experiments/*` |
| **Declines** | Decline analysis | `/api/analytics/declines/databricks` |

**Target:** <2s page load, <500ms API response

---

## Complete Data Lineage Example

### "Approval Rate" KPI Journey

1. **Source:** Transaction simulator generates event at `10:30:00`
2. **Bronze (10:30:01):** Raw event lands in `payments_raw_bronze` via DLT
3. **Silver (10:30:03):** Enriched with features in `payments_enriched_silver`
4. **Gold (10:30:05):** Aggregated in `v_executive_kpis` view:
   ```sql
   SELECT 
     ROUND(AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) * 100, 2) as approval_rate_pct
   FROM payments_enriched_silver
   WHERE event_date >= CURRENT_DATE - 30
   ```
5. **Backend (10:30:06):** FastAPI queries `v_executive_kpis` via SQL Warehouse
6. **Frontend (10:30:06.5):** React dashboard displays "87.23%" in KPI card
7. **User (10:30:07):** Business user sees updated approval rate

**Total latency:** ~7 seconds (event → UI)

---

## Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| Ingestion latency | <1s | ~500ms |
| Bronze → Silver | <3s | ~2s |
| Silver → Gold | <2s | ~1s |
| API query time | <2s | ~800ms |
| ML inference | <100ms | ~45ms |
| Dashboard load | <3s | ~1.5s |
| Agent response | <30s | ~15-20s |

---

## Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Data Storage** | Delta Lake | ACID transactions, time travel |
| **Governance** | Unity Catalog | Security, lineage, access control |
| **Pipelines** | Delta Live Tables | Automated ETL with quality checks |
| **ML Training** | MLflow | Experiment tracking, model registry |
| **ML Serving** | Model Serving | Low-latency real-time predictions |
| **Dashboards** | Lakeview | Interactive visualizations |
| **NL Analytics** | Genie | Ask questions in plain English |
| **Conversational AI** | AI Gateway + Llama 3.1 | LLM-powered insights |
| **Backend API** | FastAPI | REST endpoints |
| **Frontend** | React + TanStack Router | Modern web UI |

---

## Deployment

All resources deployed via **Databricks Asset Bundles (DABs)**:

```bash
# Deploy all infrastructure
databricks bundle deploy --target dev

# Start simulator (generates data)
databricks jobs run-now --job-id <simulator_job_id>

# Start DLT pipeline (processes data)
databricks pipelines start --pipeline-id <pipeline_id>

# Deploy web app
cd src/payment_analysis && apx deploy
```

**Target:** <15 minutes for full deployment

---

## Summary

The platform processes payment events through:

1. **High-volume ingestion** (1000 events/sec)
2. **Medallion architecture** (Bronze → Silver → Gold)
3. **ML-powered intelligence** (4 models + 7 AI agents)
4. **Self-service analytics** (10 dashboards + Genie)
5. **Modern web application** (FastAPI + React)

**Result:** Sub-10-second latency from event to insight, enabling real-time payment optimization.

For detailed implementation steps, see [1_DEPLOYMENT_GUIDE.md](./1_DEPLOYMENT_GUIDE.md).
