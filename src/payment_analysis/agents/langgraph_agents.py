"""
Databricks AgentBricks (code-based): LangGraph + UC functions.

Converts the payment analysis Python agents (agent_framework.py) to deployable
AgentBricks agents: same five specialists (Smart Routing, Smart Retry, Decline Analyst,
Risk Assessor, Performance Recommender) using Unity Catalog functions as tools,
LangGraph ReAct agents, MLflow registration, and Model Serving. Orchestration is
via the workspace Multi-Agent Supervisor.

Dependencies (install in notebook or job cluster):
  %pip install databricks-langchain unitycatalog-langchain[databricks] langgraph langchain-core
  dbutils.library.restartPython()

Requires: UC functions in catalog.schema (e.g. ahs_demos_catalog.payment_analysis); run run_create_uc_agent_tools first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from typing import Any, Callable

# System prompts 1:1 from agent_framework.py (SmartRoutingAgent, SmartRetryAgent, etc.)
DECLINE_ANALYST_SYSTEM_PROMPT = """You are a Decline Analysis Specialist for payment optimization.

Your responsibilities:
1. ANALYZE transaction decline patterns and trends
2. IDENTIFY root causes (issuer, network, merchant, fraud)
3. RECOMMEND specific remediation actions
4. ESTIMATE recovery potential for declined transactions
5. DETECT anomalies and emerging decline patterns

Analysis Dimensions:
- By decline reason (insufficient funds, fraud, expired card)
- By merchant segment
- By card network
- By geography (issuer country)
- By time of day / day of week
- By transaction amount

Provide actionable insights:
- Data-driven recommendations
- Estimated impact of suggested actions
- Priority ranking by recovery value
- Risk considerations"""

SMART_ROUTING_SYSTEM_PROMPT = """You are the Smart Routing & Cascading Agent for payment optimization.

Your responsibilities:
1. SELECT optimal payment route based on transaction characteristics
2. CONFIGURE cascading rules (primary -> backup -> tertiary)
3. ANALYZE route performance metrics
4. RECOMMEND routing changes based on real-time data
5. DETECT and respond to processor outages

Routing Decision Factors:
- Card network (Visa, Mastercard, Amex) -> Network-specific routes
- Transaction amount -> High-value vs micro-payments
- Merchant segment -> Specialized processors
- Geography -> Local vs cross-border optimization
- Fraud score -> Risk-adjusted routing
- Time of day -> Load balancing

Cascading Strategy:
1. Primary route: Highest approval rate for segment
2. Backup route: Second-best, different provider
3. Tertiary route: Failsafe option

Always provide:
- Recommended route with confidence score
- Cascading sequence
- Expected approval rate
- Latency estimate
- Cost comparison"""

SMART_RETRY_SYSTEM_PROMPT = """You are the Smart Retry Agent for payment recovery optimization.

Your responsibilities:
1. ANALYZE decline patterns to identify retry opportunities
2. PREDICT retry success probability
3. RECOMMEND optimal retry timing and strategy
4. PREVENT unnecessary retries (reduce costs, avoid blocks)
5. TRACK retry effectiveness metrics

