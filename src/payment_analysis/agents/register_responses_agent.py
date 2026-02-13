# Databricks notebook source
# MAGIC %md
# MAGIC # Register Payment Analysis ResponsesAgent to Unity Catalog
# MAGIC
# MAGIC Logs the `agent.py` ResponsesAgent (MLflow 3.x, OpenAI Responses API) to MLflow
# MAGIC and registers it in Unity Catalog. Follows Mosaic AI Agent Framework best practices:
# MAGIC
# MAGIC 1. **Models-from-code**: `mlflow.pyfunc.log_model(python_model="agent.py")`
# MAGIC 2. **Resource declarations**: UC functions declared for automatic auth passthrough
# MAGIC 3. **Pre-deployment validation**: `mlflow.models.predict()` before registration
# MAGIC 4. **Agent Evaluation**: `mlflow.genai.evaluate()` with domain-specific test cases
# MAGIC 5. **Deployment**: `databricks.agents.deploy()` to Model Serving
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - UC agent tool functions exist (Job 3: create_uc_agent_tools)
# MAGIC - Schema `agents` exists in the catalog
# MAGIC
# MAGIC **Outcome:** Model registered as `{catalog}.agents.payment_analysis_agent`.

# COMMAND ----------

# MAGIC %pip install -U -qqqq backoff databricks-openai uv databricks-agents mlflow-skinny[databricks]
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import os
import sys
import json

# ---------------------------------------------------------------------------
# Configuration: read from widgets / env
# ---------------------------------------------------------------------------
def _get_config():
    defaults = {
        "catalog": os.environ.get("CATALOG", "ahs_demos_catalog"),
        "schema": os.environ.get("SCHEMA", "payment_analysis"),
        "model_registry_schema": os.environ.get("MODEL_REGISTRY_SCHEMA", "agents"),
        "llm_endpoint": os.environ.get("LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct"),
    }
    try:
        from databricks.sdk.runtime import dbutils
        dbutils.widgets.text("catalog", defaults["catalog"])
        dbutils.widgets.text("schema", defaults["schema"])
        dbutils.widgets.text("model_registry_schema", defaults["model_registry_schema"])
        dbutils.widgets.text("llm_endpoint", defaults["llm_endpoint"])
        return {
            "catalog": (dbutils.widgets.get("catalog") or defaults["catalog"]).strip(),
            "schema": (dbutils.widgets.get("schema") or defaults["schema"]).strip(),
            "model_registry_schema": (dbutils.widgets.get("model_registry_schema") or defaults["model_registry_schema"]).strip(),
            "llm_endpoint": (dbutils.widgets.get("llm_endpoint") or defaults["llm_endpoint"]).strip(),
        }
    except Exception:
        return defaults


config = _get_config()
CATALOG = config["catalog"]
SCHEMA = config["schema"]
MODEL_SCHEMA = config["model_registry_schema"]
LLM_ENDPOINT = config["llm_endpoint"]

# Set env vars so agent.py picks them up
os.environ["CATALOG"] = CATALOG
os.environ["SCHEMA"] = SCHEMA
os.environ["LLM_ENDPOINT"] = LLM_ENDPOINT

