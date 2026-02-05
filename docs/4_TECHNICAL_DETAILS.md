# Technical Details
## Platform Architecture & Implementation

### Platform Overview

The Payment Approval Optimization Platform is a comprehensive solution built on Databricks that combines real-time data processing, machine learning, AI agents, and modern web technologies to maximize payment approval rates.

---

## Architecture

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         DATABRICKS WORKSPACE                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐ │
│  │   TRANSACTION   │─────▶│   DELTA LIVE     │─────▶│    UNITY    │ │
│  │   SIMULATOR     │      │   TABLES (DLT)   │      │  CATALOG    │ │
│  │  (1000 evt/s)   │      │                  │      │             │ │
│  └─────────────────┘      │  Bronze → Silver │      │  12+ Views  │ │
│                           │    → Gold        │      │  4 Models   │ │
│                           └──────────────────┘      └──────┬──────┘ │
│                                                             │        │
│  ┌─────────────────────────────────────────────────────────┼────┐   │
│  │                     ML & AI LAYER                        │    │   │
│  ├──────────────────────────────────────────────────────────┘    │   │
│  │                                                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │   │
│  │  │   MLflow     │  │    Model     │  │  AI Gateway  │       │   │
│  │  │ Experiments  │─▶│   Serving    │  │ Llama 3.1 70B│       │   │
│  │  └──────────────┘  └──────┬───────┘  └──────┬───────┘       │   │
│  │                           │                  │               │   │
│  │  ┌──────────────┐         │                  │               │   │
│  │  │    Genie     │◀────────┴──────────────────┘               │   │
│  │  │    Spaces    │  (7 AI Agents)                             │   │
│  │  └──────────────┘                                             │   │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   ANALYTICS & VISUALIZATION                      │ │
│  ├─────────────────────────────────────────────────────────────────┤ │
│  │  • 10 Lakeview Dashboards                                       │ │
│  │  • SQL Warehouse (Serverless)                                   │ │
│  │  • Embedded dashboard viewer                                    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└───────────────────────────────────────┬───────────────────────────────┘
                                        │
                                        │ REST API
                                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────┐          ┌─────────────────────────┐   │
│  │   FastAPI Backend       │◀────────▶│    React Frontend       │   │
│  │  (Python 3.11)          │          │  (TypeScript + Bun)     │   │
│  │                         │          │                         │   │
│  │  • Analytics API        │          │  • Dashboard Gallery    │   │
│  │  • Decisioning API      │          │  • ML Models Browser    │   │
│  │  • Notebooks Registry   │          │  • AI Agents Browser    │   │
│  │  • Agents API           │          │  • Notebooks Browser    │   │
│  │  • Unity Catalog Client │          │  • Decisioning UI       │   │
│  └─────────────────────────┘          └─────────────────────────┘   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Layer

### Medallion Architecture

The platform implements the medallion architecture for data processing:

#### Bronze Layer: Raw Ingestion

```python
@dlt.table(
    name="payments_raw_bronze",
    comment="Raw payment events from simulator",
    table_properties={"quality": "bronze"}
)
def payments_raw_bronze():
    return (
        spark.readStream
        .format("delta")
        .option("readChangeFeed", "true")
        .table("payments_stream_input")
        .withColumn("_ingested_at", current_timestamp())
    )
```

**Purpose:** Capture events as-is with audit metadata

#### Silver Layer: Enrichment & Quality

```python
@dlt.table(
    name="payments_enriched_silver",
    comment="Enriched payment events with derived features",
    table_properties={"quality": "silver"}
)
@dlt.expect_or_drop("valid_transaction_id", "transaction_id IS NOT NULL")
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect_or_warn("valid_fraud_score", "fraud_score BETWEEN 0 AND 1")
def payments_enriched_silver():
    return (
        dlt.read_stream("payments_raw_bronze")
        .withColumn("risk_tier", 
            when(col("fraud_score") < 0.3, lit("LOW"))
            .when(col("fraud_score") < 0.7, lit("MEDIUM"))
            .otherwise(lit("HIGH")))
        .withColumn("amount_bucket",
            when(col("amount") < 10, lit("micro"))
            .when(col("amount") < 100, lit("small"))
            .when(col("amount") < 1000, lit("medium"))
            .otherwise(lit("large")))
        .withColumn("is_cross_border", 
            col("issuer_country") != col("merchant_country"))
    )
```

