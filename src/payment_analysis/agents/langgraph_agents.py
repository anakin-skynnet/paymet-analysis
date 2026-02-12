"""
Databricks AgentBricks (code-based): LangGraph + UC functions.

Converts the payment analysis Python agents (agent_framework.py) to a production-ready
Mosaic AI Agent Framework / AgentBricks setup:
- Five specialist agents: LangGraph ReAct + UC functions (tool-calling agents).
- Supervisor/orchestrator: LangGraph multi-agent graph with LLM router that selects
  which specialists to run, runs only those, then synthesizes—aligned with AgentBricks
  Supervisor Agent patterns. Deployable via MLflow + Unity Catalog and Model Serving.

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


def _llm(endpoint: str = "databricks-meta-llama-3-3-70b-instruct", temperature: float = 0.1) -> "Any":
    """Chat model for Databricks Model Serving. Requires databricks-langchain."""
    from databricks_langchain import ChatDatabricks

    return ChatDatabricks(endpoint=endpoint, temperature=temperature)


def create_decline_analyst_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """
    Build Decline Analyst agent (LangGraph ReAct) with UC tools.

    Tools: get_decline_trends, get_decline_by_segment (from catalog.schema).
    """
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(catalog, ["get_decline_trends", "get_decline_by_segment"], schema=schema)
    agent = create_react_agent(
        llm,
        tools,
        prompt=DECLINE_ANALYST_SYSTEM_PROMPT),
    )
    return agent


def create_smart_routing_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """Build Smart Routing & Cascading agent (same role as SmartRoutingAgent in agent_framework.py)."""
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(catalog, ["get_route_performance", "get_cascade_recommendations"], schema=schema)
    return create_react_agent(
        llm,
        tools,
        prompt=SMART_ROUTING_SYSTEM_PROMPT),
    )


def create_smart_retry_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """Build Smart Retry agent (same role as SmartRetryAgent in agent_framework.py)."""
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(catalog, ["get_retry_success_rates", "get_recovery_opportunities"], schema=schema)
    return create_react_agent(
        llm,
        tools,
        prompt=SMART_RETRY_SYSTEM_PROMPT),
    )


def create_risk_assessor_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """Build Risk Assessor agent (same role as RiskAssessorAgent in agent_framework.py)."""
    from langgraph.prebuilt import create_react_agent

    llm = _llm(endpoint=llm_endpoint, temperature=temperature)
    tools = _toolkit_tools(catalog, ["get_high_risk_transactions", "get_risk_distribution"], schema=schema)
    return create_react_agent(
        llm,
        tools,
        prompt=RISK_ASSESSOR_SYSTEM_PROMPT),
    )


def create_performance_recommender_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """Build Performance Recommender agent (same role as PerformanceRecommenderAgent in agent_framework.py)."""
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
        prompt=PERFORMANCE_RECOMMENDER_SYSTEM_PROMPT),
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


# -----------------------------------------------------------------------------
# Supervisor / Orchestrator as LangGraph Multi-Agent System (AgentBricks-style)
# -----------------------------------------------------------------------------

SUPERVISOR_ROUTER_PROMPT = """You are the Payment Analysis Supervisor. Your job is to decide which specialist agents should handle the user query.

Available specialists (use exactly these names):
- decline_analyst: Decline pattern analysis, root causes, recovery potential
- smart_routing: Payment routing, cascading, route performance
- smart_retry: Retry decisions, retry success rates, recovery opportunities
- risk_assessor: Fraud and risk assessment, 3DS, AML
- performance_recommender: KPIs, optimization opportunities, overall recommendations

Respond with a JSON array of specialist names to invoke. Use ["decline_analyst", "smart_routing", ...] or ["all"] for comprehensive analysis.
Reply with ONLY the JSON array, no other text."""

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Payment Analysis Orchestrator. You coordinate specialist agents and synthesize their findings into one clear response.

Given the specialist outputs below, produce a concise synthesis that:
1. Summarizes the key findings from each specialist
2. Highlights the most important recommendations
3. Prioritizes actions by impact
4. Keeps the response actionable and under 500 words"""


