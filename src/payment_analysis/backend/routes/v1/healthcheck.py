"""Healthcheck endpoints (Cookbook: /api/v1/healthcheck, /api/v1/health/database)."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter()


@router.get("/healthcheck")
async def healthcheck() -> dict[str, Any]:
    """Return the API status."""
    return {
        "status": "OK",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/database")
async def health_database(request: Request) -> dict[str, Any]:
    """Lakebase connection health (Cookbook: error-handling-and-troubleshooting)."""
    rt = getattr(request.app.state, "runtime", None)
    if not rt:
        return {
            "database_instance_exists": False,
            "connection_healthy": False,
            "status": "unhealthy",
        }
    instance_exists = rt._db_configured()
    connection_healthy = False
    if instance_exists:
        try:
            with rt.get_session() as session:
                session.execute(text("SELECT 1"))
            connection_healthy = True
        except Exception:
            pass
    return {
        "database_instance_exists": instance_exists,
        "connection_healthy": connection_healthy,
        "status": "healthy" if (instance_exists and connection_healthy) else "unhealthy",
    }
