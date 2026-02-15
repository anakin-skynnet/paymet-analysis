"""
Mosaic AI Agent Framework: Payment Analysis ResponsesAgent

OpenAI Responses API agent using databricks-openai and Unity Catalog tools.
Follows the Mosaic AI Agent Framework best practices:
- ResponsesAgent (MLflow 3.x) for Databricks Model Serving compatibility
- UCFunctionToolkit for Unity Catalog tool integration
- Streaming support via predict_stream
- Backoff for rate-limit handling
- Session tracking via MLflow tracing

Based on: https://docs.databricks.com/generative-ai/agent-framework/author-agent

Env vars (set via Model Serving environment_vars):
  CATALOG, SCHEMA, LLM_ENDPOINT
"""

import json
import os
import warnings
from typing import Any, Callable, Generator, Optional
from uuid import uuid4

import backoff
import mlflow
import openai
from databricks.sdk import WorkspaceClient
from databricks_openai import DatabricksOpenAI, UCFunctionToolkit
from mlflow.entities import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)
from openai import OpenAI
from pydantic import BaseModel
from unitycatalog.ai.core.base import get_uc_function_client


# ---------------------------------------------------------------------------
# Configuration (from env or defaults)
# ---------------------------------------------------------------------------
# The ResponsesAgent (agent.py) is a single unified agent — use specialist tier
# (balanced speed/quality) by default. Falls back to LLM_ENDPOINT for compat.
LLM_ENDPOINT_NAME = os.environ.get(
    "LLM_ENDPOINT_SPECIALIST",
    os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4-5"),
)
CATALOG = os.environ.get("CATALOG", "ahs_demos_catalog")
SCHEMA = os.environ.get("SCHEMA", "payment_analysis")

# ---------------------------------------------------------------------------
# System prompt — covers all five specialist domains so the single agent
# can route any payment-analytics question to the appropriate UC tools.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""You are the Payment Analysis AI Agent — an expert in payment optimization, decline analysis, fraud/risk assessment, smart routing, smart retry, and performance recommendations.

You have access to real-time payment data, operational incidents, approval rules, similar-transaction search, and decision outcomes via Unity Catalog tools. Always use the tools to ground your answers in actual data before providing analysis.

## Your Capabilities

### Decline Analysis
- Analyze decline trends and root causes (issuer, network, merchant, fraud)
- Break down declines by merchant segment
- Estimate recovery potential and recommend remediation actions

### Smart Routing & Cascading
- Analyze route performance (approval rates, latency) by payment solution and card network
- Recommend optimal cascade configurations per merchant segment
- Detect and respond to processor performance issues

### Smart Retry & Recovery
- Evaluate retry success rates by decline reason and attempt count
- Identify high-value recovery opportunities worth retrying
- Recommend optimal retry timing and strategy

### Risk & Fraud Assessment
- Identify high-risk transactions requiring review
- Analyze risk score distribution across tiers (LOW, MEDIUM, HIGH)
- Balance fraud prevention with customer experience

### Performance Optimization
- Provide executive KPI summaries (approval rate, volume, fraud score)
- Identify optimization opportunities by routing and geography
- Track performance trends over time

### Lakebase & Operational Context (NEW)
- **Incidents & Feedback**: Check get_recent_incidents() for active MID failures, BIN anomalies, route issues, and fraud spikes reported by operations teams. Incorporate these into your analysis — e.g., if there's an open incident for a gateway, factor that into routing recommendations.
- **Approval Rules**: Use get_active_approval_rules() to understand current business policies before recommending changes. Don't suggest rules that already exist.
- **Online Features**: Use get_online_features() to see real-time ML scores and agent-generated features from the last 24 hours.
- **Decision Outcomes**: Use get_decision_outcomes() to evaluate whether past decisions (auth, retry, routing) are working. This closes the learning loop.

### Vector Search (Similar Transactions)
- Use search_similar_transactions() for RAG: find historical transactions similar to the current pattern and learn from their outcomes.
- When analyzing a specific decline pattern, search for similar past cases to see what worked.

### Recommendations (Write-Back)
- After completing analysis, persist your top recommendation using system.ai.python_exec.
- Use this exact pattern to INSERT into the approval_recommendations table:
  ```
  import uuid; spark.sql(f"INSERT INTO {CATALOG}.{SCHEMA}.approval_recommendations VALUES ('{{uuid.uuid4()}}', '<context_summary>', '<recommended_action>', <score>, '<source_type>')")
  ```
- source_type should identify the agent (e.g. "agent", "decline_analyst", "routing_agent")
- score is a confidence value between 0.0 and 1.0

