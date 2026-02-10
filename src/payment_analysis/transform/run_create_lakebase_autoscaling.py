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

# ---------------------------------------------------------------------------
# Resource paths (hierarchical naming per docs)
# See: https://docs.databricks.com/aws/en/oltp/projects/api-usage#resource-naming
# ---------------------------------------------------------------------------
project_name = f"projects/{lakebase_project_id}"
branch_name = f"{project_name}/branches/{lakebase_branch_id}"
endpoint_name = f"{branch_name}/endpoints/{lakebase_endpoint_id}"


def _resource_exists(get_fn) -> bool:
    """Return True if a Lakebase resource can be fetched (NotFound → False)."""
    try:
        get_fn()
        return True
    except NotFound:
        return False


def _is_already_exists(exc: Exception) -> bool:
    """Detect 'already exists' / 409-Conflict race conditions."""
    msg = str(exc).lower()
    return "already exists" in msg or "409" in msg or "conflict" in msg


# ---------------------------------------------------------------------------
# 1. Create project (idempotent)
# SDK: postgres_api.get_project(name="projects/{id}")
# SDK: postgres_api.create_project(project=Project, project_id=str) → LRO
# ---------------------------------------------------------------------------
print(f"Creating project {lakebase_project_id!r}...")
if _resource_exists(lambda: postgres_api.get_project(name=project_name)):
    print(f"  Project {lakebase_project_id!r} already exists, skipping.")
else:
    project_spec = ProjectSpec(display_name="payment-analysis-db", pg_version=17)
    project = Project(spec=project_spec)
    try:
        result = postgres_api.create_project(project=project, project_id=lakebase_project_id).wait()
        print(f"  ✓ Created project: {getattr(result, 'name', lakebase_project_id)}")
    except Exception as e:
        if _is_already_exists(e):
            print(f"  Project {lakebase_project_id!r} already exists (race), skipping.")
        else:
            raise RuntimeError(f"Failed to create project {lakebase_project_id!r}: {e}") from e

# ---------------------------------------------------------------------------
# 2. Create branch (idempotent)
# SDK: postgres_api.get_branch(name="projects/{id}/branches/{id}")
# SDK: postgres_api.create_branch(parent, branch, branch_id) → LRO
# ---------------------------------------------------------------------------
print(f"Creating branch {lakebase_branch_id!r} in {project_name}...")
if _resource_exists(lambda: postgres_api.get_branch(name=branch_name)):
    print(f"  Branch {lakebase_branch_id!r} already exists, skipping.")
else:
    branch_spec = BranchSpec(no_expiry=True)
    branch = Branch(spec=branch_spec)
    try:
        result = postgres_api.create_branch(parent=project_name, branch=branch, branch_id=lakebase_branch_id).wait()
        print(f"  ✓ Created branch: {getattr(result, 'name', lakebase_branch_id)}")
    except Exception as e:
        if _is_already_exists(e):
            print(f"  Branch {lakebase_branch_id!r} already exists (race), skipping.")
        else:
            raise RuntimeError(f"Failed to create branch {lakebase_branch_id!r}: {e}") from e

# ---------------------------------------------------------------------------
# 3. Create endpoint / compute (idempotent, read-write)
# SDK: postgres_api.get_endpoint(name="projects/.../endpoints/{id}")
# SDK: postgres_api.create_endpoint(parent, endpoint, endpoint_id) → LRO
# Docs recommend setting autoscaling_limit_max_cu in EndpointSpec.
# ---------------------------------------------------------------------------
print(f"Creating endpoint {lakebase_endpoint_id!r} in {branch_name}...")
if _resource_exists(lambda: postgres_api.get_endpoint(name=endpoint_name)):
    print(f"  Endpoint {lakebase_endpoint_id!r} already exists, skipping.")
