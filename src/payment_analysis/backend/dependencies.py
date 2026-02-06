from typing import Annotated, Generator

from databricks.sdk import WorkspaceClient
from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session

from .config import AppConfig
from .runtime import Runtime
from .services.databricks_service import DatabricksConfig, DatabricksService


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


def get_databricks_service(request: Request) -> DatabricksService:
    """
    Returns a DatabricksService using effective catalog/schema from app_config table.
    Effective config is loaded at startup (lifespan) and stored in request.app.state.uc_config.
    """
    bootstrap = DatabricksConfig.from_environment()
    catalog, schema = getattr(request.app.state, "uc_config", (None, None))
    if not catalog or not schema:
        catalog, schema = bootstrap.catalog, bootstrap.schema
    config = DatabricksConfig(
        host=bootstrap.host,
        token=bootstrap.token,
        warehouse_id=bootstrap.warehouse_id,
        catalog=catalog,
        schema=schema,
    )
    return DatabricksService(config=config)


DatabricksServiceDep = Annotated[DatabricksService, Depends(get_databricks_service)]
