from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import AppConfig
from .router import api
from .runtime import Runtime
from .utils import add_not_found_handler
from .logger import logger

try:
    from .._metadata import app_name as _app_name, dist_dir as _dist_dir
except Exception:
    # Safe defaults for local tooling / before APX generates metadata.
    _app_name = "payment-analysis"
    _dist_dir = Path(__file__).resolve().parents[1] / "__dist__"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize config and runtime, store in app.state for dependency injection
    config = AppConfig()
    logger.info(
        "Application starting: name=%s; DB and runtime will be initialized.",
        config.app_name,
    )

    runtime = Runtime(config)
    runtime.validate_db()
    runtime.initialize_models()
    # When PGAPPNAME is not set (e.g. Databricks App without Lakebase), DB is skipped; app still starts.

    # Load effective Unity Catalog config from app_config table (bootstrap = env)
    from .services.databricks_service import DatabricksConfig, DatabricksService
    bootstrap = DatabricksConfig.from_environment()
    if bootstrap.host and bootstrap.token and bootstrap.warehouse_id:
        try:
            svc = DatabricksService(config=bootstrap)
            row = await svc.read_app_config()
            if row and row[0] and row[1]:
                app.state.uc_config = row
                logger.info("Using catalog/schema from app_config: %s.%s", row[0], row[1])
            else:
                app.state.uc_config = (bootstrap.catalog, bootstrap.schema)
                logger.info("Using catalog/schema from env: %s.%s", bootstrap.catalog, bootstrap.schema)
        except Exception as e:
            logger.warning("Could not load app_config, using env defaults: %s", e)
            app.state.uc_config = (bootstrap.catalog, bootstrap.schema)
    else:
        app.state.uc_config = (bootstrap.catalog, bootstrap.schema)

    # Store in app.state for access via dependencies
    app.state.config = config
    app.state.runtime = runtime

    yield


app = FastAPI(title=f"{_app_name}", lifespan=lifespan)

# note the order of includes and mounts!
app.include_router(api)
if _dist_dir.exists():
    ui = StaticFiles(directory=_dist_dir, html=True)
    app.mount("/", ui)
else:
    logger.warning(
        "UI dist directory not found at %s; serving API only. "
        "Run `uv run apx build` (or `uv run apx dev start`) to generate frontend assets.",
        _dist_dir,
    )


add_not_found_handler(app)
