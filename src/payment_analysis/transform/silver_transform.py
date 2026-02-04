# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Payment Data Transformation
# MAGIC 
# MAGIC Clean, validate, and enrich payment data for analytics.

# COMMAND ----------

import dlt
from pyspark.sql.functions import *

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table: Payments Enriched

# COMMAND ----------

@dlt.table(
    name="payments_enriched_silver",
    comment="Cleaned and enriched payment transactions",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
@dlt.expect_or_drop("valid_transaction_id", "transaction_id IS NOT NULL")
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect_or_fail("valid_merchant", "merchant_id IS NOT NULL")
def payments_enriched_silver():
    """
    Enrich payment events with:
    - Merchant dimension data
    - Derived features (cross-border flag, risk tier, etc.)
    - Data quality validations
    """
    
    payments = dlt.read("payments_raw_bronze")
    merchants = dlt.read("merchants_dim_bronze")
    
    return (
        payments
        .join(
            merchants.select("merchant_id", "merchant_name", "merchant_country", "merchant_risk_tier"),
            on="merchant_id",
            how="left"
        )
        # Add derived columns
        .withColumn("is_cross_border", col("issuer_country") != col("merchant_country"))
        .withColumn("event_date", to_date(col("event_timestamp")))
        .withColumn("event_time", col("event_timestamp"))
        .withColumn("event_hour", hour(col("event_timestamp")))
        .withColumn("event_day_of_week", dayofweek(col("event_timestamp")))
        
        # Risk categorization
        .withColumn("risk_tier", 
            when(col("fraud_score") > 0.7, "high")
            .when(col("fraud_score") > 0.3, "medium")
            .otherwise("low")
        )
        
        # Amount buckets for analysis
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
        
        # Processing metadata
        .withColumn("_processed_at", current_timestamp())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table: Decision Log

# COMMAND ----------

@dlt.table(
    name="decision_log_silver",
    comment="Audit log of all decisioning calls",
    table_properties={
        "quality": "silver"
    }
)
def decision_log_silver():
    """
    Decision audit log for tracking auth/retry/routing decisions.
    
    In production, this would be populated by the decisioning API.
    """
    
    payments = dlt.read("payments_enriched_silver")
    
    return (
        payments
        .select(
            col("transaction_id"),
            lit("authentication").alias("decision_type"),
            col("event_timestamp").alias("decision_timestamp"),
            struct(
                col("merchant_id"),
                col("amount"),
                col("fraud_score"),
                col("device_trust_score")
            ).alias("request_context"),
            struct(
                when(col("uses_3ds"), "3ds_challenge")
                .when(col("has_passkey"), "passkey")
                .otherwise("frictionless").alias("recommended_path"),
                col("risk_tier")
            ).alias("decision_response"),
            col("_processed_at")
        )
    )
