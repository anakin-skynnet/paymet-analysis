# Technical Documentation

## Architecture Overview

This platform implements a **Lakehouse architecture** on Databricks, combining data warehouse reliability with data lake flexibility. Infrastructure is managed via **Databricks Asset Bundles (DABs)** for reproducible deployments.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABRICKS WORKSPACE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   DATA LAYER                      INTELLIGENCE LAYER         APPLICATION    │
│  ┌───────────┐                   ┌───────────────┐          ┌───────────┐  │
│  │  Bronze   │──────────────────▶│   ML Models   │─────────▶│   API     │  │
│  │  (Raw)    │                   │   (MLflow)    │          │ (FastAPI) │  │
│  └─────┬─────┘                   └───────┬───────┘          └─────┬─────┘  │
│        │                                 │                        │         │
│        ▼                                 ▼                        ▼         │
│  ┌───────────┐                   ┌───────────────┐          ┌───────────┐  │
│  │  Silver   │──────────────────▶│  AI Agents    │─────────▶│    UI     │  │
│  │(Enriched) │                   │  (6 agents)   │          │  (React)  │  │
│  └─────┬─────┘                   └───────────────┘          └───────────┘  │
│        │                                                          │         │
│        ▼                                                          ▼         │
│  ┌───────────┐                                              ┌───────────┐  │
│  │   Gold    │─────────────────────────────────────────────▶│Dashboards │  │
│  │ (Metrics) │                                              │  & Genie  │  │
│  └───────────┘                                              └───────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
payment-analysis/
├── databricks.yml                 # Main bundle configuration
├── resources/                     # Databricks resource definitions (YAML)
│   ├── unity_catalog.yml          # Schema, volumes, metadata
│   ├── pipelines.yml              # DLT pipelines (batch & streaming)
│   ├── streaming_simulator.yml    # Transaction generator
│   ├── ai_gateway.yml             # AI agent jobs
│   ├── ml_jobs.yml                # ML training jobs
│   ├── sql_warehouse.yml          # SQL compute
│   ├── genie_spaces.yml           # Natural language interface
│   ├── dashboards.yml             # Lakeview dashboards
│   └── model_serving.yml          # ML endpoints (optional)
├── src/payment_analysis/
│   ├── streaming/                 # Data ingestion notebooks
│   ├── transform/                 # ETL transformations
│   ├── ml/                        # Machine learning code
│   ├── agents/                    # AI agent framework
│   ├── genie/                     # Genie configuration
│   ├── backend/                   # FastAPI application
│   └── ui/                        # React frontend
├── pyproject.toml                 # Python dependencies
├── package.json                   # Node.js dependencies
└── vite.config.ts                 # Frontend build
```

---

## Resource Definitions

### Unity Catalog (`unity_catalog.yml`)

| Resource | Purpose |
|----------|---------|
| `payment_analysis_schema` | Main schema with Genie-optimized metadata |
| `raw_data` volume | Landing zone for incoming files |
| `checkpoints` volume | Streaming checkpoint storage |
| `ml_artifacts` volume | Model artifacts and features |
| `reports` volume | Generated reports and exports |

### Delta Live Tables (`pipelines.yml`)

| Pipeline | Mode | Purpose |
|----------|------|---------|
| `payment_analysis_etl` | Batch (serverless) | Bronze → Silver → Gold transformations |
| `payment_realtime_pipeline` | Continuous | Real-time streaming with 1s latency |

### AI Agent Jobs (`ai_gateway.yml`)

| Agent | Schedule | Function |
|-------|----------|----------|
| Smart Routing | Every 6 hours | Optimize processor allocation |
| Smart Retry | Every 4 hours | Identify recovery opportunities |
| Decline Analyst | Daily 8 AM | Analyze decline patterns |
| Risk Assessor | Every 2 hours | Monitor fraud signals |
| Performance Recommender | Daily 6 AM | KPI analysis |
| Orchestrator | Weekly | Comprehensive multi-agent analysis |

### ML Jobs (`ml_jobs.yml`)

| Job | Purpose |
|-----|---------|
| `train_ml_models_job` | Train approval, risk, and routing models |
| `create_gold_views_job` | Generate business metric views |
| `test_agent_framework_job` | Validate agent functionality |

---

## Source Code Overview

### Streaming (`src/payment_analysis/streaming/`)

| File | Purpose |
|------|---------|
| `bronze_ingest.py` | DLT notebook for raw data ingestion |
| `transaction_simulator.py` | Generates 1000 synthetic events/second |
| `continuous_processor.py` | Structured Streaming processor |
| `realtime_pipeline.py` | DLT streaming tables with windowed aggregations |

### Transform (`src/payment_analysis/transform/`)

| File | Purpose |
|------|---------|
| `silver_transform.py` | Data enrichment and feature engineering |
| `gold_views.py` | Business metric aggregations |
| `gold_views.sql` | SQL view definitions |
| `unity_catalog_setup.sql` | PK/FK constraints, tags, monitors |

### ML (`src/payment_analysis/ml/`)

| File | Purpose |
|------|---------|
| `train_models.py` | Train RandomForest models for approval/risk/routing |

### Agents (`src/payment_analysis/agents/`)

| File | Purpose |
|------|---------|
| `agent_framework.py` | Multi-agent system with LLM integration |

### Backend (`src/payment_analysis/backend/`)

| File | Purpose |
|------|---------|
| `app.py` | FastAPI application setup |
| `routes/analytics.py` | KPI and trend endpoints |
| `routes/decision.py` | Decisioning and ML endpoints |
| `services/databricks_service.py` | Unity Catalog and Model Serving client |

### Frontend (`src/payment_analysis/ui/`)

| Directory | Purpose |
|-----------|---------|
| `routes/` | Page components (TanStack Router) |
| `components/ui/` | Reusable shadcn/ui components |
| `lib/api.ts` | Auto-generated OpenAPI client |

---

## Deployment

### Commands

```bash
# Validate configuration
databricks bundle validate

