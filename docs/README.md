# Documentation

Single entry point for Payment Analysis docs. The platform’s **main purpose** is to **accelerate approval rates** via smart retry, smart checkout, risk analysis, fraud detection, reason codes, routing optimization, and AI-backed decisioning.

## Core docs

| Document | Purpose |
|----------|---------|
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Deploy steps, app config, env vars, troubleshooting, job inventory |
| [ARCHITECTURE_REFERENCE.md](ARCHITECTURE_REFERENCE.md) | Business use cases, architecture, data flow, data sources, UI↔backend wiring, bundle resources |
| [CONTROL_PANEL_UI.md](CONTROL_PANEL_UI.md) | What the control panel provides: run jobs, dashboards, Genie, agents, ML, Lakebase tables |
| [VERSION_ALIGNMENT.md](VERSION_ALIGNMENT.md) | Pinned dependency versions and Databricks App compatibility |

## Project structure (logical)

- **`src/payment_analysis/`** — App and bundle code  
  - **`backend/`** — FastAPI app, config, dependencies, routes (analytics, decision, dashboards, agents, rules, setup, experiments, incidents, notebooks), services (Databricks), Lakebase config  
  - **`ui/`** — React app: routes (dashboard, dashboards, decisioning, rules, smart-checkout, smart-retry, declines, reason-codes, models, ai-agents, setup, etc.), components, lib (API client)  
  - **`transform/`** — Lakehouse SQL and job notebooks: lakehouse_bootstrap.sql, gold_views.sql, run_* (ensure_catalog_schema, lakebase_data_init, lakehouse_bootstrap, gold_views), prepare_dashboards, publish_dashboards; DLT: silver_transform, gold_views (pipeline)  
  - **`streaming/`** — Bronze ingest, realtime pipeline, transaction simulator, continuous processor  
  - **`ml/`** — Model training (approval, risk, routing, retry)  
  - **`agents/`** — Agent framework (orchestrator, specialists)  
  - **`genie/`** — Genie space sync  
  - **`vector_search/`** — Vector search index creation  
- **`resources/`** — Bundle YAML: unity_catalog, lakebase, pipelines, sql_warehouse, ml_jobs, agents, streaming_simulator, genie_spaces, dashboards, fastapi_app  
- **`scripts/`** — bundle.sh (validate/deploy/verify), dashboards.py (prepare/validate-assets), run_and_validate_jobs.py, sync_requirements_from_lock.py  

All of the above support the use cases described in [ARCHITECTURE_REFERENCE.md](ARCHITECTURE_REFERENCE.md#business-purpose--use-cases).
