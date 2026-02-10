# Databricks notebook source
# MAGIC %md
# MAGIC # Transaction Stream Simulator
# MAGIC 
# MAGIC Generates high-volume synthetic payment events (1000/second) for real-time pipeline testing.

# COMMAND ----------

import time
import random
import uuid
import builtins
from datetime import datetime

from pyspark.sql.functions import col, current_timestamp, to_timestamp  # type: ignore[import-untyped]
from pyspark.sql.types import (  # type: ignore[import-untyped]
    BooleanType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# Save Python's built-in round before any PySpark shadowing
python_round = builtins.round

# COMMAND ----------

# Get parameters (when run as job, catalog/schema = bundle var.catalog, var.schema)
dbutils.widgets.text("catalog", "ahs_demos_catalog")
dbutils.widgets.text("schema", "dev_ariel_hdez_payment_analysis")
dbutils.widgets.text("events_per_second", "1000")
dbutils.widgets.text("duration_minutes", "60")
dbutils.widgets.text("output_mode", "delta")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
EVENTS_PER_SECOND = int(dbutils.widgets.get("events_per_second"))
DURATION_MINUTES = int(dbutils.widgets.get("duration_minutes"))
OUTPUT_MODE = dbutils.widgets.get("output_mode")

print(f"Configuration:")
print(f"  Catalog: {CATALOG}")
print(f"  Schema: {SCHEMA}")
print(f"  Events/second: {EVENTS_PER_SECOND}")
print(f"  Duration: {DURATION_MINUTES} minutes")
print(f"  Output mode: {OUTPUT_MODE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Event Generation Functions

# COMMAND ----------

# Reference data for realistic generation
MERCHANTS = [f"m_{i}" for i in range(100)]
CARD_NETWORKS = ["visa", "mastercard", "amex", "discover"]
COUNTRIES = ["US", "GB", "CA", "DE", "FR", "JP", "AU", "NL", "ES", "IT"]
MERCHANT_SEGMENTS = ["Travel", "Retail", "Gaming", "Digital", "Entertainment", "Grocery", "Fuel", "Subscription"]
PAYMENT_SOLUTIONS = ["standard", "3ds", "network_token", "passkey", "apple_pay", "google_pay"]
ENTRY_MODES = ["ecom", "contactless", "chip", "manual", "recurring"]
DECLINE_REASONS = ["INSUFFICIENT_FUNDS", "FRAUD_SUSPECTED", "EXPIRED_CARD", "DO_NOT_HONOR", "ISSUER_UNAVAILABLE", "CVV_MISMATCH", "LIMIT_EXCEEDED"]

# Brazil-first provenance dimensions (aligns with initiative scope)
GEO_COUNTRIES = ["BR", "US", "MX", "AR", "CL"]
ENTRY_SYSTEMS_BR = ["PD", "WS", "SEP", "CHECKOUT"]
PAYMENT_METHOD_TYPES = ["credit", "debit"]

def weighted_choice(options):
    """Pick a value from [(value, weight), ...]."""
    values = [v for v, _w in options]
    weights = [w for _v, w in options]
    return random.choices(values, weights=weights, k=1)[0]

def derive_flow_type(entry_system: str, is_recurring: bool, is_payment_link: bool) -> str:
    if is_payment_link and entry_system in {"CHECKOUT", "PD", "WS"}:
        return "payment_link"
    if is_payment_link and entry_system == "SEP":
        return "payment_link_sep"
    if is_recurring:
        return "recurring"
    if entry_system == "WS":
        return "legacy_ws"
    return "standard_ecom"

def generate_event():
    """Generate a single realistic payment event."""
    # Geo distribution: Brazil is the majority (70%+)
    geo_country = weighted_choice([("BR", 0.72), ("US", 0.10), ("MX", 0.08), ("AR", 0.06), ("CL", 0.04)])

    # Entry system distribution (Brazil monthly view)
    if geo_country == "BR":
        entry_system = weighted_choice([("PD", 0.62), ("WS", 0.34), ("SEP", 0.03), ("CHECKOUT", 0.01)])
    else:
        entry_system = weighted_choice([("WS", 0.70), ("PD", 0.20), ("SEP", 0.05), ("CHECKOUT", 0.05)])

    # Scenario flags
    is_payment_link = random.random() < (0.12 if geo_country == "BR" else 0.06)
    is_recurring = random.random() > 0.6

    amount = random.lognormvariate(4.0, 1.5)  # Log-normal distribution for amounts
    fraud_score = random.betavariate(2, 8)  # Beta distribution skewed low
    aml_risk_score = random.betavariate(2, 10)
    device_trust_score = random.betavariate(8, 2)

    card_network = random.choice(CARD_NETWORKS)
    payment_method_type = weighted_choice([("credit", 0.98), ("debit", 0.02)]) if geo_country == "BR" else weighted_choice([("credit", 0.95), ("debit", 0.05)])

    # Smart Checkout service flags (simulated)
    vault_used = random.random() < 0.65
    data_only_used = random.random() < 0.10
    click_to_pay_used = random.random() < 0.05
    idpay_invoked = random.random() < 0.04
    idpay_success = (random.random() < 0.70) if idpay_invoked else None

    # Network token: mandatory for VISA in this demo context
    is_network_token = True if card_network == "visa" else (random.random() > 0.7)
    has_passkey = random.random() > 0.9

    # 3DS: mandatory for debit in Brazil (simulate funnel stats)
    three_ds_routed = bool(geo_country == "BR" and payment_method_type == "debit")
    three_ds_friction = (random.random() < 0.80) if three_ds_routed else None
    three_ds_authenticated = (random.random() < 0.60) if three_ds_routed else None

    # Antifraud: attribute ~40–50% of declines in BR payment links
    antifraud_used = random.random() < 0.85

    # Base approval probability before interventions
    base_decline_prob = 0.08 + fraud_score * 0.30 + (0.05 if geo_country == "BR" else 0.02)

    # Apply simplified Smart Checkout effects
    if is_network_token:
        base_decline_prob *= 0.95
    if has_passkey:
        base_decline_prob *= 0.90
    if data_only_used:
        base_decline_prob *= 0.98

    # 3DS can reduce issuer declines if authenticated; otherwise it declines
    if three_ds_routed:
        if not three_ds_authenticated:
            is_approved = False
            decline_reason = "3DS_AUTH_FAILED"
        else:
            is_approved = random.random() < 0.80  # 80% of authenticated are approved
            decline_reason = None if is_approved else "DO_NOT_HONOR"
    else:
        is_approved = random.random() > base_decline_prob
        decline_reason = None if is_approved else random.choice(DECLINE_REASONS)

    # Antifraud decline attribution (only when declined)
    antifraud_result = "not_run"
    if antifraud_used:
        antifraud_result = "pass"
        if (not is_approved) and geo_country == "BR" and is_payment_link and random.random() < 0.45:
            antifraud_result = "fail"
            decline_reason = "FRAUD_SUSPECTED"

    decline_code_raw = None if is_approved else f"RC{random.randint(1, 99):02d}"
    merchant_response_code = "00" if is_approved else (decline_code_raw or "RC00")

    flow_type = derive_flow_type(entry_system=entry_system, is_recurring=is_recurring, is_payment_link=is_payment_link)
    
    return {
        "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
        "merchant_id": random.choice(MERCHANTS),
        "cardholder_id": f"ch_{random.randint(1, 10000)}",
        "card_token_id": f"ct_{random.randint(1, 200000)}",
        "amount": python_round(amount, 2),
        "currency": "USD" if random.random() > 0.2 else random.choice(["EUR", "GBP", "CAD"]),
        "card_network": card_network,
        "card_bin": f"4{random.randint(10000, 99999)}",
        "issuer_country": random.choice(COUNTRIES),
        "geo_country": geo_country,
        "merchant_segment": random.choice(MERCHANT_SEGMENTS),
        "entry_system": entry_system,
        "flow_type": flow_type,
        "transaction_stage": random.choice(["entry_response", "downstream_response"]) if flow_type in ("payment_link", "recurring", "payment_link_sep") else "entry_response",
        "merchant_response_code": merchant_response_code,
        "payment_method_type": payment_method_type,
        "payment_solution": random.choice(PAYMENT_SOLUTIONS),
        "entry_mode": random.choice(ENTRY_MODES),
        "device_type": random.choice(["mobile", "desktop", "tablet"]),
        "device_fingerprint": f"df_{random.randint(1, 5000)}",
        "ip_address": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        "uses_3ds": three_ds_routed or (random.random() > 0.4),
        "three_ds_routed": three_ds_routed,
        "three_ds_friction": three_ds_friction,
        "three_ds_authenticated": three_ds_authenticated,
        "antifraud_used": antifraud_used,
        "antifraud_result": antifraud_result,
        "vault_used": vault_used,
        "data_only_used": data_only_used,
        "click_to_pay_used": click_to_pay_used,
        "idpay_invoked": idpay_invoked,
        "idpay_success": idpay_success,
        "is_network_token": is_network_token,
        "has_passkey": has_passkey,
        "is_recurring": is_recurring,
        "is_retry": random.random() > 0.9,
        "retry_count": random.randint(0, 3) if random.random() > 0.9 else 0,
        "fraud_score": python_round(fraud_score, 4),
        "aml_risk_score": python_round(aml_risk_score, 4),
        "device_trust_score": python_round(device_trust_score, 4),
        "is_approved": is_approved,
        "decline_reason": decline_reason,
        "decline_code_raw": decline_code_raw,
        "processing_time_ms": random.randint(50, 500),
        "event_timestamp": datetime.utcnow().isoformat()
    }

def generate_batch(batch_size):
    """Generate a batch of events."""
    return [generate_event() for _ in range(batch_size)]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Schema Definition

# COMMAND ----------

event_schema = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("merchant_id", StringType(), False),
    StructField("cardholder_id", StringType(), True),
    StructField("card_token_id", StringType(), True),
    StructField("amount", DoubleType(), False),
    StructField("currency", StringType(), False),
    StructField("card_network", StringType(), True),
    StructField("card_bin", StringType(), True),
    StructField("issuer_country", StringType(), True),
    StructField("geo_country", StringType(), True),
    StructField("merchant_segment", StringType(), True),
    StructField("entry_system", StringType(), True),
    StructField("flow_type", StringType(), True),
    StructField("transaction_stage", StringType(), True),
    StructField("merchant_response_code", StringType(), True),
    StructField("payment_method_type", StringType(), True),
    StructField("payment_solution", StringType(), True),
    StructField("entry_mode", StringType(), True),
    StructField("device_type", StringType(), True),
    StructField("device_fingerprint", StringType(), True),
    StructField("ip_address", StringType(), True),
    StructField("uses_3ds", BooleanType(), True),
    StructField("three_ds_routed", BooleanType(), True),
    StructField("three_ds_friction", BooleanType(), True),
    StructField("three_ds_authenticated", BooleanType(), True),
    StructField("antifraud_used", BooleanType(), True),
    StructField("antifraud_result", StringType(), True),
    StructField("vault_used", BooleanType(), True),
    StructField("data_only_used", BooleanType(), True),
    StructField("click_to_pay_used", BooleanType(), True),
    StructField("idpay_invoked", BooleanType(), True),
    StructField("idpay_success", BooleanType(), True),
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
    StructField("event_timestamp", StringType(), False)
])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stream Generation

