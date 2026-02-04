from __future__ import annotations

from dataclasses import asdict, dataclass
from uuid import uuid4

from .schemas import (
    AuthDecisionOut,
    AuthPath,
    DecisionContext,
    RetryDecisionOut,
    RiskTier,
    RoutingDecisionOut,
)


def _audit_id() -> str:
    return uuid4().hex


def _risk_tier(ctx: DecisionContext) -> RiskTier:
    """
    Very small baseline heuristic.
    Replace with Feature Store + Model Serving score in a real implementation.
    """

    score = ctx.risk_score
    if score is None:
        # Prefer device trust if present; otherwise assume medium.
        if ctx.device_trust_score is not None and ctx.device_trust_score >= 0.9:
            return RiskTier.low
        return RiskTier.medium
    if score >= 0.8:
        return RiskTier.high
    if score >= 0.4:
        return RiskTier.medium
    return RiskTier.low


def decide_authentication(ctx: DecisionContext) -> AuthDecisionOut:
    tier = _risk_tier(ctx)

    if ctx.supports_passkey and tier == RiskTier.low:
        return AuthDecisionOut(
            audit_id=_audit_id(),
            path=AuthPath.passkey,
            risk_tier=tier,
            reason="Low risk and passkey supported; prefer strongest low-friction auth.",
        )

    if tier == RiskTier.high:
        return AuthDecisionOut(
            audit_id=_audit_id(),
            path=AuthPath.three_ds_challenge,
            risk_tier=tier,
            reason="High risk; require step-up authentication.",
        )

    if tier == RiskTier.medium:
        return AuthDecisionOut(
            audit_id=_audit_id(),
            path=AuthPath.three_ds_frictionless,
            risk_tier=tier,
            reason="Medium risk; attempt frictionless 3DS to improve issuer confidence.",
        )

    return AuthDecisionOut(
        audit_id=_audit_id(),
        path=AuthPath.none,
        risk_tier=tier,
        reason="Low risk; avoid unnecessary friction.",
    )


_SOFT_DECLINE_CODES = {
    "51",  # insufficient funds (often retryable depending on use case)
    "91",  # issuer unavailable
    "96",  # system malfunction
    "try_again_later",
    "do_not_honor_soft",
}


def decide_retry(ctx: DecisionContext) -> RetryDecisionOut:
    # Only retry up to max attempts.
    max_attempts = 3
    if ctx.attempt_number >= max_attempts:
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=False,
            max_attempts=max_attempts,
            reason="Max retry attempts reached.",
        )

    code = (ctx.previous_decline_code or "").strip().lower()
    reason = (ctx.previous_decline_reason or "").strip().lower()

    if ctx.is_recurring and (code in _SOFT_DECLINE_CODES or "timeout" in reason):
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=True,
            retry_after_seconds=15 * 60,
            max_attempts=max_attempts,
            reason="Recurring + soft decline; schedule safe retry with backoff.",
        )

    if code in {"91", "96"}:
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=True,
            retry_after_seconds=60,
            max_attempts=max_attempts,
            reason="Transient issuer/system decline; quick retry may recover.",
        )

    return RetryDecisionOut(
        audit_id=_audit_id(),
        should_retry=False,
        max_attempts=max_attempts,
        reason="Not a recognized soft decline; avoid risky retries.",
    )


@dataclass(frozen=True)
class RouteCandidate:
    name: str
    score: float


def decide_routing(ctx: DecisionContext) -> RoutingDecisionOut:
    """
    Minimal routing scaffold.

    Replace with bandit/optimizer under constraints (cost/SLA/geo) in production.
    """

    # Example: simple deterministic candidate set.
    candidates = [
        RouteCandidate("psp_primary", 0.6),
        RouteCandidate("psp_secondary", 0.55),
        RouteCandidate("psp_tertiary", 0.5),
    ]

    # Small preference: if issuer country is set and not domestic, prefer secondary.
    if ctx.issuer_country and ctx.issuer_country.upper() not in {"US"}:
        candidates = [
            RouteCandidate("psp_secondary", 0.62),
            RouteCandidate("psp_primary", 0.58),
            RouteCandidate("psp_tertiary", 0.5),
        ]

    sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
    primary = sorted_candidates[0].name
    cascade = ctx.attempt_number > 0  # cascade only after an initial failure

    return RoutingDecisionOut(
        audit_id=_audit_id(),
        primary_route=primary,
        candidates=[c.name for c in sorted_candidates],
        should_cascade=cascade,
        reason="Baseline routing heuristic; cascade after initial attempt.",
    )


def serialize_context(ctx: DecisionContext) -> dict:
    # Pydantic v2: `model_dump` is available; keep compatibility via getattr.
    dump = getattr(ctx, "model_dump", None)
    if callable(dump):
        return dump()
    return ctx.dict()  # type: ignore[no-any-return]

