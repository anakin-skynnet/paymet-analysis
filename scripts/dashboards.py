#!/usr/bin/env python3
"""
Dashboard operations: prepare (for bundle), validate-assets (list dependencies), publish (after deploy).

Usage:
  uv run python scripts/dashboards.py prepare [--catalog X] [--schema Y]
  uv run python scripts/dashboards.py validate-assets [--catalog X] [--schema Y]
  uv run python scripts/dashboards.py publish [--path /Workspace/Users/.../payment-analysis] [--dry-run]

Prepare: copies dashboard JSONs to .build/dashboards/ and gold_views.sql to .build/transform/ with catalog/schema.
Validate-assets: lists tables/views required by dashboards (no DB connection).
Publish: after deploy, publishes all 12 dashboards with embed credentials (Databricks CLI).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Literal in source dashboard JSONs (resources/dashboards/*.lvdash.json) to replace with catalog.schema.
# Default prepare uses --catalog ahs_demos_catalog --schema payment_analysis (matches bundle variables).
DEV_CATALOG_SCHEMA = "ahs_demos_catalog.ahs_demo_payment_analysis_dev"
SOURCE_DIR = REPO_ROOT / "resources" / "dashboards"
OUT_DIR = REPO_ROOT / ".build" / "dashboards"
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
    ("v_retry_performance", "gold_views.sql"),
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


def cmd_prepare(catalog: str, schema: str) -> None:
    catalog_schema = f"{catalog}.{schema}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(SOURCE_DIR.glob("*.lvdash.json")):
        content = path.read_text(encoding="utf-8")
        if DEV_CATALOG_SCHEMA in content:
            content = content.replace(DEV_CATALOG_SCHEMA, catalog_schema)
        (OUT_DIR / path.name).write_text(content, encoding="utf-8")
        count += 1
    print(f"Prepared {count} dashboards in {OUT_DIR} with catalog.schema = {catalog_schema}")
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
    parser = argparse.ArgumentParser(description="Dashboard operations: prepare, validate-assets, publish")
    sub = parser.add_subparsers(dest="cmd", required=True)
    # prepare
    p_prepare = sub.add_parser("prepare", help="Copy dashboards and gold_views.sql to .build/ with catalog/schema")
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
    args = parser.parse_args()

    if args.cmd == "prepare":
        cmd_prepare(args.catalog, args.schema)
        return 0
    if args.cmd == "validate-assets":
        cmd_validate_assets(args.catalog, args.schema)
        return 0
    if args.cmd == "publish":
        return cmd_publish(args.path, args.dry_run)
    return 1


if __name__ == "__main__":
    sys.exit(main())
