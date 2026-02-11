# AI/BI Dashboard definitions (Lakeview / .lvdash.json)

Dashboard JSONs are prepared by `scripts/dashboards.py prepare` (catalog/schema substitution) and deployed via the bundle (`resources/dashboards.yml`). Each file follows the [dbdemos](https://github.com/databricks-demos/dbdemos) and [Apps Cookbook](https://apps-cookbook.dev/docs/intro) pattern:

- **datasets**: SQL queries against Unity Catalog views. Use placeholder `__CATALOG__.__SCHEMA__`; it is replaced with the target catalog and schema at prepare time.
- **pages**: Dashboard pages. Each page has a `name`, `displayName`, and **layout** (widgets linked to datasets).
- **Widgets and datasets**: Following the [dbdemos aibi-marketing-campaign](https://github.com/databricks-demos/dbdemos-notebooks/tree/main/aibi/aibi-marketing-campaign/_resources/dashboards) example, every widget in `layout` references a dataset via `query.datasetName` (the dataset's `name`). Run `uv run python scripts/dashboards.py link-widgets` to add minimal table widgets for any dataset that has no widget yet.

## Making widgets show visual results

1. **Deploy** the bundle (including `resources/dashboards.yml`) so dashboards exist in the workspace.
2. Dashboards include a **layout** with one table widget per dataset (linked by `datasetName`). Open each dashboard in Databricks (SQL → Dashboards) to view data or add more visualizations (bar, line, counter) via **Add visualization** using the same datasets.
3. **Publish** for sharing/embed: run `uv run python scripts/dashboards.py publish` after deploy, or use the dashboard's **Publish** action in the UI with **Share with data permissions** (embed credentials) so the app can embed the dashboard.

The Gold Views job must have been run in the same catalog/schema so the views exist and widgets return data.
