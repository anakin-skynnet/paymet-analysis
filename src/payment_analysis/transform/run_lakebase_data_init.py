# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase Data Initialization
# MAGIC
# MAGIC Runs **after** the **create_lakebase_autoscaling** task. Connects to Lakebase Autoscaling and seeds the database with:
# MAGIC - **app_config** (catalog, schema for the app)
# MAGIC - **approval_rules** (default rules: 3DS for high value, retry soft decline, primary acquirer routing)
# MAGIC - **online_features** (table created; ML/AI features populated by pipelines and app)
# MAGIC - **app_settings** (warehouse_id, default_events_per_second, default_duration_minutes, etc.)
# MAGIC - **countries** (entities for UI filter dropdown; same seed as Lakehouse)
# MAGIC Backend reads these tables at startup. Ensures defaults exist before Lakehouse bootstrap and app use.
# MAGIC To expose this Lakebase database in Unity Catalog (governance, SQL, dashboards), register it: Catalog Explorer → Create catalog → Lakebase Postgres (Autoscaling) → select project/branch/database.
# MAGIC
# MAGIC **Widgets:** `catalog`, `schema`; **Lakebase Autoscaling** (`lakebase_project_id`, `lakebase_branch_id`, `lakebase_endpoint_id`). Also `lakebase_database_name`, `lakebase_schema`; optional `warehouse_id`, `default_events_per_second`, `default_duration_minutes` for app_settings.
# MAGIC See: https://docs.databricks.com/oltp/projects/

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]==3.3.2" "databricks-sdk==0.88.0" --quiet

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
        "databricks-sdk>=0.88.0. Ensure the first notebook cell runs: %pip install \"databricks-sdk==0.88.0\" --quiet, "
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
            ("warehouse_id", warehouse_id or ""),
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

        # Decision config: tunable parameters for auth, retry, routing policies
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".decisionconfig (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        conn.commit()
        cur.execute(f'SELECT COUNT(*) AS n FROM "{lakebase_schema}".decisionconfig')
        row = cur.fetchone()
        n = row["n"] if row and isinstance(row, dict) else (row[0] if row else 0)
        if n == 0:
            decision_defaults = [
                ("risk_threshold_high", "0.75", "Risk score >= this → high risk tier (require step-up auth)"),
                ("risk_threshold_medium", "0.35", "Risk score >= this → medium risk tier (3DS frictionless)"),
                ("device_trust_low_risk", "0.90", "Device trust score >= this → low risk when no risk_score provided"),
                ("retry_max_attempts_control", "3", "Max retry attempts for control group"),
                ("retry_max_attempts_treatment", "4", "Max retry attempts for treatment group (A/B)"),
                ("retry_backoff_recurring_control", "900", "Backoff seconds for recurring soft declines (control)"),
                ("retry_backoff_recurring_treatment", "300", "Backoff seconds for recurring soft declines (treatment)"),
                ("retry_backoff_transient", "60", "Backoff seconds for transient issuer/system declines (91, 96)"),
                ("retry_backoff_soft_treatment", "1800", "Backoff seconds for do_not_honor soft decline (treatment)"),
                ("routing_domestic_country", "BR", "Domestic country code for routing preference"),
                ("ml_enrichment_enabled", "true", "Enable ML model score enrichment in decision flow"),
                ("ml_enrichment_timeout_ms", "2000", "Timeout for ML model calls during decision enrichment"),
                ("rule_engine_enabled", "true", "Enable Lakebase approval_rules evaluation in decision flow"),
            ]
            for key, value, desc in decision_defaults:
                cur.execute(
                    f"""
                    INSERT INTO "{lakebase_schema}".decisionconfig (key, value, description)
                    VALUES (%s, %s, %s)
                    """,
                    (key, value, desc),
                )
            conn.commit()
            print(f"Inserted {len(decision_defaults)} default decision config entries.")
        else:
            print("decisionconfig already has rows; skipping defaults.")

        # Retryable decline codes: configurable soft decline codes for Smart Retry
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".retryabledeclinecode (
                code VARCHAR(100) PRIMARY KEY,
                label VARCHAR(500) NOT NULL,
                category VARCHAR(50) NOT NULL DEFAULT 'soft',
                default_backoff_seconds INT NOT NULL DEFAULT 900,
                max_attempts INT NOT NULL DEFAULT 3,
                is_active BOOLEAN NOT NULL DEFAULT true,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        conn.commit()
        cur.execute(f'SELECT COUNT(*) AS n FROM "{lakebase_schema}".retryabledeclinecode')
        row = cur.fetchone()
        n = row["n"] if row and isinstance(row, dict) else (row[0] if row else 0)
        if n == 0:
            decline_defaults = [
                ("51", "Insufficient funds", "soft", 7200, 2),
                ("91", "Issuer unavailable", "transient", 60, 3),
                ("96", "System malfunction", "transient", 60, 3),
                ("try_again_later", "Try again later (generic)", "soft", 900, 3),
                ("do_not_honor_soft", "Do not honor (soft variant)", "soft", 1800, 2),
                ("FUNDS_OR_LIMIT", "Funds or limit (standardized)", "soft", 7200, 2),
                ("ISSUER_TECHNICAL", "Issuer technical (standardized)", "transient", 60, 3),
                ("TEMPORARY_FAILURE", "Temporary failure (standardized)", "transient", 120, 3),
            ]
            for code, label, cat, backoff, max_att in decline_defaults:
                cur.execute(
                    f"""
                    INSERT INTO "{lakebase_schema}".retryabledeclinecode (code, label, category, default_backoff_seconds, max_attempts)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (code, label, cat, backoff, max_att),
                )
            conn.commit()
            print(f"Inserted {len(decline_defaults)} default retryable decline codes.")
        else:
            print("retryabledeclinecode already has rows; skipping defaults.")

        # Route performance: historical performance per PSP route for smart routing
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".routeperformance (
                route_name VARCHAR(255) PRIMARY KEY,
                approval_rate_pct DOUBLE PRECISION NOT NULL DEFAULT 50.0,
                avg_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 500.0,
                cost_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
                is_active BOOLEAN NOT NULL DEFAULT true,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        conn.commit()
        cur.execute(f'SELECT COUNT(*) AS n FROM "{lakebase_schema}".routeperformance')
        row = cur.fetchone()
        n = row["n"] if row and isinstance(row, dict) else (row[0] if row else 0)
        if n == 0:
            route_defaults = [
                ("psp_primary", 72.5, 180.0, 0.3),
                ("psp_secondary", 68.0, 220.0, 0.5),
                ("psp_tertiary", 55.0, 350.0, 0.7),
            ]
            for rname, ar, lat, cost in route_defaults:
                cur.execute(
                    f"""
                    INSERT INTO "{lakebase_schema}".routeperformance (route_name, approval_rate_pct, avg_latency_ms, cost_score)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (rname, ar, lat, cost),
                )
            conn.commit()
            print(f"Inserted {len(route_defaults)} default route performance entries.")
        else:
            print("routeperformance already has rows; skipping defaults.")

        # Decision outcome: feedback loop linking decisions to actual outcomes
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".decisionoutcome (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
                audit_id VARCHAR(255) NOT NULL,
                decision_type VARCHAR(100) NOT NULL,
                outcome VARCHAR(100) NOT NULL,
                outcome_code VARCHAR(100),
                outcome_reason TEXT,
                latency_ms INT,
                extra JSONB NOT NULL DEFAULT '{{}}'::jsonb
            )
        """)
        conn.commit()
        cur.execute(f'CREATE INDEX IF NOT EXISTS idx_decisionoutcome_audit_id ON "{lakebase_schema}".decisionoutcome (audit_id)')
        cur.execute(f'CREATE INDEX IF NOT EXISTS idx_decisionoutcome_decision_type ON "{lakebase_schema}".decisionoutcome (decision_type)')
        conn.commit()
        print("decisionoutcome table ensured.")

        # Countries/entities: for UI filter dropdown (same as Lakehouse; editable by users)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{lakebase_schema}".countries (
                code VARCHAR(10) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                display_order INT NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        conn.commit()
        cur.execute(f'SELECT COUNT(*) AS n FROM "{lakebase_schema}".countries')
        row = cur.fetchone()
        n = row["n"] if row and isinstance(row, dict) else (row[0] if row else 0)
        if n == 0:
            defaults = [
                ("BR", "Brazil", 1),
                ("MX", "Mexico", 2),
                ("AR", "Argentina", 3),
                ("CL", "Chile", 4),
                ("CO", "Colombia", 5),
                ("PE", "Peru", 6),
                ("EC", "Ecuador", 7),
                ("UY", "Uruguay", 8),
                ("PY", "Paraguay", 9),
                ("BO", "Bolivia", 10),
            ]
            for code, name, display_order in defaults:
                cur.execute(
                    f"""
                    INSERT INTO "{lakebase_schema}".countries (code, name, display_order)
                    VALUES (%s, %s, %s)
                    """,
                    (code, name, display_order),
                )
            conn.commit()
            print(f"Inserted {len(defaults)} default countries.")
        else:
            print("countries already has rows; skipping seed.")

# ---------------------------------------------------------------------------
# Grant Postgres access to the Databricks App service principal
#
# The app runs as its own SP whose OAuth identity must have a Postgres role.
# We look up the app (by name) → get its SP → create a Lakebase OAuth role
# and grant full access on the data schema.  This is idempotent.
# ---------------------------------------------------------------------------

app_name = _get_widget("app_name") or "payment-analysis"

print(f"\nConfiguring Postgres role for Databricks App '{app_name}' service principal...")

_sp_app_id: str | None = None
try:
    _app = ws.apps.get(app_name)
    _sp_id = getattr(_app, "service_principal_id", None)
    if _sp_id:
        _sp = ws.service_principals.get(_sp_id)
        _sp_app_id = getattr(_sp, "application_id", None)
        print(f"  App SP: {_sp.display_name} (application_id={_sp_app_id})")
except Exception as e:
    print(f"  ⚠ Could not look up app '{app_name}': {e}")

if _sp_app_id:
    with psycopg.connect(conn_str, row_factory=dict_row) as conn2:
        with conn2.cursor() as cur2:
            # Ensure the databricks_auth extension is available
            cur2.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
            conn2.commit()

            # Create OAuth role for the SP (idempotent — catches "already exists")
            try:
                cur2.execute(
                    "SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')",
                    (_sp_app_id,),
                )
                conn2.commit()
                print(f"  ✓ Postgres role created for SP {_sp_app_id}")
            except Exception as role_err:
                conn2.rollback()
                if "already exists" in str(role_err).lower():
                    print(f"  Postgres role for SP already exists")
                else:
                    print(f"  ⚠ Could not create role: {role_err}")

            # Grant privileges on the data schema
            # (safe: lakebase_schema is validated above against _SAFE_ID_RE)
            try:
                cur2.execute(f'GRANT USAGE ON SCHEMA "{lakebase_schema}" TO "{_sp_app_id}"')
                cur2.execute(f'GRANT CREATE ON SCHEMA "{lakebase_schema}" TO "{_sp_app_id}"')
                cur2.execute(
                    f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{lakebase_schema}" TO "{_sp_app_id}"'
                )
                cur2.execute(
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{lakebase_schema}" '
                    f'GRANT ALL ON TABLES TO "{_sp_app_id}"'
                )
                conn2.commit()
                print(f"  ✓ Granted full access on schema '{lakebase_schema}' to SP")
            except Exception as grant_err:
                conn2.rollback()
                print(f"  ⚠ Could not grant privileges: {grant_err}")
else:
    print("  ⚠ Skipped: could not determine app service principal application_id")

print("\nLakebase data initialization completed successfully.")
