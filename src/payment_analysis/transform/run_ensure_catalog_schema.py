# Databricks notebook source
# MAGIC %md
# MAGIC # Ensure Unity Catalog and Schema
# MAGIC
# MAGIC Creates the catalog and schema if they do not exist (idempotent). Use as the first task of Job 1
# MAGIC so the lakehouse bootstrap and downstream jobs have a place to create tables. Requires metastore
# MAGIC admin or CREATE_CATALOG / CREATE_SCHEMA privileges.
# MAGIC
# MAGIC **Widgets:** `catalog`, `schema`.

# COMMAND ----------

def _get_widget(name: str, default: str = "") -> str:
    try:
        return (dbutils.widgets.get(name) or "").strip()  # type: ignore[name-defined]  # noqa: F821
    except Exception:
        return default

catalog = _get_widget("catalog")
schema = _get_widget("schema")

if not catalog or not schema:
    raise ValueError("Widgets catalog and schema are required")

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Ensure catalog exists
try:
    w.catalogs.get(name=catalog)
    print(f"Catalog {catalog!r} already exists.")
except Exception as e:
    if "CATALOG_NOT_FOUND" in str(e) or "does not exist" in str(e).lower() or "404" in str(e):
        w.catalogs.create(name=catalog, comment="Payment analysis lakehouse catalog")
        print(f"Created catalog {catalog!r}.")
    else:
        raise

# Ensure schema exists
full_schema_name = f"{catalog}.{schema}"
try:
    w.schemas.get(full_name=full_schema_name)
    print(f"Schema {full_schema_name!r} already exists.")
except Exception as e:
    if "SCHEMA_NOT_FOUND" in str(e) or "does not exist" in str(e).lower() or "404" in str(e):
        w.schemas.create(name=schema, catalog_name=catalog, comment="Payment analysis lakehouse schema")
        print(f"Created schema {full_schema_name!r}.")
    else:
        raise

print("Ensure catalog and schema completed successfully.")
