"""Healthcheck endpoint for Databricks Apps (Cookbook: /api/v1/healthcheck)."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthcheck")
async def healthcheck() -> dict[str, Any]:
    """Return the API status."""
    return {
        "status": "OK",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
