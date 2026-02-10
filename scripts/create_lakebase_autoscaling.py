#!/usr/bin/env python3
"""
Create Lakebase Autoscaling resources (project, branch, endpoint) programmatically
and optionally set job parameters for Job 1 (lakebase_data_init).

Usage:
  uv run python scripts/create_lakebase_autoscaling.py [OPTIONS]

  Creates project, branch, and endpoint with IDs matching bundle defaults
  (payment-analysis-db, production, primary) so Job 1 and the app can connect.

  Requires: databricks-sdk (uv sync). Authenticate with: databricks auth login

Options:
  --project-id ID    Project ID (default: payment-analysis-db)
  --branch-id ID     Branch ID (default: production)
  --endpoint-id ID   Endpoint ID (default: primary)
  --job-id ID        If set, update this job's base_parameters with the three IDs
  --skip-create      Only update job parameters (do not create resources)
  --dry-run          Print what would be done, do not call the API
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create Lakebase Autoscaling project/branch/endpoint and optionally set job parameters."
    )
    parser.add_argument(
        "--project-id",
        default="payment-analysis-db",
        help="Lakebase Autoscaling project ID (1-63 chars, lowercase, digits, hyphens)",
    )
    parser.add_argument(
        "--branch-id",
        default="production",
        help="Branch ID",
    )
    parser.add_argument(
        "--endpoint-id",
        default="primary",
        help="Endpoint (compute) ID",
    )
    parser.add_argument(
        "--job-id",
        default="",
        help="Databricks job ID to update base_parameters (lakebase_project_id, etc.)",
    )
    parser.add_argument(
        "--skip-create",
        action="store_true",
        help="Do not create resources; only update job parameters if --job-id is set",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions only",
    )
    args = parser.parse_args()

    project_id = (args.project_id or "").strip()
    branch_id = (args.branch_id or "").strip()
    endpoint_id = (args.endpoint_id or "").strip()
    if not project_id or not branch_id or not endpoint_id:
        print("Error: project_id, branch_id, and endpoint_id must be non-empty.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("Dry run: would create Lakebase Autoscaling resources:")
        print(f"  project_id={project_id!r}, branch_id={branch_id!r}, endpoint_id={endpoint_id!r}")
        if args.job_id:
            print(f"  Then update job {args.job_id} base_parameters with these IDs.")
        return 0

    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.postgres import (
            Branch,
            BranchSpec,
            Endpoint,
            EndpointSpec,
            EndpointType,
            Project,
            ProjectSpec,
        )
    except ImportError as e:
        print(f"Error: {e}. Run: uv sync", file=sys.stderr)
        return 1

    w = WorkspaceClient()
    postgres_api = getattr(w, "postgres", None)
    if postgres_api is None:
        print(
            "Error: WorkspaceClient has no 'postgres' (Lakebase Autoscaling API). "
            "Ensure databricks-sdk==0.85.0 and the workspace supports Lakebase Autoscaling.",
            file=sys.stderr,
        )
        return 1

    from databricks.sdk.errors import NotFound

    def _exists(get_fn) -> bool:
        try:
            get_fn()
            return True
        except NotFound:
            return False

    def _is_conflict(exc: Exception) -> bool:
        msg = str(exc).lower()
        return "already exists" in msg or "409" in msg or "conflict" in msg

    if not args.skip_create:
        # Resource paths (hierarchical naming per SDK docs)
        project_name = f"projects/{project_id}"
        branch_name = f"{project_name}/branches/{branch_id}"
        parent_branch = f"projects/{project_id}/branches/{branch_id}"

        # Create project (idempotent)
        print(f"Creating project {project_id!r}...")
        if _exists(lambda: postgres_api.get_project(name=project_name)):
            print(f"  Project {project_id!r} already exists, skipping.")
        else:
            project_spec = ProjectSpec(display_name="payment-analysis-db", pg_version=17)
            project = Project(spec=project_spec)
            try:
                result = postgres_api.create_project(project=project, project_id=project_id).wait()
                print(f"  ✓ Created project: {getattr(result, 'name', project_id)}")
            except Exception as e:
                if _is_conflict(e):
                    print(f"  Project {project_id!r} already exists, skipping.")
                else:
                    raise

        # Create branch (idempotent)
        print(f"Creating branch {branch_id!r} in {project_name}...")
        if _exists(lambda: postgres_api.get_branch(name=branch_name)):
            print(f"  Branch {branch_id!r} already exists, skipping.")
        else:
            branch_spec = BranchSpec(no_expiry=True)
            branch = Branch(spec=branch_spec)
            try:
                result = postgres_api.create_branch(parent=project_name, branch=branch, branch_id=branch_id).wait()
                print(f"  ✓ Created branch: {getattr(result, 'name', branch_id)}")
            except Exception as e:
                if _is_conflict(e):
                    print(f"  Branch {branch_id!r} already exists, skipping.")
                else:
                    raise

        # Create endpoint (read-write compute, idempotent)
        endpoint_name = f"{parent_branch}/endpoints/{endpoint_id}"
        print(f"Creating endpoint {endpoint_id!r} in {parent_branch}...")
        if _exists(lambda: postgres_api.get_endpoint(name=endpoint_name)):
            print(f"  Endpoint {endpoint_id!r} already exists, skipping.")
        else:
            endpoint_spec = EndpointSpec(
                endpoint_type=EndpointType.ENDPOINT_TYPE_READ_WRITE,
                autoscaling_limit_max_cu=4.0,
            )
            endpoint = Endpoint(spec=endpoint_spec)
            try:
                result = postgres_api.create_endpoint(
                    parent=parent_branch, endpoint=endpoint, endpoint_id=endpoint_id,
                ).wait()
                print(f"  ✓ Created endpoint: {getattr(result, 'name', endpoint_id)}")
            except Exception as e:
                if _is_conflict(e):
                    print(f"  Endpoint {endpoint_id!r} already exists, skipping.")
                else:
                    raise

    # Output for deploy / job parameters
    print()
    print("Lakebase Autoscaling IDs (use for job parameters or bundle vars):")
    print(f"  lakebase_project_id={project_id}")
    print(f"  lakebase_branch_id={branch_id}")
    print(f"  lakebase_endpoint_id={endpoint_id}")
    print()
    print("Redeploy with these vars so Job 1 and the app use this project:")
    print(
        f"  ./scripts/bundle.sh deploy dev --var lakebase_project_id={project_id} --var lakebase_branch_id={branch_id} --var lakebase_endpoint_id={endpoint_id}"
    )
    print()
    print("Or set in the app Environment (Compute → Apps → payment-analysis → Edit → Environment):")
    print(f"  LAKEBASE_PROJECT_ID={project_id}")
    print(f"  LAKEBASE_BRANCH_ID={branch_id}")
    print(f"  LAKEBASE_ENDPOINT_ID={endpoint_id}")

    # Optionally update job base_parameters
    if args.job_id:
        job_id_str = args.job_id.strip()
        print(f"\nUpdating job {job_id_str} base_parameters...")
        try:
            job_id_int = int(job_id_str)
            job = w.jobs.get(job_id=job_id_int)
            tasks = list(job.settings.tasks or [])
            updated = False
            for t in tasks:
                if t.task_key == "lakebase_data_init" and getattr(t, "notebook_task", None):
                    params = dict(t.notebook_task.base_parameters or {})
                    params["lakebase_project_id"] = project_id
                    params["lakebase_branch_id"] = branch_id
                    params["lakebase_endpoint_id"] = endpoint_id
                    t.notebook_task.base_parameters = params
                    updated = True
                    break
            if updated:
                w.jobs.update(job_id=job_id_int, new_settings=job.settings)
                print("  Job base_parameters updated.")
            else:
                print("  No task 'lakebase_data_init' found; job not modified.")
        except Exception as e:
            print(f"  Warning: could not update job: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
