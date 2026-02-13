"""
Databricks AI Agents Registry - Payment Approval Optimization.

This module provides AI agents powered by Databricks features:
- Genie: Natural language SQL analytics
- Model Serving: ML-powered recommendations
- Mosaic AI Gateway: LLM routing and prompt engineering (https://learn.microsoft.com/en-us/azure/databricks/ai-gateway/)
- Custom Agents: Domain-specific payment intelligence

NOTE: Workspace URLs are constructed dynamically based on environment variables.
"""

from __future__ import annotations

import asyncio
import json
import os
from enum import Enum
from typing import Any

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..config import AppConfig, get_default_schema
from ..dependencies import get_workspace_client, get_workspace_client_optional
from ..logger import logger
from .setup import resolve_orchestrator_job_id

# Optional Genie space for /chat fallback: when set, POST /chat uses Databricks Genie Conversation API.
GENIE_SPACE_ID_ENV = "GENIE_SPACE_ID"
# When set, POST /api/agents/orchestrator/chat calls this Model Serving endpoint (AgentBricks/Supervisor) instead of Job 6.
ORCHESTRATOR_SERVING_ENDPOINT_ENV = "ORCHESTRATOR_SERVING_ENDPOINT"

# Job 6 poll settings (orchestrator chat fallback)
ORCHESTRATOR_JOB_POLL_TIMEOUT_S = 120
ORCHESTRATOR_JOB_POLL_INTERVAL_S = 4

router = APIRouter(tags=["agents"])

_databricks_config = AppConfig().databricks

# Default catalog.schema used in AGENTS; replaced with effective config when returning.
def _default_uc_prefix() -> str:
    catalog = os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog")
    return f"{catalog}.{get_default_schema()}"


# =============================================================================
# Helper Functions
# =============================================================================

def get_workspace_url() -> str:
    """Get Databricks workspace URL from centralized config."""
    return _databricks_config.workspace_url


def get_notebook_workspace_url(relative_path: str) -> str:
    """Construct full workspace URL for a notebook (path must match bundle sync: workspace.root_path)."""
    workspace_url = get_workspace_url()
    user_email = os.getenv("DATABRICKS_USER", "user@company.com")
    folder_name = os.getenv("BUNDLE_FOLDER", "payment-analysis")
    full_path = f"/Workspace/Users/{user_email}/{folder_name}/{relative_path}"
    return f"{workspace_url}/workspace{full_path}"


# =============================================================================
# Models
# =============================================================================

class AgentType(str, Enum):
    """AI Agent types available in Databricks."""
    GENIE = "genie"
    MODEL_SERVING = "model_serving"
    CUSTOM_LLM = "custom_llm"
    AI_GATEWAY = "ai_gateway"


class AgentCapability(str, Enum):
    """Agent capabilities."""
    NATURAL_LANGUAGE_ANALYTICS = "natural_language_analytics"
    PREDICTIVE_SCORING = "predictive_scoring"
    CONVERSATIONAL_INSIGHTS = "conversational_insights"
    AUTOMATED_RECOMMENDATIONS = "automated_recommendations"
    REAL_TIME_DECISIONING = "real_time_decisioning"


class AgentInfo(BaseModel):
    """AI Agent metadata model."""
    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent display name")
    description: str = Field(..., description="Agent purpose and capabilities")
    agent_type: AgentType = Field(..., description="Databricks AI technology")
    capabilities: list[AgentCapability] = Field(..., description="Agent capabilities")
    use_case: str = Field(..., description="Payment approval use case")
    databricks_resource: str = Field(..., description="Databricks resource path/endpoint")
    workspace_url: str | None = Field(None, description="Direct Databricks workspace URL")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    example_queries: list[str] = Field(default_factory=list, description="Example questions/prompts")


class AgentList(BaseModel):
    """List of AI agents."""
    agents: list[AgentInfo]
    total: int
    by_type: dict[str, int]


# =============================================================================
# AI Agents Registry
# =============================================================================

