# Payment Analysis — Unified Agent

This file is the **single source of truth** for the AI agent working on this repo. It unifies **all chat history, context, and prompts** so a single agent represents the latest version of the solution across all chats.

**Unified chat history & context:** All prior requests from different chats are reflected here: (1) one agent definition and rules, (2) solution scope and structure, (3) version alignment and exact dependency versions, (4) verify-and-deploy flow, (5) common prompts and where to look. When working in any chat, use this file plus `.cursor/rules/project.mdc` as the single agent; do not rely on chat-specific context that contradicts this. Verify that changes are applied on the **main** branch (run check and bundle verify; commit and push to main).

---

## 1. Solution scope

**Project:** Payment Analysis — Databricks-powered payment approval optimization.

**Goal:** Accelerate approval rates and reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities.

**Stack:** Real-time ML (4 HistGradientBoosting models with 14 engineered features), ResponsesAgent (MLflow, 10 UC tools + python_exec), rules engine, Vector Search, streaming features, Lakebase (Postgres). Data flow: simulator → Lakeflow (Bronze → Silver → Gold) → Unity Catalog → FastAPI + React app. 4 ML model serving endpoints + 1 agent endpoint (`payment-response-agent`, managed by Job 6). 17 individual + 5 consolidated UC functions. Dual-write sync for approval rules. Closed-loop DecisionEngine: parallel ML + VS enrichment (`asyncio.gather`), streaming features, thread-safe caching, outcome recording (POST /outcome), policies that use VS approval rates and agent confidence for borderline decisions.

**Use cases:** Smart Retry (with recovery gap analysis), Smart Checkout (contextual 3DS guidance), Reason codes & declines (inline expert review), Risk & fraud, Routing optimization, Decisioning (closed-loop auth/retry/routing with preset scenarios).

**When the user says "APP":** Confirm if they mean the **Databricks App** (payment-analysis) or something else.

---

## 2. Do's and don'ts

- **OpenAPI client:** Generated at build time; do not manually regenerate unless instructed.
- **apx:** Prefer running apx via MCP when available (`check`, `search_registry_components`, `add_component`, `docs`, `refresh_openapi`, `get_route_info`, `databricks_apps_logs`).
- **Components:** Use MCP `search_registry_components` and `add_component` (or `uv run apx components add <name> --yes`) for shadcn/ui. Add components under `src/payment_analysis/ui/components/`; group by functionality (e.g. `chat/`), not only by file type.
- **Frontend API:** Use error boundaries for API calls.
- **After changes:** Run `uv run apx dev check` (or MCP `check`) to validate.
- **Browser/Playwright:** If available, use native browser or Playwright MCP to verify frontend changes.
- **Databricks SDK:** Use apx MCP `docs` to search Databricks SDK docs; do not guess API signatures.
- **Naming:** Use Databricks latest features, releases, and naming.
- **Dependencies:** Do not update dependencies or packages unless the user instructs.

---

## 3. Package management

- **Python:** Always use `uv` (never `pip`). Commands: `uv lock`, `uv run ...`, `uv run python scripts/sync_requirements_from_lock.py` after changing `pyproject.toml`.
- **Frontend:** Bun may not be on `$PATH`. Use `uv run apx bun install` or `uv run apx bun add <dep>` unless the user says otherwise.

---

## 4. Project structure

- **Full-stack:** `src/payment_analysis/ui/` (React + Vite), `src/payment_analysis/backend/` (FastAPI). Backend serves frontend at `/` and API at `/api`. API client is auto-generated from OpenAPI.
- **Routes:** `src/payment_analysis/ui/routes/` (TanStack Router). Backend routes: `src/payment_analysis/backend/routes/` (analytics, decision, dashboards, agents, rules, setup, experiments, incidents, notebooks).
- **Components:** `src/payment_analysis/ui/components/` (shadcn/ui). If a component was added to `src/components/`, move it to the correct folder under `src/payment_analysis/ui/components/`.

