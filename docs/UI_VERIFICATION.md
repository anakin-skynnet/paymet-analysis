# UI Verification Checklist

This document maps requested features to the current UI and backend so you can verify that all previous prompts are included.

---

## 1. Step-by-step guide with one-click Run and Open tab

**Location:** **Setup & Run** (`/setup`)

| Requirement | Implementation |
|-------------|----------------|
| Events produced simulator | **Step 1: Data ingestion (transaction simulator)** — "Run simulator" triggers the job; card/button "Open job (run)" opens Databricks job run in a new tab. Description mentions "Events simulator". |
| Ingestion Lakeflow pipeline | **Step 2: Ingestion & ETL (Lakeflow pipeline)** — "Start ETL pipeline" starts the pipeline; "Open pipeline" opens the pipeline in a new tab. |
| Jobs and pipelines | **Quick links** at bottom: "Jobs", "Pipelines" open Databricks Jobs and Pipelines in a new tab. Steps 1, 3, 4, 5 open specific job runs; Step 6 and Quick links open pipelines. |
| Model trainings | **Step 4: Train ML models** — "Run ML training" triggers the training job; "Open job (run)" opens the run in a new tab. |
| Other required operations | **Step 3** (Create gold views), **Step 5** (Run AI orchestrator), **Step 6** (Real-time streaming pipeline). **Quick links:** SQL Warehouse, Explore schema, Genie (Ask Data), Stream processor (run). |

**Connectivity:**  
- `GET /api/setup/defaults` returns job/pipeline IDs and workspace host (no Databricks call).  
- `POST /api/setup/run-job` and `POST /api/setup/run-pipeline` use Databricks WorkspaceClient (require `X-Forwarded-Access-Token` in app context).  

---

## 2. All dashboards

**Location:** **Analytics Dashboards** (`/dashboards`)

| Requirement | Dashboard (backend ID) | Name in UI |
|-------------|------------------------|------------|
| Stream ingested dashboard | `realtime_monitoring` | Real-Time Payment Monitoring |
| Data quality dashboard | `streaming_data_quality` | Streaming & Data Quality |
| Analytics dashboards | Multiple | Executive Overview, Decline Analysis, Daily Trends, Fraud & Risk Analysis, Merchant Performance, 3DS Authentication & Security, Financial Impact, Smart Routing & Optimization, Performance & Latency |

**Full list (11 dashboards):**  
Executive Overview, Decline Analysis & Recovery, Real-Time Payment Monitoring, Fraud & Risk Analysis, Merchant Performance & Segmentation, Smart Routing & Optimization, Daily Trends & Historical Analysis, 3DS Authentication & Security, Financial Impact & ROI Analysis, Technical Performance & Latency, **Streaming & Data Quality**.

**Connectivity and data access:**  
- Dashboard **metadata** (list, names, categories, URL paths) comes from backend `GET /api/dashboards` (static registry).  
- **Data** is loaded in Databricks when the user clicks a card and opens the dashboard URL in a new tab (`getWorkspaceUrl()` + `url_path`).  
- Error state: "Failed to load dashboards. Check that the backend is running and can reach Databricks for dashboard metadata and data access."  
- Page copy states that opening a card opens the dashboard in a new tab for connectivity and data access verification.

---

## 3. Ask Data section with Genie integration

**Location:** **AI Agents** (`/ai-agents`)

| Requirement | Implementation |
|-------------|----------------|
| Samples of prompts | **Ask Data with Genie** card lists sample prompts, e.g. "What was our approval rate by card network last week?", "Show me top decline reasons and recovery potential.", "Compare 3DS vs non-3DS approval rates by merchant segment." |
| Chat to interact with Genie | **"Open Genie to chat"** button (and card click) opens Genie in the Databricks workspace in a new tab. Chat happens inside Genie in Databricks. |
| Connectivity and data access | Copy: "Data is fetched from your Databricks workspace when you use Genie. Ensure backend and Databricks (catalog, schema, warehouse) are configured for connectivity and data access." |

**Note:** There is no in-app chat widget; the app links to Genie in Databricks for conversation.

---

## 4. ML Model section

**Location:** **ML Models** (`/models`)

| Requirement | Implementation |
|-------------|----------------|
| Approval propensity | Card with name, description, model type, features, Unity Catalog path; metrics when returned by backend. Click opens Model Registry in Databricks. |
| Risk scoring model | Same as above. |
| Smart routing | Same as above. |
| Smart retry | Same as above. |
| Combined business impact | Dedicated card with links to Financial Impact and Smart Routing dashboards in Databricks. |
| Other models | All models returned by `GET /api/analytics/models` are rendered (backend uses Databricks config for catalog/schema and returns approval_propensity, risk_scoring, smart_routing, smart_retry). |
| Real values and results from Databricks | Model list, catalog paths, and (when implemented) metrics are fetched from the backend; backend uses `DatabricksService.get_ml_models()` with config catalog/schema. Info card: "Configure DATABRICKS_* for connectivity and data access." |
| Connectivity and data access | Error state shows on failed load. Info card explains backend + Databricks config; links to MLflow, Model Registry, and Decisioning for live predictions. |

**Backend:** `GET /api/analytics/models` → `DatabricksService.get_ml_models()` (catalog path from config; metrics can be extended from a UC view or MLflow).

---

## 5. Other UI areas (from previous prompts)

- **Dashboard (home)** — KPIs, approval trends, solution performance, ML & decision reasoning; cards open Executive/Daily Trends/Routing dashboards or Genie.  
- **Decisioning** — Context form and Authentication/Retry/Routing result cards; cards open Agent Framework notebook in Databricks.  
- **Notebooks** — List from API; each notebook card and category cards open notebook or workspace in a new tab.  
- **Declines / Reason codes / Smart checkout / Smart retry** — Cards open relevant dashboards (e.g. decline_analysis, routing_optimization, authentication_security) in a new tab.  
- **Profile** — User info (no Databricks process to open).  
- **Experiments / Incidents** — App-level data; no direct workspace process links required.

---

## Quick verification commands

- **Backend:** Ensure `GET /api/setup/defaults`, `GET /api/dashboards`, `GET /api/analytics/models`, `GET /api/agents/agents` return data.  
- **Frontend:** Set `VITE_DATABRICKS_HOST` (or rely on backend-provided workspace URL) so "Open in new tab" links point to your workspace.  
- **Databricks:** Configure `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, catalog/schema (and token in app context for Run job/pipeline) for full connectivity and data access.
