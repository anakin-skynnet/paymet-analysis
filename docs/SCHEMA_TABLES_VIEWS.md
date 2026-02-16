# Schema: Tables and Views Reference

Catalog/schema: `ahs_demos_catalog.payment_analysis` (or `DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA`).

This document lists tables and views, whether they are **required** by the app (backend, dashboards, agents, Genie), **where they are used**, and **why they may be empty**. Use it for schema cleansing and troubleshooting.

---

## Summary

| Type | Required | Optional / Not read by app |
|------|----------|----------------------------|
| **Silver/Bronze (Lakeflow)** | payments_enriched_silver, merchants_dim_bronze, merchant_visible_attempts_silver, reason_code_taxonomy_silver, insight_feedback_silver, smart_checkout_decisions_silver | decision_log_silver, payments_stream_alerts |
| **Gold views (Job 3 SQL)** | All `v_*` and metric views listed below (including `v_retry_success_by_reason`) | — |
| **Gold tables (Lakeflow)** | v_retry_performance, v_3ds_funnel_br, v_reason_codes_br, v_reason_code_insights_br, v_entry_system_distribution_br, v_dedup_collision_stats, v_false_insights_metric, v_smart_checkout_*, v_false_insights_metric | — |
| **Bootstrap (Job 1)** | v_recommendations_from_lakehouse, v_approval_rules_active, v_online_features_latest (and base tables) | — |

---

## Silver and Bronze Tables (Lakeflow)

Created by **Lakeflow pipelines** (Payment Analysis ETL, Real-Time, etc.). Empty until the pipeline runs and source data exists.

| Object | Required | Where used | Why empty |
|--------|----------|------------|-----------|
| **payments_enriched_silver** | **Yes** | gold_views.sql, gold_views.py, run_gold_views.py, agent_framework.py, uc_agent_tools.sql, vector_search create_index.py, train_models.py, genie | ETL pipeline (8. Payment Analysis ETL) not run, or **payments_raw_bronze** and **merchants_dim_bronze** empty. |
| **merchants_dim_bronze** | **Yes** | silver_transform.py (payments_enriched_silver reads it) | Bronze ingest (Lakeflow) not run, or no merchant seed/input. |
| **merchant_visible_attempts_silver** | **Yes** | gold_views.py (v_decline_recovery_opportunities, v_smart_checkout_path_performance_br) | payments_enriched_silver empty. |
| **reason_code_taxonomy_silver** | **Yes** | gold_views.py (v_reason_codes_br, v_reason_code_insights_br) | Pipeline not run. Has **static seed** in silver_transform; not empty once pipeline runs. |
| **insight_feedback_silver** | **Yes** | databricks_service.py (INSERT), gold_views.py (v_false_insights_metric) | Pipeline not run, or no app feedback. Has **seed rows** in silver_transform. |
| **smart_checkout_decisions_silver** | **Yes** | gold_views.py (v_smart_checkout_path_performance_br, v_smart_checkout_service_path_br) | Pipeline not run or no decision events. |
| **decision_log_silver** | **No** (not read by any view or API) | Defined in silver_transform.py only | Audit/decision log for future use. Pipeline run populates from payments_enriched_silver. Safe to drop if you do not need decision audit. |
| **payments_stream_alerts** | **No** (not read by any view or API) | Defined in realtime_pipeline.py only | Real-time alert table; no reader in app. Depends on payments_stream_metrics_10s (10-second windows, Real-Time pipeline). Safe to drop if you do not use streaming alerts. |

---

## Gold Views (Job 3 — run_gold_views.py)

Created by **Job 3 (Initialize Ingestion)** from `gold_views.sql`. All depend on **payments_enriched_silver** (and for streaming views, **payments_raw_bronze**). Empty when silver is empty.

