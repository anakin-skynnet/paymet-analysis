# Databricks notebook source
# MAGIC %md
# MAGIC # Run Lakehouse Bootstrap
# MAGIC
# MAGIC Reads `lakehouse_bootstrap.sql` from the synced workspace, prepends `USE CATALOG` / `USE SCHEMA`
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

sql_path = os.path.join(workspace_path, "src", "payment_analysis", "transform", "lakehouse_bootstrap.sql")
if not os.path.isfile(sql_path):
    raise FileNotFoundError(f"Lakehouse bootstrap SQL not found at {sql_path}. Ensure bundle sync includes src/payment_analysis/transform and job passes workspace_path.")

with open(sql_path, encoding="utf-8") as f:
    content = f.read()

header = f"USE CATALOG {catalog};\nUSE SCHEMA {schema};\n\n"
full_sql = header + content

# Split into statements (semicolon at end of line); skip empty and comment-only.
statements = []
for part in full_sql.replace("\r\n", "\n").split(";\n"):
    stmt = part.strip()
    if not stmt:
        continue
    # Skip blocks that are only comments/whitespace
    lines = [line for line in stmt.split("\n") if line.strip() and not line.strip().startswith("--")]
    if not lines:
        continue
    statements.append(stmt + ";")

# COMMAND ----------

for i, stmt in enumerate(statements):
    try:
        spark.sql(stmt)  # type: ignore[name-defined]
        print(f"Executed statement {i + 1}/{len(statements)}")
    except Exception as e:
        print(f"Statement {i + 1} failed: {stmt[:80]}...")
        raise

print("Lakehouse bootstrap completed successfully.")