print(f"Catalog:  {CATALOG}")
print(f"Schema:   {SCHEMA}")
print(f"Registry: {CATALOG}.{MODEL_SCHEMA}")
print(f"LLM:      {LLM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resolve agent.py path
# MAGIC
# MAGIC The `agent.py` file must be in the same directory as this notebook.

# COMMAND ----------

from pathlib import Path

# Resolve path to agent.py (same directory as this notebook)
_this_dir = Path(__file__).resolve().parent if "__file__" in dir() else Path(".")
agent_path = _this_dir / "agent.py"
if not agent_path.exists():
    # Fallback: try workspace file system paths
    for candidate in [
        Path("/Workspace") / os.environ.get("WORKSPACE_ROOT", "") / "src/payment_analysis/agents/agent.py",
        Path("./src/payment_analysis/agents/agent.py"),
    ]:
        if candidate.exists():
            agent_path = candidate
            break
    else:
        raise FileNotFoundError(
            f"agent.py not found. Looked in: {_this_dir}, CWD: {Path('.').resolve()}"
        )

print(f"Agent path: {agent_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test the agent
# MAGIC
# MAGIC Quick smoke test before logging. Traces are visible in MLflow.

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# Re-read config after restart
import os
os.environ.setdefault("CATALOG", "ahs_demos_catalog")
os.environ.setdefault("SCHEMA", "payment_analysis")
os.environ.setdefault("LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")

# Import the agent
sys.path.insert(0, str(Path(__file__).resolve().parent)) if "__file__" in dir() else None
from agent import AGENT  # noqa: E402

# Test: predict
result = AGENT.predict({
    "input": [{"role": "user", "content": "What are the current approval rates and top decline reasons?"}],
    "custom_inputs": {"session_id": "test-registration"},
})
print(result.model_dump(exclude_none=True))

# COMMAND ----------

# Test: streaming
for chunk in AGENT.predict_stream({
    "input": [{"role": "user", "content": "Show me high-risk transactions from the last day."}],
    "custom_inputs": {"session_id": "test-stream"},
}):
    print(chunk.model_dump(exclude_none=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log the agent as an MLflow model
# MAGIC
# MAGIC Uses **models-from-code** (`python_model="agent.py"`) for clean deployment.
# MAGIC Declares UC function resources for **automatic auth passthrough** at serving time.

# COMMAND ----------

import mlflow
from mlflow.models.resources import DatabricksFunction

# Declare UC function resources for automatic auth passthrough
UC_TOOL_NAMES = [
    f"{CATALOG}.{SCHEMA}.get_decline_trends",
    f"{CATALOG}.{SCHEMA}.get_decline_by_segment",
    f"{CATALOG}.{SCHEMA}.get_route_performance",
    f"{CATALOG}.{SCHEMA}.get_cascade_recommendations",
    f"{CATALOG}.{SCHEMA}.get_retry_success_rates",
    f"{CATALOG}.{SCHEMA}.get_recovery_opportunities",
    f"{CATALOG}.{SCHEMA}.get_high_risk_transactions",
    f"{CATALOG}.{SCHEMA}.get_risk_distribution",
    f"{CATALOG}.{SCHEMA}.get_kpi_summary",
    f"{CATALOG}.{SCHEMA}.get_optimization_opportunities",
    f"{CATALOG}.{SCHEMA}.get_trend_analysis",
    "system.ai.python_exec",
]

resources = [DatabricksFunction(function_name=name) for name in UC_TOOL_NAMES]

with mlflow.start_run(run_name="register_payment_analysis_agent"):
    logged_agent_info = mlflow.pyfunc.log_model(
        name="agent",
        python_model=str(agent_path),
        pip_requirements=[
            "databricks-openai",
            "backoff",
            "databricks-sdk",
        ],
        resources=resources,
    )

print(f"Logged model: {logged_agent_info.model_uri}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluate the agent
# MAGIC
# MAGIC Uses Mosaic AI Agent Evaluation with domain-specific test cases.

# COMMAND ----------

from mlflow.genai.scorers import RelevanceToQuery, Safety

eval_dataset = [
    {
        "inputs": {"input": [{"role": "user", "content": "What are the top decline reasons and their impact?"}]},
        "expected_response": "The top decline reasons include insufficient funds, do not honor, and fraud suspected, with their respective volumes and recovery potential.",
    },
    {
        "inputs": {"input": [{"role": "user", "content": "Show me the current KPI summary for payment performance."}]},
        "expected_response": "The executive KPI summary shows the total transaction count, approval rate percentage, total transaction value, and average fraud score.",
    },
    {
        "inputs": {"input": [{"role": "user", "content": "Which payment routes have the lowest approval rates?"}]},
        "expected_response": "Route performance analysis shows approval rates by payment solution and card network, identifying underperforming routes that could benefit from optimization.",
    },
]

eval_results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=lambda input: AGENT.predict({
        "input": input,
        "custom_inputs": {"session_id": "evaluation-session"},
    }),
    scorers=[RelevanceToQuery(), Safety()],
)

print("Evaluation complete. Review results in MLflow UI.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pre-deployment validation
# MAGIC
# MAGIC Validates the logged model can be loaded and produce output in an isolated env.

# COMMAND ----------

mlflow.models.predict(
    model_uri=f"runs:/{logged_agent_info.run_id}/agent",
    input_data={
        "input": [{"role": "user", "content": "What is the overall approval rate?"}],
        "custom_inputs": {"session_id": "validation-session"},
    },
    env_manager="uv",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register to Unity Catalog

# COMMAND ----------

mlflow.set_registry_uri("databricks-uc")

UC_MODEL_NAME = f"{CATALOG}.{MODEL_SCHEMA}.payment_analysis_agent"

uc_registered_model_info = mlflow.register_model(
    model_uri=logged_agent_info.model_uri,
    name=UC_MODEL_NAME,
)

print(f"Registered: {UC_MODEL_NAME} (version {uc_registered_model_info.version})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deploy the agent to Model Serving
# MAGIC
# MAGIC Creates a Model Serving endpoint with automatic auth passthrough.

# COMMAND ----------

from databricks import agents

agents.deploy(
    UC_MODEL_NAME,
    uc_registered_model_info.version,
    tags={
        "endpointSource": "payment-analysis",
        "domain": "payment-analytics",
        "agent_type": "responses_agent",
    },
    deploy_feedback_model=False,
)

print(f"Deployed: {UC_MODEL_NAME} v{uc_registered_model_info.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC The Payment Analysis ResponsesAgent has been:
# MAGIC 1. Tested (predict + stream)
# MAGIC 2. Evaluated (RelevanceToQuery + Safety)
# MAGIC 3. Validated (pre-deployment check)
# MAGIC 4. Registered to Unity Catalog
# MAGIC 5. Deployed to Model Serving
# MAGIC
# MAGIC You can now:
# MAGIC - Chat with it in AI Playground
# MAGIC - Share it with SMEs for feedback
# MAGIC - Embed it in the Payment Analysis app
# MAGIC - Monitor traces in MLflow

# COMMAND ----------

try:
    from databricks.sdk.runtime import dbutils
    dbutils.notebook.exit(json.dumps({
        "model_name": UC_MODEL_NAME,
        "model_version": uc_registered_model_info.version,
        "run_id": logged_agent_info.run_id,
    }))
except Exception:
    pass
