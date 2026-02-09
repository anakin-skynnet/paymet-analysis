# Databricks notebook source
# MAGIC %md
# MAGIC # Publish Dashboards (Embed Credentials)
# MAGIC
# MAGIC Lists AI/BI dashboards under the given workspace path and publishes each with embed credentials
# MAGIC so they can be embedded in the app UI. Run after bundle deploy or when you need to refresh
# MAGIC published state. Uses Databricks AI/BI Dashboards (see https://learn.microsoft.com/en-us/azure/databricks/ai-bi/).
# MAGIC
# MAGIC **Widget:** `dashboards_path` — workspace path to the folder containing dashboard objects (e.g. `/Workspace/Users/.../payment-analysis/dashboards`).

# COMMAND ----------

# MAGIC %md
# MAGIC ## List and publish

# COMMAND ----------

from typing import cast

from databricks.sdk import WorkspaceClient

dashboards_path = dbutils.widgets.get("dashboards_path")  # type: ignore[name-defined]  # noqa: F821
if not dashboards_path:
    raise ValueError("Widget dashboards_path is required (e.g. /Workspace/Users/.../payment-analysis/dashboards)")

w = WorkspaceClient()
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