| View | Required | Where used | Why empty |
|------|----------|------------|-----------|
| **v_executive_kpis** | Yes | databricks_service.py, dashboards, Genie, agent_framework, uc_agent_tools | payments_enriched_silver empty or Job 3 not run. |
| **v_approval_trends_hourly** | Yes | databricks_service.py, Genie | Same dataset as v_approval_trends_by_second; name kept for backward compatibility. |
| **v_approval_trends_by_second** | Yes | Dashboards (executive_trends, data_quality), databricks_service | Same as above. |
| **v_performance_by_geography** | Yes | databricks_service.py, dashboards, Genie, agent_framework, uc_agent_tools | Silver empty or Job 3 not run. |
| **v_top_decline_reasons** | Yes | databricks_service.py, dashboards, Genie, agent_framework, uc_agent_tools | Silver empty or Job 3 not run. |
| **v_decline_recovery_opportunities** | Yes | Dashboards (ml_optimization) | Silver empty or Job 3 not run. |
| **v_last_hour_performance** | Yes | databricks_service.py, dashboards | Silver empty or Job 3 not run. |
| **v_last_60_seconds_performance** | Yes | databricks_service.py (last-60-seconds API), data-quality UI | Real-time live metrics; last 60 seconds. Silver empty or Job 3 not run. |
| **v_active_alerts** | Yes | databricks_service.py, dashboards | Silver empty or Job 3 not run. |
| **v_solution_performance** | Yes | databricks_service.py, dashboards, Genie, agent_framework, uc_agent_tools | Silver empty or Job 3 not run. |
| **v_card_network_performance** | Yes | databricks_service.py, dashboards | Silver empty or Job 3 not run. |
| **v_merchant_segment_performance** | Yes | Dashboards (ml_optimization, executive_trends) | Silver empty or Job 3 not run. |
| **v_daily_trends** | Yes | databricks_service.py, dashboards, Genie, agent_framework, uc_agent_tools | Silver empty or Job 3 not run. |
| **v_streaming_ingestion_hourly** | Yes | scripts/dashboards.py (asset check) | Depends on payments_raw_bronze; stub created by Job 3 if missing. Empty until streaming pipeline runs. |
| **v_streaming_ingestion_by_second** | Yes | Dashboards (data_quality) | Same. |
| **v_streaming_volume_per_second** | Yes | databricks_service.py, dashboards | Same. |
| **v_silver_processed_hourly** | Yes | scripts/dashboards.py (asset check) | Same. |
| **v_silver_processed_by_second** | Yes | Dashboards (data_quality) | Same. |
| **v_data_quality_summary** | Yes | databricks_service.py, dashboards | Silver/bronze empty or Job 3 not run. |
| **v_uc_data_quality_metrics** | Yes | scripts/dashboards.py (asset check) | Same. |
| **payment_metrics** | Yes (semantic layer) | gold_views.sql WITH METRICS; dashboards.py asset validation | UC metrics view; empty when silver empty. |
| **decline_metrics** | Yes (semantic layer) | gold_views.sql WITH METRICS; dashboards.py asset validation | Same. |
| **merchant_metrics** | Yes (semantic layer) | gold_views.sql WITH METRICS; dashboards.py asset validation | Same. |
| **v_retry_success_by_reason** | Yes | Smart Retry analytics, retry analysis by decline reason and scenario | payments_enriched_silver empty, no retries, or Job 3 not run. Requires retry_count > 0 and decline_reason_standard IS NOT NULL. Shows success_rate_pct, recovered_value, avg_retry_delay per decline reason and retry scenario. |

---

## Gold Tables (Lakeflow — gold_views.py)

Created by **Lakeflow pipeline** (Payment Analysis ETL). Consumed by backend `databricks_service.py`. Empty when upstream silver is empty.

