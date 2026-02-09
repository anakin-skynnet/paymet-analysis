"""Pydantic schemas and enums for decisioning: context, auth/retry/routing decisions, KPIs."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AuthPath(str, Enum):
    none = "none"
    three_ds_frictionless = "3ds_frictionless"
    three_ds_challenge = "3ds_challenge"
    passkey = "passkey"


class DecisionContext(BaseModel):
    merchant_id: str = Field(min_length=1)
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

    network: Optional[str] = None
    card_bin: Optional[str] = None
    issuer_country: Optional[str] = None
    entry_mode: Optional[str] = None

    is_recurring: bool = False
    attempt_number: int = Field(default=0, ge=0)

    # optional signals
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    device_trust_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    supports_passkey: bool = False

    # issuer/psp decline from previous attempt(s)
    previous_decline_code: Optional[str] = None
    previous_decline_reason: Optional[str] = None

    # A/B test: if set, lookup assignment for subject_key (default merchant_id) and branch by variant
    experiment_id: Optional[str] = None
    subject_key: Optional[str] = None  # default: merchant_id

    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthDecisionOut(BaseModel):
    audit_id: str
    path: AuthPath
    risk_tier: RiskTier
    reason: str
    experiment_id: Optional[str] = None
    variant: Optional[str] = None


class RetryDecisionOut(BaseModel):
    audit_id: str
    should_retry: bool
    retry_after_seconds: Optional[int] = None
    max_attempts: int = 3
    reason: str
    experiment_id: Optional[str] = None
    variant: Optional[str] = None


class RoutingDecisionOut(BaseModel):
    audit_id: str
    primary_route: str
    candidates: list[str]
    should_cascade: bool
    reason: str
    experiment_id: Optional[str] = None
    variant: Optional[str] = None


class KPIOut(BaseModel):
    total: int
    approved: int
    approval_rate: float

