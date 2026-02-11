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
    ("v_silver_processed_hourly", "gold_views.sql"),
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
                                # Columns and values MUST exist in the dataset
                                ds = datasets_by_name.get(dn)
                                if ds:
                                    ds_columns = set(_select_columns_from_query(ds.get("query", "")))
                                    widget_fields = [f.get("name") for f in query.get("fields", []) if f.get("name")]
                                    if ds_columns and widget_fields:
                                        missing_in_ds = [f for f in widget_fields if f not in ds_columns]
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


def cmd_fix_visualization_fields() -> int:
    """Ensure widget columns and values exist: derive query.fields and spec.encodings.columns from the dataset query."""
    fixed = 0
    for path in sorted(SOURCE_DIR.glob("*.lvdash.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error reading {path}: {e}", file=sys.stderr)
            return 1
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
                ds_query = dataset.get("query", "")
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
                query = ds.get("query", "")
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
    BUILD_DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(SOURCE_DIR.glob("*.lvdash.json")):
        content = path.read_text(encoding="utf-8")
        if CATALOG_SCHEMA_PLACEHOLDER in content:
            content = content.replace(CATALOG_SCHEMA_PLACEHOLDER, catalog_schema)
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
    print("Run 'Create Payment Analysis Gold Views' job in this catalog.schema, and ensure Lakeflow has written payments_enriched_silver (and payments_raw_bronze for streaming views).")
    print()
    for asset, source in ASSETS:
        print(f"  {catalog}.{schema}.{asset}")
        print(f"    -> {source}")
    print()
    print("If you see TABLE_OR_VIEW_NOT_FOUND: run dashboards.py prepare with the same catalog/schema, then bundle deploy; then run the Gold Views job (it uses .build/transform/gold_views.sql which sets USE CATALOG/SCHEMA).")


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
    sub.add_parser("fix-visualization-fields", help="Add 'name' to table columns so Lakeview does not show 'no fields selected'")
    # delete-workspace-dashboards
    p_del = sub.add_parser("delete-workspace-dashboards", help="Delete workspace .../dashboards so deploy recreates them from config")
    p_del.add_argument("--path", default=None, help="Workspace root path")
    p_del.add_argument("--no-recursive", action="store_true", help="Do not delete folder recursively")
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
    if args.cmd == "delete-workspace-dashboards":
        return cmd_delete_workspace_dashboards(args.path, recursive=not getattr(args, "no_recursive", False))
    return 1


if __name__ == "__main__":
    sys.exit(main())
