"""
Databricks Service - Unity Catalog and Model Serving Integration.

This module provides a clean interface for:
- Executing SQL queries on SQL Warehouse
- Fetching analytics from Unity Catalog views
- Calling ML model serving endpoints

Design Patterns:
- Singleton pattern for service instance
- Async/await for non-blocking I/O
- Analytics always returns real Databricks data or empty results (no synthetic fallback)
- ML model serving endpoints use MockDataGenerator only when serving endpoint is unavailable
- Type hints throughout for IDE support
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..config import DEFAULT_ENTITY, get_default_schema

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class RiskTier(str, Enum):
    """Risk classification tiers."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    
    @classmethod
    def from_score(cls, score: float) -> "RiskTier":
        """Determine risk tier from numeric score."""
        if score < 0.3:
            return cls.LOW
        elif score < 0.7:
            return cls.MEDIUM
        return cls.HIGH


def _validate_sql_identifier(value: str, label: str = "identifier") -> str:
    """Validate that a value is a safe SQL identifier (alphanumeric + underscore only)."""
    if not value.replace("_", "").isalnum():
        raise ValueError(f"Invalid {label}: {value!r} — only alphanumeric and underscore allowed")
    return value


@dataclass(frozen=True)
class DatabricksConfig:
    """
    Immutable configuration for Databricks connection.
    
    Attributes:
        host: Databricks workspace URL
        token: Personal access token or OAuth token (OBO)
        client_id: OAuth client ID (service principal); used when token is not set
        client_secret: OAuth client secret (service principal)
        warehouse_id: SQL Warehouse ID for query execution
        catalog: Unity Catalog name
        schema: Schema name within the catalog
    """
    host: str | None = None
    token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    warehouse_id: str | None = None
    catalog: str = "ahs_demos_catalog"
    schema: str = "payment_analysis"

    def __post_init__(self) -> None:
        """Validate catalog and schema to prevent SQL injection."""
        _validate_sql_identifier(self.catalog, "catalog")
        _validate_sql_identifier(self.schema, "schema")

    @classmethod
    def from_environment(cls) -> "DatabricksConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("DATABRICKS_HOST"),
            token=os.getenv("DATABRICKS_TOKEN"),
            client_id=os.getenv("DATABRICKS_CLIENT_ID"),
            client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
            warehouse_id=os.getenv("DATABRICKS_WAREHOUSE_ID") or None,
            catalog=os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog"),
            schema=os.getenv("DATABRICKS_SCHEMA") or get_default_schema(),
        )
    
    @property
    def full_schema_name(self) -> str:
        """Return fully qualified schema name."""
        return f"{self.catalog}.{self.schema}"


# =============================================================================
# Service Implementation
# =============================================================================

# ML model registry: static metadata enriched with live UC metrics in get_ml_models().
_ML_MODEL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "approval_propensity",
        "name": "Approval Propensity Model",
        "description": "Predicts the probability that a transaction will be approved (binary classification). Used for routing and retry decisions to prioritize high-propensity flows.",
        "model_type": "HistGradientBoostingClassifier",
        "features": ["amount", "fraud_score", "device_trust_score", "is_cross_border", "retry_count", "uses_3ds"],
        "model_suffix": "approval_propensity_model",
    },
    {
        "id": "risk_scoring",
        "name": "Risk Scoring Model",
        "description": "Classifies transactions as high-risk (fraud or decline) vs low-risk. Combines fraud score, AML score, and behavioral signals for decline and routing decisions.",
        "model_type": "HistGradientBoostingClassifier",
        "features": ["amount", "fraud_score", "aml_risk_score", "is_cross_border", "processing_time_ms", "device_trust_score"],
        "model_suffix": "risk_scoring_model",
    },
    {
        "id": "smart_routing",
        "name": "Smart Routing Policy",
        "description": "Multiclass classifier that recommends payment solution (standard, 3DS, network token, passkey) to maximize approval rate given merchant segment, risk, and 3DS usage.",
        "model_type": "HistGradientBoostingClassifier",
        "features": ["amount", "fraud_score", "is_cross_border", "uses_3ds", "device_trust_score", "merchant_segment_*"],
        "model_suffix": "smart_routing_policy",
    },
    {
        "id": "smart_retry",
        "name": "Smart Retry Policy",
        "description": "Predicts whether a declined transaction is recoverable (worth retrying). Trained on decline reason, retry context, and merchant policy to recommend retry timing and strategy.",
        "model_type": "HistGradientBoostingClassifier",
        "features": [
            "decline_encoded", "retry_scenario_encoded", "retry_count", "amount",
            "is_recurring", "fraud_score", "device_trust_score", "attempt_sequence",
            "time_since_last_attempt_seconds", "prior_approved_count",
            "merchant_retry_policy_max_attempts",
        ],
        "model_suffix": "smart_retry_policy",
    },
]


