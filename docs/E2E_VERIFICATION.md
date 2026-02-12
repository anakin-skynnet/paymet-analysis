# End-to-End Verification — Payment Analysis App

This document is a checklist to verify that the UI is properly designed and connected to the backend, data is fetched from Databricks (SQL warehouse, Lakebase, dashboards), and all resources and permissions are in place so **as a user you can navigate the app and fetch data from the different artifacts**.

---

## 1. UI design and backend connectivity

### 1.1 Data flow (backend-first, Pydantic-shaped fallback)

| Area | Backend source | UI hook | Fallback when backend unavailable |
|------|----------------|--------|-----------------------------------|
| **Dashboards list** | `GET /api/dashboards` | `useListDashboards` | `MOCK_DASHBOARDS` (types from OpenAPI) |
| **KPIs, trends, quality** | `GET /api/analytics/*` (Databricks SQL or mock) | `useGetKpisSuspense`, `useGetDataQualitySummary`, etc. | Backend returns mock from `DatabricksService._get_mock_data_for_query` (Pydantic models) |
| **Agents** | `GET /api/agents/*` | `useListAgents`, `useGetAgentUrl` | Error state + message |
| **Rules, decisioning, recommendations** | Lakebase + Databricks | `useGetRecommendations`, rules APIs | Backend mock or empty |
| **Setup, workspace config** | Lakebase `app_config` + Databricks | `useGetSetupDefaultsSuspense`, `useGetWorkspaceConfigSuspense` | Config from env/defaults |

- **Command Center** shows a **data source** indicator in the footer: **"Data: Databricks"** when `GET /api/v1/health/databricks` returns `analytics_source === "Unity Catalog"`, otherwise **"Data: Sample (mock)"**.
- **Error handling:** Root `ErrorBoundary` in `__root.tsx` catches render errors; pages that use `useListDashboards` / `useGetModels` etc. handle `isError` and show alerts or mock data where applicable.

### 1.2 Style and components

- **Design system:** `src/payment_analysis/ui/styles/globals.css` — Getnet primary (red), neon cyan, vibrant green; CSS variables for card, sidebar, chart colors.
- **Components:** shadcn/ui in `src/payment_analysis/ui/components/ui/` (Button, Card, Skeleton, Tabs, Table, Alert, Select, etc.); consistent use across Command Center, Dashboards, Smart Retry, Reason Codes, Decisioning, Setup, AI Agents.
- **Landing:** Value props and initiative cards (Smart Checkout, Reason Codes, Smart Retry) link to the correct routes; **Executive overview** and **Ingestion & volume** link to **Command Center** (`/command-center`).

---

## 2. Data from Databricks (database, SQL warehouse, dashboards)

### 2.1 Backend API and Databricks

- **Analytics** (`/api/analytics/*`): Uses `DatabricksService` to run SQL via **SQL Warehouse** against Unity Catalog views (e.g. `v_executive_kpis`, `v_approval_trends_by_second`, `v_active_alerts`, `v_data_quality_summary`, `v_top_decline_reasons`, `v_retry_performance`, etc.). When Databricks is unavailable, the same endpoints return **mock data** shaped as the same Pydantic models.
- **Health:** `GET /api/v1/health/databricks` returns:
  - `databricks_available`: true when host + token + warehouse are configured and reachable.
  - `analytics_source`: `"Unity Catalog"` or `"fallback"`.
  - `ml_inference_source`: `"Model Serving"` or `"mock"`.
- **Dashboards:** `GET /api/dashboards` returns the list of unified dashboards (Data & Quality, ML & Optimization, Executive & Trends); `GET /api/dashboards/{id}/url` returns the workspace or Lakeview URL for embedding.
- **Lakebase:** Rules, app_config, approval_rules, online_features, and decisioning data are read from **Lakebase** (Postgres) when configured; see `GET /api/v1/health/database` for connection status.

### 2.2 Configuration, scopes, permissions (for presenting data in the UI)

- **App environment (Compute → Apps → payment-analysis → Edit → Environment):**
  - **LAKEBASE_PROJECT_ID**, **LAKEBASE_BRANCH_ID**, **LAKEBASE_ENDPOINT_ID** — required for Lakebase.
  - **DATABRICKS_WAREHOUSE_ID** — required for SQL/analytics (or use sql-warehouse binding).
  - **DATABRICKS_HOST** — optional when opened from Compute → Apps (URL derived from request).
  - **DATABRICKS_TOKEN** — optional when using user authorization (OBO); open app from Compute → Apps so token is forwarded.
- **User authorization (OBO):** Bundle sets **user_api_scopes**: `sql` (in `resources/fastapi_app.yml`). Ensures the app can run SQL on behalf of the user when opened from Compute → Apps.
- **App resources (bundle):** sql-warehouse (CAN_USE), jobs 1–7 (CAN_MANAGE_RUN). Permissions for these resources are applied on deploy.

---

## 3. Getnet initiatives and approval-rate focus