**Features:** Data quality checks, feature engineering, business rules

#### Gold Layer: Business Metrics

12+ aggregated views optimized for analytics:

```sql
-- Example: Executive KPIs
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
WHERE event_date >= CURRENT_DATE - 30;

-- Other key views:
-- v_approval_trends_hourly: Time-series trends
-- v_top_decline_reasons: Decline analysis with recovery potential
-- v_solution_performance: Payment solution comparison
-- v_risk_distribution: Risk tier breakdown
-- v_retry_performance: Retry effectiveness metrics
-- v_performance_by_geography: Geographic analysis
-- v_merchant_performance: Merchant segment insights
-- v_3ds_performance: 3DS security metrics
-- v_financial_summary: Revenue and recovery metrics
-- v_active_alerts: Real-time monitoring alerts
-- v_system_performance: Technical health metrics
-- v_agent_recommendations: AI agent outputs
```

### Unity Catalog Schema

```
main (catalog)
└── payment_analysis_dev (schema) or payment_analysis_prod
    ├── Tables
    │   ├── payments_stream_input (source)
    │   ├── payments_raw_bronze (bronze layer)
    │   ├── payments_enriched_silver (silver layer)
    │   └── agent_recommendations (agent outputs)
    │
    ├── Views (12+ gold views)
    │   ├── v_executive_kpis
    │   ├── v_approval_trends_hourly
    │   ├── v_top_decline_reasons
    │   ├── v_solution_performance
    │   └── ... (8 more)
    │
    └── Models (MLflow-registered)
        ├── approval_propensity_model
        ├── risk_scoring_model
        ├── smart_routing_policy
        └── smart_retry_policy
```

**Governance Features:**
- Fine-grained access control (GRANT/REVOKE)
- Data lineage tracking (automatic)
- Audit logging (all queries logged)
- Data discovery (searchable metadata)

---

## Machine Learning Layer

### Model Architecture

Four models power intelligent decisioning:

#### 1. Approval Propensity Model

**Algorithm:** Random Forest Classifier  
**Accuracy:** ~92%  
**Purpose:** Predict approval probability

```python
# Feature engineering
features = ['amount', 'fraud_score', 'merchant_segment', 
            'card_network', 'uses_3ds', 'is_network_token']

# Training
rf_approval = RandomForestClassifier(
    numTrees=100,
    maxDepth=10,
    featuresCol='features',
    labelCol='is_approved'
)

# Model serving endpoint
POST /serving-endpoints/approval-propensity-endpoint/invocations
{
  "dataframe_records": [{
    "amount": 150.0,
    "fraud_score": 0.15,
    "merchant_segment": "Retail",
    "card_network": "Visa"
  }]
}

# Response
{
  "predictions": [0.87],  # 87% approval probability
  "prediction_binary": [1]
}
```

#### 2. Risk Scoring Model

**Algorithm:** Logistic Regression  
**Accuracy:** ~88%  
**Purpose:** Fraud and AML risk assessment

```python
# Features
features = ['fraud_score', 'amount', 'is_cross_border', 
            'device_trust_score', 'velocity_score']

# Output: Risk tier (LOW/MEDIUM/HIGH)
```

#### 3. Smart Routing Policy

**Algorithm:** Random Forest Classifier  
**Accuracy:** ~75%  
**Purpose:** Recommend optimal payment processor

```python
# Features
features = ['card_network', 'amount', 'merchant_segment', 
            'geography', 'time_of_day']

# Output: Recommended processor (ProcessorA/ProcessorB/ProcessorC)
```

#### 4. Smart Retry Policy

**Algorithm:** Gradient Boosted Trees  
**Accuracy:** ~81%  
**Purpose:** Identify transactions worth retrying

