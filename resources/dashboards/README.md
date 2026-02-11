# AI/BI Dashboard definitions (Lakeview / .lvdash.json)

Dashboard JSONs are prepared by `scripts/dashboards.py prepare` (catalog/schema substitution) and deployed via the bundle (`resources/dashboards.yml`). Each file follows the [dbdemos](https://github.com/databricks-demos/dbdemos) and [Apps Cookbook](https://apps-cookbook.dev/docs/intro) pattern:

- **datasets**: SQL queries against Unity Catalog views. Use placeholder `__CATALOG__.__SCHEMA__`; it is replaced with the target catalog and schema at prepare time.
- **pages**: Dashboard pages. Each page has a `name`, `displayName`, and **layout** (widgets linked to datasets).
- **Widgets and datasets**: Following the [dbdemos](https://github.com/databricks-demos/dbdemos/tree/main/dbdemos) / [aibi-marketing-campaign](https://github.com/databricks-demos/dbdemos-notebooks/tree/main/aibi/aibi-marketing-campaign/_resources/dashboards) example, every data widget in `layout` has `queries[].query.datasetName`, `query.fields`, `spec` (widgetType, encodings), and `position` (x, y, width, height). **Columns and values for widgets MUST exist in the dataset**: widget `query.fields` and `spec.encodings.columns` must only reference columns returned by that dataset’s SQL query. Run **`best-widgets`** to set the best widget type (counter/line/bar/pie/table) and dbdemos-style encodings per dataset. **Charts are preferred over plain tables**: time series → line, category + metric → bar or pie, single-row multi-KPI → table, single metric → counter. then **`fix-visualization-fields`** to set every table widget’s fields and columns from the dataset query; run `uv run python scripts/dashboards.py link-widgets` to add minimal table widgets for any dataset that has no widget; run `uv run python scripts/dashboards.py check-widgets` to verify structure and that widget fields exist in the dataset.

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

## Widget creation (dbdemos-style)

The [aibi-marketing-campaign dashboard](https://github.com/databricks-demos/dbdemos-notebooks/blob/main/aibi/aibi-marketing-campaign/_resources/dashboards/web-marketing.lvdash.json) defines widgets with **object encodings** and **scale types**. The `best-widgets` command aligns our dashboards with that pattern:

| Type | spec.version | query.fields | encodings | disaggregated |
|------|--------------|--------------|-----------|---------------|
| **counter** | 2 | One field: `{ "name": "col", "expression": "\`col\`" }` | `value: { fieldName, displayName }` | true |
| **line** | 3 | x + aggregated y: `SUM(\`y_col\`)` as `sum(y_col)` | `x: { fieldName, scale: { type: "temporal" }, displayName }`, `y: { fieldName: "sum(y_col)", scale: { type: "quantitative" }, displayName }` | false |
| **bar** | 3 | x + aggregated y: `SUM(\`y_col\`)` as `sum(y_col)` | `x: { fieldName, scale: { type: "categorical" }, displayName }`, `y: { fieldName: "sum(y_col)", scale: { type: "quantitative" }, displayName }` | false |
| **table** | 1 | All columns | `columns: [{ fieldName, displayName, visible, order, ... }]` | true |
| **pie** | 3 | category + metric | `angle: { fieldName: "sum(y)", scale: quantitative }`, `color: { fieldName: "x", scale: categorical }` | false |

Bar charts use `scale.sort: { "by": "y-reversed" }` for descending order. Only real time dimensions (`hour`, `date`, `day`, `period_start`, `event_timestamp`, `first_detected`) trigger line charts; single-row multi-column datasets use table so all KPIs are visible.

## Visualization catalog alignment (AI/BI)

Our widget choices follow the [AI/BI dashboard visualization types](https://learn.microsoft.com/en-us/azure/databricks/dashboards/visualization-types) ([Databricks](https://docs.databricks.com/en/dashboards/visualizations/types.html)) so the best option is used for each case:

| Official type | Best for (per docs) | Our use | Verified |
|---------------|---------------------|---------|----------|
| **Line** | Change in one or more metrics over time | Time series (approval trends, volume per second, bronze/silver hourly, daily trends, alerts over time) | ✓ |
| **Pie** | Proportionality between metrics; *not* for time series | Category distribution (solution, geography, decline reason, routing, segment, etc.) | ✓ |
| **Bar** | Change in metrics over time or across categories; proportionality | Category + metric when not using pie (sort by value descending) | ✓ |
| **Table** | Standard table; reorder, hide, format | Multi-column KPI rows (executive KPIs, last hour, quality summary), alert detail, multi-field datasets | ✓ |
| **Counter** | Single value prominently; optional comparison/sparkline | Single numeric KPI only (we prefer table when multiple KPIs in one row) | ✓ |
| **Area** | One or more groups’ numeric values over time (filled trend) | Time + volume/throughput (streaming ingestion, volume per second) | ✓ |
| **Choropleth** | Geographic localities colored by aggregate values | Country/region + value (global coverage, executive geography) | ✓ |
| **Funnel** | Metric at different *stages* (step + value) | Not used; we have category + metric (pie/bar). Funnel would fit stage-based flows. | — |
| **Heatmap** | Two categories + value as color intensity | Two dimensions + value (e.g. decline reason × merchant segment) | ✓ |
| **Scatter** | Relationship between two numerical variables | Two numeric columns (no time); applied when dataset has two numeric axes | ✓ |
| **Waterfall** | Cumulative effect of sequential +/- values (e.g. P&amp;L) | Not used; financial_impact uses table/pie. | — |

So for every dataset we use a type that matches the official “best for” guidance; **area** (time + volume), **choropleth** (country + value), and **heatmap** (two categories + value) are now applied where appropriate; run `uv run python scripts/dashboards.py best-widgets` to re-apply.

Chart widgets use **single objects** for `encodings.x` and `encodings.y` (not arrays). `spec.frame` can include `showTitle`, `title`, and `showDescription`. Validation (`check-widgets`) accepts aggregate field names like `sum(column_name)` as referring to the dataset column `column_name`.

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
