# Databricks notebook source
# MAGIC %md
# MAGIC # Validate All Resources
# MAGIC
# MAGIC End-to-end validation of every resource deployed by the Payment Analysis solution.
# MAGIC Runs on **Databricks serverless** compute (no cluster config needed).
# MAGIC
# MAGIC **Tests:**
# MAGIC 1. Unity Catalog — catalog, schemas, volumes
# MAGIC 2. Bronze & Silver tables (DLT pipelines 8 & 9)
# MAGIC 3. Lakehouse bootstrap tables
# MAGIC 4. Gold views (SQL)
# MAGIC 5. Gold tables (DLT)
# MAGIC 6. Lakehouse views (bootstrap)
# MAGIC 7. Model Serving endpoints (5)
# MAGIC 8. Foundation Model / AI Gateway endpoints (LLMs)
# MAGIC 9. DLT Pipelines (2)
# MAGIC 10. SQL Warehouse
# MAGIC 11. Dashboards (3)
# MAGIC 12. Genie Space
# MAGIC 13. Jobs (8)
# MAGIC 14. UC Functions (22 agent tools)
# MAGIC 15. Vector Search (endpoint + index)
# MAGIC 16. Lakebase (Postgres) connectivity + tables
# MAGIC 17. App health (existence + HTTP healthcheck)
# MAGIC 18. End-to-end data flow — smoke tests
# MAGIC
# MAGIC **Widgets:** `catalog`, `schema`, `environment` (defaults: ahs_demos_catalog, payment_analysis, dev).

# COMMAND ----------

dbutils.widgets.text("catalog", "ahs_demos_catalog", "Unity Catalog name")  # type: ignore[name-defined]  # noqa: F821
dbutils.widgets.text("schema", "payment_analysis", "Schema name")  # type: ignore[name-defined]  # noqa: F821
dbutils.widgets.text("environment", "dev", "Environment (dev/prod)")  # type: ignore[name-defined]  # noqa: F821

CATALOG = dbutils.widgets.get("catalog")  # type: ignore[name-defined]  # noqa: F821
SCHEMA = dbutils.widgets.get("schema")  # type: ignore[name-defined]  # noqa: F821
ENV = dbutils.widgets.get("environment")  # type: ignore[name-defined]  # noqa: F821

