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
    """Read catalog, schema, model registry, and tiered LLM endpoints from widgets or env.

    Tiered LLM strategy:
    - ``llm_endpoint_orchestrator``: Strongest reasoning (Claude Opus 4.6) for router + synthesizer
    - ``llm_endpoint_specialist``: Balanced speed/quality (Claude Sonnet 4.5) for individual agents
    - ``llm_endpoint``: Backward-compatible fallback (defaults to specialist tier)
    """
    defaults = {
        "catalog": os.environ.get("CATALOG", "ahs_demos_catalog"),
        "schema": os.environ.get("SCHEMA", "payment_analysis"),
        "model_registry_schema": os.environ.get("MODEL_REGISTRY_SCHEMA", "agents"),
        "llm_endpoint": os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4-5"),
        "llm_endpoint_orchestrator": os.environ.get("LLM_ENDPOINT_ORCHESTRATOR", "databricks-claude-opus-4-6"),
        "llm_endpoint_specialist": os.environ.get("LLM_ENDPOINT_SPECIALIST", "databricks-claude-sonnet-4-5"),
    }
    dbutils = _get_dbutils()
    if not dbutils:
        return defaults
    for key, default in defaults.items():
        dbutils.widgets.text(key, default)
    return {
        key: (dbutils.widgets.get(key) or default).strip()
        for key, default in defaults.items()
    }

# COMMAND ----------

