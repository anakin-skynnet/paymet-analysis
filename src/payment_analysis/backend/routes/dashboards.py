"""
Dashboard Router - AI/BI Dashboard Integration.

This module provides endpoints for accessing all Databricks AI/BI dashboards
embedded in the FastAPI application.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import (
    REFERENCE_WORKSPACE_HOST,
    REFERENCE_WORKSPACE_ID,
    ensure_absolute_workspace_url,
    workspace_id_from_workspace_url,
)
from ..dependencies import ConfigDep, EffectiveWorkspaceUrlDep

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

# Lakeview dashboard IDs — set in app env or default to the deployed IDs.
_DASHBOARD_ID_DATA_QUALITY = os.getenv(
    "DASHBOARD_ID_DATA_QUALITY", "01f1090059311b079903b08b73dc03d8"
)
_DASHBOARD_ID_ML_OPTIMIZATION = os.getenv(
    "DASHBOARD_ID_ML_OPTIMIZATION", "01f10900593c19f19eaa6453cb1af0d8"
)
_DASHBOARD_ID_EXECUTIVE_TRENDS = os.getenv(
    "DASHBOARD_ID_EXECUTIVE_TRENDS", "01f10900592f18cb82d7a57547ac57ca"
)


def _lakeview_url_path(dashboard_id: str) -> str:
    """Lakeview published dashboard URL path (append ?embed=true for iframe)."""
    return f"/dashboardsv3/{dashboard_id}/published"


DASHBOARDS = [
    DashboardInfo(
        id="data_quality_unified",
        name="Data & Quality",
        description="Stream ingestion volume, data quality, real-time monitoring, active alerts, and global coverage by country. Single dashboard for data health and operational monitoring.",
        category=DashboardCategory.TECHNICAL,
        tags=["streaming", "ingestion", "data-quality", "realtime", "alerts", "countries", "geography"],
        url_path=_lakeview_url_path(_DASHBOARD_ID_DATA_QUALITY),
    ),
    DashboardInfo(
        id="ml_optimization_unified",
        name="ML & Optimization",
        description="Smart routing, decline analysis & recovery, fraud/risk, 3DS authentication, and financial impact. Predictions, smart retry impact, smart checkout behavior.",
        category=DashboardCategory.ANALYTICS,
        tags=["routing", "decline", "recovery", "fraud", "risk", "3ds", "smart-checkout", "smart-retry", "roi"],
        url_path=_lakeview_url_path(_DASHBOARD_ID_ML_OPTIMIZATION),
    ),
    DashboardInfo(
        id="executive_trends_unified",
        name="Executive & Trends",
        description="KPIs, approval rates, daily trends, merchant performance, and technical performance. For business users to analyze and understand approval rates.",
        category=DashboardCategory.EXECUTIVE,
        tags=["kpi", "approval-rate", "trends", "merchant", "performance", "executive"],
        url_path=_lakeview_url_path(_DASHBOARD_ID_EXECUTIVE_TRENDS),
    ),
]


# =============================================================================
# Endpoints (mounted at /api/dashboards in router.py)
# =============================================================================

@router.get("", response_model=DashboardList, operation_id="listDashboards")
async def list_dashboards(
    category: DashboardCategory | None = Query(None, description="Filter by category"),
    tag: str | None = Query(None, description="Filter by tag"),
) -> DashboardList:
    """
    List all available AI/BI dashboards.
    
    Returns metadata for all dashboards with optional filtering by category or tag.
    """
    filtered_dashboards = DASHBOARDS
    
    # Apply category filter
    if category:
        filtered_dashboards = [d for d in filtered_dashboards if d.category == category]
    
    # Apply tag filter
    if tag:
        filtered_dashboards = [d for d in filtered_dashboards if tag.lower() in [t.lower() for t in d.tags]]
    
    # Calculate category counts
    category_counts = {}
    for dashboard in DASHBOARDS:
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
    category_info = {}
    
    for category in DashboardCategory:
        dashboards_in_category = [d for d in DASHBOARDS if d.category == category]
        category_info[category.value] = {
            "name": category.value.replace("_", " ").title(),
            "count": len(dashboards_in_category),
            "dashboards": [d.id for d in dashboards_in_category],
        }
    
    return {
        "categories": category_info,
        "total_dashboards": len(DASHBOARDS),
    }


@router.get("/tags/list", response_model=dict[str, Any], operation_id="listDashboardTags")
async def list_tags() -> dict[str, Any]:
    """
    List all dashboard tags with counts.
    
    Returns:
        Dictionary of tags and how many dashboards have each tag
    """
    tag_counts = {}
    
    for dashboard in DASHBOARDS:
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
    for dashboard in DASHBOARDS:
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
        sep = "&" if "?" in url_path else "?"
        embed_path = f"{url_path}{sep}embed=true"
        full_embed_url = f"{workspace_host}{embed_path}" if workspace_host else None
        return {
            "dashboard_id": dashboard_id,
            "url": url_path,
            "full_url": full_url,
            "embed_url": embed_path,
            "full_embed_url": full_embed_url,
            "embed": True,
            "instructions": "Use full_embed_url in an iframe. Requires workspace admin to enable 'Allow embedding dashboards'.",
        }

    return {
        "dashboard_id": dashboard_id,
        "url": url_path,
        "full_url": full_url,
        "embed": False,
    }