---

## 5. Models & API

- **3-model pattern:** `Entity` (DB), `EntityIn` (input), `EntityOut` (output).
- **Routes:** Must have `response_model` and `operation_id` for client generation.

---

## 6. Frontend rules

- **Data fetching:** Use `useXSuspense` hooks with `Suspense` and `Skeleton`. Render static content immediately; fetch API data with Suspense.
- **Data access:** Use `selector()` for clean destructuring (e.g. `const { data: profile } = useProfileSuspense(selector())`).

---

## 7. Development commands

| Purpose | Command |
|--------|---------|
| Check errors (TS + Python) | `uv run apx dev check` |
| Verify all (build, smoke, dashboards, bundle) | `./scripts/bundle.sh verify [dev\|prod]` |
| Build | `uv run apx build` |
| Deploy | `./scripts/bundle.sh deploy [dev\|prod]` |

**Before any `databricks bundle` command:** Ensure dashboards exist: `uv run python scripts/dashboards.py prepare` (optionally `--catalog` / `--schema` for prod). Otherwise: "failed to read serialized dashboard from file_path .build/dashboards/...."

**Redeploy (overwrite existing):** `./scripts/bundle.sh deploy dev` runs build, prepare, then `databricks bundle deploy -t dev --force --auto-approve`.

---

## 7b. Version alignment (from unified chats)

- **Exact versions everywhere:** All dependency references use the **same** versions (no `^` or `~`). Python: `pyproject.toml` (`==`) → `uv.lock` → `requirements.txt` via `scripts/sync_requirements_from_lock.py`. Frontend: `package.json` exact versions only → `bun.lock`. See `docs/DEPLOYMENT.md#version-alignment`.
- **Do not change dependency versions** unless the user explicitly instructs.
- **Databricks App compatibility:** Runtime Python 3.11, Node 22.16; versions in docs/DEPLOYMENT.md (Version alignment) are tested compatible.
- **After changing deps:** Python: `uv lock` then `uv run python scripts/sync_requirements_from_lock.py`. Frontend: `uv run apx bun install`.

---

## 8. MCP reference (apx)

| Tool | Description |
|------|-------------|
| `check` | Check project code (tsc + ty) |
| `refresh_openapi` | Regenerate OpenAPI schema and API client |
| `search_registry_components` | Search shadcn registry |
| `add_component` | Add shadcn component |
| `docs` | Search Databricks SDK docs |
| `databricks_apps_logs` | Fetch logs from deployed app |
| `get_route_info` | Code example for an API route |

---

## 9. AI agents in the solution

**Primary: ResponsesAgent** (`payment-response-agent`): MLflow ResponsesAgent (OpenAI Responses API) with 10 UC function tools + `python_exec`. Served on Databricks Model Serving. Uses Claude Sonnet 4.5 for multi-turn tool calling. Registered as `{catalog}.agents.payment_analysis_agent` by Job 6 task `register_responses_agent`.

**Fallback: Agent Framework** (`agent_framework.py`): Custom Python orchestrator + 5 specialists (Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender). Run by Job 6 task `run_agent_framework`. Used as Path 3 fallback when Model Serving and AI Gateway are unavailable.

**AI Chat 3-tier fallback:**
1. **Path 1** — ResponsesAgent (`payment-response-agent`) with 10 UC tools + python_exec
2. **Path 2** — AI Gateway (Claude Opus 4.6, `LLM_ENDPOINT`) for direct LLM reasoning
3. **Path 3** — Job 6 agent framework (custom Python orchestrator)

**In-app (UI):** **AI agents** page lists agents from `GET /api/agents/agents`. Types: Genie, Model Serving, Custom LLM, AI Gateway. Open in Databricks via `GET /api/agents/agents/{id}/url`. Genie chat is in Databricks (one-click from app).

