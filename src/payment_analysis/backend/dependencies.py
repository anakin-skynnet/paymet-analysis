import os
from typing import Annotated, Generator

from databricks.sdk import WorkspaceClient
from fastapi import Depends, Header, HTTPException, Request

from .databricks_client_helpers import workspace_client_pat_only
from sqlmodel import Session

from .config import (
    AppConfig,
    WORKSPACE_URL_PLACEHOLDER,
    app_name,
    ensure_absolute_workspace_url,
    workspace_url_from_apps_host,
)
from .runtime import Runtime
from .services.databricks_service import DatabricksConfig, DatabricksService

# Shared message when neither OBO token nor DATABRICKS_TOKEN is available (exported for use in routes)
AUTH_REQUIRED_DETAIL = (
    "Open this app from Workspace → Compute → Apps → payment-analysis so the platform forwards your token (recommended), "
    "or set DATABRICKS_TOKEN in the app environment (Compute → Apps → Edit → Environment)."
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
    raw = (config.databricks.workspace_url or "").strip().rstrip("/")
    if not raw or raw == WORKSPACE_URL_PLACEHOLDER.rstrip("/"):
        raise HTTPException(status_code=503, detail="DATABRICKS_HOST is not set.")
    host = ensure_absolute_workspace_url(raw)
    return workspace_client_pat_only(host=host, token=token)


def _get_obo_token(request: Request) -> str | None:
    """User token when app is opened from Compute → Apps (OBO). Check common header names."""
    return (
        request.headers.get("X-Forwarded-Access-Token")
        or request.headers.get("x-forwarded-access-token")
        or None
    )


def get_workspace_client(request: Request) -> WorkspaceClient:
    """
    Returns a Databricks Workspace client using your credentials when logged in (OBO)
    or DATABRICKS_TOKEN when set. Use this for run-job, run-pipeline, etc.
    Host is always absolute (https://...). When DATABRICKS_HOST is unset, derives host
    from the request when the app is served from a Databricks Apps URL.
    When using OBO (open app from Compute → Apps), do not set DATABRICKS_CLIENT_ID/SECRET
    in the app environment or the SDK may trigger OAuth scope errors.
    """
    obo_token = _get_obo_token(request)
    config = get_config(request)
    raw = (config.databricks.workspace_url or "").strip().rstrip("/")
    if not raw or raw == WORKSPACE_URL_PLACEHOLDER.rstrip("/"):
        raw = workspace_url_from_apps_host(request.headers.get("host") or "", app_name).strip().rstrip("/")
    token = obo_token or os.environ.get("DATABRICKS_TOKEN")
    if not token:
        raise HTTPException(status_code=401, detail=AUTH_REQUIRED_DETAIL)
    if not raw:
        raise HTTPException(
            status_code=503,
            detail="DATABRICKS_HOST is not set. Set it in the app environment or open the app from Compute → Apps so the workspace URL can be derived.",
        )
    host = ensure_absolute_workspace_url(raw)
    return workspace_client_pat_only(host=host, token=token)


def get_workspace_client_optional(request: Request) -> WorkspaceClient | None:
    """
    Returns a Workspace client when credentials are available; otherwise None.
    Used by GET /setup/defaults to resolve job/pipeline IDs from the workspace when possible.
    Derives host from request when DATABRICKS_HOST is unset and app is served from Apps URL.
    Token is read from X-Forwarded-Access-Token (set when app is opened from Compute → Apps).
    """
    obo_token = _get_obo_token(request)
    config = get_config(request)
    raw = (config.databricks.workspace_url or "").strip().rstrip("/")
    if not raw or raw == WORKSPACE_URL_PLACEHOLDER.rstrip("/"):
        raw = workspace_url_from_apps_host(request.headers.get("host") or "", app_name).strip().rstrip("/")
    token = obo_token or os.environ.get("DATABRICKS_TOKEN")
    if not token or not raw:
        return None
    host = ensure_absolute_workspace_url(raw)
    return workspace_client_pat_only(host=host, token=token)


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


def _effective_databricks_host(request: Request, bootstrap_host: str | None) -> str | None:
    """Host from env or derived from request when app is opened from Compute → Apps."""
    raw = (bootstrap_host or "").strip().rstrip("/")
    if raw and "example.databricks.com" not in raw:
        return raw
    derived = workspace_url_from_apps_host(request.headers.get("host") or "", app_name).strip().rstrip("/")
    return derived if derived else None


async def get_databricks_service(request: Request) -> DatabricksService:
    """
    Returns a DatabricksService using the forwarded user token when the app is opened
    from Compute → Apps (OBO), or DATABRICKS_TOKEN when set. Host is taken from
    DATABRICKS_HOST or derived from the request Host when served from a Databricks Apps URL.
    Catalog/schema come from app_config in Lakehouse (loaded at startup or lazy on first request).
    """
    bootstrap = DatabricksConfig.from_environment()
    obo_token = _get_obo_token(request)
    token = obo_token or bootstrap.token
    effective_host = _effective_databricks_host(request, bootstrap.host)
    catalog, schema = getattr(request.app.state, "uc_config", (None, None))
    if not catalog or not schema:
        catalog, schema = bootstrap.catalog, bootstrap.schema
    # Lazy-load catalog/schema from app_config in Lakehouse once when we have OBO token but didn't load at startup
    lazy_tried = getattr(request.app.state, "uc_config_lazy_tried", False)
    if obo_token and not getattr(request.app.state, "uc_config_from_lakehouse", False) and not lazy_tried:
        if effective_host and bootstrap.warehouse_id:
            request.app.state.uc_config_lazy_tried = True
            try:
                lazy_config = DatabricksConfig(
                    host=effective_host,
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
        host=effective_host,
        token=token,
        warehouse_id=bootstrap.warehouse_id,
        catalog=catalog,
        schema=schema,
    )
    return DatabricksService(config=config)


DatabricksServiceDep = Annotated[DatabricksService, Depends(get_databricks_service)]
