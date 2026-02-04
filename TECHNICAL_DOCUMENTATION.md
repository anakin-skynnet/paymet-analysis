# Payment Analysis Platform - Technical Documentation

## Architecture Overview

This platform implements a modern **Lakehouse architecture** on Databricks, combining the reliability of data warehouses with the flexibility of data lakes. The solution uses **Databricks Asset Bundles (DABs)** for infrastructure-as-code deployment.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABRICKS WORKSPACE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Ingest    │───▶│   Bronze    │───▶│   Silver    │───▶│    Gold     │  │
│  │  (Stream)   │    │   (Raw)     │    │ (Enriched)  │    │  (Metrics)  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                                     │                   │         │
│         ▼                                     ▼                   ▼         │
│  ┌─────────────┐                      ┌─────────────┐    ┌─────────────┐   │
│  │  Simulator  │                      │  ML Models  │    │ Dashboards  │   │
│  │   (1K/s)    │                      │  (MLflow)   │    │ (Lakeview)  │   │
│  └─────────────┘                      └─────────────┘    └─────────────┘   │
│                                              │                              │
│                                              ▼                              │
│                                       ┌─────────────┐                       │
│                                       │  AI Agents  │                       │
│                                       │ (6 agents)  │                       │
│                                       └─────────────┘                       │
│                                              │                              │
│                                              ▼                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         APX Application                               │  │
│  │              FastAPI (Backend) + React (Frontend)                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
payment-analysis/
├── databricks.yml              # Main bundle configuration
├── resources/                  # Databricks resource definitions
│   ├── unity_catalog.yml       # Schema, volumes, metadata
│   ├── pipelines.yml           # DLT pipelines (batch & streaming)
│   ├── streaming_simulator.yml # Transaction generator jobs
│   ├── ai_gateway.yml          # AI agent jobs
│   ├── ml_jobs.yml             # ML training jobs
│   ├── sql_warehouse.yml       # SQL compute
│   ├── genie_spaces.yml        # Natural language interface
│   ├── dashboards.yml          # Lakeview dashboards
│   ├── dashboards/             # Dashboard JSON definitions
│   └── model_serving.yml       # ML endpoint configs (optional)
├── src/payment_analysis/
│   ├── streaming/              # Data ingestion & streaming
│   ├── transform/              # ETL transformations
│   ├── ml/                     # Machine learning
│   ├── agents/                 # AI agent framework
│   ├── genie/                  # Genie space config
│   ├── backend/                # FastAPI application
│   └── ui/                     # React frontend
├── pyproject.toml              # Python dependencies
├── package.json                # Node.js dependencies
└── vite.config.ts              # Frontend build config
```

---

## Resource Definitions

### Unity Catalog (`resources/unity_catalog.yml`)

**Purpose**: Defines the data schema and storage volumes with rich metadata for Genie.

| Resource | Description |
|----------|-------------|
| `payment_analysis_schema` | Main schema with Genie-optimized comments |
| `raw_data` volume | Landing zone for incoming files |
| `checkpoints` volume | Streaming checkpoint storage |
| `ml_artifacts` volume | Model artifacts and features |
| `reports` volume | Generated reports and exports |

**Best Practices**:
- Add detailed `comment` fields on schemas/tables for Genie discoverability
- Use `MANAGED` volumes for Databricks-managed lifecycle
- Apply data classification tags for PII columns

### Delta Live Tables (`resources/pipelines.yml`)

**Purpose**: Automated data pipelines with quality guarantees.

| Pipeline | Mode | Description |
|----------|------|-------------|
| `payment_analysis_etl` | Batch | Bronze → Silver → Gold transformations |
| `payment_realtime_pipeline` | Continuous | Real-time streaming with 1-second latency |

**Best Practices**:
- Use `continuous: true` only for real-time requirements (higher cost)
- Enable `photon: true` for performance optimization
- Set `development: true` during testing, `false` for production

### Streaming Jobs (`resources/streaming_simulator.yml`)

**Purpose**: Generate synthetic transaction data for testing.

| Job | Description |
|-----|-------------|
| `transaction_stream_simulator` | Generates 1000 events/second |
| `continuous_stream_processor` | Processes stream with Structured Streaming |

**Configuration**:
- `events_per_second`: Configurable load (default 1000)
- `duration_minutes`: Test duration
- `output_mode`: "delta" for Delta tables

### AI Agents (`resources/ai_gateway.yml`)

**Purpose**: Intelligent analysis and recommendations via LLM-powered agents.

| Agent | Schedule | Function |
|-------|----------|----------|
| Smart Routing | Every 6 hours | Optimize processor allocation |
| Smart Retry | Every 4 hours | Identify recovery opportunities |
| Decline Analyst | Daily 8 AM | Analyze decline patterns |
| Risk Assessor | Every 2 hours | Monitor fraud signals |
| Performance Recommender | Daily 6 AM | KPI analysis and suggestions |
| Orchestrator | Weekly Monday | Comprehensive multi-agent analysis |

**Best Practices**:
- Jobs deploy with `pause_status: PAUSED` - enable manually after validation
- Use single-node clusters for agent jobs (cost optimization)
- Store agent outputs in Delta tables for audit trail

### ML Jobs (`resources/ml_jobs.yml`)

**Purpose**: Train and deploy machine learning models.

| Job | Description |
|-----|-------------|
| `train_ml_models_job` | Train approval, risk, and routing models |
| `create_gold_views_job` | Generate business metric views |
| `test_agent_framework_job` | Validate agent functionality |

**Best Practices**:
- Use MLflow for experiment tracking and model registry
- Enable model serving auto-capture for inference logging
- Schedule retraining based on data drift detection

---

## Source Code

### Streaming (`src/payment_analysis/streaming/`)

| File | Purpose |
|------|---------|
| `bronze_ingest.py` | DLT notebook for raw data ingestion |
| `transaction_simulator.py` | Generates synthetic payment events |
| `continuous_processor.py` | Structured Streaming processor |
| `realtime_pipeline.py` | DLT streaming tables with windowed aggregations |

**Key Patterns**:
```python
# DLT streaming table with expectations
@dlt.table(name="payments_stream_silver")
@dlt.expect_or_drop("valid_amount", "amount > 0")
def payments_stream_silver():
    return dlt.readStream("payments_stream_bronze")
