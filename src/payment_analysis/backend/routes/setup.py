"""
Setup & Run API - Trigger jobs and pipelines from the UI.

Provides endpoints to run Databricks jobs and Lakeflow Declarative Pipelines with configurable
parameters (catalog, schema, warehouse_id). Used by the Setup & Run page.
"""

from __future__ import annotations

import os
from typing import Any, TypedDict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import AppConfig
from ..dependencies import get_obo_ws
from databricks.sdk import WorkspaceClient

router = APIRouter(prefix="/setup", tags=["setup"])

_app_config = AppConfig()


# =============================================================================
# Default resource IDs (from bundle deployment / docs/DEMO_SETUP)
# =============================================================================

class _DefaultIds(TypedDict):
    warehouse_id: str
    catalog: str
    schema: str
    jobs: dict[str, str]
    pipelines: dict[str, str]


def _get_workspace_host() -> str:
    """Get Databricks workspace host from centralized config / env."""
    return _app_config.databricks.workspace_url


DEFAULT_IDS: _DefaultIds = {
    "warehouse_id": os.getenv("DATABRICKS_WAREHOUSE_ID", "bf12ee0011ea4ced") or "",
    "catalog": os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog") or "",
    "schema": os.getenv("DATABRICKS_SCHEMA", "ahs_demo_payment_analysis_dev") or "",
    "jobs": {
        "transaction_stream_simulator": "782493643247677",
        "create_gold_views": "775632375108394",
        "train_ml_models": "231255282351595",
        "orchestrator_agent": "582671124403091",
        "smart_routing_agent": "767448715494660",
        "smart_retry_agent": "109985467901177",
        "risk_assessor_agent": "564155694169057",
        "decline_analyst_agent": "102676008371002",
        "performance_recommender_agent": "560263049146932",
        "continuous_stream_processor": "1124715161556931",
    },
    "pipelines": {
        "payment_analysis_etl": "eb4edb4a-0069-4208-9261-2151f4bf33d9",
        "payment_realtime_pipeline": "0ef506fd-d386-4581-a609-57fb9a23291c",
    },
}


# =============================================================================
# Request/Response models
# =============================================================================

class SetupDefaultsOut(BaseModel):
    """Default resource IDs and parameters for setup form."""
    warehouse_id: str = Field(..., description="SQL Warehouse ID")
    catalog: str = Field(..., description="Unity Catalog name")
    schema_name: str = Field(..., description="Schema name", serialization_alias="schema")
    jobs: dict[str, str] = Field(..., description="Job ID by logical name")
    pipelines: dict[str, str] = Field(..., description="Pipeline ID by logical name")
    workspace_host: str = Field(..., description="Databricks workspace URL")

    model_config = {"populate_by_name": True}


class RunJobIn(BaseModel):
    """Request to run a job."""
    job_id: str = Field(..., description="Databricks job ID")
    catalog: str | None = Field(None, description="Override catalog for notebook params")
    schema_name: str | None = Field(None, description="Override schema for notebook params", alias="schema")
    warehouse_id: str | None = Field(None, description="Override warehouse ID for SQL tasks")
    events_per_second: str | None = Field(None, description="For simulator: events per second")
    duration_minutes: str | None = Field(None, description="For simulator: duration in minutes")

    model_config = {"populate_by_name": True}


class RunJobOut(BaseModel):
    """Response after triggering a job run."""
    job_id: str = Field(..., description="Job ID")
    run_id: int = Field(..., description="Run ID")
    run_page_url: str = Field(..., description="URL to view the run")
    message: str = Field(..., description="Human-readable status")


class RunPipelineIn(BaseModel):
    """Request to run a pipeline."""
    pipeline_id: str = Field(..., description="Lakeflow Declarative Pipeline ID")


class RunPipelineOut(BaseModel):
    """Response after triggering a pipeline update."""
    pipeline_id: str = Field(..., description="Pipeline ID")
    update_id: str = Field(..., description="Update ID")
    pipeline_page_url: str = Field(..., description="URL to view the pipeline")
    message: str = Field(..., description="Human-readable status")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/defaults", response_model=SetupDefaultsOut, operation_id="getSetupDefaults")
def get_setup_defaults() -> SetupDefaultsOut:
    """Return default resource IDs and parameters for the Setup & Run form."""
    host = _get_workspace_host().rstrip("/")
    return SetupDefaultsOut(
        warehouse_id=DEFAULT_IDS["warehouse_id"],
        catalog=DEFAULT_IDS["catalog"],
        schema_name=DEFAULT_IDS["schema"],
        jobs=DEFAULT_IDS["jobs"],
        pipelines=DEFAULT_IDS["pipelines"],
        workspace_host=host,
    )


@router.post("/run-job", response_model=RunJobOut, operation_id="runSetupJob")
def run_setup_job(
    body: RunJobIn,
    obo_ws: WorkspaceClient = Depends(get_obo_ws),
) -> RunJobOut:
    """Run a Databricks job with optional notebook/SQL parameters."""
    host = _get_workspace_host().rstrip("/")
    catalog = body.catalog or DEFAULT_IDS["catalog"]
    schema = body.schema_name or DEFAULT_IDS["schema"]
    warehouse_id = body.warehouse_id or DEFAULT_IDS["warehouse_id"]

    notebook_params: dict[str, str] = {
        "catalog": catalog,
        "schema": schema,
    }
    if body.events_per_second is not None:
        notebook_params["events_per_second"] = body.events_per_second
    if body.duration_minutes is not None:
        notebook_params["duration_minutes"] = body.duration_minutes

    try:
        run = obo_ws.jobs.run_now(
            job_id=int(body.job_id),
            notebook_params=notebook_params,
            python_params=None,
            jar_params=None,
            spark_submit_params=None,
        )
        run_id = run.run_id
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    run_page_url = f"{host}/#job/{body.job_id}/run/{run_id}"
    return RunJobOut(
        job_id=body.job_id,
        run_id=run_id,
        run_page_url=run_page_url,
        message="Job run started successfully. Open the run page to monitor progress.",
    )


@router.post("/run-pipeline", response_model=RunPipelineOut, operation_id="runSetupPipeline")
def run_setup_pipeline(
    body: RunPipelineIn,
    obo_ws: WorkspaceClient = Depends(get_obo_ws),
) -> RunPipelineOut:
    """Start a Lakeflow Declarative Pipeline update."""
    host = _get_workspace_host().rstrip("/")
    try:
        update = obo_ws.pipelines.start_update(pipeline_id=body.pipeline_id)
        update_id = update.update_id or "unknown"
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    pipeline_page_url = f"{host}/pipelines/{body.pipeline_id}"
    return RunPipelineOut(
        pipeline_id=body.pipeline_id,
        update_id=update_id,
        pipeline_page_url=pipeline_page_url,
        message="Pipeline update started. Open the pipeline page to monitor progress.",
    )
