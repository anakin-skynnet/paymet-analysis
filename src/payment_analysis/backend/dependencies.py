from typing import Annotated, Generator

from databricks.sdk import WorkspaceClient
from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session

from .config import AppConfig
from .runtime import Runtime


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
    Returns a SQLModel session.
    """
    with rt.get_session() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