AGENTS = [
    # Genie - Natural Language Analytics
    AgentInfo(
        id="approval_optimizer_genie",
        name="Approval Optimizer (Genie)",
        description="Natural language analytics for approval rate optimization. Ask questions about approval patterns, merchant performance, and identify opportunities to increase approval rates.",
        agent_type=AgentType.GENIE,
        capabilities=[
            AgentCapability.NATURAL_LANGUAGE_ANALYTICS,
            AgentCapability.CONVERSATIONAL_INSIGHTS,
        ],
        use_case="Query payment data using natural language to discover approval optimization opportunities. Example: 'Which merchants have declining approval rates?' or 'Show me high-value transactions that are getting declined'",
        databricks_resource="Genie Space: Payment Approval Analytics",
        workspace_url=f"{get_workspace_url()}/genie",
        tags=["genie", "analytics", "approval-optimization", "natural-language"],
        example_queries=[
            "Which payment solutions have the highest approval rates?",
            "Show me decline trends by card network over the last 30 days",
            "What's the average approval rate for cross-border transactions?",
            "Which merchants should we prioritize for 3DS adoption?",
            "What's the revenue impact of improving approval rates by 1%?",
        ],
    ),
    
    AgentInfo(
        id="decline_insights_genie",
        name="Decline Insights (Genie)",
        description="Conversational analytics focused on understanding and reducing payment declines. Explore decline reasons, recovery opportunities, and retry strategies through natural language.",
        agent_type=AgentType.GENIE,
        capabilities=[
            AgentCapability.NATURAL_LANGUAGE_ANALYTICS,
            AgentCapability.CONVERSATIONAL_INSIGHTS,
        ],
        use_case="Deep-dive into decline patterns to identify recoverable transactions and optimal retry strategies. Ask about specific decline codes, merchant segments, or geographic patterns.",
        databricks_resource="Genie Space: Decline Analysis",
        workspace_url=f"{get_workspace_url()}/genie",
        tags=["genie", "declines", "recovery", "analytics"],
        example_queries=[
            "What are the top 5 decline reasons this month?",
            "How many declined transactions could be recovered with smart retry?",
            "Show me decline rates by issuer country",
            "Which decline codes have the highest retry success rates?",
            "What's the average time to successful retry for insufficient funds declines?",
        ],
    ),
    
    # Model Serving - Predictive Intelligence
    AgentInfo(
        id="approval_propensity_predictor",
        name="Approval Propensity Predictor",
        description="ML model serving endpoint that predicts transaction approval likelihood in real-time. Uses Random Forest trained on 30+ features including fraud scores, device trust, and payment history.",
        agent_type=AgentType.MODEL_SERVING,
        capabilities=[
            AgentCapability.PREDICTIVE_SCORING,
            AgentCapability.REAL_TIME_DECISIONING,
        ],
        use_case="Real-time approval probability scoring for intelligent routing decisions. Route high-propensity transactions to optimal payment solutions and flag low-propensity transactions for review.",
        databricks_resource=f"Model: {_default_uc_prefix()}.approval_propensity_model",
        workspace_url=f"{get_workspace_url()}/ml/models/{_default_uc_prefix()}.approval_propensity_model",
        tags=["model-serving", "ml", "propensity", "real-time"],
        example_queries=[
            "What's the approval probability for this transaction?",
            "Should we route this payment to 3DS or standard?",
            "Predict approval rates for upcoming batch",
        ],
    ),
    
    AgentInfo(
        id="smart_routing_advisor",
        name="Smart Routing Advisor",
        description="ML-powered agent that recommends optimal payment routing strategies based on merchant segment, transaction characteristics, and historical performance data.",
        agent_type=AgentType.MODEL_SERVING,
        capabilities=[
            AgentCapability.PREDICTIVE_SCORING,
            AgentCapability.AUTOMATED_RECOMMENDATIONS,
            AgentCapability.REAL_TIME_DECISIONING,
        ],
        use_case="Automatically select the best payment solution (standard, 3DS, network token, passkey) to maximize approval rates while balancing fraud risk and processing costs.",
        databricks_resource=f"Model: {_default_uc_prefix()}.smart_routing_policy",
        workspace_url=f"{get_workspace_url()}/ml/models/{_default_uc_prefix()}.smart_routing_policy",
        tags=["model-serving", "routing", "optimization", "decisioning"],
        example_queries=[
            "What's the best payment solution for this merchant?",
            "Should we enable network tokenization for travel merchants?",
            "Recommend routing strategy for high-value transactions",
        ],
    ),
    
    AgentInfo(
        id="smart_retry_optimizer",
        name="Smart Retry Optimizer",
        description="ML agent that identifies declined transactions with high recovery potential and recommends optimal retry timing and strategy based on decline reason and transaction context.",
        agent_type=AgentType.MODEL_SERVING,
        capabilities=[
            AgentCapability.PREDICTIVE_SCORING,
            AgentCapability.AUTOMATED_RECOMMENDATIONS,
        ],
        use_case="Increase revenue recovery by 15-25% through intelligent retry strategies. Predicts retry success probability and suggests optimal retry timing for different decline types.",
        databricks_resource=f"Model: {_default_uc_prefix()}.smart_retry_policy",
        workspace_url=f"{get_workspace_url()}/ml/models/{_default_uc_prefix()}.smart_retry_policy",
        tags=["model-serving", "retry", "recovery", "revenue"],
        example_queries=[
            "Should we retry this declined transaction?",
            "What's the best time to retry an insufficient funds decline?",
            "Estimate recovery rate for this batch of declines",
        ],
    ),
    
    # Mosaic AI Gateway - Custom LLM Agents (https://learn.microsoft.com/en-us/azure/databricks/ai-gateway/)
    AgentInfo(
        id="payment_intelligence_assistant",
        name="Payment Intelligence Assistant",
        description="LLM-powered conversational agent via Mosaic AI Gateway (Llama 3.1 70B) that provides natural language explanations of payment data, identifies anomalies, and suggests optimization strategies.",
        agent_type=AgentType.AI_GATEWAY,
        capabilities=[
            AgentCapability.CONVERSATIONAL_INSIGHTS,
            AgentCapability.AUTOMATED_RECOMMENDATIONS,
            AgentCapability.NATURAL_LANGUAGE_ANALYTICS,
        ],
        use_case="Ask complex questions about payment performance, get AI-generated insights, and receive personalized recommendations for improving approval rates based on your specific merchant portfolio.",
        databricks_resource=f"Mosaic AI Gateway: {os.getenv('AI_GATEWAY_ENDPOINT', 'databricks-meta-llama-3-3-70b-instruct')}",
        workspace_url=f"{get_workspace_url()}/serving-endpoints/{os.getenv('AI_GATEWAY_ENDPOINT', 'databricks-meta-llama-3-3-70b-instruct')}",
        tags=["ai-gateway", "llm", "conversational", "insights"],
        example_queries=[
            "Explain why our approval rate dropped last week",
            "What's causing the spike in fraud scores for gaming merchants?",
            "Generate a report on 3DS adoption impact on approval rates",
            "Suggest 3 strategies to improve approval rates for cross-border payments",
            "Analyze the trade-off between fraud prevention and approval rates",
        ],
    ),
    
    AgentInfo(
        id="risk_assessment_advisor",
        name="Risk Assessment Advisor",
        description="LLM agent specialized in risk analysis that combines fraud scores, AML signals, and behavioral patterns to provide intelligent risk assessments and mitigation recommendations.",
        agent_type=AgentType.AI_GATEWAY,
        capabilities=[
            AgentCapability.CONVERSATIONAL_INSIGHTS,
            AgentCapability.AUTOMATED_RECOMMENDATIONS,
            AgentCapability.REAL_TIME_DECISIONING,
        ],
        use_case="Real-time risk consultation for high-value or suspicious transactions. Get natural language explanations of risk factors and specific recommendations for fraud prevention.",
        databricks_resource=f"Mosaic AI Gateway: {os.getenv('AI_GATEWAY_ENDPOINT', 'databricks-meta-llama-3-3-70b-instruct')}",
        workspace_url=f"{get_workspace_url()}/serving-endpoints/{os.getenv('AI_GATEWAY_ENDPOINT', 'databricks-meta-llama-3-3-70b-instruct')}",
        tags=["ai-gateway", "risk", "fraud", "aml"],
        example_queries=[
            "Is this transaction risky? Explain the risk factors.",
            "Should we approve this high-value cross-border payment?",
            "What additional verification should we require for this transaction?",
            "Explain the fraud score for this merchant",
        ],
    ),
    
    AgentInfo(
        id="performance_recommender",
        name="Performance Recommender",
        description="AI-powered performance advisor that analyzes your payment metrics, compares against benchmarks, and generates actionable recommendations to accelerate approval rates.",
        agent_type=AgentType.CUSTOM_LLM,
        capabilities=[
            AgentCapability.AUTOMATED_RECOMMENDATIONS,
            AgentCapability.CONVERSATIONAL_INSIGHTS,
            AgentCapability.NATURAL_LANGUAGE_ANALYTICS,
        ],
        use_case="Weekly/monthly performance reviews with AI-generated insights. Automatically identifies underperforming segments and generates prioritized action plans for approval rate improvement.",
        databricks_resource="Custom Agent: Performance Analysis & Recommendations",
        workspace_url=get_notebook_workspace_url("src/payment_analysis/agents/agent_framework.py"),
        tags=["custom", "recommendations", "performance", "optimization"],
        example_queries=[
            "Generate my weekly performance report",
            "What are my top 3 opportunities to improve approval rates?",
            "Compare my performance to industry benchmarks",
            "Create an action plan to reach 90% approval rate",
        ],
    ),
]


