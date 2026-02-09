"""Incidents API: incident and remediation task CRUD for operations."""

from __future__ import annotations

from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlmodel import select

from ..db_models import Incident, RemediationTask
from ..dependencies import SessionDep

router = APIRouter(tags=["incidents"])


class IncidentIn(BaseModel):
    category: str = Field(min_length=1)
    key: str = Field(min_length=1)
    severity: str = Field(default="medium")
    details: dict[str, Any] = Field(default_factory=dict)


class TaskIn(BaseModel):
    title: str = Field(min_length=1)
    action: Optional[str] = None
    owner: Optional[str] = None


@router.get("", response_model=list[Incident], operation_id="listIncidents")
def list_incidents(
    session: SessionDep,
    limit: int = Query(100, ge=1, le=200, description="Max number of incidents"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    limit = max(1, min(limit, 200))
    stmt = select(Incident).order_by(desc(cast(Any, Incident.created_at))).limit(limit)
    if status:
        stmt = stmt.where(Incident.status == status)
    return list(session.exec(stmt).all())


@router.post("", response_model=Incident, operation_id="createIncident")
def create_incident(payload: IncidentIn, session: SessionDep) -> Incident:
    incident = Incident(
        category=payload.category,
        key=payload.key,
        severity=payload.severity,
        details=payload.details,
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


@router.post(
    "/{incident_id}/resolve", response_model=Incident, operation_id="resolveIncident"
)
def resolve_incident(incident_id: str, session: SessionDep) -> Incident:
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.status = "resolved"
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


@router.post(
    "/{incident_id}/tasks",
    response_model=RemediationTask,
    operation_id="createRemediationTask",
)
def create_task(incident_id: str, payload: TaskIn, session: SessionDep) -> RemediationTask:
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    task = RemediationTask(
        incident_id=incident_id,
        title=payload.title,
        action=payload.action,
        owner=payload.owner,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get(
    "/{incident_id}/tasks",
    response_model=list[RemediationTask],
    operation_id="listRemediationTasks",
)
def list_tasks(
    incident_id: str,
    session: SessionDep,
    limit: int = Query(200, ge=1, le=500, description="Max number of tasks"),
):
    limit = max(1, min(limit, 500))
    stmt = (
        select(RemediationTask)
        .where(RemediationTask.incident_id == incident_id)
        .order_by(desc(cast(Any, RemediationTask.created_at)))
        .limit(limit)
    )
    return list(session.exec(stmt).all())

