# Databricks notebook source
# MAGIC %md
# MAGIC # Create Vector Search Endpoint and Index
# MAGIC
# MAGIC Creates the vector search endpoint and delta-sync index for **similar-transaction lookup**.
# MAGIC Source table: `transaction_summaries_for_search` (populated from `payments_enriched_silver`).
# MAGIC Run after Lakehouse Bootstrap **and** the Lakeflow pipeline so that the silver table has data.
# MAGIC
# MAGIC **Steps performed by this notebook:**
# MAGIC 1. Populate `transaction_summaries_for_search` from `payments_enriched_silver` (MERGE).
# MAGIC 2. Create the vector search endpoint (if it doesn't exist).
# MAGIC 3. Create the delta-sync index (if it doesn't exist).
# MAGIC 4. Trigger a sync so the index picks up the latest data.
# MAGIC
# MAGIC **Used to accelerate approval rates:** This index powers similar-case recommendations. AI agents or a scheduled job can query it to find past transactions similar to a given context, then generate recommendations (e.g. retry after 2h; similar cases approved 65%) and write them to `approval_recommendations` with `source_type = 'vector_search'`. The app shows these in the Decisioning page so end-users get actionable recommendations to accelerate approvals.

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (
    DeltaSyncVectorIndexSpecRequest,
    EmbeddingSourceColumn,
    EndpointType,
    PipelineType,
    VectorIndexType,
)

# COMMAND ----------

# Get parameters (when run as job: catalog, schema, environment from job base_parameters). dbutils is provided by Databricks runtime.
dbutils.widgets.text("catalog", "ahs_demos_catalog")  # type: ignore[name-defined]
dbutils.widgets.text("schema", "payment_analysis")  # type: ignore[name-defined]
dbutils.widgets.text("environment", "dev")  # type: ignore[name-defined]

CATALOG = dbutils.widgets.get("catalog")  # type: ignore[name-defined]
SCHEMA = dbutils.widgets.get("schema")  # type: ignore[name-defined]
ENV = dbutils.widgets.get("environment")  # type: ignore[name-defined]

ENDPOINT_NAME = f"payment-similar-transactions-{ENV}"
INDEX_NAME = f"{CATALOG}.{SCHEMA}.similar_transactions_index"
SOURCE_TABLE = f"{CATALOG}.{SCHEMA}.transaction_summaries_for_search"
EMBEDDING_MODEL = "databricks-bge-large-en"

