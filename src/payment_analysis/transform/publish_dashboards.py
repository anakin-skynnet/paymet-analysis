# Databricks notebook source
# MAGIC %md
# MAGIC # Publish Dashboards (Embed Credentials)
# MAGIC
# MAGIC Lists AI/BI dashboards under the given workspace path and publishes each with embed credentials
# MAGIC so they can be embedded in the app UI. Run after bundle deploy or when you need to refresh
# MAGIC published state. Uses Databricks AI/BI Dashboards (see https://learn.microsoft.com/en-us/azure/databricks/ai-bi/).
# MAGIC
# MAGIC **Widgets:** `dashboards_path` (required), `catalog`, `schema` (optional; used to run prepare if path is missing).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resolve path and run prepare if missing

# COMMAND ----------

import os
import subprocess
import sys

from databricks.sdk.errors import ResourceDoesNotExist
from databricks.sdk import WorkspaceClient

def _get_widget(name: str, default: str = "") -> str:
    try:
        v = dbutils.widgets.get(name)  # type: ignore[name-defined]  # noqa: F821
        return (v or "").strip() or default
    except Exception:
        return default

dashboards_path = _get_widget("dashboards_path")
if not dashboards_path:
    raise ValueError("Widget dashboards_path is required (e.g. /Workspace/Users/.../payment-analysis/dashboards)")

catalog = _get_widget("catalog", "ahs_demos_catalog")
schema = _get_widget("schema", "payment_analysis")

w = WorkspaceClient()

# If the dashboards folder does not exist (e.g. publish ran without prepare), run prepare first.
try:
    list(w.workspace.list(path=dashboards_path))
except ResourceDoesNotExist:
    workspace_path = os.path.dirname(dashboards_path)
    print(f"Path {dashboards_path!r} not found. Running prepare from {workspace_path!r} with catalog={catalog!r}, schema={schema!r}.")
    os.chdir(workspace_path)
    r = subprocess.run(
        [sys.executable, "scripts/dashboards.py", "prepare", "--catalog", catalog, "--schema", schema],
        capture_output=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Prepare failed with exit code {r.returncode}. Run prepare_dashboards task first or fix catalog/schema.")
    print("Prepare completed. Proceeding to list and publish.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## List and publish

# COMMAND ----------

from typing import cast

published = 0
failed = []

for obj in w.workspace.list(path=dashboards_path):
    if getattr(obj, "object_type", None) == "DASHBOARD" and getattr(obj, "resource_id", None):
        did = cast(str, obj.resource_id)
        name = (getattr(obj, "path", None) or "").split("/")[-1] or did
        try:
            # AI/BI Dashboards API (lakeview namespace in SDK)
            w.lakeview.publish(dashboard_id=did, embed_credentials=True)
            published += 1
            print(f"Published: {name} ({did})")
        except Exception as e:
            failed.append((name, str(e)))
            print(f"Failed: {name} — {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print(f"Published {published} dashboard(s).")
if failed:
    print(f"Failed {len(failed)}: {failed}")
    raise RuntimeError(f"Publish failed for {len(failed)} dashboard(s)")
