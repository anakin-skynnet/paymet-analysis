# Unified Agent Context — Payment Analysis Project

This file consolidates knowledge and context from all conversation prompts so the Cursor agent has full context. Keep it updated when major decisions or features are added.

---

## 1. Project overview

- **Name:** payment-analysis (Paymet Analysis)
- **Type:** Full-stack Databricks App (React + Vite frontend, FastAPI backend), deployed via Databricks Asset Bundle. App runs on Databricks (Compute → Apps); not run locally.
- **Paths:** Frontend `src/payment_analysis/ui/`, backend `src/payment_analysis/backend/`, agents `src/payment_analysis/agents/`, transform `src/payment_analysis/transform/`, bundle config `databricks.yml`, resources in `resources/`.

---

## 2. BI dashboards (real-time, cleanup, widget fixes)

**User goals (consolidated):**
- Review and fix all dashboards; pick the most impactful and clear design per case; fix widget settings and assign columns/values.
- Make dashboards **real-time**: change hourly aggregation to **seconds**.
- **Clean all dashboards from workspace except those whose name starts with `dbdemos`** before deploying the new fixed ones.

**Implemented:**

- **Gold views (by-second, real-time):** In `src/payment_analysis/transform/gold_views.sql`:
  - `v_approval_trends_by_second` — approval trends by second (last 1 hour).
  - `v_approval_trends_hourly` — same per-second granularity (event_second), last 1 hour; name kept for backward compatibility.
  - `v_streaming_ingestion_by_second`, `v_streaming_ingestion_hourly` (now by-second), `v_silver_processed_by_second`, `v_silver_processed_hourly` (now by-second) — bronze/silver ingestion by second.
  - `v_streaming_volume_per_second` — volume per second; time column is `event_second`.

- **Dashboard datasets:** Executive Overview, Daily Trends, Real-Time Monitoring, and Streaming Data Quality use by-second views; time column is `event_second` (widgets use it on x-axis).

- **Dashboard script** `scripts/dashboards.py`:
  - ASSETS list includes the new by-second views.
  - **Commands:** `prepare`, `validate-assets`, `publish`, `link-widgets`, `check-widgets`, `fix-visualization-fields`, `best-widgets`, `fix-widget-settings`, `delete-workspace-dashboards`, **`clean-workspace-except-dbdemos`**.
  - **`clean-workspace-except-dbdemos`:** Lists dashboards under workspace `.../dashboards`, deletes every dashboard whose **name** (path basename) does **not** start with `dbdemos`. Use before deploy to avoid leaving old dashboards. Supports `--dry-run`.

- **Deploy flow** `scripts/bundle.sh`: On **deploy**, the script runs `clean-workspace-except-dbdemos` first, then `prepare_dashboards`, then `databricks bundle deploy`, then `publish`.

- **Widgets:** All 12 dashboards were run through `best-widgets` so widget types and encodings match dataset columns. Time axes use `event_second` where the dataset is by-second.

**Dashboard source:** `resources/dashboards/*.lvdash.json`. Prepare copies to `dashboards/` and `.build/dashboards/` and replaces `__CATALOG__.__SCHEMA__` in queries. Bundle uses `.build/dashboards/`.

**Mosaic AI Agent Framework (AgentBricks) conversion:** Current agents are custom Python (BaseAgent, OrchestratorAgent, 5 specialists). AgentBricks mapping: all 5 specialists = **Tool-Calling Agents** (LangGraph ReAct + UC functions); Orchestrator = **Multi-Agent System** (Workspace Multi-Agent Supervisor or LangGraph StateGraph). **Job 3** includes task **create_uc_agent_tools** (notebook `create_uc_agent_tools.py`) so UC tool functions exist after gold views. Conversion steps: (1) UC functions ✓ (created by Job 3), (2) LangGraph agents in `langgraph_agents.py`, (3) log/register to MLflow UC, (4) deploy to Model Serving, (5) Multi-Agent Supervisor. See `docs/DATABRICKS.md` Part 3. Migration priority: start with Decline Analyst.

---

## 3. Orchestrator agent and app UI

**User goal:** Verify the orchestrator agent created in the job is registered so it can be used and interacted with via the Databricks app UI (reference: Getnet AI Assistant–style panel with recommendations).

**Implemented / verified:**

- **Job 6** (`resources/agents.yml`): `job_6_deploy_agents` — "[${var.environment}] 6. Deploy Agents (Orchestrator & Specialists)". Single notebook task runs `agent_framework.py` (orchestrator + Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender). Bound to app in `resources/fastapi_app.yml` as `job-6-agents` with `CAN_MANAGE_RUN`.