def create_orchestrator_agent(
    catalog: str,
    *,
    schema: str = "payment_analysis",
    llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct",
    temperature: float = 0.1,
) -> "Any":
    """
    Build Supervisor-style Orchestrator as a LangGraph Multi-Agent System:
    (1) Router: LLM selects which specialist(s) to run from the user query.
    (2) Run specialists: Invoke only the selected agents.
    (3) Synthesize: Single response from specialist outputs.
    Returns a compiled graph suitable for MLflow and AgentBricks deployment.
    """
    import json
    import re
    from typing import Annotated, Any, TypedDict

    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
    from langgraph.graph import END, StateGraph
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import create_react_agent

    SPECIALIST_KEYS = [
        "decline_analyst",
        "smart_routing",
        "smart_retry",
        "risk_assessor",
        "performance_recommender",
    ]
    SPECIALIST_BUILDERS = [
        create_decline_analyst_agent,
        create_smart_routing_agent,
        create_smart_retry_agent,
        create_risk_assessor_agent,
        create_performance_recommender_agent,
    ]
    NAME_TO_BUILDER = dict(zip(SPECIALIST_KEYS, SPECIALIST_BUILDERS))

    class OrchestratorState(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
        specialist_responses: dict[str, str]
        query: str
        selected_specialists: list[str]

    catalog_arg = catalog
    schema_arg = schema
    llm_endpoint_arg = llm_endpoint

    def _last_ai_content(messages: list) -> str:
        for m in reversed(messages):
            if isinstance(m, AIMessage) and m.content:
                return m.content if isinstance(m.content, str) else str(m.content)
        return ""

    def _parse_router_output(text: str) -> list[str]:
        """Parse LLM router output to list of specialist names. Default to all if invalid."""
        text = (text or "").strip()
        # Try to find a JSON array in the response
        match = re.search(r"\[[\s\S]*?\]", text)
        if match:
            try:
                names = json.loads(match.group())
                if isinstance(names, list) and names:
                    if names == ["all"] or "all" in [str(n).strip().lower() for n in names]:
                        return list(SPECIALIST_KEYS)
                    valid = [n for n in names if isinstance(n, str) and n.strip().lower() in SPECIALIST_KEYS]
                    if valid:
                        return [n.strip().lower() for n in valid]
            except (json.JSONDecodeError, TypeError):
                pass
        return list(SPECIALIST_KEYS)

    def _entry(state: OrchestratorState) -> dict[str, Any]:
        msgs = state.get("messages") or []
        query = str(state.get("query") or "").strip()
        for m in reversed(msgs):
            if isinstance(m, HumanMessage) and m.content:
                query = m.content if isinstance(m.content, str) else str(m.content)
                break
        return {
            "query": query or "Run payment analysis.",
            "specialist_responses": dict(state.get("specialist_responses") or {}),
            "selected_specialists": list(state.get("selected_specialists") or []),
        }

    def _node_router(state: OrchestratorState) -> dict[str, Any]:
        """Supervisor router: LLM selects which specialists to run."""
        llm = _llm(endpoint=llm_endpoint_arg, temperature=0.0)
        router_agent = create_react_agent(
            llm,
            [],
            prompt=SUPERVISOR_ROUTER_PROMPT),
        )
        result = router_agent.invoke({
            "messages": [HumanMessage(content=f"User query: {state['query']}\n\nWhich specialists should run? Reply with JSON array only.")],
        })
        raw = _last_ai_content(result.get("messages") or [])
        selected = _parse_router_output(raw)
        return {"selected_specialists": selected}

    def _node_run_specialists(state: OrchestratorState) -> dict[str, Any]:
        """Run only the selected specialist agents and merge responses."""
        to_run = state.get("selected_specialists") or SPECIALIST_KEYS
        responses = dict(state.get("specialist_responses") or {})
        for name in to_run:
            if name not in NAME_TO_BUILDER:
                continue
            create_fn = NAME_TO_BUILDER[name]
            agent = create_fn(catalog_arg, schema=schema_arg, llm_endpoint=llm_endpoint_arg)
            result = agent.invoke({"messages": [HumanMessage(content=state["query"])]})
            out = _last_ai_content(result.get("messages") or [])
            responses[name] = out
        return {"specialist_responses": responses}

    def _node_synthesize(state: OrchestratorState) -> dict[str, Any]:
        parts = [f"[{k}]\n{v}" for k, v in (state.get("specialist_responses") or {}).items() if v]
        context = "\n\n".join(parts) or "No specialist output."
        llm = _llm(endpoint=llm_endpoint_arg, temperature=temperature)
        synthesizer = create_react_agent(
            llm,
            [],
            prompt=ORCHESTRATOR_SYSTEM_PROMPT),
        )
        result = synthesizer.invoke({
            "messages": [
                HumanMessage(content=f"Query: {state['query']}\n\nSpecialist outputs:\n{context}\n\nProduce a concise synthesis."),
            ],
        })
        synthesis = _last_ai_content(result.get("messages") or [])
        return {
            "messages": [AIMessage(content=synthesis or "No synthesis.")],
        }

    builder = StateGraph(OrchestratorState)
    builder.add_node("__entry__", _entry)
    builder.add_node("router", _node_router)
    builder.add_node("run_specialists", _node_run_specialists)
    builder.add_node("synthesize", _node_synthesize)

    builder.set_entry_point("__entry__")
    builder.add_edge("__entry__", "router")
    builder.add_edge("router", "run_specialists")
    builder.add_edge("run_specialists", "synthesize")
    builder.add_edge("synthesize", END)

    return builder.compile()


