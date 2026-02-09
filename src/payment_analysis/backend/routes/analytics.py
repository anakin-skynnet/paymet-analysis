"""Analytics API: KPIs, trends, reason codes, smart checkout, 3DS funnel, decline summary."""

from __future__ import annotations

from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlmodel import select

from ..config import DEFAULT_ENTITY
from ..db_models import AuthorizationEvent, DecisionLog
from ..decisioning.schemas import KPIOut
from ..dependencies import SessionDep, DatabricksServiceDep
from ..lakebase_config import get_online_features_from_lakebase

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


class SmartCheckoutServicePathOut(BaseModel):
    service_path: str
    transaction_count: int
    approved_count: int
    approval_rate_pct: float
    avg_fraud_score: float
    total_value: float
    antifraud_declines: int
    antifraud_pct_of_declines: Optional[float] = None


class SmartCheckoutPathPerformanceOut(BaseModel):
    recommended_path: str
    transaction_count: int
    approved_count: int
    approval_rate_pct: float
    total_value: float


class ThreeDSFunnelOut(BaseModel):
    event_date: str
    total_transactions: int
    three_ds_routed_count: int
    three_ds_friction_count: int
    three_ds_authenticated_count: int
    issuer_approved_after_auth_count: int
    three_ds_friction_rate_pct: Optional[float] = None
    three_ds_authentication_rate_pct: Optional[float] = None
    issuer_approval_post_auth_rate_pct: Optional[float] = None


class ReasonCodeOut(BaseModel):
    entry_system: str
    flow_type: str
    decline_reason_standard: str
    decline_reason_group: str
    recommended_action: str
    decline_count: int
    pct_of_declines: Optional[float] = None
    total_declined_value: float
    avg_amount: float
    affected_merchants: int


class ReasonCodeInsightOut(BaseModel):
    entry_system: str
    flow_type: str
    decline_reason_standard: str
    decline_reason_group: str
    recommended_action: str
    decline_count: int
    pct_of_declines: Optional[float] = None
    total_declined_value: float
    estimated_recoverable_declines: int
    estimated_recoverable_value: float
    priority: int


class FalseInsightsMetricOut(BaseModel):
    event_date: str
    reviewed_insights: int
    false_insights: int
    false_insights_pct: Optional[float] = None


class RetryPerformanceOut(BaseModel):
    retry_scenario: str
    decline_reason_standard: str
    retry_count: int
    retry_attempts: int
    success_rate_pct: float
    recovered_value: float
    avg_fraud_score: float
    avg_time_since_last_attempt_s: Optional[float] = None
    avg_prior_approvals: Optional[float] = None
    baseline_approval_pct: Optional[float] = None
    incremental_lift_pct: Optional[float] = None
    effectiveness: str


class InsightFeedbackIn(BaseModel):
    insight_id: str
    insight_type: str
    verdict: str  # valid | invalid | non_actionable
    reviewer: Optional[str] = None
    reason: Optional[str] = None
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None


class InsightFeedbackOut(BaseModel):
    accepted: bool


class EntrySystemDistributionOut(BaseModel):
    entry_system: str
    transaction_count: int
    approved_count: int
    approval_rate_pct: float
    total_value: float


class CountryOut(BaseModel):
    """Country/entity row for the filter dropdown (from Lakehouse countries table)."""
    code: str
    name: str


class DedupCollisionStatsOut(BaseModel):
    colliding_keys: int
    avg_rows_per_key: float
    avg_entry_systems_per_key: float
    avg_transaction_ids_per_key: float


class ModelMetricOut(BaseModel):
    """Single metric for an ML model."""
    name: str
    value: str


class ModelOut(BaseModel):
    """ML model metadata and optional metrics (from backend/Databricks)."""
    id: str
    name: str
    description: str
    model_type: str
    features: list[str]
    catalog_path: str
    metrics: list[ModelMetricOut] = []


class RecommendationOut(BaseModel):
    """Approval recommendation from Lakehouse / Vector Search (similar cases)."""
    id: str
    context_summary: str
    recommended_action: str
    score: float
    source_type: str
    created_at: Optional[str] = None


