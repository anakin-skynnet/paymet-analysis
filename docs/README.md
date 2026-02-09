# Documentation

Single entry point for Payment Analysis docs. The platform **accelerates approval rates** via smart retry, smart checkout, risk analysis, fraud detection, reason codes, routing optimization, and AI-backed decisioning.

---

## Logical grouping

### Business & impact

| Document | Purpose |
|----------|---------|
| **[OVERVIEW.md](OVERVIEW.md)** | **Business overview & impact on approval rates** — Goal, use cases (Smart Retry, Smart Checkout, Reason codes, Risk, Routing, Decisioning), technology map (how each technology accelerates approvals), high-level flow |

### Technical guideline

| Document | Purpose |
|----------|---------|
| **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)** | **Technical guideline** — Architecture, data flow, project structure, bundle resources, deployment summary, version alignment summary, best practices summary, verification commands |
| **[ARCHITECTURE_REFERENCE.md](ARCHITECTURE_REFERENCE.md)** | Data sources (UI ↔ backend ↔ Databricks), workspace ↔ UI mapping, Databricks App compliance checklist, catalog/schema |
| **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** | Deploy steps, app env vars, paths, troubleshooting, schema consistency |
| **[VERSION_ALIGNMENT.md](VERSION_ALIGNMENT.md)** | Pinned dependency versions and Databricks App compatibility |
| **[BEST_PRACTICES_ALIGNMENT.md](BEST_PRACTICES_ALIGNMENT.md)** | Alignment with Apps Cookbook, apx, and AI Dev Kit |

### Operational

| Document | Purpose |
|----------|---------|
| **[CONTROL_PANEL_UI.md](CONTROL_PANEL_UI.md)** | Setup & Run, dashboards, Genie, agents, ML, Lakebase data in the UI — what you get and how it works |

---

## Project structure (logical)

- **`src/payment_analysis/`** — App and bundle code  
  - **`backend/`** — FastAPI app, config, dependencies, routes (analytics, decision, dashboards, agents, rules, setup, experiments, incidents, notebooks), services, Lakebase config  
  - **`ui/`** — React app: routes, components, lib (API client)  
  - **`transform/`** — Lakehouse SQL, gold views, lakehouse bootstrap, prepare/publish dashboards  
  - **`streaming/`** — Bronze ingest, real-time pipeline, transaction simulator  
  - **`ml/`** — Model training  
  - **`agents/`** — Agent framework (orchestrator, specialists)  
  - **`genie/`** — Genie space sync  
  - **`vector_search/`** — Vector search index creation  
- **`resources/`** — Bundle YAML (unity_catalog, lakebase, pipelines, sql_warehouse, ml_jobs, agents, dashboards, fastapi_app)  
- **`scripts/`** — bundle.sh, dashboards.py, sync_requirements_from_lock.py  

See [ARCHITECTURE_REFERENCE.md](ARCHITECTURE_REFERENCE.md) and [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) for details.

---

## References

- [Databricks Apps Cookbook](https://apps-cookbook.dev/docs/intro) — FastAPI, Streamlit, Dash recipes for Databricks Apps  
- [apx](https://github.com/databricks-solutions/apx) — Toolkit for building Databricks Apps (React + FastAPI)  
- [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit) — Databricks SDK, MCP tools, and skills for AI-assisted development  
