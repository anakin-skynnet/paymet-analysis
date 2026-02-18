#!/usr/bin/env python3
"""Manage UC functions as app resources and verify dashboard references.

This script consolidates functionality from:
- add_uc_functions_to_app.py
- re_add_uc_functions_corrected.py
- add_uc_functions_to_app_resources.py

UC functions cannot be added via DAB (Databricks Asset Bundle) - they must be added manually via UI or API.

Usage:
    python scripts/manage_uc_functions.py [--verify-only]
    python scripts/manage_uc_functions.py --list-all
    python scripts/manage_uc_functions.py --verify-dashboards
"""
import argparse
import sys
from databricks.sdk import WorkspaceClient

# Consolidated UC Functions (5 functions used by ResponsesAgent)
CONSOLIDATED_FUNCTIONS = [
    "ahs_demos_catalog.payment_analysis.analyze_declines",
    "ahs_demos_catalog.payment_analysis.analyze_performance",
    "ahs_demos_catalog.payment_analysis.analyze_retry",
    "ahs_demos_catalog.payment_analysis.analyze_risk",
    "ahs_demos_catalog.payment_analysis.analyze_routing",
]

# Individual UC Functions (legacy, not currently used by ResponsesAgent)
INDIVIDUAL_FUNCTIONS = [
    "ahs_demos_catalog.payment_analysis.get_cascade_recommendations",
    "ahs_demos_catalog.payment_analysis.get_decline_by_segment",
    "ahs_demos_catalog.payment_analysis.get_decline_trends",
    "ahs_demos_catalog.payment_analysis.get_high_risk_transactions",
    "ahs_demos_catalog.payment_analysis.get_kpi_summary",
    "ahs_demos_catalog.payment_analysis.get_optimization_opportunities",
    "ahs_demos_catalog.payment_analysis.get_recovery_opportunities",
    "ahs_demos_catalog.payment_analysis.get_retry_success_rates",
    "ahs_demos_catalog.payment_analysis.get_risk_distribution",
    "ahs_demos_catalog.payment_analysis.get_route_performance",
    "ahs_demos_catalog.payment_analysis.get_trend_analysis",
]

# All UC Functions (consolidated + individual)
ALL_FUNCTIONS = CONSOLIDATED_FUNCTIONS + INDIVIDUAL_FUNCTIONS


def get_existing_uc_functions(workspace_client: WorkspaceClient, app_name: str) -> set[str]:
    """Get set of existing UC function names from app resources."""
    try:
        app = workspace_client.apps.get(app_name)
        current_resources = list(app.resources) if app.resources else []
    except Exception as e:
        print(f"❌ Failed to get app '{app_name}': {e}")
        return set()
    
    existing_funcs = set()
    for res in current_resources:
        uc = getattr(res, 'uc_securable', None)
        if uc:
            sec_type = getattr(uc, 'securable_type', None)
            if sec_type == "FUNCTION":
                full_name = getattr(uc, 'securable_full_name', None)
                if full_name:
                    existing_funcs.add(full_name)
    
    return existing_funcs


def verify_uc_functions(workspace_client: WorkspaceClient, app_name: str, functions: list[str]) -> tuple[set[str], set[str]]:
    """Verify which UC functions are present and which are missing."""
    existing = get_existing_uc_functions(workspace_client, app_name)
    missing = set(functions) - existing
    return existing, missing


def print_verification_report(existing: set[str], missing: set[str], functions: list[str], title: str):
    """Print a formatted verification report."""
    print(f"\n{title}")
    print("=" * 70)
    print(f"Expected functions: {len(functions)}")
    print(f"Existing functions: {len(existing)}")
    print(f"Missing functions: {len(missing)}")
    
    if existing:
        print(f"\n✅ Existing UC Functions ({len(existing)}):")
        for func in sorted(existing):
            print(f"  ✅ {func}")
    
    if missing:
        print(f"\n⚠️  Missing UC Functions ({len(missing)}):")
        for func in sorted(missing):
            print(f"  ❌ {func}")
    
    if not missing:
        print(f"\n✅ All {title.lower()} are present!")


def print_instructions():
    """Print instructions for adding UC functions manually."""
    print("\n" + "=" * 70)
    print("HOW TO ADD MISSING UC FUNCTIONS")
    print("=" * 70)
    print("\nOption 1: Via Databricks Apps UI (Recommended)")
    print("  1. Go to: Compute → Apps → payment-analysis")
    print("  2. Click 'Configure' → 'App resources'")
    print("  3. Click 'Add resource' → 'Unity Catalog function'")
    print("  4. For each missing function:")
    print("     - Securable type: FUNCTION")
    print("     - Securable full name: <full_function_name>")
    print("     - Permission: EXECUTE")
    print("\nOption 2: Via Databricks CLI")
    print("  Use: databricks apps update --resources <json_file>")
    print("\nNote: The Databricks SDK doesn't support updating app resources")
    print("directly. Use the UI or CLI instead.")
    print("=" * 70)


