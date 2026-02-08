import os
from typing import Annotated, Generator

from databricks.sdk import WorkspaceClient
from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session

from .config import AppConfig
from .runtime import Runtime
from .services.databricks_service import DatabricksConfig, DatabricksService

# Shared message when neither OBO token nor DATABRICKS_TOKEN is available (exported for use in routes)
AUTH_REQUIRED_DETAIL = (
    "Sign in with Databricks so the app can use your credentials, or set DATABRICKS_TOKEN in the app environment. "
    "When user authorization (OBO) is enabled, open the app from Compute → Apps so your token is forwarded."
)


def get_config(request: Request) -> AppConfig:
    """
    Returns the AppConfig instance from app.state.
    The config is initialized during application lifespan startup.
    """
    if not hasattr(request.app.state, "config"):
        raise RuntimeError(
            "AppConfig not initialized. "
            "Ensure app.state.config is set during application lifespan startup."
        )
    return request.app.state.config


ConfigDep = Annotated[AppConfig, Depends(get_config)]


def get_runtime(request: Request) -> Runtime:
    """
    Returns the Runtime instance from app.state.
    The runtime is initialized during application lifespan startup.
    """
    if not hasattr(request.app.state, "runtime"):
        raise RuntimeError(
            "Runtime not initialized. "
            "Ensure app.state.runtime is set during application lifespan startup."
        )
    return request.app.state.runtime


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]


def get_obo_ws(
    request: Request,
    token: Annotated[str | None, Header(alias="X-Forwarded-Access-Token")] = None,
) -> WorkspaceClient:
    """
    Returns a Databricks Workspace client (on-behalf-of user).
    Requires X-Forwarded-Access-Token header. Host is taken from app config so the client targets the correct workspace.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: X-Forwarded-Access-Token header is missing",
        )
    config = get_config(request)
    host = (config.databricks.workspace_url or "").rstrip("/")
    return WorkspaceClient(host=host or None, token=token, auth_type="pat")


def get_workspace_client(request: Request) -> WorkspaceClient:
    """
    Returns a Databricks Workspace client using your credentials when logged in (OBO)
    or DATABRICKS_TOKEN when set. Use this for run-job, run-pipeline, etc., so no
    hardcoded token is required when user authorization (OBO) is enabled.
    """
    obo_token = request.headers.get("X-Forwarded-Access-Token")
    config = get_config(request)
    host = (config.databricks.workspace_url or "").rstrip("/")
    token = obo_token or os.environ.get("DATABRICKS_TOKEN")
    if not token:
        raise HTTPException(status_code=401, detail=AUTH_REQUIRED_DETAIL)
    if not host:
        raise HTTPException(
            status_code=503,
            detail="DATABRICKS_HOST is not set in the app environment.",
        )
    return WorkspaceClient(host=host, token=token, auth_type="pat")


def get_workspace_client_optional(request: Request) -> WorkspaceClient | None:
    """
    Returns a Workspace client when credentials are available; otherwise None.
    Used by GET /setup/defaults to resolve job/pipeline IDs from the workspace when possible.
    """
    obo_token = request.headers.get("X-Forwarded-Access-Token")
    config = get_config(request)
    host = (config.databricks.workspace_url or "").strip().rstrip("/")
    token = obo_token or os.environ.get("DATABRICKS_TOKEN")
    if not token or not host or "example.databricks.com" in host:
        return None
    return WorkspaceClient(host=host, token=token, auth_type="pat")


def get_session(rt: RuntimeDep) -> Generator[Session, None, None]:
    """
    Returns a SQLModel session. Raises 503 if database is not configured (Databricks App: set PGAPPNAME).
    """
    try:
        with rt.get_session() as session:
            yield session
    except RuntimeError as e:
        if "not configured" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Database not configured. Set PGAPPNAME to your Lakebase instance name in the app configuration.",
            ) from e
        raise


SessionDep = Annotated[Session, Depends(get_session)]


async def get_databricks_service(request: Request) -> DatabricksService:
    """
    Returns a DatabricksService connected to Databricks using the logged-in user's
    credentials (X-Forwarded-Access-Token) when present, or DATABRICKS_TOKEN when set.
    Catalog/schema come from app_config in Lakehouse (loaded at startup or lazy on first OBO request).
    When the app is opened from Databricks (Compute → Apps), the platform forwards the user's
    token so all API calls (SQL Warehouse, jobs, dashboards) use that identity.
    """
    bootstrap = DatabricksConfig.from_environment()
    obo_token = request.headers.get("X-Forwarded-Access-Token")
    token = obo_token or bootstrap.token
    catalog, schema = getattr(request.app.state, "uc_config", (None, None))
    if not catalog or not schema:
        catalog, schema = bootstrap.catalog, bootstrap.schema
    # Lazy-load catalog/schema from app_config in Lakehouse once when we have OBO token but didn't load at startup
    lazy_tried = getattr(request.app.state, "uc_config_lazy_tried", False)
    if obo_token and not getattr(request.app.state, "uc_config_from_lakehouse", False) and not lazy_tried:
        if bootstrap.host and bootstrap.warehouse_id:
            request.app.state.uc_config_lazy_tried = True
            try:
                lazy_config = DatabricksConfig(
                    host=bootstrap.host,
                    token=obo_token,
                    warehouse_id=bootstrap.warehouse_id,
                    catalog=bootstrap.catalog,
                    schema=bootstrap.schema,
                )
                lazy_svc = DatabricksService(config=lazy_config)
                row = await lazy_svc.read_app_config()
                if row and row[0] and row[1]:
                    request.app.state.uc_config = row
                    request.app.state.uc_config_from_lakehouse = True
                    catalog, schema = row
            except Exception:
                pass
    config = DatabricksConfig(
        host=bootstrap.host,
        token=token,
        warehouse_id=bootstrap.warehouse_id,
        catalog=catalog,
        schema=schema,
    )
    return DatabricksService(config=config)


DatabricksServiceDep = Annotated[DatabricksService, Depends(get_databricks_service)]
