# Data Flow: From Transaction to Insight

This document explains the complete journey of payment data through the platform—from simulated transaction ingestion to AI-powered optimization to user-facing analytics.

---

## End-to-End Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  1. INGESTION          2. PROCESSING         3. INTELLIGENCE                │
│  ┌───────────┐        ┌───────────┐         ┌───────────┐                   │
│  │ Simulator │───────▶│  Bronze   │────────▶│ ML Models │                   │
│  │ 1000/sec  │        │   Layer   │         │ Training  │                   │
│  └───────────┘        └─────┬─────┘         └─────┬─────┘                   │
│                             │                     │                          │
│                             ▼                     ▼                          │
│                       ┌───────────┐         ┌───────────┐                   │
│                       │  Silver   │────────▶│ AI Agents │                   │
│                       │   Layer   │         │ Analysis  │                   │
│                       └─────┬─────┘         └─────┬─────┘                   │
│                             │                     │                          │
│                             ▼                     ▼                          │
│  4. ANALYTICS         ┌───────────┐         ┌───────────┐   5. APPLICATION  │
│  ┌───────────┐        │   Gold    │◀────────│  Model    │   ┌───────────┐   │
│  │Dashboards │◀───────│   Layer   │         │ Serving   │──▶│  Web App  │   │
│  └───────────┘        └───────────┘         └───────────┘   └───────────┘   │
│                             │                                     │          │
│                             ▼                                     ▼          │
│                       ┌───────────┐                         ┌───────────┐   │
│                       │   Genie   │◀────────────────────────│   Users   │   │
│                       │ (Ask AI)  │                         │           │   │
│                       └───────────┘                         └───────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Transaction Ingestion

### Simulated Transaction Stream

The **Transaction Simulator** generates realistic payment events at high volume for testing and demonstration.

```python
# Key configuration
events_per_second: 1000
duration_minutes: 60
output: Delta table with Change Data Feed enabled
```

### Transaction Event Schema

Each event contains rich payment context:

| Field | Description | Example |
|-------|-------------|---------|
| `transaction_id` | Unique identifier | `txn_abc123` |
| `amount` | Transaction amount | `150.00` |
| `currency` | ISO currency code | `USD` |
| `merchant_id` | Merchant identifier | `merch_xyz` |
| `merchant_segment` | Business category | `Retail`, `Digital`, `Travel` |
| `card_network` | Payment network | `Visa`, `Mastercard`, `Amex` |
| `issuer_country` | Card issuing country | `US`, `BR`, `MX` |
| `fraud_score` | Pre-computed risk (0-1) | `0.15` |
| `uses_3ds` | 3D Secure enabled | `true` |
| `is_network_token` | Tokenized card | `false` |
| `event_timestamp` | Transaction time | `2026-02-04T10:30:00Z` |

### Ingestion Path

```
Transaction Simulator
        │
        ▼
┌─────────────────────┐
│  payments_stream_   │  Delta table with CDF
│      input          │  (Change Data Feed)
└─────────────────────┘
        │
        ▼
   DLT Pipeline
   (Bronze Layer)
```

---

## Stage 2: Data Processing (Medallion Architecture)

### Bronze Layer: Raw Ingestion

**Purpose**: Capture raw events exactly as received, with minimal transformation.

```python
@dlt.table(name="payments_raw_bronze")
def payments_raw_bronze():
    return (
        spark.readStream
        .format("delta")
        .option("readChangeFeed", "true")
        .table("payments_stream_input")
    )
```

**Output**: Raw events with ingestion metadata (`_ingested_at`, `_source_file`)

---

### Silver Layer: Enrichment & Feature Engineering

**Purpose**: Clean, validate, and enrich data with derived features.

#### Transformations Applied

| Feature | Logic | Purpose |
|---------|-------|---------|
| `risk_tier` | `LOW` (<0.3), `MEDIUM` (0.3-0.7), `HIGH` (>0.7) | Risk classification |
| `amount_bucket` | `micro` (<10), `small` (<100), `medium` (<1000), `large` (1000+) | Amount segmentation |
| `is_cross_border` | `issuer_country != merchant_country` | Geographic risk flag |
| `composite_risk_score` | `0.4*fraud + 0.3*aml + 0.3*device_trust` | Combined risk metric |
| `event_hour` | Extract hour from timestamp | Time-based analysis |
| `event_date` | Extract date from timestamp | Daily aggregation |