```python
# Features
features = ['decline_reason', 'amount', 'fraud_score', 
            'previous_attempts', 'time_since_decline']

# Output: Should_retry (True/False) + recommended wait time
```

### MLflow Lifecycle

```
1. EXPERIMENTATION
   ├── Feature engineering notebook
   ├── Multiple algorithm trials
   ├── Hyperparameter tuning
   └── Experiment tracking in MLflow

2. MODEL REGISTRATION
   ├── Best model → Unity Catalog
   ├── Model versioning (v1, v2, ...)
   └── Stage transitions (Staging → Production)

3. MODEL SERVING
   ├── REST endpoint creation
   ├── Auto-scaling (0 → N instances)
   ├── A/B testing capability
   └── Monitoring & alerting

4. MONITORING
   ├── Prediction accuracy
   ├── Data drift detection
   ├── Feature importance changes
   └── Re-training triggers
```

### Model Serving Configuration

```yaml
# Example serving endpoint config
served_models:
  - model_name: main.payment_analysis_dev.approval_propensity_model
    model_version: 1
    workload_size: Small
    scale_to_zero_enabled: true
    environment_vars:
      ENABLE_MONITORING: "true"
    traffic_config:
      routes:
        - served_model_name: approval-propensity-1
          traffic_percentage: 100
```

**Performance:**
- **Latency:** <50ms p95
- **Throughput:** 1000+ requests/second
- **Availability:** 99.9% uptime

---

## AI Agents Layer

### Agent Framework

Seven specialized agents leverage different Databricks AI capabilities:

#### Genie Agents (2)

**Technology:** Databricks Genie (natural language SQL)

1. **Approval Optimizer Agent**
   - **Space:** `payment_analysis_genie_space`
   - **Purpose:** Self-service approval insights
   - **Example:** "What's our approval rate for high-risk Visa transactions?"

2. **Decline Insight Agent**
   - **Space:** `payment_decline_analysis_space`
   - **Purpose:** Root cause analysis of declines
   - **Example:** "Why are Mastercard declines increasing in Brazil?"

#### Model Serving Agents (3)

**Technology:** ML models via REST API

3. **Approval Propensity Predictor**
   - **Endpoint:** `/serving-endpoints/approval-propensity-endpoint`
   - **Purpose:** Real-time approval predictions
   - **Latency:** <50ms

4. **Risk Scoring Engine**
   - **Endpoint:** `/serving-endpoints/risk-scoring-endpoint`
   - **Purpose:** Transaction risk assessment
   - **Latency:** <50ms

5. **Smart Router**
   - **Endpoint:** `/serving-endpoints/smart-routing-endpoint`
   - **Purpose:** Optimal processor selection
   - **Latency:** <50ms

#### AI Gateway Agents (2)

**Technology:** Llama 3.1 70B via AI Gateway

6. **Payment Intelligence Assistant**
   - **Route:** `llama-3-1-70b-route`
   - **Purpose:** Conversational insights and recommendations
   - **Example:** "Analyze today's decline patterns and suggest optimizations"

7. **Real-Time Optimizer**
   - **Route:** `llama-3-1-70b-route`
   - **Purpose:** Proactive performance monitoring
   - **Schedule:** Every 2 hours
   - **Actions:** Automated recommendations saved to `agent_recommendations` table

### Agent API Design

```python
# Backend: src/payment_analysis/backend/routes/agents.py
@router.get("/agents")
async def list_agents() -> List[AgentInfo]:
    """Returns all 7 agents with metadata"""
    
@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> AgentInfo:
    """Get specific agent details"""
    
@router.get("/agents/{agent_id}/url")
async def get_agent_url(agent_id: str) -> dict:
    """Get direct Databricks workspace URL"""
```

**Agent Metadata:**
- Name, type, purpose, capabilities
- Example queries
- Databricks resource paths
- Direct workspace links

---

## Analytics Layer

### Lakeview Dashboards

10 pre-built dashboards defined as `.lvdash.json` files:

