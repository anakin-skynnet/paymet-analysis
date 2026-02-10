# Databricks notebook source
# MAGIC %md
# MAGIC # Publish Dashboards (Embed Credentials)
# MAGIC
# MAGIC Lists AI/BI dashboards under the given workspace path and publishes each with embed credentials
# MAGIC so they can be embedded in the app UI. Run after bundle deploy or when you need to refresh
# MAGIC published state. Uses Databricks AI/BI Dashboards (see https://learn.microsoft.com/en-us/azure/databricks/ai-bi/).
# MAGIC
# MAGIC **Widget:** `dashboards_path` — workspace path to the folder containing **DASHBOARD** objects (not just source files). DASHBOARD objects are created by `databricks bundle deploy` when `resources/dashboards.yml` is included; the prepare task only creates source `.lvdash.json` files.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resolve path and validate

# COMMAND ----------

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

w = WorkspaceClient()

# The path must exist and contain DASHBOARD objects. Prepare only creates source files; DASHBOARD objects are created by bundle deploy.
try:
    list(w.workspace.list(path=dashboards_path))
except ResourceDoesNotExist:
    raise RuntimeError(
        f"Path {dashboards_path!r} does not exist. "
        "Publish lists workspace DASHBOARD objects (created by databricks bundle deploy), not local files. "
        "Ensure (1) the prepare_dashboards task has run so the folder exists, (2) you have run `databricks bundle deploy` with resources/dashboards.yml uncommented in databricks.yml so dashboard resources are deployed and DASHBOARD objects exist in the workspace, then re-run this task."
    ) from None

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
