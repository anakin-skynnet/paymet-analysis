"""FastAPI application entrypoint for the payment-analysis Databricks App.

Serves the React UI at / and the API at /api. When deployed as a Databricks App,
the platform proxies requests and sets headers (x-forwarded-access-token, X-Forwarded-Host).
Patterns aligned with:
  - https://docs.databricks.com/aws/en/dev-tools/databricks-apps/configuration
  - https://apps-cookbook.dev/docs/intro (FastAPI recipes)
  - https://github.com/databricks-solutions/apx
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import AppConfig
from .lakebase_config import load_app_config_and_settings
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

try:
    from .. import __version__ as _app_version
except Exception:
    _app_version = "0.0.0"

_APP_DESCRIPTION = (
    "Payment approval rate optimization on Databricks: streaming analytics, ML models, AI agents, "
    "and decisioning. Serves React UI at / and API at /api (Databricks Apps token-based auth)."
)


def _resolve_ui_dist() -> Path | None:
    """Resolve UI dist directory; try metadata path, env, cwd-based paths (Databricks App vs local)."""
    cwd = Path.cwd()
    # Bundle sync uploads to workspace.file_path (e.g. .../payment-analysis/files); app may run with cwd there or at parent.
    candidates: list[Path] = [
        _dist_dir_meta.resolve() if not _dist_dir_meta.is_absolute() else _dist_dir_meta,
        Path(__file__).resolve().parents[2] / "payment_analysis" / "__dist__",  # from backend/app.py -> src/payment_analysis/__dist__
        cwd / "src" / "payment_analysis" / "__dist__",
        cwd / "files" / "src" / "payment_analysis" / "__dist__",  # when cwd is bundle root and sync put content under files/
        cwd / "__dist__",
    ]
    # Databricks App: optional env for app root (bundle workspace folder)
    app_root = os.environ.get("APP_ROOT") or os.environ.get("BUNDLE_FOLDER")
    if app_root:
        base = Path(app_root).resolve()
        candidates.insert(0, base / "src" / "payment_analysis" / "__dist__")
        candidates.insert(0, base / "files" / "src" / "payment_analysis" / "__dist__")
    # Databricks Apps runtime: workspace path may be in BUNDLE_ROOT or source under a different mount
    bundle_root = os.environ.get("BUNDLE_ROOT")
    if bundle_root:
        base = Path(bundle_root).resolve()
        candidates.insert(0, base / "files" / "src" / "payment_analysis" / "__dist__")
        candidates.insert(0, base / "src" / "payment_analysis" / "__dist__")
    # Optional explicit UI dist path (e.g. for custom deploys)
    ui_dist_env = os.environ.get("UI_DIST_DIR")
    if ui_dist_env:
        candidates.insert(0, Path(ui_dist_env).resolve())

    for p in candidates:
        try:
            p_resolved = p.resolve()
        except Exception:
            p_resolved = p
        exists = p_resolved.exists()
        has_index = (p_resolved / "index.html").exists() if exists else False
        if exists and has_index:
            return p_resolved
    logger.warning(
        "UI dist not found. cwd=%s APP_ROOT=%s. "
        "Set APP_ROOT or UI_DIST_DIR in app Environment if needed. Sync includes src/payment_analysis/__dist__.",
        cwd,
        app_root,
    )
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

    # Load config and settings from Lakebase first (backend reads these tables before starting)
    app.state.lakebase_settings = {}
    app.state.uc_config_from_lakebase = False
    uc_from_lakebase = None
    if runtime._db_configured():
        try:
            uc_from_lakebase, app.state.lakebase_settings = load_app_config_and_settings(runtime)
            if app.state.lakebase_settings:
                logger.info("Loaded app_settings from Lakebase: %s", list(app.state.lakebase_settings.keys()))
        except Exception as e:
            logger.warning("Could not load config from Lakebase: %s", e)

    # Unity Catalog config: prefer Lakebase app_config, then Lakehouse, then env
    bootstrap = DatabricksConfig.from_environment()
    app.state.uc_config_from_lakehouse = False
    if uc_from_lakebase and uc_from_lakebase[0] and uc_from_lakebase[1]:
        app.state.uc_config = uc_from_lakebase
        app.state.uc_config_from_lakebase = True
        logger.info("Using catalog/schema from Lakebase app_config: %s.%s", uc_from_lakebase[0], uc_from_lakebase[1])
    elif bootstrap.host and bootstrap.token and bootstrap.warehouse_id:
        try:
            svc = DatabricksService(config=bootstrap)
            row = await svc.read_app_config()
            if row and row[0] and row[1]:
                app.state.uc_config = row
                app.state.uc_config_from_lakehouse = True
                logger.info("Using catalog/schema from Lakehouse app_config: %s.%s", row[0], row[1])
            else:
                app.state.uc_config = (bootstrap.catalog, bootstrap.schema)
                logger.info("Using catalog/schema from env: %s.%s", bootstrap.catalog, bootstrap.schema)
        except Exception as e:
            logger.warning("Could not load app_config from Lakehouse, using env: %s", e)
            app.state.uc_config = (bootstrap.catalog, bootstrap.schema)
    else:
        app.state.uc_config = (bootstrap.catalog, bootstrap.schema)
        app.state.uc_config_lazy_tried = False
        logger.info(
            "Unity Catalog config from env (no token at startup). Catalog/schema lazy-loaded from app_config on first request if available."
        )

    # Store in app.state for access via dependencies
    app.state.config = config
    app.state.runtime = runtime

    yield


app = FastAPI(
    title=_app_name,
    description=_APP_DESCRIPTION,
    version=_app_version,
    lifespan=lifespan,
)

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
            <p>To fix: run <code>./scripts/bundle.sh deploy dev</code> from the repo (it builds the UI first, then deploys). 
            Or run <code>uv run apx build</code> then redeploy the bundle so <code>src/payment_analysis/__dist__</code> is synced.</p>
            </body></html>"""
        )


add_not_found_handler(app, _ui_dist)