#### Data Quality Expectations

```python
@dlt.expect_or_drop("valid_transaction_id", "transaction_id IS NOT NULL")
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect_or_warn("valid_fraud_score", "fraud_score BETWEEN 0 AND 1")
```

**Output**: `payments_enriched_silver` — Clean, feature-rich transaction data

---

### Gold Layer: Business Metrics & Aggregations

**Purpose**: Pre-computed metrics optimized for analytics and dashboards.

#### Key Views Created

| View | Description | Refresh |
|------|-------------|---------|
| `v_executive_kpis` | Overall approval rate, volume, value | Real-time |
| `v_approval_trends_hourly` | Hourly approval rate trends | Hourly |
| `v_top_decline_reasons` | Decline reasons with recovery potential | Hourly |
| `v_performance_by_geography` | Approval rates by country | Daily |
| `v_solution_performance` | Performance by payment processor | Hourly |
| `v_risk_distribution` | Transaction distribution by risk tier | Real-time |
| `v_active_alerts` | Triggered alerts and anomalies | Real-time |

#### Sample Gold View

```sql
CREATE OR REPLACE VIEW v_executive_kpis AS
SELECT
    COUNT(*) as total_transactions,
    SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) as approved_count,
    ROUND(AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) * 100, 2) as approval_rate_pct,
    ROUND(AVG(fraud_score), 4) as avg_fraud_score,
    ROUND(SUM(amount), 2) as total_transaction_value,
    MIN(event_date) as period_start,
    MAX(event_date) as period_end
FROM payments_enriched_silver
WHERE event_date >= CURRENT_DATE - 30
```

---

## Stage 3: Intelligence Layer

### Machine Learning Models

Three models are trained on historical data to optimize payment decisions:

| Model | Input Features | Output | Use Case |
|-------|----------------|--------|----------|
| **Approval Propensity** | amount, fraud_score, merchant_segment, card_network | Probability (0-1) | Predict if transaction will be approved |
| **Risk Scoring** | fraud_score, amount, is_cross_border, device_trust | Risk tier | Classify transaction risk level |
| **Smart Routing** | card_network, amount, merchant_segment, geography | Processor name | Select optimal payment processor |

#### Model Training Flow

```
Silver Data ──▶ Feature Engineering ──▶ MLflow Training ──▶ Model Registry
                                                                   │
                                                                   ▼
                                                          Model Serving
                                                          (Real-time API)
```

### AI Agents

Six specialized agents analyze data and provide recommendations:

```
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR AGENT                          │
│         Coordinates all agents for comprehensive analysis        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Smart Routing │   │  Smart Retry  │   │Decline Analyst│
│    Agent      │   │    Agent      │   │    Agent      │
│               │   │               │   │               │
│ • Route perf  │   │ • Retry rates │   │ • Decline     │
│ • Cascade     │   │ • Recovery    │   │   patterns    │
│   config      │   │   windows     │   │ • Root cause  │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐
│ Risk Assessor │   │  Performance  │
│    Agent      │   │  Recommender  │
│               │   │               │
│ • Fraud       │   │ • KPI trends  │
│   monitoring  │   │ • Optimization│
│ • Anomalies   │   │   actions     │
└───────────────┘   └───────────────┘
```

#### Agent Workflow

1. **Query**: User or schedule triggers agent
2. **Tool Execution**: Agent runs SQL queries against Gold layer
3. **LLM Reasoning**: Results analyzed by Llama 3.1 70B
4. **Recommendations**: Actionable insights generated
5. **Storage**: Results saved to Delta tables for audit

---

## Stage 4: Analytics & Visualization

### Lakeview Dashboards

Three pre-built dashboards provide insights for different audiences:

| Dashboard | Audience | Key Metrics |
|-----------|----------|-------------|
| **Executive Overview** | C-Suite | Approval rate, volume, revenue impact |
| **Decline Analysis** | Operations | Decline reasons, recovery potential, trends |
| **Real-Time Monitoring** | Operations | Live metrics, alerts, anomalies |

#### Dashboard Components

