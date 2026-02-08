# Version alignment and Databricks App compatibility

All dependency references in this solution use **exactly the same versions** everywhere (no ranges). This document is the single reference for verified versions and Databricks App runtime compatibility.

---

## Runtime (Databricks App)

| Runtime | Version | Source |
|--------|---------|--------|
| **Python** | 3.11 | `.python-version`; `pyproject.toml` `requires-python = ">=3.11"`. Databricks App runs Python 3.11. |
| **Node.js** | ≥22.0.0 | `package.json` `engines.node`. Databricks App uses Node.js 22.16; local dev should use 22.x. |

These versions are supported and compatible with the Databricks App execution environment (Ubuntu 22.04 LTS, Python 3.11, Node 22.16).

---

## Python (backend and scripts)

**Source of truth:** `pyproject.toml` (all direct deps use `==`).  
**Lock:** `uv.lock`.  
**App deploy:** `requirements.txt` is generated from `uv.lock` by `scripts/sync_requirements_from_lock.py` (run after `uv lock`).

### Direct dependencies (exact versions)

| Package | Version | Notes |
|---------|---------|--------|
| databricks-sdk | 0.84.0 | Workspace, SQL, jobs, Lakebase |
| fastapi | 0.128.0 | Web framework |
| uvicorn | 0.40.0 | ASGI server |
| pydantic-settings | 2.6.1 | Config |
| sqlmodel | 0.0.27 | ORM / app DB |
| psycopg[binary,pool] | 3.2.3 | Postgres driver; `[binary]` for Databricks App (no system libpq) |

### Dev dependencies

| Package | Version |
|---------|---------|
| ty | 0.0.14 |
| apx | 0.2.6 |

### Transitive (in requirements.txt for Databricks App)

pydantic, pydantic-core, starlette, sqlalchemy, greenlet, annotated-types, typing-extensions, typing-inspection — versions are fixed in `uv.lock` and reflected in `requirements.txt` by the sync script.

**After changing `pyproject.toml`:** run `uv lock` then `uv run python scripts/sync_requirements_from_lock.py`.

---

## Frontend (UI)

**Source of truth:** `package.json` (all dependencies use exact versions, no `^` or `~`).  
**Lock:** `bun.lock`.

### Key dependencies (exact versions)

| Package | Version |
|---------|---------|
| react | 19.2.3 |
| react-dom | 19.2.3 |
| vite | 7.3.1 |
| @vitejs/plugin-react | 5.1.3 |
| @tanstack/react-query | 5.90.16 |
| @tanstack/react-router | 1.158.1 |
| @tanstack/react-router-devtools | 1.158.1 |
| @tanstack/router-plugin | 1.158.1 |
| @tailwindcss/vite | 4.1.18 |
| typescript | 5.9.3 |
| motion | 12.24.10 |
| lucide-react | 0.563.0 |
| react-error-boundary | 6.0.2 |
| sonner | 2.0.7 |
| @opentelemetry/api-logs | 0.211.0 |
| @opentelemetry/exporter-logs-otlp-http | 0.211.0 |
| @opentelemetry/resources | 2.5.0 |
| @opentelemetry/sdk-logs | 0.211.0 |
| @radix-ui/react-avatar | 1.1.11 |
| @radix-ui/react-dialog | 1.1.15 |
| @radix-ui/react-separator | 1.1.8 |
| @radix-ui/react-slot | 1.2.4 |
| @radix-ui/react-tooltip | 1.2.8 |
| @types/node | 25.0.3 |
| @types/react | 19.2.7 |
| @types/react-dom | 19.2.3 |
| class-variance-authority | 0.7.1 |
| clsx | 2.1.1 |
| tailwind-merge | 3.4.0 |
| tw-animate-css | 1.4.0 |

**After changing `package.json`:** run `uv run apx bun install` (or `bun install`) to refresh `bun.lock`.

---

## Verification

- **Python:** `pyproject.toml` (source of truth, all direct deps use `==`) → `uv lock` → `uv run python scripts/sync_requirements_from_lock.py` → `requirements.txt`. Same versions in all three.
- **Frontend:** `package.json` uses **exact versions only** (no `^` or `~`); `bun.lock` holds resolved versions. All dependency references match the table above.
- **Runtime:** `.python-version` = 3.11; `package.json` `engines.node` = `>=22.0.0`. Databricks App: Python 3.11, Node.js 22.16.
- **Check:** `uv run apx dev check` runs TypeScript and Python checks.

### Files that must stay aligned

| File | Role |
|------|------|
| `pyproject.toml` | Python direct deps (exact `==`); do not add ranges. |
| `uv.lock` | Resolved Python deps; run `uv lock` after changing pyproject.toml. |
| `requirements.txt` | Generated from uv.lock by `scripts/sync_requirements_from_lock.py`; do not edit by hand. |
| `package.json` | Frontend deps (exact versions only); run `uv run apx bun install` after changes. |
| `bun.lock` | Resolved frontend deps. |
| `.python-version` | 3.11 (matches Databricks App). |

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#app-configuration-and-resource-paths) for deployment and version update steps.
