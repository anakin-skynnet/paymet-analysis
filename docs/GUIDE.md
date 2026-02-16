# Payment Analysis — Guide

Single reference for **what** the platform does, **how** it is built, and how it aligns with best practices. For deploy steps, env vars, and troubleshooting see [Deployment](DEPLOYMENT.md); for Databricks alignment and agents see [REFERENCE.md](REFERENCE.md).

---

## 1. Business overview & impact

**Primary goal:** Accelerate payment approval rates and reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities.

**Approach:** Real-time ML (4 HistGradientBoosting models with 14 engineered features), closed-loop decisioning with parallel enrichment, streaming features, AI agents with write-back tools, and actionable analytics so every decision (auth, retry, routing) is data-driven, continuously improving, and consistent with business policy.

### Use cases and impact on approval rates

| Use case | What it does | Impact on accelerating approval rates |
|----------|----------------|---------------------------------------|
| **Smart Retry** | Retry logic, timing, cohorts; ML retry model; recovery gap analysis; `v_retry_success_by_reason` gold view | Surfaces recoverable declines with recovery gap per cohort; granular retry success by decline reason and scenario. |
| **Smart Checkout** | 3DS funnel with contextual guidance, service-path performance, Brazil payment links | Balances friction vs risk with threshold-based recommendations on each metric. |
| **Reason codes & declines** | Unified decline taxonomy, inline expert review (Valid/Invalid/Non-Actionable), recovery opportunities | Identifies top decline reasons with direct feedback; Decline Analyst writes recommendations to Lakebase. |
| **Risk & fraud** | Risk tier, fraud score, Risk Assessor agent with write-back tools | Enables risk-based auth; agent proposes config changes to Lakebase. |
| **Routing optimization** | Routing performance, VS top-route boosting, Smart Routing agent, model serving | Routes to best solution using VS approval rates and agent confidence. |
| **Decisioning** | Closed-loop auth/retry/routing; parallel ML + VS + streaming features; outcome recording | Unifies all signals; policies adjust borderline decisions; feedback loop via POST /outcome. |

### Technology map

| Technology | Role | How it accelerates approval rates |
|------------|------|-----------------------------------|
| **Lakeflow (Bronze → Silver → Gold)** | Ingestion and transforms | Clean, timely data for ML and analytics. |
| **Unity Catalog** | Tables, governance, gold views | Single source of truth for KPIs and model inputs. |
| **ML models** (4 HistGradientBoosting, 14 features) | Real-time scores with training-inference parity | Decisions based on predicted likelihood and risk; `_build_ml_features()` ensures exact match. |
| **Rules engine** (Lakebase/Lakehouse) | Configurable business rules + config API | Operators tune without code; config exposed via GET /api/decision/config. |
| **Vector Search** | Similar-transaction lookup + policy integration | VS approval rates adjust borderline risk tiers in policies. |
| **7 AI agents** (all with write-back) | Analytics, recommendations, config proposals | Agents write recommendations and propose config changes directly to Lakebase. |
| **3 unified dashboards + 16+ gold views** | KPIs, funnels, reason codes, retry-by-reason | Visibility into approvals/declines; v_retry_success_by_reason for granular retry analysis. |
| **Streaming features** | Real-time behavioral features | approval_rate_5m, txn_velocity_1m feed into authentication decisions. |
| **FastAPI + React app** | Closed-loop decision API and actionable control panel | Preset scenarios, inline expert review, recovery gap, top-3 actions, 90% target lines. |
| **Outcome feedback loop** | POST /api/decision/outcome | Records actual outcomes; system continuously improves. |
| **Dual-write sync** | Approval rules synced between Lakebase and Lakehouse | Rules changes in the UI propagate to agents (and vice versa) via BackgroundTasks. |

**High-level flow:** Simulator or real pipelines → Lakeflow → Unity Catalog. Intelligence: ML + rules + Vector Search + AI agents. Application: FastAPI backend + React UI (Setup & Run, dashboards, rules, decisioning).

### Validation: alignment with accelerating approval rates

The solution is designed and documented around a single business objective: **accelerate payment approval rates** and reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities. Each major component is wired to that goal. The recent implementation of 20 QA recommendations strengthened this alignment: (1) closed feedback loop with outcome recording, (2) ML feature parity between training and inference, (3) parallel enrichment for production performance, (4) streaming real-time features, (5) policies that use VS data and agent confidence for borderline decisions, (6) agent write-back tools, and (7) actionable UI with top-3 actions, target lines, contextual guidance, preset scenarios, inline expert review, and recovery gap analysis.

