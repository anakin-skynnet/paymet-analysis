"""Incidents API: incident and remediation task CRUD for operations.

Incidents are stored in Lakebase (Postgres) as the primary OLTP store.
A Lakehouse mirror (incidents_lakehouse) is maintained for UC agent access
so agents can incorporate operational feedback into their analysis.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional, cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlmodel import select

from ..db_models import Incident, RemediationTask
from ..dependencies import SessionDep

logger = logging.getLogger(__name__)
router = APIRouter(tags=["incidents"])

_VALID_INCIDENT_STATUSES = {"open", "mitigating", "resolved"}


async def _sync_incident_to_lakehouse(incident: Incident) -> None:
    """Sync an incident to the Lakehouse mirror table (incidents_lakehouse).

    Runs as a background task so it does not block the API response.
    The Lakehouse table is used by UC agent tools (get_recent_incidents)
    to give agents access to operational feedback.

    Uses MERGE for idempotent upsert: creates on first sync, updates on
    subsequent status changes (e.g. resolve).

    SQL injection mitigation: all user-supplied values are passed through
    Databricks SQL Statement API parameters (named :param syntax) instead
    of string interpolation.
    """
    try:
        from databricks.sdk.service.sql import StatementParameterListItem, StatementState

        from ..services.databricks_service import DatabricksService

        svc = DatabricksService.create()
        if not svc.is_available:
            logger.warning("Databricks unavailable — skipping Lakehouse sync for incident %s", incident.id)
            return

        full_schema = svc.config.full_schema_name
        details_str = json.dumps(incident.details) if incident.details else "{}"

        # Parameterized MERGE — no string interpolation for user-supplied values.
        # Schema name is validated by DatabricksConfig.__post_init__ (alphanumeric + underscore only).
        query = f"""
            MERGE INTO {full_schema}.incidents_lakehouse AS target
            USING (SELECT :incident_id AS id) AS source
            ON target.id = source.id
            WHEN MATCHED THEN UPDATE SET
                status = :status,
                severity = :severity,
                details = :details
            WHEN NOT MATCHED THEN INSERT
                (id, created_at, category, incident_key, severity, status, details)
            VALUES (
                :incident_id,
                CURRENT_TIMESTAMP(),
                :category,
                :incident_key,
                :severity,
                :status,
                :details
            )
        """
        params = [
            StatementParameterListItem(name="incident_id", value=incident.id, type="STRING"),
            StatementParameterListItem(name="status", value=incident.status, type="STRING"),
            StatementParameterListItem(name="severity", value=incident.severity, type="STRING"),
            StatementParameterListItem(name="details", value=details_str, type="STRING"),
            StatementParameterListItem(name="category", value=incident.category, type="STRING"),
            StatementParameterListItem(name="incident_key", value=incident.key, type="STRING"),
        ]

        client = svc.client
        if client is None:
            logger.warning("Databricks client not initialized — skipping Lakehouse sync for incident %s", incident.id)
            return

        warehouse_id = svc._get_warehouse_id()
        if not warehouse_id:
            logger.warning("No SQL Warehouse available — skipping Lakehouse sync for incident %s", incident.id)
            return

        result = client.statement_execution.execute_statement(
            statement=query,
            warehouse_id=warehouse_id,
            parameters=params,
        )
        if result.status and result.status.state == StatementState.SUCCEEDED:
            logger.debug("Synced incident %s to Lakehouse mirror", incident.id)
        else:
            msg = result.status.error.message if result.status and result.status.error else "unknown"
            logger.warning("Lakehouse sync for incident %s returned non-success: %s", incident.id, msg)
    except Exception:
        # Non-critical: Lakehouse sync failure must not affect API response
        logger.warning("Failed to sync incident %s to Lakehouse", incident.id, exc_info=True)


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
        if status not in _VALID_INCIDENT_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(_VALID_INCIDENT_STATUSES))}",
            )
        stmt = stmt.where(Incident.status == status)
    return list(session.exec(stmt).all())


@router.post("", response_model=Incident, operation_id="createIncident")
def create_incident(
    payload: IncidentIn, session: SessionDep, background_tasks: BackgroundTasks
) -> Incident:
    incident = Incident(
        category=payload.category,
        key=payload.key,
        severity=payload.severity,
        details=payload.details,
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    # Sync to Lakehouse mirror for UC agent access
    background_tasks.add_task(_sync_incident_to_lakehouse, incident)
    return incident


@router.post(
    "/{incident_id}/resolve", response_model=Incident, operation_id="resolveIncident"
)
def resolve_incident(
    incident_id: str, session: SessionDep, background_tasks: BackgroundTasks
) -> Incident:
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.status = "resolved"
    session.add(incident)
    session.commit()
    session.refresh(incident)
    # Sync status update to Lakehouse mirror
    background_tasks.add_task(_sync_incident_to_lakehouse, incident)
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

