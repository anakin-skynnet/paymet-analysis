"""Decision Admin API: manage decision config, retryable decline codes, and route performance.

Provides CRUD endpoints for the data-driven decisioning tables in Lakebase,
allowing ops teams to tune decision parameters, manage decline codes, and
update route performance without code changes or redeployment.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..dependencies import RuntimeDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["decision-admin"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DecisionConfigOut(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    updated_at: Optional[str] = None


class DecisionConfigUpdateIn(BaseModel):
    value: str


class RetryableDeclineCodeOut(BaseModel):
    code: str
    label: str
    category: str
    default_backoff_seconds: int
    max_attempts: int
    is_active: bool
    updated_at: Optional[str] = None


class RetryableDeclineCodeIn(BaseModel):
    code: str
    label: str
    category: str = "soft"
    default_backoff_seconds: int = 900
    max_attempts: int = 3
    is_active: bool = True


class RoutePerformanceOut(BaseModel):
    route_name: str
    approval_rate_pct: float
    avg_latency_ms: float
    cost_score: float
    is_active: bool
    updated_at: Optional[str] = None


class RoutePerformanceIn(BaseModel):
    route_name: str
    approval_rate_pct: float = 50.0
    avg_latency_ms: float = 500.0
    cost_score: float = 0.5
    is_active: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_schema(runtime: RuntimeDep) -> str:
    return (runtime.config.db.db_schema or "payment_analysis").strip() or "payment_analysis"


def _check_runtime(runtime: RuntimeDep) -> None:
    if not runtime._db_configured():
        raise HTTPException(
            status_code=503,
            detail="Lakebase not configured. Set LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID.",
        )


# ---------------------------------------------------------------------------
# Decision Config CRUD
# ---------------------------------------------------------------------------

@router.get(
    "/config",
    response_model=list[DecisionConfigOut],
    operation_id="getDecisionConfig",
)
def list_decision_config(runtime: RuntimeDep) -> list[DecisionConfigOut]:
    """List all tunable decision parameters from Lakebase."""
    _check_runtime(runtime)
    schema = _get_schema(runtime)
    try:
        from sqlalchemy import text

        with runtime.get_session() as session:
            q = text(f'SELECT key, value, description, updated_at FROM "{schema}".decisionconfig ORDER BY key')
            result = session.execute(q)
            return [
                DecisionConfigOut(
                    key=str(r[0]),
                    value=str(r[1]),
                    description=str(r[2]) if r[2] else None,
                    updated_at=str(r[3]) if r[3] else None,
                )
                for r in result.fetchall()
            ]
    except Exception as e:
        logger.warning("Failed to read decision config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to read decision config: {e}")


@router.put(
    "/config/{key}",
    response_model=DecisionConfigOut,
    operation_id="updateDecisionConfig",
)
def update_decision_config(
    key: str,
    payload: DecisionConfigUpdateIn,
    runtime: RuntimeDep,
) -> DecisionConfigOut:
    """Update a single decision parameter. Creates the key if it doesn't exist."""
    _check_runtime(runtime)
    schema = _get_schema(runtime)
    try:
        from sqlalchemy import text

        with runtime.get_session() as session:
            q = text(
                f"""
                INSERT INTO "{schema}".decisionconfig (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = current_timestamp
                """
            )
            session.execute(q, {"key": key, "value": payload.value})
            session.commit()

        # Invalidate cache
        from ..decisioning.engine import _config_cache
        _config_cache.fetched_at = 0.0

        return DecisionConfigOut(key=key, value=payload.value)
    except Exception as e:
        logger.warning("Failed to update decision config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to update: {e}")


# ---------------------------------------------------------------------------
# Retryable Decline Codes CRUD
# ---------------------------------------------------------------------------

@router.get(
    "/decline-codes",
    response_model=list[RetryableDeclineCodeOut],
    operation_id="getRetryableDeclineCodes",
)
def list_decline_codes(runtime: RuntimeDep) -> list[RetryableDeclineCodeOut]:
    """List all retryable decline codes from Lakebase."""
    _check_runtime(runtime)
    schema = _get_schema(runtime)
    try:
        from sqlalchemy import text

        with runtime.get_session() as session:
            q = text(
                f'SELECT code, label, category, default_backoff_seconds, max_attempts, is_active, updated_at '
                f'FROM "{schema}".retryabledeclinecode ORDER BY category, code'
            )
            result = session.execute(q)
            return [
                RetryableDeclineCodeOut(
                    code=str(r[0]),
                    label=str(r[1]),
                    category=str(r[2]),
                    default_backoff_seconds=int(r[3]),
                    max_attempts=int(r[4]),
                    is_active=bool(r[5]),
                    updated_at=str(r[6]) if r[6] else None,
                )
                for r in result.fetchall()
            ]
    except Exception as e:
        logger.warning("Failed to read decline codes: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to read decline codes: {e}")


