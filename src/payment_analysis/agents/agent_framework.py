# Databricks notebook source
# MAGIC %md
# MAGIC # AI Agent Framework for Payment Analysis Platform
# MAGIC
# MAGIC Multi-agent system for automated payment optimization:
# MAGIC - Smart Routing & Cascading Agent
# MAGIC - Smart Retry Agent
# MAGIC - Decline Analysis Agent
# MAGIC - Risk Assessment Agent
# MAGIC - Performance Recommender Agent
# MAGIC - Orchestrator Agent

# COMMAND ----------

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
import re
import threading

logger = logging.getLogger(__name__)

# Thread-safe cache for the running SQL warehouse ID (avoids listing warehouses on every SQL call)
_warehouse_cache_lock = threading.Lock()
_warehouse_cache: Dict[str, Tuple[str, float]] = {}  # key -> (warehouse_id, timestamp)
_WAREHOUSE_CACHE_TTL_S = 300  # 5 minutes


class AgentRole(Enum):
    """Agent role definitions."""
    SMART_ROUTING = "smart_routing"
    SMART_RETRY = "smart_retry"
    DECLINE_ANALYST = "decline_analyst"
    RISK_ASSESSOR = "risk_assessor"
    PERFORMANCE_RECOMMENDER = "performance_recommender"
    ORCHESTRATOR = "orchestrator"


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    role: str
    content: str
    metadata: Optional[Dict] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentTool:
    """Tool definition for agents."""
    name: str
    description: str
    function: Callable
    parameters: Dict

    def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return self.function(**kwargs)


_SQL_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_ .-]+$")


def _sanitize_sql_string(value: str, max_len: int = 128) -> str:
    """Sanitize a string value for safe SQL interpolation. Rejects anything that
    could be used for SQL injection (quotes, semicolons, comments)."""
    if not isinstance(value, str) or len(value) > max_len:
        raise ValueError(f"Invalid SQL parameter: {value!r}")
    if not _SQL_SAFE_IDENTIFIER.match(value):
        raise ValueError(f"SQL parameter contains unsafe characters: {value!r}")
    return value


