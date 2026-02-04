from typing import Annotated

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import User as UserOut
from fastapi import APIRouter, Depends

from .dependencies import get_obo_ws
from .models import VersionOut
from .routes.analytics import router as analytics_router
from .routes.decision import router as decision_router
from .routes.experiments import router as experiments_router
from .routes.incidents import router as incidents_router

try:
    from .._metadata import api_prefix as _api_prefix
except Exception:
    _api_prefix = "/api"

api = APIRouter(prefix=_api_prefix)
api.include_router(decision_router, prefix="/decision")
api.include_router(analytics_router, prefix="/analytics")
api.include_router(experiments_router, prefix="/experiments")
api.include_router(incidents_router, prefix="/incidents")


@api.get("/version", response_model=VersionOut, operation_id="version")
async def version():
    return VersionOut.from_metadata()


@api.get("/current-user", response_model=UserOut, operation_id="currentUser")
def me(obo_ws: Annotated[WorkspaceClient, Depends(get_obo_ws)]):
    return obo_ws.current_user.me()
