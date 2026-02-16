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

### Decline Analysis — use analyze_declines(mode, ...)
- mode='trends': Decline trends and root causes (issuer, network, merchant, fraud)
- mode='by_segment': Declines broken down by merchant segment with recovery potential

### Smart Routing & Cascading — use analyze_routing(mode, ...)
- mode='performance': Route approval rates and latency by payment solution and card network
- mode='cascade': Optimal cascade configurations per merchant segment

### Smart Retry & Recovery — use analyze_retry(mode, ...)
- mode='success_rates': Retry success rates by decline reason and attempt count
- mode='opportunities': High-value recovery opportunities worth retrying

### Risk & Fraud Assessment — use analyze_risk(mode, ...)
- mode='distribution': Risk score distribution across tiers (LOW, MEDIUM, HIGH)
- mode='transactions': High-risk transactions requiring review

### Performance Optimization — use analyze_performance(mode, ...)
- mode='kpi': Executive KPI summaries (approval rate, volume, fraud score)
- mode='opportunities': Optimization opportunities by routing and geography
- mode='trends': Performance trends over time

### Lakebase & Operational Context (NEW)
- **Incidents & Feedback**: Check get_recent_incidents() for active MID failures, BIN anomalies, route issues, and fraud spikes reported by operations teams. Incorporate these into your analysis — e.g., if there's an open incident for a gateway, factor that into routing recommendations.
- **Approval Rules**: Use get_active_approval_rules() to understand current business policies before recommending changes. Don't suggest rules that already exist.
- **Decision Outcomes**: Use get_decision_outcomes() to evaluate whether past decisions (auth, retry, routing) are working. This closes the learning loop.

### Vector Search (Similar Transactions)
- Use search_similar_transactions() for RAG: find historical transactions similar to the current pattern and learn from their outcomes.
- When analyzing a specific decline pattern, search for similar past cases to see what worked.