@dataclass
class DatabricksService:
    """
    Service for interacting with Databricks APIs.
    
    Provides methods for:
    - SQL query execution on SQL Warehouse
    - KPI retrieval from Unity Catalog
    - ML model inference via Model Serving
    
    Example:
        service = DatabricksService.create()
        kpis = await service.get_kpis()
    """
    
    config: DatabricksConfig = field(default_factory=DatabricksConfig.from_environment)
    _client: "WorkspaceClient | None" = field(default=None, repr=False)
    
    @classmethod
    def create(cls, config: DatabricksConfig | None = None) -> "DatabricksService":
        """Factory method to create service instance.

        Always returns a DatabricksService (never None). If config resolution
        fails, logs the error and returns a service with default config that
        will report ``is_available = False`` on first use.
        """
        try:
            resolved = config or DatabricksConfig.from_environment()
        except Exception as exc:
            logger.warning("Failed to resolve Databricks config, service will be unavailable: %s", exc)
            resolved = DatabricksConfig()
        return cls(config=resolved)
    
    @property
    def client(self) -> "WorkspaceClient | None":
        """Lazy-initialize Databricks SDK client."""
        if self._client is None:
            self._client = self._initialize_client()
        return self._client
    
    def _initialize_client(self) -> "WorkspaceClient | None":
        """Initialize the Databricks SDK client with error handling (PAT/OBO or service principal)."""
        host = self.config.host
        if not host:
            return None
        try:
            from ..databricks_client_helpers import workspace_client_pat_only, workspace_client_service_principal

            token = self.config.token
            if token:
                client = workspace_client_pat_only(host=host, token=token)
            elif self.config.client_id and self.config.client_secret:
                client = workspace_client_service_principal(
                    host=host,
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret,
                )
            else:
                return None
            logger.info("Databricks client initialized successfully")
            return client
        except ImportError:
            logger.warning("Databricks SDK not installed")
        except Exception as e:
            logger.warning(f"Failed to initialize Databricks client: {e}")
        return None
    
    @property
    def is_available(self) -> bool:
        """Check if Databricks connection is available."""
        return self.client is not None
    
    # =========================================================================
    # Query Execution
    # =========================================================================

    # Track whether the last query used mock data so callers/frontend can indicate it
    _last_query_used_mock: bool = False

    async def execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute SQL query on SQL Warehouse.
        
        After calling, check ``self._last_query_used_mock`` to determine whether
        the response came from real Lakehouse data or was empty (Databricks unavailable).
        
        Args:
            query: SQL query string
            
        Returns:
            List of row dictionaries (empty when Databricks is unavailable)
        """
        if not self.is_available:
            logger.warning("Databricks unavailable; returning empty result set")
            self._last_query_used_mock = True
            return []
        
        try:
            result = await self._execute_query_internal(query)
            self._last_query_used_mock = False
            return result
        except Exception as e:
            err_str = str(e).lower()
            if "invalid scope" in err_str or ("403" in err_str and "forbidden" in err_str):
                logger.error(
                    "Query execution failed (likely missing SQL scope): %s. "
                    "Add the 'sql' scope in Compute → Apps → payment-analysis → Edit → Configure → Authorization scopes, then restart the app.",
                    e,
                )
            else:
                logger.error("Query execution failed: %s", e)
            self._last_query_used_mock = True
            return []
    
    async def _execute_query_parameterized(
        self,
        query: str,
        params: dict[str, str | int | float | bool],
    ) -> list[dict[str, Any]]:
        """Execute a SQL query with named :param parameters and return row dicts.

        Uses ``StatementParameterListItem`` for safe value binding.
        """
        from databricks.sdk.service.sql import StatementParameterListItem, StatementState

        client = self.client
        if client is None or not self.is_available:
            return []

        warehouse_id = self._get_warehouse_id()
        if not warehouse_id:
            return []

        stmt_params = [
            StatementParameterListItem(name=k, value=str(v), type="STRING")
            for k, v in params.items()
        ] or None

        response = client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            parameters=stmt_params,
            wait_timeout="30s",
        )

        if not response.status or response.status.state != StatementState.SUCCEEDED:
            return []
        return self._parse_statement_result(response)

    @staticmethod
    def _parse_statement_result(response: Any) -> list[dict[str, Any]]:
        """Extract row dicts from a StatementResponse (shared by query helpers)."""
        if not response.manifest or not response.manifest.schema or not response.result:
            return []
        columns_info = response.manifest.schema.columns
        if not columns_info:
            return []
        columns = [col.name for col in columns_info]
        rows = response.result.data_array or []
        return [dict(zip(columns, row)) for row in rows]

    async def _execute_query_internal(self, query: str) -> list[dict[str, Any]]:
        """Internal query execution with full error handling."""
        from databricks.sdk.service.sql import StatementState

        client = self.client
        if client is None:
            raise RuntimeError("Databricks client not available")

        warehouse_id = self._get_warehouse_id()
        if not warehouse_id:
            raise RuntimeError("No SQL Warehouse available")

        response = client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            wait_timeout="30s",
        )
        
        if not response.status or response.status.state != StatementState.SUCCEEDED:
            error = response.status.error if response.status else "Unknown error"
            raise RuntimeError(f"Query failed: {error}")
        
        return self._parse_statement_result(response)

    async def execute_non_query_parameterized(
        self,
        statement: str,
        params: dict[str, str | int | float | bool] | None = None,
    ) -> bool:
        """Execute a SQL statement with named parameters (INSERT/UPDATE/DDL).

        Uses :name syntax in the statement and StatementParameterListItem for
        safe value binding — prevents SQL injection for user-supplied data.

        Returns True on success; raises RuntimeError on failure.
        """
        if not self.is_available:
            raise RuntimeError("Databricks connection is not available")
        client = self.client
        if client is None:
            raise RuntimeError("Databricks client could not be initialized")

        from databricks.sdk.service.sql import StatementParameterListItem, StatementState

        warehouse_id = self._get_warehouse_id()
        if not warehouse_id:
            raise RuntimeError("No SQL Warehouse available")

        stmt_params = [
            StatementParameterListItem(name=k, value=str(v), type="STRING")
            for k, v in (params or {}).items()
        ] or None

        response = client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=statement,
            parameters=stmt_params,
            wait_timeout="30s",
        )
        if not response.status or response.status.state != StatementState.SUCCEEDED:
            error_msg = ""
            if response.status and response.status.error:
                error_msg = str(response.status.error.message or "")
            raise RuntimeError(f"Non-query execution failed: {error_msg}")
        return True

    async def execute_non_query(self, statement: str) -> bool:
        """
        Execute a SQL statement that does not return rows (INSERT/UPDATE/DDL).

        Returns:
            True if the statement succeeded.

        Raises:
            RuntimeError: If client/warehouse unavailable or statement execution failed
                (includes server error message for app_config and similar callers).
        """
        if not self.is_available:
            logger.warning("Databricks unavailable, skipping non-query execution")
            raise RuntimeError("Databricks connection is not available")

        client = self.client
        if client is None:
            raise RuntimeError("Databricks client could not be initialized")

        from databricks.sdk.service.sql import StatementState

        warehouse_id = self._get_warehouse_id()
        if not warehouse_id:
            raise RuntimeError(
                "No SQL Warehouse available. Set DATABRICKS_WAREHOUSE_ID in the app environment."
            )

        response = client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=statement,
            wait_timeout="30s",
        )
        if not response.status:
            raise RuntimeError("Statement execution returned no status")
        if response.status.state != StatementState.SUCCEEDED:
            err_obj = getattr(response.status, "error", None)
            err = (
                getattr(err_obj, "message", None) if err_obj else None
            ) or getattr(response.status, "error_message", None) or str(response.status)
            logger.error("Statement execution failed: %s", err)
            raise RuntimeError(err or "Statement execution failed")
        return True
    
    def _get_warehouse_id(self) -> str | None:
        """Get warehouse ID from config or discover first available."""
        if self.config.warehouse_id:
            return self.config.warehouse_id

        client = self.client
        if client is None:
            return None

        warehouses = list(client.warehouses.list())
        return warehouses[0].id if warehouses else None
    
    # =========================================================================
    # Analytics Methods
    # =========================================================================
    
    async def get_kpis(self) -> dict[str, Any]:
        """Fetch executive KPIs from Unity Catalog."""
        query = f"""
            SELECT 
                total_transactions,
                approved_count,
                approval_rate_pct,
                avg_fraud_score,
                total_transaction_value,
                period_start,
                period_end
            FROM {self.config.full_schema_name}.v_executive_kpis
            LIMIT 1
        """
        
        results = await self.execute_query(query)
        
        if results:
            row = results[0]
            total = row.get("total_transactions", 0) or 0
            approved = row.get("approved_count", 0) or 0
            rate_pct = row.get("approval_rate_pct")
            if rate_pct is None and total:
                rate_pct = (approved * 100.0 / total) if total else 0.0
            else:
                rate_pct = float(rate_pct) if rate_pct is not None else 0.0
            return {
                "total_transactions": total,
                "approved_count": approved,
                "approval_rate": rate_pct,
                "avg_fraud_score": row.get("avg_fraud_score", 0.0),
                "total_value": row.get("total_transaction_value", 0.0),
                "period_start": str(row.get("period_start", "")),
                "period_end": str(row.get("period_end", "")),
            }
        
        return {"total_transactions": 0, "approved_count": 0, "approval_rate": 0.0, "avg_fraud_score": 0.0, "total_value": 0.0, "period_start": "", "period_end": ""}
    
    async def get_approval_trends(self, seconds: int = 3600) -> list[dict[str, Any]]:
        """Fetch approval rate trends by second (real-time; last N seconds, max 3600)."""
        seconds = min(max(seconds, 1), 3600)  # Clamp to 1-3600 seconds (1 hour)
        
        query = f"""
            SELECT event_second, transaction_count, approved_count,
                   approval_rate_pct, avg_fraud_score, total_value
            FROM {self.config.full_schema_name}.v_approval_trends_hourly
            ORDER BY event_second DESC
            LIMIT {seconds}
        """
        
        results = await self.execute_query(query)
        return results or []
    
    async def get_decline_summary(self) -> list[dict[str, Any]]:
        """Fetch top decline reasons with recovery potential."""
        query = f"""
            SELECT decline_reason, decline_count, pct_of_declines,
                   total_declined_value, avg_amount, recoverable_pct
            FROM {self.config.full_schema_name}.v_top_decline_reasons
            ORDER BY decline_count DESC
            LIMIT 10
        """
        
        results = await self.execute_query(query)
        return results or []
    
    async def get_solution_performance(self) -> list[dict[str, Any]]:
        """Fetch performance metrics by payment solution."""
        query = f"""
            SELECT payment_solution, transaction_count, approved_count,
                   approval_rate_pct, avg_amount, total_value
            FROM {self.config.full_schema_name}.v_solution_performance
            ORDER BY transaction_count DESC
        """
        
        results = await self.execute_query(query)
        return results or []

    async def get_smart_checkout_service_paths(self, entity: str = DEFAULT_ENTITY, limit: int = 25) -> list[dict[str, Any]]:
        """Fetch payment-link performance by Smart Checkout service path for the given entity."""
        limit = max(1, min(limit, 100))
        # UC view names (e.g. v_*_br) are entity-specific artifacts; API uses entity param (default BR) for filtering and future multi-entity support.
        query = f"""
            SELECT
              service_path,
              transaction_count,
              approved_count,
              approval_rate_pct,
              avg_fraud_score,
              total_value,
              antifraud_declines,
              antifraud_pct_of_declines
            FROM {self.config.full_schema_name}.v_smart_checkout_service_path_br
            ORDER BY transaction_count DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_smart_checkout_path_performance(self, entity: str = DEFAULT_ENTITY, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch payment-link performance by recommended Smart Checkout path for the given entity."""
        limit = max(1, min(limit, 50))
        query = f"""
            SELECT
              recommended_path,
              transaction_count,
              approved_count,
              approval_rate_pct,
              total_value
            FROM {self.config.full_schema_name}.v_smart_checkout_path_performance_br
            ORDER BY transaction_count DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_3ds_funnel(self, entity: str = DEFAULT_ENTITY, days: int = 30) -> list[dict[str, Any]]:
        """Fetch payment-link 3DS funnel metrics by day for the given entity."""
        days = max(1, min(days, 90))
        query = f"""
            SELECT
              event_date,
              total_transactions,
              three_ds_routed_count,
              three_ds_friction_count,
              three_ds_authenticated_count,
              issuer_approved_after_auth_count,
              three_ds_friction_rate_pct,
              three_ds_authentication_rate_pct,
              issuer_approval_post_auth_rate_pct
            FROM {self.config.full_schema_name}.v_3ds_funnel_br
            WHERE event_date >= CURRENT_DATE - {days}
            ORDER BY event_date DESC
        """
        results = await self.execute_query(query)
        return results or []

    async def get_reason_codes(self, entity: str = DEFAULT_ENTITY, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch declines consolidated into unified reason-code taxonomy for the given entity."""
        limit = max(1, min(limit, 200))
        query = f"""
            SELECT
              entry_system,
              flow_type,
              decline_reason_standard,
              decline_reason_group,
              recommended_action,
              decline_count,
              pct_of_declines,
              total_declined_value,
              avg_amount,
              affected_merchants
            FROM {self.config.full_schema_name}.v_reason_codes_br
            ORDER BY decline_count DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_reason_code_insights(self, entity: str = DEFAULT_ENTITY, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch reason-code insights with estimated recoverability for the given entity (demo heuristic)."""
        limit = max(1, min(limit, 200))
        query = f"""
            SELECT
              entry_system,
              flow_type,
              decline_reason_standard,
              decline_reason_group,
              recommended_action,
              decline_count,
              pct_of_declines,
              total_declined_value,
              estimated_recoverable_declines,
              estimated_recoverable_value,
              priority
            FROM {self.config.full_schema_name}.v_reason_code_insights_br
            ORDER BY priority ASC, estimated_recoverable_value DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_entry_system_distribution(self, entity: str = DEFAULT_ENTITY) -> list[dict[str, Any]]:
        """Fetch transaction distribution by entry system for the given entity."""
        query = f"""
            SELECT
              entry_system,
              transaction_count,
              approved_count,
              approval_rate_pct,
              total_value
            FROM {self.config.full_schema_name}.v_entry_system_distribution_br
            ORDER BY transaction_count DESC
        """
        results = await self.execute_query(query)
        return results or []

    async def get_last_hour_performance(self) -> dict[str, Any]:
        """Fetch last-hour performance (transactions, approval rate, etc.) for real-time monitor."""
        query = f"""
            SELECT transactions_last_hour, approval_rate_pct, avg_fraud_score, total_value,
                   active_segments, high_risk_transactions, declines_last_hour
            FROM {self.config.full_schema_name}.v_last_hour_performance
            LIMIT 1
        """
        results = await self.execute_query(query)
        if results:
            row = results[0]
            return {
                "transactions_last_hour": int(row.get("transactions_last_hour", 0) or 0),
                "approval_rate_pct": float(row.get("approval_rate_pct", 0) or 0),
                "avg_fraud_score": float(row.get("avg_fraud_score", 0) or 0),
                "total_value": float(row.get("total_value", 0) or 0),
                "active_segments": int(row.get("active_segments", 0) or 0),
                "high_risk_transactions": int(row.get("high_risk_transactions", 0) or 0),
                "declines_last_hour": int(row.get("declines_last_hour", 0) or 0),
            }
        return {"transactions_last_hour": 0, "approval_rate_pct": 0.0, "avg_fraud_score": 0.0, "total_value": 0.0, "active_segments": 0, "high_risk_transactions": 0, "declines_last_hour": 0}

    async def get_last_60_seconds_performance(self) -> dict[str, Any]:
        """Fetch last-60-seconds performance for real-time live metrics (v_last_60_seconds_performance)."""
        query = f"""
            SELECT transactions_last_60s, approval_rate_pct, avg_fraud_score, total_value, declines_last_60s
            FROM {self.config.full_schema_name}.v_last_60_seconds_performance
            LIMIT 1
        """
        results = await self.execute_query(query)
        if results:
            row = results[0]
            return {
                "transactions_last_60s": int(row.get("transactions_last_60s", 0) or 0),
                "approval_rate_pct": float(row.get("approval_rate_pct", 0) or 0),
                "avg_fraud_score": float(row.get("avg_fraud_score", 0) or 0),
                "total_value": float(row.get("total_value", 0) or 0),
                "declines_last_60s": int(row.get("declines_last_60s", 0) or 0),
            }
        return {"transactions_last_60s": 0, "approval_rate_pct": 0.0, "avg_fraud_score": 0.0, "total_value": 0.0, "declines_last_60s": 0}

    async def get_streaming_tps(self, limit_seconds: int = 300) -> list[dict[str, Any]]:
        """Fetch real-time TPS (transactions per second) from v_streaming_volume_per_second for live monitor."""
        limit_seconds = max(10, min(limit_seconds, 3600))
        query = f"""
            SELECT event_second, records_per_second
            FROM {self.config.full_schema_name}.v_streaming_volume_per_second
            ORDER BY event_second ASC
            LIMIT {limit_seconds}
        """
        try:
            results = await self.execute_query(query)
            if results:
                return [
                    {
                        "event_second": str(row.get("event_second", "") or ""),
                        "records_per_second": int(row.get("records_per_second", 0) or 0),
                    }
                    for row in results
                ]
        except Exception as e:
            logger.debug("get_streaming_tps failed: %s", e)
        return []

    async def get_command_center_entry_throughput(
        self, entity: str = DEFAULT_ENTITY, limit_minutes: int = 30
    ) -> list[dict[str, Any]]:
        """Throughput by entry system (PD, WS, SEP, Checkout) for Command Center.

        First tries to derive real shares from ``v_entry_system_distribution`` for the
        entity, then multiplies them by real-time TPS from ``v_streaming_volume_per_second``.
        Returns empty list when no streaming data is available.
        """
        limit_seconds = max(1, min(limit_minutes, 60)) * 60
        try:
            tps_list = await self.get_streaming_tps(limit_seconds=limit_seconds)
            if not tps_list:
                return []

            # Get real entry-system shares from Databricks (no hardcoded fallback —
            # when distribution is unavailable, use equal shares so the chart
            # still renders with correct total TPS but without misleading proportions).
            shares: dict[str, float] = {"PD": 0.25, "WS": 0.25, "SEP": 0.25, "Checkout": 0.25}
            try:
                dist_data = await self.get_entry_system_distribution(entity=entity)
                if dist_data:
                    total = sum(int(r.get("transaction_count", 0)) for r in dist_data)
                    if total > 0:
                        real_shares: dict[str, float] = {}
                        for r in dist_data:
                            es = str(r.get("entry_system", "")).strip()
                            cnt = int(r.get("transaction_count", 0))
                            # Normalize entry system name → short code
                            key = es if es in ("PD", "WS", "SEP", "Checkout") else es[:10]
                            real_shares[key] = cnt / total
                        if real_shares:
                            # Merge into defaults so all 4 keys always exist
                            shares = {k: real_shares.get(k, 0.0) for k in shares}
                            # Redistribute any unaccounted share equally
                            accounted = sum(shares.values())
                            if accounted < 0.99:
                                missing = [k for k, v in shares.items() if v == 0.0]
                                if missing:
                                    leftover = (1.0 - accounted) / len(missing)
                                    for k in missing:
                                        shares[k] = leftover
            except Exception:
                pass  # Use default shares if distribution view unavailable

            return [
                {
                    "ts": row["event_second"],
                    **{
                        k: max(0, int(row["records_per_second"] * v))
                        for k, v in shares.items()
                    },
                }
                for row in tps_list
            ]
        except Exception as e:
            logger.debug("get_command_center_entry_throughput failed: %s", e)
        return []

    async def get_data_quality_summary(self) -> dict[str, Any]:
        """Fetch data quality summary (bronze/silver volumes, retention) from Databricks."""
        query = f"""
            SELECT bronze_last_24h, silver_last_24h, retention_pct_24h,
                   latest_bronze_ingestion, latest_silver_event
            FROM {self.config.full_schema_name}.v_data_quality_summary
            LIMIT 1
        """
        try:
            results = await self.execute_query(query)
            if results:
                row = results[0]
                return {
                    "bronze_last_24h": int(row.get("bronze_last_24h", 0) or 0),
                    "silver_last_24h": int(row.get("silver_last_24h", 0) or 0),
                    "retention_pct_24h": float(row.get("retention_pct_24h", 0) or 0),
                    "latest_bronze_ingestion": str(row.get("latest_bronze_ingestion", "") or ""),
                    "latest_silver_event": str(row.get("latest_silver_event", "") or ""),
                }
        except Exception as e:
            logger.debug("get_data_quality_summary failed: %s", e)
        return {"bronze_last_24h": 0, "silver_last_24h": 0, "retention_pct_24h": 0.0, "latest_bronze_ingestion": "", "latest_silver_event": ""}

    async def get_active_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch active alerts from v_active_alerts (approval rate drop, high fraud, etc.)."""
        limit = max(1, min(limit, 100))
        query = f"""
            SELECT alert_type, severity, metric_name, current_value, threshold_value,
                   alert_message, first_detected
            FROM {self.config.full_schema_name}.v_active_alerts
            ORDER BY severity DESC, first_detected DESC
            LIMIT {limit}
        """
        try:
            results = await self.execute_query(query)
            if results:
                return [
                    {
                        "alert_type": str(r.get("alert_type", "")),
                        "severity": str(r.get("severity", "MEDIUM")),
                        "metric_name": str(r.get("metric_name", "")),
                        "current_value": float(r.get("current_value", 0) or 0),
                        "threshold_value": float(r.get("threshold_value", 0) or 0),
                        "alert_message": str(r.get("alert_message", "")),
                        "first_detected": str(r.get("first_detected", "")),
                    }
                    for r in results
                ]
        except Exception as e:
            logger.debug("get_active_alerts failed: %s", e)
        return []

    async def get_performance_by_geography(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch transaction counts and approval rate by country for geographic distribution and world map."""
        limit = max(1, min(limit, 200))
        query = f"""
            SELECT country, transaction_count, approval_rate_pct, total_transaction_value
            FROM {self.config.full_schema_name}.v_performance_by_geography
            ORDER BY transaction_count DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_countries(self, limit: int = 200) -> list[dict[str, Any]]:
        """Fetch countries/entities from Lakehouse table for the filter dropdown. Users can add/remove rows in the table."""
        limit = max(1, min(limit, 500))
        query = f"""
            SELECT code, name
            FROM {self.config.full_schema_name}.countries
            WHERE is_active = true
            ORDER BY display_order ASC, name ASC
            LIMIT {limit}
        """
        try:
            results = await self.execute_query(query)
            if results:
                return [{"code": str(r.get("code", "")).strip() or "", "name": str(r.get("name", "")).strip() or ""} for r in results]
        except Exception as e:
            logger.debug("get_countries failed (table may not exist yet): %s", e)
        return []

    async def get_dedup_collision_stats(self) -> dict[str, Any]:
        """Fetch dedup collision stats (double-counting guardrail)."""
        query = f"""
            SELECT
              colliding_keys,
              avg_rows_per_key,
              avg_entry_systems_per_key,
              avg_transaction_ids_per_key
            FROM {self.config.full_schema_name}.v_dedup_collision_stats
            LIMIT 1
        """
        results = await self.execute_query(query)
        return results[0] if results else {"colliding_keys": 0, "avg_rows_per_key": 0, "avg_entry_systems_per_key": 0, "avg_transaction_ids_per_key": 0}

    async def get_false_insights_metric(self, days: int = 30) -> list[dict[str, Any]]:
        """Fetch False Insights counter-metric time series."""
        days = max(1, min(days, 180))
        query = f"""
            SELECT
              event_date,
              reviewed_insights,
              false_insights,
              false_insights_pct
            FROM {self.config.full_schema_name}.v_false_insights_metric
            WHERE event_date >= CURRENT_DATE - {days}
            ORDER BY event_date DESC
        """
        results = await self.execute_query(query)
        return results or []

    async def get_retry_performance(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch Smart Retry performance (scenario split) from Unity Catalog."""
        limit = max(1, min(limit, 200))
        query = f"""
            SELECT
              retry_scenario,
              decline_reason_standard,
              retry_count,
              retry_attempts,
              success_rate_pct,
              recovered_value,
              avg_fraud_score,
              avg_time_since_last_attempt_s,
              avg_prior_approvals,
              baseline_approval_pct,
              incremental_lift_pct,
              effectiveness
            FROM {self.config.full_schema_name}.v_retry_performance
            ORDER BY retry_attempts DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_recommendations_from_lakehouse(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch approval recommendations from Lakehouse (UC table) for similar cases / Vector Search results."""
        limit = max(1, min(limit, 100))
        query = f"""
            SELECT id, context_summary, recommended_action, score, source_type, created_at
            FROM {self.config.full_schema_name}.v_recommendations_from_lakehouse
            LIMIT {limit}
        """
        try:
            results = await self.execute_query(query)
            return results or []
        except Exception as e:
            logger.debug("get_recommendations_from_lakehouse failed: %s", e)
            return []

    async def vector_search_similar(
        self, description: str, num_results: int = 5
    ) -> list[dict[str, Any]]:
        """Search for similar transactions using Databricks Vector Search.

        Uses the ``VECTOR_SEARCH()`` table-valued function (TVF) against the
        ``similar_transactions_index`` Vector Search index — the same pattern
        used by the UC agent tool ``search_similar_transactions``.

        Falls back to a plain SQL lookup (by transaction volume) when the
        Vector Search index is not available (e.g. index not yet created).
        """
        num_results = max(1, min(num_results, 20))

        # ── Primary: Databricks Vector Search TVF ──────────────────────
        vs_query = f"""
            SELECT
                merchant_segment, issuer_country, payment_solution,
                ROUND(approval_rate_pct, 2) AS approval_rate_pct,
                ROUND(avg_fraud_score, 4) AS avg_fraud_score,
                ROUND(avg_amount, 2) AS avg_amount,
                transaction_count
            FROM VECTOR_SEARCH(
                index => '{self.config.full_schema_name}.similar_transactions_index',
                query_text => :description,
                num_results => {num_results}
            )
        """
        try:
            from databricks.sdk.service.sql import StatementParameterListItem

            client = self.client
            warehouse_id = self._get_warehouse_id()
            if client and warehouse_id:
                params = [
                    StatementParameterListItem(name="description", value=description, type="STRING"),
                ]
                result = client.statement_execution.execute_statement(
                    statement=vs_query,
                    warehouse_id=warehouse_id,
                    parameters=params,
                    wait_timeout="30s",
                )
                from databricks.sdk.service.sql import StatementState

                if result.status and result.status.state == StatementState.SUCCEEDED and result.result:
                    manifest_schema = getattr(result.manifest, "schema", None) if result.manifest else None
                    columns = [col.name for col in (manifest_schema.columns or [])] if manifest_schema and manifest_schema.columns else []
                    rows = []
                    for chunk in result.result.data_array or []:
                        row = dict(zip(columns, chunk))
                        rows.append({
                            "merchant_segment": str(row.get("merchant_segment", "")),
                            "issuer_country": str(row.get("issuer_country", "")),
                            "payment_solution": str(row.get("payment_solution", "")),
                            "approval_rate_pct": float(row.get("approval_rate_pct", 0) or 0),
                            "avg_fraud_score": float(row.get("avg_fraud_score", 0) or 0),
                            "avg_amount": float(row.get("avg_amount", 0) or 0),
                            "transaction_count": int(row.get("transaction_count", 0) or 0),
                        })
                    if rows:
                        return rows
        except Exception as e:
            logger.debug("Vector Search TVF failed (index may not exist yet), falling back to SQL: %s", e)

        # ── Fallback: plain SQL when Vector Search index is not available ──
        fallback_query = f"""
            SELECT
                merchant_segment, issuer_country, payment_solution,
                ROUND(approval_rate_pct, 2) AS approval_rate_pct,
                ROUND(avg_fraud_score, 4) AS avg_fraud_score,
                ROUND(avg_amount, 2) AS avg_amount,
                transaction_count
            FROM {self.config.full_schema_name}.transaction_summaries_for_search
            ORDER BY transaction_count DESC
            LIMIT {num_results}
        """
        try:
            results = await self.execute_query(fallback_query)
            return results or []
        except Exception as e:
            logger.debug("vector_search_similar fallback also failed: %s", e)
            return []

    async def read_app_config(self) -> tuple[str, str] | None:
        """
        Read effective catalog and schema from app_config table.
        Table lives at self.config.full_schema_name (bootstrap from env).
        Returns (catalog, schema) or None if table/row missing.
        """
        table = self.config.full_schema_name + ".app_config"
        query = f"SELECT catalog, schema FROM {table} LIMIT 1"
        try:
            rows = await self.execute_query(query)
            if rows and len(rows) > 0:
                row_catalog = (str(rows[0].get("catalog", "") or "").strip())
                row_schema = (str(rows[0].get("schema", "") or "").strip())
                if row_catalog and row_schema:
                    return (row_catalog, row_schema)
        except Exception as e:
            logger.warning("Could not read app_config table: %s", e)
        return None

    async def _ensure_app_config_table(self) -> bool:
        """
        Create app_config table if it does not exist and seed initial row if empty.
        Table lives at self.config.full_schema_name (env catalog/schema).
        Allows "Save catalog & schema" to work before the Lakehouse Bootstrap job has been run.
        """
        table = self.config.full_schema_name + ".app_config"
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INT NOT NULL DEFAULT 1,
                catalog STRING NOT NULL,
                schema STRING NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
            )
            USING DELTA
            TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
        """
        await self.execute_non_query(create_sql)
        seed_sql = f"""
            INSERT INTO {table} (id, catalog, schema)
            SELECT 1, :seed_catalog, :seed_schema
            WHERE (SELECT COUNT(*) FROM {table}) = 0
        """
        await self.execute_non_query_parameterized(
            seed_sql, {"seed_catalog": self.config.catalog, "seed_schema": self.config.schema}
        )
        return True

    async def write_app_config(self, catalog: str, schema: str) -> bool:
        """
        Write catalog and schema to app_config table (single row id=1, parameterized).
        Table lives at self.config.full_schema_name (bootstrap from env).
        Creates the table and seed row if they do not exist (so Save works before Lakehouse Bootstrap).
        """
        await self._ensure_app_config_table()
        table = self.config.full_schema_name + ".app_config"
        stmt = f"""
            MERGE INTO {table} AS t
            USING (SELECT 1 AS id, :p_catalog AS catalog, :p_schema AS schema) AS s ON t.id = s.id
            WHEN MATCHED THEN UPDATE SET t.catalog = s.catalog, t.schema = s.schema, t.updated_at = current_timestamp()
            WHEN NOT MATCHED THEN INSERT (id, catalog, schema, updated_at) VALUES (1, s.catalog, s.schema, current_timestamp())
        """
        await self.execute_non_query_parameterized(stmt, {"p_catalog": catalog, "p_schema": schema})
        return True

    async def get_approval_rules(
        self,
        *,
        rule_type: str | None = None,
        active_only: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Fetch approval rules from Lakehouse (parameterized). Used by app and by ML/Agents to accelerate approval rates."""
        limit = max(1, min(limit, 500))
        table = self.config.full_schema_name + ".approval_rules"
        where_clauses: list[str] = []
        params: dict[str, str | int | float | bool] = {}
        if rule_type:
            where_clauses.append("rule_type = :rule_type")
            params["rule_type"] = rule_type
        if active_only:
            where_clauses.append("is_active = true")
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        query = f"""
            SELECT id, name, rule_type, condition_expression, action_summary, priority, is_active, created_at, updated_at
            FROM {table}
            {where_sql}
            ORDER BY priority ASC, updated_at DESC
            LIMIT {limit}
            """
        try:
            if params:
                return await self._execute_query_parameterized(query, params) or []
            return await self.execute_query(query) or []
        except Exception:
            return []

    async def create_approval_rule(
        self,
        *,
        id: str,
        name: str,
        rule_type: str,
        action_summary: str,
        condition_expression: str | None = None,
        priority: int = 100,
        is_active: bool = True,
    ) -> bool:
        """Insert one approval rule into the Lakehouse table (parameterized)."""
        table = self.config.full_schema_name + ".approval_rules"
        cond_col = ":condition_expression" if condition_expression else "NULL"
        stmt = f"""
            INSERT INTO {table} (id, name, rule_type, condition_expression, action_summary, priority, is_active, updated_at)
            VALUES (
                :rule_id, :name, :rule_type,
                {cond_col},
                :action_summary, :priority,
                :is_active,
                current_timestamp()
            )
        """
        params: dict[str, str | int | float | bool] = {
            "rule_id": id,
            "name": name,
            "rule_type": rule_type,
            "action_summary": action_summary,
            "priority": priority,
            "is_active": str(is_active).upper(),
        }
        if condition_expression:
            params["condition_expression"] = condition_expression
        return await self.execute_non_query_parameterized(stmt, params)

    async def update_approval_rule(
        self,
        id: str,
        *,
        name: str | None = None,
        rule_type: str | None = None,
        condition_expression: str | None = None,
        action_summary: str | None = None,
        priority: int | None = None,
        is_active: bool | None = None,
    ) -> bool:
        """Update an approval rule by id (parameterized)."""
        table = self.config.full_schema_name + ".approval_rules"
        updates = ["updated_at = current_timestamp()"]
        params: dict[str, str | int | float | bool] = {"rule_id": id}
        if name is not None:
            updates.append("name = :p_name")
            params["p_name"] = name
        if rule_type is not None:
            updates.append("rule_type = :p_rule_type")
            params["p_rule_type"] = rule_type
        if condition_expression is not None:
            updates.append("condition_expression = :p_condition")
            params["p_condition"] = condition_expression
        if action_summary is not None:
            updates.append("action_summary = :p_action")
            params["p_action"] = action_summary
        if priority is not None:
            updates.append("priority = :p_priority")
            params["p_priority"] = priority
        if is_active is not None:
            updates.append("is_active = :p_active")
            params["p_active"] = str(is_active).upper()
        stmt = f"UPDATE {table} SET {', '.join(updates)} WHERE id = :rule_id"
        return await self.execute_non_query_parameterized(stmt, params)

    async def delete_approval_rule(self, id: str) -> bool:
        """Delete an approval rule by id (parameterized)."""
        table = self.config.full_schema_name + ".approval_rules"
        stmt = f"DELETE FROM {table} WHERE id = :rule_id"
        return await self.execute_non_query_parameterized(stmt, {"rule_id": id})

    async def get_online_features(
        self,
        *,
        source: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch online features from Lakehouse (ML and AI processes) for UI (parameterized)."""
        limit = max(1, min(limit, 500))
        table = self.config.full_schema_name + ".online_features"
        cols = "id, source, feature_set, feature_name, feature_value, feature_value_str, entity_id, created_at"
        params: dict[str, str | int | float | bool] = {}
        source_filter = ""
        if source and source.lower() in ("ml", "agent"):
            source_filter = "AND source = :source"
            params["source"] = source.lower()
        query = f"""
            SELECT {cols}
            FROM {table}
            WHERE created_at >= current_timestamp() - INTERVAL 24 HOURS
              {source_filter}
            ORDER BY created_at DESC
            LIMIT {limit}
        """
        try:
            if params:
                return await self._execute_query_parameterized(query, params) or []
            return await self.execute_query(query) or []
        except Exception as e:
            logger.debug("get_online_features failed: %s", e)
            return []

    async def get_ml_models(self, entity: str = DEFAULT_ENTITY) -> list[dict[str, Any]]:
        """Return ML model metadata enriched with live metrics from Unity Catalog model registry.

        Queries ``system.ml.model_versions`` to fetch the latest version info and
        ``system.ml.model_version_tags`` for logged metrics. Falls back to static
        metadata if the UC query fails (e.g. no system catalog permissions).
        """
        catalog_path_prefix = f"{self.config.catalog}.{self.config.schema}."

        # Try to fetch live metrics from UC model registry
        uc_metrics: dict[str, list[dict[str, str]]] = {}
        uc_versions: dict[str, dict[str, Any]] = {}
        if self.is_available:
            try:
                # Fetch latest version and run_id for each model
                suffixes = [str(m["model_suffix"]) for m in _ML_MODEL_DEFINITIONS]
                model_names = ", ".join(f"'{catalog_path_prefix}{s}'" for s in suffixes)
                version_query = f"""
                    SELECT full_name, version, run_id, creation_timestamp, status
                    FROM system.ml.model_versions
                    WHERE full_name IN ({model_names})
                    ORDER BY full_name, version DESC
                """
                version_rows = await self.execute_query(version_query)
                # Keep latest version per model
                for row in version_rows:
                    fname = str(row.get("full_name", ""))
                    if fname not in uc_versions:
                        uc_versions[fname] = row

                # Fetch logged metrics via model_version_tags (MLflow logs metrics as tags)
                if uc_versions:
                    for fname, vinfo in uc_versions.items():
                        run_id = vinfo.get("run_id")
                        if run_id:
                            try:
                                # Sanitize inputs to prevent SQL injection
                                safe_fname = fname.replace("'", "''")
                                safe_version = int(vinfo["version"])
                                metric_query = f"""
                                    SELECT key, value FROM system.ml.model_version_tags
                                    WHERE full_name = '{safe_fname}' AND version = {safe_version}
                                    AND key LIKE 'metric.%'
                                """
                                tag_rows = await self.execute_query(metric_query)
                                metrics_list = [
                                    {"name": str(r["key"]).replace("metric.", ""), "value": str(r["value"])}
                                    for r in tag_rows
                                ]
                                if metrics_list:
                                    uc_metrics[fname] = metrics_list
                            except Exception:
                                pass
            except Exception as e:
                logger.debug("UC model registry query failed (using static metadata): %s", e)

        out: list[dict[str, Any]] = []
        for m in _ML_MODEL_DEFINITIONS:
            suffix = str(m["model_suffix"])
            catalog_path = catalog_path_prefix + suffix
            row = {k: v for k, v in m.items() if k != "model_suffix"}
            row["catalog_path"] = catalog_path

            # Enrich with UC version info
            vinfo = uc_versions.get(catalog_path)
            if vinfo:
                row["model_type"] = f"{row['model_type']} (v{vinfo.get('version', '?')})"

            # Add live metrics or empty
            row["metrics"] = uc_metrics.get(catalog_path, [])
            out.append(row)
        return out

    async def submit_insight_feedback(
        self,
        *,
        insight_id: str,
        insight_type: str,
        reviewer: str | None,
        verdict: str,
        reason: str | None,
        model_version: str | None,
        prompt_version: str | None,
    ) -> bool:
        """
        Submit domain feedback for an insight to the UC feedback table (parameterized).

        Note: in some environments, Lakeflow-managed tables may disallow direct INSERTs.
        This is intended as a scaffold for the learning loop.
        """
        # Build columns/params dynamically to handle NULLs correctly
        cols = ["insight_id", "insight_type", "verdict", "reviewed_at"]
        placeholders = [":insight_id", ":insight_type", ":verdict", "current_timestamp()"]
        params: dict[str, str | int | float | bool] = {
            "insight_id": insight_id,
            "insight_type": insight_type,
            "verdict": verdict,
        }
        for col_name, val in [("reviewer", reviewer), ("reason", reason), ("model_version", model_version), ("prompt_version", prompt_version)]:
            if val is not None:
                cols.append(col_name)
                placeholders.append(f":{col_name}")
                params[col_name] = val

        statement = f"""
        INSERT INTO {self.config.full_schema_name}.insight_feedback_silver
        ({', '.join(cols)})
        VALUES
        ({', '.join(placeholders)})
        """

        return await self.execute_non_query_parameterized(statement, params)
    
    # =========================================================================
    # Additional analytics views
    # =========================================================================

    async def get_decline_recovery_opportunities(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Decline recovery opportunities ranked by potential recovery value."""
        limit = max(1, min(limit, 100))
        query = f"""
            SELECT *
            FROM {self.config.full_schema_name}.v_decline_recovery_opportunities
            ORDER BY potential_recovery_value DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_card_network_performance(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Approval rate and volume by card network."""
        limit = max(1, min(limit, 50))
        query = f"""
            SELECT *
            FROM {self.config.full_schema_name}.v_card_network_performance
            ORDER BY transaction_count DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_merchant_segment_performance(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Approval rate and volume by merchant segment."""
        limit = max(1, min(limit, 50))
        query = f"""
            SELECT *
            FROM {self.config.full_schema_name}.v_merchant_segment_performance
            ORDER BY transaction_count DESC
            LIMIT {limit}
        """
        results = await self.execute_query(query)
        return results or []

    async def get_daily_trends(self, *, days: int = 30) -> list[dict[str, Any]]:
        """Daily approval rate and volume trends."""
        days = max(1, min(days, 90))
        query = f"""
            SELECT *
            FROM {self.config.full_schema_name}.v_daily_trends
            WHERE event_date >= current_date() - INTERVAL {days} DAYS
            ORDER BY event_date DESC
        """
        results = await self.execute_query(query)
        return results or []

    # =========================================================================
    # ML Model Serving
    # =========================================================================
    
    async def call_approval_model(self, features: dict[str, Any]) -> dict[str, Any]:
        """Call approval propensity model endpoint."""
        return await self._call_model_endpoint(
            endpoint_name="approval-propensity",
            features=features,
            mock_fallback=lambda: MockDataGenerator.approval_prediction(features),
        )

    async def call_risk_model(self, features: dict[str, Any]) -> dict[str, Any]:
        """Call risk scoring model endpoint."""
        return await self._call_model_endpoint(
            endpoint_name="risk-scoring",
            features=features,
            mock_fallback=lambda: MockDataGenerator.risk_prediction(features),
        )

    async def call_routing_model(self, features: dict[str, Any]) -> dict[str, Any]:
        """Call smart routing model endpoint."""
        return await self._call_model_endpoint(
            endpoint_name="smart-routing",
            features=features,
            mock_fallback=lambda: MockDataGenerator.routing_prediction(features),
        )

    async def call_retry_model(self, features: dict[str, Any]) -> dict[str, Any]:
        """Call smart retry model endpoint (retry success likelihood and recovery)."""
        return await self._call_model_endpoint(
            endpoint_name="smart-retry",
            features=features,
            mock_fallback=lambda: MockDataGenerator.retry_prediction(features),
        )

    @staticmethod
    def _engineer_features(features: dict[str, Any], endpoint_name: str) -> dict[str, Any]:
        """Transform raw MLPredictionInput features to the schema each model expects.

        The ML models were trained with engineered columns (``log_amount``,
        ``hour_of_day``, ``is_weekend``, ``network_encoded``,
        ``risk_amount_interaction``, etc.) that are *not* present in the
        ``MLPredictionInput`` Pydantic model.  This method derives them from
        the raw inputs so the Model Serving endpoint receives an exact schema
        match.
        """
        import math
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        amount = float(features.get("amount", 0))
        fraud_score = float(features.get("fraud_score", 0.1))

        # Common engineered features shared by all four models
        base: dict[str, Any] = {
            "amount": amount,
            "log_amount": math.log1p(amount),
            "fraud_score": fraud_score,
            "device_trust_score": float(features.get("device_trust_score", 0.8)),
            "is_cross_border": int(bool(features.get("is_cross_border", False))),
            "hour_of_day": now.hour,
            "day_of_week": now.weekday(),
            "is_weekend": int(now.weekday() >= 5),
            "risk_amount_interaction": fraud_score * amount,
        }

        # Card network → ordinal encoded (matches LabelEncoder order in training)
        network_map = {"amex": 0, "discover": 1, "mastercard": 2, "visa": 3}
        network = str(features.get("card_network", "visa")).lower()
        base["network_encoded"] = network_map.get(network, 3)

        if "approval" in endpoint_name:
            base["retry_count"] = int(features.get("retry_count", 0))
            base["uses_3ds"] = int(bool(features.get("uses_3ds", False)))
            return base

        if "risk" in endpoint_name:
            base["aml_risk_score"] = float(features.get("aml_risk_score", 0.1))
            base["processing_time_ms"] = float(features.get("processing_time_ms", 250))
            return base

        if "routing" in endpoint_name:
            base["uses_3ds"] = int(bool(features.get("uses_3ds", False)))
            # One-hot encoded merchant_segment columns (from pd.get_dummies in training)
            _SEGMENTS = ["Digital", "Entertainment", "Fuel", "Gaming", "Grocery", "Retail", "Subscription", "Travel"]
            seg = str(features.get("merchant_segment", "Retail")).capitalize()
            for s in _SEGMENTS:
                base[f"segment_{s}"] = 1 if s == seg else 0
            return base

        # smart-retry requires additional retry-specific fields
        base["retry_count"] = int(features.get("retry_count", 0))
        base["is_recurring"] = int(bool(features.get("is_recurring", False)))
        base["attempt_sequence"] = int(features.get("attempt_sequence", 1))
        base["time_since_last_attempt_seconds"] = float(features.get("time_since_last_attempt_seconds", 60))
        base["prior_approved_count"] = int(features.get("prior_approved_count", 0))
        base["merchant_retry_policy_max_attempts"] = int(features.get("merchant_retry_policy_max_attempts", 3))
        # Decline reason and retry scenario are label-encoded integers in training;
        # default to 0 (most-common bucket) when not provided.
        base["decline_encoded"] = int(features.get("decline_encoded", 0))
        base["retry_scenario_encoded"] = int(features.get("retry_scenario_encoded", 0))
        return base

    async def _call_model_endpoint(
        self,
        endpoint_name: str,
        features: dict[str, Any],
        mock_fallback: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        """Generic model endpoint caller with fallback.

        Applies feature engineering to translate MLPredictionInput fields
        into the exact column schema each model was trained on.
        """
        if not self.is_available:
            logger.warning("Databricks unavailable, using mock for %s", endpoint_name)
            return mock_fallback()

        client = self.client
        if client is None:
            return mock_fallback()

        engineered = self._engineer_features(features, endpoint_name)
        try:
            response = client.serving_endpoints.query(
                name=endpoint_name,
                dataframe_records=[engineered],
            )
            return self._parse_model_response(response, endpoint_name)
        except Exception as e:
            logger.error("Model endpoint %s failed: %s", endpoint_name, e)
            return mock_fallback()
    
    def _parse_model_response(self, response: Any, endpoint_name: str) -> dict[str, Any]:
        """Parse model serving response based on endpoint type.

        Models are sklearn ``HistGradientBoostingClassifier`` logged via MLflow.
        By default they return ``model.predict()`` — a raw class label (int)
        rather than probability dicts.  We handle both formats.
        """
        raw = response.predictions[0]
        model_version = getattr(getattr(response, "served_model_name", None), "__str__", lambda: "unknown")() or "unknown"

        # If the serving endpoint returns a dict with 'probability' / 'prediction' keys,
        # use them directly; otherwise treat ``raw`` as the class label.
        if isinstance(raw, dict):
            pred_class = raw.get("prediction", 0)
            proba = raw.get("probability")
        else:
            pred_class = int(raw) if not isinstance(raw, int) else raw
            proba = None

        if "approval" in endpoint_name:
            p = proba[1] if isinstance(proba, (list, tuple)) and len(proba) > 1 else (0.85 if pred_class == 1 else 0.25)
            return {
                "approval_probability": p,
                "should_approve": pred_class == 1,
                "model_version": model_version,
            }
        elif "risk" in endpoint_name:
            p = proba[1] if isinstance(proba, (list, tuple)) and len(proba) > 1 else (0.75 if pred_class == 1 else 0.15)
            return {
                "risk_score": p,
                "is_high_risk": pred_class == 1,
                "risk_tier": RiskTier.from_score(p).value,
            }
        elif "retry" in endpoint_name:
            p = proba[1] if isinstance(proba, (list, tuple)) and len(proba) > 1 else (0.70 if pred_class == 1 else 0.20)
            return {
                "should_retry": pred_class == 1,
                "retry_success_probability": p,
                "model_version": model_version,
            }
        else:  # routing
            _SOLUTION_LABELS = ["3ds", "apple_pay", "google_pay", "network_token", "passkey", "standard"]
            solution = _SOLUTION_LABELS[pred_class] if 0 <= pred_class < len(_SOLUTION_LABELS) else f"class_{pred_class}"
            conf = max(proba) if isinstance(proba, (list, tuple)) and proba else 0.80
            alternatives = [s for s in _SOLUTION_LABELS if s != solution][:2]
            return {
                "recommended_solution": solution,
                "confidence": conf,
                "alternatives": alternatives,
            }
    
    # _get_mock_data_for_query removed: analytics methods now return empty data
    # when Databricks is unavailable instead of synthetic mock data.


# =============================================================================
# Mock Data Generator (ML model serving fallback only)
# =============================================================================

class MockDataGenerator:
    """
    Fallback predictions for ML Model Serving endpoints ONLY.

    These methods provide deterministic heuristic predictions when a Model
    Serving endpoint is unreachable.  They are **not** used by analytics
    methods — those always return real Databricks data or empty results so
    the UI shows proper "no data" empty states.

    All mock responses include ``_source: "mock"`` so the frontend can
    display a "model unavailable" indicator.
    """

    @staticmethod
    def approval_prediction(features: dict[str, Any]) -> dict[str, Any]:
        """Heuristic approval prediction when model endpoint is unavailable."""
        fraud_score = features.get("fraud_score", 0.1)
        amount = features.get("amount", 100)
        base_prob = 0.9 - (fraud_score * 0.5) - (amount / 10000 * 0.1)
        prob = max(0.1, min(0.99, base_prob))
        return {
            "approval_probability": round(prob, 3),
            "should_approve": prob > 0.5,
            "model_version": "heuristic-fallback",
            "_source": "mock",
        }

    @staticmethod
    def risk_prediction(features: dict[str, Any]) -> dict[str, Any]:
        """Heuristic risk prediction when model endpoint is unavailable."""
        fraud_score = features.get("fraud_score", 0.1)
        amount = features.get("amount", 100)
        risk = fraud_score * 0.6 + (amount / 5000) * 0.4
        risk = min(1.0, max(0.0, risk))
        return {
            "risk_score": round(risk, 3),
            "is_high_risk": risk > 0.7,
            "risk_tier": RiskTier.from_score(risk).value,
            "_source": "mock",
        }

    @staticmethod
    def routing_prediction(features: dict[str, Any]) -> dict[str, Any]:
        """Heuristic routing prediction when model endpoint is unavailable."""
        amount = features.get("amount", 100)
        merchant_segment = features.get("merchant_segment", "retail")
        if amount > 1000:
            recommended = "adyen"
        elif merchant_segment == "digital":
            recommended = "stripe"
        else:
            recommended = "checkout"
        all_solutions = ["adyen", "stripe", "checkout"]
        return {
            "recommended_solution": recommended,
            "confidence": 0.85,
            "alternatives": [s for s in all_solutions if s != recommended],
            "_source": "mock",
        }

    @staticmethod
    def retry_prediction(features: dict[str, Any]) -> dict[str, Any]:
        """Heuristic retry prediction when model endpoint is unavailable."""
        retry_count = features.get("retry_count", 0)
        fraud_score = features.get("fraud_score", 0.1)
        base = 0.75 - (retry_count * 0.15) - (fraud_score * 0.2)
        prob = max(0.1, min(0.95, base))
        return {
            "should_retry": prob > 0.5,
            "retry_success_probability": round(prob, 3),
            "model_version": "heuristic-fallback",
            "_source": "mock",
        }


# Singleton access is via dependencies.get_databricks_service(Request), which
# uses effective catalog/schema from app_config table (see dependencies.py).
