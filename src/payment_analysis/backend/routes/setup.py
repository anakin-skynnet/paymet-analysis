"""
Setup & Run API - Trigger jobs and pipelines from the UI.

Provides endpoints to run Databricks jobs and Lakeflow with configurable
parameters (catalog, schema, warehouse_id). Used by the Setup & Run page.
"""

from __future__ import annotations

import os
from typing import Any, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import AppConfig
from ..dependencies import get_obo_ws
from ..services.databricks_service import DatabricksConfig, DatabricksService
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


def _job_id_env_key(key: str) -> str:
    """Env var name for job ID override: e.g. transaction_stream_simulator -> DATABRICKS_JOB_ID_TRANSACTION_STREAM_SIMULATOR."""
    return "DATABRICKS_JOB_ID_" + key.upper()


def _pipeline_id_env_key(key: str) -> str:
    """Env var name for pipeline ID override: e.g. payment_analysis_etl -> DATABRICKS_PIPELINE_ID_PAYMENT_ANALYSIS_ETL."""
    return "DATABRICKS_PIPELINE_ID_" + key.upper()


# Job/pipeline IDs from bundle deploy (target workspace). Override via env: DATABRICKS_JOB_ID_<NAME>, DATABRICKS_PIPELINE_ID_<NAME>.
# See docs/DEPLOYMENT.md for the list of env vars.
DEFAULT_IDS: _DefaultIds = {
    "warehouse_id": os.getenv("DATABRICKS_WAREHOUSE_ID", "bf12ee0011ea4ced") or "",
    "catalog": os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog") or "",
    "schema": os.getenv("DATABRICKS_SCHEMA", "ahs_demo_payment_analysis_dev") or "",
    "jobs": {
        "transaction_stream_simulator": os.getenv(_job_id_env_key("transaction_stream_simulator"), "782493643247677") or "782493643247677",
        "create_gold_views": os.getenv(_job_id_env_key("create_gold_views"), "775632375108394") or "775632375108394",
        "train_ml_models": os.getenv(_job_id_env_key("train_ml_models"), "231255282351595") or "231255282351595",
        "orchestrator_agent": os.getenv(_job_id_env_key("orchestrator_agent"), "582671124403091") or "582671124403091",
        "smart_routing_agent": os.getenv(_job_id_env_key("smart_routing_agent"), "767448715494660") or "767448715494660",
        "smart_retry_agent": os.getenv(_job_id_env_key("smart_retry_agent"), "109985467901177") or "109985467901177",
        "risk_assessor_agent": os.getenv(_job_id_env_key("risk_assessor_agent"), "564155694169057") or "564155694169057",
        "decline_analyst_agent": os.getenv(_job_id_env_key("decline_analyst_agent"), "102676008371002") or "102676008371002",
        "performance_recommender_agent": os.getenv(_job_id_env_key("performance_recommender_agent"), "560263049146932") or "560263049146932",
        "continuous_stream_processor": os.getenv(_job_id_env_key("continuous_stream_processor"), "1124715161556931") or "1124715161556931",
        "test_agent_framework": os.getenv(_job_id_env_key("test_agent_framework"), "0") or "0",
    },
    "pipelines": {
        "payment_analysis_etl": os.getenv(_pipeline_id_env_key("payment_analysis_etl"), "eb4edb4a-0069-4208-9261-2151f4bf33d9") or "eb4edb4a-0069-4208-9261-2151f4bf33d9",
        "payment_realtime_pipeline": os.getenv(_pipeline_id_env_key("payment_realtime_pipeline"), "0ef506fd-d386-4581-a609-57fb9a23291c") or "0ef506fd-d386-4581-a609-57fb9a23291c",
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
    pipeline_id: str = Field(..., description="Lakeflow pipeline ID")


class RunPipelineOut(BaseModel):
    """Response after triggering a pipeline update."""
    pipeline_id: str = Field(..., description="Pipeline ID")
    update_id: str = Field(..., description="Update ID")
    pipeline_page_url: str = Field(..., description="URL to view the pipeline")
    message: str = Field(..., description="Human-readable status")


class SetupConfigIn(BaseModel):
    """Request to update effective catalog/schema (persisted in app_config table)."""
    catalog: str = Field(..., min_length=1, max_length=255, description="Unity Catalog name")
    schema_name: str = Field(..., min_length=1, max_length=255, description="Schema name", alias="schema")

    model_config = {"populate_by_name": True}


class SetupConfigOut(BaseModel):
    """Effective catalog/schema after update."""
    catalog: str = Field(..., description="Unity Catalog name")
    schema_name: str = Field(..., description="Schema name", serialization_alias="schema")

    model_config = {"populate_by_name": True}


# =============================================================================
# Endpoints
# =============================================================================

def _effective_uc_config(request: Request) -> tuple[str, str]:
    """Return (catalog, schema) from app state (set at startup from app_config table)."""
    catalog, schema = getattr(request.app.state, "uc_config", (None, None))
    if catalog and schema:
        return (catalog, schema)
    return (DEFAULT_IDS["catalog"], DEFAULT_IDS["schema"])


@router.get("/defaults", response_model=SetupDefaultsOut, operation_id="getSetupDefaults")
def get_setup_defaults(request: Request) -> SetupDefaultsOut:
    """Return default resource IDs and parameters for the Setup & Run form (catalog/schema from app_config)."""
    host = _get_workspace_host().rstrip("/")
    catalog, schema = _effective_uc_config(request)
    return SetupDefaultsOut(
        warehouse_id=DEFAULT_IDS["warehouse_id"],
        catalog=catalog,
        schema_name=schema,
        jobs=DEFAULT_IDS["jobs"],
        pipelines=DEFAULT_IDS["pipelines"],
        workspace_host=host,
    )


@router.patch("/config", response_model=SetupConfigOut, operation_id="updateSetupConfig")
async def update_setup_config(request: Request, body: SetupConfigIn) -> SetupConfigOut:
    """Update effective catalog and schema in app_config table and app state."""
    catalog = (body.catalog or "").strip()
    schema = (body.schema_name or "").strip()
    if not catalog or not schema:
        raise HTTPException(
            status_code=400,
            detail="catalog and schema are required and must be non-empty.",
        )
    bootstrap = DatabricksConfig.from_environment()
    if not (bootstrap.host and bootstrap.token and bootstrap.warehouse_id):
        raise HTTPException(
            status_code=503,
            detail="Databricks credentials not configured; cannot update app_config.",
        )
    svc = DatabricksService(config=bootstrap)
    ok = await svc.write_app_config(catalog, schema)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write app_config.")
    request.app.state.uc_config = (catalog, schema)
    return SetupConfigOut(catalog=catalog, schema_name=schema)


@router.post("/run-job", response_model=RunJobOut, operation_id="runSetupJob")
def run_setup_job(
    request: Request,
    body: RunJobIn,
    obo_ws: WorkspaceClient = Depends(get_obo_ws),
) -> RunJobOut:
    """Run a Databricks job with optional notebook/SQL parameters."""
    host = _get_workspace_host().rstrip("/")
    eff_catalog, eff_schema = _effective_uc_config(request)
    catalog = body.catalog or eff_catalog
    schema = body.schema_name or eff_schema
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
    """Start a Lakeflow pipeline update."""
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
