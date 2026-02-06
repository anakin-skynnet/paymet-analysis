#!/usr/bin/env python3
"""
List tables and views required by the 12 dashboards so you can verify they exist
in your catalog.schema (run Create Gold Views job and Lakeflow pipelines first).

Usage:
  uv run python scripts/validate_dashboard_assets.py
  uv run python scripts/validate_dashboard_assets.py --catalog X --schema Y  # to print expected FQ names

No DB connection required; this only prints the expected asset list and where they are created.
"""
from __future__ import annotations

import argparse
from pathlib import Path

DASHBOARDS_DIR = Path(__file__).resolve().parent.parent / "src" / "payment_analysis" / "dashboards"

# All dashboard asset_name references (catalog.schema.asset) and where they are created
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
    ("payments_enriched_silver", "Lakeflow pipeline (silver table)"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="List dashboard dependency assets")
    parser.add_argument("--catalog", default="ahs_demos_catalog", help="Catalog name")
    parser.add_argument("--schema", default="ahs_demo_payment_analysis_dev", help="Schema name")
    args = parser.parse_args()

    print(f"Dashboard assets (catalog={args.catalog}, schema={args.schema}):")
    print("Run 'Create Payment Analysis Gold Views' job in this catalog.schema, and ensure Lakeflow has written payments_enriched_silver (and payments_raw_bronze for streaming views).")
    print()
    for asset, source in ASSETS:
        fq = f"{args.catalog}.{args.schema}.{asset}"
        print(f"  {fq}")
        print(f"    -> {source}")
    print()
    print("If you see TABLE_OR_VIEW_NOT_FOUND: run prepare_dashboards.py with the same catalog/schema, then bundle deploy; then run the Gold Views job (it uses .build/transform/gold_views.sql which sets USE CATALOG/SCHEMA).")


if __name__ == "__main__":
    main()
