"""SPA fallback and 404 handler for FastAPI when serving the React UI."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

try:
    from .._metadata import api_prefix as _api_prefix, dist_dir as _default_dist_dir
except Exception:
    _api_prefix = "/api"
    _default_dist_dir = Path(__file__).resolve().parents[1] / "__dist__"


def add_not_found_handler(app: FastAPI, ui_dist_dir: Path | None = None):
    """Register 404 handler with SPA fallback. Use ui_dist_dir when UI is served from a resolved fallback path."""
    dist_dir = ui_dist_dir if ui_dist_dir is not None else _default_dist_dir

    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            path = request.url.path
            accept = request.headers.get("accept", "")

            is_api = path.startswith(_api_prefix)
            is_get_page_nav = request.method == "GET" and "text/html" in accept

            # Heuristic: if the last path segment looks like a file (has a dot), don't SPA-fallback
            last_segment = path.rstrip("/").split("/")[-1] if path else ""
            looks_like_asset = "." in last_segment

            if (not is_api) and is_get_page_nav and (not looks_like_asset):
                index_html = dist_dir / "index.html"
                if index_html.exists():
                    return FileResponse(index_html)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    app.exception_handler(StarletteHTTPException)(http_exception_handler)