---

## 1b. Component-by-component impact on approval rates

| Component | What it is | How it accelerates approval rates |
|-----------|------------|-----------------------------------|
| **Medallion (Bronze → Silver → Gold)** | Lakeflow pipelines and 16+ gold views: `payments_raw_bronze`, `payments_enriched_silver`, gold views (KPIs, trends, reason codes, retry performance, `v_retry_success_by_reason`). | Provides clean, timely data so ML models, rules, and dashboards see accurate patterns; `v_retry_success_by_reason` enables granular retry analysis by decline reason and scenario. |
| **Unity Catalog & Lakehouse** | Catalog/schema, volumes, `app_config`, gold views, and (optionally) rules/recommendations in Delta tables. | Single source of truth for catalog/schema and config; gold views feed dashboards and agents; rules and recommendations drive approve/decline/retry behavior. |
| **Lakebase (Postgres)** | Managed Postgres for `app_config`, `approval_rules`, `app_settings`, `online_features`, experiments, incidents. | Stores business rules and config that ML and agents read; experiments support A/B tests (e.g. 3DS strategy); operators tune rules without code to approve more good transactions and block more fraud. |
| **Rules engine (approval rules)** | Configurable rules (conditions + actions) from Lakebase or Lakehouse; exposed via `/api/rules`. **Dual-write:** changes sync between Lakebase and Lakehouse via BackgroundTasks so both the UI and agents see the same rules. | Lets operators define when to approve, decline, or retry; ML and agents use these rules so every decision is consistent with policy and optimized for approval rate vs risk. |
| **ML models (4)** | HistGradientBoosting with 14 engineered features (temporal, merchant/solution approval rates, network encoding, risk-amount interaction) — trained on `payments_enriched_silver`, registered in Unity Catalog, served via model serving endpoints. `_build_ml_features()` ensures training-inference feature parity. | **Approval propensity:** predicts likelihood of approval. **Risk:** enables risk-based auth. **Routing:** picks the solution maximizing approval for the segment. **Retry:** predicts retry success and timing. |
| **Decisioning API** | Closed-loop endpoints (`/api/decision/authentication`, `/retry`, `/routing`, `/outcome`, `/config`) powered by `DecisionEngine`: parallel ML + VS enrichment (`asyncio.gather`), streaming real-time features (approval_rate_5m, txn_velocity_1m), Lakebase config, rule evaluation, thread-safe caching (`threading.Lock`). Policies use VS approval rates and agent confidence to adjust borderline decisions. POST `/outcome` records actual outcomes. GET `/config` exposes current thresholds. | Single decision layer with continuous improvement; parallel enrichment for production performance; outcome feedback loop ensures the system learns from every decision. Falls back to pure-policy heuristics when Lakebase/ML is unavailable. |
| **Vector Search** | Delta-sync index `similar_transactions_index` on `transaction_summaries_for_search`; similar-case lookup via `VECTOR_SEARCH()` TVF. | Powers “similar cases” recommendations (e.g. “similar transactions approved 65% with retry after 2h”); feeds recommendations into the Decisioning UI and agents to suggest actions that accelerate approvals. |
| **7 AI agents** (all with write-back) | Orchestrator + Smart Routing, Smart Retry, Decline Analyst (write_decline_recommendation, propose_decline_config), Risk Assessor (write_risk_recommendation, propose_risk_config), Performance Recommender. Write-back tools let agents write recommendations and propose config changes directly to Lakebase. 17 individual UC functions + 5 consolidated for ResponsesAgent. 4 ML + 3 agent endpoints. | Answer questions; suggest and write routing, retry, and rule changes; propose config changes that operators review from the UI. |
| **3 unified dashboards** | Data & Quality, ML & Optimization, Executive & Trends in Databricks AI/BI (Lakeview). Embeddable in the app via `/embed/dashboardsv3/` path. | Give visibility into approval rates, decline reasons, solution performance, and recovery; operators see where to act and track impact. |
| **FastAPI + React app** | 16-page control panel with actionable UI: Command Center (top-3 actions, 90% target lines, last-updated), Smart Checkout (contextual guidance), Decisioning (preset scenarios, actionable recommendations with "Create Rule"/"Apply to Context"), Reason Codes (inline expert review: Valid/Invalid/Non-Actionable), Smart Retry (recovery gap analysis). All routes have `ErrorBoundary` wrappers and `glass-card` styling. | One place to operate the full stack with every data point telling operators what to do next. |
| **Genie** | Natural-language “Ask Data” in the workspace, synced with sample questions (approval rate, trends, segments). | Extends visibility: ask “What is the approval rate?” or “Which segment has the lowest approval rate?” in the lakehouse context, supporting the same goal of accelerating approval rates. |
| **Experiments & incidents** | A/B experiments (e.g. 3DS treatment vs control) and incident/remediation tracking in Lakebase. | Experiments measure impact of policy changes on approval rate; incidents track production issues that might hurt approvals so they can be fixed. |

