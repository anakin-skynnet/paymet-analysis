"""Decision policies: authentication, retry, and routing rules with A/B variant support.

All decision parameters are now data-driven via ``DecisionParams`` loaded from
Lakebase ``DecisionConfig`` table.  Hardcoded constants are only used as fallback
defaults when the database is unavailable.

ML model scores (risk, approval, retry, routing) are expected to be pre-enriched
into the ``DecisionContext`` by the ``DecisionEngine`` before these functions are
called.  The policies read ``ctx.risk_score``, ``ctx.metadata['ml_*']`` etc.
"""

from __future__ import annotations

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

# TYPE_CHECKING imports for type hints only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import DecisionParams, RetryableCode, RouteScore


# ---------------------------------------------------------------------------
# Defaults (used when DecisionParams is None – backwards compatibility)
# ---------------------------------------------------------------------------

_DEFAULT_RISK_HIGH = 0.75
_DEFAULT_RISK_MEDIUM = 0.35
_DEFAULT_DEVICE_TRUST_LOW = 0.90
_DEFAULT_RETRY_MAX_CONTROL = 3
_DEFAULT_RETRY_MAX_TREATMENT = 4
_DEFAULT_SOFT_DECLINE_CODES = {"51", "91", "96", "try_again_later", "do_not_honor_soft"}


def _audit_id() -> str:
    return uuid4().hex


def _risk_tier(
    ctx: DecisionContext,
    params: Optional["DecisionParams"] = None,
) -> RiskTier:
    """Determine risk tier from context score using configurable thresholds.

    When ``params`` is provided, thresholds come from Lakebase ``DecisionConfig``.
    Otherwise, uses hardcoded defaults for backwards compatibility.
    """
    high_threshold = params.risk_threshold_high if params else _DEFAULT_RISK_HIGH
    medium_threshold = params.risk_threshold_medium if params else _DEFAULT_RISK_MEDIUM
    device_trust_threshold = params.device_trust_low_risk if params else _DEFAULT_DEVICE_TRUST_LOW

    score = ctx.risk_score
    if score is None:
        # Prefer device trust if present; otherwise assume medium.
        if ctx.device_trust_score is not None and ctx.device_trust_score >= device_trust_threshold:
            return RiskTier.low
        return RiskTier.medium
    if score >= high_threshold:
        return RiskTier.high
    if score >= medium_threshold:
        return RiskTier.medium
    return RiskTier.low


def decide_authentication(
    ctx: DecisionContext,
    variant: Optional[str] = None,
    params: Optional["DecisionParams"] = None,
) -> AuthDecisionOut:
    """Decide authentication path based on risk tier, passkey support, and A/B variant.

    When ML-enriched, ``ctx.risk_score`` contains the model's score and thresholds
    come from Lakebase ``DecisionConfig``.  The ML approval probability
    (``ctx.metadata.get('ml_approval_probability')``) can further influence the
    path selection.
    """
    tier = _risk_tier(ctx, params)
    is_treatment = variant in ("treatment", "B")

    # ML approval probability can nudge medium → low when confidence is very high
    ml_approval_prob = ctx.metadata.get("ml_approval_probability")
    if ml_approval_prob is not None and tier == RiskTier.medium and float(ml_approval_prob) >= 0.92:
        tier = RiskTier.low
        # Don't change is_treatment; just adjust risk tier based on ML confidence

    if ctx.supports_passkey and tier == RiskTier.low:
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


