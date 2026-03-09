"""
Databricks AI Agents Registry - Payment Approval Optimization.

This module provides AI agents powered by Databricks features:
- Genie: Natural language SQL analytics
- Model Serving: ML-powered recommendations
- Mosaic AI Gateway: LLM routing and prompt engineering
- Custom Agents: Domain-specific payment intelligence
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import time
from enum import Enum
from functools import lru_cache
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..config import AppConfig, ensure_absolute_workspace_url, get_default_schema
from ..dependencies import get_workspace_client, get_workspace_client_optional
from ..logger import logger
from .setup import resolve_orchestrator_job_id

try:
    import mlflow as _mlflow
    _trace = _mlflow.trace
except ImportError:
    def _trace(*args: Any, **kwargs: Any) -> Any:
        """No-op decorator when mlflow-tracing is not installed."""
        if args and callable(args[0]):
            return args[0]
        return lambda fn: fn

# ---------------------------------------------------------------------------
# Environment config constants
# ---------------------------------------------------------------------------

GENIE_SPACE_ID_ENV = "GENIE_SPACE_ID"
ORCHESTRATOR_SERVING_ENDPOINT_ENV = "ORCHESTRATOR_SERVING_ENDPOINT"
AI_GATEWAY_ENDPOINT_ENV = "LLM_ENDPOINT"
AI_GATEWAY_ENDPOINT_DEFAULT = "databricks-claude-opus-4-6"
AI_GATEWAY_GENIE_ENDPOINT_ENV = "LLM_ENDPOINT_GENIE"
AI_GATEWAY_GENIE_ENDPOINT_DEFAULT = "databricks-claude-sonnet-4-5"

ORCHESTRATOR_JOB_POLL_TIMEOUT_S = 50
ORCHESTRATOR_JOB_POLL_INTERVAL_S = 4

# Databricks Apps proxy returns HTTP 504 after ~60 s.
# Leave headroom for deserialization + network latency.
_PROXY_DEADLINE_S = 55
_SERVING_CALL_TIMEOUT_S = 45
_GENIE_CALL_TIMEOUT_S = 45

# Shared brevity instruction so all agent paths produce concise answers.
_BREVITY_INSTRUCTION = (
    "\n\n[IMPORTANT: You are replying inside a small floating chat dialog. "
    "Keep your answer SHORT — 2-4 sentences or 3-5 bullet points max. "
    "Use plain language, no tables, no code blocks, no markdown headers. "
    "Cite numbers inline (e.g. 'approval rate is 87.3%'). "
    "End with one brief next-step suggestion when relevant.]"
)

_ORCHESTRATOR_SYSTEM_PROMPT = (
    "You are the Payment Approval Rate Accelerator — an AI assistant for the payment platform.\n\n"
    "Your role: Help users understand payment approval rates and suggest ways to improve them.\n\n"
    "Knowledge: Smart Routing, Smart Retry, Decline Analysis, Risk & Fraud, Performance Optimization.\n"
    "Data: Unity Catalog gold views (KPIs, trends, decline reasons, solution performance, merchant "
    "segments, retry rates) and 4 ML models (approval propensity, risk scoring, smart routing, smart retry).\n\n"
    "RESPONSE RULES — you are displayed in a small floating chat dialog:\n"
    "- Keep answers SHORT: 2-4 sentences max, or 3-5 bullet points max.\n"
    "- Use plain, simple language. No jargon unless the user asks for technical detail.\n"
    "- NEVER output tables, markdown tables, or tabular data. Use bullet points instead.\n"
    "- NEVER use code blocks or SQL queries in responses.\n"
    "- When citing numbers, use inline text (e.g. \"approval rate is 87.3%\"), not tables.\n"
    "- End with one brief next-step suggestion when relevant.\n"
    "- If the user asks for detailed data, suggest they check the Dashboards or Decisioning pages in the app."
)

_GENIE_SYSTEM_PROMPT = (
    "You are the Genie Assistant for the payment platform — a data analyst for payment analytics.\n\n"
    "Answer questions about payment data using Unity Catalog gold views "
    "(KPIs, trends, decline reasons, performance by solution/merchant/network, retry rates, "
    "data quality, streaming volume).\n\n"
    "RESPONSE RULES — you are displayed in a small floating chat dialog:\n"
    "- Keep answers SHORT: 2-4 sentences or 3-5 bullet points max.\n"
    "- Use plain language. No jargon.\n"
    "- NEVER output tables, markdown tables, or tabular data. Use bullet points instead.\n"
    "- NEVER use code blocks or SQL.\n"
    "- Suggest one follow-up question when relevant."
)

router = APIRouter(tags=["agents"])

# ---------------------------------------------------------------------------
# Lazy helpers (avoid module-level side effects)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _workspace_url() -> str:
    """Workspace URL, resolved once on first call."""
    cfg = AppConfig().databricks
    url = (cfg.workspace_url or "").strip().rstrip("/")
    if url and not url.startswith("https://"):
        url = f"https://{url}"
    return url


def _default_uc_prefix() -> str:
    catalog = os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog")
    return f"{catalog}.{get_default_schema()}"


def _notebook_workspace_url(relative_path: str) -> str:
    ws = _workspace_url()
    user_email = os.getenv("DATABRICKS_USER", "ariel.hdez@databricks.com")
    folder_name = os.getenv("BUNDLE_FOLDER", "payment-analysis")
    return f"{ws}/workspace/Workspace/Users/{user_email}/{folder_name}/{relative_path}"


def _effective_uc(request: Request) -> tuple[str, str]:
    uc = getattr(request.app.state, "uc_config", None)
    if uc and len(uc) == 2 and uc[0] and uc[1]:
        return (uc[0], uc[1])
    return (os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog"), get_default_schema())


# ---------------------------------------------------------------------------
# Shared extraction helpers
# ---------------------------------------------------------------------------

def _extract_chat_completion(response: Any) -> str:
    """Extract text from a chat-completion-style response (AI Gateway / foundation model)."""
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    msg = getattr(choices[0], "message", choices[0])
    return (getattr(msg, "content", "") or "").strip()


def _extract_genie_reply(message: Any) -> str:
    """Extract assistant text from GenieMessage.attachments."""
    for att in getattr(message, "attachments", None) or []:
        text_att = getattr(att, "text", None)
        if text_att is not None:
            content = getattr(text_att, "content", None)
            if content and isinstance(content, str):
                return content.strip()
    return ""


def _extract_responses_agent_reply(predictions: Any) -> str:
    """Extract the last assistant message from a ResponsesAgent prediction.

    Handles both string and list content formats:
    - String content: ``{"type": "message", "role": "assistant", "content": "..."}``
    - List content: ``{"type": "message", "content": [{"text": "..."}]}``
    """
    if not predictions:
        return ""
    pred = predictions if isinstance(predictions, dict) else (predictions[0] if isinstance(predictions, list) and predictions else {})
    if isinstance(pred, str):
        return pred.strip()
    if not isinstance(pred, dict):
        return ""

    output = pred.get("output")
    if isinstance(output, list):
        for item in reversed(output):
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message" and item.get("role") == "assistant":
                content = item.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            text = (part.get("text") or "").strip()
                            if text:
                                return text
            elif item.get("type") == "text" and item.get("text"):
                return (item["text"]).strip()
    if isinstance(output, str):
        return output.strip()
    return (pred.get("content") or pred.get("text") or "").strip()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AgentType(str, Enum):
    GENIE = "genie"
    MODEL_SERVING = "model_serving"
    CUSTOM_LLM = "custom_llm"
    AI_GATEWAY = "ai_gateway"


class AgentCapability(str, Enum):
    NATURAL_LANGUAGE_ANALYTICS = "natural_language_analytics"
    PREDICTIVE_SCORING = "predictive_scoring"
    CONVERSATIONAL_INSIGHTS = "conversational_insights"
    AUTOMATED_RECOMMENDATIONS = "automated_recommendations"
    REAL_TIME_DECISIONING = "real_time_decisioning"


class AgentInfo(BaseModel):
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
    agents: list[AgentInfo]
    total: int
    by_type: dict[str, int]


class AgentUrlOut(BaseModel):
    agent_id: str
    name: str
    url: str
    agent_type: str
    databricks_resource: str | None = None


class AgentTypeAgentSummary(BaseModel):
    id: str
    name: str
    use_case: str


class AgentTypeDetail(BaseModel):
    name: str
    count: int
    agents: list[AgentTypeAgentSummary]


class AgentTypeSummaryOut(BaseModel):
    types: dict[str, AgentTypeDetail]
    total_agents: int


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatOut(BaseModel):
    reply: str
    genie_url: str | None = Field(None, description="Open in Genie for full analytics")


class OrchestratorChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class OrchestratorChatOut(BaseModel):
    reply: str
    run_page_url: str | None = Field(None, description="URL to view the job run")
    agents_used: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent registry (lazy: workspace_url resolved on first call, not at import)
# ---------------------------------------------------------------------------

def _build_agents() -> list[AgentInfo]:
    ws = _workspace_url()
    prefix = _default_uc_prefix()
    return [
        AgentInfo(
            id="approval_optimizer_genie",
            name="Approval Optimizer (Genie)",
            description="Natural language analytics for approval rate optimization. Ask questions about approval patterns, merchant performance, and identify opportunities to increase approval rates.",
            agent_type=AgentType.GENIE,
            capabilities=[AgentCapability.NATURAL_LANGUAGE_ANALYTICS, AgentCapability.CONVERSATIONAL_INSIGHTS],
            use_case="Query payment data using natural language to discover approval optimization opportunities.",
            databricks_resource="Genie Space: Payment Approval Analytics",
            workspace_url=f"{ws}/genie",
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
            capabilities=[AgentCapability.NATURAL_LANGUAGE_ANALYTICS, AgentCapability.CONVERSATIONAL_INSIGHTS],
            use_case="Deep-dive into decline patterns to identify recoverable transactions and optimal retry strategies.",
            databricks_resource="Genie Space: Decline Analysis",
            workspace_url=f"{ws}/genie",
            tags=["genie", "declines", "recovery", "analytics"],
            example_queries=[
                "What are the top 5 decline reasons this month?",
                "How many declined transactions could be recovered with smart retry?",
                "Show me decline rates by issuer country",
                "Which decline codes have the highest retry success rates?",
                "What's the average time to successful retry for insufficient funds declines?",
            ],
        ),
        AgentInfo(
            id="approval_propensity_predictor",
            name="Approval Propensity Predictor",
            description="ML model serving endpoint that predicts transaction approval likelihood in real-time. Uses HistGradientBoosting trained on 14 engineered features.",
            agent_type=AgentType.MODEL_SERVING,
            capabilities=[AgentCapability.PREDICTIVE_SCORING, AgentCapability.REAL_TIME_DECISIONING],
            use_case="Real-time approval probability scoring for intelligent routing decisions.",
            databricks_resource=f"Model: {prefix}.approval_propensity_model",
            workspace_url=f"{ws}/ml/models/{prefix}.approval_propensity_model",
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
            capabilities=[AgentCapability.PREDICTIVE_SCORING, AgentCapability.AUTOMATED_RECOMMENDATIONS, AgentCapability.REAL_TIME_DECISIONING],
            use_case="Automatically select the best payment solution to maximize approval rates while balancing fraud risk and costs.",
            databricks_resource=f"Model: {prefix}.smart_routing_policy",
            workspace_url=f"{ws}/ml/models/{prefix}.smart_routing_policy",
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
            description="ML agent that identifies declined transactions with high recovery potential and recommends optimal retry timing and strategy.",
            agent_type=AgentType.MODEL_SERVING,
            capabilities=[AgentCapability.PREDICTIVE_SCORING, AgentCapability.AUTOMATED_RECOMMENDATIONS],
            use_case="Increase revenue recovery by 15-25% through intelligent retry strategies.",
            databricks_resource=f"Model: {prefix}.smart_retry_policy",
            workspace_url=f"{ws}/ml/models/{prefix}.smart_retry_policy",
            tags=["model-serving", "retry", "recovery", "revenue"],
            example_queries=[
                "Should we retry this declined transaction?",
                "What's the best time to retry an insufficient funds decline?",
                "Estimate recovery rate for this batch of declines",
            ],
        ),
        AgentInfo(
            id="payment_intelligence_assistant",
            name="Payment Intelligence Assistant",
            description="LLM-powered conversational agent via AI Gateway (Claude Opus 4.6 & Sonnet 4.5) that provides natural language explanations, identifies anomalies, and suggests optimization strategies.",
            agent_type=AgentType.AI_GATEWAY,
            capabilities=[AgentCapability.CONVERSATIONAL_INSIGHTS, AgentCapability.AUTOMATED_RECOMMENDATIONS, AgentCapability.NATURAL_LANGUAGE_ANALYTICS],
            use_case="Ask complex questions about payment performance, get AI-generated insights, and receive personalized recommendations.",
            databricks_resource="AI Gateway: databricks-claude-sonnet-4-5",
            workspace_url=f"{ws}/serving-endpoints/databricks-claude-sonnet-4-5",
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
            description="LLM agent specialized in risk analysis that combines fraud scores, AML signals, and behavioral patterns for intelligent risk assessments.",
            agent_type=AgentType.AI_GATEWAY,
            capabilities=[AgentCapability.CONVERSATIONAL_INSIGHTS, AgentCapability.AUTOMATED_RECOMMENDATIONS, AgentCapability.REAL_TIME_DECISIONING],
            use_case="Real-time risk consultation for high-value or suspicious transactions.",
            databricks_resource="AI Gateway: databricks-claude-sonnet-4-5",
            workspace_url=f"{ws}/serving-endpoints/databricks-claude-sonnet-4-5",
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
            description="AI-powered performance advisor that analyzes payment metrics, compares against benchmarks, and generates actionable recommendations.",
            agent_type=AgentType.CUSTOM_LLM,
            capabilities=[AgentCapability.AUTOMATED_RECOMMENDATIONS, AgentCapability.CONVERSATIONAL_INSIGHTS, AgentCapability.NATURAL_LANGUAGE_ANALYTICS],
            use_case="Weekly/monthly performance reviews with AI-generated insights and prioritized action plans.",
            databricks_resource="Custom Agent: Performance Analysis & Recommendations",
            workspace_url=_notebook_workspace_url("src/payment_analysis/agents/agent_framework.py"),
            tags=["custom", "recommendations", "performance", "optimization"],
            example_queries=[
                "Generate my weekly performance report",
                "What are my top 3 opportunities to improve approval rates?",
                "Compare my performance to industry benchmarks",
                "Create an action plan to reach 90% approval rate",
            ],
        ),
    ]


@lru_cache(maxsize=1)
def _agents_registry() -> list[AgentInfo]:
    return _build_agents()


def _apply_uc_config(agent: AgentInfo, catalog: str, schema: str) -> AgentInfo:
    """Replace default catalog.schema in resource/URL with effective config."""
    full = f"{catalog}.{schema}"
    default = _default_uc_prefix()
    if default == full:
        return agent
    resource = (agent.databricks_resource or "").replace(default, full)
    url = (agent.workspace_url or "").replace(default, full)
    if resource == (agent.databricks_resource or "") and url == (agent.workspace_url or ""):
        return agent
    return agent.model_copy(update={"databricks_resource": resource, "workspace_url": url})


# Re-export for backward compatibility
def get_workspace_url() -> str:
    return _workspace_url()


def get_notebook_workspace_url(relative_path: str) -> str:
    return _notebook_workspace_url(relative_path)


# ---------------------------------------------------------------------------
# Endpoints — IMPORTANT: specific paths BEFORE parameterized paths
# ---------------------------------------------------------------------------

@router.get("/agents/types/summary", response_model=AgentTypeSummaryOut, operation_id="getAgentTypeSummary")
async def get_type_summary() -> AgentTypeSummaryOut:
    """Get summary of agents by type."""
    agents = _agents_registry()
    types: dict[str, AgentTypeDetail] = {}
    for agent_type in AgentType:
        agents_in_type = [a for a in agents if a.agent_type == agent_type]
        types[agent_type.value] = AgentTypeDetail(
            name=agent_type.value.replace("_", " ").title(),
            count=len(agents_in_type),
            agents=[AgentTypeAgentSummary(id=a.id, name=a.name, use_case=a.use_case) for a in agents_in_type],
        )
    return AgentTypeSummaryOut(types=types, total_agents=len(agents))


@router.get("/agents", response_model=AgentList, operation_id="listAgents")
async def list_agents(
    request: Request,
    agent_type: AgentType | None = None,
    entity: str | None = Query(None, description="Entity or country code (reserved for future filtering)"),
) -> AgentList:
    """List all Databricks AI agents for payment approval optimization."""
    catalog, schema = _effective_uc(request)
    agents = _agents_registry()
    filtered = [_apply_uc_config(a, catalog, schema) for a in agents]
    if agent_type:
        filtered = [a for a in filtered if a.agent_type == agent_type]

    by_type: dict[str, int] = {}
    for a in agents:
        by_type[a.agent_type.value] = by_type.get(a.agent_type.value, 0) + 1

    return AgentList(agents=filtered, total=len(filtered), by_type=by_type)


@router.get("/agents/{agent_id}", response_model=AgentInfo, operation_id="getAgent")
async def get_agent(request: Request, agent_id: str) -> AgentInfo:
    """Get details for a specific AI agent."""
    catalog, schema = _effective_uc(request)
    for agent in _agents_registry():
        if agent.id == agent_id:
            return _apply_uc_config(agent, catalog, schema)
    raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")


@router.get("/agents/{agent_id}/url", response_model=AgentUrlOut, operation_id="getAgentUrl")
async def get_agent_url(request: Request, agent_id: str) -> AgentUrlOut:
    """Get the Databricks workspace URL for an agent."""
    agent = await get_agent(request, agent_id)
    return AgentUrlOut(
        agent_id=agent_id,
        name=agent.name,
        url=agent.workspace_url or _workspace_url(),
        agent_type=agent.agent_type.value,
        databricks_resource=agent.databricks_resource,
    )


# ---------------------------------------------------------------------------
# Genie Assistant chat
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatOut, operation_id="postChat")
async def chat(
    request: Request,
    body: ChatIn,
    ws: WorkspaceClient | None = Depends(get_workspace_client_optional),
) -> ChatOut:
    """
    Genie Assistant endpoint for natural-language SQL analytics.

    Resolution order:
      1. Databricks Genie Conversation API (when GENIE_SPACE_ID set).
      2. AI Gateway direct call (Sonnet — balanced data-analyst fallback).
      3. Static reply with link to Genie workspace.
    """
    workspace_url = ensure_absolute_workspace_url(_workspace_url())
    genie_url = f"{workspace_url.rstrip('/')}/genie" if workspace_url else None
    space_id = (os.environ.get(GENIE_SPACE_ID_ENV) or "").strip()

    # Path 1: Genie Conversation API
    if space_id and ws is not None:
        try:
            msg = await asyncio.wait_for(
                asyncio.to_thread(
                    ws.genie.start_conversation_and_wait,
                    space_id=space_id,
                    content=body.message.strip(),
                    timeout=datetime.timedelta(seconds=_GENIE_CALL_TIMEOUT_S),
                ),
                timeout=_GENIE_CALL_TIMEOUT_S,
            )
            reply = _extract_genie_reply(msg)
            if reply:
                return ChatOut(reply=reply, genie_url=genie_url)
            logger.info("Genie returned empty reply for space %s; trying AI Gateway.", space_id)
        except asyncio.TimeoutError:
            logger.warning("Genie timed out after %ds (space=%s), trying AI Gateway", _GENIE_CALL_TIMEOUT_S, space_id)
        except Exception as exc:
            logger.warning("Genie query failed (space=%s): %s", space_id, exc)

    # Path 2: AI Gateway direct (Sonnet tier)
    if ws is not None:
        try:
            endpoint_name = (os.getenv(AI_GATEWAY_GENIE_ENDPOINT_ENV) or "").strip() or AI_GATEWAY_GENIE_ENDPOINT_DEFAULT
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    ws.serving_endpoints.query,
                    name=endpoint_name,
                    messages=[
                        ChatMessage(role=ChatMessageRole.SYSTEM, content=_GENIE_SYSTEM_PROMPT),
                        ChatMessage(role=ChatMessageRole.USER, content=body.message.strip()),
                    ],
                    max_tokens=500,
                    temperature=0.2,
                ),
                timeout=_SERVING_CALL_TIMEOUT_S,
            )
            content = _extract_chat_completion(response)
            if content:
                return ChatOut(reply=content, genie_url=genie_url)
        except asyncio.TimeoutError:
            logger.warning("AI Gateway Genie fallback timed out after %ds", _SERVING_CALL_TIMEOUT_S)
        except Exception as exc:
            logger.warning("AI Gateway Genie fallback failed: %s", exc)

    # Path 3: Static reply
    if space_id:
        reply = (
            "I can help you explore payment and approval data. "
            "The Genie space is configured but the live query could not complete right now. "
            "You can open Genie directly in your Databricks workspace for natural language "
            "questions (e.g. top merchants by approval rate, decline reasons, trends)."
        )
    else:
        reply = (
            "I can help you explore payment and approval data. For natural language questions "
            "(e.g. top merchants by approval rate, decline reasons, trends), open Genie in your "
            "workspace to run queries against your Databricks tables and dashboards."
        )
    return ChatOut(reply=reply, genie_url=genie_url)


# ---------------------------------------------------------------------------
# Orchestrator chat (AI Chatbot floating dialog)
# ---------------------------------------------------------------------------

@_trace(name="query_responses_agent", span_type="AGENT")
def _query_orchestrator_endpoint(ws: WorkspaceClient, endpoint_name: str, user_message: str) -> tuple[str, list[str]]:
    """Call the ResponsesAgent on Model Serving (dataframe_records format)."""
    response = ws.serving_endpoints.query(
        name=endpoint_name,
        dataframe_records=[{
            "input": [{"role": "user", "content": user_message + _BREVITY_INSTRUCTION}],
            "custom_inputs": {"session_id": "orchestrator-chat"},
        }],
    )
    reply = _extract_responses_agent_reply(getattr(response, "predictions", None))
    return reply, ["ResponsesAgent (orchestrator)"] if reply else []


@_trace(name="query_ai_gateway", span_type="LLM")
def _query_ai_gateway_direct(ws: WorkspaceClient, user_message: str) -> tuple[str, list[str]]:
    """Call Opus 4.6 via AI Gateway with the orchestrator system prompt."""
    endpoint_name = (os.getenv(AI_GATEWAY_ENDPOINT_ENV) or "").strip() or AI_GATEWAY_ENDPOINT_DEFAULT
    response = ws.serving_endpoints.query(
        name=endpoint_name,
        messages=[
            ChatMessage(role=ChatMessageRole.SYSTEM, content=_ORCHESTRATOR_SYSTEM_PROMPT + _BREVITY_INSTRUCTION),
            ChatMessage(role=ChatMessageRole.USER, content=user_message),
        ],
        max_tokens=600,
        temperature=0.2,
    )
    content = _extract_chat_completion(response)
    return (content, ["AI Gateway (Opus)"]) if content else ("", [])


def _remaining(t0: float) -> float:
    """Seconds remaining before the proxy deadline."""
    return max(_PROXY_DEADLINE_S - (time.monotonic() - t0), 1.0)


@router.post("/orchestrator/chat", response_model=OrchestratorChatOut, operation_id="postOrchestratorChat")
async def orchestrator_chat(
    request: Request,
    body: OrchestratorChatIn,
    ws: WorkspaceClient = Depends(get_workspace_client),
) -> OrchestratorChatOut:
    """
    Orchestrator Agent — backend for the AI Chatbot floating dialog.

    Resolution order (with shared timeout budget):
      1. ResponsesAgent on Model Serving (with UC tools).
      2. AI Gateway direct call (Opus 4.6 foundation model).
      3. Job 6 (custom Python multi-agent framework).
    """
    t0 = time.monotonic()
    user_message = body.message.strip()

    # --- Path 1: ResponsesAgent ---
    endpoint_name = (os.getenv(ORCHESTRATOR_SERVING_ENDPOINT_ENV) or "").strip()
    if endpoint_name:
        logger.info("Orchestrator chat: trying Path 1 (ResponsesAgent '%s')", endpoint_name)
        try:
            reply, agents_used = await asyncio.wait_for(
                asyncio.to_thread(_query_orchestrator_endpoint, ws, endpoint_name, user_message),
                timeout=min(_SERVING_CALL_TIMEOUT_S, _remaining(t0)),
            )
            if reply:
                logger.info("Orchestrator chat: Path 1 succeeded")
                return OrchestratorChatOut(reply=reply, run_page_url=None, agents_used=agents_used)
            logger.warning("Orchestrator chat: Path 1 empty reply, trying Path 2")
        except asyncio.TimeoutError:
            logger.warning("Path 1 timed out (%.1fs elapsed), trying Path 2", time.monotonic() - t0)
        except Exception as e:
            logger.warning("Path 1 failed (%s), trying Path 2: %s", endpoint_name, e)

    # --- Path 2: AI Gateway direct ---
    if _remaining(t0) > 3:
        try:
            reply, agents_used = await asyncio.wait_for(
                asyncio.to_thread(_query_ai_gateway_direct, ws, user_message),
                timeout=min(_SERVING_CALL_TIMEOUT_S, _remaining(t0)),
            )
            if reply:
                return OrchestratorChatOut(reply=reply, run_page_url=None, agents_used=agents_used)
        except asyncio.TimeoutError:
            logger.warning("Path 2 timed out (%.1fs elapsed), trying Path 3", time.monotonic() - t0)
        except Exception as e:
            logger.warning("Path 2 failed, trying Path 3: %s", e)

    # --- Path 3: Job 6 (multi-agent framework) ---
    if _remaining(t0) < 10:
        raise HTTPException(
            status_code=504,
            detail="Request timed out. Both the ResponsesAgent and AI Gateway were unavailable. "
                   "Try again or check that the serving endpoints are running.",
        )

    job_id_str = (os.getenv("DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT") or "").strip()
    if not job_id_str or job_id_str == "0":
        job_id_str = resolve_orchestrator_job_id(ws).strip()
    if not job_id_str or job_id_str == "0":
        raise HTTPException(
            status_code=400,
            detail="Orchestrator unavailable. No serving endpoint, AI Gateway, or job ID configured. "
                   "Deploy the bundle (Job 6), open the app from Compute → Apps, then use the assistant.",
        )
    try:
        job_id = int(job_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid orchestrator job ID.") from None

    catalog, schema = _effective_uc(request)
    try:
        run = ws.jobs.run_now(job_id=job_id, notebook_params={
            "catalog": catalog,
            "schema": schema,
            "query": user_message,
            "agent_role": "orchestrator",
        })
        run_id = run.run_id
    except Exception as e:
        msg = str(e).lower()
        if "not found" in msg or "404" in msg:
            raise HTTPException(status_code=404, detail=f"Job not found: {e}") from e
        if "forbidden" in msg or "403" in msg:
            raise HTTPException(status_code=403, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e

    host = _workspace_url().rstrip("/")
    run_page_url = f"{host}/#job/{job_id}/run/{run_id}" if host else None

    elapsed = 0
    poll_budget = min(ORCHESTRATOR_JOB_POLL_TIMEOUT_S, _remaining(t0) - 2)
    while elapsed < poll_budget:
        await asyncio.sleep(min(ORCHESTRATOR_JOB_POLL_INTERVAL_S, poll_budget - elapsed))
        elapsed += ORCHESTRATOR_JOB_POLL_INTERVAL_S
        run_info = ws.jobs.get_run(run_id)
        state_obj = getattr(run_info, "state", None)
        state = getattr(state_obj, "life_cycle_state", None) or ""
        if state == "TERMINATED":
            result_state = getattr(state_obj, "result_state", None) or "UNKNOWN"
            if result_state != "SUCCESS":
                return OrchestratorChatOut(
                    reply=f"The agent run finished with state: {result_state}. Check the run in Databricks for details.",
                    run_page_url=run_page_url, agents_used=[],
                )
            try:
                out = ws.jobs.get_run_output(run_id)
                nb_out = getattr(out, "notebook_output", None)
                notebook_result = getattr(nb_out, "result", None) if nb_out else None
                if notebook_result:
                    data = json.loads(notebook_result)
                    synthesis = (data.get("synthesis") or "").strip()
                    return OrchestratorChatOut(
                        reply=synthesis or "No synthesis returned.",
                        run_page_url=run_page_url,
                        agents_used=data.get("agents_used") or [],
                    )
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Could not parse orchestrator job output: %s", e)
            return OrchestratorChatOut(
                reply="The run completed. View the full output in the run page.",
                run_page_url=run_page_url, agents_used=[],
            )
        if state in ("FAILED", "INTERNAL_ERROR", "SKIPPED"):
            msg_text = getattr(state_obj, "state_message", None) or state
            return OrchestratorChatOut(
                reply=f"The agent run did not complete: {msg_text}. Open the run page for details.",
                run_page_url=run_page_url, agents_used=[],
            )

    return OrchestratorChatOut(
        reply="The run is still in progress. Open the run page to view the result when it completes.",
        run_page_url=run_page_url, agents_used=[],
    )