### 1c. Payment services context (Getnet)

Payment transactions can use several services (Antifraud, Vault, 3DS, Data Only, Recurrence, Network Token, IdPay, Passkey, Click to Pay). **Smart Checkout**, **Reason Codes**, and **Smart Retry** rely on a shared data foundation: medallion pipelines, gold views, and a single control panel. **Brazil** accounts for most volume; the platform supports catalog/schema and country filters. **Entry systems:** Checkout, PD, WS, SEP; each returns the final response to the merchant. **Smart Retry** covers recurrence and reattempts (e.g. 1M+ such transactions per month in Brazil). **False Insights** is a quality metric (insights marked invalid by specialists) to balance speed vs accuracy.

**Business requirement → Solution:** Data foundation → Medallion + gold views. Unified decline visibility → Reason Codes, decline dashboards, Decline Analyst. Smart Checkout (Brazil) → Smart Checkout UI, 3DS funnel, Smart Routing agent. Smart Retry → Retry UI, Smart Retry agent, decisioning API. Actionable insights → Decisioning API, orchestrator + 5 agents, rules engine. Feedback loop → Experiments, incidents, rules CRUD, model retraining. Single control panel → FastAPI + React app (Setup & Run, Dashboards, Rules, Decisioning, Agents). AI-driven intelligence → 7 AI agents, Genie.

---

## 2. Architecture

- **Platform:** Databricks — Lakeflow, Unity Catalog, SQL Warehouse, MLflow, Model Serving, Genie, Vector Search, Lakebase. 3 unified dashboards. 4 ML + 3 agent model serving endpoints. All serverless compute.
- **App:** FastAPI (analytics, decisioning, dashboards, agents, rules, setup) + React (TanStack Router, shadcn/ui). API prefix `/api` for token-based auth.
- **Stack:** Delta, Unity Catalog, Lakeflow, SQL Warehouse, Lakebase (Postgres for rules/experiments/incidents/online features), Vector Search (similar transactions), MLflow, FastAPI, React, TypeScript, Vite, Bun, Databricks Asset Bundles.

**Data flow:** Ingestion → Processing (Bronze → Silver → Gold, &lt;5s) → Intelligence (ML + 7 AI agents + Vector Search) → Analytics (3 unified dashboards, Genie) → Application (FastAPI + React).

Medallion: Bronze `payments_raw_bronze`, Silver `payments_enriched_silver`, Gold 15+ views. Lakehouse bootstrap creates `app_config`, rules, recommendations, and related views (see [Deployment](DEPLOYMENT.md)). Vector Search delta-sync index `similar_transactions_index` on `transaction_summaries_for_search` for similar-transaction lookup (populated from silver via MERGE, synced to embedding model `databricks-bge-large-en`).

---

## 3. Project structure

| Area | Path | Purpose |
|------|------|---------|
| Backend | `src/payment_analysis/backend/` | FastAPI app, config, dependencies, routes (analytics, decision, dashboards, agents, rules, setup, experiments, incidents, notebooks), services, Lakebase helpers, DecisionEngine, shared utils (`is_mock_request`) |
| Frontend | `src/payment_analysis/ui/` | React app: routes, components (apx, layout, ui), lib (API client), config, hooks |
| Transform | `src/payment_analysis/transform/` | Lakehouse SQL, gold views, lakehouse bootstrap, prepare/publish dashboards |
| Streaming | `src/payment_analysis/streaming/` | Bronze ingest, real-time pipeline, transaction simulator |
| ML | `src/payment_analysis/ml/` | Model training (approval, risk, routing, retry) |
| Agents | `src/payment_analysis/agents/` | Orchestrator + specialist agents |
| Bundle | `resources/` | Unity Catalog, Lakebase, pipelines, sql_warehouse, ml_jobs, agents, dashboards, fastapi_app |
| Scripts | `scripts/` | bundle.sh (validate/deploy/verify), dashboards.py (prepare/validate-assets), sync_requirements_from_lock.py |

