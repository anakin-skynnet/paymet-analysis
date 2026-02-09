"""Healthcheck endpoints (Cookbook: /api/v1/healthcheck, /api/v1/health/database)."""

from datetime import datetime, timezone
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

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
        lakebase_mode = "autoscaling" if rt._use_lakebase_autoscaling() else ""
    return HealthDatabaseOut(
        database_instance_exists=instance_exists,
        connection_healthy=connection_healthy,
        status="healthy" if (instance_exists and connection_healthy) else "unhealthy",
        lakebase_mode=lakebase_mode,
    )
