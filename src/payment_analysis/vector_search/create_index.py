# Databricks notebook source
# MAGIC %md
# MAGIC # Create Vector Search Endpoint and Index
# MAGIC
# MAGIC Creates the vector search endpoint and delta-sync index for **similar-transaction lookup**.
# MAGIC Source table: `transaction_summaries_for_search` (from lakehouse_bootstrap). Run after Lakehouse Bootstrap.
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

print(f"Endpoint: {ENDPOINT_NAME}, Index: {INDEX_NAME}, Source: {SOURCE_TABLE}")

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
