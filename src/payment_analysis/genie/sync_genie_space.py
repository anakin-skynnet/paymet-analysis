# Databricks notebook source
# MAGIC %md
# MAGIC # Genie Space Configuration Sync
# MAGIC 
# MAGIC This notebook configures and maintains the Genie Space for Payment Analytics.

# COMMAND ----------

from databricks.sdk import WorkspaceClient
import json

# COMMAND ----------

# Get parameters
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "payment_analysis_dev")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

print(f"Configuring Genie Space for {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Genie Space Configuration

# COMMAND ----------

# Genie Space configuration
genie_space_config = {
    "name": "Payment Analytics",
    "description": """Natural language interface for payment transaction analytics.

Ask questions like:
- What is the approval rate?
- Show me decline reasons
- Compare performance by country
- Which payment solution is best?
- How many high risk transactions?
""",
    "tables": [
        f"{CATALOG}.{SCHEMA}.v_executive_kpis",
        f"{CATALOG}.{SCHEMA}.v_top_decline_reasons",
        f"{CATALOG}.{SCHEMA}.v_performance_by_geography",
        f"{CATALOG}.{SCHEMA}.v_solution_performance",
        f"{CATALOG}.{SCHEMA}.v_approval_trends_hourly",
        f"{CATALOG}.{SCHEMA}.v_daily_trends",
        f"{CATALOG}.{SCHEMA}.v_active_alerts",
        f"{CATALOG}.{SCHEMA}.payments_enriched_silver"
    ],
    "sample_questions": [
        "What is the current approval rate?",
        "Show me top 5 decline reasons",
        "Compare approval rates by country",
        "Which payment solution has the best approval rate?",
        "How many transactions were processed today?",
        "What's the average fraud score?",
        "Show me high risk transactions from the last hour",
        "What is the trend in approval rate over the past week?",
        "Which merchant segment has the lowest approval rate?",
        "Are there any active alerts?"
    ],
    "instructions": """
## Data Model

This space provides access to payment transaction analytics.

### Key Tables

1. **v_executive_kpis**: Current KPI snapshot
   - approval_rate_pct: Current approval rate (target: >85%)
   - total_transactions: Number of transactions
   - total_value: Sum of transaction amounts
   - avg_fraud_score: Average fraud risk score

2. **v_top_decline_reasons**: Why transactions are declined
   - decline_reason: Reason category
   - decline_count: Number of declines
   - pct_of_declines: Share of total
   - recoverable_pct: Estimated recovery potential

3. **v_performance_by_geography**: Performance by country
   - country: ISO country code
   - approval_rate_pct: Approval rate for that country
   - transaction_count: Volume

4. **v_solution_performance**: Performance by payment method
   - payment_solution: Method (3ds, passkey, etc.)
   - approval_rate_pct: Success rate
   - avg_latency_ms: Processing speed

5. **payments_enriched_silver**: Detailed transactions
   - Use for ad-hoc analysis
   - is_approved: TRUE/FALSE for approval
   - fraud_score: 0-1 (higher = riskier)
   - risk_tier: low/medium/high

### Key Metrics

- **Approval Rate** = SUM(approved) / COUNT(*) * 100
- **Decline Rate** = 100 - Approval Rate
- **Risk Tiers**: low (<0.3), medium (0.3-0.7), high (>0.7)

### Tips

- For overall metrics, start with v_executive_kpis
- For decline analysis, use v_top_decline_reasons
- For geographic breakdown, use v_performance_by_geography
- For time trends, use v_daily_trends or v_approval_trends_hourly
"""
}

print("Genie Space Configuration:")
print(json.dumps(genie_space_config, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create/Update Genie Space

# COMMAND ----------

# Initialize workspace client
w = WorkspaceClient()

# Check if Genie API is available
try:
    # Note: Genie API endpoints may vary by workspace version
    # This is a placeholder for when Genie API becomes available
    
    print("Genie Space configuration prepared.")
    print("\nTo create the Genie Space manually:")
    print("1. Go to Databricks Workspace > Genie")
    print("2. Click 'Create Space'")
    print("3. Name: Payment Analytics")
    print("4. Add the tables listed above")
    print("5. Configure sample questions and instructions")
    
    # Save configuration to volume for reference
    config_path = f"/Volumes/{CATALOG}/{SCHEMA}/reports/genie_config.json"
    
    try:
        dbutils.fs.put(config_path, json.dumps(genie_space_config, indent=2), overwrite=True)
        print(f"\nConfiguration saved to: {config_path}")
    except:
        print("\nNote: Could not save to volume (may not exist yet)")
        
except Exception as e:
    print(f"Note: Genie API configuration: {e}")
    print("Genie Space must be configured via the UI.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Table Metadata for Genie

# COMMAND ----------

# Verify tables have proper comments for Genie
for table in genie_space_config["tables"]:
    try:
        table_info = spark.sql(f"DESCRIBE TABLE EXTENDED {table}")
        comment_row = table_info.filter(col("col_name") == "Comment").collect()
        
        if comment_row and comment_row[0]["data_type"]:
            print(f"✓ {table}: Has comment")
        else:
            print(f"✗ {table}: Missing comment - Genie may not understand this table well")
    except Exception as e:
        print(f"? {table}: Could not verify ({e})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Sample Queries

# COMMAND ----------

# Test that sample queries work
print("Testing sample SQL queries:\n")

test_queries = [
    ("Approval Rate", f"SELECT approval_rate_pct FROM {CATALOG}.{SCHEMA}.v_executive_kpis LIMIT 1"),
    ("Top Declines", f"SELECT * FROM {CATALOG}.{SCHEMA}.v_top_decline_reasons LIMIT 5"),
    ("By Country", f"SELECT country, approval_rate_pct FROM {CATALOG}.{SCHEMA}.v_performance_by_geography LIMIT 5"),
]

for name, query in test_queries:
    try:
        result = spark.sql(query)
        count = result.count()
        print(f"✓ {name}: Query returned {count} rows")
    except Exception as e:
        print(f"✗ {name}: Query failed - {e}")

print("\nGenie Space sync complete!")
