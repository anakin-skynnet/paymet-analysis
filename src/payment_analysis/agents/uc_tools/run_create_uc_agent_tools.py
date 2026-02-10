"""
Create Unity Catalog functions for Databricks Agent Framework (code-based).

Run from a Databricks job or notebook with catalog/schema set (e.g. widget or env).
Requires: gold views and payments_enriched_silver in the given catalog.schema.
Creates: catalog.schema.* functions (same schema as data) used by LangGraph agents via UCFunctionToolkit.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


def _sql_path() -> Path:
    return Path(__file__).resolve().parent / "uc_agent_tools.sql"


def run(catalog: str, schema: str) -> None:
    """Execute UC agent tools DDL with catalog/schema substitution."""
    sql_path = _sql_path()
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    raw = sql_path.read_text()
    sql_text = raw.replace("__CATALOG__", catalog).replace("__SCHEMA__", schema)

    # Split into statements: semicolon followed by newline or end
    parts = re.split(r";\s*(?=\n|$)", sql_text)
    statements = [s.strip() for s in parts if s.strip()]

    try:
        spark  # noqa: F821  # injected in Databricks
    except NameError:
        raise RuntimeError("run_create_uc_agent_tools must run in a Databricks context (spark available)")

    for stmt in statements:
        if not stmt.strip():
            continue
        spark.sql(stmt)

    print(f"Created {len(statements)} UC agent tool functions in {catalog}.{schema}")


def main() -> None:
    """Entrypoint: read catalog/schema from env, Databricks widget, or CLI."""
    catalog = os.environ.get("CATALOG", "").strip()
    schema = os.environ.get("SCHEMA", "").strip()
    try:
        dbutils  # noqa: F821
        catalog = catalog or dbutils.widgets.get("catalog", "")
        schema = schema or dbutils.widgets.get("schema", "")
    except NameError:
        pass
    if not catalog or not schema:
        parser = argparse.ArgumentParser(description="Create UC agent tool functions in catalog.schema (e.g. ahs_demos_catalog.payment_analysis)")
        parser.add_argument("--catalog", required=False, default="", help="Unity Catalog name")
        parser.add_argument("--schema", required=False, default="", help="Schema containing payments_enriched_silver and gold views")
        args = parser.parse_args()
        catalog = (catalog or args.catalog or "").strip()
        schema = (schema or args.schema or "").strip()
    if not catalog or not schema:
        raise ValueError("Set CATALOG and SCHEMA (env, notebook widgets 'catalog' and 'schema', or --catalog/--schema)")
    run(catalog, schema)


if __name__ == "__main__":
    main()
