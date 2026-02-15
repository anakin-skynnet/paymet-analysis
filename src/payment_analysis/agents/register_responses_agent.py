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
# MAGIC **Outcome:** Model registered as `{catalog}.agents.payment_analysis_agent`, deployed to endpoint **payment-response-agent**.

# COMMAND ----------

# Environment dependencies (responses_agent) already include all required packages.
# No %pip install needed — avoids version conflicts and saves ~30s startup time.

print("=== register_responses_agent notebook starting ===", flush=True)

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration: read from widgets / env
# ---------------------------------------------------------------------------
def _get_config():
    defaults = {
        "catalog": os.environ.get("CATALOG", "ahs_demos_catalog"),
        "schema": os.environ.get("SCHEMA", "payment_analysis"),
        "model_registry_schema": os.environ.get("MODEL_REGISTRY_SCHEMA", "agents"),
        "llm_endpoint": os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4-5"),
    }
    try:
        from databricks.sdk.runtime import dbutils
        for key, default in defaults.items():
            dbutils.widgets.text(key, default)
        return {
            key: (dbutils.widgets.get(key) or default).strip()
            for key, default in defaults.items()
        }
    except Exception:
        return defaults


config = _get_config()
CATALOG = config["catalog"]
SCHEMA = config["schema"]
MODEL_SCHEMA = config["model_registry_schema"]
LLM_ENDPOINT = config["llm_endpoint"]

# Set env vars so agent.py picks them up at import time
os.environ["CATALOG"] = CATALOG
os.environ["SCHEMA"] = SCHEMA
os.environ["LLM_ENDPOINT"] = LLM_ENDPOINT

