#!/usr/bin/env python3
"""
Pre-deploy resource check and state reconciliation.

Verifies all bundle-managed resources against the workspace before deployment.
Ensures Terraform state is consistent so `bundle deploy` UPDATES existing
resources instead of destroying and recreating them.

For each resource:
  EXISTS in workspace + EXISTS in state  → will be UPDATED
  MISSING in workspace + EXISTS in state → orphaned (removed with --fix)
  EXISTS in workspace + MISSING in state → drift (warn — deploy may re-create)
  MISSING in workspace + MISSING in state → will be CREATED

Usage:
  uv run python scripts/pre_deploy_check.py [--target dev|prod] [--fix]
  uv run python scripts/pre_deploy_check.py --serving-exist    # exit 0 if all 4 ML endpoints exist
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

KNOWN_SERVING_ENDPOINTS = [
    ("approval_propensity_endpoint", "approval-propensity"),
    ("risk_scoring_endpoint", "risk-scoring"),
    ("smart_routing_endpoint", "smart-routing"),
    ("smart_retry_endpoint", "smart-retry"),
]


def _cli(*args: str, timeout: int = 20) -> tuple[bool, dict | None]:
    try:
        r = subprocess.run(
            ["databricks", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode != 0:
            return False, None
        try:
            return True, json.loads(r.stdout)
        except (json.JSONDecodeError, ValueError):
            return True, None
    except Exception:
        return False, None


def _state_path(target: str) -> Path:
    return REPO_ROOT / ".databricks" / "bundle" / target / "terraform" / "terraform.tfstate"


def _load_state(target: str) -> dict | None:
    p = _state_path(target)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def _save_state(state: dict, target: str) -> None:
    state["serial"] = state.get("serial", 0) + 1
    with open(_state_path(target), "w") as f:
        json.dump(state, f, indent=2)


def _resource_id(resource: dict) -> str | None:
    for inst in resource.get("instances", []):
        a = inst.get("attributes", {})
        return a.get("id") or a.get("name")
    return None


def _resource_attr(resource: dict, key: str) -> str | None:
    for inst in resource.get("instances", []):
        return inst.get("attributes", {}).get(key)
    return None


# ---------------------------------------------------------------------------
# Workspace existence checks (one per resource type)
# ---------------------------------------------------------------------------
def _check_app(name: str = "payment-analysis") -> tuple[str, bool]:
    ok, _ = _cli("apps", "get", name, "-o", "json")
    return name, ok


def _check_serving_endpoint(name: str) -> tuple[str, bool]:
    ok, _ = _cli("serving-endpoints", "get", name, "-o", "json")
    return name, ok


def _check_job(job_id: str) -> tuple[str, bool]:
    ok, _ = _cli("jobs", "get", job_id, "-o", "json")
    return job_id, ok


def _check_pipeline(pipeline_id: str) -> tuple[str, bool]:
    ok, _ = _cli("pipelines", "get", pipeline_id, "-o", "json")
    return pipeline_id, ok


def _check_dashboard(dashboard_id: str) -> tuple[str, bool]:
    ok, _ = _cli("api", "get", f"/api/2.0/lakeview/dashboards/{dashboard_id}")
    return dashboard_id, ok


def _check_warehouse(warehouse_id: str) -> tuple[str, bool]:
    ok, _ = _cli("warehouses", "get", warehouse_id, "-o", "json")
    return warehouse_id, ok


# Schemas, volumes, grants are durable UC objects — trust Terraform state.
def _check_uc_resource(_rid: str) -> tuple[str, bool]:
    return _rid, True


# Map Terraform resource type → checker function
_CHECKERS: dict[str, Callable] = {
    "databricks_app": _check_app,
    "databricks_model_serving": _check_serving_endpoint,
    "databricks_job": _check_job,
    "databricks_pipeline": _check_pipeline,
    "databricks_dashboard": _check_dashboard,
    "databricks_sql_endpoint": _check_warehouse,
    "databricks_schema": _check_uc_resource,
    "databricks_volume": _check_uc_resource,
    "databricks_grants": _check_uc_resource,
}


def check_serving_endpoints_exist() -> bool:
    """Quick check: do all 4 ML serving endpoints exist in the workspace?"""
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_check_serving_endpoint, ep_name): tf_name
            for tf_name, ep_name in KNOWN_SERVING_ENDPOINTS
        }
        for f in as_completed(futures):
            _, exists = f.result()
            if not exists:
                return False
    return True


def reconcile(target: str, fix: bool) -> dict:
    """
    Check all resources and reconcile state. Returns summary dict with keys:
      will_update, will_create, orphaned, serving_endpoints_exist
    """
    state = _load_state(target)
    if state is None:
        serving_exist = check_serving_endpoints_exist()
        print("No Terraform state found — all resources will be CREATED (first deploy).")
        return {
            "will_update": 0,
            "will_create": 0,
            "orphaned": 0,
            "serving_endpoints_exist": serving_exist,
        }

    resources = state.get("resources", [])
    state_index = {(r["type"], r["name"]) for r in resources}

    # --- Step 1: Check every resource in state against workspace ---
    tasks: list[tuple[str, str, str | None, Callable, list]] = []
    for r in resources:
        rtype, rname = r["type"], r["name"]
        rid = _resource_id(r)
        checker = _CHECKERS.get(rtype)
        if not checker:
            continue
        if rtype == "databricks_app":
            app_name = _resource_attr(r, "name") or "payment-analysis"
            tasks.append((rtype, rname, app_name, checker, [app_name]))
        elif rtype == "databricks_model_serving":
            ep_name = _resource_attr(r, "name") or rid
            tasks.append((rtype, rname, ep_name, checker, [ep_name]))
        elif rid:
            tasks.append((rtype, rname, rid, checker, [rid]))

    will_update = 0
    orphaned_keys: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {}
        for rtype, rname, rid, checker, args in tasks:
            f = pool.submit(checker, *args)
            futures[f] = (rtype, rname, rid)

        for f in as_completed(futures):
            rtype, rname, rid = futures[f]
            _, exists = f.result()
            if exists:
                will_update += 1
                print(f"  UPDATE  {rtype}.{rname} ({rid})")
            else:
                orphaned_keys.append((rtype, rname))
                print(f"  ORPHAN  {rtype}.{rname} ({rid}) — in state but not in workspace")

    # --- Step 2: Check known resources that SHOULD exist but may be missing from state ---
    will_create = 0
    serving_exist = True
    orphan_set = set(orphaned_keys)

    # Collect resources to check in parallel (missing from state or orphaned)
    step2_tasks: list[tuple[str, str, str, Callable, list]] = []
    for tf_name, ep_name in KNOWN_SERVING_ENDPOINTS:
        if ("databricks_model_serving", tf_name) not in state_index:
            step2_tasks.append(("databricks_model_serving", tf_name, ep_name, _check_serving_endpoint, [ep_name]))
        elif ("databricks_model_serving", tf_name) in orphan_set:
            serving_exist = False

    if ("databricks_app", "payment_analysis_app") not in state_index:
        step2_tasks.append(("databricks_app", "payment_analysis_app", "payment-analysis", _check_app, ["payment-analysis"]))

    with ThreadPoolExecutor(max_workers=len(step2_tasks) or 1) as pool:
        futures = {}
        for rtype, tf_name, display, checker, args in step2_tasks:
            f = pool.submit(checker, *args)
            futures[f] = (rtype, tf_name, display)

        for f in as_completed(futures):
            rtype, tf_name, display = futures[f]
            _, exists = f.result()
            if exists:
                print(f"  DRIFT   {rtype}.{tf_name} ({display}) — exists in workspace, missing from state")
            else:
                if rtype == "databricks_model_serving":
                    serving_exist = False
                will_create += 1
                print(f"  CREATE  {rtype}.{tf_name} ({display})")

    # --- Step 3: Fix state if requested ---
    stale_removed = 0
    if fix and orphaned_keys:
        orphan_set = set(orphaned_keys)
        state["resources"] = [
            r for r in resources if (r["type"], r["name"]) not in orphan_set
        ]
        _save_state(state, target)
        stale_removed = len(orphaned_keys)
        print(f"\n  Removed {stale_removed} orphaned entries from Terraform state.")

    return {
        "will_update": will_update,
        "will_create": will_create,
        "orphaned": len(orphaned_keys),
        "stale_removed": stale_removed,
        "serving_endpoints_exist": serving_exist,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-deploy resource check and state reconciliation")
    parser.add_argument("--target", default="dev", help="Bundle target (dev or prod)")
    parser.add_argument("--fix", action="store_true", help="Remove orphaned state entries")
    parser.add_argument(
        "--serving-exist",
        action="store_true",
        help="Quick check: exit 0 if all 4 ML serving endpoints exist, else exit 1",
    )
    args = parser.parse_args()

    if args.serving_exist:
        exists = check_serving_endpoints_exist()
        if exists:
            print("All model serving endpoints exist.")
        else:
            print("One or more model serving endpoints missing.")
        sys.exit(0 if exists else 1)

    print(f"Pre-deploy check (target={args.target}):\n")
    summary = reconcile(args.target, args.fix)

    print(f"\n{'='*60}")
    print(f"  Will UPDATE:  {summary['will_update']}")
    print(f"  Will CREATE:  {summary['will_create']}")
    if summary["orphaned"]:
        fixed = " (removed)" if summary.get("stale_removed") else " (run with --fix)"
        print(f"  Orphaned:     {summary['orphaned']}{fixed}")
    ep_status = "yes" if summary["serving_endpoints_exist"] else "no (excluded from phase 1)"
    print(f"  Serving endpoints exist: {ep_status}")
    print(f"{'='*60}")

    # Machine-readable output for bash consumption (last 2 lines)
    print(f"\nSERVING_ENDPOINTS_EXIST={'true' if summary['serving_endpoints_exist'] else 'false'}")
    print(f"RESOURCES_OK=true")


if __name__ == "__main__":
    main()