### Bundle resources

| Category | Resources |
|----------|-----------|
| UC | Schema + volumes (raw_data, checkpoints, ml_artifacts, reports) |
| Lakebase | Instance + UC catalog (rules, experiments, incidents) |
| SQL warehouse | Payment Analysis Warehouse |
| Pipelines | ETL, Real-Time Stream |
| Jobs | 7 steps (repositories, simulator, ingestion, dashboards, ML, agents, Genie sync) |
| Dashboards | 3 unified (Data & Quality, ML & Optimization, Executive & Trends) |
| Model Serving | 4 ML endpoints (always deployed) + 3 agent endpoints (managed by Job 6) |
| App | payment-analysis (FastAPI + React) |
| Vector Search | Endpoint + delta-sync index for similar transactions |

---

## 4. Workspace components ↔ UI mapping

Execution order in **Setup & Run:** foundation (Lakehouse, Vector Search, gold views, simulator), then optional streaming, ETL, ML, Genie, agents, dashboards.

| Component | Setup & Run step | One-click |
|-----------|------------------|-----------|
| Lakehouse Bootstrap | Step 1 | Run job (app_config, rules, recommendations) |
| Vector Search index | Step 1 (same job) | Run job (similar-transaction lookup) |
| Create Gold Views | Step 3 | Run job (`.build/transform/gold_views.sql`) |
| Transaction Stream Simulator | Step 2 | Run simulator |
| Pipelines (ETL, Real-Time) | — | Start pipeline from Setup & Run |
| Train ML Models | Step 5 | Run ML training |
| Genie Space Sync | Optional | Run Genie sync |
| Orchestrator + 5 agents | Step 6 | Run / Open |
| Publish Dashboards | Step 4 | Run job (embed credentials) |
| 3 Dashboards | Dashboards page | Card opens in workspace |
| Rules, Experiments, Incidents | Rules, Experiments, Incidents | CRUD via API |

Job/pipeline IDs: `GET /api/setup/defaults`; env overrides: [Deployment](DEPLOYMENT.md).

---

## 5. Data sources (UI ↔ Backend ↔ Databricks)

All UI data goes through the FastAPI backend. No direct Lakebase or Databricks calls from the frontend.

| Area | Backend API | Source |
|------|-------------|--------|
| KPIs, trends, reason codes, declines, Smart Checkout, Smart Retry, recommendations, online features, models, countries | `GET /api/analytics/*` | Databricks (Unity Catalog, SQL Warehouse); fallback to app DB when unavailable |
| Rules | `GET/POST/PATCH/DELETE /api/rules` | Lakebase (if configured) or Lakehouse |
| Setup defaults, config, settings | `GET /api/setup/*`, `PATCH /api/setup/config` | Lakebase app_config/app_settings + workspace job/pipeline resolution |
| Dashboards list & embed URL | `GET /api/dashboards/*` | Static registry + workspace URL for embed |
| Agents list & URLs | `GET /api/agents/*` | Backend → WorkspaceClient |
| Experiments, incidents, decision logs | `GET/POST /api/experiments`, `/api/incidents` | Lakebase (Postgres) |
| Decision outcomes | `POST /api/decision/outcome` | Lakebase (feedback loop) |
| Decision config | `GET /api/decision/config` | DecisionEngine (Lakebase config) |

**Credentials:** When the app is opened from **Compute → Apps**, the platform forwards the user token. The backend uses it for Databricks; otherwise `DATABRICKS_TOKEN` from the app environment. Catalog/schema come from `app_config` (Lakebase or Lakehouse), loaded at startup or on first request.

### Catalog and schema

**Bundle:** `var.catalog`, `var.schema`. **Backend:** env + `app_config`. **Dashboards:** catalog.schema from `scripts/dashboards.py prepare`. Effective catalog/schema from Lakehouse `app_config`; set via **Setup & Run** → **Save catalog & schema**.

---

## 6. Control panel & UI

All data is **fetched from the Databricks backend** and is **interactive**.

### Setup & Run (Operations)