def verify_dashboards(workspace_client: WorkspaceClient):
    """Verify dashboard IDs match expected values from app.yml."""
    print("\n" + "=" * 70)
    print("DASHBOARD VERIFICATION")
    print("=" * 70)
    
    # Expected dashboard IDs from app.yml (updated 2026-02-05)
    EXPECTED_DASHBOARD_IDS = {
        "data_quality": "01f10c630ab414f18fc5a9d5f5db58a7",
        "ml_optimization": "01f10c630ac01742adbe0ecab4d3dde7",
        "executive_trends": "01f10c630abf198a95ac2df801f29ac5",
    }
    
    try:
        dashboards = list(workspace_client.lakeview.list())
        print(f"\nFound {len(dashboards)} dashboard(s) in workspace:")
        
        dashboard_map = {}
        for dash in dashboards:
            dashboard_map[dash.dashboard_id] = dash.display_name or "(no name)"
            print(f"  ID: {dash.dashboard_id}")
            print(f"  Name: {dash.display_name or '(no name)'}")
            print()
        
        # Verify expected IDs exist
        print("Verifying dashboard IDs from app.yml:")
        all_correct = True
        for key, expected_id in EXPECTED_DASHBOARD_IDS.items():
            if expected_id in dashboard_map:
                print(f"  ✅ {key}: {expected_id} → {dashboard_map[expected_id]}")
            else:
                print(f"  ❌ {key}: {expected_id} → NOT FOUND")
                all_correct = False
        
        # Test fetching dashboard definitions
        print("\nTesting dashboard definition fetching:")
        for key, dashboard_id in EXPECTED_DASHBOARD_IDS.items():
            try:
                dashboard = workspace_client.lakeview.get(dashboard_id)
                serialized = dashboard.serialized_dashboard
                if serialized:
                    print(f"  ✅ {key} ({dashboard_id}): Definition available")
                else:
                    print(f"  ⚠️  {key} ({dashboard_id}): No serialized dashboard")
            except Exception as e:
                print(f"  ❌ {key} ({dashboard_id}): {e}")
                all_correct = False
        
        if all_correct:
            print("\n✅ All dashboard IDs are correct and accessible!")
        else:
            print("\n❌ Some dashboard IDs need to be updated!")
        
        return all_correct
        
    except Exception as e:
        print(f"❌ Failed to list dashboards: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manage UC functions as app resources and verify dashboard references",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify consolidated functions only (default)
  python scripts/manage_uc_functions.py

  # Verify all functions
  python scripts/manage_uc_functions.py --list-all

  # Verify only (don't show instructions)
  python scripts/manage_uc_functions.py --verify-only

  # Verify dashboards
  python scripts/manage_uc_functions.py --verify-dashboards
        """
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="List all UC functions (consolidated + individual), not just consolidated"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify, don't show instructions for adding"
    )
    parser.add_argument(
        "--verify-dashboards",
        action="store_true",
        help="Verify dashboard IDs match app.yml"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("UC FUNCTION RESOURCES MANAGER")
    print("=" * 70)
    
    try:
        w = WorkspaceClient()
    except Exception as e:
        print(f"❌ Failed to create WorkspaceClient: {e}")
        return 1
    
    app_name = "payment-analysis"
    
    # Get current app resources count
    try:
        app = w.apps.get(app_name)
        current_resources = list(app.resources) if app.resources else []
        print(f"\n✅ Found app: {app.name}")
        print(f"Total app resources: {len(current_resources)}")
    except Exception as e:
        print(f"❌ Failed to get app '{app_name}': {e}")
        return 1
    
    # Verify consolidated functions (default)
    functions_to_check = CONSOLIDATED_FUNCTIONS if not args.list_all else ALL_FUNCTIONS
    title = "Consolidated UC Functions" if not args.list_all else "All UC Functions"
    
    existing, missing = verify_uc_functions(w, app_name, functions_to_check)
    print_verification_report(existing, missing, functions_to_check, title)
    
    # Show instructions if there are missing functions
    if missing and not args.verify_only:
        print_instructions()
    
    # Verify dashboards if requested
    dashboards_ok = True
    if args.verify_dashboards:
        dashboards_ok = verify_dashboards(w)
    
    return 0 if (not missing and dashboards_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
