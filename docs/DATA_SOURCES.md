# Data and visualization sources

This document confirms where the app gets its **data** and **visualizations** from. When the Databricks Lakehouse is configured and available, **analytics and reporting data** are fetched from **Databricks** (Unity Catalog views, SQL Warehouse). **Embedded dashboards** are always Databricks SQL (DBSQL) dashboards.

---

## How the app connects to Databricks (logged-in user credentials)

The app connects to Databricks resources (SQL Warehouse, Unity Catalog, jobs, pipelines, dashboards) using **the credentials of the person currently logged in**:

- **When opened from Databricks:** Open the app from **Compute → Apps** in the workspace. The Databricks platform forwards the **logged-in user’s token** to the app in the `X-Forwarded-Access-Token` header on every API request. The backend uses this token for all Databricks API calls (queries, jobs, rules, recommendations, etc.), so no `DATABRICKS_TOKEN` environment variable is required.
- **When no forwarded token:** If the request does not include `X-Forwarded-Access-Token` (e.g. app opened outside the workspace or OBO disabled), the app falls back to `DATABRICKS_TOKEN` from the app environment, if set.

Catalog and schema (Unity Catalog) are taken from the `app_config` table in the Lakehouse when available: loaded at startup if a token exists in the environment, or **lazy-loaded on the first request** that has a forwarded token, so the logged-in user’s choice in **Setup & Run** is applied without requiring a service token at startup.

---

## Summary

| Area | Source | Notes |
|------|--------|--------|
| **KPIs** (Dashboard) | Databricks → fallback local DB | `GET /api/analytics/kpis` prefers Unity Catalog `v_executive_kpis` when Databricks is available |
| **Approval trends** | Databricks | `v_approval_trends_hourly` |
| **Solution performance** | Databricks | Unity Catalog views |
| **Reason codes & insights** | Databricks | Brazil reason-code views |
| **Factors delaying approval** | Databricks | Same reason-code insights |
| **Decline summary** | Databricks → fallback local DB | `GET /api/analytics/declines/summary` prefers `v_top_decline_reasons` when available |
| **Smart Checkout (paths, 3DS funnel)** | Databricks | Brazil payment-link views |
| **Smart Retry performance** | Databricks | Retry views |
| **Recommendations** | Databricks | Lakehouse / Vector Search |
| **Online features** | Databricks | Lakehouse |
| **ML models list** | Databricks | Unity Catalog / Model Registry |
| **Rules** | Databricks | Lakehouse tables (CRUD) |
| **Dashboards (embedded)** | Databricks | DBSQL dashboards; iframe to workspace |
| **Recent decisions** | App DB | Written by decisioning playground; operational only |
| **Experiments / Incidents** | App DB | Operational data (create/list/update) |
| **Auth status / config** | App / Databricks | Config and identity |

---

## Analytics and reporting (Databricks)

When the backend has a valid Databricks configuration (host, token, warehouse, catalog/schema), the following are **fetched from Databricks**:

- **KPI overview (Dashboard):** `GET /api/analytics/kpis` → Unity Catalog view `v_executive_kpis` (with fallback to local DB if Databricks is unavailable or errors).
- **Approval trends:** `GET /api/analytics/trends` → `v_approval_trends_hourly`.
- **Solution performance:** `GET /api/analytics/solutions` → solution performance view.
- **Reason codes (Brazil):** `GET /api/analytics/reason-codes/br`, `.../reason-codes/br/insights`, `.../reason-codes/br/entry-systems`, `.../factors-delaying-approval` → Unity Catalog reason-code views.
- **Decline summary:** `GET /api/analytics/declines/summary` → `v_top_decline_reasons` (with fallback to local DB when Databricks unavailable).
- **Smart Checkout:** service paths, path performance, 3DS funnel (Brazil) → Databricks views.
- **Smart Retry:** `GET /api/analytics/retry/performance` → retry performance view.
- **Recommendations:** `GET /api/analytics/recommendations` → Lakehouse / Vector Search.
- **Online features:** `GET /api/analytics/online-features` → Lakehouse.
- **ML models:** `GET /api/analytics/models` → Unity Catalog / Model Registry.
- **Rules:** `GET/POST/PATCH/DELETE /api/rules` → Lakehouse approval rules table.

All of the above are implemented in `backend/routes/analytics.py` and `backend/routes/rules.py`, using `DatabricksService` in `backend/services/databricks_service.py`, which runs SQL via the Databricks SQL Warehouse against the configured catalog and schema.

---

## Visualizations

- **In-app charts and cards:** Data is from the API; when Databricks is available, that data is from Databricks as above.
- **Embedded dashboards (Dashboards page):** Every dashboard is a **Databricks SQL (DBSQL) dashboard**. The app builds the iframe URL from the workspace URL and the dashboard path (e.g. `/sql/dashboards/executive_overview`). All visualization rendering for those dashboards happens in Databricks.

---

## App database (local)

The following are stored in and read from the **app database** (SQLModel/SQLite by default), not from Databricks:

- **Recent decisions:** Written when users run the decisioning playground; used for “Recent decisions” on the Dashboard and similar UI. Purely operational.
- **Experiments and incidents:** Created and listed via the app; operational only.
- **Ingested auth events:** `POST /api/analytics/events` writes to the app DB (demo/development).

When Databricks is **not** configured or **unavailable**, the app falls back to the local DB for:

- **KPIs** (`/api/analytics/kpis`)
- **Decline summary** (`/api/analytics/declines/summary`)

So in a deployment with Databricks configured and healthy, **all analytics and reporting data and all embedded dashboard visualizations are effectively from Databricks**; the only data that remains in the app DB is operational (recent decisions, experiments, incidents, and optionally ingested events).
