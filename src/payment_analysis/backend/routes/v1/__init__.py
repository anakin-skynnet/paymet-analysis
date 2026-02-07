"""V1 API routes (e.g. /api/v1/*)."""

from fastapi import APIRouter

from .healthcheck import router as healthcheck_router

router = APIRouter()
router.include_router(healthcheck_router)