@router.post(
    "/decline-codes",
    response_model=RetryableDeclineCodeOut,
    operation_id="createRetryableDeclineCode",
)
def create_decline_code(
    payload: RetryableDeclineCodeIn,
    runtime: RuntimeDep,
) -> RetryableDeclineCodeOut:
    """Add a new retryable decline code."""
    _check_runtime(runtime)
    schema = _get_schema(runtime)
    try:
        from sqlalchemy import text

        with runtime.get_session() as session:
            q = text(
                f"""
                INSERT INTO "{schema}".retryabledeclinecode
                (code, label, category, default_backoff_seconds, max_attempts, is_active)
                VALUES (:code, :label, :category, :backoff, :max_att, :active)
                ON CONFLICT (code) DO UPDATE SET
                    label = EXCLUDED.label,
                    category = EXCLUDED.category,
                    default_backoff_seconds = EXCLUDED.default_backoff_seconds,
                    max_attempts = EXCLUDED.max_attempts,
                    is_active = EXCLUDED.is_active,
                    updated_at = current_timestamp
                """
            )
            session.execute(q, {
                "code": payload.code,
                "label": payload.label,
                "category": payload.category,
                "backoff": payload.default_backoff_seconds,
                "max_att": payload.max_attempts,
                "active": payload.is_active,
            })
            session.commit()

        # Invalidate cache
        from ..decisioning.engine import _decline_codes_cache
        _decline_codes_cache.fetched_at = 0.0

        return RetryableDeclineCodeOut(
            code=payload.code,
            label=payload.label,
            category=payload.category,
            default_backoff_seconds=payload.default_backoff_seconds,
            max_attempts=payload.max_attempts,
            is_active=payload.is_active,
        )
    except Exception as e:
        logger.warning("Failed to create decline code: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create: {e}")


@router.delete(
    "/decline-codes/{code}",
    response_model=dict,
    operation_id="deleteRetryableDeclineCode",
)
def delete_decline_code(code: str, runtime: RuntimeDep) -> dict:
    """Delete a retryable decline code."""
    _check_runtime(runtime)
    schema = _get_schema(runtime)
    try:
        from sqlalchemy import text

        with runtime.get_session() as session:
            q = text(f'DELETE FROM "{schema}".retryabledeclinecode WHERE code = :code')
            session.execute(q, {"code": code})
            session.commit()

        from ..decisioning.engine import _decline_codes_cache
        _decline_codes_cache.fetched_at = 0.0

        return {"deleted": True, "code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")


# ---------------------------------------------------------------------------
# Route Performance CRUD
# ---------------------------------------------------------------------------

@router.get(
    "/routes",
    response_model=list[RoutePerformanceOut],
    operation_id="getRoutePerformance",
)
def list_route_performance(runtime: RuntimeDep) -> list[RoutePerformanceOut]:
    """List route performance data from Lakebase."""
    _check_runtime(runtime)
    schema = _get_schema(runtime)
    try:
        from sqlalchemy import text

        with runtime.get_session() as session:
            q = text(
                f'SELECT route_name, approval_rate_pct, avg_latency_ms, cost_score, is_active, updated_at '
                f'FROM "{schema}".routeperformance ORDER BY approval_rate_pct DESC'
            )
            result = session.execute(q)
            return [
                RoutePerformanceOut(
                    route_name=str(r[0]),
                    approval_rate_pct=float(r[1]),
                    avg_latency_ms=float(r[2]),
                    cost_score=float(r[3]),
                    is_active=bool(r[4]),
                    updated_at=str(r[5]) if r[5] else None,
                )
                for r in result.fetchall()
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read routes: {e}")


@router.post(
    "/routes",
    response_model=RoutePerformanceOut,
    operation_id="upsertRoutePerformance",
)
def upsert_route_performance(
    payload: RoutePerformanceIn,
    runtime: RuntimeDep,
) -> RoutePerformanceOut:
    """Create or update a route performance entry."""
    _check_runtime(runtime)
    schema = _get_schema(runtime)
    try:
        from sqlalchemy import text

        with runtime.get_session() as session:
            q = text(
                f"""
                INSERT INTO "{schema}".routeperformance
                (route_name, approval_rate_pct, avg_latency_ms, cost_score, is_active)
                VALUES (:name, :rate, :latency, :cost, :active)
                ON CONFLICT (route_name) DO UPDATE SET
                    approval_rate_pct = EXCLUDED.approval_rate_pct,
                    avg_latency_ms = EXCLUDED.avg_latency_ms,
                    cost_score = EXCLUDED.cost_score,
                    is_active = EXCLUDED.is_active,
                    updated_at = current_timestamp
                """
            )
            session.execute(q, {
                "name": payload.route_name,
                "rate": payload.approval_rate_pct,
                "latency": payload.avg_latency_ms,
                "cost": payload.cost_score,
                "active": payload.is_active,
            })
            session.commit()

        from ..decisioning.engine import _routes_cache
        _routes_cache.fetched_at = 0.0

        return RoutePerformanceOut(
            route_name=payload.route_name,
            approval_rate_pct=payload.approval_rate_pct,
            avg_latency_ms=payload.avg_latency_ms,
            cost_score=payload.cost_score,
            is_active=payload.is_active,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upsert route: {e}")