- **Run jobs** — Steps 1–6. **Run** starts the job via `POST /api/setup/run-job`; **Open** opens the job in the workspace.
- **Pipelines** — Start ETL and Real-Time via **Run** → `POST /api/setup/run-pipeline`.
- **Catalog & schema** — Form from `GET /api/setup/defaults`; **Save catalog & schema** → `PATCH /api/setup/config`.
- **Data & config** — App config & settings, countries, online features from backend (Lakebase/Lakehouse).

### Dashboards

- **List:** `GET /api/dashboards/dashboards`. **Embed URL:** `GET /api/dashboards/dashboards/{id}/url?embed=true`. Click to open in workspace or **View embedded** in the UI.

### Genie (AI agents)

- **Ask Data with Genie** — Card opens Genie in the Databricks workspace; chat happens inside Databricks.

### Agents & ML

- **AI agents** — List: `GET /api/agents/agents`. Open: `GET /api/agents/agents/{id}/url` → workspace.
- **ML models** — List: `GET /api/analytics/models` (Unity Catalog). Links to MLflow, model registry, notebooks from backend.

### Lakebase / Postgres data in the UI

| Data | Backend source | Where in UI |
|------|----------------|-------------|
| App config | Lakebase app_config / Lakehouse | Setup → Parameters + Data & config |
| App settings | Lakebase app_settings | Setup → Data & config |
| Countries | Lakehouse / UC | Setup → Data & config; country dropdowns |
| Online features | Lakebase → Lakehouse | Setup → Data & config |
| Approval rules | Lakebase → Lakehouse | Rules page (CRUD) |

### 6b. Two chatbots

| Chat | Endpoint | Purpose |
|------|----------|---------|
| **AI Chatbot (Orchestrator)** | `POST /api/agents/orchestrator/chat` | Orchestrator agent (Job 6 or Model Serving): recommendations, payment analysis from specialists. |
| **Genie Assistant** | `POST /api/agents/chat` | Databricks Genie Conversation API when `GENIE_SPACE_ID` is set. |

Header buttons: “AI Chatbot” (Orchestrator) and “Genie Assistant”. Command Center “Chat with Orchestrator” opens the AI Chatbot. If Orchestrator fails, the app can fall back to Genie or a static reply.

### 6c. Where artifacts are used in the app

| Category | Resources | Used in app |
|----------|-----------|-------------|
| Streaming & real-time | Bronze/Silver/Gold, pipelines, Job 2 (simulator) | Data & Quality, Command Center KPIs, Dashboards, Recommendations |
| ML models & inference | Approval propensity, Risk, Routing, Retry | Decisioning (Live ML predictions), Models page |
| Agents | Orchestrator, Decline analyst, Routing/Retry/Risk/Performance | AI Agents page, Orchestrator chat |
| Dashboards | Data & Quality, ML & Optimization, Executive & Trends | Dashboards page (list, embed, open in workspace) |
| Vector Search | Similar-case index | Decisioning recommendations via v_recommendations_from_lakehouse |
| Lakebase / Lakehouse | Rules, recommendations, app_config | Rules page, Decisioning, analytics |

---

## 7. Databricks App compliance checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| Runtime spec at root | OK | `app.yml` |
| Command | OK | `uvicorn payment_analysis.backend.app:app` |
| API prefix `/api` | OK | Router `prefix="/api"` |
| requirements.txt | OK | Exact versions from pyproject.toml/uv.lock |
| No system packages | OK | Pure Python deps; psycopg[binary] for DB |
| Config from env | OK | DATABRICKS_*, LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID |
| Bundle app resource | OK | `resources/fastapi_app.yml` |
| Node/frontend | OK | engines `>=22.0.0`; TanStack overrides |

---

## 8. Best practices alignment

