# Demo Setup — Run the Solution End-to-End

Follow these steps to run jobs and simulate the Payment Analysis solution end-to-end. Use the one-click links to open each job or pipeline in Databricks (log in if prompted).

**Base URL:** `https://adb-984752964297111.11.azuredatabricks.net`

---

## Recommended order

| Order | Step | Description |
|-------|------|-------------|
| 1 | [Data ingestion](#1-data-ingestion) | Generate test payment events |
| 2a | [Batch ETL](#2a-batch-etl-pipeline) | Process raw data into Silver/Gold tables |
| 2b | [Real-time pipeline](#2b-real-time-pipeline-optional) | *(Optional)* Continuous streaming |
| 3 | [Gold views](#3-create-gold-views) | Create analytical views for dashboards |
| 4 | [Train ML models](#4-train-ml-models) | Train approval, risk, routing, retry models |
| 5 | [AI orchestrator](#5-run-ai-orchestrator) | Coordinate all AI agents |
| 6 | [Stream processor](#6-continuous-stream-processor-optional) | *(Optional)* Always-on stream processing |

---

## Quick links (one-click)

| Step | Action | Link |
|------|--------|------|
| 1. Data ingestion | Run Transaction Simulator | [Run job](https://adb-984752964297111.11.azuredatabricks.net/#job/782493643247677/run) |
| 2a. Batch ETL | Open ETL Pipeline | [Open pipeline](https://adb-984752964297111.11.azuredatabricks.net/pipelines/eb4edb4a-0069-4208-9261-2151f4bf33d9) |
| 2b. Real-time pipeline | Open Real-Time Pipeline | [Open pipeline](https://adb-984752964297111.11.azuredatabricks.net/pipelines/0ef506fd-d386-4581-a609-57fb9a23291c) |
| 3. Gold views | Run Gold Views Job | [Run job](https://adb-984752964297111.11.azuredatabricks.net/#job/775632375108394/run) |
| 4. Train ML models | Run ML Training Job | [Run job](https://adb-984752964297111.11.azuredatabricks.net/#job/231255282351595/run) |
| 5. AI orchestrator | Run Orchestrator Job | [Run job](https://adb-984752964297111.11.azuredatabricks.net/#job/582671124403091/run) |
| 6. Stream processor | Run Continuous Stream Processor | [Run job](https://adb-984752964297111.11.azuredatabricks.net/#job/1124715161556931/run) |

**Note:** Job links with `/run` open the “Run now” flow. Pipeline links open the pipeline; use **Start** or **Run update** on that page.

---

## Steps in detail

### 1. Data ingestion

Generate synthetic payment transaction data (e.g. 1000 events/second).

- **One-click:** [Run Transaction Simulator](https://adb-984752964297111.11.azuredatabricks.net/#job/782493643247677/run)
- **CLI:** `databricks bundle run transaction_stream_simulator -t dev`

Let it run for a few minutes to populate the Bronze table.

---

### 2a. Batch ETL pipeline

Process raw data into Silver and Gold tables (Bronze → Silver → Gold).

- **One-click:** [Open ETL Pipeline](https://adb-984752964297111.11.azuredatabricks.net/pipelines/eb4edb4a-0069-4208-9261-2151f4bf33d9) → Start / Run update
- **CLI:** `databricks pipelines start-update eb4edb4a-0069-4208-9261-2151f4bf33d9`

Wait for the pipeline run to complete before creating gold views.

---

### 2b. Real-time pipeline (optional)

Run the continuous real-time payment stream.

- **One-click:** [Open Real-Time Pipeline](https://adb-984752964297111.11.azuredatabricks.net/pipelines/0ef506fd-d386-4581-a609-57fb9a23291c) → Start

---

### 3. Create gold views

Create 20+ analytical views used by dashboards and reporting.

- **One-click:** [Run Gold Views Job](https://adb-984752964297111.11.azuredatabricks.net/#job/775632375108394/run)
- **CLI:** `databricks bundle run create_gold_views_job -t dev`

---

### 4. Train ML models

Train the four ML models (approval propensity, risk scoring, smart routing, smart retry).

- **One-click:** [Run ML Training Job](https://adb-984752964297111.11.azuredatabricks.net/#job/231255282351595/run)
- **CLI:** `databricks bundle run train_ml_models_job -t dev`

---

### 5. Run AI orchestrator

Start the orchestrator so it coordinates all AI agents (routing, retry, risk, decline, performance).

- **One-click:** [Run Orchestrator Job](https://adb-984752964297111.11.azuredatabricks.net/#job/582671124403091/run)
- **CLI:** `databricks bundle run orchestrator_agent_job -t dev`

---

### 6. Continuous stream processor (optional)

Run the always-on stream processor.

- **One-click:** [Run Continuous Stream Processor](https://adb-984752964297111.11.azuredatabricks.net/#job/1124715161556931/run)
- **CLI:** `databricks bundle run continuous_stream_processor -t dev`

---

## Useful links

| Resource | Link |
|----------|------|
| SQL Warehouse | [Open warehouse](https://adb-984752964297111.11.azuredatabricks.net/sql/warehouses/bf12ee0011ea4ced) |
| Unity Catalog schema | [Explore data](https://adb-984752964297111.11.azuredatabricks.net/explore/data/main/dev_ariel_hdez_payment_analysis_dev) |

---

## Deploy before running

If resources are not yet deployed:

```bash
databricks bundle deploy -t dev
```

See [1_DEPLOYMENT_GUIDE.md](1_DEPLOYMENT_GUIDE.md) for full deployment and configuration details.
