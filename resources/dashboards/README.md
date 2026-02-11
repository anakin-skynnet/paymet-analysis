# AI/BI Dashboard definitions (Lakeview / .lvdash.json)

Dashboard JSONs are prepared by `scripts/dashboards.py prepare` (catalog/schema substitution) and deployed via the bundle (`resources/dashboards.yml`). Each file follows the [dbdemos](https://github.com/databricks-demos/dbdemos) and [Apps Cookbook](https://apps-cookbook.dev/docs/intro) pattern:

- **datasets**: SQL queries against Unity Catalog views. Use placeholder `__CATALOG__.__SCHEMA__`; it is replaced with the target catalog and schema at prepare time.
- **pages**: Dashboard pages. Each page has a `name` and `displayName`.

## Making widgets show visual results

1. **Deploy** the bundle (including `resources/dashboards.yml`) so dashboards exist in the workspace.
2. **Open** the dashboard in Databricks (SQL → Dashboards, or from the app’s Dashboards page).
3. **Add visualizations**: On each page, use **Add visualization** (or **Add chart**), select one of the **datasets** (e.g. "Executive KPIs", "Approval Trends Hourly"), then choose the chart type (table, bar, line, etc.) and map columns. Save.
4. **Publish** for sharing/embed: run `uv run python scripts/dashboards.py publish` after deploy, or use the dashboard’s **Publish** action in the UI with **Share with data permissions** (embed credentials) so the app can embed the dashboard.

Once visualizations are added and linked to datasets, widgets will show interactive results. The Gold Views job must have been run in the same catalog/schema so the views exist.
