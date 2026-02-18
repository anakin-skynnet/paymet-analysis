#!/usr/bin/env python3
"""Verify dashboard IDs in app.yml match actual dashboards in workspace."""
import os
import sys
from databricks.sdk import WorkspaceClient

# Expected dashboard IDs from app.yml (updated 2026-02-05)
EXPECTED_IDS = {
    "data_quality": "01f10c630ab414f18fc5a9d5f5db58a7",
    "ml_optimization": "01f10c630ac01742adbe0ecab4d3dde7",
    "executive_trends": "01f10c630abf198a95ac2df801f29ac5",
}

# Name patterns to match
NAME_PATTERNS = {
    "data_quality": ["Data & Quality", "Data Quality", "data_quality"],
    "ml_optimization": ["ML & Optimization", "ML Optimization", "ml_optimization"],
    "executive_trends": ["Executive & Trends", "Executive Trends", "executive_trends"],
}

def main():
    print("=" * 70)
    print("VERIFYING DASHBOARD IDs")
    print("=" * 70)
    print()
    
    try:
        w = WorkspaceClient()
    except Exception as e:
        print(f"❌ Failed to create WorkspaceClient: {e}")
        return 1
    
    # List all dashboards
    try:
        dashboards = list(w.lakeview.list())
        print(f"Found {len(dashboards)} dashboard(s) in workspace:\n")
    except Exception as e:
        print(f"❌ Failed to list dashboards: {e}")
        return 1
    
    # Display all dashboards
    for dash in dashboards:
        print(f"  ID: {dash.dashboard_id}")
        print(f"  Name: {dash.display_name or '(no name)'}")
        print()
    
    # Match dashboards by name patterns
    matched = {}
    for dash in dashboards:
        display_name = (dash.display_name or "").lower()
        for key, patterns in NAME_PATTERNS.items():
            if key in matched:
                continue
            for pattern in patterns:
                if pattern.lower() in display_name:
                    matched[key] = {
                        "id": dash.dashboard_id,
                        "name": dash.display_name or "(no name)",
                    }
                    break
    
    print("=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    print()
    
    all_correct = True
    for key, expected_id in EXPECTED_IDS.items():
        if key in matched:
            actual_id = matched[key]["id"]
            actual_name = matched[key]["name"]
            if actual_id == expected_id:
                print(f"✅ {key}:")
                print(f"   Expected: {expected_id}")
                print(f"   Actual:   {actual_id} ({actual_name})")
                print(f"   Status:   MATCH")
            else:
                print(f"❌ {key}:")
                print(f"   Expected: {expected_id}")
                print(f"   Actual:   {actual_id} ({actual_name})")
                print(f"   Status:   MISMATCH - UPDATE NEEDED")
                all_correct = False
        else:
            print(f"⚠️  {key}:")
            print(f"   Expected: {expected_id}")
            print(f"   Actual:   NOT FOUND")
            print(f"   Status:   DASHBOARD NOT FOUND IN WORKSPACE")
            all_correct = False
        print()
    
    if all_correct:
        print("✅ All dashboard IDs are correct!")
        return 0
    else:
        print("❌ Some dashboard IDs need to be updated.")
        print("\nTo update app.yml, run:")
        print("  python scripts/verify_dashboard_ids.py --update")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        # Update mode - will be implemented if needed
        print("Update mode not yet implemented. Please update app.yml manually.")
        sys.exit(1)
    sys.exit(main())