def get_notebook_config() -> "dict[str, Any]":
    """Read job/notebook parameters from Databricks widgets or return defaults (same interface as agent_framework.py)."""
    from typing import Any

    defaults: dict[str, Any] = {
        "catalog": "ahs_demos_catalog",
        "schema": "payment_analysis",
        "query": "Run comprehensive payment analysis: routing, retries, declines, risk, and performance optimizations.",
        "agent_role": "orchestrator",
        "llm_endpoint": "databricks-meta-llama-3-3-70b-instruct",
    }
    try:
        from databricks.sdk.runtime import dbutils

        dbutils.widgets.text("catalog", defaults["catalog"])
        dbutils.widgets.text("schema", defaults["schema"])
        dbutils.widgets.text("query", defaults["query"])
        dbutils.widgets.text("agent_role", defaults["agent_role"])
        dbutils.widgets.text("llm_endpoint", defaults["llm_endpoint"])
        return {
            "catalog": (dbutils.widgets.get("catalog") or defaults["catalog"]).strip(),
            "schema": (dbutils.widgets.get("schema") or defaults["schema"]).strip(),
            "query": (dbutils.widgets.get("query") or defaults["query"]).strip(),
            "agent_role": (dbutils.widgets.get("agent_role") or defaults["agent_role"]).strip().lower(),
            "llm_endpoint": (dbutils.widgets.get("llm_endpoint") or defaults["llm_endpoint"]).strip()
            or "databricks-meta-llama-3-3-70b-instruct",
        }
    except Exception:
        return defaults


def run_agentbricks(config: "dict[str, Any]") -> "dict[str, Any]":
    """
    Run AgentBricks agents: LangGraph specialists with UC tools.
    Same return shape as agent_framework.run_framework for Job 6 / orchestrator chat API.
    """
    from typing import Any

    from langchain_core.messages import AIMessage, HumanMessage

    catalog = config["catalog"]
    schema = config.get("schema") or "payment_analysis"
    query = config["query"]
    agent_role = (config.get("agent_role") or "orchestrator").strip().lower()
    llm_endpoint = (config.get("llm_endpoint") or "databricks-meta-llama-3-3-70b-instruct").strip()

    def _invoke_agent(agent: Any, q: str) -> str:
        result = agent.invoke({"messages": [HumanMessage(content=q)]})
        messages = result.get("messages") or []
        for m in reversed(messages):
            if isinstance(m, AIMessage) and m.content:
                return m.content if isinstance(m.content, str) else str(m.content)
        return ""

    if agent_role == "orchestrator":
        # Use the compiled supervisor graph (router → run_specialists → synthesize)
        orchestrator = create_orchestrator_agent(catalog, schema=schema, llm_endpoint=llm_endpoint)
        out = orchestrator.invoke({"messages": [HumanMessage(content=query)]})
        specialist_responses = out.get("specialist_responses") or {}
        agents_used = list(specialist_responses.keys())
        synthesis = ""
        for m in reversed(out.get("messages") or []):
            if isinstance(m, AIMessage) and m.content:
                synthesis = m.content if isinstance(m.content, str) else str(m.content)
                break
        return {
            "query": query,
            "agents_used": agents_used,
            "agent_responses": specialist_responses,
            "synthesis": synthesis or "No response from agents.",
        }

    specialist_map = {
        "smart_routing": create_smart_routing_agent,
        "smart_retry": create_smart_retry_agent,
        "decline_analyst": create_decline_analyst_agent,
        "risk_assessor": create_risk_assessor_agent,
        "performance_recommender": create_performance_recommender_agent,
    }
    create_fn = specialist_map.get(agent_role)
    if create_fn:
        agent = create_fn(catalog, schema=schema, llm_endpoint=llm_endpoint)
        response = _invoke_agent(agent, query)
        return {
            "query": query,
            "agents_used": [agent_role],
            "agent_responses": {agent_role: response},
            "synthesis": response or "No response.",
        }
    raise ValueError(
        f"Unknown agent_role={agent_role!r}. Use one of: orchestrator, {', '.join(specialist_map)}"
    )


# Databricks notebook entry point (Job 6: Deploy AgentBricks agents)
if __name__ == "__main__":
    import json

    config = get_notebook_config()
    query = config["query"]
    agent_role = config["agent_role"]

    print("\n" + "=" * 70)
    print("Payment Analysis — AgentBricks (LangGraph + UC tools)")
    print("=" * 70)
    print(f"Mode:    {agent_role}")
    print(f"Query:   {query}")
    print("=" * 70)

    result = run_agentbricks(config)

    print("\nAgents used:", result.get("agents_used", []))
    print("\n--- Synthesis ---")
    print(result.get("synthesis", ""))
    print("\n--- Done ---")

    try:
        from databricks.sdk.runtime import dbutils

        payload = json.dumps({
            "synthesis": result.get("synthesis", ""),
            "agents_used": result.get("agents_used", []),
        })
        dbutils.notebook.exit(payload)  # type: ignore[call-arg]
    except Exception:
        pass
