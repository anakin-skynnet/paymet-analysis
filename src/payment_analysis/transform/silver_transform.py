# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Payment Data Transformation
# MAGIC 
# MAGIC Clean, validate, and enrich payment data for analytics.

# COMMAND ----------

import dlt  # type: ignore[import-untyped]
from pyspark.sql.functions import (  # type: ignore[import-untyped]
    array,
    array_remove,
    col,
    concat,
    concat_ws,
    current_timestamp,
    date_format,
    dayofweek,
    hour,
    lag,
    lit,
    row_number,
    sha2,
    sum as spark_sum,
    struct,
    to_date,
    unix_timestamp,
    when,
)
from pyspark.sql.types import (  # type: ignore[import-untyped]
    StringType,
    StructField,
    StructType,
    TimestampType,
)
from pyspark.sql.window import Window  # type: ignore[import-untyped]

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
@dlt.expect("valid_entry_system", "entry_system IN ('PD', 'WS', 'SEP', 'CHECKOUT')")
@dlt.expect("has_response_code", "decline_code_raw IS NOT NULL OR is_approved = true")
@dlt.expect("has_geo_country", "geo_country IS NOT NULL")
def payments_enriched_silver():
    """
    Enrich payment events with:
    - Merchant dimension data
    - Derived features (cross-border flag, risk tier, etc.)
    - Data quality validations
    """
    
    # Read all columns; Lakeflow manages schema evolution for the bronze→silver boundary.
    # Pipeline expectations above enforce required fields at ingestion time.
    payments = dlt.read("payments_raw_bronze")
    merchants = dlt.read("merchants_dim_bronze")
    
    enriched = (
        payments
        .join(
            merchants.select("merchant_id", "merchant_name", "merchant_country", "merchant_risk_tier"),
            on="merchant_id",
            how="left"
        )
        # Default transaction_stage when missing
        .withColumn("transaction_stage", when(col("transaction_stage").isNull(), lit("entry_response")).otherwise(col("transaction_stage")))

        # Add derived columns
        .withColumn("is_cross_border", col("issuer_country") != col("merchant_country"))
        .withColumn("event_date", to_date(col("event_timestamp")))
        .withColumn("event_time", col("event_timestamp"))
        .withColumn("event_hour", hour(col("event_timestamp")))
        .withColumn("event_day_of_week", dayofweek(col("event_timestamp")))

        # Canonical key for merchant-visible attempt dedup across entry systems/flows
        .withColumn(
            "canonical_transaction_key",
            sha2(
                concat_ws(
                    "|",
                    col("merchant_id").cast("string"),
                    col("card_token_id").cast("string"),
                    col("amount").cast("string"),
                    col("currency").cast("string"),
                    col("entry_system").cast("string"),
                    col("flow_type").cast("string"),
                    date_format(col("event_timestamp"), "yyyy-MM-dd-HH-mm"),
                ),
                256,
            ),
        )
        
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

        # Smart Retry scenario split (conceptual)
        .withColumn(
            "retry_scenario",
            when(col("is_recurring") == True, lit("PaymentRecurrence"))
            .when(col("is_retry") == True, lit("PaymentRetry"))
            .otherwise(lit("None")),
        )

        # Reason Codes: starter taxonomy normalization
        .withColumn(
            "decline_reason_standard",
            when(col("is_approved") == True, lit(None))
            .when(col("antifraud_result") == lit("fail"), lit("FRAUD_SUSPECTED"))
            .when(col("decline_reason").isin("INSUFFICIENT_FUNDS", "LIMIT_EXCEEDED"), lit("FUNDS_OR_LIMIT"))
            .when(col("decline_reason").isin("EXPIRED_CARD"), lit("CARD_EXPIRED"))
            .when(col("decline_reason").isin("CVV_MISMATCH"), lit("SECURITY_CVV"))
            .when(col("decline_reason").isin("ISSUER_UNAVAILABLE"), lit("ISSUER_TECHNICAL"))
            .when(col("decline_reason").isin("DO_NOT_HONOR"), lit("ISSUER_DO_NOT_HONOR"))
            .when(col("decline_reason").isin("3DS_AUTH_FAILED"), lit("SECURITY_3DS_FAILED"))
            .otherwise(lit("OTHER")),
        )
        .withColumn(
            "decline_reason_group",
            when(col("is_approved") == True, lit(None))
            .when(col("decline_reason_standard") == lit("FRAUD_SUSPECTED"), lit("fraud"))
            .when(col("decline_reason_standard") == lit("FUNDS_OR_LIMIT"), lit("funds"))
            .when(col("decline_reason_standard").startswith("CARD_"), lit("card"))
            .when(col("decline_reason_standard").startswith("SECURITY_"), lit("security"))
            .when(col("decline_reason_standard").startswith("ISSUER_"), lit("issuer"))
            .otherwise(lit("other")),
        )
        .withColumn(
            "recommended_action",
            when(col("is_approved") == True, lit(None))
            .when(col("decline_reason_standard") == lit("FUNDS_OR_LIMIT"), lit("SmartRetry: delay 24-72h (payday-aware)"))
            .when(col("decline_reason_standard") == lit("CARD_EXPIRED"), lit("Request card update / credential refresh"))
            .when(col("decline_reason_standard") == lit("ISSUER_TECHNICAL"), lit("SmartRetry: immediate retry or alternate network"))
            .when(col("decline_reason_standard") == lit("ISSUER_DO_NOT_HONOR"), lit("Try alternative checkout path (3DS/network token)"))
            .when(col("decline_reason_standard") == lit("FRAUD_SUSPECTED"), lit("Review antifraud rules; reduce false positives"))
            .otherwise(lit("Manual review")),
        )

        # Smart Checkout: compact service-path label
        .withColumn(
            "service_path",
            concat_ws(
                "+",
                array_remove(
                    array(
                        when(col("antifraud_used") == True, concat(lit("antifraud="), col("antifraud_result"))),
                        when(col("three_ds_routed") == True, when(col("three_ds_friction") == True, lit("3ds=challenge")).otherwise(lit("3ds=frictionless"))),
                        when(col("idpay_invoked") == True, when(col("idpay_success") == True, lit("idpay=success")).otherwise(lit("idpay=fail"))),
                        when(col("is_network_token") == True, lit("network_token")),
                        when(col("has_passkey") == True, lit("passkey")),
                        when(col("data_only_used") == True, lit("data_only")),
                        when(col("click_to_pay_used") == True, lit("click_to_pay")),
                        when(col("vault_used") == True, lit("vault")),
                    ),
                    lit(None),
                ),
            ),
        )
        
        # Processing metadata
        .withColumn("_processed_at", current_timestamp())
    )

    # Smart Retry features: attempt sequence + time since last attempt (per merchant+card token)
    w_attempts = Window.partitionBy("merchant_id", "card_token_id").orderBy(col("event_time").asc())
    w_prior = w_attempts.rowsBetween(Window.unboundedPreceding, -1)
    enriched = (
        enriched
        .withColumn("attempt_sequence", row_number().over(w_attempts))
        .withColumn("previous_attempt_time", lag(col("event_time"), 1).over(w_attempts))
        .withColumn(
            "time_since_last_attempt_seconds",
            when(
                col("previous_attempt_time").isNotNull(),
                (unix_timestamp(col("event_time")) - unix_timestamp(col("previous_attempt_time"))).cast("long"),
            ),  # NULL for first attempt in sequence (no previous attempt)
        )
        .withColumn(
            "prior_approved_count",
            spark_sum(when(col("is_approved") == True, lit(1)).otherwise(lit(0))).over(w_prior),
        )
        .withColumn(
            "merchant_retry_policy_max_attempts",
            when(col("merchant_risk_tier") == lit("high"), lit(1))
            .when(col("merchant_risk_tier") == lit("medium"), lit(2))
            .otherwise(lit(3)),
        )
    )

    return enriched


# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table: Merchant-visible attempts (deduplicated)

# COMMAND ----------

@dlt.table(
    name="merchant_visible_attempts_silver",
    comment="One row per merchant-visible attempt (deduplicated across entry systems/flows)",
    table_properties={
        "quality": "silver"
    }
)
def merchant_visible_attempts_silver():
    attempts = dlt.read("payments_enriched_silver")

    w = Window.partitionBy("canonical_transaction_key").orderBy(col("event_time").desc())

    return (
        attempts
        .filter(col("transaction_stage") == lit("entry_response"))
        .withColumn("_rn", row_number().over(w))
        .filter(col("_rn") == lit(1))
        .drop("_rn")
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table: Reason code taxonomy (starter mapping)

# COMMAND ----------

@dlt.table(
    name="reason_code_taxonomy_silver",
    comment="Starter taxonomy for standardized reason codes (demo scaffold)",
    table_properties={"quality": "silver"},
)
def reason_code_taxonomy_silver():
    rows = [
        ("FUNDS_OR_LIMIT", "funds", "HIGH", "SmartRetry: delay 24-72h (payday-aware)",),
        ("ISSUER_TECHNICAL", "issuer", "HIGH", "SmartRetry: immediate retry or alternate network",),
        ("ISSUER_DO_NOT_HONOR", "issuer", "MEDIUM", "Try alternative checkout path (3DS/network token)",),
        ("CARD_EXPIRED", "card", "HIGH", "Request card update / credential refresh",),
        ("SECURITY_CVV", "security", "MEDIUM", "Request CVV re-entry / step-up auth",),
        ("SECURITY_3DS_FAILED", "security", "MEDIUM", "Fallback to alternate auth path; reduce friction",),
        ("FRAUD_SUSPECTED", "fraud", "LOW", "Review antifraud rules; reduce false positives",),
        ("OTHER", "other", "LOW", "Manual review",),
    ]

    return spark.createDataFrame(  # type: ignore[name-defined]
        rows,
        schema=StructType(
            [
                StructField("decline_reason_standard", StringType(), False),
                StructField("decline_reason_group", StringType(), False),
                StructField("actionability", StringType(), False),
                StructField("default_action", StringType(), False),
            ]
        ),
    ).withColumn("_created_at", current_timestamp())


# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table: Insight feedback (counter-metric scaffold)

# COMMAND ----------

@dlt.table(
    name="insight_feedback_silver",
    comment="Domain review feedback on generated insights (for False Insights counter-metric)",
    table_properties={"quality": "silver"},
)
def insight_feedback_silver():
    schema = StructType(
        [
            StructField("insight_id", StringType(), False),
            StructField("insight_type", StringType(), False),
            StructField("reviewer", StringType(), True),
            StructField("verdict", StringType(), False),  # valid | invalid | non_actionable
            StructField("reason", StringType(), True),
            StructField("model_version", StringType(), True),
            StructField("prompt_version", StringType(), True),
            StructField("reviewed_at", TimestampType(), False),
        ]
    )

    # Seed data for demo; in production, populate from app/ops feedback workflow
    from datetime import datetime

    seed_rows = [
        ("ins-001", "decline_pattern", "analyst@company.com", "valid", "Confirmed recurring BIN-level decline pattern", "1.0", "v2", datetime(2025, 12, 1, 10, 30, 0)),
        ("ins-002", "routing_suggestion", "ops@company.com", "invalid", "Suggested processor has higher decline rate for this MCC", "1.0", "v2", datetime(2025, 12, 2, 14, 15, 0)),
        ("ins-003", "retry_recommendation", "analyst@company.com", "valid", "Retry window recommendation improved recovery by 12%", "1.0", "v2", datetime(2025, 12, 3, 9, 0, 0)),
        ("ins-004", "risk_alert", "risk@company.com", "non_actionable", "Alert threshold too sensitive for this merchant segment", "1.0", "v1", datetime(2025, 12, 4, 16, 45, 0)),
        ("ins-005", "approval_optimization", "analyst@company.com", "valid", "3DS exemption recommendation validated", "1.0", "v2", datetime(2025, 12, 5, 11, 20, 0)),
    ]
    return spark.createDataFrame(seed_rows, schema=schema)  # type: ignore[name-defined]

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


# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table: Smart Checkout decisions (demo scaffold)

# COMMAND ----------

@dlt.table(
    name="smart_checkout_decisions_silver",
    comment="Recommended Smart Checkout path decisions (for audit + performance evaluation)",
    table_properties={"quality": "silver"},
)
def smart_checkout_decisions_silver():
    """
    Demo scaffold that derives a recommended checkout path from transaction context.

    In production, this would be populated by a decisioning service in the payment flow.
    """

    payments = dlt.read("payments_enriched_silver")

    return (
        payments.select(
            col("transaction_id"),
            col("event_timestamp").alias("decision_timestamp"),
            col("geo_country"),
            col("flow_type"),
            col("entry_system"),
            col("risk_tier"),
            col("fraud_score"),
            col("device_trust_score"),
            col("is_network_token"),
            col("has_passkey"),
            col("three_ds_routed"),
        )
        .withColumn(
            "recommended_path",
            when(col("risk_tier") == lit("high"), lit("3ds_challenge"))
            .when(col("has_passkey") == True, lit("passkey"))
            .when(col("is_network_token") == True, lit("network_token"))
            .when(col("three_ds_routed") == True, lit("3ds_frictionless"))
            .otherwise(lit("standard")),
        )
        .withColumn(
            "decision_reason",
            when(col("risk_tier") == lit("high"), lit("High risk: step-up auth"))
            .when(col("has_passkey") == True, lit("Passkey available"))
            .when(col("is_network_token") == True, lit("Network token available"))
            .when(col("three_ds_routed") == True, lit("3DS mandated (debit BR)"))
            .otherwise(lit("Default path")),
        )
        .withColumn("_created_at", current_timestamp())
    )
