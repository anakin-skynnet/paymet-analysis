"""
Dashboard Router - AI/BI Dashboard Integration.

This module provides endpoints for accessing all Databricks AI/BI dashboards
embedded in the FastAPI application.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import (
    REFERENCE_LAKEVIEW_DASHBOARD_ID_EXECUTIVE,
    REFERENCE_WORKSPACE_HOST,
    REFERENCE_WORKSPACE_ID,
    ensure_absolute_workspace_url,
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
# Dashboard Registry (Databricks AI/BI Dashboards)
# =============================================================================
# Unified multi-visual dashboards for approval-rate analysis (see MERGE_GROUPS
# in scripts/dashboards.py). Run "merge" then "prepare"; bundle deploys these three.
# =============================================================================

DASHBOARDS = [
    DashboardInfo(
        id="data_quality_unified",
        name="Data & Quality",
        description="Stream ingestion volume, data quality, real-time monitoring, active alerts, and global coverage by country. Single dashboard for data health and operational monitoring.",
        category=DashboardCategory.TECHNICAL,
        tags=["streaming", "ingestion", "data-quality", "realtime", "alerts", "countries", "geography"],
        url_path="/sql/dashboards/data_quality_unified",
    ),
    DashboardInfo(
        id="ml_optimization_unified",
        name="ML & Optimization",
        description="Smart routing, decline analysis & recovery, fraud/risk, 3DS authentication, and financial impact. Predictions, smart retry impact, smart checkout behavior.",
        category=DashboardCategory.ANALYTICS,
        tags=["routing", "decline", "recovery", "fraud", "risk", "3ds", "smart-checkout", "smart-retry", "roi"],
        url_path="/sql/dashboards/ml_optimization_unified",
    ),
    DashboardInfo(
        id="executive_trends_unified",
        name="Executive & Trends",
        description="KPIs, approval rates, daily trends, merchant performance, and technical performance. For business users to analyze and understand approval rates.",
        category=DashboardCategory.EXECUTIVE,
        tags=["kpi", "approval-rate", "trends", "merchant", "performance", "executive"],
        url_path="/sql/dashboards/executive_trends_unified",
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


def _dashboard_url_path_and_full(
    dashboard_id: str,
    default_url_path: str,
    config: Any,
) -> tuple[str, str | None]:
    """
    Return (url_path, full_url) for a dashboard. When executive_trends_unified and a Lakeview
    reference ID is configured (or workspace matches reference), use dashboardsv3 published URL.
    Reference: https://adb-984752964297111.11.azuredatabricks.net/dashboardsv3/01efef6277e1146bb92982fc1364845d/published?o=984752964297111
    """
    lakeview_id = getattr(config.databricks, "lakeview_id_executive_overview", None) or (
        REFERENCE_LAKEVIEW_DASHBOARD_ID_EXECUTIVE if dashboard_id == "executive_trends_unified" else None
    )
    raw_host = (config.databricks.workspace_url or "").strip().rstrip("/")
    workspace_id = config.databricks.workspace_id
    if not workspace_id and raw_host and REFERENCE_WORKSPACE_HOST.rstrip("/") == ensure_absolute_workspace_url(raw_host).rstrip("/"):
        workspace_id = REFERENCE_WORKSPACE_ID
    if dashboard_id == "executive_trends_unified" and lakeview_id:
        path = f"/dashboardsv3/{lakeview_id}/published"
        if workspace_id:
            path = f"{path}?o={workspace_id}"
        full = None
        if raw_host and "example.databricks.com" not in raw_host:
            full = ensure_absolute_workspace_url(raw_host).rstrip("/") + path
        return path, full
    return default_url_path, None


@router.get("/{dashboard_id}/url", response_model=dict[str, Any], operation_id="getDashboardUrl")
async def get_dashboard_url(
    dashboard_id: str,
    config: ConfigDep,
    workspace_host: EffectiveWorkspaceUrlDep,
    embed: bool = Query(False, description="Return embed-friendly URL"),
) -> dict[str, Any]:
    """
    Get the Databricks URL for a specific dashboard.
    Uses the effective workspace URL (from request when opened from Apps) so end users
    get their own workspace, not a hardcoded host.
    """
    dashboard = await get_dashboard(dashboard_id)
    default_path = dashboard.url_path or ""
    base_url, _full_from_config = _dashboard_url_path_and_full(dashboard_id, default_path, config)
    # Use effective workspace host (request-derived when app opened from Apps) so end users get their workspace
    full_url = f"{workspace_host}{base_url}" if workspace_host else (_full_from_config or None)

    if embed:
        sep = "&" if "?" in base_url else "?"
        embed_path = f"{base_url}{sep}embed=true"
        full_embed_url = None
        if full_url:
            full_embed_url = f"{full_url}{sep}embed=true"
        elif workspace_host:
            full_embed_url = f"{workspace_host}{embed_path}"
        return {
            "dashboard_id": dashboard_id,
            "url": base_url,
            "full_url": full_url,
            "embed_url": embed_path,
            "full_embed_url": full_embed_url,
            "embed": True,
            "instructions": "Use full_embed_url in an iframe when set; otherwise use workspace URL + embed_url",
        }

    return {
        "dashboard_id": dashboard_id,
        "url": base_url,
        "full_url": full_url,
        "embed": False,
    }


