# Databricks notebook source
# MAGIC %md
# MAGIC # Register AgentBricks Agents to Unity Catalog (MLflow)
# MAGIC
# MAGIC Logs each specialist (Tool-Calling Agent) and the Orchestrator (Multi-Agent System)
# MAGIC to MLflow and registers them in Unity Catalog under `{catalog}.agents.*`.
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - UC agent tool functions exist (Job 3: create_uc_agent_tools)
# MAGIC - Schema `agents` exists in the catalog (e.g. `ahs_demos_catalog.agents`)
# MAGIC
# MAGIC **Outcome:** Models registered as `{catalog}.agents.decline_analyst`, `smart_routing`, `smart_retry`, `risk_assessor`, `performance_recommender`, `orchestrator`. You can then deploy them to Model Serving or add to the workspace Agents (AgentBricks) UI.

# COMMAND ----------

import os
import sys
import json

# Ensure payment_analysis package is importable when run as a Databricks job (no pip install of the repo).
# Repo root is either from __file__ (e.g. .../files/src/payment_analysis/agents/... -> .../files/src)
# or from workspace_path widget / WORKSPACE_ROOT env (bundle workspace path).
def _get_dbutils():
    """Return dbutils from Databricks runtime, or None when not in a notebook."""
    try:
        from databricks.sdk.runtime import dbutils
        return dbutils
    except (ImportError, AttributeError):
        return None


def _resolve_src_root():
    """Resolve path to repo src/ (for sys.path). Prefer __file__, then widget, then env."""
    root = None
    if "__file__" in globals():
        agentbricks_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(agentbricks_dir) == "agents":
            root = os.path.abspath(os.path.join(agentbricks_dir, "..", ".."))
    if not root or not os.path.isdir(root):
        dbutils = _get_dbutils()
        workspace_path = (dbutils.widgets.get("workspace_path") or "").strip() if dbutils else ""
        if not workspace_path:
            workspace_path = os.environ.get("WORKSPACE_ROOT", "").strip()
        if workspace_path:
            root = os.path.join(workspace_path, "src")
    return root if root and os.path.isdir(root) else None


_src_root = _resolve_src_root()
if _src_root and _src_root not in sys.path:
    sys.path.insert(0, _src_root)

# COMMAND ----------

def _get_config():
    """Read catalog, schema, and model registry from widgets or env."""
    defaults = {
        "catalog": os.environ.get("CATALOG", "ahs_demos_catalog"),
        "schema": os.environ.get("SCHEMA", "payment_analysis"),
        "model_registry_schema": os.environ.get("MODEL_REGISTRY_SCHEMA", "agents"),
        "llm_endpoint": os.environ.get("LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct"),
    }
    dbutils = _get_dbutils()
    if not dbutils:
        return defaults
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

# COMMAND ----------

def _agent_script_content(suffix: str, is_orchestrator: bool) -> str:
    """Generate a models-from-code script that wraps the LangGraph agent in
    ``mlflow.pyfunc.ResponsesAgent`` — the MLflow 3.x recommended interface for
    deploying agents to Databricks Model Serving.

    Key design decisions:
    1. **ResponsesAgent** (not ChatModel / PythonModel / langchain flavor).
       Provides OpenAI Responses-API-compatible I/O, streaming, tool-call
       messages, and automatic signature inference.
    2. **Lazy LangGraph initialization** in ``_ensure_agent()`` so the serving
       container can reach READY before the first Databricks / UC connection.
    3. **``output_to_responses_items_stream``** converts LangChain messages
       returned by LangGraph into the Responses-API event stream.

    References:
    - https://mlflow.org/docs/latest/genai/flavors/responses-agent-intro/
    - https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/author-agent
    """
    import_name = "create_orchestrator_agent" if is_orchestrator else f"create_{suffix}_agent"
    return f'''"""
MLflow ResponsesAgent wrapper for the **{suffix}** LangGraph agent.

Uses ``mlflow.pyfunc.ResponsesAgent`` (MLflow 3.x) for Databricks Model Serving
with OpenAI Responses API compatibility, streaming, and tool-call support.
The LangGraph agent is built lazily on the first ``predict()`` call.

Env vars (set via Model Serving environment_vars):
  CATALOG, SCHEMA, LLM_ENDPOINT
"""
import os
import sys
import traceback
from typing import Generator

import mlflow
from mlflow.entities import SpanType
from mlflow.models import set_model
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)


class _LangGraphResponsesAgent(ResponsesAgent):
    """ResponsesAgent that wraps a LangGraph compiled graph with lazy init."""

    def __init__(self):
        self._agent = None
        self._init_error = None

    def _ensure_agent(self):
        if self._agent is not None:
            return
        if self._init_error is not None:
            raise RuntimeError(self._init_error)
        try:
            from payment_analysis.agents.langgraph_agents import {import_name}

            catalog = os.environ.get("CATALOG", "ahs_demos_catalog")
            schema = os.environ.get("SCHEMA", "payment_analysis")
            llm_endpoint = os.environ.get(
                "LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct"
            )
            self._agent = {import_name}(
                catalog, schema=schema, llm_endpoint=llm_endpoint
            )
        except Exception as exc:
            self._init_error = f"{{type(exc).__name__}}: {{exc}}"
            traceback.print_exc(file=sys.stderr)
            raise

    @mlflow.trace(span_type=SpanType.AGENT)
    def predict(
        self, request: ResponsesAgentRequest
    ) -> ResponsesAgentResponse:
        """Collect all stream events into a single ResponsesAgentResponse."""
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(
            output=outputs, custom_outputs=request.custom_inputs
        )

    @mlflow.trace(span_type=SpanType.AGENT)
    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Invoke the LangGraph agent and yield Responses-API stream events."""
        self._ensure_agent()

        # Convert Responses-API input to ChatCompletion messages (what LangGraph expects)
        cc_msgs = to_chat_completions_input(
            [i.model_dump() for i in request.input]
        )

        # Invoke the compiled graph
        result = self._agent.invoke({{"messages": cc_msgs}})

        # Convert LangChain messages back to Responses-API stream events
        yield from output_to_responses_items_stream(
            result.get("messages", [])
        )


mlflow.langchain.autolog()
agent = _LangGraphResponsesAgent()
set_model(agent)
'''