| Dashboard | File | Widgets | SQL Warehouse |
|-----------|------|---------|---------------|
| Executive Overview | `executive_overview.lvdash.json` | 12 | Serverless |
| Decline Analysis | `decline_recovery.lvdash.json` | 10 | Serverless |
| Real-Time Monitoring | `realtime_monitoring.lvdash.json` | 8 | Serverless |
| Fraud & Risk | `fraud_analysis.lvdash.json` | 9 | Serverless |
| Merchant Performance | `merchant_insights.lvdash.json` | 11 | Serverless |
| Routing Optimization | `routing_optimization.lvdash.json` | 8 | Serverless |
| Daily Trends | `daily_approval_trends.lvdash.json` | 7 | Serverless |
| 3DS Security | `security_compliance.lvdash.json` | 6 | Serverless |
| Financial Impact | `financial_impact.lvdash.json` | 9 | Serverless |
| Technical Performance | `performance_metrics.lvdash.json` | 7 | Serverless |

#### Dashboard Structure

```json
{
  "display_name": "Executive Overview",
  "warehouse_id": "{{ resources.warehouses.shared_sql_warehouse.id }}",
  "datasets": [
    {
      "name": "executive_kpis",
      "query_text": "SELECT * FROM v_executive_kpis"
    }
  ],
  "widgets": [
    {
      "name": "approval_rate_card",
      "type": "counter",
      "query": "SELECT approval_rate_pct FROM executive_kpis"
    }
  ]
}
```

**Features:**
- Dynamic refresh (configurable intervals)
- Cross-filtering between widgets
- Export to PDF/CSV
- Embedded sharing (iframe)
- Mobile-responsive layouts

### Genie Spaces

Natural language analytics for business users:

```yaml
# Genie space configuration
name: Payment Approval Analytics
description: Self-service analytics for approval rates
instructions: |
  You are an expert payment analytics assistant.
  Help users analyze approval rates, decline reasons, and optimization opportunities.
  Always provide data-driven recommendations.

sample_questions:
  - "What's our approval rate today?"
  - "Show me top 5 decline reasons"
  - "Compare Visa vs Mastercard performance"
  - "Which merchants have declining trends?"
  - "How many high-risk transactions today?"

sql_warehouse_id: "{{ resources.warehouses.shared_sql_warehouse.id }}"
catalog: main
schema: payment_analysis_dev
```

**Capabilities:**
- Natural language to SQL translation
- Automatic chart generation
- Follow-up question handling
- Data export

---

## Application Layer

### FastAPI Backend

#### Architecture

```python
# src/payment_analysis/backend/
├── main.py                 # Application entry point
├── config.py               # Configuration management
├── router.py               # Main API router
├── routes/
│   ├── analytics.py        # KPIs, trends, declines
│   ├── decisioning.py      # ML model predictions
│   ├── experiments.py      # A/B testing
│   ├── incidents.py        # Alert management
│   ├── notebooks.py        # Notebook registry
│   └── agents.py           # AI agents registry
└── clients/
    └── databricks_client.py # Unity Catalog SQL client
```

#### Key Endpoints

```python
# Analytics API
GET  /api/analytics/kpis/databricks
GET  /api/analytics/trends
GET  /api/analytics/declines/databricks
GET  /api/analytics/solutions
GET  /api/analytics/geography

# Decisioning API (ML Models)
POST /api/decisioning/auth
POST /api/decisioning/retry
POST /api/decisioning/routing

# Notebooks Registry
GET  /api/notebooks/notebooks
GET  /api/notebooks/categories
GET  /api/notebooks/{notebook_id}

# AI Agents API
GET  /api/agents/agents
GET  /api/agents/{agent_id}
GET  /api/agents/{agent_id}/url
GET  /api/agents/type-summary
```

#### Database Client

```python
class DatabricksClient:
    """Unity Catalog SQL client"""
    
    def __init__(self):
        self.workspace_url = os.getenv("DATABRICKS_WORKSPACE_URL")
        self.token = os.getenv("DATABRICKS_TOKEN")
        self.warehouse_id = os.getenv("SQL_WAREHOUSE_ID")
    
    async def execute_query(self, query: str) -> List[dict]:
        """Execute SQL against Unity Catalog"""
        # Uses Databricks SQL Connector
        with sql.connect(
            server_hostname=self.workspace_url,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            access_token=self.token
        ) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
```

