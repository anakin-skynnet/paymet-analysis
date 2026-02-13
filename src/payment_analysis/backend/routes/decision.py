"""Decisioning API: real-time auth, retry, and routing decisions with A/B experiment support.

ML predictions (approval, risk, routing) are fetched from Databricks Model Serving
when the connection is available; otherwise mock predictions are returned.
Validate with GET /api/v1/health/databricks. See docs/GUIDE.md §10 (Data sources & code guidelines).
"""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import select

from ..db_models import DecisionLog, Experiment, ExperimentAssignment
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
from ..dependencies import SessionDep, DatabricksServiceDep

router = APIRouter(tags=["decisioning"])


def _get_or_assign_variant(
    session: SessionDep,
    experiment_id: str | None,
    subject_key: str,
) -> str | None:
    """Resolve A/B variant for this subject. If no assignment exists and experiment is assignable, auto-enroll with 50/50 control/treatment (deterministic by subject_key). Returns None if no experiment or experiment not assignable."""
    if not experiment_id or not subject_key:
        return None
    stmt = select(ExperimentAssignment).where(
        ExperimentAssignment.experiment_id == experiment_id,
        ExperimentAssignment.subject_key == subject_key,
    ).limit(1)
    assignment = session.exec(stmt).first()
    if assignment:
        return assignment.variant
    exp = session.get(Experiment, experiment_id)
    if not exp or exp.status not in {"running", "draft"}:
        return None
    variant = "treatment" if (hashlib.sha256(subject_key.encode()).digest()[-1] % 2 == 1) else "control"
    session.add(
        ExperimentAssignment(
            experiment_id=experiment_id,
            subject_key=subject_key,
            variant=variant,
        )
    )
    session.commit()
    return variant


def _with_ab(decision: Any, experiment_id: str | None, variant: str | None) -> dict[str, Any]:
    """Merge experiment_id and variant into decision response for logging and response."""
    out = decision.model_dump()
    if experiment_id is not None:
        out["experiment_id"] = experiment_id
    if variant is not None:
        out["variant"] = variant
    return out


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


class RetryPredictionOut(BaseModel):
    """Output from smart retry model."""
    should_retry: bool
    retry_success_probability: float
    model_version: str


@router.post(
    "/authentication", response_model=AuthDecisionOut, operation_id="decideAuthentication"
)
def authentication(ctx: DecisionContext, session: SessionDep) -> AuthDecisionOut:
    subject_key = ctx.subject_key or ctx.merchant_id
    variant = _get_or_assign_variant(session, ctx.experiment_id, subject_key)
    variant = variant if variant is not None else "control"
    decision = decide_authentication(ctx, variant=variant)
    response = _with_ab(decision, ctx.experiment_id, variant)
    session.add(
        DecisionLog(
            audit_id=decision.audit_id,
            decision_type="authentication",
            request=serialize_context(ctx),
            response=response,
        )
    )
    session.commit()
    return AuthDecisionOut(**response)


@router.post("/retry", response_model=RetryDecisionOut, operation_id="decideRetry")
def retry(ctx: DecisionContext, session: SessionDep) -> RetryDecisionOut:
    subject_key = ctx.subject_key or ctx.merchant_id
    variant = _get_or_assign_variant(session, ctx.experiment_id, subject_key)
    variant = variant if variant is not None else "control"
    decision = decide_retry(ctx, variant=variant)
    response = _with_ab(decision, ctx.experiment_id, variant)
    session.add(
        DecisionLog(
            audit_id=decision.audit_id,
            decision_type="retry",
            request=serialize_context(ctx),
            response=response,
        )
    )
    session.commit()
    return RetryDecisionOut(**response)


@router.post("/routing", response_model=RoutingDecisionOut, operation_id="decideRouting")
def routing(ctx: DecisionContext, session: SessionDep) -> RoutingDecisionOut:
    subject_key = ctx.subject_key or ctx.merchant_id
    variant = _get_or_assign_variant(session, ctx.experiment_id, subject_key)
    variant = variant if variant is not None else "control"
    decision = decide_routing(ctx, variant=variant)
    response = _with_ab(decision, ctx.experiment_id, variant)
    session.add(
        DecisionLog(
            audit_id=decision.audit_id,
            decision_type="routing",
            request=serialize_context(ctx),
            response=response,
        )
    )
    session.commit()
    return RoutingDecisionOut(**response)


# ML Model Serving Endpoints


@router.post(
    "/ml/approval",
    response_model=ApprovalPredictionOut,
    operation_id="predictApproval",
)
async def predict_approval(
    service: DatabricksServiceDep,
    features: MLPredictionInput,
) -> ApprovalPredictionOut:
    """Get approval probability from ML model serving endpoint."""
    result = await service.call_approval_model(features.model_dump())
    return ApprovalPredictionOut(**result)


@router.post(
    "/ml/risk",
    response_model=RiskPredictionOut,
    operation_id="predictRisk",
)
async def predict_risk(
    service: DatabricksServiceDep,
    features: MLPredictionInput,
) -> RiskPredictionOut:
    """Get risk score from ML model serving endpoint."""
    result = await service.call_risk_model(features.model_dump())
    return RiskPredictionOut(**result)


@router.post(
    "/ml/routing",
    response_model=RoutingPredictionOut,
    operation_id="predictRouting",
)
async def predict_routing(
    service: DatabricksServiceDep,
    features: MLPredictionInput,
) -> RoutingPredictionOut:
    """Get optimal routing recommendation from ML model."""
    result = await service.call_routing_model(features.model_dump())
    return RoutingPredictionOut(**result)


@router.post(
    "/ml/retry",
    response_model=RetryPredictionOut,
    operation_id="predictRetry",
)
async def predict_retry(
    service: DatabricksServiceDep,
    features: MLPredictionInput,
) -> RetryPredictionOut:
    """Get retry success likelihood from smart retry model (recovery optimization)."""
    result = await service.call_retry_model(features.model_dump())
    return RetryPredictionOut(**result)