def _agent_script_content(suffix: str, is_orchestrator: bool) -> str:
    """Generate a **self-contained** models-from-code script that wraps the
    LangGraph agent in ``mlflow.pyfunc.ResponsesAgent``.

    The script imports from ``langgraph_agents`` (NOT ``payment_analysis.…``)
    because in Model Serving the ``langgraph_agents.py`` file is delivered via
    ``code_paths`` and lives directly on ``sys.path`` as a top-level module.

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
  LLM_ENDPOINT_ORCHESTRATOR (optional, used by orchestrator for strongest reasoning)
  LLM_ENDPOINT_SPECIALIST   (optional, used by specialist agents for balanced speed/quality)

IMPORTANT: This script imports from ``langgraph_agents`` (a top-level module
delivered via MLflow ``code_paths``), NOT from ``payment_analysis.agents.…``.
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
            # Import from the standalone module (delivered via code_paths).
            # This is NOT payment_analysis.agents.langgraph_agents — the file
            # is placed directly on sys.path by MLflow at model load time.
            from langgraph_agents import {import_name}

            catalog = os.environ.get("CATALOG", "ahs_demos_catalog")
            schema = os.environ.get("SCHEMA", "payment_analysis")
            # Tiered LLM: orchestrator uses strongest model, specialists use balanced model.
            # Falls back to LLM_ENDPOINT for backward compatibility.
            llm_endpoint = os.environ.get(
                "LLM_ENDPOINT{'_ORCHESTRATOR' if is_orchestrator else '_SPECIALIST'}",
                os.environ.get("LLM_ENDPOINT", "{'databricks-claude-opus-4-6' if is_orchestrator else 'databricks-claude-sonnet-4-5'}"),
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
    "databricks-sdk==0.88.0",
    "databricks-langchain==0.15.0",
    "unitycatalog-langchain[databricks]==0.3.0",
    "langgraph==1.0.8",
    "langchain-core==1.2.12",
    "mlflow==3.9.0",
    "pydantic>=2",
]

# ---------------------------------------------------------------------------
# UC tool names used by each specialist agent.
# Used for mlflow.models.resources declarations → automatic auth passthrough
# when served on Databricks Model Serving.
# See: https://docs.databricks.com/en/generative-ai/agent-framework/agent-authentication-model-serving
# ---------------------------------------------------------------------------
SPECIALIST_UC_TOOLS: dict[str, list[str]] = {
    "decline_analyst": [
        "get_decline_trends", "get_decline_by_segment",
        # Lakebase & Vector Search integration
        "get_recent_incidents", "search_similar_transactions",
        "get_active_approval_rules", "get_approval_recommendations",
    ],
    "smart_routing": [
        "get_route_performance", "get_cascade_recommendations",
        # Lakebase & operational context
        "get_recent_incidents", "get_active_approval_rules",
        "get_decision_outcomes", "get_online_features",
    ],
    "smart_retry": [
        "get_retry_success_rates", "get_recovery_opportunities",
        # Lakebase & operational context
        "get_recent_incidents", "get_active_approval_rules",
        "get_decision_outcomes", "search_similar_transactions",
    ],
    "risk_assessor": [
        "get_high_risk_transactions", "get_risk_distribution",
        # Lakebase & operational context
        "get_recent_incidents", "get_online_features",
        "get_active_approval_rules", "search_similar_transactions",
    ],
    "performance_recommender": [
        "get_kpi_summary", "get_optimization_opportunities", "get_trend_analysis",
        # Lakebase & operational context + write-back
        "get_recent_incidents", "get_active_approval_rules",
        "get_decision_outcomes", "get_online_features",
        "get_approval_recommendations",
    ],
}

# Orchestrator uses all specialist tools (it delegates to all of them).
ALL_UC_TOOL_NAMES_SHORT = sorted({
    tool for tools in SPECIALIST_UC_TOOLS.values() for tool in tools
})


def _build_resources(catalog: str, schema: str, llm_endpoint: str, tool_names: list[str]):
    """Build mlflow.models.resources list for a given agent.

    Declares:
    - DatabricksServingEndpoint for the foundation model (LLM)
    - DatabricksFunction for each UC tool used by the agent

    These declarations enable **automatic authentication passthrough** when
    the agent is deployed to Model Serving: the serving container receives
    short-lived credentials scoped to exactly these resources.

    See: https://docs.databricks.com/en/generative-ai/agent-framework/log-agent
    """
    from mlflow.models.resources import (
        DatabricksFunction,
        DatabricksServingEndpoint,
    )

    resources = [
        # Foundation model used by ChatDatabricks inside the LangGraph agent
        DatabricksServingEndpoint(endpoint_name=llm_endpoint),
    ]
    # UC functions used as tools
    for short_name in tool_names:
        full_name = f"{catalog}.{schema}.{short_name}" if "." not in short_name else short_name
        resources.append(DatabricksFunction(function_name=full_name))
    return resources


def register_agents():
    """Log each agent as an MLflow ``ResponsesAgent`` (models-from-code) and
    register to Unity Catalog.

    ``ResponsesAgent`` (MLflow 3.x) is the recommended interface for deploying
    agents on Databricks Model Serving.  It provides:
    - OpenAI Responses API compatible I/O
    - Streaming (``predict_stream``)
    - Tool-call message history
    - Automatic model signature inference

    Resource declarations (``mlflow.models.resources``) are included for each
    agent so that Model Serving can automatically provision short-lived
    credentials scoped to the LLM endpoint and UC functions the agent needs
    (automatic auth passthrough).

    **Alternative for simpler agents**: For basic LangGraph ReAct agents that
    don't need custom streaming, ``mlflow.langchain.log_model(lc_model=path)``
    is slightly simpler. We use ``mlflow.pyfunc.log_model`` with ResponsesAgent
    because it provides full control over streaming and message-format conversion.

    **MCP integration (future)**: When Databricks managed MCP servers are GA,
    consider migrating UC tool-calling to ``databricks-mcp`` for a more
    standardised tool protocol. The current UCFunctionToolkit approach is stable.

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
    llm_orchestrator = config["llm_endpoint_orchestrator"]
    llm_specialist = config["llm_endpoint_specialist"]
    llm_endpoint = config["llm_endpoint"]          # backward-compat fallback
    registered = []

    os.environ["CATALOG"] = catalog
    os.environ["SCHEMA"] = schema
    os.environ["LLM_ENDPOINT"] = llm_endpoint
    os.environ["LLM_ENDPOINT_ORCHESTRATOR"] = llm_orchestrator
    os.environ["LLM_ENDPOINT_SPECIALIST"] = llm_specialist

    print(f"Tiered LLM strategy:")
    print(f"  Orchestrator: {llm_orchestrator}")
    print(f"  Specialist:   {llm_specialist}")
    print(f"  Fallback:     {llm_endpoint}")

    # ---------------------------------------------------------------------------
    # Resolve code_paths: pass ONLY langgraph_agents.py (not the entire src/).
    #
    # Why: The Model Serving container does not pip-install the payment_analysis
    # package. Passing the whole src/ tree via code_paths is fragile and bloated.
    # langgraph_agents.py is self-contained (no payment_analysis imports) and
    # only depends on pip-installable packages listed in SERVING_PIP_REQUIREMENTS.
    #
    # MLflow copies the file to model/code/langgraph_agents.py and adds
    # model/code/ to sys.path. The generated agent script then does:
    #     from langgraph_agents import create_orchestrator_agent
    # ---------------------------------------------------------------------------
    _src_root = _resolve_src_root()
    if not _src_root or not os.path.isdir(_src_root):
        raise RuntimeError("Could not resolve repo src root; required for locating langgraph_agents.py.")

    langgraph_agents_path = os.path.join(
        _src_root, "payment_analysis", "agents", "langgraph_agents.py",
    )
    if not os.path.isfile(langgraph_agents_path):
        raise RuntimeError(
            f"langgraph_agents.py not found at {langgraph_agents_path}. "
            "This file is required as a code_paths dependency for Model Serving."
        )

    print(f"code_paths: {langgraph_agents_path}")

    set_registry_uri("databricks-uc")

    with tempfile.TemporaryDirectory(prefix="agentbricks_mfc_") as tmpdir:
        code_paths = [langgraph_agents_path]

        # 1. Register each specialist (Tool-Calling Agent)
        for create_fn, suffix in get_all_agent_builders():
            model_name = f"{catalog}.{model_schema}.{suffix}"
            script_path = os.path.join(tmpdir, f"agent_{suffix}.py")
            with open(script_path, "w") as f:
                f.write(_agent_script_content(suffix, is_orchestrator=False))

            # Resource declarations for this specialist's LLM (specialist tier) + UC tools
            specialist_tools = SPECIALIST_UC_TOOLS.get(suffix, [])
            resources = _build_resources(catalog, schema, llm_specialist, specialist_tools)

            with mlflow.start_run(run_name=f"register_{suffix}"):
                mlflow.pyfunc.log_model(
                    python_model=script_path,
                    artifact_path="model",
                    code_paths=code_paths,
                    pip_requirements=SERVING_PIP_REQUIREMENTS,
                    resources=resources,
                    registered_model_name=model_name,
                )
            registered.append(model_name)
            print(f"Registered (ResponsesAgent): {model_name}  [{len(resources)} resources]")

        # 2. Register Orchestrator (Multi-Agent System)
        #    The orchestrator delegates to all specialists, so it needs all UC tools.
        script_path = os.path.join(tmpdir, "agent_orchestrator.py")
        with open(script_path, "w") as f:
            f.write(_agent_script_content("orchestrator", is_orchestrator=True))

        # Orchestrator needs both its own LLM (orchestrator tier) AND the specialist LLM
        # because it delegates to specialists that use a different model.
        orchestrator_resources = _build_resources(
            catalog, schema, llm_orchestrator, ALL_UC_TOOL_NAMES_SHORT,
        )
        # Also declare the specialist endpoint so auth passthrough covers both tiers
        if llm_specialist != llm_orchestrator:
            from mlflow.models.resources import DatabricksServingEndpoint
            orchestrator_resources.append(
                DatabricksServingEndpoint(endpoint_name=llm_specialist),
            )

        with mlflow.start_run(run_name="register_orchestrator"):
            model_name = f"{catalog}.{model_schema}.orchestrator"
            mlflow.pyfunc.log_model(
                python_model=script_path,
                artifact_path="model",
                code_paths=code_paths,
                pip_requirements=SERVING_PIP_REQUIREMENTS,
                resources=orchestrator_resources,
                registered_model_name=model_name,
            )
            registered.append(model_name)
            print(f"Registered (ResponsesAgent): {model_name}  [{len(orchestrator_resources)} resources]")

    return registered


