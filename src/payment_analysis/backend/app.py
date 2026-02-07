from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import AppConfig
from .logger import logger
from .router import api
from .runtime import Runtime
from .services.databricks_service import DatabricksConfig, DatabricksService
from .utils import add_not_found_handler

try:
    from .._metadata import app_name as _app_name, dist_dir as _dist_dir_meta
except Exception:
    _app_name = "payment-analysis"
    _dist_dir_meta = Path(__file__).resolve().parents[1] / "__dist__"


def _resolve_ui_dist() -> Path | None:
    """Resolve UI dist directory; try metadata path and fallbacks (e.g. bundle artifact layout)."""
    candidates = [
        _dist_dir_meta.resolve() if not _dist_dir_meta.is_absolute() else _dist_dir_meta,
        Path.cwd() / "src" / "payment_analysis" / "__dist__",
        Path.cwd() / "__dist__",
    ]
    for p in candidates:
        if p.exists() and (p / "index.html").exists():
            return p
    return None


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
_ui_dist = _resolve_ui_dist()
if _ui_dist is not None:
    ui = StaticFiles(directory=str(_ui_dist), html=True)
    app.mount("/", ui)
    logger.info("Serving UI from %s", _ui_dist)
else:
    logger.warning(
        "UI dist directory not found (tried %s and fallbacks). Serving API only; GET / will show fallback. "
        "Run `uv run apx build` before deploying to include frontend.",
        _dist_dir_meta,
    )

    @app.get("/", response_class=HTMLResponse)
    def _ui_fallback():
        return HTMLResponse(
            """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Payment Analysis</title></head><body>
            <h1>Payment Analysis API</h1>
            <p>The web UI build was not found. The API is available.</p>
            <ul>
              <li><a href="/api/docs">OpenAPI (Swagger) docs</a></li>
              <li><a href="/api/redoc">ReDoc</a></li>
            </ul>
            <p>To serve the UI, run <code>uv run apx build</code> before deploying the bundle.</p>
            </body></html>"""
        )


add_not_found_handler(app, _ui_dist)
