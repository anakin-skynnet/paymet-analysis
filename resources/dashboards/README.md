# AI/BI Dashboard definitions (Lakeview / .lvdash.json)

Dashboard JSONs are prepared by `scripts/dashboards.py prepare` (catalog/schema substitution) and deployed via the bundle (`resources/dashboards.yml`). Each file follows the [dbdemos](https://github.com/databricks-demos/dbdemos) and [Apps Cookbook](https://apps-cookbook.dev/docs/intro) pattern:

- **datasets**: SQL queries against Unity Catalog views. Use placeholder `__CATALOG__.__SCHEMA__`; it is replaced with the target catalog and schema at prepare time.
- **pages**: Dashboard pages. Each page has a `name`, `displayName`, and **layout** (widgets linked to datasets).
- **Widgets and datasets**: Following the [dbdemos](https://github.com/databricks-demos/dbdemos/tree/main/dbdemos) / [aibi-marketing-campaign](https://github.com/databricks-demos/dbdemos-notebooks/tree/main/aibi/aibi-marketing-campaign/_resources/dashboards) example, every data widget in `layout` has `queries[].query.datasetName`, `query.fields`, `spec` (widgetType, encodings), and `position` (x, y, width, height). **Columns and values for widgets MUST exist in the dataset**: widget `query.fields` and `spec.encodings.columns` must only reference columns returned by that dataset’s SQL query. Run `uv run python scripts/dashboards.py fix-visualization-fields` to set every table widget’s fields and columns from the dataset query; run `uv run python scripts/dashboards.py link-widgets` to add minimal table widgets for any dataset that has no widget; run `uv run python scripts/dashboards.py check-widgets` to verify structure and that widget fields exist in the dataset.

## Comparison with dbdemos

This project is configured in line with [dbdemos AI/BI](https://github.com/databricks-demos/dbdemos/blob/main/README_AIBI.md) and the same Lakeview schema used in [databricks/tmm](https://github.com/databricks/tmm/blob/main/System-Tables-Demo/Jobs-PrPr/Jobs%20System%20Tables%20Dashboard.lvdash.json):

| Aspect | dbdemos | This project |
|--------|---------|--------------|
| **JSON structure** | `datasets` (name, displayName, query) + `pages` (name, displayName, layout) | Same |
| **Dataset definition** | Single `query` string; catalog/schema match bundle config | Single `query` with `__CATALOG__.__SCHEMA__` placeholder (replaced at prepare) |
| **Widget → dataset** | Widgets reference datasets by name | Each data widget has `queries[].query.datasetName` pointing to a dataset in the same file |
| **Widget fields** | Query fields and encodings for visualizations | `query.fields` (name, expression) and `spec.encodings.columns` (fieldName, visible, etc.) so Lakeview has fields selected |
| **Validation** | — | `check-widgets`: every dataset has ≥1 widget; every widget has datasetName, fields, spec, position |
| **File location** | `_resources/dashboards/` or `_dashboards`, filename = bundle id | Source: `resources/dashboards/*.lvdash.json`; bundle uses `file_path: ./dashboards/<name>.lvdash.json` (prepare writes to repo root `dashboards/`) |

We do not use `queryLines` (API allows only one of `query` or `query_lines` per dataset). Table widgets have full column encodings so Lakeview does not show "Visualization has no fields selected."

## Making widgets show visual results

1. **Deploy** the bundle (including `resources/dashboards.yml`) so dashboards exist in the workspace.
2. Dashboards include a **layout** with one table widget per dataset (linked by `datasetName`). Open each dashboard in Databricks (SQL → Dashboards) to view data or add more visualizations (bar, line, counter) via **Add visualization** using the same datasets.
3. **Publish** for sharing/embed: run `uv run python scripts/dashboards.py publish` after deploy, or use the dashboard's **Publish** action in the UI with **Share with data permissions** (embed credentials) so the app can embed the dashboard.

The Gold Views job must have been run in the same catalog/schema so the views exist and widgets return data.

## "Visualization has no fields selected"

If the visualization editor opens with no fields selected (or you see that message):

1. **Existing table widgets** — Our dashboard JSON already has **Columns** set for every table (via `spec.encodings.columns`). Re-run `uv run python scripts/dashboards.py fix-visualization-fields`, then `prepare` and redeploy so the workspace gets the updated definitions.
2. **When adding a new visualization in the UI** — In the editor, drag fields from the left panel to:
   - **Columns** (for tables)
   - **X-axis** / **Y-axis** (for bar/line charts)
   - **Value** (for counters/pie charts)
   Then save. Examples: *"Show sales by region as a bar chart"*, *"Display total revenue as a counter"*, *"Create a line chart of daily transactions"*.
