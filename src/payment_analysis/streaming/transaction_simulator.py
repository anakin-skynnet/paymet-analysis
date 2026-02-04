# Databricks notebook source
# MAGIC %md
# MAGIC # Transaction Stream Simulator
# MAGIC 
# MAGIC Generates high-volume synthetic payment events (1000/second) for real-time pipeline testing.

# COMMAND ----------

import time
import random
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pyspark.sql.functions import *
from pyspark.sql.types import *

# COMMAND ----------

# Get parameters
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "payment_analysis_dev")
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

def generate_event():
    """Generate a single realistic payment event."""
    amount = random.lognormvariate(4.0, 1.5)  # Log-normal distribution for amounts
    fraud_score = random.betavariate(2, 8)  # Beta distribution skewed low
    is_approved = random.random() > (0.1 + fraud_score * 0.3)  # Higher fraud = more declines
    
    return {
        "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
        "merchant_id": random.choice(MERCHANTS),
        "cardholder_id": f"ch_{random.randint(1, 10000)}",
        "amount": round(amount, 2),
        "currency": "USD" if random.random() > 0.2 else random.choice(["EUR", "GBP", "CAD"]),
        "card_network": random.choice(CARD_NETWORKS),
        "card_bin": f"4{random.randint(10000, 99999)}",
        "issuer_country": random.choice(COUNTRIES),
        "merchant_segment": random.choice(MERCHANT_SEGMENTS),
        "payment_solution": random.choice(PAYMENT_SOLUTIONS),
        "entry_mode": random.choice(ENTRY_MODES),
        "device_type": random.choice(["mobile", "desktop", "tablet"]),
        "device_fingerprint": f"df_{random.randint(1, 5000)}",
        "ip_address": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        "uses_3ds": random.random() > 0.4,
        "is_network_token": random.random() > 0.7,
        "has_passkey": random.random() > 0.9,
        "is_recurring": random.random() > 0.6,
        "is_retry": random.random() > 0.9,
        "retry_count": random.randint(0, 3) if random.random() > 0.9 else 0,
        "fraud_score": round(fraud_score, 4),
        "aml_risk_score": round(random.betavariate(2, 10), 4),
        "device_trust_score": round(random.betavariate(8, 2), 4),
        "is_approved": is_approved,
        "decline_reason": None if is_approved else random.choice(DECLINE_REASONS),
        "decline_code_raw": None if is_approved else f"RC{random.randint(1, 99):02d}",
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
    amount DOUBLE NOT NULL,
    currency STRING NOT NULL,
    card_network STRING,
    card_bin STRING,
    issuer_country STRING,
    merchant_segment STRING,
    payment_solution STRING,
    entry_mode STRING,
    device_type STRING,
    device_fingerprint STRING,
    ip_address STRING,
    uses_3ds BOOLEAN,
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
    _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
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
BATCHES_PER_SECOND = EVENTS_PER_SECOND // BATCH_SIZE
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
        if batch_count % (BATCHES_PER_SECOND * 10) == 0:
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
row_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {target_table}").collect()[0]["cnt"]
print(f"Total rows in {target_table}: {row_count:,}")

# Sample recent events
display(spark.sql(f"""
SELECT * FROM {target_table}
ORDER BY event_timestamp DESC
LIMIT 10
"""))