def decide_retry(
    ctx: DecisionContext,
    variant: Optional[str] = None,
    params: Optional["DecisionParams"] = None,
    decline_codes: Optional[dict[str, "RetryableCode"]] = None,
) -> RetryDecisionOut:
    """Decide retry strategy using configurable decline codes and parameters.

    When ``decline_codes`` is provided (from Lakebase ``RetryableDeclineCode``),
    backoff timings and max attempts come from the database.  Otherwise, uses
    hardcoded defaults.

    ML retry probability (``ctx.metadata.get('ml_retry_probability')``) is used
    to override the "not retryable" default when the model predicts high
    recovery likelihood.
    """
    is_treatment = variant in ("treatment", "B")

    # Max attempts from config
    if params:
        max_attempts = params.retry_max_attempts_treatment if is_treatment else params.retry_max_attempts_control
    else:
        max_attempts = _DEFAULT_RETRY_MAX_TREATMENT if is_treatment else _DEFAULT_RETRY_MAX_CONTROL

    if ctx.attempt_number >= max_attempts:
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=False,
            max_attempts=max_attempts,
            reason="Max retry attempts reached.",
        )

    code = (ctx.previous_decline_code or "").strip().lower()
    reason = (ctx.previous_decline_reason or "").strip().lower()

    # Data-driven decline code lookup
    if decline_codes:
        matched_code = decline_codes.get(code)
        # Also try the reason as a code (standardized codes like FUNDS_OR_LIMIT)
        if not matched_code and reason:
            matched_code = decline_codes.get(reason)

        if matched_code:
            # Use database-configured backoff and attempts
            effective_max = min(matched_code.max_attempts, max_attempts)
            if ctx.attempt_number >= effective_max:
                return RetryDecisionOut(
                    audit_id=_audit_id(),
                    should_retry=False,
                    max_attempts=effective_max,
                    reason=f"Max attempts ({effective_max}) reached for {matched_code.code} ({matched_code.category}).",
                )

            backoff = matched_code.default_backoff_seconds
            if ctx.is_recurring and is_treatment and params:
                backoff = params.retry_backoff_recurring_treatment
            elif ctx.is_recurring and params:
                backoff = params.retry_backoff_recurring_control

            return RetryDecisionOut(
                audit_id=_audit_id(),
                should_retry=True,
                retry_after_seconds=backoff,
                max_attempts=effective_max,
                reason=f"Retryable decline ({matched_code.category}: {matched_code.code}); backoff {backoff}s."
                + (" [A/B treatment]" if is_treatment else ""),
            )
    else:
        # Fallback: hardcoded soft decline codes (backwards compatibility)
        soft_codes = _DEFAULT_SOFT_DECLINE_CODES

        if ctx.is_recurring and (code in soft_codes or "timeout" in reason):
            backoff = (params.retry_backoff_recurring_treatment if is_treatment else params.retry_backoff_recurring_control) if params else (300 if is_treatment else 900)
            return RetryDecisionOut(
                audit_id=_audit_id(),
                should_retry=True,
                retry_after_seconds=backoff,
                max_attempts=max_attempts,
                reason="Recurring + soft decline; schedule retry with backoff." + (" [A/B treatment]" if is_treatment else ""),
            )

        if code in {"91", "96"}:
            backoff = params.retry_backoff_transient if params else 60
            return RetryDecisionOut(
                audit_id=_audit_id(),
                should_retry=True,
                retry_after_seconds=backoff,
                max_attempts=max_attempts,
                reason="Transient issuer/system decline; quick retry may recover.",
            )

        if is_treatment and ("do_not_honor" in reason or "51" in code):
            backoff = params.retry_backoff_soft_treatment if params else 1800
            return RetryDecisionOut(
                audit_id=_audit_id(),
                should_retry=True,
                retry_after_seconds=backoff,
                max_attempts=max_attempts,
                reason="[A/B treatment] Soft decline; allow retry with backoff.",
            )

    # ML override: if model predicts high retry success, allow one retry
    ml_retry_prob = ctx.metadata.get("ml_retry_probability")
    if ml_retry_prob is not None and float(ml_retry_prob) >= 0.65 and ctx.attempt_number < max_attempts:
        return RetryDecisionOut(
            audit_id=_audit_id(),
            should_retry=True,
            retry_after_seconds=300,
            max_attempts=max_attempts,
            reason=f"ML model predicts {float(ml_retry_prob):.0%} retry success; allowing retry.",
        )

    return RetryDecisionOut(
        audit_id=_audit_id(),
        should_retry=False,
        max_attempts=max_attempts,
        reason="Not a recognized soft decline; avoid risky retries.",
    )