### React Frontend

#### Architecture

```typescript
// src/payment_analysis/ui/
├── routes/
│   ├── _sidebar/
│   │   ├── dashboard.tsx         // KPI cards & trends
│   │   ├── dashboards.tsx        // Lakeview gallery
│   │   ├── notebooks.tsx         // Notebook browser
│   │   ├── models.tsx            // ML models page
│   │   ├── ai-agents.tsx         // AI agents gallery
│   │   ├── decisioning.tsx       // Policy playground
│   │   ├── experiments.tsx       // A/B testing
│   │   └── declines.tsx          // Decline analysis
│   └── _sidebar.tsx              // Layout & navigation
├── components/
│   ├── KPICard.tsx
│   ├── TrendChart.tsx
│   ├── DashboardEmbed.tsx
│   └── AgentCard.tsx
└── lib/
    └── api.ts                    // API client
```

#### Key Features

**1. Dashboard Gallery**
```typescript
// Embedded Lakeview dashboards
<iframe 
  src={`${databricksUrl}/sql/dashboards/${dashboardId}?embed=true`}
  width="100%"
  height="800px"
/>
```

**2. ML Models Browser**
```typescript
const models = [
  {
    name: "Approval Propensity",
    accuracy: "92%",
    path: "main.payment_analysis_dev.approval_propensity_model",
    mlflowUrl: `${databricksUrl}/#mlflow/experiments/...`
  }
  // ... 3 more models
]
```

**3. AI Agents Gallery**
```typescript
// Fetch from backend API
const { data: agents } = useQuery('/api/agents/agents')

agents.map(agent => (
  <AgentCard
    name={agent.name}
    type={agent.type}
    capabilities={agent.capabilities}
    exampleQueries={agent.example_queries}
    workspaceUrl={agent.workspace_url}
  />
))
```

**4. Notebook Browser**
```typescript
// Categorized notebook registry
const notebooks = {
  'data_engineering': [...],
  'ml': [...],
  'intelligence': [...],
  'dashboards': [...]
}

// One-click notebook opening
const openNotebook = (path: string) => {
  window.open(
    `${databricksUrl}/workspace${path}`,
    '_blank'
  )
}
```

#### Styling & UX

- **Framework:** TailwindCSS
- **Icons:** Lucide React
- **Components:** Custom design system
- **Responsive:** Mobile-first design
- **Dark Mode:** Not yet implemented

---

## Deployment

### Databricks Asset Bundles (DABs)

All infrastructure defined in `databricks.yml`:

```yaml
bundle:
  name: payment_analysis

workspace:
  host: ${DATABRICKS_HOST}
  current_user:
    userName: user@company.com

targets:
  dev:
    default: true
    mode: development
    workspace:
      root_path: ~/.bundle/${bundle.name}_${workspace.current_user.userName}

resources:
  # DLT Pipeline
  pipelines:
    payment_pipeline:
      name: "payment_processing_pipeline_${workspace.current_user.userName}"
      libraries:
        - notebook:
            path: ./src/payment_analysis/pipelines/realtime_pipeline.py
      target: payment_analysis_dev
      continuous: true

  # SQL Warehouse
  warehouses:
    shared_sql_warehouse:
      name: "payment_warehouse_${workspace.current_user.userName}"
      cluster_size: Small
      enable_serverless_compute: true
      auto_stop_mins: 10

  # Dashboards (10 total)
  dashboards:
    executive_overview:
      name: "Executive Overview - ${workspace.current_user.userName}"
      definition_path: ./resources/dashboards/executive_overview.lvdash.json
      warehouse_id: ${resources.warehouses.shared_sql_warehouse.id}

  # ML Jobs
  jobs:
    train_models:
      name: "ML Model Training - ${workspace.current_user.userName}"
      tasks:
        - task_key: train_all_models
          notebook_task:
            notebook_path: ./src/payment_analysis/ml/train_models.py
          new_cluster:
            spark_version: 13.3.x-cpu-ml-scala2.12
            node_type_id: i3.xlarge
            num_workers: 2

  # Genie Spaces
  model_serving_endpoints:
    approval_propensity:
      name: "approval-propensity-${workspace.current_user.userName}"
      config:
        served_models:
          - model_name: ${var.catalog}.${var.schema}.approval_propensity_model
            model_version: 1
            workload_size: Small
            scale_to_zero_enabled: true