# ---------------------------------------------------------------------------
# Pinned pip requirements for Model Serving.
# Must match Job 6 environment (resources/agents.yml).  Without explicit
# requirements the serving container may get incomplete / conflicting deps.
# ---------------------------------------------------------------------------
SERVING_PIP_REQUIREMENTS = [
    "databricks-sdk==0.86.0",
    "databricks-langchain==0.15.0",
    "unitycatalog-langchain[databricks]==0.3.0",
    "langgraph==1.0.8",
    "langchain-core==1.2.11",
    "mlflow==3.9.0",
    "pydantic>=2",
]


def register_agents():
    """Log each agent as an MLflow ``ResponsesAgent`` (models-from-code) and
    register to Unity Catalog.

    ``ResponsesAgent`` (MLflow 3.x) is the recommended interface for deploying
    agents on Databricks Model Serving.  It provides:
    - OpenAI Responses API compatible I/O
    - Streaming (``predict_stream``)
    - Tool-call message history
    - Automatic model signature inference

    See: https://mlflow.org/docs/latest/genai/flavors/responses-agent-intro/

    Returns list of registered model names.
    """
    import tempfile
    import mlflow
    from mlflow import set_registry_uri

    from payment_analysis.agents.langgraph_agents import get_all_agent_builders

    config = _get_config()
    catalog = config["catalog"]
    schema = config["schema"]
    model_schema = config["model_registry_schema"]
    llm_endpoint = config["llm_endpoint"]
    registered = []

    os.environ["CATALOG"] = catalog
    os.environ["SCHEMA"] = schema
    os.environ["LLM_ENDPOINT"] = llm_endpoint

    _src_root = _resolve_src_root()
    if not _src_root or not os.path.isdir(_src_root):
        raise RuntimeError("Could not resolve repo src root for code_paths; required for models-from-code.")

    set_registry_uri("databricks-uc")

    with tempfile.TemporaryDirectory(prefix="agentbricks_mfc_") as tmpdir:
        code_paths = [_src_root]

        # ResponsesAgent auto-infers signature and input_example;
        # we only pass pip_requirements and code_paths.
        log_kwargs = dict(
            artifact_path="model",
            code_paths=code_paths,
            pip_requirements=SERVING_PIP_REQUIREMENTS,
        )

        # 1. Register each specialist (Tool-Calling Agent)
        for create_fn, suffix in get_all_agent_builders():
            model_name = f"{catalog}.{model_schema}.{suffix}"
            script_path = os.path.join(tmpdir, f"agent_{suffix}.py")
            with open(script_path, "w") as f:
                f.write(_agent_script_content(suffix, is_orchestrator=False))
            with mlflow.start_run(run_name=f"register_{suffix}"):
                mlflow.pyfunc.log_model(
                    python_model=script_path,
                    registered_model_name=model_name,
                    **log_kwargs,
                )
            registered.append(model_name)
            print(f"Registered (ResponsesAgent): {model_name}")

        # 2. Register Orchestrator (Multi-Agent System)
        script_path = os.path.join(tmpdir, "agent_orchestrator.py")
        with open(script_path, "w") as f:
            f.write(_agent_script_content("orchestrator", is_orchestrator=True))
        with mlflow.start_run(run_name="register_orchestrator"):
            model_name = f"{catalog}.{model_schema}.orchestrator"
            mlflow.pyfunc.log_model(
                python_model=script_path,
                registered_model_name=model_name,
                **log_kwargs,
            )
            registered.append(model_name)
            print(f"Registered (ResponsesAgent): {model_name}")

    return registered


# COMMAND ----------

if __name__ == "__main__":
    registered = register_agents()
    print("\n" + "=" * 60)
    print("AgentBricks registration complete")
    print("=" * 60)
    for name in registered:
        print(f"  - {name}")
    dbutils = _get_dbutils()
    if dbutils:
        dbutils.notebook.exit(json.dumps({"registered_models": registered}))
