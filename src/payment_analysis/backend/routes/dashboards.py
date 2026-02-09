"""
Dashboard Router - AI/BI Dashboard Integration.

This module provides endpoints for accessing all Databricks AI/BI dashboards
embedded in the FastAPI application.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import ensure_absolute_workspace_url
from ..dependencies import ConfigDep

logger = logging.getLogger(__name__)

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
# These IDs and url_paths match the AI/BI dashboards deployed by the bundle
# (resources/dashboards.yml and resources/dashboards/*.lvdash.json). The app
# builds full URLs using config.databricks.workspace_url so the UI embeds and
# opens the actual dashboards in the Databricks workspace.
# =============================================================================

DASHBOARDS = [
    DashboardInfo(
        id="executive_overview",
        name="Executive Overview",
        description="High-level KPIs and trends for executives. Shows total transactions, approval rates, transaction value, and key performance metrics.",
        category=DashboardCategory.EXECUTIVE,
        tags=["kpi", "overview", "executive", "summary"],
        url_path="/sql/dashboards/executive_overview",
    ),
    DashboardInfo(
        id="decline_analysis",
        name="Decline Analysis & Recovery",
        description="Deep dive into decline patterns and recovery opportunities. Identifies top decline reasons, recovery potential, and retry strategies.",
        category=DashboardCategory.OPERATIONS,
        tags=["decline", "recovery", "analysis", "optimization"],
        url_path="/sql/dashboards/decline_analysis",
    ),
    DashboardInfo(
        id="realtime_monitoring",
        name="Real-Time Payment Monitoring",
        description="Live monitoring of payment system health and alerts. Shows last hour performance, active alerts, and real-time metrics.",
        category=DashboardCategory.OPERATIONS,
        tags=["realtime", "monitoring", "alerts", "health"],
        url_path="/sql/dashboards/realtime_monitoring",
    ),
    DashboardInfo(
        id="fraud_risk_analysis",
        name="Fraud & Risk Analysis",
        description="Comprehensive fraud detection and risk monitoring. Tracks fraud scores, AML risk, high-risk transactions, and security patterns.",
        category=DashboardCategory.ANALYTICS,
        tags=["fraud", "risk", "security", "aml"],
        url_path="/sql/dashboards/fraud_risk_analysis",
    ),
    DashboardInfo(
        id="merchant_performance",
        name="Merchant Performance & Segmentation",
        description="Detailed merchant performance metrics and segment analysis. Analyzes performance by merchant segment and geography.",
        category=DashboardCategory.ANALYTICS,
        tags=["merchant", "segment", "performance", "analytics"],
        url_path="/sql/dashboards/merchant_performance",
    ),
    DashboardInfo(
        id="routing_optimization",
        name="Smart Routing & Optimization",
        description="Payment routing performance and optimization recommendations. Compares payment solutions, networks, and retry strategies.",
        category=DashboardCategory.OPERATIONS,
        tags=["routing", "optimization", "smart-retry", "performance"],
        url_path="/sql/dashboards/routing_optimization",
    ),
    DashboardInfo(
        id="daily_trends",
        name="Daily Trends & Historical Analysis",
        description="Historical trends and day-over-day performance analysis. Shows 90-day trends in volume, approval rates, value, and fraud.",
        category=DashboardCategory.ANALYTICS,
        tags=["trends", "historical", "daily", "analytics"],
        url_path="/sql/dashboards/daily_trends",
    ),
    DashboardInfo(
        id="authentication_security",
        name="3DS Authentication & Security",
        description="Deep dive into 3D Secure authentication adoption and security compliance. Analyzes 3DS usage patterns and impact on approval rates.",
        category=DashboardCategory.ANALYTICS,
        tags=["3ds", "authentication", "security", "compliance"],
        url_path="/sql/dashboards/authentication_security",
    ),
    DashboardInfo(
        id="financial_impact",
        name="Financial Impact & ROI Analysis",
        description="Transaction value analysis, revenue impact, and ROI from optimization strategies. Quantifies financial impact and recovery potential.",
        category=DashboardCategory.EXECUTIVE,
        tags=["financial", "revenue", "roi", "value"],
        url_path="/sql/dashboards/financial_impact",
    ),
    DashboardInfo(
        id="performance_latency",
        name="Technical Performance & Latency",
        description="Processing time, latency metrics, and technical performance by solution and network. Monitors SLA compliance and performance trends.",
        category=DashboardCategory.TECHNICAL,
        tags=["performance", "latency", "technical", "sla"],
        url_path="/sql/dashboards/performance_latency",
    ),
    DashboardInfo(
        id="streaming_data_quality",
        name="Streaming & Data Quality",
        description="Incoming streaming data (bronze/silver), pipeline retention %, and Unity Catalog data quality metrics (freshness, completeness, downstream impact from system.data_quality_monitoring).",
        category=DashboardCategory.TECHNICAL,
        tags=["streaming", "ingestion", "data-quality", "bronze", "silver", "unity-catalog"],
        url_path="/sql/dashboards/streaming_data_quality",
    ),
    DashboardInfo(
        id="global_coverage",
        name="Global Coverage - World Map by Country",
        description="World map and metrics aggregated by country. Transaction volume, approval rates, and value across issuer countries.",
        category=DashboardCategory.ANALYTICS,
        tags=["geography", "world-map", "countries", "global", "analytics"],
        url_path="/sql/dashboards/global_coverage",
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


@router.get("/{dashboard_id}/url", response_model=dict[str, Any], operation_id="getDashboardUrl")
async def get_dashboard_url(
    dashboard_id: str,
    config: ConfigDep,
    embed: bool = Query(False, description="Return embed-friendly URL"),
) -> dict[str, Any]:
    """
    Get the Databricks URL for a specific dashboard.
    
    Args:
        dashboard_id: Unique dashboard identifier
        embed: If True, returns URL suitable for iframe embedding
        
    Returns:
        Dictionary with URL, embed_url (path), and full_embed_url (absolute URL for iframe)
        
    Raises:
        HTTPException: If dashboard not found
    """
    dashboard = await get_dashboard(dashboard_id)
    
    # Relative path; frontend can prepend workspace URL from config
    base_url = dashboard.url_path
    raw_host = (config.databricks.workspace_url or "").strip().rstrip("/")
    is_placeholder = not raw_host or "example.databricks.com" in raw_host
    workspace_host = ensure_absolute_workspace_url(raw_host) if raw_host else ""

    if embed:
        # Embed path: optional workspace ID (o=) from DATABRICKS_WORKSPACE_ID so embed works in any workspace
        embed_path = f"{base_url}?embed=true"
        if config.databricks.workspace_id:
            embed_path = f"{base_url}?o={config.databricks.workspace_id}&embed=true"
        full_embed_url = f"{workspace_host}{embed_path}" if workspace_host and not is_placeholder else None
        return {
            "dashboard_id": dashboard_id,
            "url": base_url,
            "embed_url": embed_path,
            "full_embed_url": full_embed_url,
            "embed": True,
            "instructions": "Use full_embed_url in an iframe when set; otherwise use workspace URL + embed_url",
        }

    return {
        "dashboard_id": dashboard_id,
        "url": base_url,
        "embed": False,
    }