```

### Deployment Commands

```bash
# 1. Validate bundle configuration
databricks bundle validate --target dev

# 2. Deploy all resources
databricks bundle deploy --target dev

# 3. Start DLT pipeline
databricks pipelines start --pipeline-id <pipeline_id>

# 4. Run ML training job
databricks jobs run-now --job-id <job_id>

# 5. Deploy web application
cd src/payment_analysis
apx deploy
```

### Environment Variables

```bash
# .env file
DATABRICKS_HOST=https://adb-984752964297111.11.azuredatabricks.net
DATABRICKS_TOKEN=dapi...
SQL_WAREHOUSE_ID=abc123...
CATALOG=main
SCHEMA=payment_analysis_dev
```

---

## Security & Governance

### Unity Catalog Access Control

```sql
-- Grant read access to analysts
GRANT SELECT ON SCHEMA payment_analysis_dev TO `analysts@company.com`;

-- Grant model serving access to application
GRANT EXECUTE ON MODEL approval_propensity_model TO `app_service_principal`;

-- Audit query
SELECT * FROM system.access.audit 
WHERE action_name = 'modelServing' 
AND request_timestamp > CURRENT_DATE - 7;
```

### Model Serving Authentication

```python
# Backend uses service principal
headers = {
    "Authorization": f"Bearer {os.getenv('DATABRICKS_TOKEN')}",
    "Content-Type": "application/json"
}

response = requests.post(
    f"{workspace_url}/serving-endpoints/{endpoint_name}/invocations",
    headers=headers,
    json=payload
)
```

### Data Privacy

- **PII Handling:** No PII stored (transaction IDs are anonymized)
- **Data Retention:** 90-day rolling window
- **Encryption:** At-rest (Delta Lake) and in-transit (TLS)
- **Compliance:** GDPR, PCI-DSS ready

---

## Monitoring & Operations

### System Health Metrics

```sql
-- Dashboard: Technical Performance
CREATE VIEW v_system_performance AS
SELECT
    event_date,
    AVG(CAST(processing_latency_ms AS DOUBLE)) as avg_latency_ms,
    MAX(processing_latency_ms) as p95_latency_ms,
    COUNT(*) as total_events,
    SUM(CASE WHEN pipeline_error THEN 1 ELSE 0 END) as error_count
FROM payments_enriched_silver
WHERE event_date >= CURRENT_DATE - 7
GROUP BY event_date;
```

### Model Monitoring

```python
# MLflow tracking
with mlflow.start_run():
    mlflow.log_metric("accuracy", 0.92)
    mlflow.log_metric("precision", 0.89)
    mlflow.log_metric("recall", 0.94)
    mlflow.log_param("model_type", "random_forest")
    mlflow.sklearn.log_model(model, "approval_propensity")
```

### Alerting

```sql
-- Create alert for declining approval rates
CREATE ALERT approval_rate_drop
ON SCHEDULE CRON '0 * * * *'  -- Every hour
AS
SELECT approval_rate_pct 
FROM v_executive_kpis 
WHERE approval_rate_pct < 85;  -- Threshold
```

---

## Performance Optimization

### Query Optimization

```sql
-- Use partitioning for large tables
CREATE TABLE payments_enriched_silver
PARTITIONED BY (event_date)
CLUSTER BY (merchant_id)
AS SELECT ...

