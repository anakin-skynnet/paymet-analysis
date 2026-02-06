"""
Databricks AI Agents Registry - Payment Approval Optimization.

This module provides AI agents powered by Databricks features:
- Genie: Natural language SQL analytics
- Model Serving: ML-powered recommendations
- Mosaic AI Gateway: LLM routing and prompt engineering
- Custom Agents: Domain-specific payment intelligence

NOTE: Workspace URLs are constructed dynamically based on environment variables.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import AppConfig

router = APIRouter(tags=["agents"])

_databricks_config = AppConfig().databricks

# Default catalog.schema used in AGENTS; replaced with effective config when returning.
_DEFAULT_UC_PREFIX = "ahs_demos_catalog.ahs_demo_payment_analysis_dev"


# =============================================================================
# Helper Functions
# =============================================================================

def get_workspace_url() -> str:
    """Get Databricks workspace URL from centralized config."""
    return _databricks_config.workspace_url


def get_notebook_workspace_url(relative_path: str) -> str:
    """Construct full workspace URL for a notebook."""
    workspace_url = get_workspace_url()
    user_email = os.getenv("DATABRICKS_USER", "user@company.com")
    folder_name = os.getenv("BUNDLE_FOLDER", "payment-analysis")
    full_path = f"/Users/{user_email}/{folder_name}/files/{relative_path}"
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
        databricks_resource="Model: ahs_demos_catalog.ahs_demo_payment_analysis_dev.approval_propensity_model",
        workspace_url=f"{get_workspace_url()}/ml/models/ahs_demos_catalog.ahs_demo_payment_analysis_dev.approval_propensity_model",
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
        databricks_resource="Model: ahs_demos_catalog.ahs_demo_payment_analysis_dev.smart_routing_policy",
        workspace_url=f"{get_workspace_url()}/ml/models/ahs_demos_catalog.ahs_demo_payment_analysis_dev.smart_routing_policy",
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
        databricks_resource="Model: ahs_demos_catalog.ahs_demo_payment_analysis_dev.smart_retry_policy",
        workspace_url=f"{get_workspace_url()}/ml/models/ahs_demos_catalog.ahs_demo_payment_analysis_dev.smart_retry_policy",
        tags=["model-serving", "retry", "recovery", "revenue"],
        example_queries=[
            "Should we retry this declined transaction?",
            "What's the best time to retry an insufficient funds decline?",
            "Estimate recovery rate for this batch of declines",
        ],
    ),
    
    # AI Gateway - Custom LLM Agents
    AgentInfo(
        id="payment_intelligence_assistant",
        name="Payment Intelligence Assistant",
        description="LLM-powered conversational agent via AI Gateway (Llama 3.1 70B) that provides natural language explanations of payment data, identifies anomalies, and suggests optimization strategies.",
        agent_type=AgentType.AI_GATEWAY,
        capabilities=[
            AgentCapability.CONVERSATIONAL_INSIGHTS,
            AgentCapability.AUTOMATED_RECOMMENDATIONS,
            AgentCapability.NATURAL_LANGUAGE_ANALYTICS,
        ],
        use_case="Ask complex questions about payment performance, get AI-generated insights, and receive personalized recommendations for improving approval rates based on your specific merchant portfolio.",
        databricks_resource="AI Gateway: databricks-meta-llama-3-1-70b-instruct",
        workspace_url=f"{get_workspace_url()}/serving-endpoints/databricks-meta-llama-3-1-70b-instruct",
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
        databricks_resource="AI Gateway: databricks-meta-llama-3-1-70b-instruct",
        workspace_url=f"{get_workspace_url()}/serving-endpoints/databricks-meta-llama-3-1-70b-instruct",
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
    resource = (agent.databricks_resource or "").replace(_DEFAULT_UC_PREFIX, full)
    url = (agent.workspace_url or "").replace(_DEFAULT_UC_PREFIX, full)
    if resource == (agent.databricks_resource or "") and url == (agent.workspace_url or ""):
        return agent
    return agent.model_copy(
        update={
            "databricks_resource": resource or agent.databricks_resource,
            "workspace_url": url or agent.workspace_url,
        }
    )


def _effective_uc(request: Request) -> tuple[str, str]:
    """Return (catalog, schema) from app state or default."""
    uc = getattr(request.app.state, "uc_config", None)
    if uc and len(uc) == 2 and uc[0] and uc[1]:
        return (uc[0], uc[1])
    return ("ahs_demos_catalog", "ahs_demo_payment_analysis_dev")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/agents", response_model=AgentList, operation_id="listAgents")
async def list_agents(
    request: Request,
    agent_type: AgentType | None = None,
) -> AgentList:
    """
    List all Databricks AI agents for payment approval optimization.
    
    Args:
        agent_type: Optional filter by agent type
        
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