class OnlineFeatureOut(BaseModel):
    """Online feature from ML or AI, stored in Lakehouse."""
    id: str
    source: str
    feature_set: Optional[str] = None
    feature_name: str
    feature_value: Optional[float] = None
    feature_value_str: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: Optional[str] = None


@router.get("/online-features", response_model=list[OnlineFeatureOut], operation_id="getOnlineFeatures")
async def get_online_features(
    request: Request,
    service: DatabricksServiceDep,
    source: Optional[str] = Query(None, description="Filter by source: ml or agent"),
    limit: int = Query(100, ge=1, le=500, description="Max number of features to return"),
) -> list[OnlineFeatureOut]:
    """Get online features from Lakebase (if available) or Lakehouse (ML and AI processes). Presented in the UI."""
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and runtime._db_configured():
        rows = get_online_features_from_lakebase(runtime, source=source, limit=limit)
        if rows is not None:
            return [
                OnlineFeatureOut(
                    id=r["id"],
                    source=r["source"],
                    feature_set=r.get("feature_set"),
                    feature_name=r["feature_name"],
                    feature_value=float(r["feature_value"]) if r.get("feature_value") is not None else None,
                    feature_value_str=r.get("feature_value_str"),
                    entity_id=r.get("entity_id"),
                    created_at=str(r["created_at"]) if r.get("created_at") else None,
                )
                for r in rows
            ]
    rows = await service.get_online_features(source=source, limit=limit)
    return [
        OnlineFeatureOut(
            id=r["id"],
            source=r["source"],
            feature_set=r.get("feature_set"),
            feature_name=r["feature_name"],
            feature_value=float(r["feature_value"]) if r.get("feature_value") is not None else None,
            feature_value_str=r.get("feature_value_str"),
            entity_id=r.get("entity_id"),
            created_at=str(r["created_at"]) if r.get("created_at") else None,
        )
        for r in rows
    ]


@router.get("/recommendations", response_model=list[RecommendationOut], operation_id="getRecommendations")
async def get_recommendations(
    service: DatabricksServiceDep,
    limit: int = Query(20, ge=1, le=100, description="Max number of recommendations to return"),
) -> list[RecommendationOut]:
    """Get approval recommendations from Lakehouse (UC) and Vector Search–backed similar cases."""
    rows = await service.get_recommendations_from_lakehouse(limit=limit)
    return [
        RecommendationOut(
            id=r["id"],
            context_summary=r["context_summary"],
            recommended_action=r["recommended_action"],
            score=float(r["score"]),
            source_type=r["source_type"],
            created_at=str(r["created_at"]) if r.get("created_at") else None,
        )
        for r in rows
    ]


@router.get("/countries", response_model=list[CountryOut], operation_id="getCountries")
async def list_countries(
    service: DatabricksServiceDep,
    limit: int = Query(200, ge=1, le=500, description="Max number of countries to return"),
) -> list[CountryOut]:
    """List countries/entities from the Lakehouse table for the filter dropdown. Users can add/remove rows in the table to change options."""
    data = await service.get_countries(limit=limit)
    return [CountryOut(code=r["code"], name=r["name"]) for r in data]


@router.get("/models", response_model=list[ModelOut], operation_id="getModels")
async def list_models(
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
) -> list[ModelOut]:
    """List ML models with catalog path and optional metrics from backend (catalog/schema from config)."""
    data = await service.get_ml_models(entity=entity)
    return [
        ModelOut(
            id=m["id"],
            name=m["name"],
            description=m["description"],
            model_type=m["model_type"],
            features=m["features"],
            catalog_path=m["catalog_path"],
            metrics=[ModelMetricOut(name=x["name"], value=str(x["value"])) for x in m.get("metrics") or []],
        )
        for m in data
    ]


