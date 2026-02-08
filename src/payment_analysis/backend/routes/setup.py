"""
Setup & Run API - Trigger jobs and pipelines from the UI.

Provides endpoints to run Databricks jobs and Lakeflow with configurable
parameters (catalog, schema, warehouse_id). Used by the Setup & Run page.
"""

from __future__ import annotations

import os
from typing import TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import (
    AppConfig,
    WORKSPACE_URL_PLACEHOLDER,
    app_name,
    ensure_absolute_workspace_url,
    workspace_url_from_apps_host,
)
from ..dependencies import (
    AUTH_REQUIRED_DETAIL,
    _effective_databricks_host,
    _get_obo_token,
    get_workspace_client,
    get_workspace_client_optional,
)
from ..services.databricks_service import DatabricksConfig, DatabricksService
from databricks.sdk import WorkspaceClient

router = APIRouter(prefix="/setup", tags=["setup"])

_app_config = AppConfig()


# =============================================================================
# Default resource IDs (from bundle deployment; see docs/DEPLOYMENT_GUIDE.md)
# =============================================================================

class _DefaultIds(TypedDict):
    warehouse_id: str
    catalog: str
    schema: str
    jobs: dict[str, str]
    pipelines: dict[str, str]


def _get_workspace_host() -> str:
    """Get Databricks workspace base URL (absolute) from centralized config / env. Always returns https://... so Open links go to the workspace, not relative to the app. Returns empty when unset (placeholder)."""
    raw = (_app_config.databricks.workspace_url or "").strip().rstrip("/")
    if not raw or raw == WORKSPACE_URL_PLACEHOLDER.rstrip("/"):
        return ""
    return ensure_absolute_workspace_url(raw)


def _job_id_env_key(key: str) -> str:
    """Env var name for job ID override: e.g. transaction_stream_simulator -> DATABRICKS_JOB_ID_TRANSACTION_STREAM_SIMULATOR."""
    return "DATABRICKS_JOB_ID_" + key.upper()


def _pipeline_id_env_key(key: str) -> str:
    """Env var name for pipeline ID override: e.g. payment_analysis_etl -> DATABRICKS_PIPELINE_ID_PAYMENT_ANALYSIS_ETL."""
    return "DATABRICKS_PIPELINE_ID_" + key.upper()


