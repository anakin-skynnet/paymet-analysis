"""
Dashboard Router - AI/BI Dashboard Integration.

This module provides endpoints for accessing all Databricks AI/BI dashboards
embedded in the FastAPI application.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..config import (
    REFERENCE_WORKSPACE_HOST,
    REFERENCE_WORKSPACE_ID,
    ensure_absolute_workspace_url,
    workspace_id_from_workspace_url,
)
from ..dependencies import ConfigDep, DatabricksServiceDep, EffectiveWorkspaceUrlDep, get_workspace_client_optional

router = APIRouter(tags=["dashboards"])


# =============================================================================
# Models
# =============================================================================

class DashboardCategory(str, Enum):
    """Dashboard categories for organization."""
    EXECUTIVE = "executive"
    OPERATIONS = "operations"
    ANALYTICS = "analytics"
    TECHNICAL = "technical"


class DashboardInfo(BaseModel):
    """Dashboard metadata model."""
    id: str = Field(..., description="Unique dashboard identifier")
    name: str = Field(..., description="Dashboard display name")
    description: str = Field(..., description="Dashboard description")
    category: DashboardCategory = Field(..., description="Dashboard category")
    tags: list[str] = Field(default_factory=list, description="Dashboard tags")
    url_path: str | None = Field(None, description="Databricks dashboard URL path")
    embed_url: str | None = Field(None, description="Embeddable iframe URL")


class DashboardList(BaseModel):
    """List of available dashboards."""
    dashboards: list[DashboardInfo]
    total: int
    categories: dict[str, int]


# =============================================================================
# Dashboard Registry (Databricks AI/BI Lakeview Dashboards)
# =============================================================================
# Unified multi-visual dashboards for approval-rate analysis (see MERGE_GROUPS
# in scripts/dashboards.py). Run "merge" then "prepare"; bundle deploys these three.
#
# Lakeview embed URL format:
#   /dashboardsv3/<dashboard_id>/published?o=<workspace_id>
# When opened via the app, ?embed=true is appended for iframe mode.
#
# Dashboard IDs: set via env (DASHBOARD_ID_*) or discovered at startup.
# =============================================================================

# ---------------------------------------------------------------------------
# Dashboard ID resolution — portable across workspaces.
#
# Priority:
#   1. Environment variables (DASHBOARD_ID_*) set in app.yml
#   2. Auto-discovery from Databricks workspace API (w.lakeview.list())
#   3. Empty string (dashboard links disabled)
#
# Auto-discovery searches for dashboards whose display_name matches the
# bundle naming convention: "[<env>] Data & Quality", "[<env>] ML & Optimization",
# "[<env>] Executive & Trends".
# ---------------------------------------------------------------------------
import logging as _logging
import threading as _threading

_log = _logging.getLogger(__name__)

# Cache for discovered dashboard IDs (populated once, thread-safe)
_dashboard_id_cache: dict[str, str] = {}
_discovery_lock = _threading.Lock()
_discovery_done = False
_discovery_attempt_count = 0
_DISCOVERY_MAX_RETRIES = 3

# Name patterns to look for (without environment prefix)
_DASHBOARD_NAME_PATTERNS: dict[str, list[str]] = {
    "data_quality": ["Data & Quality", "Data Quality", "data_quality"],
    "ml_optimization": ["ML & Optimization", "ML Optimization", "ml_optimization"],
    "executive_trends": ["Executive & Trends", "Executive Trends", "executive_trends"],
}


def _discover_dashboard_ids(ws: Any | None = None) -> dict[str, str]:
    """Query Databricks workspace to find dashboard IDs by display_name pattern.

    ``ws`` is an optional pre-authenticated WorkspaceClient.  When *None* the
    function tries to build one from the environment (DATABRICKS_HOST / TOKEN).
    Discovery is skipped entirely when no credentials are available so the
    module import never blocks on interactive auth flows.

    If the provided ``ws`` (user OBO token) lacks the ``dashboards`` OAuth scope,
    the function automatically retries with the app's service principal credentials
    (DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET) which do not require scopes.

    Retries up to ``_DISCOVERY_MAX_RETRIES`` times when no dashboards are found
    (dashboards may not be deployed yet on first attempts after bundle deploy).
    """
    global _discovery_done, _discovery_attempt_count
    if _discovery_done:
        return _dashboard_id_cache

    with _discovery_lock:
        if _discovery_done:
            return _dashboard_id_cache

        _discovery_attempt_count += 1
        try:
            _do_lakeview_discovery(ws)
        except Exception as exc:
            # If user OBO token lacks the dashboards scope, fall back to app SP
            exc_str = str(exc)
            if ws is not None and ("required scopes" in exc_str or "scope" in exc_str.lower()):
                _log.info("User token lacks dashboards scope — retrying discovery with app service principal.")
                try:
                    _do_lakeview_discovery(None)
                except Exception as sp_exc:
                    if _discovery_attempt_count < _DISCOVERY_MAX_RETRIES:
                        _log.info("Dashboard discovery attempt %d failed with SP (%s). Will retry.",
                                  _discovery_attempt_count, sp_exc)
                        return _dashboard_id_cache
                    _log.warning("Dashboard auto-discovery failed after %d attempts (will use env vars): %s",
                                 _discovery_attempt_count, sp_exc)
            else:
                if _discovery_attempt_count < _DISCOVERY_MAX_RETRIES:
                    _log.info("Dashboard discovery attempt %d failed (%s). Will retry.",
                              _discovery_attempt_count, exc)
                    return _dashboard_id_cache
                _log.warning("Dashboard auto-discovery failed after %d attempts (will use env vars): %s",
                             _discovery_attempt_count, exc)
        finally:
            if len(_dashboard_id_cache) >= len(_DASHBOARD_NAME_PATTERNS) or _discovery_attempt_count >= _DISCOVERY_MAX_RETRIES:
                _discovery_done = True

    return _dashboard_id_cache


def _do_lakeview_discovery(ws: Any | None) -> None:
    """Run the actual lakeview.list() call and populate _dashboard_id_cache."""
    if ws is None:
        import os as _os
        _host = _os.environ.get("DATABRICKS_HOST", "").strip()
        _token = _os.environ.get("DATABRICKS_TOKEN", "").strip()
        _client_id = _os.environ.get("DATABRICKS_CLIENT_ID", "").strip()
        if not _host or not (_token or _client_id):
            _log.info("Dashboard auto-discovery skipped: no explicit Databricks credentials in environment.")
            return
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
    else:
        w = ws

    for dash in w.lakeview.list():
        display_name = dash.display_name or ""
        for key, patterns in _DASHBOARD_NAME_PATTERNS.items():
            if key in _dashboard_id_cache:
                continue
            for pattern in patterns:
                if pattern.lower() in display_name.lower():
                    _dashboard_id_cache[key] = dash.dashboard_id or ""
                    _log.info("Discovered dashboard '%s' (id=%s) for key '%s'",
                              display_name, dash.dashboard_id, key)
                    break

        if len(_dashboard_id_cache) >= len(_DASHBOARD_NAME_PATTERNS):
            break

    missing = [k for k in _DASHBOARD_NAME_PATTERNS if k not in _dashboard_id_cache]
    if missing:
        if _discovery_attempt_count < _DISCOVERY_MAX_RETRIES:
            _log.info("Dashboard discovery attempt %d: missing %s. Will retry on next request.",
                      _discovery_attempt_count, missing)
        else:
            _log.warning("Could not discover dashboards for: %s after %d attempts. "
                         "Set DASHBOARD_ID_* env vars or run Job 4 to deploy dashboards.",
                         missing, _discovery_attempt_count)


def _get_dashboard_id_from_env(env_var: str) -> str:
    """Return dashboard ID from environment variable, or empty string."""
    return os.getenv(env_var, "").strip()


def _get_dashboard_id(env_var: str, cache_key: str) -> str:
    """Resolve a dashboard ID: env var → auto-discovery cache → empty string."""
    env_val = _get_dashboard_id_from_env(env_var)
    if env_val:
        return env_val
    return _dashboard_id_cache.get(cache_key, "")


# Dashboard IDs: initially set from env vars only (no network at import time).
# Workspace API auto-discovery runs once on the first request (see list_dashboards).
_DASHBOARD_ID_DATA_QUALITY = _get_dashboard_id_from_env("DASHBOARD_ID_DATA_QUALITY")
_DASHBOARD_ID_ML_OPTIMIZATION = _get_dashboard_id_from_env("DASHBOARD_ID_ML_OPTIMIZATION")
_DASHBOARD_ID_EXECUTIVE_TRENDS = _get_dashboard_id_from_env("DASHBOARD_ID_EXECUTIVE_TRENDS")


def _refresh_dashboard_ids_from_cache() -> None:
    """Re-read IDs after auto-discovery populates _dashboard_id_cache."""
    global _DASHBOARD_ID_DATA_QUALITY, _DASHBOARD_ID_ML_OPTIMIZATION, _DASHBOARD_ID_EXECUTIVE_TRENDS
    _DASHBOARD_ID_DATA_QUALITY = _get_dashboard_id("DASHBOARD_ID_DATA_QUALITY", "data_quality")
    _DASHBOARD_ID_ML_OPTIMIZATION = _get_dashboard_id("DASHBOARD_ID_ML_OPTIMIZATION", "ml_optimization")
    _DASHBOARD_ID_EXECUTIVE_TRENDS = _get_dashboard_id("DASHBOARD_ID_EXECUTIVE_TRENDS", "executive_trends")


def _lakeview_url_path(dashboard_id: str) -> str:
    """Lakeview published dashboard URL path (for opening in a new tab)."""
    return f"/dashboardsv3/{dashboard_id}/published"


def _lakeview_embed_path(dashboard_id: str) -> str:
    """Lakeview embed URL path with /embed/ prefix.

    Databricks requires the /embed/ prefix to serve the dashboard with
    relaxed X-Frame-Options / CSP frame-ancestors headers, allowing the
    dashboard to be loaded inside an iframe from *.databricksapps.com.
    See: https://docs.databricks.com/en/dashboards/embed.html
    """
    return f"/embed/dashboardsv3/{dashboard_id}/published"


# Mapping from dashboard id → (env var, discovery cache key)
_DASHBOARD_ID_MAP: dict[str, tuple[str, str]] = {
    "data_quality_unified": ("DASHBOARD_ID_DATA_QUALITY", "data_quality"),
    "ml_optimization_unified": ("DASHBOARD_ID_ML_OPTIMIZATION", "ml_optimization"),
    "executive_trends_unified": ("DASHBOARD_ID_EXECUTIVE_TRENDS", "executive_trends"),
}


def _current_lakeview_id(dashboard_id: str) -> str:
    """Return the current Lakeview dashboard ID (env var → discovery cache → empty)."""
    env_var, cache_key = _DASHBOARD_ID_MAP.get(dashboard_id, ("", ""))
    if env_var:
        return _get_dashboard_id(env_var, cache_key)
    return ""


# Static dashboard metadata (url_path set dynamically via _get_dashboards())
_DASHBOARDS_STATIC: list[DashboardInfo] = [
    DashboardInfo(
        id="data_quality_unified",
        name="Data & Quality",
        description="Stream ingestion volume, data quality, real-time monitoring, active alerts, and global coverage by country. Single dashboard for data health and operational monitoring.",
        category=DashboardCategory.TECHNICAL,
        tags=["streaming", "ingestion", "data-quality", "realtime", "alerts", "countries", "geography"],
    ),
    DashboardInfo(
        id="ml_optimization_unified",
        name="ML & Optimization",
        description="Smart routing, decline analysis & recovery, fraud/risk, 3DS authentication, and financial impact. Predictions, smart retry impact, smart checkout behavior.",
        category=DashboardCategory.ANALYTICS,
        tags=["routing", "decline", "recovery", "fraud", "risk", "3ds", "smart-checkout", "smart-retry", "roi"],
    ),
    DashboardInfo(
        id="executive_trends_unified",
        name="Executive & Trends",
        description="KPIs, approval rates, daily trends, merchant performance, and technical performance. For business users to analyze and understand approval rates.",
        category=DashboardCategory.EXECUTIVE,
        tags=["kpi", "approval-rate", "trends", "merchant", "performance", "executive"],
    ),
]


def _get_dashboards() -> list[DashboardInfo]:
    """Build the dashboards list with current Lakeview IDs (resolved at request time)."""
    result: list[DashboardInfo] = []
    for d in _DASHBOARDS_STATIC:
        lakeview_id = _current_lakeview_id(d.id)
        result.append(DashboardInfo(
            id=d.id,
            name=d.name,
            description=d.description,
            category=d.category,
            tags=d.tags,
            url_path=_lakeview_url_path(lakeview_id) if lakeview_id else None,
        ))
    return result


# Backward-compatible alias; callers that import DASHBOARDS get the static list
# but endpoints should use _get_dashboards() for live IDs.
DASHBOARDS = _get_dashboards()


# =============================================================================
# Endpoints (mounted at /api/dashboards in router.py)
# =============================================================================

@router.get("", response_model=DashboardList, operation_id="listDashboards")
async def list_dashboards(
    request: Request,
    category: DashboardCategory | None = Query(None, description="Filter by category"),
    tag: str | None = Query(None, description="Filter by tag"),
    ws: Any = Depends(get_workspace_client_optional),
) -> DashboardList:
    """
    List all available AI/BI dashboards.
    
    Returns metadata for all dashboards with optional filtering by category or tag.
    On the first call, runs auto-discovery of dashboard IDs from the workspace API
    using the app's service principal (Lakeview API is not available via user OBO
    tokens — the 'dashboards' scope is not a valid user_api_scope for Apps).
    """
    if not _discovery_done:
        _discover_dashboard_ids(ws=None)

    dashboards = _get_dashboards()
    filtered_dashboards = dashboards
    
    # Apply category filter
    if category:
        filtered_dashboards = [d for d in filtered_dashboards if d.category == category]
    
    # Apply tag filter
    if tag:
        filtered_dashboards = [d for d in filtered_dashboards if tag.lower() in [t.lower() for t in d.tags]]
    
    # Calculate category counts
    category_counts = {}
    for dashboard in dashboards:
        cat = dashboard.category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    return DashboardList(
        dashboards=filtered_dashboards,
        total=len(filtered_dashboards),
        categories=category_counts,
    )


@router.get("/categories/list", response_model=dict[str, Any], operation_id="listDashboardCategories")
async def list_categories() -> dict[str, Any]:
    """
    List all dashboard categories with counts.
    
    Returns:
        Dictionary mapping categories to dashboard counts
    """
    dashboards = _get_dashboards()
    category_info = {}
    
    for category in DashboardCategory:
        dashboards_in_category = [d for d in dashboards if d.category == category]
        category_info[category.value] = {
            "name": category.value.replace("_", " ").title(),
            "count": len(dashboards_in_category),
            "dashboards": [d.id for d in dashboards_in_category],
        }
    
    return {
        "categories": category_info,
        "total_dashboards": len(dashboards),
    }


@router.get("/tags/list", response_model=dict[str, Any], operation_id="listDashboardTags")
async def list_tags() -> dict[str, Any]:
    """
    List all dashboard tags with counts.
    
    Returns:
        Dictionary of tags and how many dashboards have each tag
    """
    dashboards = _get_dashboards()
    tag_counts: dict[str, int] = {}
    
    for dashboard in dashboards:
        for tag in dashboard.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Sort by count descending
    sorted_tags = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))
    
    return {
        "tags": sorted_tags,
        "total_tags": len(sorted_tags),
    }


@router.get("/{dashboard_id}", response_model=DashboardInfo, operation_id="getDashboard")
async def get_dashboard(dashboard_id: str) -> DashboardInfo:
    """
    Get metadata for a specific dashboard.
    
    Args:
        dashboard_id: Unique dashboard identifier
        
    Returns:
        Dashboard metadata including embed URL
        
    Raises:
        HTTPException: If dashboard not found
    """
    dashboards = _get_dashboards()
    for dashboard in dashboards:
        if dashboard.id == dashboard_id:
            return dashboard
    
    raise HTTPException(
        status_code=404,
        detail=f"Dashboard '{dashboard_id}' not found",
    )


def _resolve_workspace_id(config: Any) -> str:
    """Workspace ID for ?o= query param. Tries config, then reference, then derives from host."""
    wid = getattr(config.databricks, "workspace_id", None) or ""
    if wid:
        return wid
    raw_host = (getattr(config.databricks, "workspace_url", "") or "").strip().rstrip("/")
    if raw_host and REFERENCE_WORKSPACE_HOST.rstrip("/") == ensure_absolute_workspace_url(raw_host).rstrip("/"):
        return REFERENCE_WORKSPACE_ID
    # Derive from Azure host: adb-<workspace_id>.<region>.azuredatabricks.net
    return workspace_id_from_workspace_url(raw_host) or ""


@router.get("/{dashboard_id}/url", response_model=dict[str, Any], operation_id="getDashboardUrl")
async def get_dashboard_url(
    dashboard_id: str,
    config: ConfigDep,
    workspace_host: EffectiveWorkspaceUrlDep,
    embed: bool = Query(False, description="Return embed-friendly URL"),
) -> dict[str, Any]:
    """
    Get the Lakeview dashboard URL for embedding or opening in a new tab.
    All dashboards use the /dashboardsv3/<id>/published format.
    The ?o=<workspace_id> param is appended for context; &embed=true for iframe mode.
    """
    dashboard = await get_dashboard(dashboard_id)
    base_path = dashboard.url_path or ""
    workspace_id = _resolve_workspace_id(config)

    # Build path with ?o=<workspace_id> for workspace context
    if workspace_id and "?" not in base_path:
        url_path = f"{base_path}?o={workspace_id}"
    elif workspace_id:
        url_path = f"{base_path}&o={workspace_id}"
    else:
        url_path = base_path

    full_url = f"{workspace_host}{url_path}" if workspace_host else None

    if embed:
        # Use /embed/ prefix path — Databricks requires this to relax
        # X-Frame-Options / CSP frame-ancestors so iframes from external
        # domains (*.databricksapps.com) are allowed.
        # Extract dashboard ID from url_path to build the embed variant.
        dashboard_lakeview_id = ""
        for d_id_var in [_DASHBOARD_ID_DATA_QUALITY, _DASHBOARD_ID_ML_OPTIMIZATION, _DASHBOARD_ID_EXECUTIVE_TRENDS]:
            if d_id_var and d_id_var in base_path:
                dashboard_lakeview_id = d_id_var
                break
        if dashboard_lakeview_id:
            embed_base = _lakeview_embed_path(dashboard_lakeview_id)
        else:
            # Fallback: replace /dashboardsv3/ with /embed/dashboardsv3/
            embed_base = base_path.replace("/dashboardsv3/", "/embed/dashboardsv3/", 1)

        if workspace_id:
            embed_path = f"{embed_base}?o={workspace_id}"
        else:
            embed_path = embed_base
        full_embed_url = f"{workspace_host}{embed_path}" if workspace_host else None
        return {
            "dashboard_id": dashboard_id,
            "url": url_path,
            "full_url": full_url,
            "embed_url": embed_path,
            "full_embed_url": full_embed_url,
            "embed": True,
            "instructions": "Use full_embed_url in an iframe. Requires workspace admin to enable 'Allow embedding dashboards' in Settings → Security.",
        }

    return {
        "dashboard_id": dashboard_id,
        "url": url_path,
        "full_url": full_url,
        "embed": False,
    }


# =============================================================================
# Native Dashboard Data (SQL-powered in-app rendering)
# =============================================================================
# Reads dashboard JSON definitions, executes SQL queries against the warehouse,
# and returns results + widget metadata so the frontend can render charts natively.

import json as _json
from pathlib import Path as _Path

from ..config import get_default_schema

_DASHBOARDS_DIR = _Path(__file__).resolve().parent.parent.parent.parent.parent / "resources" / "dashboards"
_CATALOG_PLACEHOLDER = "__CATALOG__.__SCHEMA__"


class DatasetResult(BaseModel):
    """Result of executing a single dashboard dataset query."""
    name: str
    display_name: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class WidgetSpec(BaseModel):
    """Widget rendering specification extracted from dashboard JSON."""
    dataset_name: str
    widget_type: str
    title: str = ""
    encodings: dict[str, Any] = Field(default_factory=dict)
class DashboardDataOut(BaseModel):
    """Full dashboard data for native in-app rendering."""
    dashboard_id: str
    dashboard_name: str
    datasets: list[DatasetResult]
    widgets: list[WidgetSpec]


def _load_dashboard_json(dashboard_id: str) -> dict[str, Any] | None:
    """Load a dashboard JSON file from resources/dashboards/."""
    path = _DASHBOARDS_DIR / f"{dashboard_id}.lvdash.json"
    if not path.exists():
        return None
    try:
        return _json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_widgets(data: dict[str, Any]) -> list[WidgetSpec]:
    """Extract widget specs from dashboard JSON for frontend chart rendering."""
    widgets: list[WidgetSpec] = []
    for page in data.get("pages", []):
        for item in page.get("layout", []):
            w = item.get("widget", {})
            spec = w.get("spec", {})
            widget_type = spec.get("widgetType", "table")
            queries = w.get("queries", [])
            dataset_name = ""
            for q in queries:
                qq = q.get("query", {})
                if qq.get("datasetName"):
                    dataset_name = qq["datasetName"]
                    break
            if not dataset_name:
                continue
            widgets.append(WidgetSpec(
                dataset_name=dataset_name,
                widget_type=widget_type,
                title=w.get("name", ""),
                encodings=spec.get("encodings", {}),
            ))
    return widgets


@router.get("/{dashboard_id}/data", response_model=DashboardDataOut, operation_id="getDashboardData")
async def get_dashboard_data(
    dashboard_id: str,
    svc: DatabricksServiceDep,
) -> DashboardDataOut:
    """Execute all SQL queries for a dashboard and return data for native rendering.

    Reads the dashboard JSON definition, replaces catalog/schema placeholders,
    executes each dataset query against the SQL warehouse, and returns
    results with widget metadata so the frontend can render charts natively.
    """
    data = _load_dashboard_json(dashboard_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' JSON not found")

    dashboard_info = next((d for d in _DASHBOARDS_STATIC if d.id == dashboard_id), None)
    dashboard_name = dashboard_info.name if dashboard_info else dashboard_id

    catalog = os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog")
    schema = get_default_schema()
    catalog_schema = f"{catalog}.{schema}"

    datasets_raw = data.get("datasets", [])
    results: list[DatasetResult] = []

    for ds in datasets_raw:
        name = ds.get("name", "")
        display_name = ds.get("displayName", name)
        # Support both Lakeview formats: "query" (string) and "queryLines" (array)
        raw_query = ds.get("query") or ""
        if not raw_query:
            query_lines = ds.get("queryLines", [])
            raw_query = query_lines[0] if query_lines else ""
        if not raw_query:
            results.append(DatasetResult(name=name, display_name=display_name, error="No query defined"))
            continue

        sql = raw_query.replace(_CATALOG_PLACEHOLDER, catalog_schema)
        try:
            rows = await svc._execute_query_internal(sql)
            columns = list(rows[0].keys()) if rows else []
            results.append(DatasetResult(name=name, display_name=display_name, columns=columns, rows=rows))
        except Exception as exc:
            _log.warning("Dashboard query failed for %s.%s: %s", dashboard_id, name, exc)
            results.append(DatasetResult(name=name, display_name=display_name, error=str(exc)))

    widgets = _extract_widgets(data)

    return DashboardDataOut(
        dashboard_id=dashboard_id,
        dashboard_name=dashboard_name,
        datasets=results,
        widgets=widgets,
    )
