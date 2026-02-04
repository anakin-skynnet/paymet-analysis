# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Payment Events Ingestion
# MAGIC 
# MAGIC Delta Live Tables pipeline for ingesting raw payment events into the Bronze layer.

# COMMAND ----------

import dlt
from pyspark.sql.functions import *
from pyspark.sql.types import *

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Table: Raw Payment Events

# COMMAND ----------

# Define schema for payment events
payment_event_schema = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("merchant_id", StringType(), False),
    StructField("cardholder_id", StringType(), True),
    StructField("amount", DoubleType(), False),
    StructField("currency", StringType(), False),
    StructField("card_network", StringType(), True),
    StructField("card_bin", StringType(), True),
    StructField("issuer_country", StringType(), True),
    StructField("merchant_segment", StringType(), True),
    StructField("payment_solution", StringType(), True),
    StructField("entry_mode", StringType(), True),
    StructField("device_type", StringType(), True),
    StructField("device_fingerprint", StringType(), True),
    StructField("ip_address", StringType(), True),
    StructField("uses_3ds", BooleanType(), True),
    StructField("is_network_token", BooleanType(), True),
    StructField("has_passkey", BooleanType(), True),
    StructField("is_recurring", BooleanType(), True),
    StructField("is_retry", BooleanType(), True),
    StructField("retry_count", IntegerType(), True),
    StructField("fraud_score", DoubleType(), True),
    StructField("aml_risk_score", DoubleType(), True),
    StructField("device_trust_score", DoubleType(), True),
    StructField("is_approved", BooleanType(), True),
    StructField("decline_reason", StringType(), True),
    StructField("decline_code_raw", StringType(), True),
    StructField("processing_time_ms", IntegerType(), True),
    StructField("event_timestamp", TimestampType(), False)
])

# COMMAND ----------

@dlt.table(
    name="payments_raw_bronze",
    comment="Raw payment events ingested from streaming source",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.managed": "true"
    }
)
def payments_raw_bronze():
    """
    Ingest raw payment events from cloud storage or streaming source.
    
    In production, this would read from:
    - Kafka/Event Hubs for real-time streaming
    - Auto Loader for file-based ingestion
    """
    
    # For demo: generate synthetic data
    # In production: use spark.readStream with Auto Loader or Kafka
    
    return (
        spark.range(1000)
        .withColumn("transaction_id", concat(lit("txn_"), col("id").cast("string")))
        .withColumn("merchant_id", concat(lit("m_"), (col("id") % 50).cast("string")))
        .withColumn("cardholder_id", concat(lit("ch_"), (col("id") % 200).cast("string")))
        .withColumn("amount", (rand() * 1000 + 10).cast("double"))
        .withColumn("currency", lit("USD"))
        .withColumn("card_network", array(lit("visa"), lit("mastercard"), lit("amex")).getItem((rand() * 3).cast("int")))
        .withColumn("card_bin", concat(lit("4111"), (rand() * 100000).cast("int").cast("string")))
        .withColumn("issuer_country", array(lit("US"), lit("GB"), lit("CA"), lit("DE"), lit("FR")).getItem((rand() * 5).cast("int")))
        .withColumn("merchant_segment", array(lit("Travel"), lit("Retail"), lit("Gaming"), lit("Digital"), lit("Entertainment")).getItem((rand() * 5).cast("int")))
        .withColumn("payment_solution", array(lit("standard"), lit("3ds"), lit("network_token"), lit("passkey")).getItem((rand() * 4).cast("int")))
        .withColumn("entry_mode", array(lit("ecom"), lit("contactless"), lit("chip"), lit("manual")).getItem((rand() * 4).cast("int")))
        .withColumn("device_type", array(lit("mobile"), lit("desktop"), lit("tablet")).getItem((rand() * 3).cast("int")))
        .withColumn("device_fingerprint", concat(lit("df_"), (rand() * 10000).cast("int").cast("string")))
        .withColumn("ip_address", concat((rand() * 255).cast("int").cast("string"), lit("."), (rand() * 255).cast("int").cast("string"), lit("."), (rand() * 255).cast("int").cast("string"), lit("."), (rand() * 255).cast("int").cast("string")))
        .withColumn("uses_3ds", (rand() > 0.4).cast("boolean"))
        .withColumn("is_network_token", (rand() > 0.7).cast("boolean"))
        .withColumn("has_passkey", (rand() > 0.9).cast("boolean"))
        .withColumn("is_recurring", (rand() > 0.6).cast("boolean"))
        .withColumn("is_retry", (rand() > 0.9).cast("boolean"))
        .withColumn("retry_count", (rand() * 3).cast("int"))
        .withColumn("fraud_score", rand().cast("double"))
        .withColumn("aml_risk_score", rand().cast("double") * 0.5)
        .withColumn("device_trust_score", (rand() * 0.5 + 0.5).cast("double"))
        .withColumn("is_approved", (rand() > 0.15).cast("boolean"))
        .withColumn("decline_reason", when(col("is_approved"), lit(None)).otherwise(
            array(lit("INSUFFICIENT_FUNDS"), lit("FRAUD_SUSPECTED"), lit("EXPIRED_CARD"), lit("DO_NOT_HONOR"), lit("ISSUER_UNAVAILABLE")).getItem((rand() * 5).cast("int"))
        ))
        .withColumn("decline_code_raw", when(col("is_approved"), lit(None)).otherwise(concat(lit("RC"), (rand() * 100).cast("int").cast("string"))))
        .withColumn("processing_time_ms", (rand() * 400 + 50).cast("int"))
        .withColumn("event_timestamp", current_timestamp())
        .withColumn("_ingested_at", current_timestamp())
        .drop("id")
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Table: Merchant Dimension

# COMMAND ----------

@dlt.table(
    name="merchants_dim_bronze",
    comment="Merchant dimension data",
    table_properties={
        "quality": "bronze"
    }
)
def merchants_dim_bronze():
    """Merchant dimension table for enrichment."""
    
    return (
        spark.range(50)
        .withColumn("merchant_id", concat(lit("m_"), col("id").cast("string")))
        .withColumn("merchant_name", concat(lit("Merchant "), col("id").cast("string")))
        .withColumn("merchant_segment", array(lit("Travel"), lit("Retail"), lit("Gaming"), lit("Digital"), lit("Entertainment")).getItem((col("id") % 5).cast("int")))
        .withColumn("merchant_country", array(lit("US"), lit("GB"), lit("CA")).getItem((col("id") % 3).cast("int")))
        .withColumn("merchant_risk_tier", array(lit("low"), lit("medium"), lit("high")).getItem((col("id") % 3).cast("int")))
        .withColumn("created_at", current_timestamp())
        .drop("id")
    )