def _apply_uc_config(agent: AgentInfo, catalog: str, schema: str) -> AgentInfo:
    """Replace default catalog.schema with effective config in resource and URL."""
    full = f"{catalog}.{schema}"
    resource = (agent.databricks_resource or "").replace(_default_uc_prefix(), full)
    url = (agent.workspace_url or "").replace(_default_uc_prefix(), full)
    if resource == (agent.databricks_resource or "") and url == (agent.workspace_url or ""):
        return agent
    return agent.model_copy(
        update={
            "databricks_resource": resource or agent.databricks_resource,
            "workspace_url": url or agent.workspace_url,
        }
    )


def _effective_uc(request: Request) -> tuple[str, str]:
    """Return (catalog, schema) from app state or default (env-based, not hardcoded)."""
    uc = getattr(request.app.state, "uc_config", None)
    if uc and len(uc) == 2 and uc[0] and uc[1]:
        return (uc[0], uc[1])
    return (os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog"), get_default_schema())


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/agents", response_model=AgentList, operation_id="listAgents")
async def list_agents(
    request: Request,
    agent_type: AgentType | None = None,
    entity: str | None = Query(None, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
) -> AgentList:
    """
    List all Databricks AI agents for payment approval optimization.

    Args:
        agent_type: Optional filter by agent type
        entity: Optional entity/country code for filtering (future use)

    Returns:
        List of agents with metadata
    """
    catalog, schema = _effective_uc(request)
    filtered = [_apply_uc_config(a, catalog, schema) for a in AGENTS]
    
    if agent_type:
        filtered = [a for a in filtered if a.agent_type == agent_type]
    
    # Count by type
    by_type = {}
    for agent in AGENTS:
        agent_type_val = agent.agent_type.value
        by_type[agent_type_val] = by_type.get(agent_type_val, 0) + 1
    
    return AgentList(
        agents=filtered,
        total=len(filtered),
        by_type=by_type,
    )


@router.get("/agents/{agent_id}", response_model=AgentInfo, operation_id="getAgent")
async def get_agent(request: Request, agent_id: str) -> AgentInfo:
    """Get details for a specific AI agent."""
    catalog, schema = _effective_uc(request)
    for agent in AGENTS:
        if agent.id == agent_id:
            return _apply_uc_config(agent, catalog, schema)
    
    raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")


class AgentUrlOut(BaseModel):
    agent_id: str
    name: str
    url: str
    agent_type: str
    databricks_resource: str | None = None


class ChatIn(BaseModel):
    """Inbound message for Getnet AI Assistant."""
    message: str = Field(..., min_length=1, max_length=4000)


class ChatOut(BaseModel):
    """Response from Getnet AI Assistant."""
    reply: str
    genie_url: str | None = Field(None, description="Open in Genie for full natural-language analytics")


def _extract_genie_reply(message: Any) -> str:
    """Extract assistant text from GenieMessage.attachments (Databricks SDK GenieMessage)."""
    attachments = getattr(message, "attachments", None) or []
    for att in attachments:
        text_att = getattr(att, "text", None)
        if text_att is not None:
            content = getattr(text_att, "content", None)
            if content and isinstance(content, str):
                return content.strip()
    return ""


@router.post("/chat", response_model=ChatOut, operation_id="postChat")
async def chat(
    request: Request,
    body: ChatIn,
    ws: WorkspaceClient | None = Depends(get_workspace_client_optional),
) -> ChatOut:
    """
    Getnet AI Assistant fallback: when Orchestrator (Job 6) is not used, this endpoint
    is called. If GENIE_SPACE_ID is set and the app has Databricks auth, uses the
    Databricks Genie Conversation API to answer over payment/approval data; otherwise
    returns a static reply and a link to open Genie in the workspace.
    """
    workspace_url = get_workspace_url()
    genie_url = f"{workspace_url.rstrip('/')}/genie" if workspace_url else None
    space_id = (os.environ.get(GENIE_SPACE_ID_ENV) or "").strip()

    if space_id and ws is not None:
        try:
            import datetime

            def _genie_query() -> Any:
                return ws.genie.start_conversation_and_wait(
                    space_id=space_id,
                    content=body.message.strip(),
                    timeout=datetime.timedelta(minutes=2),
                )

            msg = await asyncio.to_thread(_genie_query)
            reply = _extract_genie_reply(msg)
            if reply:
                return ChatOut(reply=reply, genie_url=genie_url)
        except Exception:
            logger.debug("Genie space query failed; falling back to orchestrator", exc_info=True)

    reply = (
        "I can help you explore payment and approval data. For natural language questions "
        "(e.g. top merchants by approval rate, decline reasons, trends), open Genie in your "
        "workspace to run queries against your Databricks tables and dashboards."
    )
    return ChatOut(reply=reply, genie_url=genie_url)


# =============================================================================
# Agent Framework Orchestrator Chat (Job 6 – Deploy Agents)
# =============================================================================

class OrchestratorChatIn(BaseModel):
    """Message for the Agent Framework orchestrator (recommendations & payment analysis)."""
    message: str = Field(..., min_length=1, max_length=4000)


class OrchestratorChatOut(BaseModel):
    """Response from the orchestrator (synthesis from specialists)."""
    reply: str
    run_page_url: str | None = Field(None, description="URL to view the job run in Databricks")
    agents_used: list[str] = Field(default_factory=list)


def _orchestrator_job_id() -> str:
    """Resolve orchestrator job ID from environment."""
    job_id = (os.getenv("DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT") or "").strip()
    if not job_id:
        job_id = (os.getenv("DATABRICKS_JOB_ID_JOB_6_DEPLOY_AGENTS") or "").strip()
    return job_id


def _query_orchestrator_endpoint(ws: WorkspaceClient, endpoint_name: str, user_message: str) -> tuple[str, list[str]]:
    """Call the orchestrator Model Serving endpoint (AgentBricks/Supervisor). Returns (reply, agents_used)."""
    # LangChain/LangGraph chat format: messages list
    payload = {"messages": [{"type": "human", "content": user_message}]}
    response = ws.serving_endpoints.query(
        name=endpoint_name,
        dataframe_records=[payload],
    )
    reply = ""
    agents_used: list[str] = []
    if response.predictions:
        pred = response.predictions[0]
        if isinstance(pred, dict):
            # Optional: messages list with last message content
            msgs = pred.get("messages") or pred.get("output") or pred.get("outputs")
            if isinstance(msgs, list) and msgs:
                last = msgs[-1]
                if isinstance(last, dict):
                    reply = (last.get("content") or last.get("text") or "").strip()
            if not reply:
                reply = (pred.get("content") or pred.get("text") or pred.get("synthesis") or "").strip()
            raw_agents = pred.get("agents_used")
            agents_used = list(raw_agents) if isinstance(raw_agents, (list, tuple)) else []
        elif isinstance(pred, str):
            reply = pred.strip()
    return reply or "No response from orchestrator endpoint.", agents_used


@router.post("/orchestrator/chat", response_model=OrchestratorChatOut, operation_id="postOrchestratorChat")
async def orchestrator_chat(
    request: Request,
    body: OrchestratorChatIn,
    ws: WorkspaceClient = Depends(get_workspace_client),
) -> OrchestratorChatOut:
    """
    Run the orchestrator: when ORCHESTRATOR_SERVING_ENDPOINT is set, calls that AgentBricks/Supervisor
    Model Serving endpoint; otherwise runs Job 6 (custom Python framework). Returns synthesized
    recommendation and payment analysis. Requires Databricks token (open app from Compute → Apps).
    """
    endpoint_name = (os.getenv(ORCHESTRATOR_SERVING_ENDPOINT_ENV) or "").strip()
    if endpoint_name:
        try:
            reply, agents_used = await asyncio.to_thread(
                _query_orchestrator_endpoint, ws, endpoint_name, body.message.strip()
            )
            return OrchestratorChatOut(reply=reply, run_page_url=None, agents_used=agents_used)
        except Exception as e:
            logger.warning(
                "Orchestrator serving endpoint %s failed, falling back to Job 6: %s",
                endpoint_name,
                e,
                exc_info=False,
            )

    job_id_str = _orchestrator_job_id().strip()
    if not job_id_str or job_id_str == "0":
        job_id_str = resolve_orchestrator_job_id(ws).strip()
    if not job_id_str or job_id_str == "0":
        raise HTTPException(
            status_code=400,
            detail="Orchestrator job ID is not set. Deploy the bundle (Job 6 – Deploy Agents exists), open this app from Compute → Apps, then use the assistant. Optionally set DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT.",
        )
    try:
        job_id = int(job_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid orchestrator job ID.") from None

    catalog, schema = _effective_uc(request)
    notebook_params: dict[str, str] = {
        "catalog": catalog,
        "schema": schema,
        "query": body.message.strip(),
        "agent_role": "orchestrator",
    }

    try:
        run = ws.jobs.run_now(
            job_id=job_id,
            notebook_params=notebook_params,
            python_params=None,
            jar_params=None,
            spark_submit_params=None,
        )
        run_id = run.run_id
    except Exception as e:
        msg = str(e).lower()
        if "not found" in msg or "404" in msg:
            raise HTTPException(status_code=404, detail=f"Job not found: {e}") from e
        if "forbidden" in msg or "403" in msg:
            raise HTTPException(status_code=403, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e

    host = get_workspace_url().rstrip("/")
    run_page_url = f"{host}/#job/{job_id}/run/{run_id}" if host else None

    # Poll until run completes; use asyncio.sleep to avoid blocking the event loop
    elapsed = 0
    while elapsed < ORCHESTRATOR_JOB_POLL_TIMEOUT_S:
        await asyncio.sleep(
            min(ORCHESTRATOR_JOB_POLL_INTERVAL_S, ORCHESTRATOR_JOB_POLL_TIMEOUT_S - elapsed)
        )
        elapsed += ORCHESTRATOR_JOB_POLL_INTERVAL_S
        run_info = await asyncio.to_thread(ws.jobs.get_run, run_id)
        state_obj = getattr(run_info, "state", None)
        state = getattr(state_obj, "life_cycle_state", None) or ""
        if state == "TERMINATED":
            result_state = getattr(state_obj, "result_state", None) or "UNKNOWN"
            if result_state != "SUCCESS":
                return OrchestratorChatOut(
                    reply=f"The agent run finished with state: {result_state}. Check the run in Databricks for details.",
                    run_page_url=run_page_url,
                    agents_used=[],
                )
            try:
                out = await asyncio.to_thread(ws.jobs.get_run_output, run_id)
                nb_out = getattr(out, "notebook_output", None)
                notebook_result = getattr(nb_out, "result", None) if nb_out else None
                if notebook_result:
                    data = json.loads(notebook_result)
                    synthesis = (data.get("synthesis") or "").strip()
                    agents_used = data.get("agents_used") or []
                    return OrchestratorChatOut(
                        reply=synthesis or "No synthesis returned.",
                        run_page_url=run_page_url,
                        agents_used=agents_used,
                    )
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Could not parse orchestrator job output: %s", e)
            return OrchestratorChatOut(
                reply="The run completed successfully. View the full output in the run page.",
                run_page_url=run_page_url,
                agents_used=[],
            )
        if state in ("FAILED", "INTERNAL_ERROR", "SKIPPED"):
            msg = getattr(state_obj, "state_message", None) or state
            return OrchestratorChatOut(
                reply=f"The agent run did not complete: {msg}. Open the run page for details.",
                run_page_url=run_page_url,
                agents_used=[],
            )

    return OrchestratorChatOut(
        reply="The run is still in progress. Open the run page to view the result when it completes.",
        run_page_url=run_page_url,
        agents_used=[],
    )


@router.get("/agents/{agent_id}/url", response_model=AgentUrlOut, operation_id="getAgentUrl")
async def get_agent_url(request: Request, agent_id: str) -> AgentUrlOut:
    """Get the Databricks workspace URL for an agent."""
    agent = await get_agent(request, agent_id)
    
    return AgentUrlOut(
        agent_id=agent_id,
        name=agent.name,
        url=agent.workspace_url or get_workspace_url(),
        agent_type=agent.agent_type.value,
        databricks_resource=agent.databricks_resource,
    )


@router.get("/agents/types/summary", response_model=dict[str, Any], operation_id="getAgentTypeSummary")
async def get_type_summary() -> dict[str, Any]:
    """
    Get summary of agents by type with descriptions.
    
    Returns counts and agent lists for each type.
    """
    summary = {}
    
    for agent_type in AgentType:
        agents_in_type = [a for a in AGENTS if a.agent_type == agent_type]
        summary[agent_type.value] = {
            "name": agent_type.value.replace("_", " ").title(),
            "count": len(agents_in_type),
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "use_case": a.use_case,
                }
                for a in agents_in_type
            ],
        }
    
    return {
        "types": summary,
        "total_agents": len(AGENTS),
    }