**References:** [Apps Cookbook](https://apps-cookbook.dev/docs/intro), [apx](https://github.com/databricks-solutions/apx), [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit).

- **API:** All routes use `response_model` and `operation_id` for OpenAPI client generation. API prefix `/api`. Health: `/api/v1/healthcheck`, `/api/v1/health/database`.
- **Cookbook:** FastAPI layout, `/api` prefix, healthcheck at `/api/v1/healthcheck`, OAuth2/token auth.
- **apx:** Full-stack (React + FastAPI), OpenAPI client at build time, `apx dev check` / `apx build`, shadcn/ui under `src/payment_analysis/ui/components/`, uv for Python, Bun for frontend.
- **AI Dev Kit:** Databricks SDK usage (no guessing API), MCP tools, Asset Bundles, Apps as first-class.

**Unified rules (AGENTS.md / .cursor/rules):** 3-model pattern (Entity, EntityIn, EntityOut); frontend useXSuspense + Suspense + Skeleton; selector(); exact dependency versions; uv / apx bun; do not update deps unless instructed; check after changes.

---

## 9. Verification

**Commands:**

| Purpose | Command |
|--------|--------|
| TypeScript + Python | `uv run apx dev check` |
| Bundle (prepare + validate) | `./scripts/bundle.sh validate dev` |
| Full verify (build, smoke, dashboards, bundle) | `./scripts/bundle.sh verify dev` |
| Deploy resources (phase 1: all except App) | `./scripts/bundle.sh deploy dev` |
| Deploy app (phase 2: App with model serving) | `./scripts/bundle.sh deploy app dev` |
| Automated two-phase deploy | `./scripts/deploy_with_dependencies.sh dev` |

**Data source indicator:** Command Center footer shows **“Data: Databricks”** when `GET /api/v1/health/databricks` returns `analytics_source === "Unity Catalog"`, otherwise **“Data: Sample (mock)”**. If you see mock, check app env (DATABRICKS_WAREHOUSE_ID, DATABRICKS_HOST or open from Compute → Apps) and user auth scopes.

**Deployment summary:** Two-phase: `./scripts/bundle.sh deploy dev` (phase 1: resources) → run jobs 5 & 6 → `./scripts/bundle.sh deploy app dev` (phase 2: App). Or automated: `./scripts/deploy_with_dependencies.sh dev`. App env: defined in **`app.yml`** (e.g. LAKEBASE_*, ORCHESTRATOR_SERVING_ENDPOINT); override in App Environment (e.g. DATABRICKS_WAREHOUSE_ID, DATABRICKS_TOKEN). Full steps and troubleshooting: [Deployment](DEPLOYMENT.md).

---

## 10. Data sources & code guidelines

Aligns the app with Databricks Apps best practices and confirms **all data and AI are from Databricks** when the workspace connection is available.

**Reference guidelines:** [Databricks Apps Cookbook](https://apps-cookbook.dev/docs/intro), [apx](https://github.com/databricks-solutions/apx), [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit), [dbdemos](https://github.com/databricks-demos/dbdemos).

### Data and AI source: Databricks-first

| Area | Primary source | Fallback when Databricks unavailable |
|------|----------------|--------------------------------------|
| **Analytics (KPIs, trends, reason codes)** | Unity Catalog views via SQL Warehouse (Statement Execution API) | Mock data; `/kpis` can fall back to local DB counts |
| **ML inference (approval, risk, routing)** | Databricks Model Serving endpoints | Mock predictions |
| **Recommendations / Vector Search** | UC tables + Vector Search / Lakehouse | Mock recommendations |
| **Online features** | Lakebase or Lakehouse feature tables | Mock features |
| **Rules (approval rules)** | Lakebase/Lakehouse or UC | Local DB / error when not available |
| **Agents list** | Workspace (Mosaic AI Gateway, Genie, UC models) | N/A |
| **Dashboards** | DBSQL dashboards in workspace (embed URLs) | N/A |
| **Jobs / Pipelines** | Databricks Jobs & Pipelines APIs | N/A |

**Unity Catalog views used by analytics** (via `DatabricksService.execute_query()`): `v_executive_kpis`, `v_approval_trends_hourly` (per-second granularity), `v_approval_trends_by_second`, `v_solution_performance`, `v_top_decline_reasons`, `v_smart_checkout_*`, `v_3ds_funnel_br`, `v_reason_codes_br`, `v_reason_code_insights_br`, `v_entry_system_distribution_br`, `v_dedup_collision_stats`, `v_false_insights_metric`, `v_retry_performance`, `v_retry_success_by_reason`, `v_recommendations_from_lakehouse`, plus country tables. Full list in `databricks_service.py`.

**AI/ML sources:** Model Serving (approval, risk, routing); Genie / Mosaic AI Gateway (linked from UI); agents listed from workspace config.

**Validation:** `GET /api/v1/health/databricks` returns whether the Databricks connection is available and the effective data source. See also docstrings in `backend/services/databricks_service.py` and `backend/routes/analytics.py`.

**Implementation:** SQL via **Databricks SDK** `statement_execution.execute_statement()` (not legacy SQL Connector). When the app is opened from Compute → Apps, token is forwarded via `X-Forwarded-Access-Token`. Mock/fallbacks only when connection is missing or fails.