| Table | Required | Where used | Why empty |
|-------|----------|------------|-----------|
| **v_retry_performance** | Yes | databricks_service.py (retry-performance API) | payments_enriched_silver empty or pipeline not run. |
| **v_smart_checkout_service_path_br** | Yes | databricks_service.py | smart_checkout_decisions_silver + payments_enriched_silver empty. |
| **v_smart_checkout_path_performance_br** | Yes | databricks_service.py | Same. |
| **v_3ds_funnel_br** | Yes | databricks_service.py | payments_enriched_silver empty or pipeline not run. |
| **v_reason_codes_br** | Yes | databricks_service.py | reason_code_taxonomy_silver + payments_enriched_silver. |
| **v_reason_code_insights_br** | Yes | databricks_service.py | Same. |
| **v_entry_system_distribution_br** | Yes | databricks_service.py | payments_enriched_silver empty. |
| **v_dedup_collision_stats** | Yes | databricks_service.py | payments_enriched_silver empty. |
| **v_false_insights_metric** | Yes | databricks_service.py | insight_feedback_silver empty (has seed; pipeline must run). |

---

## Bootstrap Tables and Views (Job 1 — lakehouse_bootstrap.sql)

Created by **Job 1 (Create Data Repositories)**, task `lakehouse_bootstrap`. Base tables are seeded when empty.

| Object | Required | Where used | Why empty |
|--------|----------|------------|-----------|
| **approval_recommendations** | Yes | v_recommendations_from_lakehouse | Table created by Job 1; empty until app or jobs write recommendations. |
| **v_recommendations_from_lakehouse** | Yes | databricks_service.py | approval_recommendations empty. |
| **approval_rules** | Yes | v_approval_rules_active, agent_framework | Job 1 seeds default rules when empty. |
| **v_approval_rules_active** | Yes | agent_framework.py | approval_rules empty or no active rules. |
| **countries** | Yes | Backend /api/countries, UI filter | Job 1 seeds default countries when empty. |
| **online_features** | Yes | v_online_features_latest | Empty until ML/agent jobs write features. |
| **incidents_lakehouse** | Yes | uc_agent_tools.sql (get_recent_incidents), backend incidents.py | Empty until incidents are created via the app or agents. |
| **v_online_features_latest** | Optional | lakehouse_bootstrap.sql only; no backend query found | online_features empty until ML/agent write. |

---

## Duplicates and consolidation

- **v_approval_trends_hourly** and **v_approval_trends_by_second**: Same per-second dataset (last 1 hour). Both are used (backend uses hourly; dashboards use by_second). Kept for backward compatibility; no consolidation needed.
- No other duplicate views found; each view/table has a distinct purpose.

---

## Schema cleansing recommendations

