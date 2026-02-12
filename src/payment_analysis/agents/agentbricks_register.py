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
    """Generate model-from-code script content. LangChain v1+ requires lc_model to be a path to script with set_model()."""
    import_name = "create_orchestrator_agent" if is_orchestrator else f"create_{suffix}_agent"
    return f'''"""
MLflow model-from-code script for {suffix}. Built at registration time; uses env CATALOG, SCHEMA, LLM_ENDPOINT.
See https://mlflow.org/docs/latest/model/models-from-code.html
"""
import os
from mlflow.models import set_model
from payment_analysis.agents.langgraph_agents import {import_name}

def _build():
    catalog = os.environ.get("CATALOG", "ahs_demos_catalog")
    schema = os.environ.get("SCHEMA", "payment_analysis")
    llm_endpoint = os.environ.get("LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")
    return {import_name}(catalog, schema=schema, llm_endpoint=llm_endpoint)

set_model(_build())
'''


def _make_agent_signature():
    """Build ModelSignature for LangChain/LangGraph chat agents. UC requires both input and output specs."""
    from mlflow.models.signature import ModelSignature, infer_signature

    # UC requires explicit input and output types. Try infer from dict; else use explicit Schema.
    input_example = {"messages": [{"type": "human", "content": "What are the top decline reasons?"}]}
    output_example = {"messages": [{"type": "ai", "content": "Summary of decline reasons and recommendations."}]}
    try:
        sig = infer_signature(input_example, output_example)
        if sig.inputs is not None and sig.outputs is not None:
            return sig
    except Exception:
        pass
    # Fallback: explicit schema (Unity Catalog accepts string columns for chat payloads)
    from mlflow.types.schema import ColSpec, Schema

    inputs = Schema([ColSpec("string", "messages")])
    outputs = Schema([ColSpec("string", "messages")])
    return ModelSignature(inputs=inputs, outputs=outputs)


def register_agents():
    """Log each agent to MLflow (models-from-code) and register to UC. Returns list of registered model names."""
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

    # LangChain v1+ only supports models-from-code: lc_model must be a path to a script that calls set_model().
    os.environ["CATALOG"] = catalog
    os.environ["SCHEMA"] = schema
    os.environ["LLM_ENDPOINT"] = llm_endpoint

    _src_root = _resolve_src_root()
    if not _src_root or not os.path.isdir(_src_root):
        raise RuntimeError("Could not resolve repo src root for code_paths; required for models-from-code.")

    set_registry_uri("databricks-uc")

    # Unity Catalog requires an explicit model signature (input + output). Infer from examples.
    input_example = {"messages": [{"type": "human", "content": "What are the top decline reasons?"}]}
    signature = _make_agent_signature()

    with tempfile.TemporaryDirectory(prefix="agentbricks_mfc_") as tmpdir:
        code_paths = [_src_root]

        # 1. Register each specialist (Tool-Calling Agent)
        for create_fn, suffix in get_all_agent_builders():
            model_name = f"{catalog}.{model_schema}.{suffix}"
            script_path = os.path.join(tmpdir, f"agent_{suffix}.py")
            with open(script_path, "w") as f:
                f.write(_agent_script_content(suffix, is_orchestrator=False))
            with mlflow.start_run(run_name=f"register_{suffix}"):
                mlflow.langchain.log_model(
                    lc_model=script_path,
                    artifact_path="model",
                    registered_model_name=model_name,
                    code_paths=code_paths,
                    signature=signature,
                    input_example=input_example,
                )
            registered.append(model_name)
            print(f"Registered: {model_name}")

        # 2. Register Orchestrator (Multi-Agent System)
        script_path = os.path.join(tmpdir, "agent_orchestrator.py")
        with open(script_path, "w") as f:
            f.write(_agent_script_content("orchestrator", is_orchestrator=True))
        with mlflow.start_run(run_name="register_orchestrator"):
            model_name = f"{catalog}.{model_schema}.orchestrator"
            mlflow.langchain.log_model(
                lc_model=script_path,
                artifact_path="model",
                registered_model_name=model_name,
                code_paths=code_paths,
                signature=signature,
                input_example=input_example,
            )
            registered.append(model_name)
            print(f"Registered: {model_name}")

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
