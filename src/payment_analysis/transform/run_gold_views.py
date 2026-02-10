# Databricks notebook source
# MAGIC %md
# MAGIC # Run Gold Views
# MAGIC
# MAGIC Reads `gold_views.sql` from the synced workspace, prepends `USE CATALOG` / `USE SCHEMA`
# MAGIC from job parameters, and executes each statement. Does not depend on `.build/` so the job
# MAGIC works after any bundle deploy (with `src/payment_analysis/transform` synced).
# MAGIC
# MAGIC **Widgets:** `workspace_path` (repo root under workspace, e.g. .../files), `catalog`, `schema`.

# COMMAND ----------

import os

workspace_path = dbutils.widgets.get("workspace_path")  # type: ignore[name-defined]  # noqa: F821
catalog = dbutils.widgets.get("catalog")  # type: ignore[name-defined]  # noqa: F821
schema = dbutils.widgets.get("schema")  # type: ignore[name-defined]  # noqa: F821

if not workspace_path or not catalog or not schema:
    raise ValueError("Widgets workspace_path, catalog, and schema are required")

sql_path = os.path.join(workspace_path, "src", "payment_analysis", "transform", "gold_views.sql")
if not os.path.isfile(sql_path):
    raise FileNotFoundError(f"Gold views SQL not found at {sql_path}. Ensure bundle sync includes src/payment_analysis/transform and job passes workspace_path.")

with open(sql_path, encoding="utf-8") as f:
    content = f.read()

# Validate catalog/schema exist before running (clear error if not)
try:
    spark.sql(f"USE CATALOG `{catalog}`")  # type: ignore[name-defined]
    spark.sql(f"USE SCHEMA `{schema}`")  # type: ignore[name-defined]
except Exception as e:
    if "CATALOG_NOT_FOUND" in str(e) or "Schema" in str(e) or "not found" in str(e).lower():
        raise RuntimeError(
            f"Catalog {catalog!r} or schema {schema!r} not found in this workspace. "
            "Create the Unity Catalog and schema (see docs/DEPLOYMENT.md), or run the job with notebook_params catalog=<your_catalog> schema=<your_schema>."
        ) from e
    raise

# Gold views depend on the silver table produced by the Lakeflow ETL pipeline
if not spark.catalog.tableExists("payments_enriched_silver"):  # type: ignore[name-defined]
    raise RuntimeError(
        f"The table payments_enriched_silver was not found in {catalog}.{schema}. "
        "Gold views require the silver table from the Lakeflow pipeline. "
        "Run the pipeline 'Payment Analysis ETL' (Step 8 in Setup & Run, or pipelines payment_analysis_etl) so that "
        "payments_enriched_silver (and payments_raw_bronze) exist in this catalog and schema, then re-run this job."
    )

header = f"USE CATALOG {catalog};\nUSE SCHEMA {schema};\n\n"
full_sql = header + content

# Split into statements (semicolon at end of line); skip empty and comment-only.
statements = []
for part in full_sql.replace("\r\n", "\n").split(";\n"):
    stmt = part.strip()
    if not stmt:
        continue
    lines = [line for line in stmt.split("\n") if line.strip() and not line.strip().startswith("--")]
    if not lines:
        continue
    statements.append(stmt + ";")

print(f"Executing {len(statements)} SQL statements in {catalog}.{schema} ...")

# COMMAND ----------

succeeded = 0
for i, stmt in enumerate(statements):
    try:
        spark.sql(stmt)  # type: ignore[name-defined]
        succeeded += 1
        print(f"  [{succeeded}/{len(statements)}] OK")
    except Exception as e:
        err_msg = str(e)
        if "TABLE_OR_VIEW_NOT_FOUND" in err_msg or "42P01" in err_msg or "cannot be found" in err_msg:
            raise RuntimeError(
                f"Gold views failed: a required table or view is missing ({err_msg[:200]}...). "
                "Ensure Job 1 (Create Data Repositories) has run and the Lakeflow pipeline has produced "
                "payments_enriched_silver (and other silver/bronze tables). Then re-run this job."
            ) from e
        print(f"  [{i + 1}/{len(statements)}] FAILED: {stmt[:80]}...")
        raise

print(f"\n✓ Gold views completed: {succeeded}/{len(statements)} statements executed in {catalog}.{schema}")
