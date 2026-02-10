# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer - Analytics Views
# MAGIC 
# MAGIC Create aggregated views optimized for dashboards and Genie queries.

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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Approval KPIs

# COMMAND ----------

@dlt.table(
    name="v_approval_kpis",
    comment="Approval rate KPIs by various dimensions",
    table_properties={
        "quality": "gold"
    }
)
def v_approval_kpis():
    """Executive-level approval KPIs."""
    
    payments = dlt.read("payments_enriched_silver")
    
    return (
        payments
        .groupBy("event_date")
        .agg(
            count("*").alias("total_transactions"),
            sum(when(col("is_approved"), 1).otherwise(0)).alias("approved_count"),
            sum(when(~col("is_approved"), 1).otherwise(0)).alias("declined_count"),
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("approval_rate_pct"),
            round(avg("fraud_score"), 3).alias("avg_fraud_score"),
            round(sum("amount"), 2).alias("total_value"),
            countDistinct("merchant_id").alias("unique_merchants")
        )
        .orderBy(col("event_date").desc())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Decline Patterns

# COMMAND ----------

@dlt.table(
    name="v_decline_patterns",
    comment="Decline reason analysis for recovery opportunities",
    table_properties={
        "quality": "gold"
    }
)
def v_decline_patterns():
    """Reason-code-first decline patterns with entry system and flow type segmentation."""
    
    payments = dlt.read("payments_enriched_silver")
    
    return (
        payments
        .filter(~col("is_approved"))
        .groupBy("decline_reason_standard", "decline_reason_group", "entry_system", "flow_type", "merchant_segment")
        .agg(
            count("*").alias("decline_count"),
            round(avg("fraud_score"), 3).alias("avg_fraud_score"),
            round(avg("device_trust_score"), 3).alias("avg_device_trust"),
            round(sum("amount"), 2).alias("total_declined_value"),
            countDistinct("merchant_id").alias("affected_merchants"),
            round(avg("composite_risk_score"), 3).alias("avg_composite_risk"),
        )
        .withColumn("recovery_potential",
            when((col("avg_fraud_score") < 0.3) & (col("avg_device_trust") > 0.6), "HIGH")
            .when((col("avg_fraud_score") < 0.5) & (col("avg_device_trust") > 0.4), "MEDIUM")
            .otherwise("LOW")
        )
        .orderBy(col("decline_count").desc())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Risk Signals

# COMMAND ----------

@dlt.table(
    name="v_risk_signals",
    comment="Risk signal aggregations for fraud monitoring",
    table_properties={
        "quality": "gold"
    }
)
def v_risk_signals():
    """Risk signals by segment and geography."""
    
    payments = dlt.read("payments_enriched_silver")
    
    return (
        payments
        .groupBy("merchant_segment", "issuer_country", "risk_tier")
        .agg(
            count("*").alias("transaction_count"),
            round(avg("fraud_score"), 3).alias("avg_fraud_score"),
            round(avg("aml_risk_score"), 3).alias("avg_aml_score"),
            round(avg("composite_risk_score"), 3).alias("avg_composite_risk"),
            sum(when(col("is_approved"), 1).otherwise(0)).alias("approved_count"),
            round(sum("amount"), 2).alias("total_value")
        )
        .withColumn("approval_rate_pct",
            round(col("approved_count") * 100.0 / col("transaction_count"), 2)
        )
        .orderBy(col("avg_composite_risk").desc())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Routing Performance

# COMMAND ----------

@dlt.table(
    name="v_routing_performance",
    comment="Payment solution routing performance metrics",
    table_properties={
        "quality": "gold"
    }
)
def v_routing_performance():
    """Performance metrics by payment solution and network."""
    
    payments = dlt.read("payments_enriched_silver")
    
    return (
        payments
        .groupBy("payment_solution", "card_network")
        .agg(
            count("*").alias("transaction_count"),
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("approval_rate_pct"),
            round(avg("processing_time_ms"), 2).alias("avg_latency_ms"),
            round(avg("fraud_score"), 3).alias("avg_fraud_score"),
            round(sum("amount"), 2).alias("total_value")
        )
        .orderBy(col("transaction_count").desc())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Retry Performance

# COMMAND ----------

@dlt.table(
    name="v_retry_performance",
    comment="Smart retry strategy performance",
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
        .filter(col("is_retry") == False)
        .agg(
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("baseline_approval_pct")
        )
    )

    # Retry cohorts with features
    retry_cohorts = (
        payments
        .filter(col("is_retry") == True)
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
            when(col("success_rate_pct") > 40, "Effective")
            .when(col("success_rate_pct") > 20, "Moderate")
            .otherwise("Low")
        )
        .orderBy("retry_scenario", "decline_reason_standard", "retry_count")
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Recommendations

# COMMAND ----------

@dlt.table(
    name="v_recommendations",
    comment="AI-generated recommendations for approval rate improvement",
    table_properties={
        "quality": "gold"
    }
)
def v_recommendations():
    """Actionable recommendations based on data patterns."""
    
    decline_patterns = dlt.read("v_decline_patterns")
    
    return (
        decline_patterns
        .filter(col("recovery_potential").isin("HIGH", "MEDIUM"))
        .withColumn("recommendation",
            when(col("decline_reason_standard") == "FUNDS_OR_LIMIT", "Enable Smart Retry with 24-48h delay")
            .when(col("decline_reason_standard") == "ISSUER_TECHNICAL", "Route to alternative network")
            .when(col("decline_reason_standard") == "CARD_EXPIRED", "Trigger card update notification")
            .when(col("decline_reason_standard") == "ISSUER_DO_NOT_HONOR", "Try alternative payment solution")
            .when(col("decline_reason_standard") == "FRAUD_SUSPECTED", "Review antifraud rules; reduce false positives")
            .when(col("decline_reason_standard") == "SECURITY_CVV", "Request CVV re-entry / step-up auth")
            .when(col("decline_reason_standard") == "SECURITY_3DS_FAILED", "Fallback to alternate auth path; reduce friction")
            .otherwise("Manual review recommended")
        )
        .withColumn("estimated_recovery_value",
            round(col("total_declined_value") * 
                when(col("recovery_potential") == "HIGH", 0.4)
                .when(col("recovery_potential") == "MEDIUM", 0.2)
                .otherwise(0.05), 2)
        )
        .withColumn("priority",
            when(col("estimated_recovery_value") > 10000, 1)
            .when(col("estimated_recovery_value") > 1000, 2)
            .otherwise(3)
        )
        .select(
            "decline_reason_standard",
            "decline_reason_group",
            "merchant_segment",
            "decline_count",
            "recovery_potential",
            "recommendation",
            "estimated_recovery_value",
            "priority"
        )
        .orderBy("priority", col("estimated_recovery_value").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Smart Checkout (Brazil / Payment Link) — service-path breakdown

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
# MAGIC ## Gold View: Smart Checkout (Brazil / Payment Link) — 3DS funnel

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
            sum(when(col("three_ds_routed") == True, 1).otherwise(0)).alias("three_ds_routed_count"),
            sum(when(col("three_ds_friction") == True, 1).otherwise(0)).alias("three_ds_friction_count"),
            sum(when(col("three_ds_authenticated") == True, 1).otherwise(0)).alias("three_ds_authenticated_count"),
            sum(when((col("three_ds_authenticated") == True) & (col("is_approved") == True), 1).otherwise(0)).alias("issuer_approved_after_auth_count"),
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
# MAGIC ## Gold View: Reason Codes (Brazil) — unified taxonomy and actionability

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
# MAGIC ## Gold View: Reason Codes Insights (Brazil) — estimated recovery / uplift (demo)

# COMMAND ----------

@dlt.table(
    name="v_reason_code_insights_br",
    comment="Brazil reason-code insights with estimated recoverability and prioritization (demo heuristic)",
    table_properties={"quality": "gold"},
)
def v_reason_code_insights_br():
    rc = dlt.read("v_reason_codes_br")

    # Heuristic recoverability factors (placeholder; replace with learned estimates)
    factor = (
        when(col("decline_reason_standard") == lit("FUNDS_OR_LIMIT"), lit(0.25))
        .when(col("decline_reason_standard") == lit("ISSUER_TECHNICAL"), lit(0.40))
        .when(col("decline_reason_standard") == lit("ISSUER_DO_NOT_HONOR"), lit(0.20))
        .when(col("decline_reason_standard") == lit("CARD_EXPIRED"), lit(0.05))
        .when(col("decline_reason_standard") == lit("FRAUD_SUSPECTED"), lit(0.10))
        .otherwise(lit(0.05))
    )

    return (
        rc
        .withColumn("estimated_recoverable_declines", round(col("decline_count") * factor, 0).cast("int"))
        .withColumn("estimated_recoverable_value", round(col("total_declined_value") * factor, 2))
        .withColumn(
            "priority",
            when(col("estimated_recoverable_value") >= 100000, lit(1))
            .when(col("estimated_recoverable_value") >= 10000, lit(2))
            .otherwise(lit(3)),
        )
        .orderBy(col("priority").asc(), col("estimated_recoverable_value").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Brazil entry-system distribution (coverage check)

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
            sum(when(col("is_approved") == True, 1).otherwise(0)).alias("approved_count"),
            round(sum(when(col("is_approved") == True, 1).otherwise(0)) * 100.0 / count("*"), 2).alias("approval_rate_pct"),
            round(sum("amount"), 2).alias("total_value"),
        )
        .orderBy(col("transaction_count").desc())
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold View: Dedup collision stats (double-counting guardrail)

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
# MAGIC ## Gold View: False Insights counter-metric

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
# MAGIC ## Gold View: Smart Checkout (Brazil / Payment Link) — recommended path performance

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
            sum(when(col("is_approved") == True, 1).otherwise(0)).alias("approved_count"),
            round(sum(when(col("is_approved") == True, 1).otherwise(0)) * 100.0 / count("*"), 2).alias("approval_rate_pct"),
            round(sum("amount"), 2).alias("total_value"),
        )
        .orderBy(col("transaction_count").desc())
    )