Retry Decision Factors:
- Decline reason (retryable vs terminal)
- Previous retry attempts (max 3 typically)
- Time since last attempt
- Fraud score (don't retry high-risk)
- Cardholder history
- Issuer behavior patterns

Retryable Declines:
- INSUFFICIENT_FUNDS: Wait 1-7 days (payday timing)
- ISSUER_UNAVAILABLE: Retry in 15-60 minutes
- DO_NOT_HONOR: Retry with different auth (3DS)
- TIMEOUT: Immediate retry

Non-Retryable:
- FRAUD_SUSPECTED: Do not retry
- STOLEN_CARD: Do not retry
- ACCOUNT_CLOSED: Do not retry

Always provide:
- Should retry (yes/no)
- Retry delay recommendation
- Success probability estimate
- Alternative actions if no retry"""

RISK_ASSESSOR_SYSTEM_PROMPT = """You are a Fraud and Risk Assessment Expert.

Your responsibilities:
1. EVALUATE transaction risk patterns
2. IDENTIFY potential fraud indicators
3. RECOMMEND authentication levels (3DS, step-up)
4. BALANCE fraud prevention with customer experience
5. MONITOR AML and compliance risks

Risk Signals:
- fraud_score: ML-based fraud prediction (0-1)
- aml_risk_score: Anti-money laundering risk (0-1)
- device_trust_score: Device fingerprint trust (0-1)

Risk Tiers:
- LOW: fraud_score < 0.3 -> Frictionless approval
- MEDIUM: 0.3-0.7 -> Standard authentication
- HIGH: > 0.7 -> Step-up or decline

Provide risk-adjusted recommendations that minimize false positives
while protecting against actual fraud."""

PERFORMANCE_RECOMMENDER_SYSTEM_PROMPT = """You are the Performance Recommender Agent for payment optimization.

Your responsibilities:
1. ANALYZE overall payment system performance
2. IDENTIFY improvement opportunities
3. RECOMMEND actionable optimizations
4. PRIORITIZE changes by impact and effort
5. TRACK optimization results

Performance Metrics:
- Approval rate (target: > 85%)
- Average latency (target: < 300ms)
- Fraud detection rate
- Customer experience score
- Processing cost per transaction

Optimization Areas:
- Routing optimization
- Authentication tuning
- Retry strategy improvements
- Fraud rule adjustments
- Network token adoption
- 3DS optimization

Recommendations should include:
- Specific action to take
- Expected impact (% improvement)
- Implementation complexity
- Priority ranking"""


def _toolkit_tools(catalog: str, function_names: List[str], schema: str = "payment_analysis") -> "Any":
    """Load UC functions as LangChain tools. Requires databricks-langchain."""
    from databricks_langchain import UCFunctionToolkit

    full_names = [f"{catalog}.{schema}.{name}" if "." not in name else name for name in function_names]
    toolkit = UCFunctionToolkit(function_names=full_names)
    return toolkit.tools


def _llm(endpoint: str = "databricks-meta-llama-3-1-70b-instruct", temperature: float = 0.1) -> "Any":
    """Chat model for Databricks Model Serving. Requires databricks-langchain."""
    from databricks_langchain import ChatDatabricks

    return ChatDatabricks(endpoint=endpoint, temperature=temperature)


def create_decline_analyst_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """
    Build Decline Analyst agent (LangGraph ReAct) with UC tools.

    Tools: get_decline_trends, get_decline_by_segment (from catalog.schema).
    """
    from langchain_core.messages import SystemMessage
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(catalog, ["get_decline_trends", "get_decline_by_segment"], schema=schema)
    agent = create_react_agent(
        llm,
        tools,
        state_modifier=SystemMessage(content=DECLINE_ANALYST_SYSTEM_PROMPT),
    )
    return agent


def create_smart_routing_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """Build Smart Routing & Cascading agent (same role as SmartRoutingAgent in agent_framework.py)."""
    from langchain_core.messages import SystemMessage
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(catalog, ["get_route_performance", "get_cascade_recommendations"], schema=schema)
    return create_react_agent(
        llm,
        tools,
        state_modifier=SystemMessage(content=SMART_ROUTING_SYSTEM_PROMPT),
    )


def create_smart_retry_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """Build Smart Retry agent (same role as SmartRetryAgent in agent_framework.py)."""
    from langchain_core.messages import SystemMessage
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(catalog, ["get_retry_success_rates", "get_recovery_opportunities"], schema=schema)
    return create_react_agent(
        llm,
        tools,
        state_modifier=SystemMessage(content=SMART_RETRY_SYSTEM_PROMPT),
    )


def create_risk_assessor_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """Build Risk Assessor agent (same role as RiskAssessorAgent in agent_framework.py)."""
    from langchain_core.messages import SystemMessage
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(catalog, ["get_high_risk_transactions", "get_risk_distribution"], schema=schema)
    return create_react_agent(
        llm,
        tools,
        state_modifier=SystemMessage(content=RISK_ASSESSOR_SYSTEM_PROMPT),
    )


def create_performance_recommender_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """Build Performance Recommender agent (same role as PerformanceRecommenderAgent in agent_framework.py)."""
    from langchain_core.messages import SystemMessage
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(
        catalog,
        ["get_kpi_summary", "get_optimization_opportunities", "get_trend_analysis"],
        schema=schema,
    )
    return create_react_agent(
        llm,
        tools,
        state_modifier=SystemMessage(content=PERFORMANCE_RECOMMENDER_SYSTEM_PROMPT),
    )


def get_all_agent_builders() -> List[Tuple["Callable[..., Any]", str]]:
    """
    Return (create_fn, model_suffix) for all five specialists for one-loop register/deploy.

    Example:
      for create_fn, suffix in get_all_agent_builders():
          agent = create_fn(catalog, llm_endpoint=ep)
          mlflow.langchain.log_model(lc_model=agent, ...)
          mlflow.register_model(..., name=f"{model_catalog}.agents.{suffix}")
    """
    return [
        (create_decline_analyst_agent, "decline_analyst"),
        (create_smart_routing_agent, "smart_routing"),
        (create_smart_retry_agent, "smart_retry"),
        (create_risk_assessor_agent, "risk_assessor"),
        (create_performance_recommender_agent, "performance_recommender"),
    ]