else:
    endpoint_spec = EndpointSpec(
        endpoint_type=EndpointType.ENDPOINT_TYPE_READ_WRITE,
        autoscaling_limit_max_cu=4.0,
    )
    endpoint = Endpoint(spec=endpoint_spec)
    try:
        result = postgres_api.create_endpoint(
            parent=branch_name, endpoint=endpoint, endpoint_id=lakebase_endpoint_id,
        ).wait()
        print(f"  ✓ Created endpoint: {getattr(result, 'name', lakebase_endpoint_id)}")
    except Exception as e:
        if _is_already_exists(e):
            print(f"  Endpoint {lakebase_endpoint_id!r} already exists (race), skipping.")
        else:
            raise RuntimeError(f"Failed to create endpoint {lakebase_endpoint_id!r}: {e}") from e

# ---------------------------------------------------------------------------
# 4. Wait for endpoint to be ready (host assigned)
#
# Per the official SDK docs (manage-computes):
#   endpoint.status.hosts.host   → connection hostname (string)
#   endpoint.status.current_state → state enum / string
#
# The docs note: "In the SDK, access the host via endpoint.status.hosts.host
# (not endpoint.status.host)."
# ---------------------------------------------------------------------------
max_wait = 600
interval = 10
elapsed = 0

print(f"Waiting for endpoint to be ready: {endpoint_name}")

while elapsed < max_wait:
    try:
        ep = postgres_api.get_endpoint(name=endpoint_name)

        # Safety: status might not be populated yet
        if not hasattr(ep, "status") or ep.status is None:
            print(f"  [{elapsed}s] Endpoint found but status not yet available")
            time.sleep(interval)
            elapsed += interval
            continue

        status = ep.status

        # Host: status.hosts.host (per SDK docs, plural then singular)
        hosts_obj = getattr(status, "hosts", None)
        host = getattr(hosts_obj, "host", None) if hosts_obj else None

        # State: status.current_state (per SDK docs)
        state = getattr(status, "current_state", None) or getattr(status, "state", "UNKNOWN")

        print(f"  [{elapsed}s] State: {state}, Host: {host or 'not assigned yet'}")

        if host:
            print(f"✓ Endpoint ready after {elapsed}s!")
            print(f"  Connection host: {host}")
            print(f"  State: {state}")
            break

        # Fail fast on terminal error states
        state_upper = str(state).upper()
        if "FAILED" in state_upper or "ERROR" in state_upper:
            raise RuntimeError(
                f"Endpoint {endpoint_name!r} entered failed state: {state}. "
                "Check Compute → Lakebase in the workspace for details."
            )

    except NotFound:
        print(f"  [{elapsed}s] Endpoint not found in registry yet (still provisioning)")
    except RuntimeError:
        raise
    except Exception as e:
        print(f"  [{elapsed}s] Warning: {type(e).__name__}: {e}")

    time.sleep(interval)
    elapsed += interval
else:
    # Timeout — collect final state for diagnostics
    print(f"⚠ Timeout after {max_wait}s")
    print(f"Check Lakebase UI: Compute → Lakebase → {lakebase_project_id}")
    try:
        ep = postgres_api.get_endpoint(name=endpoint_name)
        if hasattr(ep, "status") and ep.status:
            hosts_obj = getattr(ep.status, "hosts", None)
            final_host = getattr(hosts_obj, "host", None) if hosts_obj else None
            final_state = getattr(ep.status, "current_state", None) or getattr(ep.status, "state", "UNKNOWN")
            print(f"  Final state: {final_state}, Host: {final_host or 'not assigned'}")
    except Exception as ex:
        print(f"  Could not retrieve final status: {ex}")

    raise RuntimeError(
        f"Endpoint {endpoint_name!r} did not become ready within {max_wait}s. "
        "Check Compute → Lakebase in the workspace; the endpoint may still be starting. "
        f"Project: {lakebase_project_id}, Branch: {lakebase_branch_id}, Endpoint: {lakebase_endpoint_id}"
    )

# COMMAND ----------

print()
print("Lakebase Autoscaling ready. Next task (lakebase_data_init) will use these IDs:")
print(f"  lakebase_project_id={lakebase_project_id}")
print(f"  lakebase_branch_id={lakebase_branch_id}")
print(f"  lakebase_endpoint_id={lakebase_endpoint_id}")
print("Create Lakebase Autoscaling completed successfully.")
