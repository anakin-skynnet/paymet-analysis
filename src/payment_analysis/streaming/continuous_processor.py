# Databricks notebook source
# MAGIC %md
# MAGIC # Continuous Stream Processor
# MAGIC 
# MAGIC Real-time processing of payment events using Structured Streaming.

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *

# COMMAND ----------

# Get parameters (when run as job, catalog/schema = bundle var.catalog, var.schema)
dbutils.widgets.text("catalog", "ahs_demos_catalog")
dbutils.widgets.text("schema", "dev_ariel_hdez_payment_analysis")
dbutils.widgets.text("checkpoint_location", "/tmp/checkpoints/stream_processor")
dbutils.widgets.text("trigger_interval", "1 second")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
CHECKPOINT_LOCATION = dbutils.widgets.get("checkpoint_location")
TRIGGER_INTERVAL = dbutils.widgets.get("trigger_interval")

print(f"Configuration:")
print(f"  Catalog: {CATALOG}")
print(f"  Schema: {SCHEMA}")
print(f"  Checkpoint: {CHECKPOINT_LOCATION}")
print(f"  Trigger: {TRIGGER_INTERVAL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read Stream from Input Table

# COMMAND ----------

# Source table with Change Data Feed enabled
source_table = f"{CATALOG}.{SCHEMA}.payments_stream_input"

# Read as stream using CDF
stream_df = (
    spark.readStream
    .format("delta")
    .option("readChangeFeed", "true")
    .option("startingVersion", 0)
    .table(source_table)
    .filter(col("_change_type").isin(["insert", "update_postimage"]))
)

print(f"Reading stream from: {source_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Real-time Enrichment & Processing

# COMMAND ----------

# Enrich the stream
enriched_stream = (
    stream_df
    # Add derived columns
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
    
    # Composite risk score
    .withColumn("composite_risk_score",
        (col("fraud_score") * 0.5 + col("aml_risk_score") * 0.3 + (1 - col("device_trust_score")) * 0.2)
    )
    
    # Processing timestamp
    .withColumn("_processed_at", current_timestamp())
    
    # Drop CDF columns
    .drop("_change_type", "_commit_version", "_commit_timestamp")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Silver Table

# COMMAND ----------

# Target table
silver_table = f"{CATALOG}.{SCHEMA}.payments_realtime_silver"

# Write stream to silver table
query = (
    enriched_stream.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"{CHECKPOINT_LOCATION}/silver")
    .trigger(processingTime=TRIGGER_INTERVAL)
    .toTable(silver_table)
)

print(f"Writing stream to: {silver_table}")
print(f"Stream query ID: {query.id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Real-time Aggregations (1-minute windows)

# COMMAND ----------

# Aggregated metrics stream
agg_stream = (
    enriched_stream
    .withWatermark("event_timestamp", "2 minutes")
    .groupBy(
        window(col("event_timestamp"), "1 minute"),
        col("merchant_segment"),
        col("payment_solution")
    )
    .agg(
        count("*").alias("transaction_count"),
        sum(when(col("is_approved"), 1).otherwise(0)).alias("approved_count"),
        avg("amount").alias("avg_amount"),
        sum("amount").alias("total_amount"),
        avg("fraud_score").alias("avg_fraud_score"),
        avg("processing_time_ms").alias("avg_latency_ms")
    )
    .withColumn("approval_rate", col("approved_count") / col("transaction_count") * 100)
    .withColumn("window_start", col("window.start"))
    .withColumn("window_end", col("window.end"))
    .drop("window")
)

# Write aggregations
agg_table = f"{CATALOG}.{SCHEMA}.payments_realtime_metrics"

agg_query = (
    agg_stream.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"{CHECKPOINT_LOCATION}/metrics")
    .trigger(processingTime=TRIGGER_INTERVAL)
    .toTable(agg_table)
)

print(f"Writing aggregations to: {agg_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Monitor Streams

# COMMAND ----------

# Wait for streams (in continuous mode, this runs forever)
import time

try:
    while True:
        active = spark.streams.active  # type: ignore[name-defined]
        if not active:
            print("No active streams — exiting monitor loop.")
            break

        for stream in active:
            progress = stream.recentProgress
            if progress:
                latest = progress[-1]
                print(
                    f"Stream {stream.name}: "
                    f"{latest.get('numInputRows', 0)} rows/batch, "
                    f"processing rate: "
                    f"{latest.get('processedRowsPerSecond', 0):.0f} rows/sec"
                )

        time.sleep(30)  # Status update every 30 seconds
except KeyboardInterrupt:
    print("Monitor loop interrupted — stopping streams.")
    for stream in spark.streams.active:  # type: ignore[name-defined]
        stream.stop()
except Exception as exc:
    print(f"Stream monitoring error: {exc}")
    raise