SILVER_TABLE = f"{CATALOG}.{SCHEMA}.payments_enriched_silver"
print(f"Endpoint: {ENDPOINT_NAME}, Index: {INDEX_NAME}, Source: {SOURCE_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Populate source table from Silver (if silver table exists)
# MAGIC
# MAGIC Build a `summary_text` for each transaction by concatenating its key attributes.
# MAGIC The vector search embedding model will convert this text into a dense vector.
# MAGIC We use MERGE to avoid duplicates on re-runs. If `payments_enriched_silver` does not exist
# MAGIC (e.g. Lakeflow pipeline not run yet), we skip the MERGE and still create the endpoint and index
# MAGIC so Job 1 can complete; re-run this notebook or Job 3 to sync data later.

# COMMAND ----------

try:
    row_count_before = spark.sql(f"SELECT COUNT(*) AS cnt FROM {SOURCE_TABLE}").first()["cnt"]  # type: ignore[name-defined]
    print(f"Source table row count BEFORE merge: {row_count_before}")

    merge_sql = f"""
    MERGE INTO {SOURCE_TABLE} AS target
    USING (
        SELECT
            transaction_id,
            CONCAT(
                'Transaction ', transaction_id,
                ': amount=', CAST(amount AS STRING), ' ', currency,
                ', merchant_segment=', COALESCE(merchant_segment, 'unknown'),
                ', network=', COALESCE(card_network, 'unknown'),
                ', payment_solution=', COALESCE(payment_solution, 'unknown'),
                ', outcome=', CASE WHEN is_approved THEN 'approved'
                                   ELSE CONCAT('declined:', COALESCE(decline_reason, 'unknown')) END,
                ', fraud_score=', CAST(ROUND(COALESCE(fraud_score, 0), 3) AS STRING),
                ', risk_tier=', COALESCE(risk_tier, 'unknown'),
                ', country=', COALESCE(issuer_country, 'unknown'),
                ', cross_border=', CAST(COALESCE(is_cross_border, false) AS STRING)
            ) AS summary_text,
            CASE WHEN is_approved THEN 'approved' ELSE 'declined' END AS outcome,
            amount,
            card_network AS network,
            merchant_segment,
            COALESCE(event_time, current_timestamp()) AS created_at
        FROM {SILVER_TABLE}
    ) AS source
    ON target.transaction_id = source.transaction_id
    WHEN NOT MATCHED THEN
        INSERT (transaction_id, summary_text, outcome, amount, network, merchant_segment, created_at)
        VALUES (source.transaction_id, source.summary_text, source.outcome, source.amount, source.network, source.merchant_segment, source.created_at)
    WHEN MATCHED THEN
        UPDATE SET
            summary_text   = source.summary_text,
            outcome        = source.outcome,
            amount         = source.amount,
            network        = source.network,
            merchant_segment = source.merchant_segment
    """
    spark.sql(merge_sql)  # type: ignore[name-defined]

    row_count_after = spark.sql(f"SELECT COUNT(*) AS cnt FROM {SOURCE_TABLE}").first()["cnt"]  # type: ignore[name-defined]
    print(f"Source table row count AFTER merge: {row_count_after}  (added {row_count_after - row_count_before} rows)")
except Exception as e:
    err = str(e).lower()
    if "table or view not found" in err or "cannot find" in err or "payments_enriched_silver" in err:
        print(f"Silver table {SILVER_TABLE} not found; skipping MERGE. Endpoint and index will be created with current source table state.")
    else:
        raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Create Vector Search Endpoint & Index

# COMMAND ----------

w = WorkspaceClient()

# Create endpoint if it does not exist
try:
    existing = list(w.vector_search_endpoints.list_endpoints())
    names = [e.name for e in existing]
except Exception:
    names = []
if ENDPOINT_NAME not in names:
    print(f"Creating endpoint {ENDPOINT_NAME}...")
    w.vector_search_endpoints.create_endpoint_and_wait(name=ENDPOINT_NAME, endpoint_type=EndpointType.STANDARD)
    print("Endpoint created.")
else:
    print(f"Endpoint {ENDPOINT_NAME} already exists.")

# COMMAND ----------

# Create index if it does not exist
try:
    idx = w.vector_search_indexes.get_index(index_name=INDEX_NAME)
    print(f"Index {INDEX_NAME} already exists.")
except Exception:
    print(f"Creating index {INDEX_NAME}...")
    spec = DeltaSyncVectorIndexSpecRequest(
        source_table=SOURCE_TABLE,
        pipeline_type=PipelineType.TRIGGERED,
        embedding_source_columns=[
            EmbeddingSourceColumn(name="summary_text", embedding_model_endpoint_name=EMBEDDING_MODEL),
        ],
    )
    w.vector_search_indexes.create_index(
        name=INDEX_NAME,
        endpoint_name=ENDPOINT_NAME,
        primary_key="transaction_id",
        index_type=VectorIndexType.DELTA_SYNC,
        delta_sync_index_spec=spec,
    )
    print("Index creation started. Sync will run according to pipeline_type TRIGGERED.")

# COMMAND ----------

# Optionally trigger a sync if index already existed
try:
    w.vector_search_indexes.sync_index(index_name=INDEX_NAME)
    print("Sync triggered.")
except Exception as e:
    print(f"Sync trigger (optional): {e}")
