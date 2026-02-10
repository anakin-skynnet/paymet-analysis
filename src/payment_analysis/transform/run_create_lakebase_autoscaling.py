# Databricks notebook source
# MAGIC %md
# MAGIC # Create Lakebase Autoscaling
# MAGIC
# MAGIC Creates the Lakebase Autoscaling **project**, **branch**, and **endpoint** (compute) so that the next task
# MAGIC (**lakebase_data_init**) can connect and insert default app_config, approval_rules, online_features, and app_settings.
# MAGIC Run as the second task of Job 1 (after ensure_catalog_schema). Idempotent: skips creation if resources already exist.
# MAGIC
# MAGIC **Widgets:** `lakebase_project_id`, `lakebase_branch_id`, `lakebase_endpoint_id` (same as lakebase_data_init; set from bundle vars).
# MAGIC See: https://docs.databricks.com/oltp/projects/ and https://docs.databricks.com/oltp/projects/api-usage

# COMMAND ----------

# MAGIC %pip install "databricks-sdk==0.85.0" --quiet

# COMMAND ----------

def _get_widget(name: str, default: str = "") -> str:
    try:
        return (dbutils.widgets.get(name) or "").strip()  # type: ignore[name-defined]  # noqa: F821
    except Exception:
        return default

lakebase_project_id = _get_widget("lakebase_project_id")
lakebase_branch_id = _get_widget("lakebase_branch_id")
lakebase_endpoint_id = _get_widget("lakebase_endpoint_id")

if not lakebase_project_id or not lakebase_branch_id or not lakebase_endpoint_id:
    raise ValueError(
        "Widgets lakebase_project_id, lakebase_branch_id, and lakebase_endpoint_id are required. "
        "Set them in the job base_parameters (from bundle vars) or run scripts/create_lakebase_autoscaling.py first."
    )

# COMMAND ----------

import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.postgres import (
    Branch,
    BranchSpec,
    Endpoint,
    EndpointSpec,
    EndpointType,
    Project,
    ProjectSpec,
)

ws = WorkspaceClient()
postgres_api = getattr(ws, "postgres", None)
if postgres_api is None:
    raise AttributeError(
        "WorkspaceClient has no attribute 'postgres'. Lakebase Autoscaling API requires databricks-sdk==0.85.0 "
        "and a workspace with Lakebase Autoscaling enabled."
    )

# Create project
print(f"Creating project {lakebase_project_id!r}...")
project_spec = ProjectSpec(display_name="payment-analysis-db", pg_version=17)
project = Project(spec=project_spec)
try:
    op = postgres_api.create_project(project=project, project_id=lakebase_project_id)
    result = op.wait()
    print(f"  Created project: {getattr(result, 'name', lakebase_project_id)}")
except Exception as e:
    if "already exists" in str(e).lower() or "409" in str(e):
        print(f"  Project {lakebase_project_id!r} already exists, skipping.")
    else:
        raise

# Create branch
parent_project = f"projects/{lakebase_project_id}"
print(f"Creating branch {lakebase_branch_id!r} in {parent_project}...")
branch_spec = BranchSpec(no_expiry=True)
branch = Branch(spec=branch_spec)
try:
    op = postgres_api.create_branch(parent=parent_project, branch=branch, branch_id=lakebase_branch_id)
    result = op.wait()
    print(f"  Created branch: {getattr(result, 'name', lakebase_branch_id)}")
except Exception as e:
    if "already exists" in str(e).lower() or "409" in str(e):
        print(f"  Branch {lakebase_branch_id!r} already exists, skipping.")
    else:
        raise

# Create endpoint (read-write compute)
parent_branch = f"projects/{lakebase_project_id}/branches/{lakebase_branch_id}"
endpoint_name = f"{parent_branch}/endpoints/{lakebase_endpoint_id}"
print(f"Creating endpoint {lakebase_endpoint_id!r} in {parent_branch}...")
endpoint_spec = EndpointSpec(endpoint_type=EndpointType.ENDPOINT_TYPE_READ_WRITE)
endpoint = Endpoint(spec=endpoint_spec)
try:
    op = postgres_api.create_endpoint(
        parent=parent_branch, endpoint=endpoint, endpoint_id=lakebase_endpoint_id
    )
    result = op.wait()
    print(f"  Created endpoint: {getattr(result, 'name', lakebase_endpoint_id)}")
except Exception as e:
    if "already exists" in str(e).lower() or "409" in str(e):
        print(f"  Endpoint {lakebase_endpoint_id!r} already exists, skipping.")
    else:
        raise

# Wait for endpoint to be visible (get_endpoint) and ready (host available) so lakebase_data_init can connect
max_wait = 600
interval = 10
elapsed = 0

print("Waiting for endpoint to be ready...")

while elapsed < max_wait:
    try:
        ep = postgres_api.get_endpoint(name=endpoint_name)

        # Endpoint found - check if it has a host
        host = getattr(ep.status, "host", None) if hasattr(ep, "status") else None
        state = getattr(ep.status, "state", "UNKNOWN") if hasattr(ep, "status") else "UNKNOWN"

        print(f"  [{elapsed}s] State: {state}, Host: {host or 'not assigned yet'}")

        if host:
            print(f"✓ Endpoint ready after {elapsed}s!")
            print(f"  Connection host: {host}")
            break

    except NotFound:
        print(f"  [{elapsed}s] Endpoint not found in registry yet")
    except Exception as e:
        print(f"  [{elapsed}s] Error: {e}")

    time.sleep(interval)
    elapsed += interval
else:
    print(f"⚠ Timeout after {max_wait}s")
    print(f"Check Lakebase UI: Compute → Lakebase → {lakebase_project_id}")
    raise RuntimeError(
        f"Endpoint {endpoint_name!r} did not become ready within {max_wait}s. "
        "Check Compute → Lakebase in the workspace; the endpoint may still be starting."
    )

# COMMAND ----------

print()
print("Lakebase Autoscaling ready. Next task (lakebase_data_init) will use these IDs:")
print(f"  lakebase_project_id={lakebase_project_id}")
print(f"  lakebase_branch_id={lakebase_branch_id}")
print(f"  lakebase_endpoint_id={lakebase_endpoint_id}")
print("Create Lakebase Autoscaling completed successfully.")
