from __future__ import annotations

from typing import Any, List, Optional, cast

from fastapi import APIRouter
from sqlalchemy import desc, func
from sqlmodel import select
from pydantic import BaseModel

from ..db_models import AuthorizationEvent, DecisionLog
from ..decisioning.schemas import KPIOut
from ..dependencies import SessionDep
from ..services.databricks_service import get_databricks_service

router = APIRouter(tags=["analytics"])


class DeclineBucketOut(BaseModel):
    key: str
    count: int
    pct_of_declines: Optional[float] = None
    total_value: Optional[float] = None
    recoverable_pct: Optional[float] = None


class DatabricksKPIOut(BaseModel):
    """Extended KPIs from Databricks Unity Catalog."""
    total_transactions: int
    approval_rate: float
    avg_fraud_score: float
    total_value: float
    period_start: str
    period_end: str


class ApprovalTrendOut(BaseModel):
    """Approval trend data point."""
    hour: str
    transaction_count: int
    approved_count: int
    approval_rate_pct: float
    avg_fraud_score: float
    total_value: float


class SolutionPerformanceOut(BaseModel):
    """Payment solution performance metrics."""
    payment_solution: str
    transaction_count: int
    approved_count: int
    approval_rate_pct: float
    avg_amount: float
    total_value: float


@router.get("/kpis", response_model=KPIOut, operation_id="getKpis")
def kpis(session: SessionDep) -> KPIOut:
    """Get KPIs from local Lakebase database."""
    total = session.exec(select(func.count(AuthorizationEvent.id))).one() or 0
    approved = (
        session.exec(
            select(func.count(AuthorizationEvent.id)).where(
                AuthorizationEvent.result == "approved"
            )
        ).one()
        or 0
    )
    approval_rate = float(approved) / float(total) if total else 0.0
    return KPIOut(total=int(total), approved=int(approved), approval_rate=approval_rate)


@router.get("/kpis/databricks", response_model=DatabricksKPIOut, operation_id="getDatabricksKpis")
async def databricks_kpis() -> DatabricksKPIOut:
    """Get KPIs from Databricks Unity Catalog."""
    service = get_databricks_service()
    data = await service.get_kpis()
    return DatabricksKPIOut(**data)


@router.get("/trends", response_model=List[ApprovalTrendOut], operation_id="getApprovalTrends")
async def approval_trends(hours: int = 168) -> List[ApprovalTrendOut]:
    """Get approval rate trends from Databricks."""
    hours = max(1, min(hours, 720))  # Limit to 30 days
    service = get_databricks_service()
    data = await service.get_approval_trends(hours)
    return [ApprovalTrendOut(**row) for row in data]


@router.get("/solutions", response_model=List[SolutionPerformanceOut], operation_id="getSolutionPerformance")
async def solution_performance() -> List[SolutionPerformanceOut]:
    """Get payment solution performance from Databricks."""
    service = get_databricks_service()
    data = await service.get_solution_performance()
    return [SolutionPerformanceOut(**row) for row in data]


@router.post("/events", response_model=AuthorizationEvent, operation_id="ingestAuthEvent")
def ingest_event(event: AuthorizationEvent, session: SessionDep) -> AuthorizationEvent:
    # For demo purposes: allow inserting directly.
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.get("/decisions/recent", response_model=list[DecisionLog], operation_id="recentDecisions")
def recent_decisions(
    session: SessionDep, limit: int = 50, decision_type: Optional[str] = None
) -> list[DecisionLog]:
    limit = max(1, min(limit, 200))
    stmt = select(DecisionLog).order_by(desc(cast(Any, DecisionLog.created_at))).limit(
        limit
    )
    if decision_type:
        stmt = stmt.where(DecisionLog.decision_type == decision_type)
    return list(session.exec(stmt).all())


@router.get(
    "/declines/summary",
    response_model=list[DeclineBucketOut],
    operation_id="declineSummary",
)
def decline_summary(session: SessionDep, limit: int = 20) -> list[DeclineBucketOut]:
    """Get decline summary from local Lakebase database."""
    limit = max(1, min(limit, 100))
    stmt = (
        select(
            AuthorizationEvent.decline_reason,
            func.count(AuthorizationEvent.id),
        )
        .where(AuthorizationEvent.result == "declined")
        .group_by(AuthorizationEvent.decline_reason)
        .order_by(func.count(AuthorizationEvent.id).desc())
        .limit(limit)
    )
    rows = session.exec(stmt).all()
    out: list[DeclineBucketOut] = []
    for reason, count in rows:
        out.append(DeclineBucketOut(key=reason or "unknown", count=int(count or 0)))
    return out


@router.get(
    "/declines/databricks",
    response_model=list[DeclineBucketOut],
    operation_id="getDatabricksDeclines",
)
async def databricks_decline_summary() -> list[DeclineBucketOut]:
    """Get decline summary from Databricks Unity Catalog with recovery insights."""
    service = get_databricks_service()
    data = await service.get_decline_summary()
    return [
        DeclineBucketOut(
            key=row.get("decline_reason", "unknown"),
            count=int(row.get("decline_count", 0)),
            pct_of_declines=row.get("pct_of_declines"),
            total_value=row.get("total_declined_value"),
            recoverable_pct=row.get("recoverable_pct"),
        )
        for row in data
    ]

