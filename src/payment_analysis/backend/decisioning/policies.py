"""Decision policies: authentication, retry, and routing rules with A/B variant support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
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


def _risk_tier(ctx: DecisionContext, *, params: Optional[Any] = None) -> RiskTier:
    """Risk tier from score with data-driven thresholds (from DecisionConfig via Lakebase)."""

    score = ctx.risk_score
    # Use Lakebase thresholds when available; fall back to sensible defaults.
    high_threshold = getattr(params, "risk_threshold_high", None) or 0.75
    med_threshold = getattr(params, "risk_threshold_medium", None) or 0.35
    trust_floor = getattr(params, "device_trust_low_risk", None) or 0.90

    if score is None:
        # Prefer device trust if present; otherwise assume medium.
        if ctx.device_trust_score is not None and ctx.device_trust_score >= trust_floor:
            return RiskTier.low
        return RiskTier.medium
    if score >= high_threshold:
        return RiskTier.high
    if score >= med_threshold:
        return RiskTier.medium
    return RiskTier.low


def decide_authentication(
    ctx: DecisionContext,
    variant: Optional[str] = None,
    *,
    params: Optional[Any] = None,
) -> AuthDecisionOut:
    tier = _risk_tier(ctx, params=params)
    is_treatment = variant == "treatment" or variant == "B"

    if ctx.supports_passkey and tier == RiskTier.low:
        # Treatment: prefer 3DS frictionless for low risk (stricter, measure lift)
        if is_treatment:
            return AuthDecisionOut(
                audit_id=_audit_id(),
                path=AuthPath.three_ds_frictionless,
                risk_tier=tier,
                reason="[A/B treatment] Low risk; 3DS frictionless for experiment.",
            )
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
        # Treatment: try challenge instead of frictionless (stricter)
        if is_treatment:
            return AuthDecisionOut(
                audit_id=_audit_id(),
                path=AuthPath.three_ds_challenge,
                risk_tier=tier,
                reason="[A/B treatment] Medium risk; step-up challenge for experiment.",
            )
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


def decide_retry(
    ctx: DecisionContext,
    variant: Optional[str] = None,
    *,
    params: Optional[Any] = None,
    decline_codes: Optional[Any] = None,
) -> RetryDecisionOut:
    is_treatment = variant == "treatment" or variant == "B"
    # Use Lakebase-driven max_attempts via params when available
    max_attempts_ctrl = getattr(params, "retry_max_attempts_control", None) or 3
    max_attempts_treat = getattr(params, "retry_max_attempts_treatment", None) or 4
    max_attempts = max_attempts_treat if is_treatment else max_attempts_ctrl

    if ctx.attempt_number >= max_attempts:
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=False,
            max_attempts=max_attempts,
            reason="Max retry attempts reached.",
        )

    code = (ctx.previous_decline_code or "").strip().lower()
    reason = (ctx.previous_decline_reason or "").strip().lower()

    # Use Lakebase decline codes when provided; fall back to hardcoded set
    soft_codes = set(_SOFT_DECLINE_CODES)
    if decline_codes and isinstance(decline_codes, dict):
        soft_codes = set(decline_codes.keys()) | soft_codes

    # Get backoff from Lakebase decline code config when available
    def _db_backoff(c: str, default: int) -> int:
        if decline_codes and isinstance(decline_codes, dict) and c in decline_codes:
            return getattr(decline_codes[c], "default_backoff_seconds", default)
        return default

    if ctx.is_recurring and (code in soft_codes or "timeout" in reason):
        # Treatment: shorter backoff for recurring (from Lakebase params)
        ctrl_backoff = getattr(params, "retry_backoff_recurring_control", None) or 900
        treat_backoff = getattr(params, "retry_backoff_recurring_treatment", None) or 300
        backoff = treat_backoff if is_treatment else ctrl_backoff
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=True,
            retry_after_seconds=backoff,
            max_attempts=max_attempts,
            reason="Recurring + soft decline; schedule retry with backoff." + (" [A/B treatment]" if is_treatment else ""),
        )

    if code in {"91", "96"}:
        transient_backoff = _db_backoff(code, getattr(params, "retry_backoff_transient", None) or 60)
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=True,
            retry_after_seconds=transient_backoff,
            max_attempts=max_attempts,
            reason="Transient issuer/system decline; quick retry may recover.",
        )

    # Treatment: allow one extra retry for do_not_honor_soft
    if is_treatment and ("do_not_honor" in reason or "51" in code):
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=True,
            retry_after_seconds=30 * 60,
            max_attempts=max_attempts,
            reason="[A/B treatment] Soft decline; allow retry with backoff.",
        )

    # ML override: if model predicts high retry success, allow one retry
    # Use ML-suggested delay when available; otherwise estimate from probability
    ml_retry_prob = ctx.metadata.get("ml_retry_probability")
    if ml_retry_prob is not None and float(ml_retry_prob) >= 0.65 and ctx.attempt_number < max_attempts:
        ml_delay = ctx.metadata.get("ml_retry_delay_seconds")
        if ml_delay is not None:
            backoff = int(float(ml_delay))
        else:
            # Estimate backoff from probability: higher confidence -> shorter delay
            prob = float(ml_retry_prob)
            backoff = max(60, int(600 * (1 - prob)))  # 65% -> 210s, 90% -> 60s
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=True,
            retry_after_seconds=backoff,
            max_attempts=max_attempts,
            reason=f"ML model predicts {float(ml_retry_prob):.0%} retry success; retry in {backoff}s.",
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


def decide_routing(
    ctx: DecisionContext,
    variant: Optional[str] = None,
    *,
    params: Optional[Any] = None,
    route_scores: Optional[Any] = None,
) -> RoutingDecisionOut:
    """Data-driven routing with Lakebase RoutePerformance scores and A/B support."""
    is_treatment = variant == "treatment" or variant == "B"
    domestic = getattr(params, "routing_domestic_country", None) or "BR"

    # Use Lakebase route performance data when available
    if route_scores and isinstance(route_scores, list) and len(route_scores) >= 2:
        candidates = [
            RouteCandidate(getattr(rs, "route_name", str(rs)), getattr(rs, "approval_rate_pct", 50.0) / 100.0)
            for rs in route_scores
        ]
        reason_suffix = "Data-driven routing from RoutePerformance metrics."
        if is_treatment and len(candidates) >= 2:
            # Treatment: swap top two routes to measure lift
            candidates[0], candidates[1] = candidates[1], candidates[0]
            reason_suffix += " [A/B treatment] Route order reversed."
    else:
        # Fallback: hardcoded heuristic
        if is_treatment:
            candidates = [
                RouteCandidate("psp_secondary", 0.62),
                RouteCandidate("psp_primary", 0.58),
                RouteCandidate("psp_tertiary", 0.5),
            ]
            reason_suffix = " [A/B treatment] Secondary-first routing."
        else:
            candidates = [
                RouteCandidate("psp_primary", 0.6),
                RouteCandidate("psp_secondary", 0.55),
                RouteCandidate("psp_tertiary", 0.5),
            ]
            # Small preference: if issuer country is set and not domestic, prefer secondary.
            if ctx.issuer_country and ctx.issuer_country.upper() != domestic:
                candidates = [
                    RouteCandidate("psp_secondary", 0.62),
                    RouteCandidate("psp_primary", 0.58),
                    RouteCandidate("psp_tertiary", 0.5),
                ]
            reason_suffix = "Baseline routing heuristic; cascade after initial attempt."

    # ML routing override: prefer ML-recommended route when confidence is high
    ml_route = ctx.metadata.get("ml_recommended_route")
    ml_conf = ctx.metadata.get("ml_route_confidence", 0.0)
    if ml_route and float(ml_conf) >= 0.7:
        # Move ML-recommended route to front
        ml_candidates = [c for c in candidates if c.name == ml_route]
        other_candidates = [c for c in candidates if c.name != ml_route]
        if ml_candidates:
            candidates = ml_candidates + other_candidates
            reason_suffix = f"ML-optimised routing (confidence {float(ml_conf):.0%}). " + reason_suffix

    sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
    primary = sorted_candidates[0].name
    cascade = ctx.attempt_number > 0

    return RoutingDecisionOut(
        audit_id=_audit_id(),
        primary_route=primary,
        candidates=[c.name for c in sorted_candidates],
        should_cascade=cascade,
        reason=reason_suffix,
    )


def serialize_context(ctx: DecisionContext) -> dict:
    """Serialize a DecisionContext to a plain dict.

    Compatible with both Pydantic v1 (``.dict()``) and v2 (``.model_dump()``).
    """
    dump = getattr(ctx, "model_dump", None)
    if callable(dump):
        return dump()
    # Pydantic v1 fallback; removed in v3+.
    legacy = getattr(ctx, "dict", None)
    if callable(legacy):
        return legacy()
    # Last resort: dataclass or plain-object fallback
    return dict(ctx)

