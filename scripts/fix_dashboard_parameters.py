#!/usr/bin/env python3
"""
Fix hardcoded values in Lakeview dashboard JSON files.

This script replaces hardcoded schema names and warehouse IDs with
parameterized values that will be substituted during deployment.
"""

import json
import re
from pathlib import Path


def fix_dashboard_file(file_path: Path, schema_placeholder: str, warehouse_placeholder: str) -> bool:
    """
    Fix a single dashboard file by replacing hardcoded values.
    
    Args:
        file_path: Path to the dashboard JSON file
        schema_placeholder: Placeholder for schema name (e.g., "${var.catalog}.${var.schema}")
        warehouse_placeholder: Placeholder for warehouse ID (e.g., "${var.warehouse_id}")
    
    Returns:
        True if file was modified, False otherwise
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Replace hardcoded schema names (pattern: main.dev_*_payment_analysis_dev)
    # This regex matches: main.dev_<username>_payment_analysis_dev
    content = re.sub(
        r'"datasetName":\s*"main\.dev_[a-zA-Z0-9_]+_payment_analysis_dev',
        f'"datasetName": "{schema_placeholder}',
        content
    )
    
    # Replace hardcoded warehouse IDs
    content = re.sub(
        r'"warehouse_id":\s*"[a-f0-9]+"',
        f'"warehouse_id": "{warehouse_placeholder}"',
        content
    )
    
    # Only write if content changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    
    return False


def main():
    """Fix all dashboard files in the resources/dashboards directory."""
    # Configuration
    schema_placeholder = "${var.catalog}.${var.schema}"
    warehouse_placeholder = "${var.warehouse_id}"
    
    # Find all dashboard files
    dashboards_dir = Path(__file__).parent.parent / "resources" / "dashboards"
    dashboard_files = list(dashboards_dir.glob("*.lvdash.json"))
    
    if not dashboard_files:
        print(f"❌ No dashboard files found in {dashboards_dir}")
        return 1
    
    print(f"🔍 Found {len(dashboard_files)} dashboard files")
    print(f"📝 Schema placeholder: {schema_placeholder}")
    print(f"📝 Warehouse placeholder: {warehouse_placeholder}")
    print()
    
    # Fix each file
    fixed_count = 0
    for file_path in sorted(dashboard_files):
        if fix_dashboard_file(file_path, schema_placeholder, warehouse_placeholder):
            print(f"✅ Fixed: {file_path.name}")
            fixed_count += 1
        else:
            print(f"⏭️  Skipped (no changes): {file_path.name}")
    
    print()
    print(f"✨ Fixed {fixed_count} of {len(dashboard_files)} dashboard files")
    
    return 0 if fixed_count > 0 else 1


if __name__ == "__main__":
    exit(main())