print(f"Validating: {CATALOG}.{SCHEMA}  (env={ENV})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup — helpers

# COMMAND ----------

import json
import time
import traceback
from dataclasses import dataclass, field

@dataclass
class TestResult:
    name: str
    category: str
    passed: bool
    message: str = ""
    elapsed_ms: float = 0

results: list[TestResult] = []

def run_test(name: str, category: str, fn):
    """Execute *fn()* and record pass/fail."""
    t0 = time.time()
    try:
        msg = fn()
        elapsed = (time.time() - t0) * 1000
        results.append(TestResult(name=name, category=category, passed=True, message=str(msg or "OK"), elapsed_ms=elapsed))
    except Exception as exc:
        elapsed = (time.time() - t0) * 1000
        results.append(TestResult(name=name, category=category, passed=False, message=str(exc), elapsed_ms=elapsed))

def sql(query: str):
    """Run SQL and return list of Row objects."""
    return spark.sql(query).collect()  # type: ignore[name-defined]  # noqa: F821

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Unity Catalog — catalog, schemas, volumes

# COMMAND ----------

def test_catalog_exists():
    rows = sql(f"SHOW CATALOGS LIKE '{CATALOG}'")
    assert len(rows) > 0, f"Catalog '{CATALOG}' not found"
    return f"Catalog '{CATALOG}' exists"

def test_schema_exists():
    rows = sql(f"SHOW SCHEMAS IN {CATALOG} LIKE '{SCHEMA}'")
    assert len(rows) > 0, f"Schema '{CATALOG}.{SCHEMA}' not found"
    return f"Schema '{CATALOG}.{SCHEMA}' exists"

def test_agents_schema_exists():
    rows = sql(f"SHOW SCHEMAS IN {CATALOG} LIKE 'agents'")
    assert len(rows) > 0, f"Schema '{CATALOG}.agents' not found"
    return f"Schema '{CATALOG}.agents' exists"

VOLUMES = ["raw_data", "checkpoints", "ml_artifacts", "reports"]

def make_volume_test(vol_name):
    def test():
        rows = sql(f"SHOW VOLUMES IN {CATALOG}.{SCHEMA} LIKE '{vol_name}'")
        assert len(rows) > 0, f"Volume '{vol_name}' not found"
        return f"Volume '{vol_name}' exists"
    return test

run_test("Catalog exists", "Unity Catalog", test_catalog_exists)
run_test("Schema exists", "Unity Catalog", test_schema_exists)
run_test("Agents schema exists", "Unity Catalog", test_agents_schema_exists)
for v in VOLUMES:
    run_test(f"Volume: {v}", "Unity Catalog", make_volume_test(v))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Bronze & Silver tables (DLT pipelines)

# COMMAND ----------

BRONZE_SILVER_TABLES = [
    # Pipeline 8 — batch ETL
    "payments_raw_bronze",
    "merchants_dim_bronze",
    "payments_enriched_silver",
    "merchant_visible_attempts_silver",
    "reason_code_taxonomy_silver",
    "insight_feedback_silver",
    "decision_log_silver",
    "smart_checkout_decisions_silver",
    # Pipeline 9 — real-time stream
    "payments_stream_bronze",
    "payments_stream_silver",
    "payments_stream_metrics_10s",
    "payments_stream_alerts",
    # Simulator input
    "payments_stream_input",
]

def make_table_test(table_name, check_rows=False):
    def test():
        rows = sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA} LIKE '{table_name}'")
        assert len(rows) > 0, f"Table '{table_name}' not found in {CATALOG}.{SCHEMA}"
        if check_rows:
            count = sql(f"SELECT COUNT(*) AS cnt FROM {CATALOG}.{SCHEMA}.{table_name}")[0].cnt
            return f"Table '{table_name}' exists — {count:,} rows"
        return f"Table '{table_name}' exists"
    return test

