"""Healthcheck endpoints (Cookbook: /api/v1/healthcheck, /api/v1/health/database).
Data source validation: /api/v1/health/databricks confirms analytics and AI are from Databricks when available.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from ...dependencies import get_databricks_service
from ...services.databricks_service import DatabricksService

router = APIRouter()


class HealthcheckOut(BaseModel):
    status: str
    timestamp: str


class HealthDatabaseOut(BaseModel):
    database_instance_exists: bool
    connection_healthy: bool
    status: str
    lakebase_mode: str = Field("", description="'autoscaling' when Lakebase Autoscaling is configured, '' otherwise.")


@router.get("/healthcheck", response_model=HealthcheckOut, operation_id="healthcheck")
async def healthcheck() -> HealthcheckOut:
    """Return the API status."""
    return HealthcheckOut(
        status="OK",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/database", response_model=HealthDatabaseOut, operation_id="healthDatabase")
async def health_database(request: Request) -> HealthDatabaseOut:
    """Lakebase connection health (Cookbook: error-handling-and-troubleshooting)."""
    rt = getattr(request.app.state, "runtime", None)
    if not rt:
        return HealthDatabaseOut(
            database_instance_exists=False,
            connection_healthy=False,
            status="unhealthy",
            lakebase_mode="",
        )
    instance_exists = rt._db_configured()
    connection_healthy = False
    if instance_exists:
        try:
            with rt.get_session() as session:
                session.execute(text("SELECT 1"))
            connection_healthy = True
        except Exception:
            pass
    lakebase_mode = ""
    if instance_exists:
        if rt._use_lakebase_autoscaling():
            lakebase_mode = "autoscaling"
        elif rt._use_lakebase_direct_connection():
            lakebase_mode = "direct"
    return HealthDatabaseOut(
        database_instance_exists=instance_exists,
        connection_healthy=connection_healthy,
        status="healthy" if (instance_exists and connection_healthy) else "unhealthy",
        lakebase_mode=lakebase_mode,
    )


class HealthDatabricksOut(BaseModel):
    """Data source validation: all analytics and AI are from Databricks when available."""

    databricks_available: bool = Field(
        ...,
        description="True when the app can reach Databricks (host + token + warehouse).",
    )
    analytics_source: str = Field(
        ...,
        description="'Unity Catalog' when Databricks is available, 'fallback' (mock or local DB) otherwise.",
    )
    ml_inference_source: str = Field(
        ...,
        description="'Model Serving' when Databricks is available, 'mock' otherwise.",
    )
    timestamp: str = Field(
        ...,
        description="ISO timestamp of the check.",
    )


@router.get(
    "/health/databricks",
    response_model=HealthDatabricksOut,
    operation_id="healthDatabricks",
)
async def health_databricks(
    service: DatabricksService = Depends(get_databricks_service),
) -> HealthDatabricksOut:
    """Validate that data and AI are served from Databricks when the connection is available.
    Use this endpoint to confirm the app is using Unity Catalog and Model Serving in your environment.
    See docs/GUIDE.md §10 (Data sources & code guidelines).
    """
    available = service.is_available
    return HealthDatabricksOut(
        databricks_available=available,
        analytics_source="Unity Catalog" if available else "fallback",
        ml_inference_source="Model Serving" if available else "mock",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
