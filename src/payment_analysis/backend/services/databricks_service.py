"""
Databricks Service - Unity Catalog and Model Serving Integration.

This module provides a clean interface for:
- Executing SQL queries on SQL Warehouse
- Fetching analytics from Unity Catalog views
- Calling ML model serving endpoints

Design Patterns:
- Singleton pattern for service instance
- Async/await for non-blocking I/O
- Graceful fallback to mock data for development
- Type hints throughout for IDE support
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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

    @classmethod
    def from_environment(cls) -> "DatabricksConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("DATABRICKS_HOST"),
            token=os.getenv("DATABRICKS_TOKEN"),
            client_id=os.getenv("DATABRICKS_CLIENT_ID"),
            client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
            warehouse_id=os.getenv("DATABRICKS_WAREHOUSE_ID", "148ccb90800933a1"),
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
        """Factory method to create service instance."""
        return cls(config=config or DatabricksConfig.from_environment())
    
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
    
    async def execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute SQL query on SQL Warehouse.
        
        Args:
            query: SQL query string
            
        Returns:
            List of row dictionaries
        """
        if not self.is_available:
            logger.warning("Databricks unavailable, returning mock data")
            return self._get_mock_data_for_query(query)
        
        try:
            return await self._execute_query_internal(query)
        except Exception as e:
            err_str = str(e).lower()
            if "invalid scope" in err_str or ("403" in err_str and "forbidden" in err_str):
                logger.error(
                    "Query execution failed (likely missing SQL scope): %s. "
                    "Add the 'sql' scope in Compute → Apps → payment-analysis → Edit → Configure → Authorization scopes, then restart the app.",
                    e,
                )
            else:
                logger.error(f"Query execution failed: {e}")
            return self._get_mock_data_for_query(query)
    
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
        
        # Validate response
        if not response.status or response.status.state != StatementState.SUCCEEDED:
            error = response.status.error if response.status else "Unknown error"
            raise RuntimeError(f"Query failed: {error}")
        
        # Extract results with null safety
        if not response.manifest or not response.manifest.schema or not response.result:
            return []
        
        columns_info = response.manifest.schema.columns
        if not columns_info:
            return []
        
        columns = [col.name for col in columns_info]
        rows = response.result.data_array or []
        
        return [dict(zip(columns, row)) for row in rows]

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
        
        return MockDataGenerator.kpis()
    
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
        return results or MockDataGenerator.approval_trends(seconds)
    
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
        return results or MockDataGenerator.decline_summary()
    
    async def get_solution_performance(self) -> list[dict[str, Any]]:
        """Fetch performance metrics by payment solution."""
        query = f"""
            SELECT payment_solution, transaction_count, approved_count,
                   approval_rate_pct, avg_amount, total_value
            FROM {self.config.full_schema_name}.v_solution_performance
            ORDER BY transaction_count DESC
        """
        
        results = await self.execute_query(query)
        return results or MockDataGenerator.solution_performance()

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
        return results or MockDataGenerator.smart_checkout_service_paths(limit)

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
        return results or MockDataGenerator.smart_checkout_path_performance(limit)

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
        return results or MockDataGenerator.three_ds_funnel(days)

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
        return results or MockDataGenerator.reason_codes(limit)

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
        return results or MockDataGenerator.reason_code_insights(limit)

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
        return results or MockDataGenerator.entry_system_distribution()

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
        return MockDataGenerator.last_hour_performance()

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
        return MockDataGenerator.last_60_seconds_performance()

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
        return MockDataGenerator.streaming_tps(limit_seconds=limit_seconds)

    async def get_command_center_entry_throughput(
        self, entity: str = DEFAULT_ENTITY, limit_minutes: int = 30
    ) -> list[dict[str, Any]]:
        """Throughput by entry system (PD, WS, SEP, Checkout) for Command Center. Databricks first: derive from v_streaming_volume_per_second with fixed shares; else mock."""
        limit_seconds = max(1, min(limit_minutes, 60)) * 60
        try:
            tps_list = await self.get_streaming_tps(limit_seconds=limit_seconds)
            if tps_list:
                # Derive PD/WS/SEP/Checkout from total TPS using standard shares (62%, 34%, 3%, 1%)
                shares = (0.62, 0.34, 0.03, 0.01)
                return [
                    {
                        "ts": row["event_second"],
                        "PD": int(row["records_per_second"] * shares[0]),
                        "WS": int(row["records_per_second"] * shares[1]),
                        "SEP": int(row["records_per_second"] * shares[2]),
                        "Checkout": max(0, int(row["records_per_second"] * shares[3])),
                    }
                    for row in tps_list
                ]
        except Exception as e:
            logger.debug("get_command_center_entry_throughput failed: %s", e)
        return MockDataGenerator.command_center_entry_throughput(
            country_code=entity, limit_minutes=limit_minutes
        )

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
        return MockDataGenerator.data_quality_summary()

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
        return MockDataGenerator.active_alerts()

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
        return results or MockDataGenerator.performance_by_geography()

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
        return MockDataGenerator.countries()

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
        return results[0] if results else MockDataGenerator.dedup_collision_stats()

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
        return results or MockDataGenerator.false_insights_metric(days)

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
        return results or MockDataGenerator.retry_performance(limit)

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
        except Exception:
            return MockDataGenerator.recommendations(limit)

    def _escape_sql_string(self, s: str) -> str:
        """Escape single quotes for SQL string literals."""
        return (s or "").replace("'", "''")

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
            SELECT 1, '{self._escape_sql_string(self.config.catalog)}', '{self._escape_sql_string(self.config.schema)}'
            WHERE (SELECT COUNT(*) FROM {table}) = 0
        """
        await self.execute_non_query(seed_sql)
        return True

    async def write_app_config(self, catalog: str, schema: str) -> bool:
        """
        Write catalog and schema to app_config table (single row id=1).
        Table lives at self.config.full_schema_name (bootstrap from env).
        Creates the table and seed row if they do not exist (so Save works before Lakehouse Bootstrap).
        """
        await self._ensure_app_config_table()
        table = self.config.full_schema_name + ".app_config"
        c, s = self._escape_sql_string(catalog), self._escape_sql_string(schema)
        stmt = f"""
            MERGE INTO {table} AS t
            USING (SELECT 1 AS id, '{c}' AS catalog, '{s}' AS schema) AS s ON t.id = s.id
            WHEN MATCHED THEN UPDATE SET t.catalog = s.catalog, t.schema = s.schema, t.updated_at = current_timestamp()
            WHEN NOT MATCHED THEN INSERT (id, catalog, schema, updated_at) VALUES (1, s.catalog, s.schema, current_timestamp())
        """
        await self.execute_non_query(stmt)
        return True

    async def get_approval_rules(
        self,
        *,
        rule_type: str | None = None,
        active_only: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Fetch approval rules from Lakehouse. Used by app and by ML/Agents to accelerate approval rates."""
        limit = max(1, min(limit, 500))
        table = self.config.full_schema_name + ".approval_rules"
        where_clauses = []
        if rule_type:
            where_clauses.append(f"rule_type = '{self._escape_sql_string(rule_type)}'")
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
        """Insert one approval rule into the Lakehouse table."""
        table = self.config.full_schema_name + ".approval_rules"
        cond = f"'{self._escape_sql_string(condition_expression)}'" if condition_expression else "NULL"
        stmt = f"""
            INSERT INTO {table} (id, name, rule_type, condition_expression, action_summary, priority, is_active, updated_at)
            VALUES (
                '{self._escape_sql_string(id)}',
                '{self._escape_sql_string(name)}',
                '{self._escape_sql_string(rule_type)}',
                {cond},
                '{self._escape_sql_string(action_summary)}',
                {priority},
                {str(is_active).upper()},
                current_timestamp()
            )
        """
        return await self.execute_non_query(stmt)

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
        """Update an approval rule by id."""
        table = self.config.full_schema_name + ".approval_rules"
        updates = ["updated_at = current_timestamp()"]
        if name is not None:
            updates.append(f"name = '{self._escape_sql_string(name)}'")
        if rule_type is not None:
            updates.append(f"rule_type = '{self._escape_sql_string(rule_type)}'")
        if condition_expression is not None:
            updates.append(f"condition_expression = '{self._escape_sql_string(condition_expression)}'")
        if action_summary is not None:
            updates.append(f"action_summary = '{self._escape_sql_string(action_summary)}'")
        if priority is not None:
            updates.append(f"priority = {priority}")
        if is_active is not None:
            updates.append(f"is_active = {str(is_active).upper()}")
        stmt = f"UPDATE {table} SET {', '.join(updates)} WHERE id = '{self._escape_sql_string(id)}'"
        return await self.execute_non_query(stmt)

    async def delete_approval_rule(self, id: str) -> bool:
        """Delete an approval rule by id."""
        table = self.config.full_schema_name + ".approval_rules"
        stmt = f"DELETE FROM {table} WHERE id = '{self._escape_sql_string(id)}'"
        return await self.execute_non_query(stmt)

    async def get_online_features(
        self,
        *,
        source: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch online features from Lakehouse (ML and AI processes) for UI."""
        limit = max(1, min(limit, 500))
        table = self.config.full_schema_name + ".online_features"
        where = "WHERE created_at >= current_timestamp() - INTERVAL 24 HOURS"
        if source and source.lower() in ("ml", "agent"):
            where += f" AND source = '{self._escape_sql_string(source.lower())}'"
        query = f"""
            SELECT id, source, feature_set, feature_name, feature_value, feature_value_str, entity_id, created_at
            FROM {table}
            {where}
            ORDER BY created_at DESC
            LIMIT {limit}
        """
        try:
            return await self.execute_query(query) or []
        except Exception:
            return MockDataGenerator.online_features(limit)

    async def get_ml_models(self, entity: str = DEFAULT_ENTITY) -> list[dict[str, Any]]:
        """Return ML model metadata and optional metrics. Catalog path uses config (catalog.schema). entity for future filtering.
        All four models are trained in train_models notebook; model_type and features must match that notebook.
        """
        base = [
            {
                "id": "approval_propensity",
                "name": "Approval Propensity Model",
                "description": "Predicts the probability that a transaction will be approved (binary classification). Used for routing and retry decisions to prioritize high-propensity flows.",
                "model_type": "RandomForestClassifier",
                "features": ["amount", "fraud_score", "device_trust_score", "is_cross_border", "retry_count", "uses_3ds"],
                "model_suffix": "approval_propensity_model",
                "metrics": [],
            },
            {
                "id": "risk_scoring",
                "name": "Risk Scoring Model",
                "description": "Classifies transactions as high-risk (fraud or decline) vs low-risk. Combines fraud score, AML score, and behavioral signals for decline and routing decisions.",
                "model_type": "RandomForestClassifier",
                "features": ["amount", "fraud_score", "aml_risk_score", "is_cross_border", "processing_time_ms", "device_trust_score"],
                "model_suffix": "risk_scoring_model",
                "metrics": [],
            },
            {
                "id": "smart_routing",
                "name": "Smart Routing Policy",
                "description": "Multiclass classifier that recommends payment solution (standard, 3DS, network token, passkey) to maximize approval rate given merchant segment, risk, and 3DS usage.",
                "model_type": "RandomForestClassifier",
                "features": ["amount", "fraud_score", "is_cross_border", "uses_3ds", "device_trust_score", "merchant_segment_*"],
                "model_suffix": "smart_routing_policy",
                "metrics": [],
            },
            {
                "id": "smart_retry",
                "name": "Smart Retry Policy",
                "description": "Predicts whether a declined transaction is recoverable (worth retrying). Trained on decline reason, retry context, and merchant policy to recommend retry timing and strategy.",
                "model_type": "RandomForestClassifier",
                "features": [
                    "decline_encoded",
                    "retry_scenario_encoded",
                    "retry_count",
                    "amount",
                    "is_recurring",
                    "fraud_score",
                    "device_trust_score",
                    "attempt_sequence",
                    "time_since_last_attempt_seconds",
                    "prior_approved_count",
                    "merchant_retry_policy_max_attempts",
                ],
                "model_suffix": "smart_retry_policy",
                "metrics": [],
            },
        ]
        catalog_path_prefix = f"{self.config.catalog}.{self.config.schema}."
        out: list[dict[str, Any]] = []
        for m in base:
            suffix = str(m["model_suffix"])
            row = {k: v for k, v in m.items() if k != "model_suffix"}
            row["catalog_path"] = catalog_path_prefix + suffix
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
        Submit domain feedback for an insight to the UC feedback table.

        Note: in some environments, Lakeflow-managed tables may disallow direct INSERTs.
        This is intended as a scaffold for the learning loop.
        """

        def esc(v: str | None) -> str:
            if v is None:
                return "NULL"
            return "'" + v.replace("'", "''") + "'"

        statement = f"""
        INSERT INTO {self.config.full_schema_name}.insight_feedback_silver
        (insight_id, insight_type, reviewer, verdict, reason, model_version, prompt_version, reviewed_at)
        VALUES
        ({esc(insight_id)}, {esc(insight_type)}, {esc(reviewer)}, {esc(verdict)}, {esc(reason)}, {esc(model_version)}, {esc(prompt_version)}, current_timestamp())
        """

        return await self.execute_non_query(statement)
    
    # =========================================================================
    # ML Model Serving
    # =========================================================================
    
    async def call_approval_model(self, features: dict[str, Any]) -> dict[str, Any]:
        """Call approval propensity model endpoint."""
        return await self._call_model_endpoint(
            endpoint_name=f"approval-propensity-{os.getenv('ENVIRONMENT', 'dev')}",
            features=features,
            mock_fallback=lambda: MockDataGenerator.approval_prediction(features),
        )
    
    async def call_risk_model(self, features: dict[str, Any]) -> dict[str, Any]:
        """Call risk scoring model endpoint."""
        return await self._call_model_endpoint(
            endpoint_name=f"risk-scoring-{os.getenv('ENVIRONMENT', 'dev')}",
            features=features,
            mock_fallback=lambda: MockDataGenerator.risk_prediction(features),
        )
    
    async def call_routing_model(self, features: dict[str, Any]) -> dict[str, Any]:
        """Call smart routing model endpoint."""
        return await self._call_model_endpoint(
            endpoint_name=f"smart-routing-{os.getenv('ENVIRONMENT', 'dev')}",
            features=features,
            mock_fallback=lambda: MockDataGenerator.routing_prediction(features),
        )

    async def call_retry_model(self, features: dict[str, Any]) -> dict[str, Any]:
        """Call smart retry model endpoint (retry success likelihood and recovery)."""
        return await self._call_model_endpoint(
            endpoint_name=f"smart-retry-{os.getenv('ENVIRONMENT', 'dev')}",
            features=features,
            mock_fallback=lambda: MockDataGenerator.retry_prediction(features),
        )

    async def _call_model_endpoint(
        self,
        endpoint_name: str,
        features: dict[str, Any],
        mock_fallback: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        """Generic model endpoint caller with fallback."""
        if not self.is_available:
            logger.warning(f"Databricks unavailable, using mock for {endpoint_name}")
            return mock_fallback()

        client = self.client
        if client is None:
            return mock_fallback()

        try:
            response = client.serving_endpoints.query(
                name=endpoint_name,
                dataframe_records=[features],
            )
            return self._parse_model_response(response, endpoint_name)
        except Exception as e:
            logger.error(f"Model endpoint {endpoint_name} failed: {e}")
            return mock_fallback()
    
    def _parse_model_response(self, response: Any, endpoint_name: str) -> dict[str, Any]:
        """Parse model serving response based on endpoint type."""
        prediction = response.predictions[0]
        model_version = response.metadata.model_version if response.metadata else "unknown"
        
        if "approval" in endpoint_name:
            return {
                "approval_probability": prediction.get("probability", [0.5, 0.5])[1],
                "should_approve": prediction.get("prediction", 1) == 1,
                "model_version": model_version,
            }
        elif "risk" in endpoint_name:
            prob = prediction.get("probability", [0.9, 0.1])[1]
            return {
                "risk_score": prob,
                "is_high_risk": prediction.get("prediction", 0) == 1,
                "risk_tier": RiskTier.from_score(prob).value,
            }
        elif "retry" in endpoint_name:
            prob = prediction.get("probability", [0.5, 0.5])
            retry_prob = prob[1] if isinstance(prob, (list, tuple)) and len(prob) > 1 else (float(prob) if isinstance(prob, (int, float)) else 0.5)
            return {
                "should_retry": prediction.get("prediction", 1) == 1,
                "retry_success_probability": retry_prob,
                "model_version": model_version,
            }
        else:  # routing
            return {
                "recommended_solution": prediction.get("prediction", "primary_processor"),
                "confidence": max(prediction.get("probability", [0.5])),
                "alternatives": ["backup_processor", "network_tokenization"],
            }
    
    # =========================================================================
    # Mock Data Routing
    # =========================================================================
    
    def _get_mock_data_for_query(self, query: str) -> list[dict[str, Any]]:
        """Route to appropriate mock data based on query content."""
        query_lower = query.lower()
        
        if "v_executive_kpis" in query_lower:
            return [MockDataGenerator.kpis()]
        elif "v_top_decline_reasons" in query_lower:
            return MockDataGenerator.decline_summary()
        elif "v_approval_trends" in query_lower:
            return MockDataGenerator.approval_trends(3600)
        elif "v_solution_performance" in query_lower:
            return MockDataGenerator.solution_performance()
        elif "v_smart_checkout_service_path_br" in query_lower:
            return MockDataGenerator.smart_checkout_service_paths(25)
        elif "v_smart_checkout_path_performance_br" in query_lower:
            return MockDataGenerator.smart_checkout_path_performance(20)
        elif "v_3ds_funnel_br" in query_lower:
            return MockDataGenerator.three_ds_funnel(30)
        elif "v_reason_codes_br" in query_lower:
            return MockDataGenerator.reason_codes(50)
        elif "v_reason_code_insights_br" in query_lower:
            return MockDataGenerator.reason_code_insights(50)
        elif "v_entry_system_distribution_br" in query_lower:
            return MockDataGenerator.entry_system_distribution()
        elif "v_performance_by_geography" in query_lower:
            return MockDataGenerator.performance_by_geography()
        elif "v_last_hour_performance" in query_lower:
            return [MockDataGenerator.last_hour_performance()]
        elif "v_last_60_seconds_performance" in query_lower:
            return [MockDataGenerator.last_60_seconds_performance()]
        elif "v_streaming_volume_per_second" in query_lower:
            return MockDataGenerator.streaming_tps(limit_seconds=300)
        elif "v_data_quality_summary" in query_lower:
            return [MockDataGenerator.data_quality_summary()]
        elif ".countries" in query_lower:
            return MockDataGenerator.countries()
        elif "v_dedup_collision_stats" in query_lower:
            return [MockDataGenerator.dedup_collision_stats()]
        elif "v_active_alerts" in query_lower:
            return MockDataGenerator.active_alerts()
        elif "v_false_insights_metric" in query_lower:
            return MockDataGenerator.false_insights_metric(30)
        elif "v_retry_performance" in query_lower:
            return MockDataGenerator.retry_performance(50)
        
        return []


# =============================================================================
# Mock Data Generator (for development/testing)
# =============================================================================

class MockDataGenerator:
    """
    Generates realistic mock data for development and testing.
    
    All methods are static and deterministic where possible,
    with random elements for trend/time-series data.
    """
    
    @staticmethod
    def kpis() -> dict[str, Any]:
        """Generate mock KPI data."""
        total = 15234
        approval_pct = 87.5
        return {
            "total_transactions": total,
            "approved_count": int(total * approval_pct / 100),
            "approval_rate": approval_pct,
            "avg_fraud_score": 0.12,
            "total_value": 1250000.00,
            "period_start": "2026-01-01",
            "period_end": "2026-02-04",
        }
    
    @staticmethod
    def approval_trends(seconds: int) -> list[dict[str, Any]]:
        """Generate mock approval trends by second (real-time)."""
        import random
        
        base_time = datetime.now()
        n = min(seconds, 3600)
        return [
            {
                "event_second": (base_time - timedelta(seconds=i)).isoformat(),
                "transaction_count": random.randint(500, 1500),
                "approved_count": random.randint(400, 1300),
                "approval_rate_pct": round(random.uniform(82, 92), 2),
                "avg_fraud_score": round(random.uniform(0.05, 0.20), 3),
                "total_value": round(random.uniform(50000, 150000), 2),
            }
            for i in range(n)
        ]
    
    @staticmethod
    def decline_summary() -> list[dict[str, Any]]:
        """Generate mock decline summary with realistic distribution."""
        reasons = [
            ("insufficient_funds", 2500, 32.5, 125000, 75.0),
            ("do_not_honor", 1800, 23.4, 95000, 67.0),
            ("card_expired", 950, 12.3, 47000, 59.0),
            ("invalid_card", 780, 10.1, 39000, 51.0),
            ("suspected_fraud", 650, 8.5, 85000, 43.0),
            ("cvv_mismatch", 450, 5.9, 22000, 35.0),
            ("limit_exceeded", 320, 4.2, 48000, 27.0),
            ("other", 250, 3.1, 12000, 19.0),
        ]
        
        return [
            {
                "decline_reason": reason,
                "decline_count": count,
                "pct_of_declines": pct,
                "total_declined_value": value,
                "avg_amount": round(value / count, 2),
                "recoverable_pct": recoverable,
            }
            for reason, count, pct, value, recoverable in reasons
        ]
    
    @staticmethod
    def solution_performance() -> list[dict[str, Any]]:
        """Generate mock solution performance data."""
        solutions = [
            ("adyen", 8500, 7650, 90.0, 175.0),
            ("stripe", 4200, 3700, 88.1, 200.0),
            ("checkout", 2100, 1820, 86.7, 225.0),
            ("worldpay", 850, 720, 84.7, 250.0),
        ]
        
        return [
            {
                "payment_solution": solution,
                "transaction_count": count,
                "approved_count": approved,
                "approval_rate_pct": rate,
                "avg_amount": avg_amt,
                "total_value": round(count * avg_amt, 2),
            }
            for solution, count, approved, rate, avg_amt in solutions
        ]

    @staticmethod
    def recommendations(limit: int = 10) -> list[dict[str, Any]]:
        """Generate mock approval recommendations (Lakehouse / Vector Search fallback)."""
        from datetime import timezone
        now = datetime.now(timezone.utc).isoformat()
        return [
            {"id": "rec_1", "context_summary": "Low amount, domestic, low risk", "recommended_action": "Route standard; no 3DS friction", "score": 0.92, "source_type": "rule", "created_at": now},
            {"id": "rec_2", "context_summary": "Cross-border, medium risk", "recommended_action": "Use 3DS for authentication", "score": 0.88, "source_type": "rule", "created_at": now},
            {"id": "rec_3", "context_summary": "Declined insufficient_funds", "recommended_action": "Retry after 2h; similar cases approved 65%", "score": 0.78, "source_type": "vector_search", "created_at": now},
        ][:limit]

    @staticmethod
    def online_features(limit: int = 20) -> list[dict[str, Any]]:
        """Mock online features from ML/AI (Lakehouse fallback)."""
        from datetime import timezone
        now = datetime.now(timezone.utc).isoformat()
        return [
            {"id": "of_1", "source": "ml", "feature_set": "approval_propensity", "feature_name": "approval_probability", "feature_value": 0.89, "feature_value_str": None, "entity_id": "tx_demo_1", "created_at": now},
            {"id": "of_2", "source": "ml", "feature_set": "risk_scoring", "feature_name": "risk_score", "feature_value": 0.22, "feature_value_str": None, "entity_id": "tx_demo_1", "created_at": now},
            {"id": "of_3", "source": "agent", "feature_set": "smart_routing", "feature_name": "recommended_route", "feature_value": None, "feature_value_str": "psp_primary", "entity_id": "tx_demo_1", "created_at": now},
        ][:limit]

    @staticmethod
    def smart_checkout_service_paths(limit: int = 25) -> list[dict[str, Any]]:
        """Mock Smart Checkout service-path breakdown."""
        rows = [
            ("antifraud=pass+network_token+vault", 12000, 8800, 73.3, 0.12, 2_100_000, 900, 45.0),
            ("antifraud=pass+3ds=challenge+network_token+vault", 350, 250, 71.4, 0.14, 65_000, 20, 40.0),
            ("antifraud=fail+vault", 800, 0, 0.0, 0.35, 120_000, 800, 80.0),
        ]
        return [
            {
                "service_path": sp,
                "transaction_count": tc,
                "approved_count": ac,
                "approval_rate_pct": ar,
                "avg_fraud_score": fs,
                "total_value": tv,
                "antifraud_declines": ad,
                "antifraud_pct_of_declines": ap,
            }
            for sp, tc, ac, ar, fs, tv, ad, ap in rows[:limit]
        ]

    @staticmethod
    def smart_checkout_path_performance(limit: int = 20) -> list[dict[str, Any]]:
        """Mock recommended-path performance."""
        rows = [
            ("standard", 14000, 10300, 73.6, 2_300_000.0),
            ("network_token", 5000, 3800, 76.0, 900_000.0),
            ("3ds_challenge", 180, 115, 63.9, 40_000.0),
            ("passkey", 90, 78, 86.7, 22_000.0),
        ]
        return [
            {
                "recommended_path": p,
                "transaction_count": tc,
                "approved_count": ac,
                "approval_rate_pct": ar,
                "total_value": tv,
            }
            for p, tc, ac, ar, tv in rows[:limit]
        ]

    @staticmethod
    def three_ds_funnel(days: int = 30) -> list[dict[str, Any]]:
        """Mock 3DS funnel time series."""
        base = datetime.now().date()
        out: list[dict[str, Any]] = []
        for i in range(min(days, 30)):
            d = base - timedelta(days=i)
            routed = 120
            friction = 96
            authed = 72
            approved_after = 58
            out.append(
                {
                    "event_date": str(d),
                    "total_transactions": 15000,
                    "three_ds_routed_count": routed,
                    "three_ds_friction_count": friction,
                    "three_ds_authenticated_count": authed,
                    "issuer_approved_after_auth_count": approved_after,
                    "three_ds_friction_rate_pct": round(friction * 100.0 / routed, 2),
                    "three_ds_authentication_rate_pct": round(authed * 100.0 / routed, 2),
                    "issuer_approval_post_auth_rate_pct": round(approved_after * 100.0 / authed, 2),
                }
            )
        return out

    @staticmethod
    def reason_codes(limit: int = 50) -> list[dict[str, Any]]:
        """Mock unified reason codes summary."""
        rows = [
            ("PD", "standard_ecom", "FUNDS_OR_LIMIT", "funds", "SmartRetry: delay 24-72h (payday-aware)", 1800, 32.5, 95_000, 52.8, 220),
            ("WS", "legacy_ws", "ISSUER_DO_NOT_HONOR", "issuer", "Try alternative checkout path (3DS/network token)", 1300, 23.4, 72_000, 55.4, 180),
            ("PD", "payment_link", "FRAUD_SUSPECTED", "fraud", "Review antifraud rules; reduce false positives", 900, 16.2, 80_000, 88.9, 95),
        ]
        return [
            {
                "entry_system": es,
                "flow_type": ft,
                "decline_reason_standard": drs,
                "decline_reason_group": drg,
                "recommended_action": ra,
                "decline_count": dc,
                "pct_of_declines": pct,
                "total_declined_value": tv,
                "avg_amount": aa,
                "affected_merchants": am,
            }
            for es, ft, drs, drg, ra, dc, pct, tv, aa, am in rows[:limit]
        ]

    @staticmethod
    def reason_code_insights(limit: int = 50) -> list[dict[str, Any]]:
        """Mock reason-code insights with estimated recoverability."""
        rows = [
            ("PD", "standard_ecom", "FUNDS_OR_LIMIT", "funds", "SmartRetry: delay 24-72h (payday-aware)", 1800, 32.5, 95_000, 450, 23_750, 2),
            ("WS", "legacy_ws", "ISSUER_TECHNICAL", "issuer", "SmartRetry: immediate retry or alternate network", 900, 16.2, 80_000, 360, 32_000, 2),
            ("PD", "payment_link", "FRAUD_SUSPECTED", "fraud", "Review antifraud rules; reduce false positives", 900, 16.2, 80_000, 90, 8_000, 3),
        ]
        return [
            {
                "entry_system": es,
                "flow_type": ft,
                "decline_reason_standard": drs,
                "decline_reason_group": drg,
                "recommended_action": ra,
                "decline_count": dc,
                "pct_of_declines": pct,
                "total_declined_value": tv,
                "estimated_recoverable_declines": erd,
                "estimated_recoverable_value": erv,
                "priority": pr,
            }
            for es, ft, drs, drg, ra, dc, pct, tv, erd, erv, pr in rows[:limit]
        ]

    @staticmethod
    def entry_system_distribution() -> list[dict[str, Any]]:
        """Mock entry-system distribution for Brazil."""
        rows = [
            ("PD", 62000, 45000, 72.6, 11_200_000.0),
            ("WS", 34000, 24500, 72.1, 6_100_000.0),
            ("SEP", 3000, 2100, 70.0, 520_000.0),
            ("CHECKOUT", 1000, 720, 72.0, 180_000.0),
        ]
        return [
            {
                "entry_system": es,
                "transaction_count": tc,
                "approved_count": ac,
                "approval_rate_pct": ar,
                "total_value": tv,
            }
            for es, tc, ac, ar, tv in rows
        ]

    @staticmethod
    def performance_by_geography() -> list[dict[str, Any]]:
        """Mock performance by country for geographic distribution and world map."""
        return [
            {"country": "BR", "transaction_count": 350000, "approval_rate_pct": 73.2, "total_transaction_value": 1250000.0},
            {"country": "US", "transaction_count": 120000, "approval_rate_pct": 91.5, "total_transaction_value": 480000.0},
            {"country": "MX", "transaction_count": 80000, "approval_rate_pct": 78.1, "total_transaction_value": 320000.0},
            {"country": "AR", "transaction_count": 25000, "approval_rate_pct": 69.4, "total_transaction_value": 95000.0},
            {"country": "CO", "transaction_count": 20000, "approval_rate_pct": 75.0, "total_transaction_value": 82000.0},
            {"country": "CL", "transaction_count": 15000, "approval_rate_pct": 82.3, "total_transaction_value": 61000.0},
            {"country": "GB", "transaction_count": 18000, "approval_rate_pct": 89.0, "total_transaction_value": 72000.0},
            {"country": "DE", "transaction_count": 14000, "approval_rate_pct": 88.5, "total_transaction_value": 56000.0},
        ]

    @staticmethod
    def last_hour_performance() -> dict[str, Any]:
        """Mock last-hour performance for real-time monitor."""
        return {
            "transactions_last_hour": 55200,
            "approval_rate_pct": 92.5,
            "avg_fraud_score": 0.12,
            "total_value": 125000.0,
            "active_segments": 4,
            "high_risk_transactions": 8,
            "declines_last_hour": 4140,
        }

    @staticmethod
    def last_60_seconds_performance() -> dict[str, Any]:
        """Mock last-60-seconds performance for real-time live metrics."""
        return {
            "transactions_last_60s": 920,
            "approval_rate_pct": 92.5,
            "avg_fraud_score": 0.12,
            "total_value": 2083.0,
            "declines_last_60s": 69,
        }

    @staticmethod
    def streaming_tps(limit_seconds: int = 300) -> list[dict[str, Any]]:
        """Mock TPS time series for real-time ingestion monitor (Simulate Transaction Events -> ETL -> Real-Time Stream)."""
        now = datetime.now()
        out: list[dict[str, Any]] = []
        base_tps = 18
        for i in range(limit_seconds - 1, -1, -1):
            ts = now - timedelta(seconds=i)
            # Slight variation for demo
            variation = (hash(ts.isoformat()) % 7) - 3
            tps = max(5, base_tps + variation)
            out.append({
                "event_second": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "records_per_second": tps,
            })
        return out

    @staticmethod
    def command_center_entry_throughput(
        country_code: str = "BR", limit_minutes: int = 30
    ) -> list[dict[str, Any]]:
        """Mock entry-system throughput (PD 62%, WS 34%, SEP 3%, Checkout 1%) for Command Center real-time chart."""
        import random
        base_tps = 420 if country_code == "BR" else 180 if country_code == "MX" else 90
        shares = (0.62, 0.34, 0.03, 0.01)
        now = datetime.now()
        n = min(limit_minutes * 60, 3600)
        out: list[dict[str, Any]] = []
        for i in range(n, 0, -1):
            t = now - timedelta(seconds=i)
            jitter = 0.9 + random.random() * 0.2
            total = max(1, int(base_tps * jitter * (1 + 0.1 * (i % 10 - 5) / 5)))
            out.append({
                "ts": t.isoformat(),
                "PD": int(total * shares[0]),
                "WS": int(total * shares[1]),
                "SEP": int(total * shares[2]),
                "Checkout": max(0, int(total * shares[3])),
            })
        return out

    @staticmethod
    def data_quality_summary() -> dict[str, Any]:
        """Mock data quality summary."""
        return {
            "bronze_last_24h": 500000,
            "silver_last_24h": 498000,
            "retention_pct_24h": 99.6,
            "latest_bronze_ingestion": str(datetime.now().isoformat()),
            "latest_silver_event": str(datetime.now().isoformat()),
        }

    @staticmethod
    def countries() -> list[dict[str, Any]]:
        """Default countries/entities when Lakehouse table is missing or empty."""
        return [
            {"code": "BR", "name": "Brazil"},
            {"code": "MX", "name": "Mexico"},
            {"code": "AR", "name": "Argentina"},
            {"code": "CL", "name": "Chile"},
            {"code": "CO", "name": "Colombia"},
            {"code": "PE", "name": "Peru"},
            {"code": "EC", "name": "Ecuador"},
            {"code": "UY", "name": "Uruguay"},
            {"code": "PY", "name": "Paraguay"},
            {"code": "BO", "name": "Bolivia"},
        ]

    @staticmethod
    def dedup_collision_stats() -> dict[str, Any]:
        """Mock dedup collision stats."""
        return {
            "colliding_keys": 0,
            "avg_rows_per_key": 0.0,
            "avg_entry_systems_per_key": 0.0,
            "avg_transaction_ids_per_key": 0.0,
        }

    @staticmethod
    def false_insights_metric(days: int = 30) -> list[dict[str, Any]]:
        """Mock False Insights counter-metric series."""
        base = datetime.now().date()
        out: list[dict[str, Any]] = []
        for i in range(min(days, 30)):
            d = base - timedelta(days=i)
            reviewed = 20
            false = 3 if i % 7 != 0 else 6
            out.append(
                {
                    "event_date": str(d),
                    "reviewed_insights": reviewed,
                    "false_insights": false,
                    "false_insights_pct": round(false * 100.0 / reviewed, 2),
                }
            )
        return out

    @staticmethod
    def retry_performance(limit: int = 50) -> list[dict[str, Any]]:
        """Mock retry performance with scenario split."""
        rows = [
            # scenario, reason, retry_count, attempts, success_rate, recovered_value, avg_fraud, avg_wait_s, avg_prior_appr, baseline, lift, effectiveness
            ("PaymentRetry", "FUNDS_OR_LIMIT", 1, 1200, 28.0, 18000.0, 0.11, 3600.0, 0.6, 18.5, 9.5, "Moderate"),
            ("PaymentRetry", "ISSUER_TECHNICAL", 1, 800, 45.0, 22000.0, 0.09, 120.0, 0.4, 18.5, 26.5, "Effective"),
            ("PaymentRecurrence", "CARD_EXPIRED", 1, 300, 5.0, 1200.0, 0.08, 86400.0, 1.2, 18.5, -13.5, "Low"),
        ]
        return [
            {
                "retry_scenario": s,
                "decline_reason_standard": r,
                "retry_count": rc,
                "retry_attempts": a,
                "success_rate_pct": sr,
                "recovered_value": rv,
                "avg_fraud_score": af,
                "avg_time_since_last_attempt_s": avg_wait,
                "avg_prior_approvals": avg_prior,
                "baseline_approval_pct": baseline,
                "incremental_lift_pct": lift,
                "effectiveness": e,
            }
            for (s, r, rc, a, sr, rv, af, avg_wait, avg_prior, baseline, lift, e) in rows[:limit]
        ]
    
    @staticmethod
    def active_alerts() -> list[dict[str, Any]]:
        """Generate mock active alerts for command center / Alerts panel."""
        from datetime import datetime
        now = datetime.now().isoformat()
        return [
            {
                "alert_type": "APPROVAL_RATE_DROP",
                "severity": "HIGH",
                "metric_name": "approval_rate_pct",
                "current_value": 83.2,
                "threshold_value": 85.0,
                "alert_message": "Approval rate dropped to 83.2%",
                "first_detected": now,
            },
            {
                "alert_type": "HIGH_FRAUD_RATE",
                "severity": "MEDIUM",
                "metric_name": "high_risk_transactions",
                "current_value": 25.0,
                "threshold_value": 20.0,
                "alert_message": "25 high-risk transactions in last hour",
                "first_detected": now,
            },
        ]

    @staticmethod
    def approval_prediction(features: dict[str, Any]) -> dict[str, Any]:
        """Generate mock approval prediction based on features."""
        fraud_score = features.get("fraud_score", 0.1)
        amount = features.get("amount", 100)
        
        # Simple heuristic for mock probability
        base_prob = 0.9 - (fraud_score * 0.5) - (amount / 10000 * 0.1)
        prob = max(0.1, min(0.99, base_prob))
        
        return {
            "approval_probability": round(prob, 3),
            "should_approve": prob > 0.5,
            "model_version": "mock-v1",
        }
    
    @staticmethod
    def risk_prediction(features: dict[str, Any]) -> dict[str, Any]:
        """Generate mock risk prediction based on features."""
        fraud_score = features.get("fraud_score", 0.1)
        amount = features.get("amount", 100)
        
        risk = fraud_score * 0.6 + (amount / 5000) * 0.4
        risk = min(1.0, max(0.0, risk))
        
        return {
            "risk_score": round(risk, 3),
            "is_high_risk": risk > 0.7,
            "risk_tier": RiskTier.from_score(risk).value,
        }
    
    @staticmethod
    def routing_prediction(features: dict[str, Any]) -> dict[str, Any]:
        """Generate mock routing prediction based on features."""
        amount = features.get("amount", 100)
        merchant_segment = features.get("merchant_segment", "retail")
        
        # Simple routing logic
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
        }

    @staticmethod
    def retry_prediction(features: dict[str, Any]) -> dict[str, Any]:
        """Generate mock retry prediction (smart retry model fallback)."""
        retry_count = features.get("retry_count", 0)
        fraud_score = features.get("fraud_score", 0.1)
        # Lower success probability as retries increase or risk increases
        base = 0.75 - (retry_count * 0.15) - (fraud_score * 0.2)
        prob = max(0.1, min(0.95, base))
        return {
            "should_retry": prob > 0.5,
            "retry_success_probability": round(prob, 3),
            "model_version": "mock-v1",
        }


# Singleton access is via dependencies.get_databricks_service(Request), which
# uses effective catalog/schema from app_config table (see dependencies.py).
