# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase Data Initialization
# MAGIC
# MAGIC Runs **after** the **create_lakebase_autoscaling** task. Connects to Lakebase Autoscaling and seeds the database with:
# MAGIC - **app_config** (catalog, schema for the app)
# MAGIC - **approval_rules** (default rules: 3DS for high value, retry soft decline, primary acquirer routing)
# MAGIC - **online_features** (table created; ML/AI features populated by pipelines and app)
# MAGIC - **app_settings** (warehouse_id, default_events_per_second, default_duration_minutes, etc.)
# MAGIC Backend reads these tables at startup. Ensures defaults exist before Lakehouse bootstrap and app use.
# MAGIC
# MAGIC **Widgets:** `catalog`, `schema`; **Lakebase Autoscaling** (`lakebase_project_id`, `lakebase_branch_id`, `lakebase_endpoint_id`). Also `lakebase_database_name`, `lakebase_schema`; optional `warehouse_id`, `default_events_per_second`, `default_duration_minutes` for app_settings.
# MAGIC See: https://docs.databricks.com/oltp/projects/

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]==3.2.3" "databricks-sdk==0.85.0" --quiet

# COMMAND ----------

import uuid

def _get_widget(name: str, default: str = "") -> str:
    try:
        return (dbutils.widgets.get(name) or "").strip()  # type: ignore[name-defined]  # noqa: F821
    except Exception:
        return default

catalog = _get_widget("catalog")
schema = _get_widget("schema")
lakebase_project_id = _get_widget("lakebase_project_id")
lakebase_branch_id = _get_widget("lakebase_branch_id")
lakebase_endpoint_id = _get_widget("lakebase_endpoint_id")
lakebase_database_name = _get_widget("lakebase_database_name") or "payment_analysis"
lakebase_schema = _get_widget("lakebase_schema") or "payment_analysis"
warehouse_id = _get_widget("warehouse_id") or ""
default_events_per_second = _get_widget("default_events_per_second") or "1000"
default_duration_minutes = _get_widget("default_duration_minutes") or "60"

if not catalog or not schema:
    raise ValueError("Widgets catalog and schema are required")
if not lakebase_project_id or not lakebase_branch_id or not lakebase_endpoint_id:
    raise ValueError(
        "Lakebase Autoscaling required: set lakebase_project_id, lakebase_branch_id, lakebase_endpoint_id "
        "(from Job 1 create_lakebase_autoscaling). See https://docs.databricks.com/oltp/projects/"
    )

# COMMAND ----------

import re
import time as _time

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

ws = WorkspaceClient()
port = 5432

# Lakebase Autoscaling (Postgres API): projects/branches/endpoints
postgres_api = getattr(ws, "postgres", None)
if postgres_api is None:
    raise AttributeError(
        "WorkspaceClient has no attribute 'postgres'. The Postgres (Lakebase Autoscaling) API requires "
        "databricks-sdk==0.85.0. Ensure the first notebook cell runs: %pip install \"databricks-sdk==0.85.0\" --quiet, "
        "then re-run the notebook; or use a cluster/job with a newer Databricks runtime that includes it."
    )
endpoint_name = f"projects/{lakebase_project_id}/branches/{lakebase_branch_id}/endpoints/{lakebase_endpoint_id}"
branch_name = f"projects/{lakebase_project_id}/branches/{lakebase_branch_id}"


# ---------------------------------------------------------------------------
# Validate schema name (prevent SQL injection in f-string queries below)
# ---------------------------------------------------------------------------
_SAFE_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
if not _SAFE_ID_RE.match(lakebase_schema):
    raise ValueError(f"Invalid lakebase_schema: {lakebase_schema!r}. Must be alphanumeric + underscores.")


def _discover_endpoint() -> str:
    """Discover the actual endpoint name on this branch.

    Lakebase auto-generates endpoint names (e.g. ep-broad-forest-xxx) when a
    project is created.  The configured lakebase_endpoint_id (e.g. 'primary')
    may not match the actual name.  Try the configured name first; if not
    found, list endpoints on the branch and use the first one."""
    # 1. Try configured name
    try:
        postgres_api.get_endpoint(name=endpoint_name)
        return endpoint_name
    except NotFound:
        pass

    # 2. List endpoints on the branch and pick the first one
    print(f"  Endpoint {lakebase_endpoint_id!r} not found. Discovering existing endpoints on {branch_name}...")
    endpoints = list(postgres_api.list_endpoints(parent=branch_name))
    for ep_item in endpoints:
        ep_n = getattr(ep_item, "name", "")
        ep_st = getattr(ep_item, "status", None)
        state = getattr(ep_st, "current_state", "?") if ep_st else "?"
        print(f"    Found: {ep_n} (state={state})")

    if endpoints:
        actual = getattr(endpoints[0], "name", "")
        print(f"  Using endpoint: {actual}")
        return actual

    raise RuntimeError(
        f"No endpoints found on branch {branch_name!r}. "
        "Run Job 1 task create_lakebase_autoscaling first, or create a Lakebase endpoint "
        "in Compute → Lakebase. See https://docs.databricks.com/oltp/projects/"
    )


# ---------------------------------------------------------------------------
# Retry get_endpoint (eventual consistency / endpoint just created)
# Uses endpoint discovery to handle auto-generated endpoint names.
# ---------------------------------------------------------------------------
max_attempts = 5
endpoint = None
cred = None
actual_endpoint_name = None

