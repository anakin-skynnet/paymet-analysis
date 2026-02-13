"""
Setup & Run API – defaults, config, and optional run endpoints (Databricks App).

- GET /setup/defaults: job/pipeline IDs (resolved when user token is present) and workspace URL for Execute buttons.
- PATCH /setup/config: save catalog/schema to app_config table.
- POST /setup/run-job, POST /setup/run-pipeline: trigger runs using user token (x-forwarded-access-token) or DATABRICKS_TOKEN.
Workspace URL is derived from request when app is opened from Compute → Apps.
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
    get_default_schema,
    workspace_id_from_workspace_url,
    workspace_url_from_apps_host,
)
from ..dependencies import (
    AUTH_REQUIRED_DETAIL,
    _effective_databricks_host,
    _get_obo_token,
    _request_host_for_derivation,
    get_workspace_client,
    get_workspace_client_optional,
)
from ..lakebase_config import write_app_config as write_lakebase_app_config
from ..services.databricks_service import DatabricksConfig, DatabricksService
from databricks.sdk import WorkspaceClient

router = APIRouter(prefix="/setup", tags=["setup"])

_app_config = AppConfig()


# =============================================================================
# Default resource IDs (from bundle deployment; see docs/DEPLOYMENT.md)
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
# See docs/DEPLOYMENT.md for the list of env vars.
DEFAULT_IDS: _DefaultIds = {
    "warehouse_id": os.getenv("DATABRICKS_WAREHOUSE_ID", "") or "",
    "catalog": os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog") or "",
    "schema": get_default_schema(),
    "jobs": {
        "transaction_stream_simulator": os.getenv(_job_id_env_key("transaction_stream_simulator"), "0") or "0",
        "create_gold_views": os.getenv(_job_id_env_key("create_gold_views"), "0") or "0",
        "ensure_catalog_schema": os.getenv(_job_id_env_key("ensure_catalog_schema"), "0") or "0",
        "create_lakebase_autoscaling": os.getenv(_job_id_env_key("create_lakebase_autoscaling"), "0") or "0",
        "lakebase_data_init": os.getenv(_job_id_env_key("lakebase_data_init"), "0") or "0",
        "lakehouse_bootstrap": os.getenv(_job_id_env_key("lakehouse_bootstrap"), "0") or "0",
        "vector_search_index": os.getenv(_job_id_env_key("vector_search_index"), "0") or "0",
        "train_ml_models": os.getenv(_job_id_env_key("train_ml_models"), "0") or "0",
        "genie_sync": os.getenv(_job_id_env_key("genie_sync"), "0") or "0",
        "run_agent_framework": os.getenv(_job_id_env_key("run_agent_framework"), "0") or "0",
        "orchestrator_agent": os.getenv(_job_id_env_key("orchestrator_agent"), "0") or "0",
        "test_agent_framework": os.getenv(_job_id_env_key("test_agent_framework"), "0") or "0",
        "continuous_stream_processor": os.getenv(_job_id_env_key("continuous_stream_processor"), "0") or "0",
        "prepare_dashboards": os.getenv(_job_id_env_key("prepare_dashboards"), "0") or "0",
        "publish_dashboards": os.getenv(_job_id_env_key("publish_dashboards"), "0") or "0",
    },
    "pipelines": {
        "payment_analysis_etl": os.getenv(_pipeline_id_env_key("payment_analysis_etl"), "0") or "0",
        "payment_realtime_pipeline": os.getenv(_pipeline_id_env_key("payment_realtime_pipeline"), "0") or "0",
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
    workspace_id: str = Field("", description="Workspace ID (for Jobs URL query param o=). From DATABRICKS_WORKSPACE_ID or derived from host.")
    token_received: bool = Field(False, description="True when OBO token was present (X-Forwarded-Access-Token or Authorization Bearer when on Apps host).")
    workspace_url_derived: bool = Field(False, description="True when workspace URL was set (env or derived from request host); used to show why Execute is disabled.")
    lakebase_autoscaling: bool = Field(False, description="True when app is connected to Lakebase Autoscaling (LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID set).")
    lakebase_connection_mode: str = Field("", description="'autoscaling' or 'direct' when Lakebase is configured, '' otherwise.")

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


class SetupSettingsOut(BaseModel):
    """App settings (key-value) from Lakebase app_settings, read at startup. Used for job defaults and config."""
    settings: dict[str, str] = Field(default_factory=dict, description="Key-value pairs (e.g. warehouse_id, default_events_per_second)")


# =============================================================================
# Resolve job/pipeline IDs by name when env defaults are "0" or missing
# =============================================================================
# Jobs use numeric prefix in name for logical execution order (1 → 2 → 3 → 4 → 5 → 6 → 7).
# Each step has one job; multiple logical keys map to the same job_id.
# Substring must appear in the deployed job name. Bundle: ml_jobs.yml (1,3,4,5), streaming_simulator.yml (2), agents.yml (6), genie_spaces.yml (7).
_STEP_JOB_SUBSTRINGS: dict[str, list[str]] = {
    "1. Create Data Repositories": ["ensure_catalog_schema", "create_lakebase_autoscaling", "lakebase_data_init", "lakehouse_bootstrap", "vector_search_index"],
    "2. Simulate Transaction Events": ["transaction_stream_simulator"],
    "3. Initialize Ingestion": ["create_gold_views", "continuous_stream_processor"],
    "4. Deploy Dashboards": ["prepare_dashboards", "publish_dashboards"],
    "5. Train Models & Publish to Model Serving": ["train_ml_models"],
    "6. Deploy Agents": [
        "run_agent_framework",
        "orchestrator_agent",
        "test_agent_framework",
    ],
    "7. Genie Space Sync": ["genie_sync"],
}
_PIPELINE_NAME_SUBSTRINGS: dict[str, str] = {
    "payment_analysis_etl": "Payment Analysis ETL",
    "payment_realtime_pipeline": "Real-Time Stream",
}


def _resolve_job_and_pipeline_ids(ws: WorkspaceClient) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve job and pipeline IDs by listing workspace and matching step names. Returns (jobs, pipelines) with only resolved IDs. One job can satisfy multiple keys (same step)."""
    resolved_jobs: dict[str, str] = {}
    resolved_pipelines: dict[str, str] = {}
    try:
        for job in ws.jobs.list():
            name = (job.settings.name or "") if job.settings else ""
            if not job.job_id:
                continue
            job_id_str = str(job.job_id)
            for substr, keys in _STEP_JOB_SUBSTRINGS.items():
                if substr in name:
                    for key in keys:
                        resolved_jobs[key] = job_id_str
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
    resolved_jobs: dict[str, str],
    resolved_pipelines: dict[str, str],
    all_job_keys: dict[str, str],
    all_pipeline_keys: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Return only IDs that were resolved from the workspace (existing resources). Unresolved keys get '0' so Execute is disabled and never opens a non-existent resource."""
    out_jobs = {k: resolved_jobs.get(k) or "0" for k in all_job_keys}
    out_pipelines = {k: resolved_pipelines.get(k) or "0" for k in all_pipeline_keys}
    return out_jobs, out_pipelines


def resolve_orchestrator_job_id(ws: WorkspaceClient) -> str:
    """Return the Job 6 (Deploy Agents) job ID from the workspace, or '0' if not found. Used by the orchestrator chat so it works without DATABRICKS_JOB_ID_ORCHESTRATOR_AGENT set."""
    resolved_jobs, _ = _resolve_job_and_pipeline_ids(ws)
    return resolved_jobs.get("orchestrator_agent", "0") or "0"


# =============================================================================
# Endpoints
# =============================================================================

def _effective_uc_config(request: Request) -> tuple[str, str]:
    """Return (catalog, schema) from app state (set at startup from Lakebase app_config or Lakehouse). Fallback to default catalog and schema (payment_analysis)."""
    catalog, schema = getattr(request.app.state, "uc_config", (None, None))
    catalog = (catalog or "").strip() or DEFAULT_IDS["catalog"]
    schema = (schema or "").strip() or get_default_schema()
    return (catalog, schema)


def _effective_warehouse_id(request: Request) -> str:
    """Return warehouse_id from Lakebase app_settings (read at startup) or env defaults."""
    settings = getattr(request.app.state, "lakebase_settings", None) or {}
    return (settings.get("warehouse_id") or "").strip() or DEFAULT_IDS["warehouse_id"]


def _effective_job_defaults(request: Request) -> tuple[str, str]:
    """Return (default_events_per_second, default_duration_minutes) from Lakebase app_settings."""
    settings = getattr(request.app.state, "lakebase_settings", None) or {}
    return (
        (settings.get("default_events_per_second") or "").strip() or "1000",
        (settings.get("default_duration_minutes") or "").strip() or "60",
    )


@router.get("/settings", response_model=SetupSettingsOut, operation_id="getSetupSettings")
def get_setup_settings(request: Request) -> SetupSettingsOut:
    """Return app settings (key-value) from Lakebase app_settings, loaded at startup. Used to show default values and config in the control panel."""
    settings = getattr(request.app.state, "lakebase_settings", None) or {}
    return SetupSettingsOut(settings=dict(settings))


@router.get("/defaults", response_model=SetupDefaultsOut, operation_id="getSetupDefaults")
def get_setup_defaults(
    request: Request,
    ws: WorkspaceClient | None = Depends(get_workspace_client_optional),
) -> SetupDefaultsOut:
    """Return resource IDs and parameters for Setup & Run. Job/pipeline IDs are only returned when resolved from the workspace (existing resources) so Execute always opens a real job/pipeline in Databricks. Workspace host is always the Databricks workspace URL, never the app URL."""
    token_received = bool(_get_obo_token(request))
    host = _get_workspace_host().rstrip("/")
    derived_from_request = False
    if not host:
        host = workspace_url_from_apps_host(_request_host_for_derivation(request), app_name).rstrip("/")
        derived_from_request = bool(host)
    if host and "databricksapps" in host.lower():
        host = ""  # Never return app URL; links must open in the Databricks workspace
    host = ensure_absolute_workspace_url(host).rstrip("/") if host else ""
    workspace_url_derived = derived_from_request and bool(host)
    workspace_id = (_app_config.databricks.workspace_id or "").strip() or (workspace_id_from_workspace_url(host) or "")
    catalog, schema = _effective_uc_config(request)
    if ws is None:
        jobs = {k: "0" for k in DEFAULT_IDS["jobs"]}
        pipelines = {k: "0" for k in DEFAULT_IDS["pipelines"]}
    else:
        resolved_jobs, resolved_pipelines = _resolve_job_and_pipeline_ids(ws)
        jobs, pipelines = _merge_resolved_ids(
            resolved_jobs, resolved_pipelines, DEFAULT_IDS["jobs"], DEFAULT_IDS["pipelines"]
        )
    runtime = getattr(request.app.state, "runtime", None)
    lakebase_autoscaling = bool(
        runtime and (runtime._use_lakebase_autoscaling() or runtime._use_lakebase_direct_connection())
    )
    lakebase_connection_mode = ""
    if runtime and runtime._db_configured():
        if runtime._use_lakebase_direct_connection():
            lakebase_connection_mode = "direct"
        elif runtime._use_lakebase_autoscaling():
            lakebase_connection_mode = "autoscaling"
    return SetupDefaultsOut(
        warehouse_id=_effective_warehouse_id(request),
        catalog=catalog,
        schema_name=schema,
        jobs=jobs,
        pipelines=pipelines,
        workspace_host=host or "",
        workspace_id=workspace_id,
        token_received=token_received,
        workspace_url_derived=workspace_url_derived,
        lakebase_autoscaling=lakebase_autoscaling,
        lakebase_connection_mode=lakebase_connection_mode,
    )


@router.patch("/config", response_model=SetupConfigOut, operation_id="updateSetupConfig")
async def update_setup_config(request: Request, body: SetupConfigIn) -> SetupConfigOut:
    """Update effective catalog and schema in app_config table and app state. Uses user token (OBO), PAT, or service principal for app-level write."""
    catalog = (body.catalog or "").strip()
    schema = (body.schema_name or "").strip()
    if not catalog or not schema:
        raise HTTPException(
            status_code=400,
            detail="catalog and schema are required and must be non-empty.",
        )
    bootstrap = DatabricksConfig.from_environment()
    obo_token = _get_obo_token(request)
    token = obo_token or bootstrap.token
    use_sp = not token and bootstrap.client_id and bootstrap.client_secret
    if not token and not use_sp:
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
        token=token,
        client_id=bootstrap.client_id if use_sp else None,
        client_secret=bootstrap.client_secret if use_sp else None,
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
    runtime = getattr(request.app.state, "runtime", None)
    if runtime:
        write_lakebase_app_config(runtime, catalog, schema)
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
    warehouse_id = body.warehouse_id or _effective_warehouse_id(request)
    default_eps, default_dur = _effective_job_defaults(request)

    notebook_params: dict[str, str] = {
        "catalog": catalog,
        "schema": schema,
    }
    if warehouse_id:
        notebook_params["warehouse_id"] = warehouse_id
    if body.events_per_second is not None:
        notebook_params["events_per_second"] = body.events_per_second
    elif default_eps:
        notebook_params["events_per_second"] = default_eps
    if body.duration_minutes is not None:
        notebook_params["duration_minutes"] = body.duration_minutes
    elif default_dur:
        notebook_params["duration_minutes"] = default_dur

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