# Deploy to development
databricks bundle deploy --target dev

# Deploy to production
databricks bundle deploy --target prod

# View deployed resources
databricks bundle summary
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_TOKEN` | Authentication token |
| `DATABRICKS_WAREHOUSE_ID` | SQL Warehouse ID |
| `DATABRICKS_CATALOG` | Unity Catalog name |
| `DATABRICKS_SCHEMA` | Schema name |

---

## Best Practices

### Data Engineering
- **Medallion Architecture**: Bronze (raw) → Silver (enriched) → Gold (aggregated)
- **Schema Evolution**: Enable `mergeSchema` for flexible ingestion
- **Partitioning**: Partition by date for query performance
- **Z-Ordering**: Apply on frequently filtered columns

### Streaming
- **Checkpointing**: Use Unity Catalog volumes for durability
- **Trigger Intervals**: 1s for real-time, 1min for near-real-time
- **Watermarking**: Handle late-arriving data in windowed aggregations

### Machine Learning
- **MLflow**: Track all experiments and register models
- **Feature Store**: Use Unity Catalog feature tables
- **A/B Testing**: Champion/challenger with traffic splitting
- **Monitoring**: Enable inference tables for drift detection

### Security
- **Unity Catalog**: Centralized governance for all data
- **Row-Level Security**: Dynamic views for sensitive data
- **Column Masking**: Mask PII based on user groups
- **Audit Logging**: System tables for compliance

### Cost Optimization
- **Serverless DLT**: Auto-scaling, pay-per-use
- **Auto-terminate**: Clusters stop after 10-30 min idle
- **Spot Instances**: Use for non-critical batch jobs
- **Photon**: Enable for compute-intensive workloads

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Schema not found | Run ETL pipeline first to create tables |
| Model serving auth | Configure external model API tokens |
| App limit reached | Delete unused apps (workspace limit: 200) |
| Pipeline alerts invalid | Use `on_update_failure` or `on_update_success` |
| Quartz cron format | Use 7-field format with `?` for day conflicts |

---

## References

- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/)
- [Delta Live Tables](https://docs.databricks.com/delta-live-tables/)
- [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/)
- [MLflow on Databricks](https://docs.databricks.com/mlflow/)
- [APX Framework](https://github.com/databricks-solutions/apx)