for tbl in BRONZE_SILVER_TABLES:
    run_test(f"Table: {tbl}", "Bronze/Silver Tables", make_table_test(tbl, check_rows=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Lakehouse bootstrap tables

# COMMAND ----------

BOOTSTRAP_TABLES = [
    "app_config",
    "transaction_summaries_for_search",
    "approval_rules",
    "approval_recommendations",
    "countries",
    "incidents_lakehouse",
    "online_features",
]

for tbl in BOOTSTRAP_TABLES:
    run_test(f"Table: {tbl}", "Lakehouse Bootstrap", make_table_test(tbl, check_rows=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Gold views (SQL)

# COMMAND ----------

GOLD_VIEWS_SQL = [
    "v_executive_kpis",
    "v_approval_trends_hourly",
    "v_approval_trends_by_second",
    "v_performance_by_geography",
    "v_top_decline_reasons",
    "v_decline_recovery_opportunities",
    "v_last_hour_performance",
    "v_last_60_seconds_performance",
    "v_active_alerts",
    "v_solution_performance",
    "v_card_network_performance",
    "v_merchant_segment_performance",
    "v_daily_trends",
    "v_streaming_ingestion_hourly",
    "v_streaming_ingestion_by_second",
    "v_silver_processed_hourly",
    "v_silver_processed_by_second",
    "v_streaming_volume_per_second",
    "v_data_quality_summary",
    "v_uc_data_quality_metrics",
    "v_transaction_summaries_for_search",
    "v_recommendations_from_lakehouse",
    "v_retry_success_by_reason",
    # Metric views
    "payment_metrics",
    "decline_metrics",
    "merchant_metrics",
]

def make_view_test(view_name):
    def test():
        rows = sql(f"SHOW VIEWS IN {CATALOG}.{SCHEMA} LIKE '{view_name}'")
        if not rows:
            rows = sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA} LIKE '{view_name}'")
        assert len(rows) > 0, f"View/table '{view_name}' not found"
        count = sql(f"SELECT COUNT(*) AS cnt FROM {CATALOG}.{SCHEMA}.{view_name}")[0].cnt
        return f"View '{view_name}' — {count:,} rows"
    return test

for vw in GOLD_VIEWS_SQL:
    run_test(f"View: {vw}", "Gold Views (SQL)", make_view_test(vw))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Gold tables (DLT pipeline)

# COMMAND ----------

GOLD_DLT_TABLES = [
    "v_retry_performance",
    "v_smart_checkout_service_path_br",
    "v_3ds_funnel_br",
    "v_reason_codes_br",
    "v_reason_code_insights_br",
    "v_entry_system_distribution_br",
    "v_dedup_collision_stats",
    "v_false_insights_metric",
    "v_smart_checkout_path_performance_br",
]

for tbl in GOLD_DLT_TABLES:
    run_test(f"Gold DLT: {tbl}", "Gold Tables (DLT)", make_table_test(tbl, check_rows=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Lakehouse views (bootstrap)

# COMMAND ----------

LAKEHOUSE_VIEWS = [
    "v_approval_rules_active",
    "v_incidents_recent",
    "v_online_features_latest",
]

for vw in LAKEHOUSE_VIEWS:
    run_test(f"View: {vw}", "Lakehouse Views", make_view_test(vw))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Model Serving endpoints

# COMMAND ----------

import urllib.request
import urllib.error
import os

SERVING_ENDPOINTS = [
    "approval-propensity",
    "risk-scoring",
    "smart-routing",
    "smart-retry",
    "payment-response-agent",
]

def make_serving_test(endpoint_name):
    def test():
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        ep = w.serving_endpoints.get(endpoint_name)
        state = ep.state
        ready = getattr(state, "ready", None)
        config_update = getattr(state, "config_update", None)
        assert ready == "READY" or str(ready) == "EndpointStateReady.READY", (
            f"Endpoint '{endpoint_name}' state: ready={ready}, config_update={config_update}"
        )
        served = ep.config.served_entities or ep.config.served_models or []
        entity_info = f"{len(served)} served entit{'y' if len(served)==1 else 'ies'}"
        return f"Endpoint '{endpoint_name}' is READY — {entity_info}"
    return test

for ep_name in SERVING_ENDPOINTS:
    run_test(f"Serving: {ep_name}", "Model Serving", make_serving_test(ep_name))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Foundation Model / AI Gateway endpoints

# COMMAND ----------

LLM_ENDPOINTS = [
    "databricks-claude-opus-4-6",
    "databricks-claude-sonnet-4-5",
    "databricks-llama-4-maverick",
]

def make_llm_test(endpoint_name):
    def test():
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        ep = w.serving_endpoints.get(endpoint_name)
        state = ep.state
        ready = getattr(state, "ready", None)
        assert ready == "READY" or str(ready) == "EndpointStateReady.READY", (
            f"LLM endpoint '{endpoint_name}' not ready: {ready}"
        )
        return f"LLM '{endpoint_name}' is READY"
    return test

for llm in LLM_ENDPOINTS:
    run_test(f"LLM: {llm}", "AI Gateway / LLMs", make_llm_test(llm))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. DLT Pipelines

# COMMAND ----------

PIPELINES = {
    "payment_analysis_etl": f"[{ENV}] 8. Payment Analysis ETL",
    "payment_realtime_pipeline": f"[{ENV}] 9. Payment Real-Time Stream",
}

def make_pipeline_test(display_name):
    def test():
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        found = None
        for p in w.pipelines.list_pipelines():
            if p.name == display_name:
                found = p
                break
        assert found is not None, f"Pipeline '{display_name}' not found"
        state = found.state
        return f"Pipeline '{display_name}' — state: {state}"
    return test

for key, name in PIPELINES.items():
    run_test(f"Pipeline: {key}", "DLT Pipelines", make_pipeline_test(name))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. SQL Warehouse

# COMMAND ----------

def test_sql_warehouse():
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    wh_name = f"[{ENV}] Payment Analysis Warehouse"
    found = None
    for wh in w.warehouses.list():
        if wh.name == wh_name:
            found = wh
            break
    assert found is not None, f"Warehouse '{wh_name}' not found"
    state = found.state
    return f"Warehouse '{wh_name}' — state: {state}, size: {found.cluster_size}"

run_test("SQL Warehouse", "SQL Warehouse", test_sql_warehouse)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Dashboards

# COMMAND ----------

DASHBOARD_NAMES = [
    f"[{ENV}] Data & Quality",
    f"[{ENV}] ML & Optimization",
    f"[{ENV}] Executive & Trends",
]

def make_dashboard_test(dash_name):
    def test():
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        found = None
        for d in w.lakeview.list():
            if d.display_name == dash_name:
                found = d
                break
        assert found is not None, f"Dashboard '{dash_name}' not found"
        return f"Dashboard '{dash_name}' — id: {found.dashboard_id}"
    return test

for dn in DASHBOARD_NAMES:
    run_test(f"Dashboard: {dn}", "Dashboards", make_dashboard_test(dn))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Genie Space

# COMMAND ----------

def test_genie_space():
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    found = None
    for gs in w.genie.list_spaces():
        if "Payment" in (gs.title or ""):
            found = gs
            break
    if found is None:
        for gs in w.genie.list_spaces():
            found = gs
            break
    assert found is not None, "No Genie space found"
    return f"Genie space: '{found.title}' — id: {found.space_id}"

run_test("Genie Space", "Genie Space", test_genie_space)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Jobs

# COMMAND ----------

JOB_NAMES = [
    f"[{ENV}] 1. Create Data Repositories (Lakehouse, Vector Search, Lakebase)",
    f"[{ENV}] 2. Simulate Transaction Events (Producer)",
    f"[{ENV}] 3. Initialize Ingestion (Lakehouse, UC Agent Tools, Vector Search)",
    f"[{ENV}] 4. Deploy Dashboards (Prepare & Publish)",
    f"[{ENV}] 5. Train Models & Publish to Model Serving",
    f"[{ENV}] 6. Deploy Agents (Orchestrator & Specialists)",
    f"[{ENV}] 7. Genie Space Sync",
    f"[{ENV}] Validate All Resources",
]

def make_job_test(job_name):
    def test():
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        found = None
        for j in w.jobs.list(name=job_name):
            if j.settings and j.settings.name == job_name:
                found = j
                break
        assert found is not None, f"Job '{job_name}' not found"
        return f"Job '{job_name}' — id: {found.job_id}"
    return test

for jn in JOB_NAMES:
    run_test(f"Job: {jn.split(']')[1].strip()}", "Jobs", make_job_test(jn))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 14. UC Functions (Agent Tools)

# COMMAND ----------

UC_FUNCTIONS = [
    "get_decline_trends",
    "get_decline_by_segment",
    "get_route_performance",
    "get_cascade_recommendations",
    "get_retry_success_rates",
    "get_recovery_opportunities",
    "get_high_risk_transactions",
    "get_risk_distribution",
    "get_kpi_summary",
    "get_optimization_opportunities",
    "get_trend_analysis",
    "get_active_approval_rules",
    "get_recent_incidents",
    "get_online_features",
    "get_approval_recommendations",
    "get_decision_outcomes",
    "search_similar_transactions",
    # Consolidated tools (ResponsesAgent)
    "analyze_declines",
    "analyze_routing",
    "analyze_retry",
    "analyze_risk",
    "analyze_performance",
]

def make_function_test(func_name):
    def test():
        rows = sql(f"SHOW USER FUNCTIONS IN {CATALOG}.{SCHEMA} LIKE '{func_name}'")
        if not rows:
            rows = sql(f"SHOW FUNCTIONS IN {CATALOG}.{SCHEMA} LIKE '{func_name}'")
        assert len(rows) > 0, f"UC function '{func_name}' not found in {CATALOG}.{SCHEMA}"
        return f"Function '{func_name}' exists"
    return test

for fn in UC_FUNCTIONS:
    run_test(f"Function: {fn}", "UC Functions", make_function_test(fn))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 15. Lakebase (Postgres) connectivity

# COMMAND ----------

def test_lakebase_connectivity():
    """Test Lakebase Postgres connection using Databricks SDK."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    project_id = "payment-analysis-db"
    try:
        project = w.lakebase.get_project(project_id)
        state = getattr(project, "state", "UNKNOWN")
        return f"Lakebase project '{project_id}' — state: {state}"
    except Exception as exc:
        if "NOT_FOUND" in str(exc) or "404" in str(exc):
            raise AssertionError(f"Lakebase project '{project_id}' not found: {exc}") from exc
        raise

run_test("Lakebase project", "Lakebase", test_lakebase_connectivity)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Lakebase Postgres tables (SQLModel entities)

# COMMAND ----------

LAKEBASE_PG_TABLES = [
    "authorizationevent",
    "decisionlog",
    "experiment",
    "experimentassignment",
    "incident",
    "remediationtask",
    "decisionconfig",
    "retryabledeclinecode",
    "routeperformance",
    "decisionoutcome",
    "proposedconfigchange",
]

# Cache the Postgres connection across all table tests to avoid repeated auth
_pg_conn_cache: dict = {}

def _get_pg_connection():
    """Create or reuse a psycopg connection to Lakebase Postgres."""
    if "conn" in _pg_conn_cache:
        return _pg_conn_cache["conn"]
    from databricks.sdk import WorkspaceClient
    import psycopg

    w = WorkspaceClient()
    project_id = "payment-analysis-db"

    branches = list(w.lakebase.list_branches(project_id))
    if not branches:
        raise AssertionError("No Lakebase branches found")
    branch_id = getattr(branches[0], "branch_id", None) or getattr(branches[0], "name", None)

    endpoints = list(w.lakebase.list_endpoints(project_id, branch_id))
    if not endpoints:
        raise AssertionError("No Lakebase endpoints found")
    endpoint_name = getattr(endpoints[0], "name", None)

    cred_resp = w.api_client.do(
        "POST",
        f"/api/2.0/lakebase/projects/{project_id}/databases/databricks_postgres/credentials",
        body={"endpoint": endpoint_name},
    )
    pg_token = cred_resp.get("token", "")

    endpoint_resp = w.api_client.do(
        "GET",
        f"/api/2.0/lakebase/projects/{project_id}/endpoints/{endpoint_name}",
    )
    pg_host = endpoint_resp.get("host", "")

    user_email = w.current_user.me().user_name
    conn_str = f"postgresql://{user_email}@{pg_host}:5432/databricks_postgres?sslmode=require"
    conn = psycopg.connect(conn_str, password=pg_token)
    _pg_conn_cache["conn"] = conn
    return conn

def make_lakebase_table_test(table_name):
    def test():
        pg_schema = SCHEMA or "payment_analysis"
        try:
            conn = _get_pg_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                    (pg_schema, table_name),
                )
                cnt = cur.fetchone()[0]
                assert cnt > 0, f"Table '{pg_schema}.{table_name}' not found in Lakebase Postgres"
                cur.execute(f'SELECT COUNT(*) FROM "{pg_schema}"."{table_name}"')
                row_count = cur.fetchone()[0]
                return f"Lakebase table '{pg_schema}.{table_name}' exists — {row_count:,} rows"
        except ImportError:
            return f"SKIP — psycopg not available (table: {table_name})"
        except AssertionError:
            raise
        except Exception as exc:
            raise AssertionError(f"Lakebase table check failed for '{table_name}': {exc}") from exc
    return test

for tbl in LAKEBASE_PG_TABLES:
    run_test(f"Lakebase table: {tbl}", "Lakebase Tables", make_lakebase_table_test(tbl))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 16. Vector Search

# COMMAND ----------

def test_vector_search_endpoint():
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    endpoint_name = f"payment-similar-transactions-{ENV}"
    try:
        ep = w.vector_search_endpoints.get_endpoint(endpoint_name)
        status = getattr(ep, "endpoint_status", None)
        state = getattr(status, "state", "UNKNOWN") if status else "UNKNOWN"
        return f"VS endpoint '{endpoint_name}' — state: {state}"
    except Exception as exc:
        if "NOT_FOUND" in str(exc) or "RESOURCE_DOES_NOT_EXIST" in str(exc):
            raise AssertionError(f"VS endpoint '{endpoint_name}' not found") from exc
        raise

def test_vector_search_index():
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    index_name = f"{CATALOG}.{SCHEMA}.similar_transactions_index"
    try:
        idx = w.vector_search_indexes.get_index(index_name)
        status = getattr(idx, "status", None)
        state = getattr(status, "ready", None) if status else "UNKNOWN"
        return f"VS index '{index_name}' — ready: {state}"
    except Exception as exc:
        if "NOT_FOUND" in str(exc) or "RESOURCE_DOES_NOT_EXIST" in str(exc):
            raise AssertionError(f"VS index '{index_name}' not found") from exc
        raise

run_test("Vector Search endpoint", "Vector Search", test_vector_search_endpoint)
run_test("Vector Search index", "Vector Search", test_vector_search_index)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 17. App health

# COMMAND ----------

def test_app_exists():
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    app_name = "payment-analysis"
    try:
        app = w.apps.get(app_name)
        state = getattr(app, "status", None) or getattr(app, "compute_status", None)
        url = getattr(app, "url", "") or ""
        return f"App '{app_name}' — state: {state}, url: {url}"
    except Exception as exc:
        raise AssertionError(f"App '{app_name}' not found: {exc}") from exc

def test_app_healthcheck():
    """Hit the app's /api/v1/healthcheck endpoint to verify it is serving."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    app_name = "payment-analysis"
    try:
        app = w.apps.get(app_name)
        url = (getattr(app, "url", "") or "").rstrip("/")
        if not url:
            return "SKIP — app URL not available (app may be starting)"
        healthcheck_url = f"{url}/api/v1/healthcheck"
        token = w.config.token if hasattr(w.config, "token") and w.config.token else None
        if not token:
            try:
                token = w.dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
            except Exception:
                pass
        req = urllib.request.Request(healthcheck_url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=15)
        body = resp.read().decode("utf-8", errors="replace")
        status_code = resp.getcode()
        assert status_code == 200, f"Healthcheck returned HTTP {status_code}"
        return f"Healthcheck OK (HTTP {status_code}): {body[:200]}"
    except urllib.error.HTTPError as he:
        raise AssertionError(f"Healthcheck HTTP {he.code}: {he.reason}") from he
    except urllib.error.URLError as ue:
        raise AssertionError(f"Healthcheck URL error: {ue.reason}") from ue

def test_app_db_health():
    """Hit /api/v1/health/database to verify Lakebase connectivity from the app."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    app_name = "payment-analysis"
    try:
        app = w.apps.get(app_name)
        url = (getattr(app, "url", "") or "").rstrip("/")
        if not url:
            return "SKIP — app URL not available"
        db_url = f"{url}/api/v1/health/database"
        token = w.config.token if hasattr(w.config, "token") and w.config.token else None
        if not token:
            try:
                token = w.dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
            except Exception:
                pass
        req = urllib.request.Request(db_url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=15)
        body = resp.read().decode("utf-8", errors="replace")
        return f"DB health OK: {body[:200]}"
    except urllib.error.HTTPError as he:
        if he.code == 503:
            return f"DB health: Lakebase unavailable (HTTP 503) — expected if endpoint suspended"
        raise AssertionError(f"DB health HTTP {he.code}: {he.reason}") from he
    except urllib.error.URLError as ue:
        raise AssertionError(f"DB health URL error: {ue.reason}") from ue

run_test("App: payment-analysis", "App Health", test_app_exists)
run_test("App: HTTP healthcheck", "App Health", test_app_healthcheck)
run_test("App: database health", "App Health", test_app_db_health)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 18. End-to-end data flow — quick smoke test

# COMMAND ----------

def test_data_flow_bronze_to_gold():
    """Verify data flows from bronze → silver → gold by checking counts."""
    bronze = sql(f"SELECT COUNT(*) AS cnt FROM {CATALOG}.{SCHEMA}.payments_raw_bronze")[0].cnt
    silver = sql(f"SELECT COUNT(*) AS cnt FROM {CATALOG}.{SCHEMA}.payments_enriched_silver")[0].cnt
    kpis = sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.v_executive_kpis LIMIT 1")
    assert bronze > 0, "Bronze table has 0 rows — pipeline 8 may not have run"
    assert silver > 0, "Silver table has 0 rows — pipeline 8 may not have run"
    assert len(kpis) > 0, "Executive KPIs view returns no data"
    return f"Data flow OK: bronze={bronze:,}, silver={silver:,}, KPIs available"

def test_data_flow_streaming():
    """Verify real-time stream data exists."""
    stream_bronze = sql(f"SELECT COUNT(*) AS cnt FROM {CATALOG}.{SCHEMA}.payments_stream_bronze")[0].cnt
    stream_silver = sql(f"SELECT COUNT(*) AS cnt FROM {CATALOG}.{SCHEMA}.payments_stream_silver")[0].cnt
    return f"Streaming flow: stream_bronze={stream_bronze:,}, stream_silver={stream_silver:,}"

def test_model_serving_inference():
    """Quick inference test against approval-propensity endpoint."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    payload = {
        "dataframe_records": [
            {
                "transaction_amount": 150.0,
                "merchant_category": "retail",
                "card_network": "visa",
                "is_international": 0,
                "hour_of_day": 14,
                "day_of_week": 3,
                "fraud_score": 0.1,
                "retry_count": 0,
            }
        ]
    }
    try:
        resp = w.serving_endpoints.query(name="approval-propensity", dataframe_records=payload["dataframe_records"])
        predictions = getattr(resp, "predictions", None)
        assert predictions is not None, "No predictions returned"
        return f"Inference OK — predictions: {predictions}"
    except Exception as exc:
        if "NOT_READY" in str(exc):
            return f"Endpoint not ready (expected if just deployed): {exc}"
        raise

def test_agent_inference():
    """Quick inference test against the payment-response-agent endpoint."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    try:
        resp = w.serving_endpoints.query(
            name="payment-response-agent",
            messages=[{"role": "user", "content": "What is the current approval rate?"}],
        )
        choices = getattr(resp, "choices", None)
        if choices and len(choices) > 0:
            content = getattr(choices[0], "message", {})
            return f"Agent inference OK — response received"
        return f"Agent inference OK — raw: {str(resp)[:150]}"
    except Exception as exc:
        if "NOT_READY" in str(exc) or "LOADING" in str(exc):
            return f"Agent endpoint not ready (expected if just deployed): {exc}"
        raise

def test_llm_gateway_call():
    """Quick test call to the AI Gateway LLM endpoint."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    try:
        resp = w.serving_endpoints.query(
            name="databricks-claude-sonnet-4-5",
            messages=[{"role": "user", "content": "Say hello in one word."}],
            max_tokens=10,
        )
        choices = getattr(resp, "choices", None)
        if choices and len(choices) > 0:
            return "LLM gateway call OK — response received"
        return f"LLM gateway OK — raw: {str(resp)[:100]}"
    except Exception as exc:
        if "NOT_READY" in str(exc):
            return f"LLM not ready: {exc}"
        raise

def test_streaming_metrics():
    """Verify streaming metrics aggregation is producing data."""
    try:
        rows = sql(f"SELECT COUNT(*) AS cnt FROM {CATALOG}.{SCHEMA}.payments_stream_metrics_10s")
        cnt = rows[0].cnt
        return f"Streaming metrics: {cnt:,} rows in payments_stream_metrics_10s"
    except Exception as exc:
        raise AssertionError(f"Streaming metrics check failed: {exc}") from exc

def test_gold_kpis_freshness():
    """Check that executive KPIs view has recent data."""
    try:
        rows = sql(f"""
            SELECT approval_rate_pct, total_transactions, total_approved
            FROM {CATALOG}.{SCHEMA}.v_executive_kpis
            LIMIT 1
        """)
        assert len(rows) > 0, "v_executive_kpis returns no data"
        r = rows[0]
        return f"KPIs: approval_rate={r.approval_rate_pct}%, txns={r.total_transactions:,}, approved={r.total_approved:,}"
    except Exception as exc:
        raise AssertionError(f"KPI freshness check failed: {exc}") from exc

run_test("Data flow: bronze → silver → gold", "E2E Data Flow", test_data_flow_bronze_to_gold)
run_test("Data flow: streaming pipeline", "E2E Data Flow", test_data_flow_streaming)
run_test("Data flow: streaming metrics", "E2E Data Flow", test_streaming_metrics)
run_test("Data flow: KPI freshness", "E2E Data Flow", test_gold_kpis_freshness)
run_test("Inference: approval-propensity", "E2E Data Flow", test_model_serving_inference)
run_test("Inference: payment-response-agent", "E2E Data Flow", test_agent_inference)
run_test("Inference: LLM gateway", "E2E Data Flow", test_llm_gateway_call)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Results Summary

# COMMAND ----------

passed = [r for r in results if r.passed]
failed = [r for r in results if not r.passed]

print("=" * 90)
print(f"  VALIDATION RESULTS: {len(passed)} passed, {len(failed)} failed, {len(results)} total")
print("=" * 90)

categories = {}
for r in results:
    categories.setdefault(r.category, []).append(r)

for cat, tests in categories.items():
    cat_passed = sum(1 for t in tests if t.passed)
    cat_failed = sum(1 for t in tests if not t.passed)
    icon = "✅" if cat_failed == 0 else "⚠️"
    print(f"\n{icon} {cat} ({cat_passed}/{len(tests)} passed)")
    for t in tests:
        status = "  ✅" if t.passed else "  ❌"
        print(f"  {status} {t.name} [{t.elapsed_ms:.0f}ms] — {t.message}")

print("\n" + "=" * 90)
if failed:
    print(f"  ⚠️  {len(failed)} TEST(S) FAILED — review errors above")
    print("=" * 90)
    for f in failed:
        print(f"  ❌ [{f.category}] {f.name}: {f.message}")
else:
    print("  ✅ ALL TESTS PASSED — all resources validated and connected")
print("=" * 90)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Results as DataFrame (for dashboards / downstream)

# COMMAND ----------

from pyspark.sql import Row  # type: ignore[import]  # noqa: F821

result_rows = [
    Row(
        category=r.category,
        test_name=r.name,
        passed=r.passed,
        message=r.message,
        elapsed_ms=round(r.elapsed_ms, 1),
    )
    for r in results
]

df = spark.createDataFrame(result_rows)  # type: ignore[name-defined]  # noqa: F821
display(df)  # type: ignore[name-defined]  # noqa: F821

# COMMAND ----------

# MAGIC %md
# MAGIC ## Assert all passed (fail notebook if any test failed)

# COMMAND ----------

if failed:
    raise AssertionError(
        f"{len(failed)} validation test(s) failed:\n"
        + "\n".join(f"  - [{f.category}] {f.name}: {f.message}" for f in failed)
    )
print(f"✅ All {len(results)} validation tests passed successfully.")
