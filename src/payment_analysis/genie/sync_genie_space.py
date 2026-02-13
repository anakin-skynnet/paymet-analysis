# Databricks notebook source
# MAGIC %md
# MAGIC # Genie Space Configuration Sync
# MAGIC
# MAGIC This notebook configures and maintains the Genie Space for Payment Analytics.

# COMMAND ----------

from databricks.sdk import WorkspaceClient  # type: ignore[import-untyped]
from pyspark.sql.functions import col  # type: ignore[import-untyped]
import json

# COMMAND ----------

# Get parameters (when run as job, workspace_path/catalog/schema/space_id come from job base_parameters = bundle vars)
dbutils.widgets.text("workspace_path", "")
dbutils.widgets.text("catalog", "ahs_demos_catalog")
dbutils.widgets.text("schema", "payment_analysis")
dbutils.widgets.text("space_id", "")

WORKSPACE_PATH = (dbutils.widgets.get("workspace_path") or "").strip()
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
GENIE_SPACE_ID = (dbutils.widgets.get("space_id") or "").strip()

print(f"Configuring Genie Space for {CATALOG}.{SCHEMA}" + (f" (space_id={GENIE_SPACE_ID})" if GENIE_SPACE_ID else ""))

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
- For time trends, use v_daily_trends or v_approval_trends_by_second (or v_approval_trends_hourly; both return per-second data with event_second)
"""
}

print("Genie Space Configuration:")
print(json.dumps(genie_space_config, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ensure Gold Views Exist
# MAGIC
# MAGIC Genie tables/views must exist in catalog.schema. If missing (e.g. Job 3 not run), run gold_views.sql here so v_performance_by_geography and other views are created.

# COMMAND ----------

import os

def _view_exists(catalog: str, schema: str, view_name: str) -> bool:
    try:
        spark.sql(f"DESCRIBE TABLE EXTENDED `{catalog}`.`{schema}`.`{view_name}`")
        return True
    except Exception:
        return False

def _ensure_gold_views(workspace_path: str, catalog: str, schema: str) -> None:
    """Run gold_views.sql if payments_enriched_silver exists and any Genie view is missing."""
    spark.sql(f"USE CATALOG `{catalog}`")
    spark.sql(f"USE SCHEMA `{schema}`")
    if not spark.catalog.tableExists("payments_enriched_silver"):
        print("payments_enriched_silver not found; skip creating gold views. Run Job 3 (Initialize Ingestion) after the Lakeflow pipeline has produced silver data.")
        return
    sql_path = os.path.join(workspace_path or ".", "src", "payment_analysis", "transform", "gold_views.sql")
    if not os.path.isfile(sql_path):
        print(f"gold_views.sql not found at {sql_path}; ensure workspace_path is set and bundle sync includes transform.")
        return
    with open(sql_path, encoding="utf-8") as f:
        content = f.read()
    header = f"USE CATALOG `{catalog}`;\nUSE SCHEMA `{schema}`;\n\n"
    full_sql = header + content
    statements = []
    for part in full_sql.replace("\r\n", "\n").split(";\n"):
        stmt = part.strip()
        if not stmt:
            continue
        lines = [line for line in stmt.split("\n") if line.strip() and not line.strip().startswith("--")]
        if not lines:
            continue
        statements.append(stmt + ";")
    for stmt in statements:
        try:
            spark.sql(stmt)
        except Exception as e:
            print(f"Gold view statement failed: {e}")
            raise
    print(f"Gold views ensured in {catalog}.{schema} ({len(statements)} statements).")

_genie_views = ["v_executive_kpis", "v_top_decline_reasons", "v_performance_by_geography", "v_solution_performance", "v_daily_trends"]
_missing = [v for v in _genie_views if not _view_exists(CATALOG, SCHEMA, v)]
if _missing and WORKSPACE_PATH:
    print(f"Missing views for Genie: {_missing}. Running gold_views.sql ...")
    _ensure_gold_views(WORKSPACE_PATH, CATALOG, SCHEMA)
elif _missing:
    print(f"Missing views: {_missing}. Set workspace_path in the job and re-run, or run Job 3 (Initialize Ingestion) first.")
else:
    print("All required gold views exist.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create/Update Genie Space

# COMMAND ----------

# Initialize workspace client
w = WorkspaceClient()

# Save configuration to volume for reference (always)
config_path = f"/Volumes/{CATALOG}/{SCHEMA}/reports/genie_config.json"
try:
    dbutils.fs.put(config_path, json.dumps(genie_space_config, indent=2), overwrite=True)
    print(f"Configuration saved to: {config_path}")
except Exception:
    print("Note: Could not save to volume (may not exist yet)")

# If space_id is set, push sample questions (and title/description) to the deployed Genie space
if GENIE_SPACE_ID:
    try:
        space = w.genie.get_space(space_id=GENIE_SPACE_ID, include_serialized_space=True)
        serialized = getattr(space, "serialized_space", None) or getattr(space, "serializedSpace", None)
        if serialized:
            config = json.loads(serialized) if isinstance(serialized, str) else serialized
            config["sample_questions"] = genie_space_config["sample_questions"]
            config["title"] = genie_space_config["name"]
            config["description"] = genie_space_config["description"]
            w.genie.update_space(
                space_id=GENIE_SPACE_ID,
                title=genie_space_config["name"],
                description=genie_space_config["description"],
                serialized_space=json.dumps(config) if isinstance(config, dict) else serialized,
            )
            print(f"Updated Genie space {GENIE_SPACE_ID} with {len(genie_space_config['sample_questions'])} sample questions.")
        else:
            w.genie.update_space(
                space_id=GENIE_SPACE_ID,
                title=genie_space_config["name"],
                description=genie_space_config["description"],
            )
            print(f"Updated Genie space {GENIE_SPACE_ID} title and description. Add sample questions in Genie UI if needed.")
    except Exception as e:
        print(f"Could not update Genie space via API: {e}")
        print("Sample questions are in genie_config.json and in this notebook; add them in Workspace > Genie > Space > Configure.")
else:
    print("No space_id provided; sample questions are in genie_config.json. Set genie_space_id in the job to push to the deployed space.")

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
