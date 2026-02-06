from typing import Annotated

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import User as UserOut
from fastapi import APIRouter, Depends

from .dependencies import get_obo_ws
from .models import VersionOut
from .routes.agents import router as agents_router
from .routes.analytics import router as analytics_router
from .routes.decision import router as decision_router
from .routes.experiments import router as experiments_router
from .routes.incidents import router as incidents_router
from .routes.dashboards import router as dashboards_router
from .routes.notebooks import router as notebooks_router
from .routes.rules import router as rules_router
from .routes.setup import router as setup_router

try:
    from .._metadata import api_prefix as _api_prefix
except Exception:
    _api_prefix = "/api"

api = APIRouter(prefix=_api_prefix)
api.include_router(decision_router, prefix="/decision")
api.include_router(agents_router, prefix="/agents")
api.include_router(analytics_router, prefix="/analytics")
api.include_router(experiments_router, prefix="/experiments")
api.include_router(incidents_router, prefix="/incidents")
api.include_router(dashboards_router, prefix="/dashboards")
api.include_router(notebooks_router, prefix="/notebooks")
api.include_router(rules_router, prefix="/rules")
api.include_router(setup_router)


@api.get("/version", response_model=VersionOut, operation_id="version")
async def version():
    return VersionOut.from_metadata()


@api.get("/current-user", response_model=UserOut, operation_id="currentUser")
def me(obo_ws: Annotated[WorkspaceClient, Depends(get_obo_ws)]):
    return obo_ws.current_user.me()