```
Executive Overview
├── KPI Cards (approval rate, volume, value, fraud score)
├── Approval Rate Trend (line chart, 7 days)
├── Geographic Performance (bar chart by country)
└── Top Decline Reasons (table with recovery %)

Decline Analysis
├── Decline Breakdown (pie chart by reason)
├── Recovery Potential (stacked bar)
├── Retry Success Rate (line chart)
└── Merchant Analysis (sortable table)

Real-Time Monitoring
├── Live Transaction Counter
├── Active Alerts (severity-coded)
├── Solution Performance (comparison bars)
└── Risk Distribution (gauge charts)
```

### Genie: Natural Language Analytics

Users can ask questions in plain English:

| Question | Genie Response |
|----------|----------------|
| "What's our approval rate?" | "Current approval rate is 87.5%, up 1.2% from last week" |
| "Show me top decline reasons" | Table with reasons, counts, and recovery potential |
| "Compare Visa vs Mastercard" | Side-by-side approval rates and volume |
| "Which merchants need attention?" | List of merchants with declining approval rates |

#### Genie Configuration

```yaml
# Sample questions trained into Genie
- "What is the current approval rate?"
- "Show me top 5 decline reasons"
- "Compare approval rates by country"
- "Which payment solution performs best?"
- "How many high risk transactions today?"
```

---

## Stage 5: Application Layer

### FastAPI Backend

The API serves as the bridge between Databricks and end users:

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  /api/kpis/databricks     ──▶  Unity Catalog Query      │
│  /api/trends              ──▶  Gold Layer Views         │
│  /api/declines/databricks ──▶  Decline Summary View     │
│  /api/solutions           ──▶  Solution Performance     │
│                                                          │
│  /api/ml/approval         ──▶  Model Serving Endpoint   │
│  /api/ml/risk             ──▶  Model Serving Endpoint   │
│  /api/ml/routing          ──▶  Model Serving Endpoint   │
│                                                          │
│  /api/decision/auth       ──▶  Policy Engine            │
│  /api/decision/retry      ──▶  Policy Engine            │
│  /api/decision/routing    ──▶  Policy Engine            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### React Frontend

Modern UI for business users to interact with the platform:

| Page | Features |
|------|----------|
| **Dashboard** | KPI cards, trend charts, quick actions |
| **Declines** | Decline analysis, drill-down, export |
| **Decisioning** | Test policies, view recommendations |
| **Experiments** | A/B test configuration and results |
| **Incidents** | Alert management, remediation tracking |

---

## Data Lineage Summary

```
Transaction Event (Source)
    │
    ├──▶ payments_stream_input (Raw Delta Table)
    │         │
    │         ▼
    │    payments_raw_bronze (DLT Bronze)
    │         │
    │         ▼
    │    payments_enriched_silver (DLT Silver)
    │         │
    │         ├──▶ v_executive_kpis (Gold View)
    │         ├──▶ v_approval_trends_hourly (Gold View)
    │         ├──▶ v_top_decline_reasons (Gold View)
    │         ├──▶ v_solution_performance (Gold View)
    │         │
    │         ├──▶ ML Model Training
    │         │         │
    │         │         ▼
    │         │    Model Serving Endpoints
    │         │
    │         └──▶ AI Agent Analysis
    │                   │
    │                   ▼
    │              Recommendations
    │
    └──▶ End User (Dashboards, Genie, Web App)
```

---

## Key Performance Metrics

| Metric | Target | Measurement Point |
|--------|--------|-------------------|
| Ingestion Latency | <1 second | Simulator → Bronze |
| Processing Latency | <5 seconds | Bronze → Silver |
| Query Response Time | <2 seconds | Gold View → Dashboard |
| ML Inference Latency | <100ms | API → Model Serving |
| Agent Response Time | <30 seconds | Query → Recommendation |

---

## Summary

This platform transforms raw payment events into actionable intelligence through:

1. **High-Volume Ingestion**: 1000+ events/second with sub-second latency
2. **Automated Processing**: DLT pipelines ensure data quality and freshness
3. **ML-Powered Decisions**: Real-time predictions for approval, risk, and routing
4. **AI Agent Analysis**: Continuous optimization recommendations
5. **Self-Service Analytics**: Dashboards and natural language queries for all users

The result: **Higher approval rates, lower fraud, and faster insights**—all on a unified Databricks platform.