- **Backend** `src/payment_analysis/backend/routes/agents.py`:
  - `POST /api/agents/orchestrator/chat`: Runs Job 6 with notebook params (catalog, schema, query, agent_role=orchestrator), polls until run terminates, returns `synthesis`, `agents_used`, `run_page_url`.
  - **Job ID resolution:** Orchestrator job ID comes from `DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT` if set; otherwise from **workspace resolution** via `resolve_orchestrator_job_id(ws)` in `setup.py` (same logic as Setup “Refresh job IDs”: list jobs, match “6. Deploy Agents”). So the assistant works after deploy without setting the env var, as long as the app is opened from Compute → Apps.

- **UI:** Command Center (`src/payment_analysis/ui/routes/_sidebar/command-center.tsx`) matches reference layout: top KPIs (Gross Approval Rate, False Decline Rate, Data Quality Health), Real-Time Monitor (entry systems PD/WS/SEP/Checkout, 0.5s refresh), 3DS Friction Funnel, Entry Gate Telemetry, Top 5 Decline Reasons, False Insights Tracker, Retry/Recurrence, Alerts panel, Data Quality checklist, Control Panel. Two chat panels: **Getnet AI Assistant** (`POST /api/agents/chat`), **Agent Recommendations** (`POST /api/agents/orchestrator/chat`). Charts and alerts auto-refresh every 0.5s. Backend: `GET /api/analytics/command-center/entry-throughput` (Databricks first, then mock), `GET /api/analytics/active-alerts`; `DatabricksService.get_command_center_entry_throughput()` and `get_active_alerts()`.

- **Docs:** `AGENTS.md` includes an “Orchestrator in the app UI” section: requirements (Job 6 deployed, open from Compute → Apps, optional env var, catalog/schema) and how to verify (Command Center → Agent Recommendations → send a message).

**Requirements for using the orchestrator via UI:** Job 6 deployed; open app from Compute → Apps (token forwarded); optional `DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT`; effective catalog/schema (app_config or env).

---

## 4. Commands and workflows (quick reference)

| Intent | Command / step |
|--------|----------------|
| Check code | `uv run apx dev check` |
| Prepare dashboards | `uv run python scripts/dashboards.py prepare [--catalog X] [--schema Y]` |
| Clean non-dbdemos dashboards | `uv run python scripts/dashboards.py clean-workspace-except-dbdemos [--path ...] [--dry-run]` |
| Full deploy (clean + prepare + deploy + publish) | `./scripts/bundle.sh deploy dev` (or `prod`) |
| Verify bundle | `./scripts/bundle.sh verify [dev\|prod]` |
| Publish dashboards (embed credentials) | `uv run python scripts/dashboards.py publish` |
| Best widget types on all dashboards | `uv run python scripts/dashboards.py best-widgets` |

---

## 5. Key file reference

| Area | Paths |
|------|--------|
| Agent framework (orchestrator + specialists) | `src/payment_analysis/agents/agent_framework.py` |
| Agent API (list, chat, orchestrator chat) | `src/payment_analysis/backend/routes/agents.py` |
| Job ID resolution (setup + orchestrator) | `src/payment_analysis/backend/routes/setup.py` (`resolve_orchestrator_job_id`, `_resolve_job_and_pipeline_ids`) |
| Gold views (by-second real-time + daily/other) | `src/payment_analysis/transform/gold_views.sql` |
| Dashboard source JSONs | `resources/dashboards/*.lvdash.json` |
| Dashboard script | `scripts/dashboards.py` |
| Bundle app + job bindings | `resources/fastapi_app.yml`, `resources/agents.yml` |
| Single source of truth (scope, prompts, MCP, agents) | `AGENTS.md` at repo root |
| Cursor project rules | `.cursor/rules/project.mdc` |

---

## 6. Patterns and conventions (from prompts)

- **Dashboards:** Use by-second views and `event_second` for real-time; widget fields must match dataset query columns; run `best-widgets` after changing datasets.
- **Workspace cleanup:** Before deploying new dashboards, run `clean-workspace-except-dbdemos` so only dashboards with names starting with `dbdemos` are kept; all others under `.../dashboards` are removed.
- **Orchestrator:** No need to set `DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT` if the app is opened from Compute → Apps; backend resolves Job 6 from the workspace.
- **Package management:** Use `uv` for Python; for frontend prefer `uv run apx bun install` / `uv run apx bun add` when bun may not be on PATH.
- **Dependencies:** Do not update dependencies/packages unless instructed.

---

*Last consolidated: Command Center (0.5s chart/alerts refresh, entry-throughput API, Alerts/Data Quality/Top Decline cards), package.json pinned versions, run_and_validate_jobs status hint fix; dashboards (reference Lakeview v3 URL for Executive Overview when workspace matches adb-984752964297111); orchestrator, deploy flow. No open TODO/FIXME in codebase.*