def decide_routing(
    ctx: DecisionContext,
    variant: Optional[str] = None,
    params: Optional["DecisionParams"] = None,
    route_scores: Optional[list["RouteScore"]] = None,
) -> RoutingDecisionOut:
    """Data-driven routing using Lakebase route performance data.

    When ``route_scores`` is provided (from Lakebase ``RoutePerformance``),
    routes are ranked by composite score (approval rate, latency, cost).
    Otherwise, uses hardcoded defaults.

    ML routing recommendation (``ctx.metadata.get('ml_recommended_route')``)
    is factored in when confidence is high.
    """
    is_treatment = variant in ("treatment", "B")
    domestic_country = params.routing_domestic_country if params else "BR"

    # Build candidate list from Lakebase route performance
    if route_scores and len(route_scores) > 0:
        candidates = [r.route_name for r in route_scores]

        # A/B treatment: reverse the top two routes
        if is_treatment and len(candidates) >= 2:
            candidates[0], candidates[1] = candidates[1], candidates[0]

        # Cross-border preference: if issuer country differs from domestic, prefer secondary
        if not is_treatment and ctx.issuer_country and ctx.issuer_country.upper() != domestic_country.upper():
            if len(candidates) >= 2:
                candidates[0], candidates[1] = candidates[1], candidates[0]

        # ML routing override: if model recommends a specific route with high confidence
        ml_route = ctx.metadata.get("ml_recommended_route")
        ml_confidence = ctx.metadata.get("ml_route_confidence", 0.0)
        if ml_route and float(ml_confidence) >= 0.80 and ml_route in candidates:
            # Move ML-recommended route to top
            candidates.remove(ml_route)
            candidates.insert(0, ml_route)

        primary = candidates[0]
        cascade = ctx.attempt_number > 0
        reason_parts = []
        if is_treatment:
            reason_parts.append("[A/B treatment]")
        reason_parts.append(f"Data-driven routing (top: {primary})")
        top_score = next((r for r in route_scores if r.route_name == primary), None)
        if top_score:
            reason_parts.append(f"approval={top_score.approval_rate_pct:.1f}%")
        if ml_route:
            reason_parts.append(f"ML={ml_route}@{float(ml_confidence):.0%}")

        return RoutingDecisionOut(
            audit_id=_audit_id(),
            primary_route=primary,
            candidates=candidates,
            should_cascade=cascade,
            reason=" | ".join(reason_parts),
        )

    # Fallback: hardcoded route scores (backwards compatibility)
    from dataclasses import dataclass as _dc

    @_dc(frozen=True)
    class _RC:
        name: str
        score: float

    if is_treatment:
        fallback = [_RC("psp_secondary", 0.62), _RC("psp_primary", 0.58), _RC("psp_tertiary", 0.5)]
        reason_suffix = " [A/B treatment] Secondary-first routing."
    else:
        fallback = [_RC("psp_primary", 0.6), _RC("psp_secondary", 0.55), _RC("psp_tertiary", 0.5)]
        if ctx.issuer_country and ctx.issuer_country.upper() != domestic_country.upper():
            fallback = [_RC("psp_secondary", 0.62), _RC("psp_primary", 0.58), _RC("psp_tertiary", 0.5)]
        reason_suffix = "Baseline routing heuristic; cascade after initial attempt."

    sorted_candidates = sorted(fallback, key=lambda c: c.score, reverse=True)
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

    Adds aliases used by the rule engine (e.g. ``amount_cents`` for
    ``amount_minor``, ``merchant_country`` for ``issuer_country``)
    so condition_expression strings work intuitively.

    Compatible with both Pydantic v1 (``.dict()``) and v2 (``.model_dump()``).
    """
    dump = getattr(ctx, "model_dump", None)
    if callable(dump):
        d = dump()
    else:
        # Pydantic v1 fallback; removed in v3+.
        legacy = getattr(ctx, "dict", None)
        if callable(legacy):
            d = legacy()
        else:
            # Last resort: dataclass or plain-object fallback
            d = dict(ctx)  # type: ignore[call-overload]

    # Add aliases for rule engine condition_expression compatibility
    d.setdefault("amount_cents", d.get("amount_minor", 0))
    d.setdefault("merchant_country", d.get("issuer_country"))
    d.setdefault("decline_reason", d.get("previous_decline_reason"))
    d.setdefault("decline_code", d.get("previous_decline_code"))

    return d