@router.get("/kpis", response_model=KPIOut, operation_id="getKpis")
async def kpis(session: SessionDep, service: DatabricksServiceDep) -> KPIOut:
    """Get KPIs: from Databricks Unity Catalog when available, otherwise from local database."""
    if service.is_available:
        try:
            data = await service.get_kpis()
            total = int(data.get("total_transactions", 0))
            approval_pct = float(data.get("approval_rate", 0.0))
            approval_rate = (approval_pct / 100.0) if approval_pct > 1 else approval_pct
            approved = int(data.get("approved_count", total * approval_rate))
            return KPIOut(total=total, approved=approved, approval_rate=approval_rate)
        except Exception:
            pass
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
async def databricks_kpis(service: DatabricksServiceDep) -> DatabricksKPIOut:
    """Get KPIs from Databricks Unity Catalog."""
    data = await service.get_kpis()
    return DatabricksKPIOut(**data)


@router.get("/trends", response_model=list[ApprovalTrendOut], operation_id="getApprovalTrends")
async def approval_trends(service: DatabricksServiceDep, hours: int = 168) -> list[ApprovalTrendOut]:
    """Get approval rate trends from Databricks."""
    hours = max(1, min(hours, 720))  # Limit to 30 days
    data = await service.get_approval_trends(hours)
    return [ApprovalTrendOut(**row) for row in data]


@router.get("/solutions", response_model=list[SolutionPerformanceOut], operation_id="getSolutionPerformance")
async def solution_performance(service: DatabricksServiceDep) -> list[SolutionPerformanceOut]:
    """Get payment solution performance from Databricks."""
    data = await service.get_solution_performance()
    return [SolutionPerformanceOut(**row) for row in data]


@router.get(
    "/smart-checkout/service-paths",
    response_model=list[SmartCheckoutServicePathOut],
    operation_id="getSmartCheckoutServicePaths",
)
async def smart_checkout_service_paths(
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = 25,
) -> list[SmartCheckoutServicePathOut]:
    """Payment-link performance by Smart Checkout service path for the given entity."""
    limit = max(1, min(limit, 100))
    data = await service.get_smart_checkout_service_paths(entity=entity, limit=limit)
    return [SmartCheckoutServicePathOut(**row) for row in data]


@router.get(
    "/smart-checkout/path-performance",
    response_model=list[SmartCheckoutPathPerformanceOut],
    operation_id="getSmartCheckoutPathPerformance",
)
async def smart_checkout_path_performance(
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = 20,
) -> list[SmartCheckoutPathPerformanceOut]:
    """Payment-link performance by recommended Smart Checkout path for the given entity."""
    limit = max(1, min(limit, 50))
    data = await service.get_smart_checkout_path_performance(entity=entity, limit=limit)
    return [SmartCheckoutPathPerformanceOut(**row) for row in data]


@router.get(
    "/smart-checkout/3ds-funnel",
    response_model=list[ThreeDSFunnelOut],
    operation_id="getThreeDsFunnel",
)
async def three_ds_funnel(
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    days: int = 30,
) -> list[ThreeDSFunnelOut]:
    """Payment-link 3DS funnel metrics by day for the given entity."""
    days = max(1, min(days, 90))
    data = await service.get_3ds_funnel(entity=entity, days=days)
    return [ThreeDSFunnelOut(**row) for row in data]


@router.get(
    "/reason-codes",
    response_model=list[ReasonCodeOut],
    operation_id="getReasonCodes",
)
async def reason_codes(
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = 50,
) -> list[ReasonCodeOut]:
    """Declines consolidated into unified reason-code taxonomy for the given entity."""
    limit = max(1, min(limit, 200))
    data = await service.get_reason_codes(entity=entity, limit=limit)
    return [ReasonCodeOut(**row) for row in data]


@router.get(
    "/reason-codes/insights",
    response_model=list[ReasonCodeInsightOut],
    operation_id="getReasonCodeInsights",
)
async def reason_code_insights(
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = 50,
) -> list[ReasonCodeInsightOut]:
    """Reason-code insights with estimated recoverability for the given entity (demo heuristic)."""
    limit = max(1, min(limit, 200))
    data = await service.get_reason_code_insights(entity=entity, limit=limit)
    return [ReasonCodeInsightOut(**row) for row in data]


