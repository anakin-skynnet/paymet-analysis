"""Analytics API: KPIs, trends, reason codes, smart checkout, 3DS funnel, decline summary.

All data is fetched from Databricks (Unity Catalog views via SQL Warehouse).
When Databricks is unavailable, endpoints fall back to **realistic mock data**
so the UI remains functional and visually populated.  GET /kpis and
GET /declines/summary additionally fall back to the local SQLite database before
using mock data.

**Data-source indicator:** Every analytics response includes an
``X-Data-Source: lakehouse`` or ``X-Data-Source: mock`` header so the frontend
can display a "Data: Databricks" or "Data: Mock" indicator.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)
from sqlmodel import select

from ..config import DEFAULT_ENTITY
from ..db_models import AuthorizationEvent, DecisionLog
from ..decisioning.schemas import KPIOut
from ..dependencies import RuntimeDep, SessionDep, OptionalSessionDep, DatabricksServiceDep
from ..lakebase_config import get_countries_from_lakebase, get_online_features_from_lakebase, write_app_settings_keys
from .. import mock_analytics as _mock

router = APIRouter(tags=["analytics"])


def _is_mock_request(request: Request) -> bool:
    """Check if the client explicitly requested mock data via the ``X-Mock-Data`` header.

    The frontend toggle sets this header to ``"true"`` on every ``/api/`` call
    when mock mode is enabled.  Backend endpoints check this *before* querying
    Databricks so we skip the (potentially slow) lakehouse round-trip entirely.
    """
    return request.headers.get("x-mock-data", "").lower() == "true"


def _set_data_source_header(response: Response, service: Any, *, forced_mock: bool = False) -> None:
    """Set X-Data-Source header based on whether the last query used mock data."""
    if forced_mock:
        response.headers["X-Data-Source"] = "mock"
        return
    is_mock = getattr(service, "_last_query_used_mock", False)
    response.headers["X-Data-Source"] = "mock" if is_mock else "lakehouse"


class ControlPanelIn(BaseModel):
    """Control panel toggle state (Smart Routing, Fraud Shadow, Recalculate Algorithms)."""
    activate_smart_routing: Optional[bool] = None
    deploy_fraud_shadow_model: Optional[bool] = None
    recalculate_algorithms: Optional[bool] = None


class ControlPanelOut(BaseModel):
    ok: bool = True
    message: Optional[str] = None


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
    """Approval trend data point (per-second real-time)."""
    event_second: str
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
    decline_reason_standard: Optional[str] = None
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


class GeographyOut(BaseModel):
    """Transaction count and approval rate by country for geographic distribution and world map."""
    country: str
    transaction_count: int
    approval_rate_pct: Optional[float] = None
    total_transaction_value: Optional[float] = None


class ActiveAlertOut(BaseModel):
    """Single active alert from v_active_alerts (Databricks)."""
    alert_type: str
    severity: str
    metric_name: str
    current_value: float
    threshold_value: float
    alert_message: str
    first_detected: str


class LastHourPerformanceOut(BaseModel):
    """Last-hour performance for real-time monitor (from v_last_hour_performance)."""
    transactions_last_hour: int
    approval_rate_pct: float
    avg_fraud_score: float
    total_value: float
    active_segments: int
    high_risk_transactions: int
    declines_last_hour: int


class Last60SecondsPerformanceOut(BaseModel):
    """Last-60-seconds performance for real-time live metrics (from v_last_60_seconds_performance)."""
    transactions_last_60s: int
    approval_rate_pct: float
    avg_fraud_score: float
    total_value: float
    declines_last_60s: int


class DataQualitySummaryOut(BaseModel):
    """Data quality summary (bronze/silver volumes, retention) from v_data_quality_summary."""
    bronze_last_24h: int
    silver_last_24h: int
    retention_pct_24h: float
    latest_bronze_ingestion: str
    latest_silver_event: str


class CommandCenterEntryThroughputPointOut(BaseModel):
    """Single time point for Command Center real-time monitor: throughput by entry system (PD, WS, SEP, Checkout)."""
    ts: str
    PD: int
    WS: int
    SEP: int
    Checkout: int


class StreamingTpsPointOut(BaseModel):
    """Single TPS data point for real-time ingestion monitor (from v_streaming_volume_per_second)."""
    event_second: str
    records_per_second: int


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
    response: Response,
    service: DatabricksServiceDep,
    source: Optional[str] = Query(None, description="Filter by source: ml or agent"),
    limit: int = Query(100, ge=1, le=500, description="Max number of features to return"),
) -> list[OnlineFeatureOut]:
    """Get online features from Lakebase (if available) or Lakehouse (ML and AI processes). Mock when toggle is on."""
    if _is_mock_request(request):
        _set_data_source_header(response, service, forced_mock=True)
        rows = _mock.mock_online_features(limit=limit)
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
    request: Request,
    response: Response,
    service: DatabricksServiceDep,
    limit: int = Query(20, ge=1, le=100, description="Max number of recommendations to return"),
) -> list[RecommendationOut]:
    """Get approval recommendations from Lakehouse (UC) and Vector Search–backed similar cases; mock when toggle on or fallback."""
    if _is_mock_request(request):
        _set_data_source_header(response, service, forced_mock=True)
        rows = _mock.mock_recommendations()[:limit]
    else:
        rows = await service.get_recommendations_from_lakehouse(limit=limit)
        if not rows:
            rows = _mock.mock_recommendations()[:limit]
        _set_data_source_header(response, service)
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
    request: Request,
    response: Response,
    service: DatabricksServiceDep,
    limit: int = Query(200, ge=1, le=500, description="Max number of countries to return"),
) -> list[CountryOut]:
    """List countries/entities from Lakebase (when configured) or Lakehouse. Mock when toggle is on."""
    if _is_mock_request(request):
        _set_data_source_header(response, service, forced_mock=True)
        return [CountryOut(code=r["code"], name=r["name"]) for r in _mock.mock_countries(limit=limit)]
    runtime = getattr(request.app.state, "runtime", None)
    if runtime and runtime._db_configured():
        rows = get_countries_from_lakebase(runtime, limit=limit)
        if rows is not None:
            return [CountryOut(code=r["code"], name=r["name"]) for r in rows]
    data = await service.get_countries(limit=limit)
    return [CountryOut(code=r["code"], name=r["name"]) for r in data]


@router.get("/models", response_model=list[ModelOut], operation_id="getModels")
async def list_models(
    request: Request,
    response: Response,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
) -> list[ModelOut]:
    """List ML models with catalog path and optional metrics. Mock when toggle is on."""
    if _is_mock_request(request):
        _set_data_source_header(response, service, forced_mock=True)
        data = _mock.mock_models(entity=entity)
    else:
        data = await service.get_ml_models(entity=entity)
        _set_data_source_header(response, service)
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
async def kpis(request: Request, session: OptionalSessionDep, service: DatabricksServiceDep) -> KPIOut:
    """Get KPIs: from Databricks Unity Catalog when available, otherwise from local database."""
    if _is_mock_request(request):
        return KPIOut(**_mock.mock_kpis())
    if service.is_available:
        try:
            data = await service.get_kpis()
            total = int(data.get("total_transactions", 0))
            approved = int(data.get("approved_count", 0))
            approval_pct = data.get("approval_rate")
            if approval_pct is not None:
                pct = float(approval_pct)
                approval_rate = (pct / 100.0) if pct > 1 else pct
            else:
                approval_rate = 0.0
            # Prefer rate derived from counts when view returns 0/null (e.g. empty table)
            if total and (approval_rate is None or approval_rate == 0.0):
                approval_rate = float(approved) / float(total)
            return KPIOut(total=total, approved=approved, approval_rate=approval_rate)
        except Exception:
            logger.debug("UC view KPI query unavailable; falling back to local DB", exc_info=True)
    if session is None:
        m = _mock.mock_kpis()
        return KPIOut(**m)
    total = session.exec(select(func.count(AuthorizationEvent.id))).one() or 0
    approved = (
        session.exec(
            select(func.count(AuthorizationEvent.id)).where(
                AuthorizationEvent.result == "approved"
            )
        ).one()
        or 0
    )
    if total == 0:
        m = _mock.mock_kpis()
        return KPIOut(**m)
    approval_rate = float(approved) / float(total) if total else 0.0
    return KPIOut(total=int(total), approved=int(approved), approval_rate=approval_rate)


@router.get(
    "/metrics",
    response_model=KPIOut,
    operation_id="getMetrics",
)
async def metrics(
    request: Request,
    session: OptionalSessionDep,
    service: DatabricksServiceDep,
    country_filter: str = Query(DEFAULT_ENTITY, alias="country", description="Country/entity filter (e.g. BR)."),
) -> KPIOut:
    """Aggregated Gold-layer metrics (KPIs) filtered by country. Alias for executive dashboards and global multi-tenancy."""
    # country_filter reserved for future Unity Catalog row-level filtering; KPIs currently global
    return await kpis(request, session, service)


@router.post(
    "/control-panel",
    response_model=ControlPanelOut,
    operation_id="postControlPanel",
)
async def control_panel(
    payload: ControlPanelIn,
    service: DatabricksServiceDep,
    rt: RuntimeDep,
) -> ControlPanelOut:
    """Persist control panel toggles to app_settings. When Databricks is available, job triggers can be added later via config."""
    settings: dict[str, str] = {}
    if payload.activate_smart_routing is not None:
        settings["control_activate_smart_routing"] = "true" if payload.activate_smart_routing else "false"
    if payload.deploy_fraud_shadow_model is not None:
        settings["control_deploy_fraud_shadow_model"] = "true" if payload.deploy_fraud_shadow_model else "false"
    if payload.recalculate_algorithms is not None:
        settings["control_recalculate_algorithms"] = "true" if payload.recalculate_algorithms else "false"
    if settings:
        write_app_settings_keys(rt, settings)
    return ControlPanelOut(ok=True, message="Control panel state received.")


@router.get("/kpis/databricks", response_model=DatabricksKPIOut, operation_id="getDatabricksKpis")
async def databricks_kpis(service: DatabricksServiceDep, response: Response) -> DatabricksKPIOut:
    """Get KPIs from Databricks Unity Catalog."""
    data = await service.get_kpis()
    _set_data_source_header(response, service)
    return DatabricksKPIOut(**data)


@router.get("/trends", response_model=list[ApprovalTrendOut], operation_id="getApprovalTrends")
async def approval_trends(request: Request, service: DatabricksServiceDep, response: Response, seconds: int = 3600) -> list[ApprovalTrendOut]:
    """Get approval rate trends by second (real-time) from Databricks; mock fallback."""
    seconds = max(1, min(seconds, 3600))
    if _is_mock_request(request):
        _set_data_source_header(response, service, forced_mock=True)
        return [ApprovalTrendOut(**row) for row in _mock.mock_approval_trends(seconds)]
    data = await service.get_approval_trends(seconds)
    if not data:
        data = _mock.mock_approval_trends(seconds)
    _set_data_source_header(response, service)
    return [ApprovalTrendOut(**row) for row in data]


@router.get("/solutions", response_model=list[SolutionPerformanceOut], operation_id="getSolutionPerformance")
async def solution_performance(request: Request, service: DatabricksServiceDep, response: Response) -> list[SolutionPerformanceOut]:
    """Get payment solution performance from Databricks; mock fallback."""
    if _is_mock_request(request):
        _set_data_source_header(response, service, forced_mock=True)
        return [SolutionPerformanceOut(**row) for row in _mock.mock_solution_performance()]
    data = await service.get_solution_performance()
    if not data:
        data = _mock.mock_solution_performance()
    _set_data_source_header(response, service)
    return [SolutionPerformanceOut(**row) for row in data]


@router.get(
    "/smart-checkout/service-paths",
    response_model=list[SmartCheckoutServicePathOut],
    operation_id="getSmartCheckoutServicePaths",
)
async def smart_checkout_service_paths(
    request: Request,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = 25,
) -> list[SmartCheckoutServicePathOut]:
    """Payment-link performance by Smart Checkout service path for the given entity."""
    limit = max(1, min(limit, 100))
    if _is_mock_request(request):
        return [SmartCheckoutServicePathOut(**row) for row in _mock.mock_smart_checkout_service_paths()]
    data = await service.get_smart_checkout_service_paths(entity=entity, limit=limit)
    if not data:
        data = _mock.mock_smart_checkout_service_paths()
    return [SmartCheckoutServicePathOut(**row) for row in data]


@router.get(
    "/smart-checkout/path-performance",
    response_model=list[SmartCheckoutPathPerformanceOut],
    operation_id="getSmartCheckoutPathPerformance",
)
async def smart_checkout_path_performance(
    request: Request,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = 20,
) -> list[SmartCheckoutPathPerformanceOut]:
    """Payment-link performance by recommended Smart Checkout path for the given entity."""
    limit = max(1, min(limit, 50))
    if _is_mock_request(request):
        return [SmartCheckoutPathPerformanceOut(**row) for row in _mock.mock_smart_checkout_path_performance()]
    data = await service.get_smart_checkout_path_performance(entity=entity, limit=limit)
    if not data:
        data = _mock.mock_smart_checkout_path_performance()
    return [SmartCheckoutPathPerformanceOut(**row) for row in data]


@router.get(
    "/smart-checkout/3ds-funnel",
    response_model=list[ThreeDSFunnelOut],
    operation_id="getThreeDsFunnel",
)
async def three_ds_funnel(
    request: Request,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    days: int = 30,
) -> list[ThreeDSFunnelOut]:
    """Payment-link 3DS funnel metrics by day for the given entity."""
    days = max(1, min(days, 90))
    if _is_mock_request(request):
        return [ThreeDSFunnelOut(**row) for row in _mock.mock_3ds_funnel()]
    data = await service.get_3ds_funnel(entity=entity, days=days)
    if not data:
        data = _mock.mock_3ds_funnel()
    return [ThreeDSFunnelOut(**row) for row in data]


@router.get(
    "/reason-codes",
    response_model=list[ReasonCodeOut],
    operation_id="getReasonCodes",
)
async def reason_codes(
    request: Request,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = 50,
) -> list[ReasonCodeOut]:
    """Declines consolidated into unified reason-code taxonomy for the given entity."""
    limit = max(1, min(limit, 200))
    if _is_mock_request(request):
        data = _mock.mock_reason_code_insights()[:limit]
    else:
        data = await service.get_reason_codes(entity=entity, limit=limit)
        if not data:
            data = _mock.mock_reason_code_insights()[:limit]
    # Fill defaults for fields required by ReasonCodeOut but absent in insight mock data
    return [
        ReasonCodeOut(
            entry_system=row["entry_system"],
            flow_type=row["flow_type"],
            decline_reason_standard=row["decline_reason_standard"],
            decline_reason_group=row["decline_reason_group"],
            recommended_action=row["recommended_action"],
            decline_count=row["decline_count"],
            pct_of_declines=row.get("pct_of_declines"),
            total_declined_value=row["total_declined_value"],
            avg_amount=row.get("avg_amount", row["total_declined_value"] / max(row["decline_count"], 1)),
            affected_merchants=row.get("affected_merchants", max(1, row["decline_count"] // 10)),
        )
        for row in data
    ]


@router.get(
    "/reason-codes/insights",
    response_model=list[ReasonCodeInsightOut],
    operation_id="getReasonCodeInsights",
)
async def reason_code_insights(
    request: Request,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = 50,
) -> list[ReasonCodeInsightOut]:
    """Reason-code insights with estimated recoverability for the given entity (demo heuristic)."""
    limit = max(1, min(limit, 200))
    if _is_mock_request(request):
        return [ReasonCodeInsightOut(**row) for row in _mock.mock_reason_code_insights()]
    data = await service.get_reason_code_insights(entity=entity, limit=limit)
    if not data:
        data = _mock.mock_reason_code_insights()
    return [ReasonCodeInsightOut(**row) for row in data]


@router.get(
    "/factors-delaying-approval",
    response_model=list[ReasonCodeInsightOut],
    operation_id="getFactorsDelayingApproval",
)
async def factors_delaying_approval(
    request: Request,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
    limit: int = Query(10, ge=1, le=50, description="Max number of factors to return"),
) -> list[ReasonCodeInsightOut]:
    """
    Top conditions or factors that delay or reduce approval rates, with recommended actions.
    Use this to discover what to fix and how to accelerate approvals.
    """
    if _is_mock_request(request):
        return [ReasonCodeInsightOut(**row) for row in _mock.mock_reason_code_insights()[:limit]]
    data = await service.get_reason_code_insights(entity=entity, limit=limit)
    if not data:
        data = _mock.mock_reason_code_insights()[:limit]
    return [ReasonCodeInsightOut(**row) for row in data]


@router.get(
    "/reason-codes/entry-systems",
    response_model=list[EntrySystemDistributionOut],
    operation_id="getEntrySystemDistribution",
)
async def entry_system_distribution(
    request: Request,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Entity or country code (e.g. BR). Filter by Getnet entity."),
) -> list[EntrySystemDistributionOut]:
    """Transaction distribution by entry system for the given entity (coverage check)."""
    if _is_mock_request(request):
        return [EntrySystemDistributionOut(**row) for row in _mock.mock_entry_system_distribution()]
    data = await service.get_entry_system_distribution(entity=entity)
    if not data:
        data = _mock.mock_entry_system_distribution()
    return [EntrySystemDistributionOut(**row) for row in data]


@router.get(
    "/geography",
    response_model=list[GeographyOut],
    operation_id="getGeography",
)
async def geography(
    request: Request,
    service: DatabricksServiceDep,
    limit: int = Query(50, ge=1, le=200, description="Max countries to return"),
) -> list[GeographyOut]:
    """Transaction count and approval rate by country for geographic distribution (e.g. world map). Data from Databricks v_performance_by_geography."""
    if _is_mock_request(request):
        data = _mock.mock_geography()
    else:
        data = await service.get_performance_by_geography(limit=limit)
        if not data:
            data = _mock.mock_geography()
    return [
        GeographyOut(
            country=str(r.get("country", "")),
            transaction_count=int(r.get("transaction_count", 0)),
            approval_rate_pct=float(r["approval_rate_pct"]) if r.get("approval_rate_pct") is not None else None,
            total_transaction_value=float(r["total_transaction_value"]) if r.get("total_transaction_value") is not None else None,
        )
        for r in data
    ]


@router.get(
    "/last-hour",
    response_model=LastHourPerformanceOut,
    operation_id="getLastHourPerformance",
)
async def last_hour_performance(request: Request, service: DatabricksServiceDep) -> LastHourPerformanceOut:
    """Last-hour performance for real-time monitor; mock fallback."""
    if _is_mock_request(request):
        return LastHourPerformanceOut(**_mock.mock_last_hour_performance())
    data = await service.get_last_hour_performance()
    if not data or data.get("transactions_last_hour", 0) == 0:
        data = _mock.mock_last_hour_performance()
    return LastHourPerformanceOut(**data)


@router.get(
    "/last-60-seconds",
    response_model=Last60SecondsPerformanceOut,
    operation_id="getLast60SecondsPerformance",
)
async def last_60_seconds_performance(request: Request, service: DatabricksServiceDep) -> Last60SecondsPerformanceOut:
    """Last-60-seconds performance for real-time live metrics; mock fallback."""
    if _is_mock_request(request):
        return Last60SecondsPerformanceOut(**_mock.mock_last_60_seconds_performance())
    data = await service.get_last_60_seconds_performance()
    if not data or data.get("transactions_last_60s", 0) == 0:
        data = _mock.mock_last_60_seconds_performance()
    return Last60SecondsPerformanceOut(**data)


@router.get(
    "/data-quality",
    response_model=DataQualitySummaryOut,
    operation_id="getDataQualitySummary",
)
async def data_quality_summary(request: Request, service: DatabricksServiceDep) -> DataQualitySummaryOut:
    """Data quality summary (bronze/silver volumes, retention); mock fallback."""
    if _is_mock_request(request):
        return DataQualitySummaryOut(**_mock.mock_data_quality_summary())
    data = await service.get_data_quality_summary()
    if not data or data.get("bronze_last_24h", 0) == 0:
        data = _mock.mock_data_quality_summary()
    return DataQualitySummaryOut(**data)


@router.get(
    "/streaming-tps",
    response_model=list[StreamingTpsPointOut],
    operation_id="getStreamingTps",
)
async def streaming_tps(
    request: Request,
    service: DatabricksServiceDep,
    limit_seconds: int = Query(300, ge=10, le=3600, description="Time window in seconds (min 10 for real-time)"),
) -> list[StreamingTpsPointOut]:
    """Real-time TPS from streaming pipeline (v_streaming_volume_per_second). Simulate Transaction Events -> ETL -> Payment Real-Time Stream."""
    if _is_mock_request(request):
        return [StreamingTpsPointOut(event_second=r["event_second"], records_per_second=r["records_per_second"]) for r in _mock.mock_streaming_tps()]
    data = await service.get_streaming_tps(limit_seconds=limit_seconds)
    if not data:
        data = _mock.mock_streaming_tps()
    return [StreamingTpsPointOut(event_second=r["event_second"], records_per_second=r["records_per_second"]) for r in data]


@router.get(
    "/command-center/entry-throughput",
    response_model=list[CommandCenterEntryThroughputPointOut],
    operation_id="getCommandCenterEntryThroughput",
)
async def command_center_entry_throughput(
    request: Request,
    service: DatabricksServiceDep,
    entity: str = Query(DEFAULT_ENTITY, description="Country/entity code (e.g. BR)."),
    limit_minutes: int = Query(30, ge=1, le=60, description="Time window in minutes"),
) -> list[CommandCenterEntryThroughputPointOut]:
    """Real-time throughput by entry system (PD, WS, SEP, Checkout) for Command Center. Derived from streaming TPS with approximate entry-system shares."""
    if _is_mock_request(request):
        data = _mock.mock_entry_throughput()
    else:
        data = await service.get_command_center_entry_throughput(entity=entity, limit_minutes=limit_minutes)
        if not data:
            data = _mock.mock_entry_throughput()
    return [
        CommandCenterEntryThroughputPointOut(ts=r["ts"], PD=r["PD"], WS=r["WS"], SEP=r["SEP"], Checkout=r["Checkout"])
        for r in data
    ]


@router.get(
    "/active-alerts",
    response_model=list[ActiveAlertOut],
    operation_id="getActiveAlerts",
)
async def active_alerts(
    request: Request,
    service: DatabricksServiceDep,
    limit: int = Query(50, ge=1, le=100, description="Max alerts to return"),
) -> list[ActiveAlertOut]:
    """Active alerts for command center (approval rate drop, high fraud, etc.). Data from Databricks v_active_alerts."""
    if _is_mock_request(request):
        return [ActiveAlertOut(**row) for row in _mock.mock_active_alerts()]
    data = await service.get_active_alerts(limit=limit)
    if not data:
        data = _mock.mock_active_alerts()
    return [ActiveAlertOut(**row) for row in data]


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
async def false_insights_metric(request: Request, service: DatabricksServiceDep, days: int = 30) -> list[FalseInsightsMetricOut]:
    """False Insights counter-metric time series (expert review invalid/non-actionable)."""
    days = max(1, min(days, 180))
    if _is_mock_request(request):
        return [FalseInsightsMetricOut(**row) for row in _mock.mock_false_insights_metric()]
    data = await service.get_false_insights_metric(days=days)
    if not data:
        data = _mock.mock_false_insights_metric()
    return [FalseInsightsMetricOut(**row) for row in data]


@router.get(
    "/retry/performance",
    response_model=list[RetryPerformanceOut],
    operation_id="getRetryPerformance",
)
async def retry_performance(request: Request, service: DatabricksServiceDep, limit: int = 50) -> list[RetryPerformanceOut]:
    """Smart Retry performance with scenario split."""
    limit = max(1, min(limit, 200))
    if _is_mock_request(request):
        return [RetryPerformanceOut(**row) for row in _mock.mock_retry_performance()]
    data = await service.get_retry_performance(limit=limit)
    if not data:
        data = _mock.mock_retry_performance()
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


@router.get(
    "/declines/recovery-opportunities",
    response_model=list[dict],
    operation_id="getDeclineRecoveryOpportunities",
)
async def decline_recovery_opportunities(
    request: Request,
    service: DatabricksServiceDep,
    limit: int = Query(20, ge=1, le=100, description="Max rows"),
) -> list[dict]:
    """Decline recovery opportunities ranked by estimated recoverable value; mock fallback."""
    if _is_mock_request(request):
        return _mock.mock_decline_recovery_opportunities()[:limit]
    data = await service.get_decline_recovery_opportunities(limit=limit)
    if not data:
        data = _mock.mock_decline_recovery_opportunities()[:limit]
    return data


@router.get(
    "/card-network-performance",
    response_model=list[dict],
    operation_id="getCardNetworkPerformance",
)
async def card_network_performance(
    request: Request,
    service: DatabricksServiceDep,
    limit: int = Query(20, ge=1, le=50, description="Max rows"),
) -> list[dict]:
    """Approval rate and volume by card network; mock fallback."""
    if _is_mock_request(request):
        return _mock.mock_card_network_performance()[:limit]
    data = await service.get_card_network_performance(limit=limit)
    if not data:
        data = _mock.mock_card_network_performance()[:limit]
    return data


@router.get(
    "/merchant-segment-performance",
    response_model=list[dict],
    operation_id="getMerchantSegmentPerformance",
)
async def merchant_segment_performance(
    request: Request,
    service: DatabricksServiceDep,
    limit: int = Query(20, ge=1, le=50, description="Max rows"),
) -> list[dict]:
    """Approval rate and volume by merchant segment; mock fallback."""
    if _is_mock_request(request):
        return _mock.mock_merchant_segment_performance()[:limit]
    data = await service.get_merchant_segment_performance(limit=limit)
    if not data:
        data = _mock.mock_merchant_segment_performance()[:limit]
    return data


@router.get(
    "/daily-trends",
    response_model=list[dict],
    operation_id="getDailyTrends",
)
async def daily_trends(
    request: Request,
    service: DatabricksServiceDep,
    days: int = Query(30, ge=1, le=90, description="Number of days"),
) -> list[dict]:
    """Daily approval rate and volume trends; mock fallback."""
    if _is_mock_request(request):
        return _mock.mock_daily_trends(days=days)
    data = await service.get_daily_trends(days=days)
    if not data:
        data = _mock.mock_daily_trends(days=days)
    return data


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
    request: Request,
    session: OptionalSessionDep,
    service: DatabricksServiceDep,
    limit: int = 20,
) -> list[DeclineBucketOut]:
    """Get decline summary: from Databricks Unity Catalog when available, otherwise from local database."""
    if _is_mock_request(request):
        return [DeclineBucketOut(**r) for r in _mock.mock_decline_summary()[:limit]]
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
            logger.debug("UC view recommendations unavailable; falling back to local DB", exc_info=True)
    if session is None:
        return [DeclineBucketOut(**r) for r in _mock.mock_decline_summary()[:limit]]
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
    if not rows:
        return [DeclineBucketOut(**r) for r in _mock.mock_decline_summary()[:limit]]
    out: list[DeclineBucketOut] = []
    for reason, count in rows:
        out.append(DeclineBucketOut(key=reason or "unknown", count=int(count or 0)))
    return out


@router.get(
    "/declines/databricks",
    response_model=list[DeclineBucketOut],
    operation_id="getDatabricksDeclines",
)
async def databricks_decline_summary(request: Request, service: DatabricksServiceDep) -> list[DeclineBucketOut]:
    """Get decline summary from Databricks Unity Catalog with recovery insights; mock fallback."""
    if _is_mock_request(request):
        data = _mock.mock_decline_summary()
    else:
        data = await service.get_decline_summary()
        if not data:
            data = _mock.mock_decline_summary()
    return [
        DeclineBucketOut(
            key=row.get("decline_reason", row.get("key", "unknown")),
            count=int(row.get("decline_count", row.get("count", 0))),
            pct_of_declines=row.get("pct_of_declines"),
            total_value=row.get("total_declined_value", row.get("total_value")),
            recoverable_pct=row.get("recoverable_pct"),
        )
        for row in data
    ]

