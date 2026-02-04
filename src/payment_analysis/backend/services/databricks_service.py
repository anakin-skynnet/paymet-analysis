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
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, Any

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
        token: Personal access token or OAuth token
        warehouse_id: SQL Warehouse ID for query execution
        catalog: Unity Catalog name
        schema: Schema name within the catalog
    """
    host: str | None = None
    token: str | None = None
    warehouse_id: str | None = None
    catalog: str = "main"
    schema: str = "payment_analysis_dev"

    @classmethod
    def from_environment(cls) -> "DatabricksConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("DATABRICKS_HOST"),
            token=os.getenv("DATABRICKS_TOKEN"),
            warehouse_id=os.getenv("DATABRICKS_WAREHOUSE_ID"),
            catalog=os.getenv("DATABRICKS_CATALOG", "main"),
            schema=os.getenv("DATABRICKS_SCHEMA", "payment_analysis_dev"),
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
        """Initialize the Databricks SDK client with error handling."""
        try:
            from databricks.sdk import WorkspaceClient
            
            client = WorkspaceClient(
                host=self.config.host,
                token=self.config.token,
            )
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
            logger.error(f"Query execution failed: {e}")
            return self._get_mock_data_for_query(query)
    
    async def _execute_query_internal(self, query: str) -> list[dict[str, Any]]:
        """Internal query execution with full error handling."""
        from databricks.sdk.service.sql import StatementState
        
        warehouse_id = self._get_warehouse_id()
        if not warehouse_id:
            raise RuntimeError("No SQL Warehouse available")
        
        response = self.client.statement_execution.execute_statement(
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
    
    def _get_warehouse_id(self) -> str | None:
        """Get warehouse ID from config or discover first available."""
        if self.config.warehouse_id:
            return self.config.warehouse_id
        
        warehouses = list(self.client.warehouses.list())
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
            return {
                "total_transactions": row.get("total_transactions", 0),
                "approval_rate": row.get("approval_rate_pct", 0.0),
                "avg_fraud_score": row.get("avg_fraud_score", 0.0),
                "total_value": row.get("total_transaction_value", 0.0),
                "period_start": str(row.get("period_start", "")),
                "period_end": str(row.get("period_end", "")),
            }
        
        return MockDataGenerator.kpis()
    
    async def get_approval_trends(self, hours: int = 168) -> list[dict[str, Any]]:
        """Fetch approval rate trends over specified hours."""
        hours = min(max(hours, 1), 720)  # Clamp to 1-720 hours
        
        query = f"""
            SELECT hour, transaction_count, approved_count,
                   approval_rate_pct, avg_fraud_score, total_value
            FROM {self.config.full_schema_name}.v_approval_trends_hourly
            ORDER BY hour DESC
            LIMIT {hours}
        """
        
        results = await self.execute_query(query)
        return results or MockDataGenerator.approval_trends(hours)
    
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
    
    async def _call_model_endpoint(
        self,
        endpoint_name: str,
        features: dict[str, Any],
        mock_fallback: callable,
    ) -> dict[str, Any]:
        """Generic model endpoint caller with fallback."""
        if not self.is_available:
            logger.warning(f"Databricks unavailable, using mock for {endpoint_name}")
            return mock_fallback()
        
        try:
            response = self.client.serving_endpoints.query(
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
            return MockDataGenerator.approval_trends(24)
        elif "v_solution_performance" in query_lower:
            return MockDataGenerator.solution_performance()
        
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
        return {
            "total_transactions": 15234,
            "approval_rate": 87.5,
            "avg_fraud_score": 0.12,
            "total_value": 1250000.00,
            "period_start": "2026-01-01",
            "period_end": "2026-02-04",
        }
    
    @staticmethod
    def approval_trends(hours: int) -> list[dict[str, Any]]:
        """Generate mock approval trends."""
        import random
        
        base_time = datetime.now()
        return [
            {
                "hour": (base_time - timedelta(hours=i)).isoformat(),
                "transaction_count": random.randint(500, 1500),
                "approved_count": random.randint(400, 1300),
                "approval_rate_pct": round(random.uniform(82, 92), 2),
                "avg_fraud_score": round(random.uniform(0.05, 0.20), 3),
                "total_value": round(random.uniform(50000, 150000), 2),
            }
            for i in range(hours)
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


# =============================================================================
# Singleton Access
# =============================================================================

@lru_cache(maxsize=1)
def get_databricks_service() -> DatabricksService:
    """
    Get or create the Databricks service singleton.
    
    Uses lru_cache for thread-safe singleton pattern.
    """
    return DatabricksService.create()