def _sanitize_sql_number(value: Any, min_val: float = 0, max_val: float = 1e12) -> float:
    """Cast and clamp a numeric SQL parameter."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Expected numeric SQL parameter, got: {value!r}")
    return max(min_val, min(num, max_val))


class BaseAgent:
    """Base class for all payment analysis agents."""

    def __init__(
        self,
        role: AgentRole,
        catalog: str,
        schema: str,
        llm_endpoint: str = "databricks-claude-sonnet-4-5",
        *,
        lakebase_project_id: str = "",
        lakebase_branch_id: str = "",
        lakebase_endpoint_id: str = "",
        lakebase_schema: str = "payment_analysis",
    ):
        self.role = role
        self.catalog = catalog
        self.schema = schema
        self.llm_endpoint = llm_endpoint
        self.lakebase_project_id = (lakebase_project_id or "").strip()
        self.lakebase_branch_id = (lakebase_branch_id or "").strip()
        self.lakebase_endpoint_id = (lakebase_endpoint_id or "").strip()
        self.lakebase_schema = (lakebase_schema or "payment_analysis").strip() or "payment_analysis"
        self.status = AgentStatus.IDLE
        self.conversation_history: List[AgentMessage] = []
        self.tools: List[AgentTool] = []

    def add_tool(self, tool: AgentTool):
        """Register a tool with this agent."""
        self.tools.append(tool)

    def get_system_prompt(self) -> str:
        """Get role-specific system prompt."""
        raise NotImplementedError("Subclasses must implement get_system_prompt()")

    def think(self, user_input: str) -> str:
        """Agent reasoning step using LLM."""
        self.status = AgentStatus.THINKING

        self.conversation_history.append(
            AgentMessage(role="user", content=user_input)
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
        ]

        for msg in self.conversation_history[-10:]:
            messages.append({"role": msg.role, "content": msg.content})

        try:
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

            w = WorkspaceClient()

            response = w.serving_endpoints.query(
                name=self.llm_endpoint,
                messages=[
                    ChatMessage(
                        role=ChatMessageRole.SYSTEM if m["role"] == "system" else (
                            ChatMessageRole.USER if m["role"] == "user" else ChatMessageRole.ASSISTANT
                        ),
                        content=m["content"]
                    )
                    for m in messages
                ],
                max_tokens=2000,
                temperature=0.7
            )

            choice = response.choices[0] if response.choices else None
            msg = choice.message if choice else None
            content = (getattr(msg, "content", None) or "").strip() or ""

            self.conversation_history.append(
                AgentMessage(role="assistant", content=content)
            )

            self.status = AgentStatus.COMPLETE
            return content

        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.exception("Agent %s error during think(): %s", self.role.value, e)
            return f"Analysis temporarily unavailable ({self.role.value}). Please try again."

    def execute_tool(self, tool_name: str, **kwargs) -> Dict:
        """Execute a tool by name."""
        self.status = AgentStatus.TOOL_USE

        tool = next((t for t in self.tools if t.name == tool_name), None)

        if tool is None:
            return {"error": f"Tool '{tool_name}' not found"}

        try:
            result = tool.execute(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_sql(self, query: str) -> List[Dict]:
        """Execute SQL query and return results."""
        return self._execute_sql_parameterized(query, {})

    @staticmethod
    def _get_cached_warehouse_id() -> Optional[str]:
        """Return a cached RUNNING SQL warehouse ID, refreshing if stale.

        Only caches warehouses whose state is RUNNING. If no warehouse is
        running, returns ``None`` so the caller can handle gracefully rather
        than sending queries to a stopped warehouse.  On SQL execution
        failure the caller should call ``_invalidate_warehouse_cache()`` so
        the next attempt re-resolves.
        """
        import time as _time
        cache_key = "default"
        with _warehouse_cache_lock:
            cached = _warehouse_cache.get(cache_key)
            if cached and (_time.time() - cached[1]) < _WAREHOUSE_CACHE_TTL_S:
                return cached[0]
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            warehouses = list(w.warehouses.list())
            wh_id = next(
                (wh.id for wh in warehouses if wh.state and str(wh.state) == "RUNNING"),
                None,
            )
            if wh_id is None:
                logger.warning("No RUNNING SQL warehouse found (%d total).", len(warehouses))
                return None
            with _warehouse_cache_lock:
                _warehouse_cache[cache_key] = (wh_id, _time.time())
            return wh_id
        except Exception as e:
            logger.warning("Could not list warehouses: %s", e)
            return None

    @staticmethod
    def _invalidate_warehouse_cache() -> None:
        """Clear the warehouse cache so the next call re-resolves."""
        with _warehouse_cache_lock:
            _warehouse_cache.clear()

    def _execute_sql_parameterized(self, query: str, params: Dict[str, str]) -> List[Dict]:
        """Execute SQL query with named parameters and return results.

        Parameters use the ``:name`` syntax in the query and are passed to the
        Databricks SQL Statement API as ``StatementParameterListItem`` objects,
        which safely bind values without string interpolation.

        Uses a cached warehouse ID to avoid listing warehouses on every call.
        """
        try:
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.service.sql import StatementParameterListItem, StatementState

            warehouse_id = self._get_cached_warehouse_id()
            if not warehouse_id:
                logger.warning("No SQL warehouse available for query execution.")
                return []

            w = WorkspaceClient()
            stmt_params = [
                StatementParameterListItem(name=k, value=str(v), type="STRING")
                for k, v in params.items()
            ] if params else None

            response = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=query,
                parameters=stmt_params,
                wait_timeout="30s"
            )

            if response.status and getattr(response.status, "state", None) == StatementState.SUCCEEDED:
                manifest = response.manifest
                schema = getattr(manifest, "schema", None) if manifest else None
                cols = getattr(schema, "columns", None) if schema else None
                columns = [c.name for c in (cols or [])]
                result = response.result
                rows = getattr(result, "data_array", None) or [] if result else []
                return [dict(zip(columns, row)) for row in rows]
            # Log non-success state for debugging
            state = getattr(response.status, "state", "unknown") if response.status else "unknown"
            error_msg = getattr(getattr(response.status, "error", None), "message", "") if response.status else ""
            logger.warning("SQL statement did not succeed: state=%s error=%s", state, error_msg)
            return []
        except Exception as e:
            logger.error("SQL execution error: %s", e)
            self._invalidate_warehouse_cache()
            return []

    # -- Lakebase connection helper (shared by rules, write-back, config changes) --

    def _get_lakebase_conn_str(self) -> Optional[str]:
        """Resolve Lakebase Postgres connection string. Returns None if unavailable."""
        if not (self.lakebase_project_id and self.lakebase_branch_id and self.lakebase_endpoint_id):
            return None
        try:
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.errors import NotFound as _NotFound

            ws = WorkspaceClient()
            postgres_api = getattr(ws, "postgres", None)
            if postgres_api is None:
                logger.warning("WorkspaceClient has no 'postgres'; cannot connect to Lakebase.")
                return None

            configured_endpoint_name = (
                f"projects/{self.lakebase_project_id}/branches/{self.lakebase_branch_id}"
                f"/endpoints/{self.lakebase_endpoint_id}"
            )
            branch_path = f"projects/{self.lakebase_project_id}/branches/{self.lakebase_branch_id}"
            try:
                postgres_api.get_endpoint(name=configured_endpoint_name)
                endpoint_name = configured_endpoint_name
            except _NotFound:
                eps = list(postgres_api.list_endpoints(parent=branch_path))
                endpoint_name = getattr(eps[0], "name", configured_endpoint_name) if eps else configured_endpoint_name

            endpoint = postgres_api.get_endpoint(name=endpoint_name)
            cred = postgres_api.generate_database_credential(endpoint=endpoint_name)
            host = getattr(getattr(getattr(endpoint, "status", None), "hosts", None), "host", None)
            if not host:
                logger.warning("Lakebase endpoint has no host.")
                return None
            username = (
                (ws.current_user.me().user_name if ws.current_user else None)
                or getattr(ws.config, "client_id", None)
                or "postgres"
            )
            return (
                f"host={host} port=5432 dbname=databricks_postgres user={username} "
                f"password={cred.token} sslmode=require"
            )
        except Exception as e:
            logger.warning("Could not resolve Lakebase connection: %s", e)
            return None

    def _get_approval_rules_from_lakebase(self, rule_type: Optional[str] = None) -> List[Dict]:
        """Load active approval rules from the OLTP Lakebase Autoscaling Postgres database."""
        conn_str = self._get_lakebase_conn_str()
        if not conn_str:
            return []
        try:
            import psycopg
            from psycopg.rows import dict_row

            allowed = ("authentication", "retry", "routing")
            filter_type = rule_type if rule_type and rule_type in allowed else None
            schema_name = self.lakebase_schema or "payment_analysis"
            with psycopg.connect(conn_str, row_factory=dict_row) as conn:  # type: ignore[arg-type]
                with conn.cursor() as cur:
                    if filter_type:
                        q = (
                            f'SELECT name, rule_type, action_summary, condition_expression, priority '
                            f'FROM "{schema_name}".approval_rules '
                            f'WHERE is_active = true AND rule_type = %s ORDER BY priority ASC LIMIT 50'
                        )
                        cur.execute(q, (filter_type,))  # type: ignore[arg-type]
                    else:
                        q = (
                            f'SELECT name, rule_type, action_summary, condition_expression, priority '
                            f'FROM "{schema_name}".approval_rules '
                            f'WHERE is_active = true ORDER BY priority ASC LIMIT 50'
                        )
                        cur.execute(q)  # type: ignore[arg-type]
                    rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning("Could not load approval rules from Lakebase: %s", e)
            return []

    def get_lakehouse_approval_rules(self, rule_type: Optional[str] = None) -> List[Dict]:
        """
        Load active approval rules from the OLTP Lakebase Autoscaling Postgres database when
        lakebase_project_id, lakebase_branch_id, lakebase_endpoint_id are set; otherwise fall back
        to the Lakehouse view. Rules are written from the app (Rules page) and used here to
        accelerate approval rates. Returns list of dicts with keys: name, rule_type, action_summary,
        condition_expression, priority.
        """
        rules = self._get_approval_rules_from_lakebase(rule_type=rule_type)
        if rules:
            return rules
        try:
            allowed = ("authentication", "retry", "routing")
            if rule_type and rule_type not in allowed:
                rule_type = None
            where = "WHERE rule_type = :rule_type" if rule_type else ""
            params = {"rule_type": rule_type} if rule_type else {}
            query = f"""
                SELECT name, rule_type, action_summary, condition_expression, priority
                FROM {self.catalog}.{self.schema}.v_approval_rules_active
                {where}
                ORDER BY priority ASC
                LIMIT 50
            """
            return self._execute_sql_parameterized(query, params)
        except Exception as e:
            logger.warning("Could not load Lakehouse approval rules: %s", e)
            return []

    # -- Agent write-back to Lakebase -------------------------------------------

    def write_recommendation_to_lakebase(
        self,
        recommendation_type: str,
        segment: str,
        action_summary: str,
        expected_impact_pct: float,
        confidence: float,
    ) -> bool:
        """Write an agent recommendation to the Lakebase approval_recommendations table."""
        conn_str = self._get_lakebase_conn_str()
        if not conn_str:
            return False
        try:
            import psycopg
            import uuid

            schema = self.lakebase_schema or "payment_analysis"
            rec_id = uuid.uuid4().hex[:16]
            with psycopg.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f'INSERT INTO "{schema}".approval_recommendations '
                        f"(id, recommendation_type, segment, action_summary, expected_impact_pct, "
                        f"confidence, status, source_agent) "
                        f"VALUES (%s, %s, %s, %s, %s, %s, 'active', %s)",
                        (rec_id, recommendation_type, segment, action_summary,
                         expected_impact_pct, confidence, self.role.value),
                    )
                conn.commit()
            logger.info("Agent %s wrote recommendation %s to Lakebase", self.role.value, rec_id)
            return True
        except Exception as e:
            logger.warning("Failed to write recommendation to Lakebase: %s", e)
            return False

    def propose_config_change(
        self,
        config_key: str,
        proposed_value: str,
        reason: str,
    ) -> bool:
        """Propose a configuration change to Lakebase DecisionConfig."""
        conn_str = self._get_lakebase_conn_str()
        if not conn_str:
            return False
        try:
            import psycopg
            import uuid

            schema = self.lakebase_schema or "payment_analysis"
            change_id = uuid.uuid4().hex[:16]
            with psycopg.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f'INSERT INTO "{schema}".config_change_proposals '
                        f"(id, config_key, proposed_value, reason, proposed_by, status) "
                        f"VALUES (%s, %s, %s, %s, %s, 'proposed')",
                        (change_id, config_key, proposed_value, reason, self.role.value),
                    )
                conn.commit()
            logger.info("Agent %s proposed config change: %s=%s", self.role.value, config_key, proposed_value)
            return True
        except Exception as e:
            logger.warning("Failed to propose config change: %s", e)
            return False

    def analyze_experiment_results(self, experiment_name: str) -> Dict[str, Any]:
        """Analyze A/B experiment results using Lakehouse data (#6 experiment integration).

        Computes approval rate lift, statistical significance, and generates a
        recommendation (keep/discard) based on the treatment vs control comparison.
        """
        query = f"""
            WITH experiment_metrics AS (
                SELECT
                    variant,
                    COUNT(*) AS total_transactions,
                    SUM(CASE WHEN outcome = 'approved' THEN 1 ELSE 0 END) AS approved,
                    ROUND(SUM(CASE WHEN outcome = 'approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS approval_rate,
                    AVG(latency_ms) AS avg_latency
                FROM {self.catalog}.{self.schema}.v_experiment_outcomes
                WHERE experiment_name = :exp_name
                GROUP BY variant
            )
            SELECT * FROM experiment_metrics
        """
        rows = self._execute_sql_parameterized(query, {"exp_name": experiment_name})
        if not rows or len(rows) < 2:
            return {
                "experiment": experiment_name,
                "status": "insufficient_data",
                "message": f"Need at least 2 variants; found {len(rows)}",
            }

        control = next((r for r in rows if r.get("variant") == "control"), rows[0])
        treatment = next((r for r in rows if r.get("variant") == "treatment"), rows[1])

        ctrl_rate = float(control.get("approval_rate", 0))
        treat_rate = float(treatment.get("approval_rate", 0))
        lift = treat_rate - ctrl_rate
        ctrl_n = int(control.get("total_transactions", 0))
        treat_n = int(treatment.get("total_transactions", 0))

        recommendation = "keep_treatment" if lift > 0.5 and treat_n >= 100 else (
            "discard_treatment" if lift < -0.5 else "continue_experiment"
        )

        result = {
            "experiment": experiment_name,
            "control_rate": ctrl_rate,
            "treatment_rate": treat_rate,
            "lift_pct": round(lift, 2),
            "control_n": ctrl_n,
            "treatment_n": treat_n,
            "recommendation": recommendation,
            "status": "analyzed",
        }

        # Write recommendation to Lakebase if we have a clear signal
        if recommendation in ("keep_treatment", "discard_treatment"):
            action = f"Experiment '{experiment_name}': {recommendation} (lift={lift:+.2f}%)"
            self.write_recommendation_to_lakebase(
                recommendation_type="experiment",
                segment="all",
                action_summary=action,
                expected_impact_pct=abs(lift),
                confidence=min(0.95, (ctrl_n + treat_n) / 10000),
            )

        return result


class SmartRoutingAgent(BaseAgent):
    """Agent for smart payment routing and cascading decisions."""

    def __init__(
        self,
        catalog: str,
        schema: str,
        *,
        lakebase_project_id: str = "",
        lakebase_branch_id: str = "",
        lakebase_endpoint_id: str = "",
        lakebase_schema: str = "payment_analysis",
        llm_endpoint: str = "databricks-claude-sonnet-4-5",
    ):
        super().__init__(
            AgentRole.SMART_ROUTING,
            catalog,
            schema,
            llm_endpoint=llm_endpoint,
            lakebase_project_id=lakebase_project_id,
            lakebase_branch_id=lakebase_branch_id,
            lakebase_endpoint_id=lakebase_endpoint_id,
            lakebase_schema=lakebase_schema,
        )
        self._register_tools()

    def get_system_prompt(self) -> str:
        return """You are the Smart Routing & Cascading Agent for payment optimization.

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

    def _register_tools(self):
        """Register routing tools."""
        
        def get_route_performance(**kwargs):
            """Get performance metrics by route."""
            query = f"""
            SELECT 
                payment_solution,
                card_network,
                COUNT(*) as volume,
                AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) * 100 as approval_rate,
                AVG(processing_time_ms) as avg_latency
            FROM {self.catalog}.{self.schema}.payments_enriched_silver
            WHERE event_date >= CURRENT_DATE - 7
            GROUP BY payment_solution, card_network
            ORDER BY volume DESC
            """
            return self._execute_sql(query)

        def get_cascade_recommendations(**kwargs):
            """Get recommended cascade configuration."""
            segment = _sanitize_sql_string(kwargs.get("merchant_segment", "Retail"))
            query = f"""
            SELECT 
                payment_solution,
                AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) * 100 as approval_rate,
                AVG(processing_time_ms) as latency,
                COUNT(*) as volume
            FROM {self.catalog}.{self.schema}.payments_enriched_silver
            WHERE merchant_segment = :segment
              AND event_date >= CURRENT_DATE - 30
            GROUP BY payment_solution
            ORDER BY approval_rate DESC
            LIMIT 3
            """
            return self._execute_sql_parameterized(query, {"segment": segment})

        def write_routing_recommendation(**kwargs):
            """Write a routing optimization recommendation to Lakebase for the decision loop."""
            segment = kwargs.get("segment", "all")
            action = kwargs.get("action_summary", "")
            impact = float(kwargs.get("expected_impact_pct", 0))
            conf = float(kwargs.get("confidence", 0.5))
            return self.write_recommendation_to_lakebase("routing", segment, action, impact, conf)

        def propose_routing_config(**kwargs):
            """Propose a routing configuration change (e.g. preferred route for a segment)."""
            key = kwargs.get("config_key", "")
            value = kwargs.get("proposed_value", "")
            reason = kwargs.get("reason", "")
            return self.propose_config_change(key, value, reason)

        self.add_tool(AgentTool(
            name="get_route_performance",
            description="Get approval rates and latency by payment route",
            function=get_route_performance,
            parameters={}
        ))

        self.add_tool(AgentTool(
            name="get_cascade_recommendations",
            description="Get recommended cascade configuration for a segment",
            function=get_cascade_recommendations,
            parameters={"merchant_segment": "string"}
        ))

        self.add_tool(AgentTool(
            name="write_routing_recommendation",
            description="Write a routing optimization recommendation to Lakebase",
            function=write_routing_recommendation,
            parameters={"segment": "string", "action_summary": "string", "expected_impact_pct": "number", "confidence": "number"}
        ))

        self.add_tool(AgentTool(
            name="propose_routing_config",
            description="Propose a routing configuration change in Lakebase",
            function=propose_routing_config,
            parameters={"config_key": "string", "proposed_value": "string", "reason": "string"}
        ))


class SmartRetryAgent(BaseAgent):
    """Agent for intelligent payment retry decisions."""

    def __init__(
        self,
        catalog: str,
        schema: str,
        *,
        lakebase_project_id: str = "",
        lakebase_branch_id: str = "",
        lakebase_endpoint_id: str = "",
        lakebase_schema: str = "payment_analysis",
        llm_endpoint: str = "databricks-claude-sonnet-4-5",
    ):
        super().__init__(
            AgentRole.SMART_RETRY,
            catalog,
            schema,
            llm_endpoint=llm_endpoint,
            lakebase_project_id=lakebase_project_id,
            lakebase_branch_id=lakebase_branch_id,
            lakebase_endpoint_id=lakebase_endpoint_id,
            lakebase_schema=lakebase_schema,
        )
        self._register_tools()

    def get_system_prompt(self) -> str:
        return """You are the Smart Retry Agent for payment recovery optimization.

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

    def _register_tools(self):
        """Register retry analysis tools."""

        def get_retry_success_rates(**kwargs):
            """Get historical retry success rates by decline reason."""
            query = f"""
            SELECT 
                decline_reason,
                retry_count,
                COUNT(*) as attempts,
                AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
                AVG(amount) as avg_amount
            FROM {self.catalog}.{self.schema}.payments_enriched_silver
            WHERE is_retry = true
              AND event_date >= CURRENT_DATE - 30
            GROUP BY decline_reason, retry_count
            ORDER BY decline_reason, retry_count
            """
            return self._execute_sql(query)

        def get_recovery_opportunities(**kwargs):
            """Find high-value recovery opportunities."""
            min_amount = int(_sanitize_sql_number(kwargs.get("min_amount", 100), min_val=0, max_val=1_000_000))
            query = f"""
            SELECT 
                decline_reason,
                COUNT(*) as decline_count,
                SUM(amount) as total_value,
                AVG(fraud_score) as avg_fraud_score,
                CASE 
                    WHEN AVG(fraud_score) < 0.3 THEN 'HIGH'
                    WHEN AVG(fraud_score) < 0.5 THEN 'MEDIUM'
                    ELSE 'LOW'
                END as recovery_likelihood
            FROM {self.catalog}.{self.schema}.payments_enriched_silver
            WHERE NOT is_approved
              AND amount >= {min_amount}
              AND fraud_score < 0.5
              AND retry_count < 3
              AND event_date >= CURRENT_DATE - 7
            GROUP BY decline_reason
            HAVING COUNT(*) > 10
            ORDER BY total_value DESC
            """
            return self._execute_sql(query)

        def write_retry_recommendation(**kwargs):
            """Write a retry optimization recommendation to Lakebase for the decision loop."""
            segment = kwargs.get("segment", "all")
            action = kwargs.get("action_summary", "")
            impact = float(kwargs.get("expected_impact_pct", 0))
            conf = float(kwargs.get("confidence", 0.5))
            return self.write_recommendation_to_lakebase("retry", segment, action, impact, conf)

        self.add_tool(AgentTool(
            name="get_retry_success_rates",
            description="Get historical retry success rates by decline reason",
            function=get_retry_success_rates,
            parameters={}
        ))

        self.add_tool(AgentTool(
            name="get_recovery_opportunities",
            description="Find high-value transactions worth retrying",
            function=get_recovery_opportunities,
            parameters={"min_amount": "number"}
        ))

        self.add_tool(AgentTool(
            name="write_retry_recommendation",
            description="Write a retry optimization recommendation to Lakebase for the decision loop",
            function=write_retry_recommendation,
            parameters={"segment": "string", "action_summary": "string", "expected_impact_pct": "number", "confidence": "number"}
        ))


class DeclineAnalystAgent(BaseAgent):
    """Agent specialized in analyzing decline patterns."""

    def __init__(
        self,
        catalog: str,
        schema: str,
        *,
        lakebase_project_id: str = "",
        lakebase_branch_id: str = "",
        lakebase_endpoint_id: str = "",
        lakebase_schema: str = "payment_analysis",
        llm_endpoint: str = "databricks-claude-sonnet-4-5",
    ):
        super().__init__(
            AgentRole.DECLINE_ANALYST,
            catalog,
            schema,
            llm_endpoint=llm_endpoint,
            lakebase_project_id=lakebase_project_id,
            lakebase_branch_id=lakebase_branch_id,
            lakebase_endpoint_id=lakebase_endpoint_id,
            lakebase_schema=lakebase_schema,
        )
        self._register_tools()

    def get_system_prompt(self) -> str:
        return """You are a Decline Analysis Specialist for payment optimization.

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

    def _register_tools(self):
        """Register decline analysis tools."""

        def get_decline_trends(**kwargs):
            """Get decline trends over time."""
            query = f"""
            SELECT * FROM {self.catalog}.{self.schema}.v_top_decline_reasons
            ORDER BY decline_count DESC
            LIMIT 10
            """
            return self._execute_sql(query)

        def get_decline_by_segment(**kwargs):
            """Get declines broken down by merchant segment."""
            query = f"""
            SELECT 
                merchant_segment,
                decline_reason,
                COUNT(*) as decline_count,
                SUM(amount) as declined_value,
                AVG(fraud_score) as avg_fraud_score
            FROM {self.catalog}.{self.schema}.payments_enriched_silver
            WHERE NOT is_approved
              AND event_date >= CURRENT_DATE - 30
            GROUP BY merchant_segment, decline_reason
            ORDER BY decline_count DESC
            LIMIT 20
            """
            return self._execute_sql(query)

        def write_decline_recommendation(**kwargs):
            """Write a decline analysis recommendation to Lakebase for the decision loop."""
            segment = kwargs.get("segment", "all")
            action = kwargs.get("action_summary", "")
            impact = float(kwargs.get("expected_impact_pct", 0))
            conf = float(kwargs.get("confidence", 0.5))
            return self.write_recommendation_to_lakebase("decline_analysis", segment, action, impact, conf)

        def propose_decline_config(**kwargs):
            """Propose a configuration change based on decline analysis (e.g. adjust risk thresholds)."""
            key = kwargs.get("config_key", "")
            value = kwargs.get("proposed_value", "")
            reason = kwargs.get("reason", "")
            return self.propose_config_change(key, value, reason)

        self.add_tool(AgentTool(
            name="get_decline_trends",
            description="Get top decline reasons and their characteristics",
            function=get_decline_trends,
            parameters={}
        ))

        self.add_tool(AgentTool(
            name="get_decline_by_segment",
            description="Get decline breakdown by merchant segment",
            function=get_decline_by_segment,
            parameters={}
        ))

        self.add_tool(AgentTool(
            name="write_decline_recommendation",
            description="Write a decline analysis recommendation to Lakebase for the decision loop",
            function=write_decline_recommendation,
            parameters={"segment": "string", "action_summary": "string", "expected_impact_pct": "number", "confidence": "number"}
        ))

        self.add_tool(AgentTool(
            name="propose_decline_config",
            description="Propose a configuration change based on decline analysis",
            function=propose_decline_config,
            parameters={"config_key": "string", "proposed_value": "string", "reason": "string"}
        ))


class RiskAssessorAgent(BaseAgent):
    """Agent for fraud detection and risk assessment."""

    def __init__(
        self,
        catalog: str,
        schema: str,
        *,
        lakebase_project_id: str = "",
        lakebase_branch_id: str = "",
        lakebase_endpoint_id: str = "",
        lakebase_schema: str = "payment_analysis",
        llm_endpoint: str = "databricks-claude-sonnet-4-5",
    ):
        super().__init__(
            AgentRole.RISK_ASSESSOR,
            catalog,
            schema,
            llm_endpoint=llm_endpoint,
            lakebase_project_id=lakebase_project_id,
            lakebase_branch_id=lakebase_branch_id,
            lakebase_endpoint_id=lakebase_endpoint_id,
            lakebase_schema=lakebase_schema,
        )
        self._register_tools()

    def get_system_prompt(self) -> str:
        return """You are a Fraud and Risk Assessment Expert.

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

    def _register_tools(self):
        """Register risk assessment tools."""

        def get_high_risk_transactions(**kwargs):
            """Get high-risk transactions for review."""
            threshold = _sanitize_sql_number(kwargs.get("threshold", 0.7), min_val=0.0, max_val=1.0)
            query = f"""
            SELECT 
                transaction_id,
                merchant_segment,
                amount,
                fraud_score,
                aml_risk_score,
                device_trust_score,
                is_approved,
                decline_reason
            FROM {self.catalog}.{self.schema}.payments_enriched_silver
            WHERE fraud_score > {threshold}
              AND event_date >= CURRENT_DATE - 1
            ORDER BY fraud_score DESC
            LIMIT 50
            """
            return self._execute_sql(query)

        def get_risk_distribution(**kwargs):
            """Get risk score distribution."""
            query = f"""
            SELECT 
                risk_tier,
                COUNT(*) as transaction_count,
                AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) * 100 as approval_rate,
                AVG(fraud_score) as avg_fraud_score,
                SUM(amount) as total_value
            FROM {self.catalog}.{self.schema}.payments_enriched_silver
            WHERE event_date >= CURRENT_DATE - 7
            GROUP BY risk_tier
            ORDER BY avg_fraud_score DESC
            """
            return self._execute_sql(query)

        def write_risk_recommendation(**kwargs):
            """Write a risk assessment recommendation to Lakebase for the decision loop."""
            segment = kwargs.get("segment", "all")
            action = kwargs.get("action_summary", "")
            impact = float(kwargs.get("expected_impact_pct", 0))
            conf = float(kwargs.get("confidence", 0.5))
            return self.write_recommendation_to_lakebase("risk_assessment", segment, action, impact, conf)

        def propose_risk_config(**kwargs):
            """Propose a risk threshold change based on risk assessment analysis."""
            key = kwargs.get("config_key", "")
            value = kwargs.get("proposed_value", "")
            reason = kwargs.get("reason", "")
            return self.propose_config_change(key, value, reason)

        self.add_tool(AgentTool(
            name="get_high_risk_transactions",
            description="Get high-risk transactions requiring review",
            function=get_high_risk_transactions,
            parameters={"threshold": "number"}
        ))

        self.add_tool(AgentTool(
            name="get_risk_distribution",
            description="Get risk score distribution across tiers",
            function=get_risk_distribution,
            parameters={}
        ))

        self.add_tool(AgentTool(
            name="write_risk_recommendation",
            description="Write a risk assessment recommendation to Lakebase for the decision loop",
            function=write_risk_recommendation,
            parameters={"segment": "string", "action_summary": "string", "expected_impact_pct": "number", "confidence": "number"}
        ))

        self.add_tool(AgentTool(
            name="propose_risk_config",
            description="Propose a risk threshold change based on risk analysis",
            function=propose_risk_config,
            parameters={"config_key": "string", "proposed_value": "string", "reason": "string"}
        ))


class PerformanceRecommenderAgent(BaseAgent):
    """Agent for performance optimization recommendations."""

    def __init__(
        self,
        catalog: str,
        schema: str,
        *,
        lakebase_project_id: str = "",
        lakebase_branch_id: str = "",
        lakebase_endpoint_id: str = "",
        lakebase_schema: str = "payment_analysis",
        llm_endpoint: str = "databricks-claude-sonnet-4-5",
    ):
        super().__init__(
            AgentRole.PERFORMANCE_RECOMMENDER,
            catalog,
            schema,
            llm_endpoint=llm_endpoint,
            lakebase_project_id=lakebase_project_id,
            lakebase_branch_id=lakebase_branch_id,
            lakebase_endpoint_id=lakebase_endpoint_id,
            lakebase_schema=lakebase_schema,
        )
        self._register_tools()

    def get_system_prompt(self) -> str:
        return """You are the Performance Recommender Agent for payment optimization.

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

    def _register_tools(self):
        """Register performance analysis tools."""

        def get_kpi_summary(**kwargs):
            """Get executive KPI summary."""
            query = f"""
            SELECT * FROM {self.catalog}.{self.schema}.v_executive_kpis
            """
            return self._execute_sql(query)

        def get_optimization_opportunities(**kwargs):
            """Identify optimization opportunities."""
            query = f"""
            SELECT 
                'Routing' as optimization_area,
                payment_solution,
                approval_rate_pct,
                transaction_count,
                CASE 
                    WHEN approval_rate_pct < 80 THEN 'HIGH'
                    WHEN approval_rate_pct < 85 THEN 'MEDIUM'
                    ELSE 'LOW'
                END as priority
            FROM {self.catalog}.{self.schema}.v_solution_performance
            WHERE approval_rate_pct < 90
            
            UNION ALL
            
            SELECT 
                'Geography' as optimization_area,
                country as payment_solution,
                approval_rate_pct,
                transaction_count,
                CASE 
                    WHEN approval_rate_pct < 80 THEN 'HIGH'
                    WHEN approval_rate_pct < 85 THEN 'MEDIUM'
                    ELSE 'LOW'
                END as priority
            FROM {self.catalog}.{self.schema}.v_performance_by_geography
            WHERE approval_rate_pct < 85
              AND transaction_count > 100
            
            ORDER BY 
                CASE priority 
                    WHEN 'HIGH' THEN 1 
                    WHEN 'MEDIUM' THEN 2 
                    WHEN 'LOW' THEN 3 
                END,
                approval_rate_pct
            """
            return self._execute_sql(query)

        def get_trend_analysis(**kwargs):
            """Get performance trends."""
            query = f"""
            SELECT * FROM {self.catalog}.{self.schema}.v_daily_trends
            ORDER BY event_date DESC
            LIMIT 30
            """
            return self._execute_sql(query)

        self.add_tool(AgentTool(
            name="get_kpi_summary",
            description="Get current KPI summary",
            function=get_kpi_summary,
            parameters={}
        ))

        self.add_tool(AgentTool(
            name="get_optimization_opportunities",
            description="Identify areas for optimization",
            function=get_optimization_opportunities,
            parameters={}
        ))

        def analyze_ab_experiment(**kwargs):
            """Analyze A/B experiment results and generate a recommendation."""
            exp_name = kwargs.get("experiment_name", "")
            return self.analyze_experiment_results(exp_name)

        def write_performance_recommendation(**kwargs):
            """Write a performance optimization recommendation to Lakebase."""
            segment = kwargs.get("segment", "all")
            action = kwargs.get("action_summary", "")
            impact = float(kwargs.get("expected_impact_pct", 0))
            conf = float(kwargs.get("confidence", 0.5))
            return self.write_recommendation_to_lakebase("performance", segment, action, impact, conf)

        def propose_threshold_change(**kwargs):
            """Propose a decision threshold change (e.g. risk_threshold_high) to Lakebase."""
            key = kwargs.get("config_key", "")
            value = kwargs.get("proposed_value", "")
            reason = kwargs.get("reason", "")
            return self.propose_config_change(key, value, reason)

        self.add_tool(AgentTool(
            name="get_trend_analysis",
            description="Get performance trends over time",
            function=get_trend_analysis,
            parameters={}
        ))

        self.add_tool(AgentTool(
            name="analyze_ab_experiment",
            description="Analyze A/B experiment results and recommend keep/discard treatment",
            function=analyze_ab_experiment,
            parameters={"experiment_name": "string"}
        ))

        self.add_tool(AgentTool(
            name="write_performance_recommendation",
            description="Write a performance optimization recommendation to Lakebase",
            function=write_performance_recommendation,
            parameters={"segment": "string", "action_summary": "string", "expected_impact_pct": "number", "confidence": "number"}
        ))

        self.add_tool(AgentTool(
            name="propose_threshold_change",
            description="Propose a decision threshold change in Lakebase (e.g. risk_threshold_high)",
            function=propose_threshold_change,
            parameters={"config_key": "string", "proposed_value": "string", "reason": "string"}
        ))


# Tiered LLM strategy — strongest model for orchestrator reasoning, balanced for specialists.
LLM_TIER_ORCHESTRATOR = "databricks-claude-opus-4-6"
LLM_TIER_SPECIALIST = "databricks-claude-sonnet-4-5"


class OrchestratorAgent(BaseAgent):
    """Meta-agent that coordinates all specialized agents.

    Uses a tiered LLM strategy:
      - Orchestrator routing: Opus 4.6 (strongest reasoning for query classification)
      - Synthesis: Sonnet 4.5 (fast, sufficient for summarizing specialist outputs)
      - Specialists (domain analysis): Sonnet 4.5 (balanced speed / quality)
    """

    def __init__(
        self,
        catalog: str,
        schema: str,
        *,
        lakebase_project_id: str = "",
        lakebase_branch_id: str = "",
        lakebase_endpoint_id: str = "",
        lakebase_schema: str = "payment_analysis",
        llm_endpoint: str = LLM_TIER_ORCHESTRATOR,
        specialist_llm_endpoint: str = LLM_TIER_SPECIALIST,
    ):
        super().__init__(
            AgentRole.ORCHESTRATOR,
            catalog,
            schema,
            llm_endpoint=llm_endpoint,
            lakebase_project_id=lakebase_project_id,
            lakebase_branch_id=lakebase_branch_id,
            lakebase_endpoint_id=lakebase_endpoint_id,
            lakebase_schema=lakebase_schema,
        )
        lakebase_kw = {
            "lakebase_project_id": lakebase_project_id,
            "lakebase_branch_id": lakebase_branch_id,
            "lakebase_endpoint_id": lakebase_endpoint_id,
            "lakebase_schema": lakebase_schema,
            "llm_endpoint": specialist_llm_endpoint,
        }
        # Initialize all specialist agents with the balanced-tier model
        self.smart_routing = SmartRoutingAgent(catalog, schema, **lakebase_kw)
        self.smart_retry = SmartRetryAgent(catalog, schema, **lakebase_kw)
        self.decline_analyst = DeclineAnalystAgent(catalog, schema, **lakebase_kw)
        self.risk_assessor = RiskAssessorAgent(catalog, schema, **lakebase_kw)
        self.performance_recommender = PerformanceRecommenderAgent(catalog, schema, **lakebase_kw)

    def get_system_prompt(self) -> str:
        return """You are the Orchestrator Agent for Payment Analysis.

Your role is to:
1. UNDERSTAND user queries and route to appropriate specialist agents
2. COORDINATE multi-agent workflows
3. SYNTHESIZE insights from multiple agents
4. PROVIDE comprehensive recommendations

Available Specialist Agents:
- SmartRoutingAgent: Payment routing and cascading optimization
- SmartRetryAgent: Intelligent retry decisions and recovery
- DeclineAnalystAgent: Decline pattern analysis
- RiskAssessorAgent: Fraud detection and risk assessment
- PerformanceRecommenderAgent: Overall optimization recommendations

Route queries based on keywords:
- "routing", "cascade", "processor" -> SmartRoutingAgent
- "retry", "recovery", "reprocess" -> SmartRetryAgent
- "decline", "reject", "failure" -> DeclineAnalystAgent
- "fraud", "risk", "suspicious" -> RiskAssessorAgent
- "performance", "optimize", "improve" -> PerformanceRecommenderAgent

For complex queries, engage multiple agents and synthesize responses."""

    def _route_query(self, query: str) -> Dict[str, "BaseAgent"]:
        """Select specialist agents for the query using keyword matching."""
        query_lower = query.lower()
        selected: Dict[str, BaseAgent] = {}

        if any(w in query_lower for w in ("routing", "cascade", "processor", "route")):
            selected["smart_routing"] = self.smart_routing
        if any(w in query_lower for w in ("retry", "recovery", "reprocess", "failed")):
            selected["smart_retry"] = self.smart_retry
        if any(w in query_lower for w in ("decline", "reject", "fail", "denied")):
            selected["decline_analyst"] = self.decline_analyst
        if any(w in query_lower for w in ("fraud", "risk", "suspicious", "aml")):
            selected["risk_assessor"] = self.risk_assessor
        if any(w in query_lower for w in ("performance", "optimize", "improve", "recommend", "kpi")):
            selected["performance_recommender"] = self.performance_recommender

        # Broad/ambiguous queries: default to performance recommender
        if not selected:
            selected["performance_recommender"] = self.performance_recommender

        return selected

    def handle_query(self, query: str) -> Dict:
        """Route query to specialists, run them in parallel, and synthesize with LLM."""
        selected = self._route_query(query)
        responses: Dict[str, str] = {}

        # Run specialists in parallel using ThreadPoolExecutor
        if len(selected) == 1:
            name, agent = next(iter(selected.items()))
            responses[name] = agent.think(query)
        else:
            with ThreadPoolExecutor(max_workers=min(len(selected), 5)) as executor:
                futures = {
                    executor.submit(agent.think, query): name
                    for name, agent in selected.items()
                }
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        responses[name] = future.result(timeout=120)
                    except Exception as e:
                        logger.warning("Specialist %s failed: %s", name, e)
                        responses[name] = f"[{name}] analysis unavailable: {e}"

        synthesis = self._synthesize_responses(query, responses)
        return {
            "query": query,
            "agents_used": list(responses.keys()),
            "agent_responses": responses,
            "synthesis": synthesis,
        }

    def _synthesize_responses(self, query: str, responses: Dict[str, str]) -> str:
        """Synthesize specialist responses using the orchestrator LLM for intelligent summary."""
        if len(responses) <= 1:
            return next(iter(responses.values()), "")

        # Build a context block from specialist outputs
        parts = []
        for agent_name, response in responses.items():
            label = agent_name.upper().replace("_", " ")
            parts.append(f"### {label}\n{response}")
        combined = "\n\n".join(parts)

        synthesis_prompt = (
            f"You received the following analysis from specialist agents in response to the user query:\n"
            f'"{query}"\n\n'
            f"{combined}\n\n"
            f"Provide a concise, unified executive summary that:\n"
            f"1. Highlights the top 3-5 actionable findings across all agents\n"
            f"2. Identifies any conflicting signals and how to resolve them\n"
            f"3. Recommends prioritized next steps\n"
            f"Keep the response under 500 words. Use numbered lists."
        )

        try:
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

            w = WorkspaceClient()
            # Use Sonnet (balanced tier) for synthesis — faster than Opus and
            # sufficient quality for summarizing specialist outputs.
            response = w.serving_endpoints.query(
                name=LLM_TIER_SPECIALIST,
                messages=[
                    ChatMessage(role=ChatMessageRole.SYSTEM, content=self.get_system_prompt()),
                    ChatMessage(role=ChatMessageRole.USER, content=synthesis_prompt),
                ],
                max_tokens=1500,
                temperature=0.2,
            )
            choice = response.choices[0] if response.choices else None
            msg = choice.message if choice else None
            content = (getattr(msg, "content", None) or "").strip()
            if content:
                return content
        except Exception as e:
            logger.warning("LLM synthesis failed, falling back to concatenation: %s", e)

        # Fallback: plain concatenation
        return "\n\n".join(
            f"[{name.upper().replace('_', ' ')}]\n{resp}" for name, resp in responses.items()
        )


def setup_agent_framework(
    catalog: str = "ahs_demos_catalog",
    schema: str = "payment_analysis",
    *,
    lakebase_project_id: str = "",
    lakebase_branch_id: str = "",
    lakebase_endpoint_id: str = "",
    lakebase_schema: str = "payment_analysis",
    model_registry_catalog: str = "",
    model_registry_schema: str = "agents",
    llm_endpoint: str = LLM_TIER_ORCHESTRATOR,
    specialist_llm_endpoint: str = LLM_TIER_SPECIALIST,
) -> OrchestratorAgent:
    """Initialize the multi-agent framework with a tiered LLM strategy.

    Orchestrator uses the strongest model (Opus 4.6) for routing and synthesis.
    Specialists use a balanced model (Sonnet 4.5) for domain-specific analysis.
    When Lakebase IDs are set, approval rules are read from OLTP Lakebase Postgres.
    model_registry_* define the UC registry for AgentBricks (catalog.schema.agent_name).
    """
    orchestrator = OrchestratorAgent(
        catalog,
        schema,
        lakebase_project_id=lakebase_project_id,
        lakebase_branch_id=lakebase_branch_id,
        lakebase_endpoint_id=lakebase_endpoint_id,
        lakebase_schema=lakebase_schema,
        llm_endpoint=llm_endpoint or LLM_TIER_ORCHESTRATOR,
        specialist_llm_endpoint=specialist_llm_endpoint or LLM_TIER_SPECIALIST,
    )
    reg = f"{model_registry_catalog or catalog}.{model_registry_schema or 'agents'}"
    logger.info(
        "Agent framework initialized (Orchestrator [%s] + 5 specialists [%s]); registry: %s",
        orchestrator.llm_endpoint, specialist_llm_endpoint, reg,
    )
    return orchestrator


def get_notebook_config() -> Dict[str, Any]:
    """Read job/notebook parameters from Databricks widgets or return defaults. Used as single source for catalog, schema, query, Lakebase connection, and model registry (AgentBricks UC registry)."""
    defaults = {
        "catalog": "ahs_demos_catalog",
        "schema": "payment_analysis",
        "query": "Run comprehensive payment analysis: routing, retries, declines, risk, and performance optimizations.",
        "agent_role": "orchestrator",
        "lakebase_project_id": "",
        "lakebase_branch_id": "",
        "lakebase_endpoint_id": "",
        "lakebase_schema": "payment_analysis",
        "model_registry_catalog": "ahs_demos_catalog",
        "model_registry_schema": "agents",
        "llm_endpoint": LLM_TIER_ORCHESTRATOR,
        "specialist_llm_endpoint": LLM_TIER_SPECIALIST,
    }
    try:
        from databricks.sdk.runtime import dbutils
        dbutils.widgets.text("catalog", defaults["catalog"])
        dbutils.widgets.text("schema", defaults["schema"])
        dbutils.widgets.text("query", defaults["query"])
        dbutils.widgets.text("agent_role", defaults["agent_role"])
        dbutils.widgets.text("lakebase_project_id", defaults["lakebase_project_id"])
        dbutils.widgets.text("lakebase_branch_id", defaults["lakebase_branch_id"])
        dbutils.widgets.text("lakebase_endpoint_id", defaults["lakebase_endpoint_id"])
        dbutils.widgets.text("lakebase_schema", defaults["lakebase_schema"])
        dbutils.widgets.text("model_registry_catalog", defaults["model_registry_catalog"])
        dbutils.widgets.text("model_registry_schema", defaults["model_registry_schema"])
        dbutils.widgets.text("llm_endpoint", defaults["llm_endpoint"])
        dbutils.widgets.text("specialist_llm_endpoint", defaults["specialist_llm_endpoint"])
        return {
            "catalog": dbutils.widgets.get("catalog") or defaults["catalog"],
            "schema": dbutils.widgets.get("schema") or defaults["schema"],
            "query": dbutils.widgets.get("query") or defaults["query"],
            "agent_role": (dbutils.widgets.get("agent_role") or defaults["agent_role"]).strip(),
            "lakebase_project_id": (dbutils.widgets.get("lakebase_project_id") or "").strip(),
            "lakebase_branch_id": (dbutils.widgets.get("lakebase_branch_id") or "").strip(),
            "lakebase_endpoint_id": (dbutils.widgets.get("lakebase_endpoint_id") or "").strip(),
            "lakebase_schema": (dbutils.widgets.get("lakebase_schema") or defaults["lakebase_schema"]).strip() or "payment_analysis",
            "model_registry_catalog": (dbutils.widgets.get("model_registry_catalog") or defaults["model_registry_catalog"]).strip() or defaults["catalog"],
            "model_registry_schema": (dbutils.widgets.get("model_registry_schema") or defaults["model_registry_schema"]).strip() or "agents",
            "llm_endpoint": (dbutils.widgets.get("llm_endpoint") or defaults["llm_endpoint"]).strip() or LLM_TIER_ORCHESTRATOR,
            "specialist_llm_endpoint": (dbutils.widgets.get("specialist_llm_endpoint") or defaults["specialist_llm_endpoint"]).strip() or LLM_TIER_SPECIALIST,
        }
    except Exception:
        return defaults


def run_framework(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the agent framework: build orchestrator (and all specialists) and execute the query.
    This is the single entry point for the Job 6 task. Returns the orchestrator result dict.
    """
    catalog = config["catalog"]
    schema = config["schema"]
    query = config["query"]
    agent_role = (config.get("agent_role") or "orchestrator").strip().lower()
    llm_endpoint = (config.get("llm_endpoint") or "").strip() or LLM_TIER_ORCHESTRATOR
    specialist_llm_endpoint = (config.get("specialist_llm_endpoint") or "").strip() or LLM_TIER_SPECIALIST
    lakebase_kw = {
        "lakebase_project_id": config.get("lakebase_project_id") or "",
        "lakebase_branch_id": config.get("lakebase_branch_id") or "",
        "lakebase_endpoint_id": config.get("lakebase_endpoint_id") or "",
        "lakebase_schema": config.get("lakebase_schema") or "payment_analysis",
    }
    registry_kw = {
        "model_registry_catalog": config.get("model_registry_catalog") or catalog,
        "model_registry_schema": config.get("model_registry_schema") or "agents",
    }

    if agent_role == "orchestrator":
        orchestrator = setup_agent_framework(
            catalog, schema, llm_endpoint=llm_endpoint, specialist_llm_endpoint=specialist_llm_endpoint,
            **lakebase_kw, **registry_kw,
        )
        return orchestrator.handle_query(query)

    # Optional: run a single specialist (e.g. for ad-hoc or debug)
    specialist_map = {
        "smart_routing": SmartRoutingAgent,
        "smart_retry": SmartRetryAgent,
        "decline_analyst": DeclineAnalystAgent,
        "risk_assessor": RiskAssessorAgent,
        "performance_recommender": PerformanceRecommenderAgent,
    }
    agent_class = specialist_map.get(agent_role)
    if agent_class:
        agent = agent_class(catalog, schema, llm_endpoint=llm_endpoint, **lakebase_kw)
        response = agent.think(query)
        return {"query": query, "agents_used": [agent_role], "agent_responses": {agent_role: response}, "synthesis": response}
    raise ValueError(f"Unknown agent_role={agent_role!r}. Use one of: orchestrator, {', '.join(specialist_map)}")


# Databricks notebook entry point (Job 6: single task run_agent_framework)
if __name__ == "__main__":
    import json
    config = get_notebook_config()
    query = config["query"]
    agent_role = config["agent_role"]

    print("\n" + "=" * 70)
    print("Payment Analysis Agent Framework")
    print("=" * 70)
    print(f"Mode:    {agent_role}")
    print(f"Query:   {query}")
    print("=" * 70)

    result = run_framework(config)

    print("\nAgents used:", result.get("agents_used", []))
    print("\n--- Synthesis ---")
    print(result.get("synthesis", ""))
    print("\n--- Done ---")

    # Exit with result so Jobs API get_run_output() can return it (e.g. for app orchestrator chat).
    try:
        from databricks.sdk.runtime import dbutils
        payload = json.dumps({"synthesis": result.get("synthesis", ""), "agents_used": result.get("agents_used", [])})
        dbutils.notebook.exit(payload)  # type: ignore[call-arg]
    except Exception:
        pass
