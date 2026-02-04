"""
Databricks Service - Connects backend to Unity Catalog and Model Serving.

Provides functionality to:
1. Query Unity Catalog tables/views for analytics
2. Call ML model serving endpoints for predictions
3. Execute SQL queries on SQL Warehouse
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DatabricksConfig:
    """Configuration for Databricks connection."""
    host: Optional[str] = None
    token: Optional[str] = None
    warehouse_id: Optional[str] = None
    catalog: str = "main"
    schema: str = "payment_analysis_dev"

    @classmethod
    def from_env(cls) -> "DatabricksConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("DATABRICKS_HOST"),
            token=os.getenv("DATABRICKS_TOKEN"),
            warehouse_id=os.getenv("DATABRICKS_WAREHOUSE_ID"),
            catalog=os.getenv("DATABRICKS_CATALOG", "main"),
            schema=os.getenv("DATABRICKS_SCHEMA", "payment_analysis_dev"),
        )


class DatabricksService:
    """Service for interacting with Databricks APIs."""

    def __init__(self, config: Optional[DatabricksConfig] = None):
        self.config = config or DatabricksConfig.from_env()
        self._client = None

    @property
    def client(self):
        """Lazy-load the Databricks SDK client."""
        if self._client is None:
            try:
                from databricks.sdk import WorkspaceClient
                self._client = WorkspaceClient(
                    host=self.config.host,
                    token=self.config.token,
                )
                logger.info("Databricks client initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize Databricks client: {e}")
                self._client = None
        return self._client

    def is_available(self) -> bool:
        """Check if Databricks connection is available."""
        return self.client is not None

    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query on SQL Warehouse and return results."""
        if not self.is_available():
            logger.warning("Databricks not available, returning mock data")
            return self._get_mock_data(query)

        try:
            from databricks.sdk.service.sql import StatementState

            # Find warehouse
            warehouse_id = self.config.warehouse_id
            if not warehouse_id:
                warehouses = list(self.client.warehouses.list())
                if warehouses:
                    warehouse_id = warehouses[0].id
                else:
                    logger.error("No SQL Warehouses available")
                    return []

            # Execute statement
            response = self.client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=query,
                wait_timeout="30s"
            )

            # Check status
            if response.status is None or response.status.state != StatementState.SUCCEEDED:
                error_msg = response.status.error if response.status else "Unknown error"
                logger.error(f"Query failed: {error_msg}")
                return []

            # Safely extract results with null checks
            manifest = response.manifest
            result = response.result
            if manifest is None or manifest.schema is None or result is None:
                logger.warning("Query returned empty result structure")
                return []

            columns_info = manifest.schema.columns
            if columns_info is None:
                return []

            columns = [col.name for col in columns_info]
            rows = result.data_array or []
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return self._get_mock_data(query)

    async def get_kpis(self) -> Dict[str, Any]:
        """Get executive KPIs from Unity Catalog."""
        query = f"""
        SELECT 
            total_transactions,
            approved_count,
            approval_rate_pct,
            avg_fraud_score,
            total_transaction_value,
            period_start,
            period_end
        FROM {self.config.catalog}.{self.config.schema}.v_executive_kpis
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

        # Return mock data if no results
        return {
            "total_transactions": 15234,
            "approval_rate": 87.5,
            "avg_fraud_score": 0.12,
            "total_value": 1250000.00,
            "period_start": "2026-01-01",
            "period_end": "2026-02-04",
        }

    async def get_approval_trends(self, hours: int = 168) -> List[Dict[str, Any]]:
        """Get approval rate trends over time."""
        query = f"""
        SELECT 
            hour,
            transaction_count,
            approved_count,
            approval_rate_pct,
            avg_fraud_score,
            total_value
        FROM {self.config.catalog}.{self.config.schema}.v_approval_trends_hourly
        ORDER BY hour DESC
        LIMIT {hours}
        """

        results = await self.execute_query(query)
        return results if results else self._mock_approval_trends(hours)

    async def get_decline_summary(self) -> List[Dict[str, Any]]:
        """Get top decline reasons with recovery potential."""
        query = f"""
        SELECT 
            decline_reason,
            decline_count,
            pct_of_declines,
            total_declined_value,
            avg_amount,
            recoverable_pct
        FROM {self.config.catalog}.{self.config.schema}.v_top_decline_reasons
        ORDER BY decline_count DESC
        LIMIT 10
        """

        results = await self.execute_query(query)
        return results if results else self._mock_decline_summary()

    async def get_solution_performance(self) -> List[Dict[str, Any]]:
        """Get performance by payment solution."""
        query = f"""
        SELECT 
            payment_solution,
            transaction_count,
            approved_count,
            approval_rate_pct,
            avg_amount,
            total_value
        FROM {self.config.catalog}.{self.config.schema}.v_solution_performance
        ORDER BY transaction_count DESC
        """

        results = await self.execute_query(query)
        return results if results else self._mock_solution_performance()

    async def call_approval_model(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Call ML model serving endpoint for approval prediction."""
        if not self.is_available():
            logger.warning("Databricks not available, returning mock prediction")
            return self._mock_approval_prediction(features)

        try:
            endpoint_name = f"approval-propensity-{os.getenv('ENVIRONMENT', 'dev')}"

            response = self.client.serving_endpoints.query(
                name=endpoint_name,
                dataframe_records=[features]
            )

            prediction = response.predictions[0]
            return {
                "approval_probability": prediction.get("probability", [0.5, 0.5])[1],
                "should_approve": prediction.get("prediction", 1) == 1,
                "model_version": response.metadata.model_version if response.metadata else "unknown"
            }

        except Exception as e:
            logger.error(f"Error calling approval model: {e}")
            return self._mock_approval_prediction(features)

    async def call_risk_model(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Call ML model serving endpoint for risk scoring."""
        if not self.is_available():
            return self._mock_risk_prediction(features)

        try:
            endpoint_name = f"risk-scoring-{os.getenv('ENVIRONMENT', 'dev')}"

            response = self.client.serving_endpoints.query(
                name=endpoint_name,
                dataframe_records=[features]
            )

            prediction = response.predictions[0]
            return {
                "risk_score": prediction.get("probability", [0.9, 0.1])[1],
                "is_high_risk": prediction.get("prediction", 0) == 1,
                "risk_tier": self._get_risk_tier(prediction.get("probability", [0.9, 0.1])[1])
            }

        except Exception as e:
            logger.error(f"Error calling risk model: {e}")
            return self._mock_risk_prediction(features)

    async def call_routing_model(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Call ML model for optimal payment routing."""
        if not self.is_available():
            return self._mock_routing_prediction(features)

        try:
            endpoint_name = f"smart-routing-{os.getenv('ENVIRONMENT', 'dev')}"

            response = self.client.serving_endpoints.query(
                name=endpoint_name,
                dataframe_records=[features]
            )

            prediction = response.predictions[0]
            return {
                "recommended_solution": prediction.get("prediction", "primary_processor"),
                "confidence": max(prediction.get("probability", [0.5])),
                "alternatives": ["backup_processor", "network_tokenization"]
            }

        except Exception as e:
            logger.error(f"Error calling routing model: {e}")
            return self._mock_routing_prediction(features)

    # Mock data methods for development/testing

    def _get_mock_data(self, query: str) -> List[Dict[str, Any]]:
        """Return mock data based on query pattern."""
        query_lower = query.lower()

        if "v_executive_kpis" in query_lower:
            return [{"total_transactions": 15234, "approval_rate_pct": 87.5}]
        elif "v_top_decline_reasons" in query_lower:
            return self._mock_decline_summary()
        elif "v_approval_trends" in query_lower:
            return self._mock_approval_trends(24)

        return []

    def _mock_approval_trends(self, hours: int) -> List[Dict[str, Any]]:
        """Generate mock approval trends."""
        import random
        from datetime import datetime, timedelta

        base_time = datetime.now()
        return [
            {
                "hour": (base_time - timedelta(hours=i)).isoformat(),
                "transaction_count": random.randint(500, 1500),
                "approved_count": random.randint(400, 1300),
                "approval_rate_pct": round(random.uniform(82, 92), 2),
                "avg_fraud_score": round(random.uniform(0.05, 0.20), 3),
                "total_value": round(random.uniform(50000, 150000), 2)
            }
            for i in range(hours)
        ]

    def _mock_decline_summary(self) -> List[Dict[str, Any]]:
        """Generate mock decline summary."""
        reasons = [
            ("insufficient_funds", 2500, 32.5, 125000),
            ("do_not_honor", 1800, 23.4, 95000),
            ("card_expired", 950, 12.3, 47000),
            ("invalid_card", 780, 10.1, 39000),
            ("suspected_fraud", 650, 8.5, 85000),
            ("cvv_mismatch", 450, 5.9, 22000),
            ("limit_exceeded", 320, 4.2, 48000),
            ("other", 250, 3.1, 12000)
        ]

        return [
            {
                "decline_reason": reason,
                "decline_count": count,
                "pct_of_declines": pct,
                "total_declined_value": value,
                "avg_amount": round(value / count, 2),
                "recoverable_pct": round(75 - i * 8, 1)
            }
            for i, (reason, count, pct, value) in enumerate(reasons)
        ]

    def _mock_solution_performance(self) -> List[Dict[str, Any]]:
        """Generate mock solution performance."""
        solutions = [
            ("adyen", 8500, 7650, 90.0),
            ("stripe", 4200, 3700, 88.1),
            ("checkout", 2100, 1820, 86.7),
            ("worldpay", 850, 720, 84.7)
        ]

        return [
            {
                "payment_solution": solution,
                "transaction_count": count,
                "approved_count": approved,
                "approval_rate_pct": rate,
                "avg_amount": round(150 + i * 25, 2),
                "total_value": round(count * (150 + i * 25), 2)
            }
            for i, (solution, count, approved, rate) in enumerate(solutions)
        ]

    def _mock_approval_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock approval prediction."""
        fraud_score = features.get("fraud_score", 0.1)
        amount = features.get("amount", 100)

        base_prob = 0.9 - (fraud_score * 0.5) - (amount / 10000 * 0.1)
        prob = max(0.1, min(0.99, base_prob))

        return {
            "approval_probability": round(prob, 3),
            "should_approve": prob > 0.5,
            "model_version": "mock-v1"
        }

    def _mock_risk_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock risk prediction."""
        fraud_score = features.get("fraud_score", 0.1)
        amount = features.get("amount", 100)

        risk = fraud_score * 0.6 + (amount / 5000) * 0.4
        risk = min(1.0, max(0.0, risk))

        return {
            "risk_score": round(risk, 3),
            "is_high_risk": risk > 0.7,
            "risk_tier": self._get_risk_tier(risk)
        }

    def _mock_routing_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock routing prediction."""
        amount = features.get("amount", 100)
        merchant_segment = features.get("merchant_segment", "retail")

        solutions = ["adyen", "stripe", "checkout"]
        if amount > 1000:
            recommended = "adyen"
        elif merchant_segment == "digital":
            recommended = "stripe"
        else:
            recommended = "checkout"

        return {
            "recommended_solution": recommended,
            "confidence": 0.85,
            "alternatives": [s for s in solutions if s != recommended]
        }

    def _get_risk_tier(self, risk_score: float) -> str:
        """Convert risk score to tier."""
        if risk_score < 0.3:
            return "LOW"
        elif risk_score < 0.7:
            return "MEDIUM"
        else:
            return "HIGH"


# Singleton instance
_databricks_service: Optional[DatabricksService] = None


def get_databricks_service() -> DatabricksService:
    """Get or create the Databricks service singleton."""
    global _databricks_service
    if _databricks_service is None:
        _databricks_service = DatabricksService()
    return _databricks_service
