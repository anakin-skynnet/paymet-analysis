# Control Panel & UI – What You Get

This document confirms the **control panel** experience in the Payment Analysis UI: all data is **fetched from the Databricks backend** and is **interactive** for a better UX.

## 1. Setup & Run (Control Panel)

**Route:** **Setup & run** (sidebar → Operations).

- **Run jobs**  
  - Steps 1–6 (Create Data Repositories → Simulate events → Initialize ingestion → Deploy dashboards → Train models → Deploy agents).  
  - **Run** starts the job via backend `POST /api/setup/run-job` and opens the run in Databricks.  
  - **Open** opens the job/pipeline in the workspace (links use workspace URL from backend).

- **Pipelines**  
  - Start ETL and Real-Time pipelines via **Run** → `POST /api/setup/run-pipeline`; link opens the pipeline in the workspace.

- **Catalog & schema**  
  - Form is filled from `GET /api/setup/defaults` (backend uses Lakebase app_config / app_settings when available).  
  - **Save catalog & schema** → `PATCH /api/setup/config` persists to Lakebase/Lakehouse and updates app state.

- **Data & config (Lakebase / Lakehouse)**  
  - **App config & settings:** Table built from:
    - Effective catalog, schema, warehouse_id from `GET /api/setup/defaults`
    - Key-value app settings from `GET /api/setup/settings` (Lakebase `app_settings`: e.g. `default_events_per_second`, `default_duration_minutes`).
  - **Countries / entities:** Table from `GET /api/analytics/countries` (Lakehouse/Lakebase).
  - **Online features:** Table from `GET /api/analytics/online-features` (Lakebase first, then Lakehouse; ML/agent output).

All of this is **backend-driven** and **interactive** (run jobs, save config, view live tables).

## 2. Dashboards

**Route:** **Dashboards** (sidebar → Overview).

- **List:** `GET /api/dashboards/dashboards` (with optional category).
- **Embed URL:** `GET /api/dashboards/dashboards/{id}/url?embed=true` for in-app embed.
- **Interaction:** Click a dashboard to open it in the Databricks workspace, or use **View embedded** to show it in the UI. All from backend and workspace URLs.

## 3. Genie (Chat)

**Route:** **AI agents** (sidebar → AI & automation).

- **Ask Data with Genie:** Prominent card that opens **Genie in the Databricks workspace** (same-workspace URL).  
- Chat happens **inside Databricks** (Genie UI). The app provides the link; UX is “one click to chat with Genie.”

## 4. Agents & ML

- **AI agents**  
  - **Route:** **AI agents**.  
  - **List:** `GET /api/agents/agents` (entity/type filters).  
  - **Open agent:** `GET /api/agents/agents/{id}/url` → open in workspace.  
  - All data and links from the backend.

- **ML models**  
  - **Route:** **ML models**.  
  - **List:** `GET /api/analytics/models` (from Unity Catalog / backend).  
  - Links to MLflow, model registry, and notebooks from backend/workspace config.

- **Agents and ML endpoints**  
  - Model serving and agent endpoints are used by the backend (decisioning, recommendations). The UI shows **metadata and links** (agents list, models list) from the backend; actual inference is triggered by the app backend or by jobs.

## 5. Lakebase / Postgres Data in the UI

All of these are **fetched from the Databricks backend** (which reads Lakebase when configured, then Lakehouse as fallback where applicable):

| Data              | Backend source                    | Where in UI                          |
|-------------------|-----------------------------------|--------------------------------------|
| App config        | Lakebase app_config / Lakehouse   | Setup → Parameters + Data & config   |
| App settings      | Lakebase app_settings             | Setup → Data & config (key-value)    |
| Default values    | Same (warehouse_id, defaults)     | Setup → Parameters + defaults API    |
| Countries         | Lakehouse / UC                    | Setup → Data & config; country dropdowns |
| Online features   | Lakebase → Lakehouse              | Setup → Data & config (table)        |
| Approval rules    | Lakebase → Lakehouse              | Rules page (list/create/update/delete)  |

So you get a **single control panel** (Setup & run) where you can run jobs, check and interact with published dashboards (via list + embed/open), open Genie for chat, and see agents and ML info—plus **tables** for app config, app settings, countries, and online features, all **fetched from the backend** and **interactive**.

## Quick checklist

- [x] Control panel (Setup & run) to run jobs and pipelines  
- [x] Dashboards: list and interact (open in workspace or embedded) from backend  
- [x] Genie: one-click open to chat in Databricks  
- [x] Agents: list and open from backend  
- [x] ML models: list and links from backend  
- [x] Tables: countries, app settings, config, online features in Setup → Data & config, all from backend  
- [x] Rules: CRUD from backend (Lakebase or Lakehouse)  
- [x] All of this data is **fetched from the Databricks backend** and **interactive** in the UI  
