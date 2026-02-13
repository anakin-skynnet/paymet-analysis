# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer — Backend API Tables
# MAGIC
# MAGIC Lakeflow-managed materialized gold tables consumed exclusively by the **backend
# MAGIC FastAPI service** (SQL queries in `databricks_service.py`).
# MAGIC
# MAGIC **Ownership:** Lakeflow ETL pipeline (Pipeline 8).
# MAGIC
# MAGIC Dashboard, Genie, and Agent gold views live in `gold_views.sql` and are created
# MAGIC by **Job 3** (`run_gold_views.py`) as lightweight SQL VIEWs.  The two sets use
# MAGIC **distinct names** so there is never a conflict between Lakeflow tables and
# MAGIC Job 3 views.

# COMMAND ----------

import dlt  # type: ignore[import-untyped]
from pyspark.sql.functions import (  # type: ignore[import-untyped]
    avg,
    col,
    count,
    countDistinct,
    lit,
    round,
    sum,
    when,
)

# Configurable thresholds (set via pipeline config; aligned with Lakebase decisionconfig)
RETRY_EFFECTIVENESS_HIGH = float(spark.conf.get("spark.payment.retry_effectiveness_high", "40"))
RETRY_EFFECTIVENESS_MODERATE = float(spark.conf.get("spark.payment.retry_effectiveness_moderate", "20"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Retry Cohort Analysis (backend: `/api/analytics/retry-performance`)

# COMMAND ----------

@dlt.table(
    name="v_retry_performance",
    comment="Smart retry strategy performance by scenario, reason, and retry count",
    table_properties={
        "quality": "gold"
    }
)
def v_retry_performance():
    """Retry success metrics by decline reason with incremental lift vs baseline."""
    
    payments = dlt.read("payments_enriched_silver")
    
    # Baseline: overall approval rate for non-retry transactions (single-row DF, safe cross join)
    baseline = (
        payments
        .filter(~col("is_retry"))
        .agg(
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("baseline_approval_pct")
        )
    )

    # Retry cohorts with features
    retry_cohorts = (
        payments
        .filter(col("is_retry"))
        .groupBy("retry_scenario", "decline_reason_standard", "retry_count")
        .agg(
            count("*").alias("retry_attempts"),
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("success_rate_pct"),
            round(sum(when(col("is_approved"), col("amount")).otherwise(0)), 2).alias("recovered_value"),
            round(avg("fraud_score"), 3).alias("avg_fraud_score"),
            round(avg("time_since_last_attempt_seconds"), 0).alias("avg_time_since_last_attempt_s"),
            round(avg("prior_approved_count"), 1).alias("avg_prior_approvals"),
        )
    )

    # Join baseline (single row) instead of .collect() to avoid OOM
    return (
        retry_cohorts
        .crossJoin(baseline)
        .withColumn("incremental_lift_pct",
            round(col("success_rate_pct") - col("baseline_approval_pct"), 2)
        )
        .withColumn("effectiveness",
            when(col("success_rate_pct") > RETRY_EFFECTIVENESS_HIGH, "Effective")
            .when(col("success_rate_pct") > RETRY_EFFECTIVENESS_MODERATE, "Moderate")
            .otherwise("Low")
        )
        .orderBy("retry_scenario", "decline_reason_standard", "retry_count")
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Smart Checkout — Brazil / Payment Link: service-path breakdown
# MAGIC (backend: `/api/analytics/smart-checkout-service-path-br`)

# COMMAND ----------

@dlt.table(
    name="v_smart_checkout_service_path_br",
    comment="Brazil payment-link performance by Smart Checkout service path",
    table_properties={"quality": "gold"},
)
def v_smart_checkout_service_path_br():
    payments = dlt.read("payments_enriched_silver")

    br_links = payments.filter(
        (col("geo_country") == lit("BR"))
        & (col("flow_type").isin(["payment_link", "payment_link_sep"]))
    )

    return (
        br_links
        .groupBy("service_path")
        .agg(
            count("*").alias("transaction_count"),
            sum(when(col("is_approved"), 1).otherwise(0)).alias("approved_count"),
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("approval_rate_pct"),
            round(avg("fraud_score"), 3).alias("avg_fraud_score"),
            round(sum("amount"), 2).alias("total_value"),
            # Antifraud attribution
            sum(when((~col("is_approved")) & (col("antifraud_result") == lit("fail")), 1).otherwise(0)).alias("antifraud_declines"),
            round(
                sum(when((~col("is_approved")) & (col("antifraud_result") == lit("fail")), 1).otherwise(0))
                * 100.0
                / sum(when(~col("is_approved"), 1).otherwise(0)),
                2,
            ).alias("antifraud_pct_of_declines"),
        )
        .orderBy(col("transaction_count").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Smart Checkout — Brazil / Payment Link: 3DS funnel
# MAGIC (backend: `/api/analytics/3ds-funnel-br`)

# COMMAND ----------

@dlt.table(
    name="v_3ds_funnel_br",
    comment="Brazil payment-link 3DS funnel (routed → friction → authenticated → approved)",
    table_properties={"quality": "gold"},
)
def v_3ds_funnel_br():
    payments = dlt.read("payments_enriched_silver")

    br_links = payments.filter(
        (col("geo_country") == lit("BR"))
        & (col("flow_type").isin(["payment_link", "payment_link_sep"]))
    )

    return (
        br_links
        .groupBy("event_date")
        .agg(
            count("*").alias("total_transactions"),
            sum(when(col("three_ds_routed"), 1).otherwise(0)).alias("three_ds_routed_count"),
            sum(when(col("three_ds_friction"), 1).otherwise(0)).alias("three_ds_friction_count"),
            sum(when(col("three_ds_authenticated"), 1).otherwise(0)).alias("three_ds_authenticated_count"),
            sum(when(col("three_ds_authenticated") & col("is_approved"), 1).otherwise(0)).alias("issuer_approved_after_auth_count"),
        )
        .withColumn(
            "three_ds_friction_rate_pct",
            round(col("three_ds_friction_count") * 100.0 / when(col("three_ds_routed_count") == 0, lit(None)).otherwise(col("three_ds_routed_count")), 2),
        )
        .withColumn(
            "three_ds_authentication_rate_pct",
            round(col("three_ds_authenticated_count") * 100.0 / when(col("three_ds_routed_count") == 0, lit(None)).otherwise(col("three_ds_routed_count")), 2),
        )
        .withColumn(
            "issuer_approval_post_auth_rate_pct",
            round(col("issuer_approved_after_auth_count") * 100.0 / when(col("three_ds_authenticated_count") == 0, lit(None)).otherwise(col("three_ds_authenticated_count")), 2),
        )
        .orderBy(col("event_date").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Reason Codes — Brazil: unified taxonomy
# MAGIC (backend: `/api/analytics/reason-codes-br`)

# COMMAND ----------

@dlt.table(
    name="v_reason_codes_br",
    comment="Brazil declines consolidated into unified reason-code taxonomy (entry-system aware)",
    table_properties={"quality": "gold"},
)
def v_reason_codes_br():
    attempts = dlt.read("merchant_visible_attempts_silver")

    br = attempts.filter(col("geo_country") == lit("BR"))
    declined = br.filter(~col("is_approved"))

    total_declines = declined.agg(count("*").alias("total_declines"))

    by_reason = (
        declined
        .groupBy("entry_system", "flow_type", "decline_reason_standard", "decline_reason_group", "recommended_action")
        .agg(
            count("*").alias("decline_count"),
            round(sum("amount"), 2).alias("total_declined_value"),
            round(avg("amount"), 2).alias("avg_amount"),
            countDistinct("merchant_id").alias("affected_merchants"),
        )
    )

    # Add percent of declines via cross join (small table)
    return (
        by_reason
        .crossJoin(total_declines)
        .withColumn("pct_of_declines", round(col("decline_count") * 100.0 / col("total_declines"), 2))
        .drop("total_declines")
        .orderBy(col("decline_count").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Reason Code Insights — Brazil: estimated recovery (demo heuristic)
# MAGIC (backend: `/api/analytics/reason-code-insights-br`)

# COMMAND ----------

@dlt.table(
    name="v_reason_code_insights_br",
    comment="Brazil reason-code insights with estimated recoverability and prioritization (demo heuristic)",
    table_properties={"quality": "gold"},
)
def v_reason_code_insights_br():
    rc = dlt.read("v_reason_codes_br")

    # Heuristic recoverability factors (configurable via pipeline config; replace with ML-learned estimates)
    # Recovery rates by decline reason: how likely a declined transaction can be recovered via retry/re-route
    recovery_funds = float(spark.conf.get("spark.payment.recovery_rate_funds", "0.25"))
    recovery_issuer_tech = float(spark.conf.get("spark.payment.recovery_rate_issuer_tech", "0.40"))
    recovery_do_not_honor = float(spark.conf.get("spark.payment.recovery_rate_do_not_honor", "0.20"))
    recovery_card_expired = float(spark.conf.get("spark.payment.recovery_rate_card_expired", "0.05"))
    recovery_fraud = float(spark.conf.get("spark.payment.recovery_rate_fraud", "0.10"))
    recovery_default = float(spark.conf.get("spark.payment.recovery_rate_default", "0.05"))
    priority_high_threshold = float(spark.conf.get("spark.payment.priority_high_value_threshold", "100000"))
    priority_medium_threshold = float(spark.conf.get("spark.payment.priority_medium_value_threshold", "10000"))

    factor = (
        when(col("decline_reason_standard") == lit("FUNDS_OR_LIMIT"), lit(recovery_funds))
        .when(col("decline_reason_standard") == lit("ISSUER_TECHNICAL"), lit(recovery_issuer_tech))
        .when(col("decline_reason_standard") == lit("ISSUER_DO_NOT_HONOR"), lit(recovery_do_not_honor))
        .when(col("decline_reason_standard") == lit("CARD_EXPIRED"), lit(recovery_card_expired))
        .when(col("decline_reason_standard") == lit("FRAUD_SUSPECTED"), lit(recovery_fraud))
        .otherwise(lit(recovery_default))
    )

    return (
        rc
        .withColumn("estimated_recoverable_declines", round(col("decline_count") * factor, 0).cast("int"))
        .withColumn("estimated_recoverable_value", round(col("total_declined_value") * factor, 2))
        .withColumn(
            "priority",
            when(col("estimated_recoverable_value") >= priority_high_threshold, lit(1))
            .when(col("estimated_recoverable_value") >= priority_medium_threshold, lit(2))
            .otherwise(lit(3)),
        )
        .orderBy(col("priority").asc(), col("estimated_recoverable_value").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Entry-System Distribution — Brazil (coverage check)
# MAGIC (backend: `/api/analytics/entry-system-distribution-br`)

# COMMAND ----------

@dlt.table(
    name="v_entry_system_distribution_br",
    comment="Brazil transaction distribution by entry system (coverage sanity check)",
    table_properties={"quality": "gold"},
)
def v_entry_system_distribution_br():
    attempts = dlt.read("merchant_visible_attempts_silver")

    br = attempts.filter(col("geo_country") == lit("BR"))

    return (
        br.groupBy("entry_system")
        .agg(
            count("*").alias("transaction_count"),
            sum(when(col("is_approved"), 1).otherwise(0)).alias("approved_count"),
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("approval_rate_pct"),
            round(sum("amount"), 2).alias("total_value"),
        )
        .orderBy(col("transaction_count").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Dedup Collision Stats (quality guardrail)
# MAGIC (backend: `/api/analytics/dedup-collision-stats`)

# COMMAND ----------

@dlt.table(
    name="v_dedup_collision_stats",
    comment="Monitor potential double-counting by canonical_transaction_key",
    table_properties={"quality": "gold"},
)
def v_dedup_collision_stats():
    enriched = dlt.read("payments_enriched_silver")

    collisions = (
        enriched
        .groupBy("canonical_transaction_key")
        .agg(
            count("*").alias("rows_per_key"),
            countDistinct("entry_system").alias("entry_systems_per_key"),
            countDistinct("transaction_id").alias("transaction_ids_per_key"),
        )
        .filter(col("rows_per_key") > 1)
    )

    return (
        collisions
        .agg(
            count("*").alias("colliding_keys"),
            round(avg("rows_per_key"), 2).alias("avg_rows_per_key"),
            round(avg("entry_systems_per_key"), 2).alias("avg_entry_systems_per_key"),
            round(avg("transaction_ids_per_key"), 2).alias("avg_transaction_ids_per_key"),
        )
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## False Insights Quality Metric
# MAGIC (backend: `/api/analytics/false-insights`)

# COMMAND ----------

@dlt.table(
    name="v_false_insights_metric",
    comment="Quality metric: percentage of insights marked invalid/non-actionable by specialists",
    table_properties={"quality": "gold"},
)
def v_false_insights_metric():
    feedback = dlt.read("insight_feedback_silver")

    # Verdict set: valid | invalid | non_actionable
    agg = (
        feedback
        .withColumn("event_date", col("reviewed_at").cast("date"))
        .groupBy("event_date")
        .agg(
            count("*").alias("reviewed_insights"),
            sum(when(col("verdict").isin(["invalid", "non_actionable"]), 1).otherwise(0)).alias("false_insights"),
        )
    )

    return (
        agg
        .withColumn(
            "false_insights_pct",
            round(col("false_insights") * 100.0 / when(col("reviewed_insights") == 0, lit(None)).otherwise(col("reviewed_insights")), 2),
        )
        .orderBy(col("event_date").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Smart Checkout — Brazil / Payment Link: recommended path performance
# MAGIC (backend: `/api/analytics/smart-checkout-path-performance-br`)

# COMMAND ----------

@dlt.table(
    name="v_smart_checkout_path_performance_br",
    comment="Brazil payment-link performance by recommended Smart Checkout path (audit-based)",
    table_properties={"quality": "gold"},
)
def v_smart_checkout_path_performance_br():
    decisions = dlt.read("smart_checkout_decisions_silver")
    payments = dlt.read("payments_enriched_silver")

    joined = (
        decisions.join(payments.select("transaction_id", "is_approved", "amount", "service_path"), on="transaction_id", how="left")
    )

    br_links = joined.filter(
        (col("geo_country") == lit("BR"))
        & (col("flow_type").isin(["payment_link", "payment_link_sep"]))
    )

    return (
        br_links
        .groupBy("recommended_path")
        .agg(
            count("*").alias("transaction_count"),
            sum(when(col("is_approved"), 1).otherwise(0)).alias("approved_count"),
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("approval_rate_pct"),
            round(sum("amount"), 2).alias("total_value"),
        )
        .orderBy(col("transaction_count").desc())
    )