-- Z-ORDER for common filters
OPTIMIZE payments_enriched_silver
ZORDER BY (fraud_score, card_network);
```

### Caching Strategy

```python
# Frontend: React Query caching
const { data } = useQuery(
  'executive-kpis',
  fetchKPIs,
  { 
    staleTime: 30000,  // 30 seconds
    cacheTime: 300000  // 5 minutes
  }
)
```

### Model Serving Optimization

```yaml
# Auto-scaling configuration
config:
  served_models:
    - workload_size: Small  # Start small
      scale_to_zero_enabled: true  # Cost savings
      auto_capture_config:
        enabled: true  # Monitor drift
```

---

## Development Workflow

### Local Development

```bash
# Backend
cd src/payment_analysis
bun install
bun run dev  # Starts FastAPI on :3000

# Frontend
cd src/payment_analysis/ui
bun install
bun run dev  # Starts Vite dev server on :5173
```

### Testing

```python
# Backend unit tests
pytest tests/

# Frontend tests
bun test
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy to Databricks
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy bundle
        run: |
          databricks bundle validate --target prod
          databricks bundle deploy --target prod
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Data Storage** | Delta Lake | ACID transactions, time travel, versioning |
| **Data Governance** | Unity Catalog | Security, lineage, discovery |
| **Data Processing** | Delta Live Tables | Automated ETL with quality checks |
| **Compute** | Databricks Clusters | Distributed processing |
| **SQL Analytics** | SQL Warehouse (Serverless) | Low-latency queries for dashboards |
| **ML Training** | MLflow + Spark ML | Experiment tracking, model registry |
| **ML Serving** | Model Serving | Real-time predictions (<50ms) |
| **Dashboards** | Lakeview | Interactive visualizations |
| **NL Analytics** | Genie | Natural language to SQL |
| **Conversational AI** | AI Gateway + Llama 3.1 | LLM-powered insights |
| **Backend API** | FastAPI (Python 3.11) | REST endpoints |
| **Frontend** | React + TypeScript + Bun | Modern web UI |
| **Routing** | TanStack Router | Type-safe routing |
| **Styling** | TailwindCSS | Utility-first CSS |
| **Deployment** | Databricks Asset Bundles | Infrastructure as code |
| **Version Control** | Git + GitHub | Source control |

---

## Troubleshooting

### Common Issues

**1. DLT Pipeline Stuck**
```bash
# Check pipeline status
databricks pipelines get --pipeline-id <id>

# Restart pipeline
databricks pipelines stop --pipeline-id <id>
databricks pipelines start --pipeline-id <id>
```

**2. Model Serving 503 Error**
```bash
# Check endpoint status
databricks serving-endpoints get --name approval-propensity-endpoint

# Endpoint might be scaled to zero (cold start ~30s)
```

**3. Dashboard Not Loading**
- Verify SQL Warehouse is running
- Check Unity Catalog permissions
- Validate dashboard JSON syntax

**4. Frontend CORS Error**
```python
# Add CORS middleware to FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

## Future Enhancements

### Planned Features

1. **Real-Time Decisioning**: Sub-10ms predictions via Databricks Online Tables
2. **Advanced Fraud Detection**: Graph neural networks for fraud rings
3. **Personalized Routing**: Per-merchant optimization models
4. **Causal Inference**: Counterfactual analysis of policy changes
5. **AutoML Integration**: Automated model retraining
6. **Mobile App**: Native iOS/Android dashboards
7. **Slack Integration**: AI agent alerts and queries
8. **Advanced A/B Testing**: Statistical significance testing

### Scalability Roadmap

| Current | Target | Solution |
|---------|--------|----------|
| 1K events/sec | 10K events/sec | Increase DLT cluster size |
| 4 ML models | 10+ models | Model registry versioning |
| 10 dashboards | 50+ dashboards | Dashboard folders & tags |
| 100 users | 1000+ users | SSO, RBAC, user groups |

---

## References

- **Databricks Documentation**: https://docs.databricks.com
- **Delta Lake Guide**: https://docs.delta.io
- **MLflow Documentation**: https://mlflow.org/docs
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **React Documentation**: https://react.dev

---

For deployment instructions, see [1_DEPLOYMENT_GUIDE.md](./1_DEPLOYMENT_GUIDE.md).