The UI is structured so the Getnet team can analyze and optimize **approval rates** with a single, minimalist entry point:

- **Command Center (Overview):** Gross Approval Rate, False Decline Rate, Data Quality Health; Entry Systems Throughput; Top 5 Decline Reasons; 3DS Funnel; Smart Retry (recurrence vs manual); links to Executive Dashboard, All dashboards, Genie, Orchestrator chat.
- **Initiatives (pages):**
  - **Smart Checkout** — service path performance, path recommendations (from Databricks or mock).
  - **Reason Codes** — unified decline intelligence, entry system distribution, false insights (reason code translation).
  - **Smart Retry** — retry performance, recovery, success rate (impact of smart retry).
- **Decisioning** — recommendations and next steps (Lakehouse / Vector Search or mock).
- **Dashboards** — three unified BI dashboards: **Data & Quality**, **ML & Optimization**, **Executive & Trends** (stream ingestion, data quality, countries, risks, predictions, behavior, smart retry impact, smart checkout, routing, decline, fraud, KPIs, trends, merchant performance).
- **AI Agents** — Orchestrator and specialists (Smart Routing, Retry, Decline Analyst, Risk, Performance); Genie “Ask Data” link.
- **ML impact:** When Databricks is available, analytics and model-serving-based decisioning use **Unity Catalog** and **Model Serving**; the footer on Command Center shows “Data: Databricks”. When not available, the same UI shows mock/sample data so the flow is always usable.

---

## 4. Resources deployed and ready to use

| Resource | Where | Purpose | Permissions / notes |
|----------|--------|--------|---------------------|
| **Lakebase** | Job 1 (Create Data Repositories) | Postgres: app_config, approval_rules, online_features, app_settings | App connects via LAKEBASE_* env vars; Job 1 creates project/branch/endpoint. |
| **SQL Warehouse** | `resources/sql_warehouse.yml` | Queries for analytics, dashboards, gold views | App binding: CAN_USE; DATABRICKS_WAREHOUSE_ID in app env or from binding. |
| **Unity Catalog** | `resources/unity_catalog.yml` | Schema, volumes (raw_data, checkpoints, ml_artifacts, reports) | Schema `payment_analysis`; grants for users. |
| **Dashboards** | `resources/dashboards.yml` | 3 unified Lakeview dashboards | Deployed under workspace root_path/dashboards; publish step sets embed credentials. |
| **Vector Search** | Job 1 task / manual from `resources/vector_search.yml` | Similar-transaction lookup for recommendations | Created by Job 1 or manually; used by decisioning when available. |
| **Agents** | `resources/agents.yml` (job 6) | Agent framework (orchestrator + specialists) | Run via Job 6; UI shows agents and chat. |
| **Genie** | Optional; `resources/genie_spaces.yml` | Ask Data (NL analytics) | Bind genie-space in app when genie_space_id is set. |
| **Jobs 1–7** | `resources/ml_jobs.yml`, etc. | Setup & Run: repos, simulator, ingestion, dashboards, ML, agents, Genie | App bindings: CAN_MANAGE_RUN for each job. |

### 4.1 As a user: navigate and fetch data

- **Open the app** from **Compute → Apps → payment-analysis** (recommended so your token is forwarded).
- **Landing:** Click **Open Command Center** or **Executive overview** → Command Center with KPIs, charts, and “Data: Databricks” or “Data: Sample (mock)” in the footer.
- **Dashboards:** **All dashboards** → list of 3 unified dashboards; open in Databricks or embed; data comes from SQL warehouse + Unity Catalog when connected.
- **Smart Retry / Smart Checkout / Reason Codes:** Navigate from sidebar or landing initiative cards; data from `GET /api/analytics/*` (Databricks or mock).
- **Decisioning:** Recommendations from Lakehouse/Vector Search or mock.
- **Setup:** Run jobs 1–7 and pipelines; ensure catalog/schema and Lakebase IDs match app env.
- **AI Agents:** List agents, open Orchestrator chat; Genie link for Ask Data.

If you see **“Data: Sample (mock)”** on Command Center, check:

1. App env: **DATABRICKS_WAREHOUSE_ID**, and **DATABRICKS_HOST** (or open from Apps so host is derived).
2. **User auth:** Open from Compute → Apps; scope `sql` is configured in the app.
3. **GET /api/v1/health/databricks** in browser or Logs to confirm `databricks_available` and `analytics_source`.

---

## 5. Validation commands

- **TypeScript + Python:** `uv run apx dev check`
- **Bundle (prepare + validate):** `./scripts/bundle.sh validate dev`
- **Full verify (build, backend smoke, dashboards, bundle):** `./scripts/bundle.sh verify dev`
- **Deploy (overwrite dashboards, deploy, publish):** `./scripts/bundle.sh deploy dev`

After deploy, run **Job 1** (Create Data Repositories) if not already done, then **Job 3** (Initialize Ingestion) after the ETL pipeline has created silver tables, so dashboards and analytics have data.
