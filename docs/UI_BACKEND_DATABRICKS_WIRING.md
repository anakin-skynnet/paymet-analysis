# UI ↔ Backend ↔ Lakebase & Databricks Wiring

This document describes how the **frontend** connects to **Lakebase** (Postgres) for CRUD, how **dashboards** are embedded and where they get data, and how **jobs/pipelines** are triggered from the UI. It aligns with the [Apps Cookbook](https://apps-cookbook.dev/docs/intro), [apx](https://github.com/databricks-solutions/apx), and [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit).

---

## 1. Architecture overview

- **UI (React/Vite)** never talks to Lakebase or Databricks directly. All calls go to the **FastAPI backend** at `/api/*`.
- **Backend** uses two data planes:
  - **Lakebase (Postgres)** — via `SessionDep` / `Runtime.get_session()` for experiments, incidents, decision logs, auth events.
  - **Databricks** — via `DatabricksService` (SQL Warehouse, Unity Catalog) and `WorkspaceClient` (jobs, pipelines, workspace URLs).

This matches the **Cookbook** pattern: FastAPI app with routes under `/api`; **apx** provides the full-stack layout (React + FastAPI) and OpenAPI client generation; **AI Dev Kit** provides skills/MCP for Databricks (jobs, dashboards, UC) used while building the app.

---

## 2. UI → Lakebase (CRUD operations)

**The UI does not connect to Lakebase.** It calls the backend; the backend uses a Postgres session bound to the **Databricks Lakebase** instance (when `PGAPPNAME` is set in the app).

### 2.1 Flow

1. **UI** uses the generated API client (e.g. `useListExperiments`, `useCreateIncident`, `createApprovalRule` mutations) or `fetch("/api/...")` to hit FastAPI.
2. **FastAPI** route depends on `SessionDep` (from `dependencies.get_session`).
3. **`get_session`** yields a **SQLModel `Session`** from `Runtime.get_session()`.
4. **`Runtime`** (see [backend/runtime.py](../src/payment_analysis/backend/runtime.py)):
   - **Production (Databricks App):** Connects to the **Lakebase** database instance by name (`PGAPPNAME`). Uses `WorkspaceClient.database.get_database_instance()` and `generate_database_credential()` so each connection uses a short-lived token (see [Apps Cookbook – Lakebase connection](https://apps-cookbook.dev/docs/fastapi/getting_started/lakebase_connection)).
   - **Local dev:** Uses `APX_DEV_DB_PORT` and a local Postgres (e.g. PGlite) when running `apx dev start`.
5. **Routes** that perform CRUD on Lakebase use `SessionDep` and SQLModel/db_models:
   - **Experiments:** `POST/GET /api/experiments`, `POST /api/experiments/:id/start|stop|assign`, `GET /api/experiments/:id/assignments` → [backend/routes/experiments.py](../src/payment_analysis/backend/routes/experiments.py).
   - **Incidents:** `GET/POST /api/incidents`, `POST /api/incidents/:id/resolve`, `GET/POST /api/incidents/:id/tasks` → [backend/routes/incidents.py](../src/payment_analysis/backend/routes/incidents.py).
   - **Decision logs / Auth events:** Written by decision routes; stored in app DB (Lakebase when configured) via `SessionDep`.

### 2.2 What lives in Lakebase vs Databricks

| Data | Storage | Backend dependency |
|------|---------|--------------------|
| Experiments, experiment assignments | **Lakebase** (Postgres) | `SessionDep` |
| Incidents, remediation tasks | **Lakebase** (Postgres) | `SessionDep` |
| Decision logs, authorization events | **Lakebase** (Postgres) | `SessionDep` |
| Approval rules | **Databricks** (Unity Catalog table) | `DatabricksService` |
| app_config (catalog/schema) | **Databricks** (Unity Catalog table) | `DatabricksService` |
| Analytics (KPIs, trends, reason codes, etc.) | **Databricks** (UC views, SQL Warehouse) | `DatabricksService` |

So: **CRUD for experiments/incidents/decision logs** = UI → FastAPI → Lakebase (Postgres). **Rules and analytics** = UI → FastAPI → Databricks (SQL Warehouse / UC).

---

## 3. Dashboards: embedding and data source

### 3.1 How dashboards are embedded

1. **Dashboard list**  
   UI calls `GET /api/dashboards` (and optionally `?category=...`). The backend returns a **static registry** of dashboard metadata (id, name, description, category, `url_path`). Registry IDs match the **Lakeview** dashboards deployed by the bundle (`resources/dashboards.yml`, `resources/dashboards/*.lvdash.json`). See [backend/routes/dashboards.py](../src/payment_analysis/backend/routes/dashboards.py).

2. **Embed URL**  
   When the user opens a dashboard in the app (e.g. `/dashboards?embed=executive_overview`), the UI calls:
   - `GET /api/dashboards/:dashboard_id/url?embed=true`
   The backend returns:
   - `embed_url`: workspace-relative path (e.g. `/sql/dashboards/executive_overview?o=workspace_id&embed=true`).
   - `full_embed_url`: absolute URL for the iframe (`workspace_host + embed_url`), when `DATABRICKS_HOST` (and optionally `DATABRICKS_WORKSPACE_ID`) is set.

3. **Iframe**  
   The UI ([dashboards.tsx](../src/payment_analysis/ui/routes/_sidebar/dashboards.tsx)) renders an **iframe** with `src={iframeSrc}` where `iframeSrc` is `full_embed_url` or `workspace_url + embed_url`. So the **dashboard runs inside the Databricks workspace** (Lakeview/DBSQL); the app only provides the frame and the URL.

4. **Workspace URL for links**  
   At app load, the UI calls `GET /api/config/workspace` and caches the result in [workspace.ts](../src/payment_analysis/ui/config/workspace.ts) via `WorkspaceUrlBootstrapper`. That way `getWorkspaceUrl()`, `getDashboardUrl(path)`, and `getGenieUrl()` resolve correctly for “Open in Databricks” links and the embed base URL.

### 3.2 Where dashboard data comes from

**Dashboard data is not fetched by the app.** The **Databricks Lakeview** dashboard runs in the iframe and executes its own **SQL against the SQL Warehouse** (Unity Catalog views/tables in the configured catalog/schema). So:

- **Data source for dashboard charts** = Databricks SQL Warehouse + Unity Catalog (same catalog/schema as in Setup & Run and as used by the backend for analytics).
- **Embedding** = Cookbook-style “embed in app” using workspace URL + embed query params; **apx** does not prescribe a specific embed mechanism — this app uses the standard Lakeview embed URL pattern.

---

## 4. Jobs and pipelines: triggered from the UI

### 4.1 Flow

1. **Setup & Run** page ([setup.tsx](../src/payment_analysis/ui/routes/_sidebar/setup.tsx)) shows steps (Lakehouse Bootstrap, Gold Views, Simulator, ETL, ML, Genie, Agents, Publish dashboards, etc.) and an **Execute** button per step.
2. **Execute** opens the job or pipeline in the Databricks workspace in a new tab (job run page `/#job/{id}/run` or pipeline page `/pipelines/{id}`), ready to run there. No backend run call from the UI.
3. **Default job/pipeline IDs** come from `GET /api/setup/defaults`. The backend resolves IDs from the workspace when credentials are available and merges with bundle defaults. See [backend/routes/setup.py](../src/payment_analysis/backend/routes/setup.py).
4. **Optional API:** `POST /api/setup/run-job` and `POST /api/setup/run-pipeline` remain available for programmatic use; the UI does not call them.

### 4.2 Execute and quick links (Setup page)

On the **Setup & Run** page, each step has an **Execute** button that opens the Databricks workspace in a new tab:

| Target | URL pattern | Where it goes |
|--------|-------------|----------------|
| **Job** | `${workspace_host}/#job/${job_id}/run` | **Job run** page: run now or view runs (not the job definition/edit page). |
| **Pipeline** | `${workspace_host}/pipelines/${pipeline_id}` | **Pipeline** detail page: view or start updates. |
| **SQL Warehouse** | `${workspace_host}/sql/warehouses/${warehouse_id}` | SQL Warehouse page. |
| **Data explorer** | `${workspace_host}/explore/data/${catalog}/${schema}` | Unity Catalog data explorer. |
| **Genie** | `${workspace_host}/genie` | Genie. |
| **Jobs list** | `${workspace_host}/#job` | Jobs list. |
| **Pipelines list** | `${workspace_host}/pipelines` | Pipelines list. |

- **Job IDs** and **pipeline IDs** come from `defaults.jobs` / `defaults.pipelines` returned by `GET /api/setup/defaults`.
- **workspace_host** is `defaults.workspace_host` or the cached value from `GET /api/config/workspace`.
- Execute and quick-link buttons are disabled when the corresponding ID or host is missing. Links use `noopener,noreferrer`.

---

## 5. Reference alignment

| Topic | Apps Cookbook | apx | AI Dev Kit |
|-------|----------------|-----|------------|
| **API prefix** | Routes under `/api` for OAuth/token | Same; OpenAPI at `/api/openapi.json`, client generated from it | N/A (skills/MCP for building) |
| **Lakebase** | [Lakebase connection](https://apps-cookbook.dev/docs/fastapi/getting_started/lakebase_connection) recipe: Postgres via instance name + credential | App can use Lakebase; runtime uses `PGAPPNAME` and Databricks credential | N/A |
| **Dashboards** | — | — | Skills for AI/BI dashboards; this app embeds Lakeview via iframe + workspace URL |
| **Jobs / Pipelines** | — | — | MCP tools and skills for jobs/pipelines; this app uses SDK `jobs.run_now` and `pipelines.start_update` |
| **Frontend** | — | React + Vite + FastAPI, OpenAPI client, `src/.../ui` and `backend` | N/A |

---

## 6. Summary diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  UI (React, Vite, TanStack Router)                                      │
│  - Calls only /api/* (relative to app origin)                            │
│  - WorkspaceUrlBootstrapper: GET /api/config/workspace → cache base URL  │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FastAPI backend (/api)                                                  │
│  - SessionDep → Runtime.get_session() → Lakebase (Postgres)              │
│    → Experiments, Incidents, DecisionLog, AuthorizationEvent (CRUD)     │
│  - DatabricksService (SQL Warehouse, UC)                                 │
│    → Rules, app_config, analytics (KPIs, trends, reason codes, etc.)     │
│  - WorkspaceClient (OBO or DATABRICKS_TOKEN)                              │
│    → setup/defaults (resolve IDs), optional run-job/run-pipeline API,    │
│      dashboard URL, notebooks, agents                                    │
└─────────────────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                     ▼
┌───────────────┐     ┌──────────────────────────────────────────────────┐
│  Lakebase     │     │  Databricks                                        │
│  (Postgres)   │     │  - SQL Warehouse (UC views, app_config, rules)    │
│  PGAPPNAME    │     │  - Jobs (run_now), Pipelines (start_update)        │
│  Experiments  │     │  - Lakeview dashboards (embed URL for iframe)     │
│  Incidents    │     │  - Genie, MLflow, notebooks (URLs from backend)   │
│  DecisionLog  │     └──────────────────────────────────────────────────┘
└───────────────┘
```

For more detail on which API endpoints map to which data sources, see [DATA_SOURCES.md](DATA_SOURCES.md).
