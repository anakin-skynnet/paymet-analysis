"""API router: config, auth, and feature routes.

All routes are under /api (required for Databricks Apps token-based auth).
Every route uses response_model and operation_id for OpenAPI client generation (apx/cookbook).
Auth and workspace URL use Databricks Apps headers (x-forwarded-access-token, X-Forwarded-Host).
See: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers
     https://apps-cookbook.dev/docs/category/fastapi
"""

from typing import Annotated

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import User as UserOut
from fastapi import APIRouter, Depends, Request

from .config import ensure_absolute_workspace_url
from .dependencies import ConfigDep, EffectiveWorkspaceUrlDep, get_workspace_client
from .models import AuthStatusOut, VersionOut, WorkspaceConfigOut
from .routes.agents import router as agents_router
from .routes.analytics import router as analytics_router
from .routes.dashboards import router as dashboards_router
from .routes.decision import router as decision_router
from .routes.decision_admin import router as decision_admin_router
from .routes.experiments import router as experiments_router
from .routes.incidents import router as incidents_router
from .routes.notebooks import router as notebooks_router
from .routes.rules import router as rules_router
from .routes.setup import router as setup_router
from .routes.v1 import router as v1_router

try:
    from .._metadata import api_prefix as _api_prefix
except Exception:
    _api_prefix = "/api"

api = APIRouter(prefix=_api_prefix)

# Config and auth (no prefix or shared)
# Feature routes (alphabetical by path prefix)
api.include_router(agents_router, prefix="/agents")
api.include_router(analytics_router, prefix="/analytics")
api.include_router(dashboards_router, prefix="/dashboards")
api.include_router(decision_router, prefix="/decision")
api.include_router(decision_admin_router, prefix="/decision/admin")
api.include_router(experiments_router, prefix="/experiments")
api.include_router(incidents_router, prefix="/incidents")
api.include_router(notebooks_router, prefix="/notebooks")
api.include_router(rules_router, prefix="/rules")
api.include_router(setup_router)
api.include_router(v1_router, prefix="/v1")


@api.get("/version", response_model=VersionOut, operation_id="version")
async def version():
    return VersionOut.from_metadata()


@api.get(
    "/config/workspace",
    response_model=WorkspaceConfigOut,
    operation_id="getWorkspaceConfig",
)
def get_workspace_config(workspace_url: EffectiveWorkspaceUrlDep):
    """Return workspace base URL for Execute links and dashboard embed. When the app is opened from Compute → Apps, uses the request-derived workspace URL so end users get their own workspace."""
    return WorkspaceConfigOut(workspace_url=workspace_url or "")


@api.get("/auth/status", response_model=AuthStatusOut, operation_id="getAuthStatus")
def auth_status(request: Request) -> AuthStatusOut:
    """Return whether the request has user credentials (Databricks Apps: x-forwarded-access-token). Used to show Sign in with Databricks when false."""
    token = (
        request.headers.get("X-Forwarded-Access-Token")
        or request.headers.get("x-forwarded-access-token")
    )
    return AuthStatusOut(authenticated=bool(token and str(token).strip()))


@api.get("/current-user", response_model=UserOut, operation_id="currentUser")
def me(ws: Annotated[WorkspaceClient, Depends(get_workspace_client)]):
    """Return current Databricks user (uses your credentials when logged in or DATABRICKS_TOKEN)."""
    return ws.current_user.me()
