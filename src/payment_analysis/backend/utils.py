"""SPA fallback and 404 handler for FastAPI when serving the React UI.

StaticFiles returns a 404 Response (does not raise) for missing paths, so the exception
handler alone is not enough. We add middleware that intercepts 404 responses and
serves index.html for GET requests with Accept: text/html (so client-side routes work
on direct load or refresh).
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from .._metadata import api_prefix as _api_prefix, dist_dir as _default_dist_dir
except Exception:
    _api_prefix = "/api"
    _default_dist_dir = Path(__file__).resolve().parents[1] / "__dist__"


def _should_fallback_to_index(path: str, method: str, accept: str) -> bool:
    if path.startswith(_api_prefix):
        return False
    if method != "GET" or "text/html" not in accept:
        return False
    last_segment = path.rstrip("/").split("/")[-1] if path else ""
    if "." in last_segment:
        return False
    return True


class SPAFallbackMiddleware(BaseHTTPMiddleware):
    """Intercept 404 responses and serve index.html for non-API GET (so SPA routes work)."""

    def __init__(self, app, ui_dist_dir: Path):
        super().__init__(app)
        self.ui_dist_dir = ui_dist_dir

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.status_code != 404:
            return response
        path = request.url.path
        accept = request.headers.get("accept", "")
        if not _should_fallback_to_index(path, request.method, accept):
            return response
        index_html = self.ui_dist_dir / "index.html"
        if not index_html.exists():
            return response
        return FileResponse(index_html)


def add_not_found_handler(app: FastAPI, ui_dist_dir: Path | None = None) -> None:
    """Register 404 exception handler and SPA fallback middleware.

    - Exception handler: for routes that raise HTTPException(404).
    - Middleware: for StaticFiles 404 responses (it returns 404, does not raise).
    """
    dist_dir = ui_dist_dir if ui_dist_dir is not None else _default_dist_dir

    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            path = request.url.path
            accept = request.headers.get("accept", "")
            if _should_fallback_to_index(path, request.method, accept):
                index_html = dist_dir / "index.html"
                if index_html.exists():
                    return FileResponse(index_html)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    app.exception_handler(StarletteHTTPException)(http_exception_handler)

    if dist_dir.exists() and (dist_dir / "index.html").exists():
        app.add_middleware(SPAFallbackMiddleware, ui_dist_dir=dist_dir)  # type: ignore[arg-type]
