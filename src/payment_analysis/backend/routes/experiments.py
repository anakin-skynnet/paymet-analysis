"""Experiments API: A/B experiment CRUD and assignment for decisioning."""

from __future__ import annotations

from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlmodel import select

from ..db_models import Experiment, ExperimentAssignment, utcnow
from ..dependencies import SessionDep

router = APIRouter(tags=["experiments"])


class ExperimentIn(BaseModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None


class AssignIn(BaseModel):
    subject_key: str = Field(min_length=1)
    variant: str = Field(min_length=1)


@router.post("", response_model=Experiment, operation_id="createExperiment")
def create_experiment(payload: ExperimentIn, session: SessionDep) -> Experiment:
    exp = Experiment(name=payload.name, description=payload.description)
    session.add(exp)
    session.commit()
    session.refresh(exp)
    return exp


@router.get("", response_model=list[Experiment], operation_id="listExperiments")
def list_experiments(
    session: SessionDep,
    limit: int = Query(100, ge=1, le=200, description="Max number of experiments"),
) -> list[Experiment]:
    limit = max(1, min(limit, 200))
    stmt = select(Experiment).order_by(desc(cast(Any, Experiment.created_at))).limit(
        limit
    )
    return list(session.exec(stmt).all())


@router.post("/{experiment_id}/start", response_model=Experiment, operation_id="startExperiment")
def start_experiment(experiment_id: str, session: SessionDep) -> Experiment:
    exp = session.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    exp.status = "running"
    exp.started_at = exp.started_at or utcnow()
    session.add(exp)
    session.commit()
    session.refresh(exp)
    return exp


@router.post("/{experiment_id}/stop", response_model=Experiment, operation_id="stopExperiment")
def stop_experiment(experiment_id: str, session: SessionDep) -> Experiment:
    exp = session.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    exp.status = "stopped"
    exp.ended_at = utcnow()
    session.add(exp)
    session.commit()
    session.refresh(exp)
    return exp


@router.post(
    "/{experiment_id}/assign",
    response_model=ExperimentAssignment,
    operation_id="assignExperiment",
)
def assign(experiment_id: str, payload: AssignIn, session: SessionDep) -> ExperimentAssignment:
    exp = session.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.status not in {"running", "draft"}:
        raise HTTPException(status_code=400, detail="Experiment is not assignable")

    assignment = ExperimentAssignment(
        experiment_id=experiment_id,
        subject_key=payload.subject_key,
        variant=payload.variant,
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment


@router.get(
    "/{experiment_id}/assignments",
    response_model=list[ExperimentAssignment],
    operation_id="listExperimentAssignments",
)
def list_assignments(
    experiment_id: str, session: SessionDep, limit: int = 200
) -> list[ExperimentAssignment]:
    limit = max(1, min(limit, 500))
    stmt = (
        select(ExperimentAssignment)
        .where(ExperimentAssignment.experiment_id == experiment_id)
        .order_by(desc(cast(Any, ExperimentAssignment.created_at)))
        .limit(limit)
    )
    return list(session.exec(stmt).all())