**UC Tools:** 17 individual UC functions + 5 consolidated functions for the ResponsesAgent (fits Databricks 10-function limit: 5 consolidated + 5 operational = 10 total). Created by Job 3 from `uc_agent_tools.sql`.

**Registry (backend):** `src/payment_analysis/backend/routes/agents.py` — `AGENTS` list (Genie, Model Serving, AI Gateway, Custom) with metadata, example queries, workspace URLs. Catalog/schema from `app_config` when available.

**AI Chat in the app UI:** The floating dialog uses `POST /api/agents/orchestrator/chat`. Requirements:

1. **Job 6 deployed** — Bundle deploy creates "[${var.environment}] 6. Deploy Agents (Orchestrator & Specialists)" in the workspace. Task 2 registers the ResponsesAgent and deploys the `payment-response-agent` endpoint.
2. **`ORCHESTRATOR_SERVING_ENDPOINT`** — Set to `payment-response-agent` in `app.yml`.
3. **Open app from Compute → Apps** — So the platform forwards your token; the backend uses it for Model Serving queries.
4. **Optional:** Set `DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT` in the app environment to pin a specific job ID.

To verify: Open the app from Compute → Apps → payment-analysis, open the **AI Chatbot** floating dialog, send a message (e.g. "What are the top decline reasons?"). The ResponsesAgent uses UC tools to query live data and returns a data-driven response.

---

## 10. Common prompts and requests

When the user asks to:

- **Add a UI component** — Use MCP `search_registry_components` / `add_component` or `uv run apx components add <name> --yes`; place in `src/payment_analysis/ui/components/`.
- **Add or change an API route** — Use `response_model` and `operation_id`; run check after. Use `get_route_info` for examples.
- **Fix build or deploy** — Run `uv run apx dev check` and `./scripts/bundle.sh verify dev`; check dashboard prepare if bundle fails on dashboards.
- **Work with agents** — Backend: `backend/routes/agents.py` and `AGENTS`; framework: `agents/agent_framework.py` and `resources/agents.yml`.
- **Change catalog/schema** — Bundle uses `var.catalog` / `var.schema`; app uses Lakebase `app_config`; set via Setup & Run → Save catalog & schema.
- **Run jobs or pipelines** — From app Setup & Run; jobs 1–6 in order; pipelines (ETL, Real-Time) when needed.
- **Verify / version alignment / deploy** — Run `uv run apx dev check` and `./scripts/bundle.sh verify dev`; ensure exact dependency versions (see docs/DEPLOYMENT.md#version-alignment); commit and push to main; deploy with `./scripts/bundle.sh deploy dev` to overwrite existing resources.

---

## 11. Documentation map

| Doc | Purpose |
|-----|---------|
| `databricks.yml` | [Databricks Asset Bundles (DAB)](https://docs.databricks.com/aws/en/dev-tools/bundles/) root config; workspace, resources, sync, targets |
| `docs/INDEX.md` | Document map and quick reference |
| `docs/GUIDE.md` | Business overview, architecture, project structure, control panel & UI, best practices alignment |
| `docs/DEPLOYMENT.md` | Deploy steps, env vars, version alignment, troubleshooting |
| `docs/REFERENCE.md` | Databricks alignment, agent architecture, model serving, UC functions (17 individual + 5 consolidated), Vector Search |
| `docs/SCHEMA_TABLES_VIEWS.md` | Tables and views reference (required vs optional, where used, why empty) |
| `.cursor/rules/project.mdc` | Cursor rule set (aligns with this file) |

**External references (best practices):** [Apps Cookbook](https://apps-cookbook.dev/docs/intro) (FastAPI, healthcheck, tables), [apx](https://github.com/databricks-solutions/apx) (toolkit, build, OpenAPI), [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit) (Databricks SDK, MCP, skills).

---

**This agent represents the latest version of the Payment Analysis solution. All chat history, context, and prompts are unified here; all requests from different chats should be handled consistently. Verify that changes are applied on the main branch.**