# COMMAND ----------

def _ensure_serving_endpoint(
    endpoint_name: str,
    entity_name: str,
    entity_version: str,
    workload_type: str = "CPU",
    workload_size: str = "Small",
    scale_to_zero: bool = True,
    environment_vars: dict | None = None,
):
    """Create or update a Model Serving endpoint (idempotent).

    If the endpoint exists, update it to serve the new model version.
    If it doesn't exist, create it from scratch.
    """
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import (
        EndpointCoreConfigInput,
        ServedEntityInput,
        TrafficConfig,
        Route,
    )

    w = WorkspaceClient()
    served_entity = ServedEntityInput(
        entity_name=entity_name,
        entity_version=str(entity_version),
        workload_size=workload_size,
        scale_to_zero_enabled=scale_to_zero,
        workload_type=workload_type,
        environment_vars=environment_vars or {},
    )

    model_short = entity_name.split(".")[-1]
    served_model_name = f"{model_short}-{entity_version}"
    traffic = TrafficConfig(
        routes=[Route(served_model_name=served_model_name, traffic_percentage=100)]
    )

    try:
        existing = w.serving_endpoints.get(endpoint_name)
        print(f"  Endpoint '{endpoint_name}' exists (ready={existing.state.ready}), "
              f"updating to {entity_name} v{entity_version}...")
        w.serving_endpoints.update_config(
            name=endpoint_name,
            served_entities=[served_entity],
            traffic_config=traffic,
        )
        print(f"  ✓ Update initiated for '{endpoint_name}'")
    except Exception as get_err:
        err_str = str(get_err)
        if "RESOURCE_DOES_NOT_EXIST" in err_str or "does not exist" in err_str.lower():
            print(f"  Endpoint '{endpoint_name}' not found, creating with "
                  f"{entity_name} v{entity_version}...")
            w.serving_endpoints.create(
                name=endpoint_name,
                config=EndpointCoreConfigInput(
                    served_entities=[served_entity],
                    traffic_config=traffic,
                ),
            )
            print(f"  ✓ Create initiated for '{endpoint_name}'")
        else:
            raise


