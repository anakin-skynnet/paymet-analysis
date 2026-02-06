"""API for approval rules stored in the Lakehouse (Unity Catalog). Used by ML and Agents to accelerate approval rates."""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.databricks_service import get_databricks_service

router = APIRouter(tags=["rules"])


class ApprovalRuleOut(BaseModel):
    """Approval rule as stored in the Lakehouse."""
    id: str
    name: str
    rule_type: str
    condition_expression: Optional[str] = None
    action_summary: str
    priority: int
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ApprovalRuleIn(BaseModel):
    """Payload to create an approval rule."""
    name: str = Field(min_length=1, max_length=500)
    rule_type: str = Field(..., pattern="^(authentication|retry|routing)$")
    action_summary: str = Field(min_length=1, max_length=2000)
    condition_expression: Optional[str] = Field(None, max_length=5000)
    priority: int = Field(default=100, ge=0, le=10000)
    is_active: bool = True


class ApprovalRuleUpdate(BaseModel):
    """Payload to update an approval rule (partial)."""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    rule_type: Optional[str] = Field(None, pattern="^(authentication|retry|routing)$")
    action_summary: Optional[str] = Field(None, min_length=1, max_length=2000)
    condition_expression: Optional[str] = Field(None, max_length=5000)
    priority: Optional[int] = Field(None, ge=0, le=10000)
    is_active: Optional[bool] = None


def _rule_row_to_out(row: dict) -> ApprovalRuleOut:
    return ApprovalRuleOut(
        id=str(row["id"]),
        name=str(row["name"]),
        rule_type=str(row["rule_type"]),
        condition_expression=str(row["condition_expression"]) if row.get("condition_expression") else None,
        action_summary=str(row["action_summary"]),
        priority=int(row.get("priority", 100)),
        is_active=bool(row.get("is_active", True)),
        created_at=str(row["created_at"]) if row.get("created_at") else None,
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )


@router.get("", response_model=list[ApprovalRuleOut], operation_id="listApprovalRules")
async def list_approval_rules(
    rule_type: Optional[str] = None,
    active_only: bool = False,
    limit: int = 200,
) -> list[ApprovalRuleOut]:
    """List approval rules from the Lakehouse. ML and AI agents read these to accelerate approval rates."""
    service = get_databricks_service()
    rows = await service.get_approval_rules(rule_type=rule_type, active_only=active_only, limit=limit)
    return [_rule_row_to_out(r) for r in rows]


@router.post("", response_model=ApprovalRuleOut, operation_id="createApprovalRule")
async def create_approval_rule(payload: ApprovalRuleIn) -> ApprovalRuleOut:
    """Create an approval rule in the Lakehouse. It will be used by decisioning and AI agents."""
    service = get_databricks_service()
    if not service.is_available:
        raise HTTPException(status_code=503, detail="Databricks Lakehouse unavailable; cannot write rules.")
    rule_id = uuid4().hex
    ok = await service.create_approval_rule(
        id=rule_id,
        name=payload.name,
        rule_type=payload.rule_type,
        action_summary=payload.action_summary,
        condition_expression=payload.condition_expression,
        priority=payload.priority,
        is_active=payload.is_active,
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to write rule to Lakehouse.")
    rows = await service.get_approval_rules(limit=1)
    for r in rows:
        if str(r.get("id")) == rule_id:
            return _rule_row_to_out(r)
    return _rule_row_to_out({
        "id": rule_id,
        "name": payload.name,
        "rule_type": payload.rule_type,
        "condition_expression": payload.condition_expression,
        "action_summary": payload.action_summary,
        "priority": payload.priority,
        "is_active": payload.is_active,
        "created_at": None,
        "updated_at": None,
    })


@router.patch("/{rule_id}", response_model=ApprovalRuleOut, operation_id="updateApprovalRule")
async def update_approval_rule(rule_id: str, payload: ApprovalRuleUpdate) -> ApprovalRuleOut:
    """Update an approval rule in the Lakehouse."""
    service = get_databricks_service()
    if not service.is_available:
        raise HTTPException(status_code=503, detail="Databricks Lakehouse unavailable; cannot update rules.")
    ok = await service.update_approval_rule(
        rule_id,
        name=payload.name,
        rule_type=payload.rule_type,
        condition_expression=payload.condition_expression,
        action_summary=payload.action_summary,
        priority=payload.priority,
        is_active=payload.is_active,
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to update rule in Lakehouse.")
    rows = await service.get_approval_rules(limit=500)
    for r in rows:
        if str(r.get("id")) == rule_id:
            return _rule_row_to_out(r)
    raise HTTPException(status_code=404, detail="Rule not found after update.")


@router.delete("/{rule_id}", status_code=204, operation_id="deleteApprovalRule")
async def delete_approval_rule(rule_id: str) -> None:
    """Delete an approval rule from the Lakehouse."""
    service = get_databricks_service()
    if not service.is_available:
        raise HTTPException(status_code=503, detail="Databricks Lakehouse unavailable; cannot delete rules.")
    ok = await service.delete_approval_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to delete rule from Lakehouse.")
