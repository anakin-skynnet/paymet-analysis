# Deep alignment: Cookbook, apx, AI Dev Kit

This document reviews how the Payment Analysis solution aligns with the three reference sources and with the rules defined in previous prompts (AGENTS.md, .cursor/rules, version alignment, structure).

**Reference URLs:**
- [Apps Cookbook (intro)](https://apps-cookbook.dev/docs/intro)
- [apx](https://github.com/databricks-solutions/apx)
- [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit)

---

## 1. Databricks Apps Cookbook

**What it defines:** FastAPI recipes for Databricks Apps: app structure, routes under `/api`, healthcheck at `/api/v1/healthcheck`, OAuth2/token auth via `/api` prefix, table reads, error handling.

### Compliance

| Cookbook requirement | Our implementation | Status |
|----------------------|---------------------|--------|
| API prefix `/api` for token-based auth | `api = APIRouter(prefix=_api_prefix)` with `_api_prefix = "/api"` from apx metadata | ✅ |
| Main entrypoint `app.py` | `src/payment_analysis/backend/app.py` — FastAPI app, lifespan, mounts | ✅ |
| Versioned routes e.g. `/api/v1/*` | `api.include_router(v1_router, prefix="/v1")` → `/api/v1/healthcheck`, `/api/v1/health/database` | ✅ |
| Healthcheck endpoint | `GET /api/v1/healthcheck` returning status + timestamp (Pydantic `HealthcheckOut`); docstring "Return the API status." | ✅ |
| Healthcheck returns status + timestamp | `HealthcheckOut(status="OK", timestamp=...)` | ✅ |
| Optional: DB health (error handling) | `GET /api/v1/health/database` — Lakebase connection health (`HealthDatabaseOut`) | ✅ |
| App config (e.g. app.yaml) | `app.yml` at root: uvicorn, `payment_analysis.backend.app:app`, host/port, PYTHONPATH, PGAPPNAME | ✅ |
| Dependencies (requirements.txt) | `requirements.txt` generated from `uv.lock` via `scripts/sync_requirements_from_lock.py`; used by bundle/app | ✅ |

**Conclusion:** The solution matches Cookbook FastAPI structure and healthcheck patterns. We go beyond the minimal Cookbook example by using Pydantic response models and `operation_id` on all routes (see apx below).

---

## 2. apx (Databricks Apps toolkit)

**What it defines:** CLI and tooling for building Databricks Apps — init, build, dev server, OpenAPI client generation, React + FastAPI, shadcn/ui, TanStack Router, Bun, uv; project layout and metadata in `pyproject.toml`.

### Compliance

| apx expectation | Our implementation | Status |
|-----------------|---------------------|--------|
| FastAPI + React full-stack | Backend: `src/payment_analysis/backend/` (FastAPI). Frontend: `src/payment_analysis/ui/` (React, Vite, TanStack Router) | ✅ |
| OpenAPI client generation | Build-time generation from OpenAPI schema; `response_model` and `operation_id` on every route for client generation | ✅ |
| `pyproject.toml` metadata | `[tool.apx.metadata]`: app-name, app-slug, app-entrypoint (`payment_analysis.backend.app:app`), api-prefix (`/api`), metadata-path | ✅ |
| UI root | `[tool.apx.ui]` root = `src/payment_analysis/ui` | ✅ |
| Build produces `__dist__` | `apx build` → `src/payment_analysis/__dist__`; bundle sync includes it | ✅ |
| Dev check (TypeScript + Python) | `uv run apx dev check` (tsc + ty) — used in rules and docs | ✅ |
| Bun for frontend | `uv run apx bun install` / `apx bun add`; package.json exact versions | ✅ |
| uv for Python | All Python commands use `uv` (never pip); `uv lock`, `uv run ...` | ✅ |
| Components: shadcn/ui | Components under `src/payment_analysis/ui/components/`; add via MCP or `uv run apx components add <name> --yes` | ✅ |

**Conclusion:** Project structure, metadata, build, and dev workflow follow apx. All API routes have `response_model` and `operation_id` as required for OpenAPI client generation (AGENTS.md / project.mdc).

---

## 3. AI Dev Kit

**What it defines:** Databricks patterns for AI-assisted development — skills, MCP tools, SDK usage, workspace-centric development; compatible with Cursor/Claude; Asset Bundles, MLflow, Model Serving, Apps, etc.

### Compliance

| AI Dev Kit area | Our implementation | Status |
|-----------------|---------------------|--------|
| Databricks SDK usage | Backend uses `databricks.sdk` (WorkspaceClient, SQL, jobs, serving, vector search); no guessing of API — use apx MCP `docs` per rules | ✅ |
| MCP / AI-friendly | AGENTS.md and project.mdc reference apx MCP (check, refresh_openapi, search_registry_components, add_component, docs, get_route_info, databricks_apps_logs) | ✅ |
| Asset Bundles | `databricks.yml` is the DAB root; includes workspace, sync, resources (UC, lakebase, pipelines, jobs, dashboards, app); docs reference DAB | ✅ |
| Apps as first-class | App defined in `resources/fastapi_app.yml`; runtime in `app.yml`; docs describe opening from Compute → Apps and token forwarding | ✅ |

**Conclusion:** We use the SDK correctly, document MCP usage, and deploy via DAB. No AI Dev Kit–specific code is required; alignment is through patterns and docs.

---

## 4. Previous prompts (unified rules)

These are codified in **AGENTS.md** and **.cursor/rules/project.mdc**.

| Rule | Verification |
|------|--------------|
| Single agent / unified context | AGENTS.md is the single source of truth; project.mdc points to it | ✅ |
| API: `response_model` and `operation_id` on every route | Grep: all backend route handlers have both (including healthcheck, decision ML, incidents tasks, experiments assignments, analytics) | ✅ |
| 3-model pattern (Entity, EntityIn, EntityOut) | Used in routes (e.g. Experiment/ExperimentIn, Incident/IncidentIn, ApprovalRuleOut, etc.) | ✅ |
| Frontend: useXSuspense, Suspense, Skeleton; selector() | Patterns used in UI routes; selector in `lib/selector.ts` | ✅ |
| Components under `src/payment_analysis/ui/components/` | All under that path; apx, layout, ui subdirs | ✅ |
| Exact dependency versions (no ^ or ~) | VERSION_ALIGNMENT.md; package.json exact; pyproject.toml `==`; no change unless user instructs | ✅ |
| Do not update deps unless instructed | Stated in AGENTS.md and project.mdc | ✅ |
| uv for Python, apx bun for frontend | All commands in docs use `uv run ...` and `uv run apx bun install` | ✅ |
| Check after changes | `uv run apx dev check` in rules and common prompts | ✅ |
| Naming: Dashboards (AI/BI), Lakeflow (not DLT in user-facing text) | Applied in docs and UI copy; `dlt` kept in code where required | ✅ |
| DAB referenced in config and docs | databricks.yml links to DAB docs; DEPLOYMENT_GUIDE, README reference DAB | ✅ |

---

## 5. Gaps and recommendations

- **None critical.** The solution is aligned with Cookbook (FastAPI + healthcheck), apx (structure, OpenAPI, build, check), and AI Dev Kit (SDK, MCP, DAB). Previous-prompt rules (versions, response_model/operation_id, frontend patterns, paths) are satisfied.

- **Optional:** Keep the three reference URLs in README and AGENTS.md (already present). When adding new routes or changing app structure, re-check this doc and the Cookbook/apx docs.

---

## 6. Quick reference

| Source | URL | Use when |
|--------|-----|----------|
| Apps Cookbook | https://apps-cookbook.dev/docs/intro | FastAPI layout, /api prefix, healthcheck, tables, error handling |
| apx | https://github.com/databricks-solutions/apx | Build, dev check, OpenAPI, components, project layout |
| AI Dev Kit | https://github.com/databricks-solutions/ai-dev-kit | Databricks SDK, MCP, skills, bundle-based Apps |
