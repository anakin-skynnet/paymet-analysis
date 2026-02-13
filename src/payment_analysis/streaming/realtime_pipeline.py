# Databricks notebook source
# MAGIC %md
# MAGIC # Real-Time Payment Processing Pipeline
# MAGIC
# MAGIC Lakeflow for continuous streaming processing of payment events.

# COMMAND ----------

import dlt  # type: ignore[import-untyped]
from pyspark.sql.functions import (  # type: ignore[import-untyped]
    approx_count_distinct,
    avg,
    col,
    concat,
    count,
    current_timestamp,
    hour,
    lit,
    minute,
    round,
    sum,
    to_date,
    when,
    window,
)

# COMMAND ----------

# Configurable thresholds (set via pipeline config or spark.conf; aligned with Lakebase decisionconfig)
RISK_THRESHOLD_HIGH = float(spark.conf.get("spark.payment.risk_threshold_high", "0.75"))
RISK_THRESHOLD_MEDIUM = float(spark.conf.get("spark.payment.risk_threshold_medium", "0.35"))
RISK_WEIGHT_FRAUD = float(spark.conf.get("spark.payment.risk_weight_fraud", "0.5"))
RISK_WEIGHT_AML = float(spark.conf.get("spark.payment.risk_weight_aml", "0.3"))
RISK_WEIGHT_DEVICE = float(spark.conf.get("spark.payment.risk_weight_device", "0.2"))
ALERT_APPROVAL_RATE_WARNING = float(spark.conf.get("spark.payment.alert_approval_rate_warning", "80"))
ALERT_APPROVAL_RATE_CRITICAL = float(spark.conf.get("spark.payment.alert_approval_rate_critical", "70"))
ALERT_FRAUD_SCORE_WARNING = float(spark.conf.get("spark.payment.alert_fraud_score_warning", "0.5"))
ALERT_FRAUD_SCORE_CRITICAL = float(spark.conf.get("spark.payment.alert_fraud_score_critical", "0.7"))
ALERT_LATENCY_WARNING = float(spark.conf.get("spark.payment.alert_latency_warning", "500"))

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

        # NOTE: Rich enrichment (canonical_transaction_key, retry_scenario,
        # decline taxonomy, service_path) lives in the ETL pipeline's
        # payments_enriched_silver table.  This real-time pipeline keeps only
        # the lightweight features needed by the 10-second windowed aggregations
        # and alert generation downstream.
        
        # Risk categorization (thresholds from pipeline config; aligned with Lakebase decisionconfig)
        .withColumn("risk_tier", 
            when(col("fraud_score") > RISK_THRESHOLD_HIGH, "high")
            .when(col("fraud_score") > RISK_THRESHOLD_MEDIUM, "medium")
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
        
        # Composite risk (weights from pipeline config)
        .withColumn("composite_risk_score",
            (col("fraud_score") * RISK_WEIGHT_FRAUD + col("aml_risk_score") * RISK_WEIGHT_AML + (1 - col("device_trust_score")) * RISK_WEIGHT_DEVICE)
        )
        
        .withColumn("_processed_at", current_timestamp())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Real-Time Aggregations (10-second windows for real-time insights)

# COMMAND ----------

@dlt.table(
    name="payments_stream_metrics_10s",
    comment="Real-time payment metrics aggregated per 10 seconds",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.managed": "true"
    }
)
def payments_stream_metrics_10s():
    """
    10-second windowed aggregations for real-time dashboards and alerts.
    """
    return (
        dlt.readStream("payments_stream_silver")
        .withWatermark("event_timestamp", "1 minute")
        .groupBy(
            window(col("event_timestamp"), "10 seconds"),
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
            approx_count_distinct("merchant_id").alias("unique_merchants")
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
    comment="Real-time alerts for anomaly detection (not read by any view or API; optional for monitoring)",
    table_properties={
        "quality": "gold"
    }
)
def payments_stream_alerts():
    """
    Real-time alert generation for anomalies (10-second windows).

    Note: Uses ``dlt.readStream`` for incremental processing from the upstream
    streaming metrics table.  No backend or dashboard reads this table. Safe to
    drop from pipeline if streaming alerts are not needed.
    """
    metrics = dlt.readStream("payments_stream_metrics_10s")
    
    return (
        metrics
        .filter(
            (col("approval_rate_pct") < ALERT_APPROVAL_RATE_WARNING) |
            (col("avg_fraud_score") > ALERT_FRAUD_SCORE_WARNING) |
            (col("avg_latency_ms") > ALERT_LATENCY_WARNING)
        )
        .withColumn("alert_type",
            when(col("approval_rate_pct") < ALERT_APPROVAL_RATE_WARNING, "LOW_APPROVAL_RATE")
            .when(col("avg_fraud_score") > ALERT_FRAUD_SCORE_WARNING, "HIGH_FRAUD_RATE")
            .when(col("avg_latency_ms") > ALERT_LATENCY_WARNING, "HIGH_LATENCY")
            .otherwise("UNKNOWN")
        )
        .withColumn("severity",
            when(col("approval_rate_pct") < ALERT_APPROVAL_RATE_CRITICAL, "CRITICAL")
            .when(col("avg_fraud_score") > ALERT_FRAUD_SCORE_CRITICAL, "CRITICAL")
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
