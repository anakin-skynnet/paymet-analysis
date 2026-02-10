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

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


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
    RESPONDING = "responding"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    role: str
    content: str
    metadata: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.now)


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


class BaseAgent:
    """Base class for all payment analysis agents."""

    def __init__(
        self,
        role: AgentRole,
        catalog: str,
        schema: str,
        llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
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
            logger.error(f"Agent error: {e}")
            return f"Error: {str(e)}"

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
        try:
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.service.sql import StatementState

            w = WorkspaceClient()
            warehouses = list(w.warehouses.list())
            warehouse_id = next(
                (wh.id for wh in warehouses if wh.state and str(wh.state) == "RUNNING"),
                warehouses[0].id if warehouses else None
            )

            if not warehouse_id:
                return []

            response = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=query,
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
            return []
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return []

    def _get_approval_rules_from_lakebase(self, rule_type: Optional[str] = None) -> List[Dict]:
        """
        Load active approval rules from the OLTP Lakebase Autoscaling Postgres database.
        Returns list of dicts with keys: name, rule_type, action_summary, condition_expression, priority.
        """
        if not (self.lakebase_project_id and self.lakebase_branch_id and self.lakebase_endpoint_id):
            return []
        try:
            from databricks.sdk import WorkspaceClient
            import psycopg
            from psycopg.rows import dict_row

            ws = WorkspaceClient()
            postgres_api = getattr(ws, "postgres", None)
            if postgres_api is None:
                logger.warning("WorkspaceClient has no 'postgres'; cannot read from Lakebase.")
                return []
            endpoint_name = (
                f"projects/{self.lakebase_project_id}/branches/{self.lakebase_branch_id}"
                f"/endpoints/{self.lakebase_endpoint_id}"
            )
            endpoint = postgres_api.get_endpoint(name=endpoint_name)
            cred = postgres_api.generate_database_credential(endpoint=endpoint_name)
            status = getattr(endpoint, "status", None)
            hosts = getattr(status, "hosts", None) if status else None
            if hosts and isinstance(hosts, list) and len(hosts) > 0:
                host = getattr(hosts[0], "host", None) or getattr(hosts[0], "hostname", None)
            else:
                host = getattr(hosts, "host", None) or getattr(hosts, "hostname", None) if hosts else None
            if not host:
                logger.warning("Lakebase endpoint has no host.")
                return []
            schema_name = self.lakebase_schema or "payment_analysis"
            username = (
                (ws.current_user.me().user_name if ws.current_user else None)
                or getattr(ws.config, "client_id", None)
                or "postgres"
            )
            conn_str = (
                f"host={host} port=5432 dbname=databricks_postgres user={username} "
                f"password={cred.token} sslmode=require"
            )
            allowed = ("authentication", "retry", "routing")
            filter_type = rule_type if rule_type and rule_type in allowed else None
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
            where = f"WHERE rule_type = '{rule_type}'" if rule_type else ""
            query = f"""
                SELECT name, rule_type, action_summary, condition_expression, priority
                FROM {self.catalog}.{self.schema}.v_approval_rules_active
                {where}
                ORDER BY priority ASC
                LIMIT 50
            """
            return self._execute_sql(query)
        except Exception as e:
            logger.warning("Could not load Lakehouse approval rules: %s", e)
            return []


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
    ):
        super().__init__(
            AgentRole.SMART_ROUTING,
            catalog,
            schema,
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
            segment = kwargs.get("merchant_segment", "Retail")
            query = f"""
            SELECT 
                payment_solution,
                AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) * 100 as approval_rate,
                AVG(processing_time_ms) as latency,
                COUNT(*) as volume
            FROM {self.catalog}.{self.schema}.payments_enriched_silver
            WHERE merchant_segment = '{segment}'
              AND event_date >= CURRENT_DATE - 30
            GROUP BY payment_solution
            ORDER BY approval_rate DESC
            LIMIT 3
            """
            return self._execute_sql(query)

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
    ):
        super().__init__(
            AgentRole.SMART_RETRY,
            catalog,
            schema,
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
            min_amount = kwargs.get("min_amount", 100)
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
    ):
        super().__init__(
            AgentRole.DECLINE_ANALYST,
            catalog,
            schema,
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
    ):
        super().__init__(
            AgentRole.RISK_ASSESSOR,
            catalog,
            schema,
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
            threshold = kwargs.get("threshold", 0.7)
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
    ):
        super().__init__(
            AgentRole.PERFORMANCE_RECOMMENDER,
            catalog,
            schema,
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

        self.add_tool(AgentTool(
            name="get_trend_analysis",
            description="Get performance trends over time",
            function=get_trend_analysis,
            parameters={}
        ))


class OrchestratorAgent(BaseAgent):
    """Meta-agent that coordinates all specialized agents."""

    def __init__(
        self,
        catalog: str,
        schema: str,
        *,
        lakebase_project_id: str = "",
        lakebase_branch_id: str = "",
        lakebase_endpoint_id: str = "",
        lakebase_schema: str = "payment_analysis",
    ):
        super().__init__(
            AgentRole.ORCHESTRATOR,
            catalog,
            schema,
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
        }
        # Initialize all specialist agents (approval rules from Lakebase when IDs set)
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

    def handle_query(self, query: str) -> Dict:
        """Route query to appropriate agents and synthesize response."""
        query_lower = query.lower()
        responses = {}

        if any(word in query_lower for word in ["routing", "cascade", "processor", "route"]):
            responses["smart_routing"] = self.smart_routing.think(query)
        if any(word in query_lower for word in ["retry", "recovery", "reprocess", "failed"]):
            responses["smart_retry"] = self.smart_retry.think(query)
        if any(word in query_lower for word in ["decline", "reject", "fail", "denied"]):
            responses["decline_analyst"] = self.decline_analyst.think(query)
        if any(word in query_lower for word in ["fraud", "risk", "suspicious", "aml"]):
            responses["risk_assessor"] = self.risk_assessor.think(query)
        if any(word in query_lower for word in ["performance", "optimize", "improve", "recommend", "kpi"]):
            responses["performance_recommender"] = self.performance_recommender.think(query)
        if not responses:
            responses["performance_recommender"] = self.performance_recommender.think(query)

        # Synthesize responses
        synthesis = self._synthesize_responses(responses)

        return {
            "query": query,
            "agents_used": list(responses.keys()),
            "agent_responses": responses,
            "synthesis": synthesis
        }

    def _synthesize_responses(self, responses: Dict[str, str]) -> str:
        """Synthesize responses from multiple agents."""
        synthesis = "=== ORCHESTRATED AGENT RESPONSE ===\n\n"

        for agent_name, response in responses.items():
            synthesis += f"[{agent_name.upper().replace('_', ' ')}]\n{response}\n\n"

        synthesis += "=== END ORCHESTRATED RESPONSE ===\n"
        return synthesis


def setup_agent_framework(
    catalog: str = "ahs_demos_catalog",
    schema: str = "payment_analysis",
    *,
    lakebase_project_id: str = "",
    lakebase_branch_id: str = "",
    lakebase_endpoint_id: str = "",
    lakebase_schema: str = "payment_analysis",
) -> OrchestratorAgent:
    """Initialize the multi-agent framework. When Lakebase IDs are set, approval rules are read from OLTP Lakebase Postgres."""
    orchestrator = OrchestratorAgent(
        catalog,
        schema,
        lakebase_project_id=lakebase_project_id,
        lakebase_branch_id=lakebase_branch_id,
        lakebase_endpoint_id=lakebase_endpoint_id,
        lakebase_schema=lakebase_schema,
    )
    logger.info("Agent framework initialized (Orchestrator + 5 specialists)")
    return orchestrator


def get_notebook_config() -> Dict[str, Any]:
    """Read job/notebook parameters from Databricks widgets or return defaults. Used as single source for catalog, schema, query, and Lakebase connection."""
    defaults = {
        "catalog": "ahs_demos_catalog",
        "schema": "payment_analysis",
        "query": "Run comprehensive payment analysis: routing, retries, declines, risk, and performance optimizations.",
        "agent_role": "orchestrator",
        "lakebase_project_id": "",
        "lakebase_branch_id": "",
        "lakebase_endpoint_id": "",
        "lakebase_schema": "payment_analysis",
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
        return {
            "catalog": dbutils.widgets.get("catalog") or defaults["catalog"],
            "schema": dbutils.widgets.get("schema") or defaults["schema"],
            "query": dbutils.widgets.get("query") or defaults["query"],
            "agent_role": (dbutils.widgets.get("agent_role") or defaults["agent_role"]).strip(),
            "lakebase_project_id": (dbutils.widgets.get("lakebase_project_id") or "").strip(),
            "lakebase_branch_id": (dbutils.widgets.get("lakebase_branch_id") or "").strip(),
            "lakebase_endpoint_id": (dbutils.widgets.get("lakebase_endpoint_id") or "").strip(),
            "lakebase_schema": (dbutils.widgets.get("lakebase_schema") or defaults["lakebase_schema"]).strip() or "payment_analysis",
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
    lakebase_kw = {
        "lakebase_project_id": config.get("lakebase_project_id") or "",
        "lakebase_branch_id": config.get("lakebase_branch_id") or "",
        "lakebase_endpoint_id": config.get("lakebase_endpoint_id") or "",
        "lakebase_schema": config.get("lakebase_schema") or "payment_analysis",
    }

    if agent_role == "orchestrator":
        orchestrator = setup_agent_framework(catalog, schema, **lakebase_kw)
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
        agent = agent_class(catalog, schema, **lakebase_kw)
        response = agent.think(query)
        return {"query": query, "agents_used": [agent_role], "agent_responses": {agent_role: response}, "synthesis": response}
    raise ValueError(f"Unknown agent_role={agent_role!r}. Use one of: orchestrator, {', '.join(specialist_map)}")


# Databricks notebook entry point (Job 6: single task run_agent_framework)
if __name__ == "__main__":
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