# COMMAND ----------

# Target table
target_table = f"{CATALOG}.{SCHEMA}.payments_stream_input"

# Create table if not exists
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {target_table} (
    transaction_id STRING NOT NULL,
    merchant_id STRING NOT NULL,
    cardholder_id STRING,
    card_token_id STRING,
    amount DOUBLE NOT NULL,
    currency STRING NOT NULL,
    card_network STRING,
    card_bin STRING,
    issuer_country STRING,
    geo_country STRING,
    merchant_segment STRING,
    entry_system STRING,
    flow_type STRING,
    transaction_stage STRING,
    merchant_response_code STRING,
    payment_method_type STRING,
    payment_solution STRING,
    entry_mode STRING,
    device_type STRING,
    device_fingerprint STRING,
    ip_address STRING,
    uses_3ds BOOLEAN,
    three_ds_routed BOOLEAN,
    three_ds_friction BOOLEAN,
    three_ds_authenticated BOOLEAN,
    antifraud_used BOOLEAN,
    antifraud_result STRING,
    vault_used BOOLEAN,
    data_only_used BOOLEAN,
    click_to_pay_used BOOLEAN,
    idpay_invoked BOOLEAN,
    idpay_success BOOLEAN,
    is_network_token BOOLEAN,
    has_passkey BOOLEAN,
    is_recurring BOOLEAN,
    is_retry BOOLEAN,
    retry_count INT,
    fraud_score DOUBLE,
    aml_risk_score DOUBLE,
    device_trust_score DOUBLE,
    is_approved BOOLEAN,
    decline_reason STRING,
    decline_code_raw STRING,
    processing_time_ms INT,
    event_timestamp TIMESTAMP NOT NULL,
    _ingested_at TIMESTAMP
)
USING DELTA
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Raw payment events from transaction stream simulator - 1000 events/second'
""")

print(f"Target table: {target_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Simulation

# COMMAND ----------

# Simulation parameters
BATCH_SIZE = 100  # Events per batch
BATCHES_PER_SECOND = max(1, EVENTS_PER_SECOND // BATCH_SIZE)
SLEEP_TIME = 1.0 / BATCHES_PER_SECOND
TOTAL_SECONDS = DURATION_MINUTES * 60

print(f"Starting simulation:")
print(f"  Batch size: {BATCH_SIZE}")
print(f"  Batches/second: {BATCHES_PER_SECOND}")
print(f"  Total duration: {TOTAL_SECONDS} seconds")

start_time = time.time()
total_events = 0
batch_count = 0

try:
    while (time.time() - start_time) < TOTAL_SECONDS:
        batch_start = time.time()
        
        # Generate and write batch
        events = generate_batch(BATCH_SIZE)
        df = spark.createDataFrame(events, schema=event_schema)
        df = df.withColumn("event_timestamp", to_timestamp(col("event_timestamp")))
        df = df.withColumn("_ingested_at", current_timestamp())
        
        df.write.mode("append").saveAsTable(target_table)
        
        total_events += BATCH_SIZE
        batch_count += 1
        
        # Progress update every 10 seconds
        elapsed = time.time() - start_time
        progress_interval = max(1, BATCHES_PER_SECOND * 10)
        if batch_count % progress_interval == 0:
            rate = total_events / elapsed
            print(f"Progress: {total_events:,} events in {elapsed:.1f}s ({rate:.0f} events/sec)")
        
        # Sleep to maintain target rate
        batch_duration = time.time() - batch_start
        if batch_duration < SLEEP_TIME:
            time.sleep(SLEEP_TIME - batch_duration)

except KeyboardInterrupt:
    print("Simulation interrupted by user")

finally:
    elapsed = time.time() - start_time
    rate = total_events / elapsed if elapsed > 0 else 0
    print(f"\n{'='*60}")
    print(f"Simulation Complete!")
    print(f"  Total events: {total_events:,}")
    print(f"  Duration: {elapsed:.1f} seconds")
    print(f"  Average rate: {rate:.0f} events/second")
    print(f"  Target table: {target_table}")
    print(f"{'='*60}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Results

# COMMAND ----------

# Check row count
row_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {target_table}").first()["cnt"]  # type: ignore[name-defined]
print(f"Total rows in {target_table}: {row_count:,}")

# Sample recent events
display(spark.sql(f"""
SELECT * FROM {target_table}
ORDER BY event_timestamp DESC
LIMIT 10
"""))
