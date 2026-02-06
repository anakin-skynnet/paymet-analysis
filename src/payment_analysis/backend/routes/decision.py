from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ..db_models import DecisionLog
from ..decisioning.policies import (
    decide_authentication,
    decide_retry,
    decide_routing,
    serialize_context,
)
from ..decisioning.schemas import (
    AuthDecisionOut,
    DecisionContext,
    RetryDecisionOut,
    RoutingDecisionOut,
)
from ..dependencies import SessionDep
from ..services.databricks_service import get_databricks_service

router = APIRouter(tags=["decisioning"])


class MLPredictionInput(BaseModel):
    """Input for ML model predictions."""
    amount: float
    fraud_score: float = 0.1
    device_trust_score: float = 0.8
    is_cross_border: bool = False
    retry_count: int = 0
    uses_3ds: bool = False
    merchant_segment: str = "retail"
    card_network: str = "visa"


class ApprovalPredictionOut(BaseModel):
    """Output from approval propensity model."""
    approval_probability: float
    should_approve: bool
    model_version: str


class RiskPredictionOut(BaseModel):
    """Output from risk scoring model."""
    risk_score: float
    is_high_risk: bool
    risk_tier: str


class RoutingPredictionOut(BaseModel):
    """Output from smart routing model."""
    recommended_solution: str
    confidence: float
    alternatives: list[str]


@router.post(
    "/authentication", response_model=AuthDecisionOut, operation_id="decideAuthentication"
)
def authentication(ctx: DecisionContext, session: SessionDep) -> AuthDecisionOut:
    decision = decide_authentication(ctx)
    session.add(
        DecisionLog(
            audit_id=decision.audit_id,
            decision_type="authentication",
            request=serialize_context(ctx),
            response=decision.model_dump(),
        )
    )
    session.commit()
    return decision


@router.post("/retry", response_model=RetryDecisionOut, operation_id="decideRetry")
def retry(ctx: DecisionContext, session: SessionDep) -> RetryDecisionOut:
    decision = decide_retry(ctx)
    session.add(
        DecisionLog(
            audit_id=decision.audit_id,
            decision_type="retry",
            request=serialize_context(ctx),
            response=decision.model_dump(),
        )
    )
    session.commit()
    return decision


@router.post("/routing", response_model=RoutingDecisionOut, operation_id="decideRouting")
def routing(ctx: DecisionContext, session: SessionDep) -> RoutingDecisionOut:
    decision = decide_routing(ctx)
    session.add(
        DecisionLog(
            audit_id=decision.audit_id,
            decision_type="routing",
            request=serialize_context(ctx),
            response=decision.model_dump(),
        )
    )
    session.commit()
    return decision


# ML Model Serving Endpoints


@router.post(
    "/ml/approval",
    response_model=ApprovalPredictionOut,
    operation_id="predictApproval",
)
async def predict_approval(features: MLPredictionInput) -> ApprovalPredictionOut:
    """Get approval probability from ML model serving endpoint."""
    service = get_databricks_service()
    result = await service.call_approval_model(features.model_dump())
    return ApprovalPredictionOut(**result)


@router.post(
    "/ml/risk",
    response_model=RiskPredictionOut,
    operation_id="predictRisk",
)
async def predict_risk(features: MLPredictionInput) -> RiskPredictionOut:
    """Get risk score from ML model serving endpoint."""
    service = get_databricks_service()
    result = await service.call_risk_model(features.model_dump())
    return RiskPredictionOut(**result)


@router.post(
    "/ml/routing",
    response_model=RoutingPredictionOut,
    operation_id="predictRouting",
)
async def predict_routing(features: MLPredictionInput) -> RoutingPredictionOut:
    """Get optimal routing recommendation from ML model."""
    service = get_databricks_service()
    result = await service.call_routing_model(features.model_dump())
    return RoutingPredictionOut(**result)