## Guidelines
- Always call the relevant tool(s) FIRST, then analyze the results
- **Always check get_recent_incidents() for open incidents** that affect your analysis
- **Always check get_active_approval_rules()** before recommending new rules to avoid duplicates
- When recommending actions, search for similar past transactions to validate your recommendations
- Provide data-driven recommendations with estimated impact
- Use tables and structured formatting for clarity
- When multiple domains are relevant, address each systematically
- Mention the data freshness (e.g. "last 7 days", "last 30 days") based on tool results
- Catalog: {CATALOG}, Schema: {SCHEMA}
"""


# ---------------------------------------------------------------------------
# Tool infrastructure (matches reference notebook pattern)
# ---------------------------------------------------------------------------
class ToolInfo(BaseModel):
    """Tool specification + execution function."""

    name: str
    spec: dict
    exec_fn: Callable

    class Config:
        arbitrary_types_allowed = True


def create_tool_info(
    tool_spec: dict, exec_fn_param: Optional[Callable] = None
) -> ToolInfo:
    """Factory to create ToolInfo from a UC toolkit tool spec."""
    # Remove 'strict' property (unsupported by some models)
    tool_spec.get("function", {}).pop("strict", None)
    tool_name = tool_spec["function"]["name"]
    # UC double-underscore convention -> dot notation
    udf_name = tool_name.replace("__", ".")

    def exec_fn(**kwargs: Any) -> Any:
        result = uc_function_client.execute_function(udf_name, kwargs)
        return result.error if result.error is not None else result.value

    return ToolInfo(
        name=tool_name, spec=tool_spec, exec_fn=exec_fn_param or exec_fn
    )


# ---------------------------------------------------------------------------
# Register all payment-analysis UC tools
# ---------------------------------------------------------------------------
TOOL_INFOS: list[ToolInfo] = []

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

uc_function_client = get_uc_function_client()
uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)
for tool_spec in uc_toolkit.tools:
    TOOL_INFOS.append(create_tool_info(tool_spec))


# ---------------------------------------------------------------------------
# ResponsesAgent implementation
# ---------------------------------------------------------------------------
class PaymentAnalysisAgent(ResponsesAgent):
    """
    Payment Analysis tool-calling agent.

    Uses the OpenAI Responses API via Databricks Model Serving FMAPI.
    Handles tool execution via UC functions and LLM interactions via streaming.
    """

    def __init__(self, llm_endpoint: str, tools: list[ToolInfo]):
        self.llm_endpoint = llm_endpoint
        self.workspace_client = WorkspaceClient()
        # DatabricksOpenAI auto-configures host/token from the Databricks environment
        self.model_serving_client: OpenAI = DatabricksOpenAI()
        self._tools_dict = {tool.name: tool for tool in tools}

    def get_tool_specs(self) -> list[dict]:
        """Return tool specifications in the format OpenAI expects."""
        return [t.spec for t in self._tools_dict.values()]

    @mlflow.trace(span_type=SpanType.TOOL)
    def execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute the named UC tool with given arguments."""
        return self._tools_dict[tool_name].exec_fn(**args)

    @backoff.on_exception(backoff.expo, openai.RateLimitError)
    @mlflow.trace(span_type=SpanType.LLM)
    def call_llm(
        self, messages: list[dict[str, Any]]
    ) -> Generator[dict[str, Any], None, None]:
        """Stream LLM response chunks from Databricks FMAPI."""
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="PydanticSerializationUnexpectedValue"
            )
            for chunk in self.model_serving_client.chat.completions.create(
                model=self.llm_endpoint,
                messages=to_chat_completions_input(messages),
                tools=self.get_tool_specs(),
                stream=True,
            ):
                yield chunk.to_dict()

    def handle_tool_call(
        self,
        tool_call: dict[str, Any],
        messages: list[dict[str, Any]],
    ) -> ResponsesAgentStreamEvent:
        """Execute a tool call, append result to message history, and return stream event."""
        raw_args = tool_call.get("arguments") or "{}"
        args = json.loads(raw_args)
        result = str(self.execute_tool(tool_name=tool_call["name"], args=args))

        tool_call_output = self.create_function_call_output_item(
            tool_call["call_id"], result
        )
        messages.append(tool_call_output)
        return ResponsesAgentStreamEvent(
            type="response.output_item.done", item=tool_call_output
        )

    def call_and_run_tools(
        self,
        messages: list[dict[str, Any]],
        max_iter: int = 10,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Iteratively call LLM and execute tools until the agent produces a final response."""
        for _ in range(max_iter):
            last_msg = messages[-1]
            if last_msg.get("role", None) == "assistant":
                return
            elif last_msg.get("type", None) == "function_call":
                yield self.handle_tool_call(last_msg, messages)
            else:
                yield from output_to_responses_items_stream(
                    chunks=self.call_llm(messages), aggregator=messages
                )

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(
                "Max iterations reached. Stopping.", str(uuid4())
            ),
        )

    def predict(
        self, request: ResponsesAgentRequest
    ) -> ResponsesAgentResponse:
        """Collect all stream events into a single ResponsesAgentResponse."""
        session_id = None
        if request.custom_inputs and "session_id" in request.custom_inputs:
            session_id = request.custom_inputs.get("session_id")
        elif request.context and request.context.conversation_id:
            session_id = request.context.conversation_id

        if session_id:
            mlflow.update_current_trace(
                metadata={"mlflow.trace.session": session_id}
            )

        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(
            output=outputs, custom_outputs=request.custom_inputs
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Invoke the agent and yield Responses-API stream events."""
        session_id = None
        if request.custom_inputs and "session_id" in request.custom_inputs:
            session_id = request.custom_inputs.get("session_id")
        elif request.context and request.context.conversation_id:
            session_id = request.context.conversation_id

        if session_id:
            mlflow.update_current_trace(
                metadata={"mlflow.trace.session": session_id}
            )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            i.model_dump() for i in request.input
        ]
        yield from self.call_and_run_tools(messages=messages)


# ---------------------------------------------------------------------------
# MLflow model registration
# ---------------------------------------------------------------------------
mlflow.openai.autolog()
AGENT = PaymentAnalysisAgent(llm_endpoint=LLM_ENDPOINT_NAME, tools=TOOL_INFOS)
mlflow.models.set_model(AGENT)