for attempt in range(max_attempts):
    try:
        actual_endpoint_name = _discover_endpoint()
        endpoint = postgres_api.get_endpoint(name=actual_endpoint_name)
        cred = postgres_api.generate_database_credential(endpoint=actual_endpoint_name)
        break
    except NotFound:
        if attempt == max_attempts - 1:
            raise RuntimeError(
                f"Lakebase endpoint not found after {max_attempts} attempts: {endpoint_name!r}. "
                "Run Job 1 task create_lakebase_autoscaling first. "
                "See https://docs.databricks.com/oltp/projects/"
            )
        print(f"  Endpoint not found (attempt {attempt + 1}/{max_attempts}), retrying in {10 * (attempt + 1)}s...")
        _time.sleep(10 * (attempt + 1))
    except Exception:
        raise

if endpoint is None or cred is None:
    raise RuntimeError("Failed to get Lakebase endpoint and credential.")

token = cred.token

# Resolve host: endpoint.status.hosts.host (hosts is an object, not a list)
# Canonical impl: src/payment_analysis/backend/lakebase_helpers.py
host = getattr(getattr(getattr(endpoint, "status", None), "hosts", None), "host", None)
if not host:
    raise ValueError("Endpoint has no host; ensure the compute endpoint is running.")

# Autoscaling projects always have a "databricks_postgres" database.
# The lakebase_database_name widget may say "payment_analysis" — that's the Postgres schema, not the DB.
dbname = "databricks_postgres"
username = (ws.current_user.me().user_name if ws.current_user else None) or getattr(ws.config, "client_id", None) or "postgres"

# COMMAND ----------

import psycopg
from psycopg.rows import dict_row

conn_str = f"host={host} port={port} dbname={dbname} user={username} password={token} sslmode=require"
print("Connecting to Lakebase (Postgres)...")

with psycopg.connect(conn_str, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        # Create schema if not exists
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{lakebase_schema}"')
        conn.commit()
        print(f"Schema {lakebase_schema!r} ensured.")

        # App config: single row (id=1) with catalog and schema for the app
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".app_config (
                id INT PRIMARY KEY DEFAULT 1,
                catalog VARCHAR(255) NOT NULL,
                schema VARCHAR(255) NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        conn.commit()
        cur.execute(
            f"""
            INSERT INTO "{lakebase_schema}".app_config (id, catalog, schema)
            VALUES (1, %s, %s)
            ON CONFLICT (id) DO UPDATE SET catalog = EXCLUDED.catalog, schema = EXCLUDED.schema, updated_at = current_timestamp
            """,
            (catalog, schema),
        )
        conn.commit()
        print("Default app_config (catalog, schema) inserted or updated.")

        # Approval rules: same shape as Lakehouse table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".approval_rules (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(500) NOT NULL,
                rule_type VARCHAR(100) NOT NULL,
                condition_expression TEXT,
                action_summary TEXT NOT NULL,
                priority INT NOT NULL DEFAULT 100,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        conn.commit()

        # Seed default rules only when table is empty
        cur.execute(f'SELECT COUNT(*) AS n FROM "{lakebase_schema}".approval_rules')
        row = cur.fetchone()
        n = row["n"] if row and isinstance(row, dict) else (row[0] if row else 0)
        if n == 0:
            defaults = [
                (
                    str(uuid.uuid4()),
                    "Default 3DS for high value",
                    "authentication",
                    "amount_cents >= 50000",
                    "Require 3DS for transactions >= 500.00; reduces fraud and false declines",
                    100,
                ),
                (
                    str(uuid.uuid4()),
                    "Retry after soft decline",
                    "retry",
                    "decline_reason IN ('INSUFFICIENT_FUNDS','TEMPORARY_FAILURE')",
                    "Retry once after 2h for soft declines; improves approval rate",
                    90,
                ),
                (
                    str(uuid.uuid4()),
                    "Primary acquirer routing",
                    "routing",
                    "merchant_country = 'BR'",
                    "Route Brazil e-commerce to primary acquirer; fallback to backup on timeout",
                    110,
                ),
            ]
            for rid, name, rule_type, cond, action, prio in defaults:
                cur.execute(
                    f"""
                    INSERT INTO "{lakebase_schema}".approval_rules (id, name, rule_type, condition_expression, action_summary, priority, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, true)
                    """,
                    (rid, name, rule_type, cond, action, prio),
                )
            conn.commit()
            print(f"Inserted {len(defaults)} default approval rules.")
        else:
            print("approval_rules already has rows; skipping default rules.")

        # Online features: ML/AI output for app Dashboard (same shape as Lakehouse)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".online_features (
                id VARCHAR(255) NOT NULL,
                source VARCHAR(100) NOT NULL,
                feature_set VARCHAR(255),
                feature_name VARCHAR(255) NOT NULL,
                feature_value DOUBLE PRECISION,
                feature_value_str VARCHAR(500),
                entity_id VARCHAR(255),
                created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        conn.commit()
        print("online_features table ensured.")

        # App settings: key-value for job parameters and config (backend reads at startup)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".app_settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        conn.commit()
        settings_defaults = [
            ("catalog", catalog),
            ("schema", schema),
            ("warehouse_id", warehouse_id or "148ccb90800933a1"),
            ("default_events_per_second", default_events_per_second),
            ("default_duration_minutes", default_duration_minutes),
        ]
        for k, v in settings_defaults:
            cur.execute(
                f"""
                INSERT INTO "{lakebase_schema}".app_settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = current_timestamp
                """,
                (k, v),
            )
        conn.commit()
        print(f"app_settings seeded: {[k for k, _ in settings_defaults]}.")

print("Lakebase data initialization completed successfully.")
