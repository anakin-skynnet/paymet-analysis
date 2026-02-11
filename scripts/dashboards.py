#!/usr/bin/env python3
"""
Dashboard operations: prepare (for bundle), validate-assets (list dependencies), publish (after deploy).

Usage:
  uv run python scripts/dashboards.py prepare [--catalog X] [--schema Y]
  uv run python scripts/dashboards.py validate-assets [--catalog X] [--schema Y]
  uv run python scripts/dashboards.py publish [--path /Workspace/Users/.../payment-analysis] [--dry-run]

Prepare: copies dashboard JSONs to dashboards/ (workspace root) and gold_views.sql to .build/transform/ with catalog/schema.
Validate-assets: lists tables/views required by dashboards (no DB connection).
Publish: after deploy, publishes all 12 dashboards with embed credentials (Databricks CLI).

Dashboard JSONs (resources/dashboards/*.lvdash.json) follow dbdemos/cookbook pattern: each file has "datasets"
(SQL queries using __CATALOG__.__SCHEMA__) and "pages". Each page should have a "layout" with widgets that
reference datasets via query.datasetName (see dbdemos aibi-marketing-campaign). Use "link-widgets" to add
minimal table widgets linked to each dataset so visual components show data without manual "Add visualization".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Placeholder in source dashboard JSONs (resources/dashboards/*.lvdash.json); replaced with catalog.schema during prepare.
CATALOG_SCHEMA_PLACEHOLDER = "__CATALOG__.__SCHEMA__"
SOURCE_DIR = REPO_ROOT / "resources" / "dashboards"
# Bundle (resources/dashboards.yml) uses file_path: ./dashboards/<name>.lvdash.json (project root).
OUT_DIR = REPO_ROOT / "dashboards"
# Also write to .build/dashboards for any scripts that expect it.
BUILD_DASHBOARDS_DIR = REPO_ROOT / ".build" / "dashboards"
GOLD_VIEWS_SOURCE = REPO_ROOT / "src" / "payment_analysis" / "transform" / "gold_views.sql"
LAKEHOUSE_BOOTSTRAP_SOURCE = REPO_ROOT / "src" / "payment_analysis" / "transform" / "lakehouse_bootstrap.sql"
GOLD_VIEWS_OUT_DIR = REPO_ROOT / ".build" / "transform"

ASSETS = [
    ("v_executive_kpis", "gold_views.sql"),
    ("v_approval_trends_hourly", "gold_views.sql"),
    ("v_approval_trends_by_second", "gold_views.sql"),
    ("v_performance_by_geography", "gold_views.sql"),
    ("v_top_decline_reasons", "gold_views.sql"),
    ("v_decline_recovery_opportunities", "gold_views.sql"),
    ("v_last_hour_performance", "gold_views.sql"),
    ("v_active_alerts", "gold_views.sql"),
    ("v_solution_performance", "gold_views.sql"),
    ("v_card_network_performance", "gold_views.sql"),
    ("v_retry_performance", "Lakeflow pipeline (gold table)"),
    ("v_merchant_segment_performance", "gold_views.sql"),
    ("v_daily_trends", "gold_views.sql"),
    ("v_streaming_ingestion_hourly", "gold_views.sql"),
    ("v_streaming_ingestion_by_second", "gold_views.sql"),
    ("v_streaming_volume_per_second", "gold_views.sql"),
    ("v_silver_processed_hourly", "gold_views.sql"),
    ("v_silver_processed_by_second", "gold_views.sql"),
    ("v_data_quality_summary", "gold_views.sql"),
    ("v_uc_data_quality_metrics", "gold_views.sql"),
    ("payment_metrics", "gold_views.sql"),
    ("decline_metrics", "gold_views.sql"),
    ("merchant_metrics", "gold_views.sql"),
    ("payments_enriched_silver", "Lakeflow pipeline (silver table)"),
]
PUBLISH_TIMEOUT = 60


def _select_columns_from_query(query: str) -> list[str]:
    """Extract column names from a SQL query (SELECT col1, col2, ... FROM ...). Simple parser."""
    if not query or not query.strip():
        return []
    # Match SELECT ... FROM (case-insensitive, allow newlines)
    m = re.search(r"\bSELECT\s+(.+?)\s+FROM\s+", query, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    select_part = m.group(1).strip()
    # Split by comma, but avoid splitting inside parens (e.g. func(a,b))
    parts: list[str] = []
    depth = 0
    start = 0
    for i, c in enumerate(select_part):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(select_part[start:i].strip())
            start = i + 1
    if start < len(select_part):
        parts.append(select_part[start:].strip())
    # Take last identifier (e.g. "col" or "t.col AS alias" -> use alias or col)
    columns: list[str] = []
    for p in parts:
        if not p or p.upper() == "*":
            continue
        # "expr AS alias" or "alias" or "table.col"
        if " AS " in p.upper():
            alias = p.upper().split(" AS ", 1)[1].strip().strip("`\"'")
            columns.append(alias)
        else:
            name = p.split()[-1].strip("`\"'") if p.split() else p.strip("`\"'")
            columns.append(name)
    return columns[:20]  # limit columns for table widget


def _make_table_widget(dataset_name: str, columns: list[str], x: int, y: int, width: int = 6, height: int = 4) -> dict:
    """Build a minimal table widget linked to the dataset (dbdemos pattern)."""
    widget_id = str(uuid.uuid4()).replace("-", "")[:12]
    # Lakeview requires at least one selected field; "*" is not a valid field name.
    if not columns or (len(columns) == 1 and columns[0] == "*"):
        columns = ["value"]  # fallback so widget has a field; user can change in UI if needed
    fields = [{"name": c, "expression": f"`{c}`"} for c in columns]
    return {
        "widget": {
            "name": widget_id,
            "queries": [
                {
                    "name": "main_query",
                    "query": {
                        "datasetName": dataset_name,
                        "fields": fields,
                        "disaggregated": True,
                    },
                }
            ],
            "spec": {
                "version": 1,
                "widgetType": "table",
                "encodings": {
                    "columns": [
                        {
                            "name": c,
                            "fieldName": c,
                            "displayName": c,
                            "title": c,
                            "booleanValues": ["false", "true"],
                            "imageUrlTemplate": "{{ @ }}",
                            "imageTitleTemplate": "{{ @ }}",
                            "imageWidth": "",
                            "imageHeight": "",
                            "linkUrlTemplate": "{{ @ }}",
                            "linkTextTemplate": "{{ @ }}",
                            "linkTitleTemplate": "{{ @ }}",
                            "linkOpenInNewTab": True,
                            "type": "string",
                            "displayAs": "string",
                            "visible": True,
                            "order": i,
                            "allowSearch": True,
                            "alignContent": "left",
                            "allowHTML": False,
                            "highlightLinks": False,
                            "useMonospaceFont": False,
                            "preserveWhitespace": False,
                        }
                        for i, c in enumerate(columns)
                    ]
                },
                "frame": {"showTitle": True, "title": dataset_name, "showDescription": False},
            },
        },
        "position": {"x": x, "y": y, "width": width, "height": height},
    }


def cmd_check_widgets() -> int:
    """Verify dashboard structure and widget settings per dbdemos pattern (see README and dbdemos/installer_dashboard)."""
    errors: list[str] = []
    for path in sorted(SOURCE_DIR.glob("*.lvdash.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: invalid JSON — {e}")
            continue
        # --- Datasets (dbdemos: name, displayName, query or queryLines) ---
        datasets = data.get("datasets", [])
        dataset_names = set()
        for i, ds in enumerate(datasets):
            name = ds.get("name")
            if not name:
                errors.append(f"{path.name}: dataset[{i}] missing 'name'")
                continue
            dataset_names.add(name)
            if not ds.get("displayName"):
                errors.append(f"{path.name}: dataset '{name}' missing 'displayName'")
            if not ds.get("query") and not ds.get("queryLines"):
                errors.append(f"{path.name}: dataset '{name}' missing 'query' or 'queryLines'")
        # --- Pages and layout ---
        datasets_by_name = {ds.get("name"): ds for ds in datasets if ds.get("name")}
        pages = data.get("pages", [])
        if not pages:
            errors.append(f"{path.name}: no 'pages' defined")
        referenced: set[str] = set()
        for pidx, page in enumerate(pages):
            if not page.get("name"):
                errors.append(f"{path.name}: page[{pidx}] missing 'name'")
            if not page.get("displayName"):
                errors.append(f"{path.name}: page[{pidx}] missing 'displayName'")
            layout = page.get("layout", [])
            if not layout:
                errors.append(f"{path.name}: page[{pidx}] has no 'layout'")
            for lidx, item in enumerate(layout):
                widget = item.get("widget")
                pos = item.get("position")
                if not widget:
                    errors.append(f"{path.name}: page[{pidx}] layout[{lidx}] missing 'widget'")
                    continue
                if not pos:
                    errors.append(f"{path.name}: page[{pidx}] layout[{lidx}] widget missing 'position'")
                else:
                    for key in ("x", "y", "width", "height"):
                        if key not in pos:
                            errors.append(f"{path.name}: page[{pidx}] layout[{lidx}] position missing '{key}'")
                # Data widget: must have queries with query.datasetName and query.fields, and spec
                queries = widget.get("queries", [])
                if queries:
                    for qidx, q in enumerate(queries):
                        query = q.get("query", {})
                        dn = query.get("datasetName")
                        if not dn:
                            errors.append(f"{path.name}: page[{pidx}] layout[{lidx}] queries[{qidx}] missing 'query.datasetName'")
                        else:
                            referenced.add(dn)
                            if dn not in dataset_names:
                                errors.append(f"{path.name}: widget references unknown dataset '{dn}'")
                            else:
                                # Columns and values MUST exist in the dataset (allow aggregate names like sum(col) → col)
                                ds = datasets_by_name.get(dn)
                                if ds:
                                    ds_columns = set(_select_columns_from_query(_get_dataset_query(ds)))
                                    widget_fields = [f.get("name") for f in query.get("fields", []) if f.get("name")]
                                    if ds_columns and widget_fields:
                                        def _base_column(f: str) -> str:
                                            m = re.match(r"(sum|avg|count|min|max)\s*\(\s*([^)]+)\s*\)", f, re.IGNORECASE)
                                            return m.group(2).strip("` ") if m else f
                                        missing_in_ds = [f for f in widget_fields if _base_column(f) not in ds_columns]
                                        if missing_in_ds:
                                            errors.append(
                                                f"{path.name}: page[{pidx}] layout[{lidx}] widget fields not in dataset '{dn}': {missing_in_ds}"
                                            )
                        if "fields" not in query or not query["fields"]:
                            errors.append(f"{path.name}: page[{pidx}] layout[{lidx}] queries[{qidx}] missing or empty 'query.fields'")
                    spec = widget.get("spec", {})
                    if not spec:
                        errors.append(f"{path.name}: page[{pidx}] layout[{lidx}] data widget missing 'spec'")
                    else:
                        if not spec.get("widgetType"):
                            errors.append(f"{path.name}: page[{pidx}] layout[{lidx}] spec missing 'widgetType'")
                        if spec.get("widgetType") == "table" and "encodings" in spec and "columns" not in spec["encodings"]:
                            errors.append(f"{path.name}: page[{pidx}] layout[{lidx}] table widget spec.encodings missing 'columns'")
        missing = dataset_names - referenced
        if missing:
            errors.append(f"{path.name}: dataset(s) with no widget: {', '.join(sorted(missing))}")
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("All dashboards match dbdemos pattern: datasets defined, widgets have datasetName/fields/spec/position.")
    return 0


def _strip_optional_widget_spec_keys(data: dict) -> None:
    """Remove optional/unnecessary keys from widget specs (e.g. widgetHeaderAlignment when ALIGNMENT_UNSPECIFIED)."""
    for page in data.get("pages", []):
        for item in page.get("layout", []):
            spec = (item.get("widget") or {}).get("spec")
            if isinstance(spec, dict) and spec.get("widgetHeaderAlignment") == "ALIGNMENT_UNSPECIFIED":
                spec.pop("widgetHeaderAlignment", None)


def _table_column_spec(field_name: str, order: int) -> dict:
    """Single column encoding for a table widget so Lakeview has fields selected."""
    return {
        "name": field_name,
        "fieldName": field_name,
        "displayName": field_name,
        "title": field_name,
        "order": order,
        "visible": True,
        "type": "string",
        "displayAs": "string",
        "allowSearch": True,
        "alignContent": "left",
        "allowHTML": False,
        "highlightLinks": False,
        "useMonospaceFont": False,
        "preserveWhitespace": False,
        "booleanValues": ["false", "true"],
        "imageUrlTemplate": "{{ @ }}",
        "imageTitleTemplate": "{{ @ }}",
        "imageWidth": "",
        "imageHeight": "",
        "linkUrlTemplate": "{{ @ }}",
        "linkTextTemplate": "{{ @ }}",
        "linkTitleTemplate": "{{ @ }}",
        "linkOpenInNewTab": True,
    }


def _dataset_by_name(data: dict, name: str) -> dict | None:
    """Return the dataset with the given name, or None."""
    for ds in data.get("datasets", []):
        if ds.get("name") == name:
            return ds
    return None


def _get_dataset_query(dataset: dict) -> str:
    """Return the dataset SQL query string from 'query' or from 'queryLines' joined (for source JSONs that use queryLines)."""
    q = dataset.get("query")
    if q and isinstance(q, str) and q.strip():
        return q.strip()
    lines = dataset.get("queryLines")
    if isinstance(lines, list) and lines:
        return " ".join(str(l).strip() for l in lines if l).strip()
    return ""


# Names that suggest a numeric value column for charts (Y-axis or value). Match whole-word or trailing _count/_value/ etc. so "country" doesn't match but "decline_count" does.
_NUMERIC_LIKE = re.compile(
    r"(?:\b|_)(count|pct|rate|value|amount|score|ms|cost|total|avg|sum|volume|records_per|transactions?|approved|declined)(?:\b|_|$)",
    re.IGNORECASE,
)
# Only these column names are treated as time dimensions (line/area chart X-axis). Avoid false matches like "transactions_last_hour".
_TIME_DIMENSION_NAMES = frozenset(("hour", "date", "day", "period_start", "event_timestamp", "event_second", "first_detected"))
# Geographic columns for choropleth (map): country/region by name.
_GEOGRAPHIC_COLUMNS = frozenset(("country", "region", "state", "nation"))
# Categorical columns that work well for bar/pie (category + metric).
_CATEGORICAL_LIKE = re.compile(
    r"reason|country|solution|network|segment|type|severity|template|source|device|alert|metric"
)
# Few-category columns: part-of-whole (pie). Many-category or ranking → bar.
_PIE_FRIENDLY_CATEGORIES = frozenset(("payment_solution", "card_network", "merchant_segment", "alert_type", "severity"))


def _display_name(col: str) -> str:
    """Human-readable display name for a column (dbdemos style)."""
    return col.replace("_", " ").title()


def _recommend_widget_type(columns: list[str], query: str) -> tuple[str, list[str], dict]:
    """Recommend best chart/widget type from dataset columns (BI expert guide).
    Mapping: Comparison/rankings → bar; Trends over time → line or area (area for volume/throughput);
    Proportions (part-of-whole, few slices) → pie; Two numeric vars → scatter; Two categories + value → heatmap;
    Geography + value → choropleth; Single KPI → counter; Multi-column detail → table.
    See resources/dashboards/README.md and Databricks visualization types. Returns (widget_type, fields, encodings)."""
    if not columns:
        return "table", [], {"columns": []}
    q_lower = (query or "").lower()
    has_limit_1 = bool(re.search(r"\blimit\s+1\b", q_lower))  # exact "LIMIT 1", not "LIMIT 168"
    # Single numeric KPI only → counter
    if len(columns) == 1 and (_NUMERIC_LIKE.search(columns[0]) or has_limit_1):
        c = columns[0]
        return "counter", [c], {"value": {"fieldName": c, "displayName": _display_name(c)}}
    # Single-row (LIMIT 1) with multiple columns → table so all KPIs visible (not one counter)
    if has_limit_1 and len(columns) > 2:
        fields = columns
        return "table", fields, {"columns": [_table_column_spec(c, i) for i, c in enumerate(columns)]}
    if has_limit_1 and len(columns) >= 1 and any(_NUMERIC_LIKE.search(c) for c in columns):
        c = next((x for x in columns if _NUMERIC_LIKE.search(x)), columns[0])
        return "counter", [c], {"value": {"fieldName": c, "displayName": _display_name(c)}}
    # Geography (country/region) + value → choropleth (best for world/country maps)
    first_lower = columns[0].lower()
    if first_lower in _GEOGRAPHIC_COLUMNS and len(columns) >= 2:
        geo_col = columns[0]
        value_col = next((c for c in columns[1:] if _NUMERIC_LIKE.search(c)), columns[1])
        fields = [geo_col, value_col]
        encodings = {
            "region": {"fieldName": geo_col, "displayName": _display_name(geo_col)},
            "color": {"fieldName": f"sum({value_col})", "scale": {"type": "quantitative"}, "displayName": _display_name(value_col)},
        }
        return "choropleth", fields, encodings
    # Time series → line or area (area for volume/throughput)
    time_cols = [c for c in columns if c in _TIME_DIMENSION_NAMES]
    if time_cols and len(columns) >= 2:
        x_col = time_cols[0]
        rest = [c for c in columns if c != x_col]
        y_col = next((c for c in rest if _NUMERIC_LIKE.search(c)), rest[0] if rest else columns[0])
        fields = [x_col, y_col]
        x_display, y_display = _display_name(x_col), _display_name(y_col)
        encodings = {
            "x": {"fieldName": x_col, "scale": {"type": "temporal"}, "displayName": x_display, "axis": {"title": x_display}},
            "y": {"fieldName": f"sum({y_col})", "scale": {"type": "quantitative"}, "displayName": y_display, "axis": {"title": y_display}},
        }
        use_area = bool(re.search(r"records_per_second|record_count|volume", y_col, re.IGNORECASE))
        return "area" if use_area else "line", fields, encodings
    # Two numeric columns (no time) → scatter
    if len(columns) >= 2 and not time_cols:
        first_numeric = _NUMERIC_LIKE.search(columns[0])
        second_numeric = _NUMERIC_LIKE.search(columns[1]) if len(columns) > 1 else None
        if first_numeric and second_numeric and columns[0] != columns[1]:
            x_col, y_col = columns[0], columns[1]
            fields = [x_col, y_col]
            encodings = {
                "x": {"fieldName": x_col, "scale": {"type": "quantitative"}, "displayName": _display_name(x_col), "axis": {"title": _display_name(x_col)}},
                "y": {"fieldName": y_col, "scale": {"type": "quantitative"}, "displayName": _display_name(y_col), "axis": {"title": _display_name(y_col)}},
            }
            return "scatter", fields, encodings
    # Two categorical + value → heatmap
    if len(columns) >= 3 and not has_limit_1:
        cat1 = columns[0].lower() in ("decline_reason", "merchant_segment", "card_network", "payment_solution", "country", "alert_type") or _CATEGORICAL_LIKE.search(columns[0])
        cat2 = columns[1].lower() in ("merchant_segment", "card_network", "decline_reason") or _CATEGORICAL_LIKE.search(columns[1])
        val_col = next((c for c in columns[2:] if _NUMERIC_LIKE.search(c)), None)
        if cat1 and cat2 and val_col:
            fields = [columns[0], columns[1], val_col]
            encodings = {
                "x": {"fieldName": columns[0], "scale": {"type": "categorical"}, "displayName": _display_name(columns[0]), "axis": {"title": _display_name(columns[0])}},
                "y": {"fieldName": columns[1], "scale": {"type": "categorical"}, "displayName": _display_name(columns[1]), "axis": {"title": _display_name(columns[1])}},
                "color": {"fieldName": f"sum({val_col})", "scale": {"type": "quantitative"}, "displayName": _display_name(val_col)},
            }
            return "heatmap", fields, encodings
    # Categorical + numeric → bar or pie (only when first column is clearly categorical, not a metric)
    if not has_limit_1 and len(columns) >= 2:
        first, second = columns[0], columns[1]
        first_looks_numeric = _NUMERIC_LIKE.search(first)  # e.g. transactions_last_hour, approval_rate_pct
        first_cat = not first_looks_numeric and (
            first.lower() in (
                "decline_reason", "country", "payment_solution", "card_network", "merchant_segment",
                "segment", "alert_type", "severity", "metric_name", "template", "source", "device",
            )
            or _CATEGORICAL_LIKE.search(first)
        )
        if ( _NUMERIC_LIKE.search(second) or first_cat ) and first_cat:
            x_col = first
            y_col = next((c for c in columns[1:] if _NUMERIC_LIKE.search(c)), second)
            fields = [x_col, y_col]
            # Pie for part-of-whole (few categories); bar for many categories / ranking
            use_pie = first.lower() in _PIE_FRIENDLY_CATEGORIES
            if use_pie:
                x_display, y_display = _display_name(x_col), _display_name(y_col)
                encodings = {
                    "angle": {"fieldName": f"sum({y_col})", "scale": {"type": "quantitative"}, "displayName": y_display},
                    "color": {"fieldName": x_col, "scale": {"type": "categorical"}, "displayName": x_display, "legend": {"position": "bottom", "hideTitle": False}},
                }
                return "pie", fields, encodings
            x_display, y_display = _display_name(x_col), _display_name(y_col)
            encodings = {
                "x": {
                    "fieldName": x_col,
                    "scale": {"type": "categorical", "sort": {"by": "y-reversed"}},
                    "displayName": x_display,
                    "axis": {"title": x_display},
                },
                "y": {"fieldName": f"sum({y_col})", "scale": {"type": "quantitative"}, "displayName": y_display, "axis": {"title": y_display}},
            }
            return "bar", fields, encodings
    # Default: table
    fields = columns
    encodings = {"columns": [_table_column_spec(c, i) for i, c in enumerate(columns)]}
    return "table", fields, encodings


def cmd_best_widgets() -> int:
    """Set each widget to the best type (line/bar/table) and configure encodings from dataset columns."""
    updated = 0
    for path in sorted(SOURCE_DIR.glob("*.lvdash.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error reading {path}: {e}", file=sys.stderr)
            return 1
        _strip_optional_widget_spec_keys(data)
        datasets_by_name = {ds.get("name"): ds for ds in data.get("datasets", []) if ds.get("name")}
        changed = False
        for page in data.get("pages", []):
            for item in page.get("layout", []):
                w = item.get("widget", {})
                queries = w.get("queries", [])
                main_query = next((q.get("query", {}) for q in queries if q.get("query", {}).get("datasetName")), None)
                if not main_query:
                    continue
                dataset_name = main_query.get("datasetName")
                dataset = datasets_by_name.get(dataset_name)
                if not dataset:
                    continue
                ds_query = _get_dataset_query(dataset)
                columns = _select_columns_from_query(ds_query)
                if not columns:
                    existing = [f.get("name") for f in main_query.get("fields", []) if f.get("name")]
                    columns = existing or [dataset.get("displayName", dataset_name)]
                widget_type, fields, encodings = _recommend_widget_type(columns, ds_query)
                # Build query.fields and disaggregated per widget type
                if widget_type == "counter":
                    new_fields = [{"name": fields[0], "expression": f"`{fields[0]}`"}]
                    main_query["disaggregated"] = True
                elif widget_type in ("line", "bar", "pie", "area"):
                    x_col, y_col = fields[0], fields[1]
                    new_fields = [
                        {"name": x_col, "expression": f"`{x_col}`"},
                        {"name": f"sum({y_col})", "expression": f"SUM(`{y_col}`)"},
                    ]
                    main_query["disaggregated"] = False
                elif widget_type == "choropleth":
                    geo_col, value_col = fields[0], fields[1]
                    new_fields = [
                        {"name": geo_col, "expression": f"`{geo_col}`"},
                        {"name": f"sum({value_col})", "expression": f"SUM(`{value_col}`)"},
                    ]
                    main_query["disaggregated"] = False
                elif widget_type == "scatter":
                    new_fields = [{"name": f, "expression": f"`{f}`"} for f in fields]
                    main_query["disaggregated"] = True
                elif widget_type == "heatmap":
                    x_col, y_col, val_col = fields[0], fields[1], fields[2]
                    new_fields = [
                        {"name": x_col, "expression": f"`{x_col}`"},
                        {"name": y_col, "expression": f"`{y_col}`"},
                        {"name": f"sum({val_col})", "expression": f"SUM(`{val_col}`)"},
                    ]
                    main_query["disaggregated"] = False
                else:
                    new_fields = [{"name": f, "expression": f"`{f}`"} for f in fields]
                if main_query.get("fields") != new_fields:
                    main_query["fields"] = new_fields
                    changed = True
                spec = w.get("spec", {})
                if spec.get("widgetType") != widget_type:
                    spec["widgetType"] = widget_type
                    changed = True
                # version 2 for counter, 3 for chart types (line/bar/pie/area/choropleth/scatter/heatmap)
                chart_types = ("line", "bar", "pie", "area", "choropleth", "scatter", "heatmap")
                want_version = 2 if widget_type == "counter" else (3 if widget_type in chart_types else 1)
                if spec.get("version") != want_version:
                    spec["version"] = want_version
                    changed = True
                enc = spec.get("encodings") or {}
                if spec.get("encodings") is None:
                    spec["encodings"] = enc
                if widget_type == "table":
                    want_cols = encodings.get("columns", [])
                    existing_names = [c.get("fieldName") or c.get("name") for c in (enc.get("columns") or [])]
                    want_names = [c.get("fieldName") or c.get("name") for c in want_cols]
                    if existing_names != want_names:
                        enc["columns"] = want_cols
                        changed = True
                    if "x" in enc or "y" in enc or "value" in enc:
                        enc.pop("x", None)
                        enc.pop("y", None)
                        enc.pop("value", None)
                        changed = True
                elif widget_type == "counter":
                    want_value = encodings.get("value", {})
                    if enc.get("value") != want_value:
                        enc["value"] = want_value
                        changed = True
                    if "x" in enc or "y" in enc or "angle" in enc or "color" in enc or "columns" in enc:
                        enc.pop("x", None)
                        enc.pop("y", None)
                        enc.pop("angle", None)
                        enc.pop("color", None)
                        enc.pop("columns", None)
                        changed = True
                elif widget_type == "pie":
                    if enc.get("angle") != encodings.get("angle") or enc.get("color") != encodings.get("color"):
                        enc["angle"] = encodings.get("angle")
                        enc["color"] = encodings.get("color")
                        changed = True
                    enc.pop("x", None)
                    enc.pop("y", None)
                    enc.pop("value", None)
                    enc.pop("region", None)
                    if "columns" in enc:
                        del enc["columns"]
                        changed = True
                elif widget_type == "choropleth":
                    if enc.get("region") != encodings.get("region") or enc.get("color") != encodings.get("color"):
                        enc["region"] = encodings.get("region")
                        enc["color"] = encodings.get("color")
                        changed = True
                    for k in ("x", "y", "value", "angle", "columns"):
                        enc.pop(k, None)
                elif widget_type == "heatmap":
                    if enc.get("x") != encodings.get("x") or enc.get("y") != encodings.get("y") or enc.get("color") != encodings.get("color"):
                        enc["x"] = encodings.get("x")
                        enc["y"] = encodings.get("y")
                        enc["color"] = encodings.get("color")
                        changed = True
                    enc.pop("value", None)
                    enc.pop("angle", None)
                    enc.pop("region", None)
                    if "columns" in enc:
                        del enc["columns"]
                        changed = True
                else:
                    # line/bar/area/scatter: x and y encodings
                    if enc.get("x") != encodings.get("x") or enc.get("y") != encodings.get("y"):
                        enc["x"] = encodings.get("x")
                        enc["y"] = encodings.get("y")
                        changed = True
                    enc.pop("value", None)
                    enc.pop("angle", None)
                    enc.pop("region", None)
                    enc.pop("color", None)
                    if "columns" in enc:
                        del enc["columns"]
                        changed = True
                # Frame: show title from dataset displayName (per MS Learn dashboard visualizations)
                frame = spec.get("frame") or {}
                want_title = dataset.get("displayName", dataset_name) if dataset else dataset_name
                if frame.get("title") != want_title or frame.get("showTitle") is not True:
                    frame["showTitle"] = True
                    frame["title"] = want_title
                    frame["showDescription"] = frame.get("showDescription", False)
                    spec["frame"] = frame
                    changed = True
        if changed:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Best widgets: {path.name}")
            updated += 1
    print(f"Updated {updated} dashboard(s) with best widget type and required columns.")
    return 0


def cmd_fix_widget_settings() -> int:
    """Apply missing Databricks visualization settings: frame title from displayName, axis titles (line/bar), legend (pie)."""
    updated = 0
    for path in sorted(SOURCE_DIR.glob("*.lvdash.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error reading {path}: {e}", file=sys.stderr)
            return 1
        _strip_optional_widget_spec_keys(data)
        datasets_by_name = {ds.get("name"): ds for ds in data.get("datasets", []) if ds.get("name")}
        changed = False
        for page in data.get("pages", []):
            for item in page.get("layout", []):
                w = item.get("widget", {})
                queries = w.get("queries", [])
                main_query = next((q.get("query", {}) for q in queries if q.get("query", {}).get("datasetName")), None)
                if not main_query:
                    continue
                dataset_name = main_query.get("datasetName")
                dataset = datasets_by_name.get(dataset_name)
                display_title = (dataset.get("displayName", dataset_name) if dataset else dataset_name)
                spec = w.get("spec", {})
                # Frame: title from displayName, showTitle true (per MS Learn)
                frame = spec.get("frame") or {}
                if frame.get("title") != display_title or frame.get("showTitle") is not True:
                    frame["showTitle"] = True
                    frame["title"] = display_title
                    frame.setdefault("showDescription", False)
                    spec["frame"] = frame
                    changed = True
                enc = spec.get("encodings") or {}
                wt = spec.get("widgetType")
                if wt in ("line", "bar"):
                    for key in ("x", "y"):
                        e = enc.get(key)
                        if not e:
                            continue
                        display_name = e.get("displayName") or e.get("fieldName") or key
                        if not e.get("axis") or e.get("axis", {}).get("title") != display_name:
                            e["axis"] = e.get("axis") or {}
                            e["axis"]["title"] = display_name
                            changed = True
                elif wt == "pie":
                    color_enc = enc.get("color")
                    if color_enc and not color_enc.get("legend"):
                        color_enc["legend"] = {"position": "bottom", "hideTitle": False}
                        changed = True
        if changed:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Fixed widget settings: {path.name}")
            updated += 1
    print(f"Updated {updated} dashboard(s) with widget settings (frame, axis, legend).")
    return 0


def cmd_fix_visualization_fields() -> int:
    """Ensure widget columns and values exist: derive query.fields and spec.encodings.columns from the dataset query."""
    fixed = 0
    for path in sorted(SOURCE_DIR.glob("*.lvdash.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error reading {path}: {e}", file=sys.stderr)
            return 1
        _strip_optional_widget_spec_keys(data)
        datasets_by_name = {ds.get("name"): ds for ds in data.get("datasets", []) if ds.get("name")}
        changed = False
        # Remove queryLines if present (API allows only one of query or query_lines per dataset)
        for ds in data.get("datasets", []):
            if "queryLines" in ds:
                del ds["queryLines"]
                changed = True
        # Table widgets: set query.fields and encodings.columns from the dataset query so columns/values exist
        for page in data.get("pages", []):
            for item in page.get("layout", []):
                w = item.get("widget", {})
                spec = w.get("spec", {})
                if spec.get("widgetType") != "table":
                    continue
                queries = w.get("queries", [])
                main_query = next((q.get("query", {}) for q in queries if q.get("query", {}).get("datasetName")), None)
                if not main_query:
                    continue
                dataset_name = main_query.get("datasetName")
                dataset = _dataset_by_name(data, dataset_name) if dataset_name else None
                if not dataset:
                    continue
                ds_query = _get_dataset_query(dataset)
                field_names = _select_columns_from_query(ds_query)
                if not field_names:
                    # SELECT * or unparseable: keep existing fields if present, else fallback
                    existing_fields = main_query.get("fields", [])
                    field_names = [f.get("name") for f in existing_fields if f.get("name")]
                    if not field_names:
                        field_names = [dataset.get("displayName", dataset_name or "value")]
                # Ensure query.fields and spec.encodings.columns use only these columns (they exist in the dataset)
                new_fields = [{"name": n, "expression": f"`{n}`"} for n in field_names]
                new_cols = [_table_column_spec(n, i) for i, n in enumerate(field_names)]
                if main_query.get("fields") != new_fields:
                    main_query["fields"] = new_fields
                    changed = True
                enc = spec.get("encodings") or {}
                if spec.get("encodings") is None:
                    spec["encodings"] = enc
                existing_names = [c.get("fieldName") or c.get("name") for c in (enc.get("columns") or [])]
                if existing_names != field_names:
                    enc["columns"] = new_cols
                    changed = True
        if changed:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Fixed {path.name}: widget columns/values from dataset")
            fixed += 1
    print(f"Updated {fixed} dashboard(s) for visualization fields.")
    return 0


def cmd_link_widgets() -> int:
    """Add minimal layout with one table widget per dataset so widgets are linked (dbdemos pattern)."""
    updated = 0
    for path in sorted(SOURCE_DIR.glob("*.lvdash.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error reading {path}: {e}", file=sys.stderr)
            return 1
        _strip_optional_widget_spec_keys(data)
        datasets = data.get("datasets", [])
        pages = data.get("pages", [])
        if not datasets or not pages:
            continue
        changed = False
        for page in pages:
            layout = page.get("layout", [])
            # Check if every dataset is referenced by at least one widget
            linked = set()
            for item in layout:
                w = item.get("widget", {})
                for q in w.get("queries", []):
                    qq = q.get("query", {})
                    if "datasetName" in qq:
                        linked.add(qq["datasetName"])
            for ds in datasets:
                ds_name = ds.get("name")
                if not ds_name or ds_name in linked:
                    continue
                # Add a table widget for this dataset
                query = _get_dataset_query(ds)
                cols = _select_columns_from_query(query)
                if not cols and "query" in ds:
                    # Fallback: use displayName or name as single column placeholder
                    cols = [ds.get("displayName", ds_name)]
                y_offset = sum(
                    item.get("position", {}).get("height", 4) + 1
                    for item in layout
                )
                new_widget = _make_table_widget(ds_name, cols, 0, y_offset)
                layout.append(new_widget)
                linked.add(ds_name)
                changed = True
            if changed:
                page["layout"] = layout
        if changed:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Updated {path.name}: linked widgets to datasets")
            updated += 1
    print(f"Linked widgets in {updated} dashboard(s).")
    return 0


def cmd_prepare(catalog: str, schema: str) -> None:
    catalog_schema = f"{catalog}.{schema}"
    if not catalog or not schema:
        raise SystemExit("prepare requires non-empty --catalog and --schema (or set BUNDLE_VAR_catalog / BUNDLE_VAR_schema)")
    BUILD_DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Source: resources/dashboards (canonical); fallback to dashboards/ when no JSONs in resources (e.g. repo only has prepared files)
    source_dir = SOURCE_DIR
    source_files = sorted(source_dir.glob("*.lvdash.json"))
    if not source_files:
        source_dir = OUT_DIR
        source_files = sorted(source_dir.glob("*.lvdash.json"))
    count = 0
    for path in source_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        _strip_optional_widget_spec_keys(data)
        content = json.dumps(data, indent=2)
        if CATALOG_SCHEMA_PLACEHOLDER in content:
            content = content.replace(CATALOG_SCHEMA_PLACEHOLDER, catalog_schema)
        else:
            # Fallback: replace literal catalog.schema (e.g. from a previous prepare)
            content = content.replace("ahs_demos_catalog.payment_analysis", catalog_schema)
        if CATALOG_SCHEMA_PLACEHOLDER in content:
            raise SystemExit(
                f"prepare: {path.name} still contains {CATALOG_SCHEMA_PLACEHOLDER!r} after replace. "
                "Check source JSON for typos or different placeholder."
            )
        (BUILD_DASHBOARDS_DIR / path.name).write_text(content, encoding="utf-8")
        (OUT_DIR / path.name).write_text(content, encoding="utf-8")
        count += 1
    print(f"Prepared {count} dashboards in {OUT_DIR} and {BUILD_DASHBOARDS_DIR} with catalog.schema = {catalog_schema}")
    GOLD_VIEWS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = f"-- Catalog/schema for this run (must match dashboard asset_name)\nUSE CATALOG {catalog};\nUSE SCHEMA {schema};\n\n"
    (GOLD_VIEWS_OUT_DIR / "gold_views.sql").write_text(header + GOLD_VIEWS_SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    (GOLD_VIEWS_OUT_DIR / "lakehouse_bootstrap.sql").write_text(
        header + LAKEHOUSE_BOOTSTRAP_SOURCE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(f"Prepared gold_views.sql and lakehouse_bootstrap.sql in {GOLD_VIEWS_OUT_DIR} with USE CATALOG {catalog}; USE SCHEMA {schema};")


def cmd_validate_assets(catalog: str, schema: str) -> None:
    print(f"Dashboard assets (catalog={catalog}, schema={schema}):")
    print("Run Job 3 (Create Gold Views) in this catalog.schema. It requires payments_enriched_silver (Lakeflow);")
    print("if payments_raw_bronze is missing, Job 3 creates a stub so streaming views (v_streaming_ingestion_by_second, etc.) exist.")
    print()
    for asset, source in ASSETS:
        print(f"  {catalog}.{schema}.{asset}")
        print(f"    -> {source}")
    print()
    print("If you see TABLE_OR_VIEW_NOT_FOUND: run 'dashboards.py prepare' with the same catalog/schema, deploy, then run Job 3 (Gold Views).")


def get_workspace_root() -> str | None:
    try:
        result = subprocess.run(
            ["databricks", "bundle", "validate", "-t", "dev"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )
        for line in result.stdout.splitlines() + result.stderr.splitlines():
            m = re.search(r"Path:\s*(\S+)", line, re.I)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return None


def cmd_delete_workspace_dashboards(path: str | None, recursive: bool) -> int:
    """Delete dashboard objects under workspace .../dashboards so deploy can recreate them from config."""
    root = path or get_workspace_root()
    if not root:
        print(
            "Error: could not get workspace path. Pass --path /Workspace/Users/.../payment-analysis",
            file=sys.stderr,
        )
        return 1
    dashboards_path = f"{root.rstrip('/')}/dashboards"
    cmd = ["databricks", "workspace", "delete", dashboards_path]
    if recursive:
        cmd.append("--recursive")
    print(f"Deleting {dashboards_path} (recursive={recursive})...")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        print("Done. Run prepare then deploy to create dashboards with configured widgets:")
        print("  uv run python scripts/dashboards.py prepare --catalog <cat> --schema <schema>")
        print("  databricks bundle deploy -t dev --force --auto-approve")
        print("  uv run python scripts/dashboards.py publish")
        return 0
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        if "RESOURCE_DOES_NOT_EXIST" in err or "does not exist" in err.lower():
            print(f"Path {dashboards_path} does not exist; nothing to delete.")
            return 0
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("Error: databricks CLI not found.", file=sys.stderr)
        return 1


def _list_workspace_recursive(path: str, timeout_per_call: int = 30) -> list[dict]:
    """List workspace path and recurse into directories. Returns flat list of all objects (path, object_type)."""
    try:
        result = subprocess.run(
            ["databricks", "workspace", "list", path.rstrip("/"), "-o", "json"],
            capture_output=True,
            text=True,
            timeout=timeout_per_call,
        )
        result.check_returncode()
        objects = json.loads(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []
    all_objs = objects if isinstance(objects, list) else []
    out: list[dict] = []
    for o in all_objs:
        p = (o.get("path") or "").strip()
        obj_type = (o.get("object_type") or "").strip()
        if not p:
            continue
        out.append({"path": p, "object_type": obj_type})
        if obj_type == "DIRECTORY":
            out.extend(_list_workspace_recursive(p, timeout_per_call))
    return out


def cmd_clean_all_my_dashboards_except_dbdemos(path: str | None, dry_run: bool) -> int:
    """List all dashboards under workspace (recursive) and delete any whose name does NOT start with 'dbdemos'.
    Default: scan from bundle root (your project folder). Use --path /Workspace/Users/<you>/ to scan your entire user workspace."""
    root = (path or get_workspace_root() or "").rstrip("/")
    if not root:
        print(
            "Error: could not get workspace path. Pass --path /Workspace/Users/.../payment-analysis or /Workspace/Users/<you>/",
            file=sys.stderr,
        )
        return 1
    print(f"Scanning workspace under {root} for dashboards (keeping names starting with 'dbdemos')...")
    all_objs = _list_workspace_recursive(root)
    dashboards = [o["path"] for o in all_objs if o.get("object_type") == "DASHBOARD"]
    to_delete = []
    for p in dashboards:
        name = p.split("/")[-1]
        if not name.lower().startswith("dbdemos"):
            to_delete.append(p)
    if not to_delete:
        print("No dashboards to delete (all dashboards found start with 'dbdemos' or none found).")
        return 0
    print(f"Deleting {len(to_delete)} dashboard(s) that do not start with 'dbdemos':")
    for p in to_delete:
        print(f"  - {p}")
    if dry_run:
        print("Dry run: no changes made.")
        return 0
    failed = []
    for p in to_delete:
        try:
            subprocess.run(
                ["databricks", "workspace", "delete", p],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            print(f"Deleted: {p.split('/')[-1]}")
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e)).strip()
            if "RESOURCE_DOES_NOT_EXIST" in err or "does not exist" in err.lower():
                pass
            else:
                print(f"Failed: {p} — {err}", file=sys.stderr)
                failed.append(p)
    if failed:
        print(f"Failed to delete {len(failed)} dashboard(s).", file=sys.stderr)
        return 1
    print(f"Successfully deleted {len(to_delete)} dashboard(s).")
    return 0


def cmd_clean_non_dbdemos_dashboards(path: str | None, dry_run: bool) -> int:
    """List dashboards under workspace .../dashboards and delete any whose name does NOT start with 'dbdemos'."""
    root = path or get_workspace_root()
    if not root:
        print(
            "Error: could not get workspace path. Pass --path /Workspace/Users/.../payment-analysis",
            file=sys.stderr,
        )
        return 1
    dashboards_path = f"{root.rstrip('/')}/dashboards"
    try:
        result = subprocess.run(
            ["databricks", "workspace", "list", dashboards_path, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        result.check_returncode()
        objects = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("Error: workspace list timed out", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse workspace list: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("Error: databricks CLI not found.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"Error: workspace list failed: {e.stderr or e}. Deploy first or pass --path.", file=sys.stderr)
        return 1
    all_objs = objects if isinstance(objects, list) else []
    dashboards = [o for o in all_objs if o.get("object_type") == "DASHBOARD"]
    to_delete = []
    for o in dashboards:
        p = (o.get("path") or "").strip()
        if not p:
            continue
        name = p.split("/")[-1]
        if not name.lower().startswith("dbdemos"):
            to_delete.append(p)
    if not to_delete:
        print(f"No dashboards to delete (all under {dashboards_path} start with 'dbdemos' or folder is empty).")
        return 0
    print(f"Deleting {len(to_delete)} dashboard(s) that do not start with 'dbdemos':")
    for p in to_delete:
        print(f"  - {p}")
    if dry_run:
        print("Dry run: no changes made.")
        return 0
    failed = []
    for p in to_delete:
        try:
            subprocess.run(
                ["databricks", "workspace", "delete", p],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            print(f"Deleted: {p.split('/')[-1]}")
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e)).strip()
            if "RESOURCE_DOES_NOT_EXIST" in err or "does not exist" in err.lower():
                pass
            else:
                print(f"Failed: {p} — {err}", file=sys.stderr)
                failed.append(p)
    if failed:
        print(f"Failed to delete {len(failed)} dashboard(s).", file=sys.stderr)
        return 1
    print(f"Successfully deleted {len(to_delete)} dashboard(s).")
    return 0


def cmd_publish(path: str | None, dry_run: bool) -> int:
    root = path or get_workspace_root()
    if not root:
        print("Error: could not get workspace path. Run from repo root after deploy, or pass --path /Workspace/Users/.../payment-analysis", file=sys.stderr)
        return 1
    dashboards_path = f"{root.rstrip('/')}/dashboards"
    try:
        result = subprocess.run(
            ["databricks", "workspace", "list", dashboards_path, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        result.check_returncode()
        objects = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("Error: workspace list timed out", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse workspace list: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("Error: databricks CLI not found.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"Error: workspace list failed: {e.stderr or e}. Deploy first: ./scripts/bundle.sh deploy dev", file=sys.stderr)
        return 1
    dashboards = [o for o in (objects if isinstance(objects, list) else []) if o.get("object_type") == "DASHBOARD"]
    if not dashboards:
        print(f"No dashboards found under {dashboards_path}. Deploy first: ./scripts/bundle.sh deploy dev")
        return 0
    print(f"Found {len(dashboards)} dashboard(s) under {dashboards_path}:")
    for o in dashboards:
        name = o.get("path", "").split("/")[-1].replace(".lvdash.json", "")
        print(f"  - {o.get('resource_id')}  {name}")
    if dry_run:
        print("Dry run: skipping publish.")
        return 0
    failed = []
    for o in dashboards:
        did, name = o.get("resource_id"), (o.get("path", "") or "").split("/")[-1]
        if not did:
            continue
        try:
            # CLI: databricks lakeview (AI/BI Dashboards backend)
            subprocess.run(
                ["databricks", "lakeview", "publish", did, "--embed-credentials"],
                check=True,
                capture_output=True,
                text=True,
                timeout=PUBLISH_TIMEOUT,
            )
            print(f"Published: {name}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"Failed: {name} — {getattr(e, 'stderr', e) or e}", file=sys.stderr)
            failed.append(name)
    if failed:
        print(f"Failed: {len(failed)} dashboard(s).", file=sys.stderr)
        return 1
    print(f"Successfully published {len(dashboards)} dashboard(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Dashboard operations: prepare, validate-assets, publish, link-widgets")
    sub = parser.add_subparsers(dest="cmd", required=True)
    # prepare
    p_prepare = sub.add_parser("prepare", help="Copy dashboard JSONs to dashboards/ and gold_views.sql to .build/transform/ with catalog/schema")
    p_prepare.add_argument("--catalog", default=os.environ.get("BUNDLE_VAR_catalog", "ahs_demos_catalog"))
    p_prepare.add_argument("--schema", default=os.environ.get("BUNDLE_VAR_schema", "payment_analysis"))
    # validate-assets
    p_va = sub.add_parser("validate-assets", help="List tables/views required by dashboards")
    p_va.add_argument("--catalog", default="ahs_demos_catalog")
    p_va.add_argument("--schema", default="payment_analysis")
    # publish
    p_pub = sub.add_parser("publish", help="Publish all dashboards with embed credentials (after deploy)")
    p_pub.add_argument("--path", default=None, help="Workspace root path")
    p_pub.add_argument("--dry-run", action="store_true")
    # link-widgets
    sub.add_parser("link-widgets", help="Add layout with table widgets linked to each dataset (dbdemos pattern)")
    # check-widgets
    sub.add_parser("check-widgets", help="Verify widgets reference datasets in the same file and every dataset has a widget")
    # fix-visualization-fields
    sub.add_parser("fix-visualization-fields", help="Set widget columns/values from dataset query (table widgets)")
    # best-widgets
    sub.add_parser("best-widgets", help="Set best widget type (line/bar/table) and required columns from dataset")
    sub.add_parser("fix-widget-settings", help="Apply missing visualization settings: frame title, axis titles, legend")
    # delete-workspace-dashboards
    p_del = sub.add_parser("delete-workspace-dashboards", help="Delete workspace .../dashboards so deploy recreates them from config")
    p_del.add_argument("--path", default=None, help="Workspace root path")
    p_del.add_argument("--no-recursive", action="store_true", help="Do not delete folder recursively")
    # clean-workspace-except-dbdemos
    p_clean = sub.add_parser("clean-workspace-except-dbdemos", help="Delete all dashboards under .../dashboards except those whose name starts with 'dbdemos'")
    p_clean.add_argument("--path", default=None, help="Workspace root path")
    p_clean.add_argument("--dry-run", action="store_true", help="Only list dashboards that would be deleted")
    # clean-all-my-dashboards-except-dbdemos
    p_clean_all = sub.add_parser(
        "clean-all-my-dashboards-except-dbdemos",
        help="Recursively find and delete ALL dashboards in your workspace (where you are owner) except names starting with 'dbdemos'. Default: scan from your user folder.",
    )
    p_clean_all.add_argument("--path", default=None, help="Workspace path to scan (e.g. /Workspace/Users/<you>/). Default: parent of bundle root = your user folder.")
    p_clean_all.add_argument("--dry-run", action="store_true", help="Only list dashboards that would be deleted")
    args = parser.parse_args()

    if args.cmd == "prepare":
        cmd_prepare(args.catalog, args.schema)
        return 0
    if args.cmd == "validate-assets":
        cmd_validate_assets(args.catalog, args.schema)
        return 0
    if args.cmd == "publish":
        return cmd_publish(args.path, args.dry_run)
    if args.cmd == "link-widgets":
        return cmd_link_widgets()
    if args.cmd == "check-widgets":
        return cmd_check_widgets()
    if args.cmd == "fix-visualization-fields":
        return cmd_fix_visualization_fields()
    if args.cmd == "best-widgets":
        return cmd_best_widgets()
    if args.cmd == "fix-widget-settings":
        return cmd_fix_widget_settings()
    if args.cmd == "delete-workspace-dashboards":
        return cmd_delete_workspace_dashboards(args.path, recursive=not getattr(args, "no_recursive", False))
    if args.cmd == "clean-workspace-except-dbdemos":
        return cmd_clean_non_dbdemos_dashboards(args.path, dry_run=getattr(args, "dry_run", False))
    if args.cmd == "clean-all-my-dashboards-except-dbdemos":
        return cmd_clean_all_my_dashboards_except_dbdemos(args.path, dry_run=getattr(args, "dry_run", False))
    return 1


if __name__ == "__main__":
    sys.exit(main())
