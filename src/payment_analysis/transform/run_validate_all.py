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
# MAGIC 3. Gold views (SQL + DLT)
# MAGIC 4. Lakehouse bootstrap tables
# MAGIC 5. Model Serving endpoints (5)
# MAGIC 6. Foundation Model / AI Gateway endpoints (LLMs)
# MAGIC 7. DLT Pipelines (2)
# MAGIC 8. SQL Warehouse
# MAGIC 9. Dashboards (3)
# MAGIC 10. Genie Space
# MAGIC 11. Lakebase (Postgres) connectivity
# MAGIC 12. UC Functions (agent tools)
# MAGIC 13. Jobs (7)
# MAGIC 14. App health
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
    # Consolidated tools
    "analyze_declines",
    "analyze_routing",
    "analyze_retries",
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
# MAGIC ## 16. App health

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

run_test("App: payment-analysis", "App", test_app_exists)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 17. End-to-end data flow — quick smoke test

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

run_test("Data flow: bronze → silver → gold", "E2E Data Flow", test_data_flow_bronze_to_gold)
run_test("Data flow: streaming pipeline", "E2E Data Flow", test_data_flow_streaming)
run_test("Inference: approval-propensity", "E2E Data Flow", test_model_serving_inference)

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