1. **Required and in use**  
   Keep all tables and views marked **Required** above. If they are empty, fix data flow: run Job 1 → run ETL pipeline (and optionally Real-Time pipeline) → run Job 3. See [DEPLOYMENT.md](DEPLOYMENT.md#why-tables-and-views-may-be-empty).

2. **Not read by the app**  
   - **decision_log_silver**: Written by pipeline; no view or API reads it. Optional for audit. To remove: drop from Lakeflow pipeline (silver_transform.py) and drop table in catalog if desired.  
   - **payments_stream_alerts**: Written by Real-Time pipeline; no view or API reads it. Optional for monitoring. To remove: drop from realtime_pipeline.py and drop table if desired.

3. **Do not drop**  
   All other listed objects are referenced by the backend, dashboards, Genie, or agents. Removing them will break APIs or dashboards.

4. **Order of operations for “no empty tables”**  
   - Run Job 1 (lakehouse_bootstrap, etc.).  
   - Run Lakeflow **Payment Analysis ETL** pipeline so payments_enriched_silver (and other silver tables) exist.  
   - Run Job 3 (run_gold_views) so SQL gold views exist.  
   - Optionally run Real-Time pipeline and Job 2 (transaction simulator) to populate streaming views.

---

## How data is inserted

**Views** do not have an insertion process. They are `SELECT` over base tables; data appears when those tables are populated.

**Tables** get data as follows:

| Source | Mechanism | Tables / views affected |
|--------|-----------|--------------------------|
| **Lakeflow pipeline (ETL)** | Pipeline reads upstream DLT tables (or streams) and writes to the next table. | **Bronze:** payments_raw_bronze (readStream from payments_stream_input), merchants_dim_bronze (synthetic `spark.range(50)` in bronze_ingest.py). **Silver:** payments_enriched_silver, merchant_visible_attempts_silver, reason_code_taxonomy_silver (static seed), insight_feedback_silver (seed + app INSERT), decision_log_silver, smart_checkout_decisions_silver. **Gold (Lakeflow):** v_retry_performance, v_3ds_funnel_br, v_reason_codes_br, v_reason_code_insights_br, v_entry_system_distribution_br, v_dedup_collision_stats, v_false_insights_metric, v_smart_checkout_*. |
| **Lakeflow pipeline (Real-Time)** | readStream from payments_stream_input → payments_stream_bronze → payments_stream_silver → 10s windowed metrics → payments_stream_alerts. | payments_stream_bronze, payments_stream_silver, payments_stream_metrics_10s, payments_stream_alerts. |
| **Job 1 – lakehouse_bootstrap.sql** | `INSERT INTO ... WHERE (SELECT COUNT(*) FROM ...) = 0` (seed when empty). | app_config, approval_rules, countries. |
| **Job 2 – transaction_simulator** | `df.write.mode("append").saveAsTable(target_table)` into `payments_stream_input`. | payments_stream_input (and CDF feeds bronze pipelines). |
| **Job 1 – vector_search create_index** | MERGE from payments_enriched_silver into transaction_summaries_for_search (populated with 50k+ rows). Delta-sync index `similar_transactions_index` created and synced for embedding. | transaction_summaries_for_search → similar_transactions_index (Vector Search). |
| **Job 3 – run_gold_views.py** | Executes `gold_views.sql`; only creates VIEWs (no table insertion). | All gold views in gold_views.sql (data comes from underlying tables). |
| **Backend (FastAPI)** | `DatabricksService` runs INSERT/MERGE via SQL Warehouse. | app_config (MERGE from Setup Save), approval_rules (create/update/delete rule — **dual-write:** Lakebase and Lakehouse are synced via BackgroundTasks so both the UI and agents see the same rules), **insight_feedback_silver** (INSERT when user submits feedback). |

---

## Tables / views with no insertion process

These **tables** exist in the schema but have **no code path in this repo** that inserts into them. They stay empty unless you add a job, agent, or external process to write them.

| Object | Created by | Insertion process in repo? | Notes |
|--------|------------|----------------------------|--------|
| **approval_recommendations** | lakehouse_bootstrap.sql | **No direct insertion** | Table created and empty by default. AI agents or a scheduled job can write recommendations here. The dual-write sync for approval rules (via BackgroundTasks in `rules.py`) does not write to this table; it syncs `approval_rules` between Lakebase and Lakehouse. Decisioning UI shows "No recommendations yet" until something writes here. |
| **online_features** (Lakehouse) | lakehouse_bootstrap.sql | **Yes** (DecisionEngine) | Table created by bootstrap. The `DecisionEngine` (used by `/api/decision/*` routes) auto-populates online features in Lakebase during ML enrichment; those features are also readable from the Lakehouse table. (Lakebase `online_features` is the primary write target.) |
| **payments_stream_input** | transaction_simulator (CREATE TABLE IF NOT EXISTS) | **Yes** | Populated by **transaction_simulator** when run as a job; no data if that job never runs. |

**Views** are not inserted into; they reflect underlying tables. The following **views** will therefore be empty if their base table has no insertion (or no rows):

- **v_recommendations_from_lakehouse** — empty while `approval_recommendations` has no rows.
- **v_online_features_latest** — empty while Lakehouse `online_features` has no rows.