```

### Transform (`src/payment_analysis/transform/`)

| File | Purpose |
|------|---------|
| `silver_transform.py` | Enrichment and feature engineering |
| `gold_views.py` | Business metric aggregations |
| `gold_views.sql` | SQL-based view definitions |
| `unity_catalog_setup.sql` | Advanced UC configuration (PK/FK, tags, monitors) |

**Key Features**:
- Risk tier calculation: `low` (<0.3), `medium` (0.3-0.7), `high` (>0.7)
- Composite risk scoring combining fraud, AML, and device trust
- Data classification tags for PII compliance

### ML (`src/payment_analysis/ml/`)

| File | Purpose |
|------|---------|
| `train_models.py` | Train RandomForest models for approval/risk/routing |

**Models**:
1. **Approval Propensity**: Predicts transaction approval likelihood
2. **Risk Scoring**: Classifies transaction risk level
3. **Smart Routing**: Recommends optimal payment processor

### Agents (`src/payment_analysis/agents/`)

| File | Purpose |
|------|---------|
| `agent_framework.py` | Multi-agent system with tool definitions |

**Architecture**:
```python
class OrchestratorAgent(BaseAgent):
    """Coordinates all specialist agents."""
    
    def __init__(self, catalog, schema):
        self.smart_routing = SmartRoutingAgent(catalog, schema)
        self.smart_retry = SmartRetryAgent(catalog, schema)
        self.decline_analyst = DeclineAnalystAgent(catalog, schema)
        self.risk_assessor = RiskAssessorAgent(catalog, schema)
        self.performance_recommender = PerformanceRecommenderAgent(catalog, schema)