### Recommendations (Write-Back)
- After completing analysis, persist your top recommendation using system.ai.python_exec.
- Use this exact parameterized pattern (prevents SQL injection from generated content):
  ```
  import uuid
  rec_id = str(uuid.uuid4())
  context = "<context_summary>"        # plain text, no quotes or special chars
  action = "<recommended_action>"      # plain text
  score = 0.85                         # float between 0.0 and 1.0
  source = "<source_type>"             # e.g. "agent", "decline_analyst", "routing_agent"
  spark.sql(
      "INSERT INTO {CATALOG}.{SCHEMA}.approval_recommendations VALUES (?, ?, ?, ?, ?)",
      args=[rec_id, context, action, score, source]
  )
  ```
  IMPORTANT: Always use spark.sql() with the `args` parameter for safe parameterized insertion.
  Never use f-strings or string concatenation for user-generated values in SQL.
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
    # 5 consolidated analytics functions (each supports a mode parameter for different analysis types).
    # Databricks enforces a 10 UC-function limit per agent — consolidation keeps us within budget.
    f"{CATALOG}.{SCHEMA}.analyze_declines",       # mode: trends | by_segment
    f"{CATALOG}.{SCHEMA}.analyze_routing",         # mode: performance | cascade
    f"{CATALOG}.{SCHEMA}.analyze_retry",           # mode: success_rates | opportunities
    f"{CATALOG}.{SCHEMA}.analyze_risk",            # mode: distribution | transactions
    f"{CATALOG}.{SCHEMA}.analyze_performance",     # mode: kpi | opportunities | trends
    # 5 shared operational context functions
    f"{CATALOG}.{SCHEMA}.get_active_approval_rules",
    f"{CATALOG}.{SCHEMA}.get_recent_incidents",
    f"{CATALOG}.{SCHEMA}.search_similar_transactions",
    f"{CATALOG}.{SCHEMA}.get_approval_recommendations",
    f"{CATALOG}.{SCHEMA}.get_decision_outcomes",
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
        # DatabricksOpenAI auto-configures host/token from the Databricks environment
        self.model_serving_client: OpenAI = DatabricksOpenAI()
        self._tools_dict = {tool.name: tool for tool in tools}
        # Cache tool specs at init (avoids rebuilding on every LLM call)
        self._tool_specs_cache: list[dict] = [t.spec for t in self._tools_dict.values()]

    def get_tool_specs(self) -> list[dict]:
        """Return cached tool specifications in the format OpenAI expects."""
        return self._tool_specs_cache

    @mlflow.trace(span_type=SpanType.TOOL)
    def execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute the named UC tool with given arguments. Returns error string on failure."""
        try:
            return self._tools_dict[tool_name].exec_fn(**args)
        except KeyError:
            return f"Error: unknown tool '{tool_name}'"
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

    @backoff.on_exception(backoff.expo, (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError), max_tries=3)
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
        try:
            args = json.loads(raw_args)
        except (json.JSONDecodeError, TypeError) as e:
            args = {}
            result = f"Error: invalid tool arguments — {e}"
        else:
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
        """Iteratively call LLM and execute tools until the agent produces a final response.

        The ``output_to_responses_items_stream`` helper (MLflow) can raise
        ``json.JSONDecodeError`` when the LLM streams a tool-call chunk with
        empty arguments (race between chunk assembly and parsing).  When this
        happens, we fall back to a non-streaming single-shot LLM call so the
        agent can still complete tool execution and return a result.
        """
        for iteration in range(max_iter):
            last_msg = messages[-1]
            if last_msg.get("role", None) == "assistant":
                return
            elif last_msg.get("type", None) == "function_call":
                yield self.handle_tool_call(last_msg, messages)
            else:
                try:
                    yield from output_to_responses_items_stream(
                        chunks=self.call_llm(messages), aggregator=messages
                    )
                except json.JSONDecodeError:
                    # Streaming chunk assembly failed — retry with a non-streaming call.
                    yield from self._fallback_non_streaming(messages, iteration)

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(
                "I've done extensive analysis but need to wrap up. Here's what I found so far — "
                "try asking a more focused question for deeper detail on a specific area.",
                str(uuid4()),
            ),
        )

    @mlflow.trace(span_type=SpanType.LLM, name="fallback_non_streaming")
    def _fallback_non_streaming(
        self,
        messages: list[dict[str, Any]],
        iteration: int,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Non-streaming LLM call used when the streaming parser crashes.

        Makes a single synchronous ``chat.completions.create`` call (no
        ``stream=True``) so argument assembly is atomic and not subject to
        chunked JSON-parse races.
        """
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="PydanticSerializationUnexpectedValue")
            response = self.model_serving_client.chat.completions.create(
                model=self.llm_endpoint,
                messages=to_chat_completions_input(messages),
                tools=self.get_tool_specs(),
                stream=False,
            )

        choice = response.choices[0] if response.choices else None
        if choice is None:
            return

        msg = choice.message
        # If the LLM returned tool calls, enqueue them for execution
        if msg.tool_calls:
            for tc in msg.tool_calls:
                fn = tc.function
                call_item = {
                    "type": "function_call",
                    "call_id": tc.id,
                    "name": fn.name,
                    "arguments": fn.arguments or "{}",
                }
                messages.append(call_item)
                yield self.handle_tool_call(call_item, messages)
        elif msg.content:
            # Final assistant text
            text_item = self.create_text_output_item(msg.content.strip(), str(uuid4()))
            messages.append({"role": "assistant", "content": msg.content.strip()})
            yield ResponsesAgentStreamEvent(type="response.output_item.done", item=text_item)

    @staticmethod
    def _get_session_id(request: ResponsesAgentRequest) -> Optional[str]:
        """Extract session ID from request (custom_inputs or conversation context)."""
        if request.custom_inputs and "session_id" in request.custom_inputs:
            return request.custom_inputs.get("session_id")
        if request.context and request.context.conversation_id:
            return request.context.conversation_id
        return None

    def _tag_session(self, request: ResponsesAgentRequest) -> None:
        """Tag the current MLflow trace with the session ID if available."""
        session_id = self._get_session_id(request)
        if session_id:
            mlflow.update_current_trace(
                metadata={"mlflow.trace.session": session_id}
            )

    def predict(
        self, request: ResponsesAgentRequest
    ) -> ResponsesAgentResponse:
        """Collect all stream events into a single ResponsesAgentResponse."""
        self._tag_session(request)
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
        self._tag_session(request)

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
