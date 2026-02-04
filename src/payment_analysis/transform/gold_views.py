# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer - Analytics Views
# MAGIC 
# MAGIC Create aggregated views optimized for dashboards and Genie queries.

# COMMAND ----------

import dlt
from pyspark.sql.functions import *

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
    """Decline patterns for analysis and recovery."""
    
    payments = dlt.read("payments_enriched_silver")
    
    return (
        payments
        .filter(~col("is_approved"))
        .groupBy("decline_reason", "merchant_segment")
        .agg(
            count("*").alias("decline_count"),
            round(avg("fraud_score"), 3).alias("avg_fraud_score"),
            round(avg("device_trust_score"), 3).alias("avg_device_trust"),
            round(sum("amount"), 2).alias("total_declined_value"),
            countDistinct("merchant_id").alias("affected_merchants")
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
    """Retry success metrics by decline reason."""
    
    payments = dlt.read("payments_enriched_silver")
    
    return (
        payments
        .filter(col("is_retry") == True)
        .groupBy("decline_reason", "retry_count")
        .agg(
            count("*").alias("retry_attempts"),
            round(sum(when(col("is_approved"), 1).otherwise(0)) * 100.0 / count("*"), 2).alias("success_rate_pct"),
            round(sum(when(col("is_approved"), col("amount")).otherwise(0)), 2).alias("recovered_value"),
            round(avg("fraud_score"), 3).alias("avg_fraud_score")
        )
        .withColumn("effectiveness",
            when(col("success_rate_pct") > 40, "Effective")
            .when(col("success_rate_pct") > 20, "Moderate")
            .otherwise("Low")
        )
        .orderBy("decline_reason", "retry_count")
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
            when(col("decline_reason") == "INSUFFICIENT_FUNDS", "Enable Smart Retry with 24-48h delay")
            .when(col("decline_reason") == "ISSUER_UNAVAILABLE", "Route to alternative network")
            .when(col("decline_reason") == "CARD_EXPIRED", "Trigger card update notification")
            .when(col("decline_reason") == "DO_NOT_HONOR", "Try alternative payment solution")
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
            "decline_reason",
            "merchant_segment",
            "decline_count",
            "recovery_potential",
            "recommendation",
            "estimated_recovery_value",
            "priority"
        )
        .orderBy("priority", col("estimated_recovery_value").desc())
    )