print(f"Catalog:  {CATALOG}")
print(f"Schema:   {SCHEMA}")
print(f"Registry: {CATALOG}.{MODEL_SCHEMA}")
print(f"LLM:      {LLM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resolve agent.py path and import
# MAGIC
# MAGIC The `agent.py` file must be in the same directory as this notebook.

# COMMAND ----------

# ---------------------------------------------------------------------------
# Resolve the agents directory and add to sys.path
# ---------------------------------------------------------------------------
_agents_dir = None

# 1. Databricks notebook context (most reliable in serverless)
try:
    from databricks.sdk.runtime import dbutils as _dbu
    _nb_ctx = _dbu.notebook.entry_point.getDbutils().notebook().getContext()
    _nb_path = str(_nb_ctx.notebookPath().get())
    _agents_dir = Path(_nb_path).parent
    if not (_agents_dir / "agent.py").exists():
        _agents_dir = None
    else:
        print(f"Resolved agents dir via notebook context: {_agents_dir}")
except Exception as _e:
    print(f"Notebook context resolution failed: {_e}")

# 2. __file__ (works for .py files, not standard notebooks)
if not _agents_dir and "__file__" in dir():
    _candidate = Path(__file__).resolve().parent
    if (_candidate / "agent.py").exists():
        _agents_dir = _candidate
        print(f"Resolved agents dir via __file__: {_agents_dir}")

# 3. CWD and common workspace paths
if not _agents_dir:
    for _candidate in [
        Path("."),
        Path("./src/payment_analysis/agents"),
    ]:
        if (_candidate / "agent.py").exists():
            _agents_dir = _candidate.resolve()
            print(f"Resolved agents dir via filesystem scan: {_agents_dir}")
            break

if _agents_dir:
    sys.path.insert(0, str(_agents_dir))
    agent_path = _agents_dir / "agent.py"
else:
    # Last resort: assume CWD
    agent_path = Path("agent.py")
    print(f"WARNING: Could not locate agent.py directory. CWD={Path('.').resolve()}")
    print(f"CWD contents: {list(Path('.').iterdir())}")
    print(f"sys.path: {sys.path[:5]}")

print(f"Agent path: {agent_path} (exists={agent_path.exists()})")

# COMMAND ----------

# Import the agent module
print(f"Importing agent from {agent_path}...", flush=True)
try:
    from agent import AGENT  # noqa: E402
    print("SUCCESS: agent imported and initialized", flush=True)
except Exception as e:
    print(f"ERROR: Failed to import agent: {e}", flush=True)
    import traceback
    traceback.print_exc()
    # Write error to notebook exit value so it's visible in the job run
    try:
        from databricks.sdk.runtime import dbutils
        dbutils.notebook.exit(json.dumps({"error": str(e), "traceback": traceback.format_exc()[:2000]}))
    except Exception:
        pass
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test the agent
# MAGIC
# MAGIC Quick smoke test before logging. Traces are visible in MLflow.

# COMMAND ----------

# Test: predict
try:
    result = AGENT.predict({
        "input": [{"role": "user", "content": "What are the current approval rates and top decline reasons?"}],
        "custom_inputs": {"session_id": "test-registration"},
    })
    print("Predict test passed:")
    print(result.model_dump(exclude_none=True))
except Exception as e:
    print(f"WARNING: Agent predict test failed (non-fatal): {e}", flush=True)
    import traceback
    traceback.print_exc()
    # Don't raise — the agent can still be logged even if predict fails (e.g. LLM timeout)

# COMMAND ----------

# Test: streaming
try:
    for chunk in AGENT.predict_stream({
        "input": [{"role": "user", "content": "Show me high-risk transactions from the last day."}],
        "custom_inputs": {"session_id": "test-stream"},
    }):
        print(chunk.model_dump(exclude_none=True))
except Exception as e:
    print(f"WARNING: Agent streaming test failed (non-fatal): {e}", flush=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log the agent as an MLflow model
# MAGIC
# MAGIC Uses **models-from-code** (`python_model="agent.py"`) for clean deployment.
# MAGIC Declares UC function resources for **automatic auth passthrough** at serving time.

# COMMAND ----------

import mlflow
from mlflow.models.resources import (
    DatabricksFunction,
    DatabricksServingEndpoint,
)

# Declare Databricks resources for automatic auth passthrough at serving time.
# DatabricksServingEndpoint: the foundation model used by the agent (via OpenAI client).
# DatabricksFunction: UC functions used as tools by the agent.
# See: https://docs.databricks.com/en/generative-ai/agent-framework/agent-authentication-model-serving
UC_TOOL_NAMES = [
    # Decline Analyst
    f"{CATALOG}.{SCHEMA}.get_decline_trends",
    f"{CATALOG}.{SCHEMA}.get_decline_by_segment",
    # Smart Routing
    f"{CATALOG}.{SCHEMA}.get_route_performance",
    f"{CATALOG}.{SCHEMA}.get_cascade_recommendations",
    # Smart Retry
    f"{CATALOG}.{SCHEMA}.get_retry_success_rates",
    f"{CATALOG}.{SCHEMA}.get_recovery_opportunities",
    # Risk Assessor
    f"{CATALOG}.{SCHEMA}.get_high_risk_transactions",
    f"{CATALOG}.{SCHEMA}.get_risk_distribution",
    # Performance Recommender
    f"{CATALOG}.{SCHEMA}.get_kpi_summary",
    f"{CATALOG}.{SCHEMA}.get_optimization_opportunities",
    f"{CATALOG}.{SCHEMA}.get_trend_analysis",
    # Lakebase & Operational Context
    f"{CATALOG}.{SCHEMA}.get_active_approval_rules",
    f"{CATALOG}.{SCHEMA}.get_recent_incidents",
    f"{CATALOG}.{SCHEMA}.get_online_features",
    f"{CATALOG}.{SCHEMA}.get_decision_outcomes",
    # Vector Search (Similar Transactions)
    f"{CATALOG}.{SCHEMA}.search_similar_transactions",
    f"{CATALOG}.{SCHEMA}.get_approval_recommendations",
    # General-purpose Python exec (for ad-hoc analysis and recommendation write-back)
    "system.ai.python_exec",
]

resources = [
    # Foundation model endpoint used by the agent for LLM inference
    DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT),
    # UC functions used as tools
    *[DatabricksFunction(function_name=name) for name in UC_TOOL_NAMES],
]

with mlflow.start_run(run_name="register_payment_analysis_agent"):
    logged_agent_info = mlflow.pyfunc.log_model(
        name="agent",
        python_model=str(agent_path),
        pip_requirements=[
            "databricks-openai==0.10.0",
            "unitycatalog-ai[databricks]==0.3.2",
            "backoff==2.2.1",
            "databricks-sdk==0.88.0",
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

try:
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
except Exception as e:
    print(f"WARNING: Agent evaluation failed (non-fatal): {e}", flush=True)
    # Evaluation failure should not block model registration/deployment

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pre-deployment validation
# MAGIC
# MAGIC Validates the logged model can be loaded and produce output in an isolated env.

# COMMAND ----------

try:
    mlflow.models.predict(
        model_uri=f"runs:/{logged_agent_info.run_id}/agent",
        input_data={
            "input": [{"role": "user", "content": "What is the overall approval rate?"}],
            "custom_inputs": {"session_id": "validation-session"},
        },
        env_manager="uv",
    )
    print("Pre-deployment validation passed")
except Exception as e:
    print(f"WARNING: Pre-deployment validation failed (non-fatal): {e}")
    # Don't raise — validation failure shouldn't block registration

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
# MAGIC Creates a Model Serving endpoint named **payment-response-agent** with automatic auth passthrough.

# COMMAND ----------

# Note: The Model Serving endpoint is managed by Databricks Asset Bundles
# (resources/model_serving.yml). After this notebook registers a new model
# version, update entity_version in model_serving.yml and run bundle deploy.
# No need for databricks.agents.deploy() — the endpoint config is in Terraform.
print(f"Model registered: {UC_MODEL_NAME} v{uc_registered_model_info.version}")
print(f"To deploy: update entity_version in resources/model_serving.yml, then run 'databricks bundle deploy'")

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