@router.get(
    "/factors-delaying-approval",
    response_model=list[ReasonCodeInsightOut],
    operation_id="getFactorsDelayingApproval",
)
async def factors_delaying_approval(
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = Query(10, ge=1, le=50, description="Max number of factors to return"),
) -> list[ReasonCodeInsightOut]:
    """
    Top conditions or factors that delay or reduce approval rates, with recommended actions.
    Use this to discover what to fix and how to accelerate approvals.
    """
    data = await service.get_reason_code_insights(entity=entity, limit=limit)
    return [ReasonCodeInsightOut(**row) for row in data]


@router.get(
    "/reason-codes/entry-systems",
    response_model=list[EntrySystemDistributionOut],
    operation_id="getEntrySystemDistribution",
)
async def entry_system_distribution(
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
) -> list[EntrySystemDistributionOut]:
    """Transaction distribution by entry system for the given entity (coverage check)."""
    data = await service.get_entry_system_distribution(entity=entity)
    return [EntrySystemDistributionOut(**row) for row in data]


@router.get(
    "/reason-codes/dedup-collisions",
    response_model=DedupCollisionStatsOut,
    operation_id="getDedupCollisionStats",
)
async def dedup_collision_stats(service: DatabricksServiceDep) -> DedupCollisionStatsOut:
    """Dedup collision stats (double-counting guardrail)."""
    data = await service.get_dedup_collision_stats()
    return DedupCollisionStatsOut(**data)


@router.get(
    "/insights/false-insights",
    response_model=list[FalseInsightsMetricOut],
    operation_id="getFalseInsightsMetric",
)
async def false_insights_metric(service: DatabricksServiceDep, days: int = 30) -> list[FalseInsightsMetricOut]:
    """False Insights counter-metric time series (expert review invalid/non-actionable)."""
    days = max(1, min(days, 180))
    data = await service.get_false_insights_metric(days=days)
    return [FalseInsightsMetricOut(**row) for row in data]


@router.get(
    "/retry/performance",
    response_model=list[RetryPerformanceOut],
    operation_id="getRetryPerformance",
)
async def retry_performance(service: DatabricksServiceDep, limit: int = 50) -> list[RetryPerformanceOut]:
    """Smart Retry performance with scenario split."""
    limit = max(1, min(limit, 200))
    data = await service.get_retry_performance(limit=limit)
    return [RetryPerformanceOut(**row) for row in data]


@router.post(
    "/insights/feedback",
    response_model=InsightFeedbackOut,
    operation_id="submitInsightFeedback",
)
async def submit_insight_feedback(
    service: DatabricksServiceDep,
    payload: InsightFeedbackIn,
) -> InsightFeedbackOut:
    """
    Submit domain feedback on an insight (learning loop scaffold).

    When Databricks is unavailable, this returns accepted=false.
    """
    try:
        ok = await service.submit_insight_feedback(
            insight_id=payload.insight_id,
            insight_type=payload.insight_type,
            reviewer=payload.reviewer,
            verdict=payload.verdict,
            reason=payload.reason,
            model_version=payload.model_version,
            prompt_version=payload.prompt_version,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to submit insight feedback: {e}",
        )
    return InsightFeedbackOut(accepted=bool(ok))


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
async def decline_summary(
    session: SessionDep,
    service: DatabricksServiceDep,
    limit: int = 20,
) -> list[DeclineBucketOut]:
    """Get decline summary: from Databricks Unity Catalog when available, otherwise from local database."""
    if service.is_available:
        try:
            data = await service.get_decline_summary()
            return [
                DeclineBucketOut(
                    key=str(row.get("decline_reason", "unknown")),
                    count=int(row.get("decline_count", 0)),
                    pct_of_declines=row.get("pct_of_declines"),
                    total_value=row.get("total_declined_value"),
                    recoverable_pct=row.get("recoverable_pct"),
                )
                for row in data[:limit]
            ]
        except Exception:
            pass
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
async def databricks_decline_summary(service: DatabricksServiceDep) -> list[DeclineBucketOut]:
    """Get decline summary from Databricks Unity Catalog with recovery insights."""
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

