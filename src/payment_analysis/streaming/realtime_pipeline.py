# Databricks notebook source
# MAGIC %md
# MAGIC # Real-Time Payment Processing Pipeline
# MAGIC 
# MAGIC Delta Live Tables pipeline for continuous streaming processing of payment events.

# COMMAND ----------

import dlt
from pyspark.sql.functions import *
from pyspark.sql.types import *

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze: Stream Input (CDC from simulator table)

# COMMAND ----------

@dlt.table(
    name="payments_stream_bronze",
    comment="Real-time payment events from streaming source",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.managed": "true",
        "delta.enableChangeDataFeed": "true"
    }
)
def payments_stream_bronze():
    """
    Read from the streaming input table with Change Data Feed.
    In production, replace with Kafka/Event Hubs source.
    """
    return (
        spark.readStream
        .format("delta")
        .option("readChangeFeed", "true")
        .option("startingVersion", "latest")
        .table("payments_stream_input")
        .filter(col("_change_type").isin(["insert", "update_postimage"]))
        .drop("_change_type", "_commit_version", "_commit_timestamp")
        .withColumn("_ingested_at", current_timestamp())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver: Real-Time Enrichment

# COMMAND ----------

@dlt.table(
    name="payments_stream_silver",
    comment="Real-time enriched payment events",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true",
        "delta.enableChangeDataFeed": "true"
    }
)
@dlt.expect_or_drop("valid_transaction_id", "transaction_id IS NOT NULL")
@dlt.expect_or_drop("valid_amount", "amount > 0")
def payments_stream_silver():
    """
    Enrich streaming payments with derived features.
    """
    return (
        dlt.readStream("payments_stream_bronze")
        # Derived columns
        .withColumn("event_date", to_date(col("event_timestamp")))
        .withColumn("event_hour", hour(col("event_timestamp")))
        .withColumn("event_minute", minute(col("event_timestamp")))
        
        # Risk categorization
        .withColumn("risk_tier", 
            when(col("fraud_score") > 0.7, "high")
            .when(col("fraud_score") > 0.3, "medium")
            .otherwise("low")
        )
        
        # Amount bucket
        .withColumn("amount_bucket",
            when(col("amount") < 50, "micro")
            .when(col("amount") < 200, "small")
            .when(col("amount") < 500, "medium")
            .when(col("amount") < 1000, "large")
            .otherwise("very_large")
        )
        
        # Composite risk
        .withColumn("composite_risk_score",
            (col("fraud_score") * 0.5 + col("aml_risk_score") * 0.3 + (1 - col("device_trust_score")) * 0.2)
        )
        
        .withColumn("_processed_at", current_timestamp())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Real-Time Aggregations (1-minute windows)

# COMMAND ----------

@dlt.table(
    name="payments_stream_metrics_1min",
    comment="Real-time payment metrics aggregated per minute",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.managed": "true"
    }
)
def payments_stream_metrics_1min():
    """
    1-minute windowed aggregations for real-time dashboards.
    """
    return (
        dlt.readStream("payments_stream_silver")
        .withWatermark("event_timestamp", "2 minutes")
        .groupBy(
            window(col("event_timestamp"), "1 minute"),
            col("merchant_segment"),
            col("payment_solution"),
            col("card_network")
        )
        .agg(
            count("*").alias("transaction_count"),
            sum(when(col("is_approved"), 1).otherwise(0)).alias("approved_count"),
            sum(when(~col("is_approved"), 1).otherwise(0)).alias("declined_count"),
            avg("amount").alias("avg_amount"),
            sum("amount").alias("total_amount"),
            avg("fraud_score").alias("avg_fraud_score"),
            avg("processing_time_ms").alias("avg_latency_ms"),
            countDistinct("merchant_id").alias("unique_merchants")
        )
        .withColumn("approval_rate_pct", 
            round(col("approved_count") / col("transaction_count") * 100, 2)
        )
        .withColumn("window_start", col("window.start"))
        .withColumn("window_end", col("window.end"))
        .drop("window")
    )

# COMMAND ----------

@dlt.table(
    name="payments_stream_alerts",
    comment="Real-time alerts for anomaly detection",
    table_properties={
        "quality": "gold"
    }
)
def payments_stream_alerts():
    """
    Real-time alert generation for anomalies.
    """
    metrics = dlt.read("payments_stream_metrics_1min")
    
    return (
        metrics
        .filter(
            (col("approval_rate_pct") < 80) |  # Low approval rate
            (col("avg_fraud_score") > 0.5) |   # High fraud
            (col("avg_latency_ms") > 500)      # High latency
        )
        .withColumn("alert_type",
            when(col("approval_rate_pct") < 80, "LOW_APPROVAL_RATE")
            .when(col("avg_fraud_score") > 0.5, "HIGH_FRAUD_RATE")
            .when(col("avg_latency_ms") > 500, "HIGH_LATENCY")
            .otherwise("UNKNOWN")
        )
        .withColumn("severity",
            when(col("approval_rate_pct") < 70, "CRITICAL")
            .when(col("avg_fraud_score") > 0.7, "CRITICAL")
            .otherwise("WARNING")
        )
        .withColumn("alert_message",
            concat(
                lit("Alert: "),
                col("alert_type"),
                lit(" detected in "),
                col("merchant_segment"),
                lit(" via "),
                col("payment_solution")
            )
        )
        .select(
            "window_start",
            "window_end",
            "alert_type",
            "severity",
            "merchant_segment",
            "payment_solution",
            "approval_rate_pct",
            "avg_fraud_score",
            "avg_latency_ms",
            "transaction_count",
            "alert_message"
        )
    )