def deploy_agent_endpoints(registered: list[str]):
    """Deploy or update Model Serving endpoints for registered agents.

    Maps registered UC model names to their serving endpoint names and
    creates/updates each endpoint idempotently. This removes the need
    for hardcoded entity_version values in model_serving.yml.
    """
    import mlflow

    config = _get_config()
    catalog = config["catalog"]
    schema = config["schema"]
    llm_orchestrator = config["llm_endpoint_orchestrator"]
    llm_specialist = config["llm_endpoint_specialist"]

    # Map UC model name suffix → (endpoint_name, env_vars)
    AGENT_ENDPOINTS: dict[str, tuple[str, dict[str, str]]] = {
        "orchestrator": (
            "payment-analysis-orchestrator",
            {
                "ENABLE_MLFLOW_TRACING": "true",
                "CATALOG": catalog,
                "SCHEMA": schema,
                "LLM_ENDPOINT": llm_orchestrator,
                "LLM_ENDPOINT_ORCHESTRATOR": llm_orchestrator,
                "LLM_ENDPOINT_SPECIALIST": llm_specialist,
            },
        ),
        "decline_analyst": (
            "decline-analyst",
            {
                "ENABLE_MLFLOW_TRACING": "true",
                "CATALOG": catalog,
                "SCHEMA": schema,
                "LLM_ENDPOINT": llm_specialist,
            },
        ),
    }

    client = mlflow.MlflowClient()
    errors: list[str] = []

    for model_name in registered:
        suffix = model_name.split(".")[-1]  # e.g. "orchestrator", "decline_analyst"
        if suffix not in AGENT_ENDPOINTS:
            continue  # skip specialist models not mapped to endpoints

        ep_name, env_vars = AGENT_ENDPOINTS[suffix]
        try:
            # Get latest version for this model
            versions = client.search_model_versions(
                f"name='{model_name}'", order_by=["version_number DESC"], max_results=1,
            )
            if not versions:
                print(f"  ⚠ No versions for {model_name}, skipping endpoint '{ep_name}'")
                continue
            latest_version = versions[0].version
            print(f"\n{ep_name}: {model_name} v{latest_version}")
            _ensure_serving_endpoint(
                endpoint_name=ep_name,
                entity_name=model_name,
                entity_version=latest_version,
                environment_vars=env_vars,
            )
        except Exception as e:
            print(f"  ✗ Endpoint '{ep_name}' FAILED: {e}")
            errors.append(f"{ep_name}: {e}")

    if errors:
        print(f"\n⚠ {len(errors)} agent endpoint(s) failed:")
        for err in errors:
            print(f"  ✗ {err}")
    else:
        print("\n✓ All agent serving endpoints deployed/updated")


# COMMAND ----------

if __name__ == "__main__":
    registered = register_agents()
    print("\n" + "=" * 60)
    print("AgentBricks registration complete")
    print("=" * 60)
    for name in registered:
        print(f"  - {name}")

    # Deploy/update serving endpoints for orchestrator and decline_analyst
    print("\n" + "=" * 60)
    print("Deploying agent serving endpoints")
    print("=" * 60)
    try:
        deploy_agent_endpoints(registered)
    except Exception as ep_err:
        print(f"⚠ Endpoint deployment failed (non-fatal): {ep_err}")

    dbutils = _get_dbutils()
    if dbutils:
        dbutils.notebook.exit(json.dumps({"registered_models": registered}))
