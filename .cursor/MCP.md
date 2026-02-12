# MCP Tools — Payment Analysis

This project configures MCP (Model Context Protocol) servers in `.cursor/mcp.json`. All of them support the solution’s **backend services** and **Databricks** data flow.

## Configured servers

| Server      | Purpose | How it connects to the solution |
|------------|---------|----------------------------------|
| **apx**    | Databricks App toolkit | Runs in-repo: `check`, `refresh_openapi`, `search_registry_components`, `add_component`, **Databricks SDK `docs`**, `get_route_info`, `databricks_apps_logs`. Use for code quality, OpenAPI client, shadcn components, and Databricks API docs. |
| **shadcn** | shadcn/ui components | Browse and install components from the registry. Install target is `src/payment_analysis/ui/components/ui` (see root `components.json`). Keeps UI consistent and wired to backend data. |
| **playwright** | Browser automation | Take screenshots, run actions in a real browser. Use to verify frontend pages that consume `/api` and Databricks-served data. |
| **databricks** | Unity Catalog, SQL, jobs, workspace | Lists catalogs/schemas/tables, `execute_sql`, jobs (list/run/status), workspace files, clusters, DBFS, UC lineage. Use for **development-time** exploration and validation; the **app serves data** via FastAPI → Databricks, not via this MCP. |

## Data flow (backend ↔ Databricks)

- **App runtime:** The FastAPI backend (`src/payment_analysis/backend/`) calls Databricks (Unity Catalog, Lakehouse, Lakebase) and exposes REST APIs under `/api`. The React UI uses the generated API client and always fetches from these backend routes.
- **Databricks MCP:** Used by the **agent in Cursor** to explore UC metadata and run SQL (e.g. validate views, debug queries). It does **not** replace the app backend; it enriches development and troubleshooting.

## Optional: Databricks MCP credentials

The **databricks** server only works when these environment variables are set (e.g. in your shell or Cursor env). Do **not** put secrets in `mcp.json`; the config uses `${env:...}` interpolation.

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Workspace URL (e.g. `https://adb-xxxx.azuredatabricks.net` or `https://your-workspace.cloud.databricks.com`). |
| `DATABRICKS_TOKEN` | Personal access token or service principal token with UC and SQL warehouse access. |
| `DATABRICKS_WAREHOUSE_ID` | SQL warehouse ID (from SQL Warehouses in the workspace). Used for `execute_sql_query` and lineage. |

To use the Databricks MCP:

1. Set the variables (e.g. in `~/.zshrc` or Cursor’s env).
2. Restart Cursor or reload MCP servers.
3. Enable the **databricks** server in **Settings → Features → MCP**.

If these are not set, the databricks server may fail to start; the rest of the solution (apx, shadcn, playwright, and the app backend) does not depend on it.

## Enabling and using MCPs

1. **Cursor Settings → Features → MCP** — ensure each server you need is enabled (green).
2. Restart Cursor after editing `.cursor/mcp.json`.
3. In chat, the agent can use tools from enabled servers (e.g. “list UC schemas”, “add the table component”, “check the project”, “open the app in the browser”).