# Job/pipeline IDs from bundle deploy (target workspace). Override via env: DATABRICKS_JOB_ID_<NAME>, DATABRICKS_PIPELINE_ID_<NAME>.
# See docs/DEPLOYMENT_GUIDE.md for the list of env vars.
DEFAULT_IDS: _DefaultIds = {
    "warehouse_id": os.getenv("DATABRICKS_WAREHOUSE_ID", "148ccb90800933a1") or "",
    "catalog": os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog") or "",
    "schema": os.getenv("DATABRICKS_SCHEMA", "payment_analysis") or "",
    "jobs": {
        "transaction_stream_simulator": os.getenv(_job_id_env_key("transaction_stream_simulator"), "782493643247677") or "782493643247677",
        "create_gold_views": os.getenv(_job_id_env_key("create_gold_views"), "775632375108394") or "775632375108394",
        "lakehouse_bootstrap": os.getenv(_job_id_env_key("lakehouse_bootstrap"), "0") or "0",
        "vector_search_index": os.getenv(_job_id_env_key("vector_search_index"), "0") or "0",
        "train_ml_models": os.getenv(_job_id_env_key("train_ml_models"), "231255282351595") or "231255282351595",
        "genie_sync": os.getenv(_job_id_env_key("genie_sync"), "0") or "0",
        "orchestrator_agent": os.getenv(_job_id_env_key("orchestrator_agent"), "582671124403091") or "582671124403091",
        "smart_routing_agent": os.getenv(_job_id_env_key("smart_routing_agent"), "767448715494660") or "767448715494660",
        "smart_retry_agent": os.getenv(_job_id_env_key("smart_retry_agent"), "109985467901177") or "109985467901177",
        "risk_assessor_agent": os.getenv(_job_id_env_key("risk_assessor_agent"), "564155694169057") or "564155694169057",
        "decline_analyst_agent": os.getenv(_job_id_env_key("decline_analyst_agent"), "102676008371002") or "102676008371002",
        "performance_recommender_agent": os.getenv(_job_id_env_key("performance_recommender_agent"), "560263049146932") or "560263049146932",
        "continuous_stream_processor": os.getenv(_job_id_env_key("continuous_stream_processor"), "1124715161556931") or "1124715161556931",
        "test_agent_framework": os.getenv(_job_id_env_key("test_agent_framework"), "0") or "0",
        "publish_dashboards": os.getenv(_job_id_env_key("publish_dashboards"), "0") or "0",
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
# Resolve job/pipeline IDs by name when env defaults are "0" or missing
# =============================================================================

# Map logical key -> substring that appears in the deployed job/pipeline name (bundle naming).
_JOB_NAME_SUBSTRINGS: dict[str, str] = {
    "lakehouse_bootstrap": "Lakehouse Bootstrap",
    "vector_search_index": "Vector Search Index",
    "create_gold_views": "Gold Views",
    "transaction_stream_simulator": "Transaction Stream Simulator",
    "train_ml_models": "Train Payment Approval ML Models",
    "genie_sync": "Genie Space Sync",
    "orchestrator_agent": "Orchestrator",
    "smart_routing_agent": "Smart Routing Agent",
    "smart_retry_agent": "Smart Retry Agent",
    "decline_analyst_agent": "Decline Analyst Agent",
    "risk_assessor_agent": "Risk Assessor Agent",
    "performance_recommender_agent": "Performance Recommender Agent",
    "continuous_stream_processor": "Continuous Stream Processor",
    "test_agent_framework": "Test AI Agent Framework",
    "publish_dashboards": "Publish Dashboards",
}
_PIPELINE_NAME_SUBSTRINGS: dict[str, str] = {
    "payment_analysis_etl": "Payment Analysis ETL",
    "payment_realtime_pipeline": "Real-Time Stream",
}


def _resolve_job_and_pipeline_ids(ws: WorkspaceClient) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve job and pipeline IDs by listing workspace and matching names. Returns (jobs, pipelines) with only resolved IDs."""
    resolved_jobs: dict[str, str] = {}
    resolved_pipelines: dict[str, str] = {}
    try:
        for job in ws.jobs.list():
            name = (job.settings.name or "") if job.settings else ""
            for key, substr in _JOB_NAME_SUBSTRINGS.items():
                if substr in name and job.job_id:
                    resolved_jobs[key] = str(job.job_id)
                    break
    except Exception:
        pass
    try:
        for pipeline in ws.pipelines.list_pipelines():
            name = (pipeline.name or "") if pipeline else ""
            for key, substr in _PIPELINE_NAME_SUBSTRINGS.items():
                if substr in name and pipeline.pipeline_id:
                    resolved_pipelines[key] = pipeline.pipeline_id
                    break
    except Exception:
        pass
    return resolved_jobs, resolved_pipelines


def _merge_resolved_ids(
    jobs: dict[str, str],
    pipelines: dict[str, str],
    resolved_jobs: dict[str, str],
    resolved_pipelines: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Use resolved ID when current value is missing or '0'."""
    out_jobs = dict(jobs)
    for key, rid in resolved_jobs.items():
        if key in out_jobs and (not out_jobs[key] or out_jobs[key] == "0"):
            out_jobs[key] = rid
    out_pipelines = dict(pipelines)
    for key, rid in resolved_pipelines.items():
        if key in out_pipelines and (not out_pipelines[key] or out_pipelines[key] == "0"):
            out_pipelines[key] = rid
    return out_jobs, out_pipelines


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
def get_setup_defaults(
    request: Request,
    ws: WorkspaceClient | None = Depends(get_workspace_client_optional),
) -> SetupDefaultsOut:
    """Return default resource IDs and parameters for the Setup & Run form. When credentials are present, resolves job/pipeline IDs from the workspace by name so steps can be run after deploy without setting env vars."""
    host = _get_workspace_host().rstrip("/")
    if not host:
        host = workspace_url_from_apps_host(request.headers.get("host") or "", app_name).rstrip("/")
    catalog, schema = _effective_uc_config(request)
    jobs = dict(DEFAULT_IDS["jobs"])
    pipelines = dict(DEFAULT_IDS["pipelines"])
    if ws is not None:
        resolved_jobs, resolved_pipelines = _resolve_job_and_pipeline_ids(ws)
        jobs, pipelines = _merge_resolved_ids(jobs, pipelines, resolved_jobs, resolved_pipelines)
    return SetupDefaultsOut(
        warehouse_id=DEFAULT_IDS["warehouse_id"],
        catalog=catalog,
        schema_name=schema,
        jobs=jobs,
        pipelines=pipelines,
        workspace_host=host,
    )


@router.patch("/config", response_model=SetupConfigOut, operation_id="updateSetupConfig")
async def update_setup_config(request: Request, body: SetupConfigIn) -> SetupConfigOut:
    """Update effective catalog and schema in app_config table and app state. Uses your token when opened from Compute → Apps (OBO) or DATABRICKS_TOKEN when set."""
    catalog = (body.catalog or "").strip()
    schema = (body.schema_name or "").strip()
    if not catalog or not schema:
        raise HTTPException(
            status_code=400,
            detail="catalog and schema are required and must be non-empty.",
        )
    bootstrap = DatabricksConfig.from_environment()
    obo_token = _get_obo_token(request)
    if not obo_token and not bootstrap.token:
        raise HTTPException(status_code=401, detail=AUTH_REQUIRED_DETAIL)
    effective_host = _effective_databricks_host(request, bootstrap.host)
    missing = []
    if not effective_host:
        missing.append("DATABRICKS_HOST (or open the app from Compute → Apps so the workspace URL can be derived)")
    if not bootstrap.warehouse_id:
        missing.append("DATABRICKS_WAREHOUSE_ID")
    if missing:
        raise HTTPException(status_code=503, detail=f"Set in the app environment: {', '.join(missing)}.")
    config = DatabricksConfig(
        host=effective_host,
        token=obo_token or bootstrap.token,
        warehouse_id=bootstrap.warehouse_id,
        catalog=bootstrap.catalog,
        schema=bootstrap.schema,
    )
    svc = DatabricksService(config=config)
    try:
        await svc.write_app_config(catalog, schema)
    except RuntimeError as e:
        msg = str(e).strip()
        detail = f"Failed to write app_config: {msg}" if msg else "Failed to write app_config."
        raise HTTPException(status_code=500, detail=detail)
    request.app.state.uc_config = (catalog, schema)
    return SetupConfigOut(catalog=catalog, schema_name=schema)


def _run_job_error_status(e: Exception) -> int:
    """Map job run exception to HTTP status (403 forbidden, 404 not found, else 400)."""
    msg = str(e).lower()
    if "not found" in msg or "404" in msg or "no job" in msg:
        return 404
    if "forbidden" in msg or "403" in msg or "permission" in msg or "scope" in msg:
        return 403
    return 400


@router.post("/run-job", response_model=RunJobOut, operation_id="runSetupJob")
def run_setup_job(
    request: Request,
    body: RunJobIn,
    ws: WorkspaceClient = Depends(get_workspace_client),
) -> RunJobOut:
    """Run a Databricks job with optional notebook/SQL parameters."""
    job_id_str = (body.job_id or "").strip()
    if not job_id_str or job_id_str == "0":
        raise HTTPException(
            status_code=400,
            detail="Job ID is not set. Use Refresh job IDs on this page, or set DATABRICKS_JOB_ID_<name> in the app environment.",
        )
    try:
        job_id_int = int(job_id_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job ID: {body.job_id!r}. Must be a numeric Databricks job ID.",
        ) from None
    if job_id_int <= 0:
        raise HTTPException(
            status_code=400,
            detail="Job ID is not set. Use Refresh job IDs on this page, or set DATABRICKS_JOB_ID_<name> in the app environment.",
        )

    host = _get_workspace_host().rstrip("/")
    if not host:
        host = workspace_url_from_apps_host(request.headers.get("host") or "", app_name).rstrip("/")
    host = ensure_absolute_workspace_url(host) if host else ""
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
        run = ws.jobs.run_now(
            job_id=job_id_int,
            notebook_params=notebook_params,
            python_params=None,
            jar_params=None,
            spark_submit_params=None,
        )
        run_id = run.run_id
    except Exception as e:
        status = _run_job_error_status(e)
        raise HTTPException(status_code=status, detail=str(e)) from e

    run_page_url = f"{host}/#job/{body.job_id}/run/{run_id}" if host else ""
    return RunJobOut(
        job_id=body.job_id,
        run_id=run_id,
        run_page_url=run_page_url,
        message="Job run started successfully. Open the run page to monitor progress.",
    )


@router.post("/run-pipeline", response_model=RunPipelineOut, operation_id="runSetupPipeline")
def run_setup_pipeline(
    request: Request,
    body: RunPipelineIn,
    ws: WorkspaceClient = Depends(get_workspace_client),
) -> RunPipelineOut:
    """Start a Lakeflow pipeline update."""
    host = _get_workspace_host().rstrip("/")
    if not host:
        host = workspace_url_from_apps_host(request.headers.get("host") or "", app_name).rstrip("/")
    host = ensure_absolute_workspace_url(host) if host else ""
    try:
        update = ws.pipelines.start_update(pipeline_id=body.pipeline_id)
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