```

### Backend (`src/payment_analysis/backend/`)

| File | Purpose |
|------|---------|
| `app.py` | FastAPI application setup |
| `routes/analytics.py` | KPI and trend endpoints |
| `routes/decision.py` | Decisioning and ML prediction endpoints |
| `services/databricks_service.py` | Unity Catalog and Model Serving client |
| `decisioning/policies.py` | Business rules for auth/retry/routing |

**Key Endpoints**:
- `GET /api/kpis/databricks` - Fetch KPIs from Unity Catalog
- `POST /api/ml/approval` - Call approval model serving endpoint
- `POST /api/decision/routing` - Execute routing policy

### Frontend (`src/payment_analysis/ui/`)

Built with React + Vite + TanStack Router + shadcn/ui.

| Directory | Purpose |
|-----------|---------|
| `routes/` | Page components (dashboard, declines, etc.) |
| `components/ui/` | Reusable UI components |
| `lib/api.ts` | Auto-generated API client from OpenAPI |

---

## Deployment

### Prerequisites
- Databricks CLI configured with workspace access
- Python 3.11+ with `uv` package manager
- Node.js 18+ with `bun`

### Commands

```bash
# Validate bundle configuration
databricks bundle validate

# Deploy to development
databricks bundle deploy --target dev

# Deploy to specific folder
# Edit databricks.yml: workspace.root_path

# View deployed resources
databricks bundle summary
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_TOKEN` | PAT or OAuth token |
| `DATABRICKS_WAREHOUSE_ID` | SQL Warehouse ID |
| `DATABRICKS_CATALOG` | Unity Catalog name (default: main) |
| `DATABRICKS_SCHEMA` | Schema name |

---

## Best Practices & Recommendations

### Data Engineering
1. **Medallion Architecture**: Always use Bronze → Silver → Gold pattern
2. **Schema Evolution**: Enable `mergeSchema` for flexible ingestion
3. **Partitioning**: Partition large tables by date for query performance
4. **Z-Ordering**: Apply Z-ORDER on frequently filtered columns

### Streaming
1. **Checkpointing**: Always use Unity Catalog volumes for checkpoints
2. **Trigger Intervals**: Balance latency vs. cost (1s for real-time, 1min for near-real-time)
3. **Watermarking**: Use watermarks for late data handling in windowed aggregations

### Machine Learning
1. **Feature Store**: Consider Unity Catalog feature tables for consistency
2. **Model Registry**: Use MLflow for versioning and lineage
3. **A/B Testing**: Deploy champion/challenger models with traffic splitting
4. **Monitoring**: Enable inference tables for drift detection

### Security
1. **Unity Catalog**: Use for all data governance
2. **Row-Level Security**: Apply dynamic views for sensitive data
3. **Column Masking**: Mask PII columns based on user groups
4. **Audit Logging**: Enable system tables for compliance

### Cost Optimization
1. **Serverless**: Use serverless SQL warehouses when possible
2. **Auto-terminate**: Configure cluster auto-termination (10-30 min)
3. **Spot Instances**: Use spot workers for non-critical jobs
4. **Photon**: Enable for compute-intensive workloads

### Monitoring
1. **Lakehouse Monitors**: Set up data quality monitors on Silver tables
2. **Alerts**: Configure alerts for pipeline failures and SLA breaches
3. **Dashboards**: Create operational dashboards for system health

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Schema not found | Run ETL pipeline first to create tables |
| Model serving auth | Configure external model API tokens |
| App limit reached | Delete unused apps (workspace limit: 200) |
| Pipeline alerts invalid | Use only `on_update_failure`, `on_update_success` |
| Quartz cron format | Use 7-field format with `?` for day conflicts |

### Useful Commands

```bash
# Check pipeline status
databricks pipelines list

# View job runs
databricks jobs list

# Query warehouse
databricks sql execute --warehouse-id <id> "SELECT * FROM ..."

# Tail logs
databricks clusters logs <cluster-id>
```

---

## References

- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/)
- [Delta Live Tables](https://docs.databricks.com/delta-live-tables/)
- [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/)
- [MLflow on Databricks](https://docs.databricks.com/mlflow/)
- [APX Framework](https://github.com/databricks-solutions/apx)
