# Databricks notebook source
# MAGIC %md
# MAGIC # Create UC Agent Tools
# MAGIC
# MAGIC Creates Unity Catalog functions for the Agent Framework (AgentBricks path):
# MAGIC `get_decline_trends`, `get_route_performance`, `get_retry_success_rates`, etc. in `catalog.schema`.
# MAGIC Run after gold views and `payments_enriched_silver` exist. Wrapper for Job 3; implementation in `payment_analysis.agents.uc_tools.run_create_uc_agent_tools`.

# COMMAND ----------

dbutils.widgets.text("catalog", "ahs_demos_catalog")  # type: ignore[name-defined]
dbutils.widgets.text("schema", "payment_analysis")  # type: ignore[name-defined]

catalog = dbutils.widgets.get("catalog")  # type: ignore[name-defined]
schema = dbutils.widgets.get("schema")  # type: ignore[name-defined]

if not catalog or not schema:
    raise ValueError("Widgets catalog and schema are required")

# COMMAND ----------

from payment_analysis.agents.uc_tools.run_create_uc_agent_tools import run

run(catalog, schema)

# COMMAND ----------

# MAGIC %md
# MAGIC UC agent tool functions are ready. Use them with LangGraph agents or the custom agent framework.
