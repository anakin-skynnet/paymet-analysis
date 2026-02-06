from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logger import logger

try:
    from .._metadata import api_prefix as _api_prefix, dist_dir as _dist_dir
except Exception:
    _api_prefix = "/api"
    _dist_dir = Path(__file__).resolve().parents[1] / "__dist__"


def add_not_found_handler(app: FastAPI):
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.info(
            f"HTTP exception handler called for request {request.url.path} with status code {exc.status_code}"
        )
        if exc.status_code == 404:
            path = request.url.path
            accept = request.headers.get("accept", "")

            is_api = path.startswith(_api_prefix)
            is_get_page_nav = request.method == "GET" and "text/html" in accept

            # Heuristic: if the last path segment looks like a file (has a dot), don't SPA-fallback
            last_segment = path.rstrip("/").split("/")[-1] if path else ""
            looks_like_asset = "." in last_segment

            if (not is_api) and is_get_page_nav and (not looks_like_asset):
                index_html = _dist_dir / "index.html"
                if index_html.exists():
                    # Let the SPA router handle it
                    return FileResponse(index_html)
        # Default: return the original HTTP error (JSON 404 for API, etc.)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    app.exception_handler(StarletteHTTPException)(http_exception_handler)
