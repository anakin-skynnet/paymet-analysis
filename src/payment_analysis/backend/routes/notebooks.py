"""
Notebook Registry - Maps UI sections to Databricks notebooks.

This module provides a centralized registry of all Databricks notebooks
used in the payment analysis platform, organized by functional area.

NOTE: Workspace paths are relative to the bundle deployment location.
They will be constructed dynamically based on the actual deployment path.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import (
    AppConfig,
    WORKSPACE_URL_PLACEHOLDER,
    app_name,
    ensure_absolute_workspace_url,
    workspace_url_from_apps_host,
)
from ..dependencies import ConfigDep, _request_host_for_derivation

router = APIRouter(tags=["notebooks"])

_databricks_config = AppConfig().databricks


def _workspace_base_url_for_request(request: Request, config: AppConfig) -> str:
    """Return absolute Databricks workspace base URL for links (notebooks, folders). Same logic as GET /api/config/workspace."""
    raw = (config.databricks.workspace_url or "").strip().rstrip("/")
    if not raw or raw.rstrip("/") == WORKSPACE_URL_PLACEHOLDER.rstrip("/"):
        host_header = _request_host_for_derivation(request)
        raw = workspace_url_from_apps_host(host_header, app_name).strip().rstrip("/")
    if not raw or "databricksapps" in raw.lower():
        return ""
    return ensure_absolute_workspace_url(raw).rstrip("/")


# =============================================================================
# Helper Functions
# =============================================================================

def get_workspace_base_path() -> str:
    """
    Get the workspace base path dynamically from environment or use default.
    
    The actual path is set during bundle deployment and available via:
    - DATABRICKS_BUNDLE_ROOT environment variable
    - Or falls back to pattern-based path
    """
    bundle_root = os.getenv("DATABRICKS_BUNDLE_ROOT")
    if bundle_root:
        return bundle_root
    
    # Fallback: construct from user email and folder name
    user_email = os.getenv("DATABRICKS_USER", "user@company.com")
    folder_name = os.getenv("BUNDLE_FOLDER", "payment-analysis")
    return f"/Workspace/Users/{user_email}/{folder_name}/files"


def get_notebook_path(relative_path: str) -> str:
    """Construct full notebook path from relative path."""
    base = get_workspace_base_path()
    return f"{base}/{relative_path}"


# =============================================================================
# Models
# =============================================================================

class NotebookCategory(str, Enum):
    """Notebook categories."""
    INTELLIGENCE = "intelligence"
    ML_TRAINING = "ml_training"
    STREAMING = "streaming"
    TRANSFORMATION = "transformation"
    ANALYTICS = "analytics"


class NotebookInfo(BaseModel):
    """Notebook metadata model."""
    id: str = Field(..., description="Unique notebook identifier")
    name: str = Field(..., description="Notebook display name")
    description: str = Field(..., description="Notebook purpose and functionality")
    category: NotebookCategory = Field(..., description="Functional category")
    workspace_path: str = Field(..., description="Databricks workspace path")
    job_name: str | None = Field(None, description="Associated job name if scheduled")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    documentation_url: str | None = Field(None, description="Link to documentation")


class NotebookList(BaseModel):
    """List of notebooks."""
    notebooks: list[NotebookInfo]
    total: int
    by_category: dict[str, int]


# =============================================================================
# Notebook Registry
# =============================================================================

NOTEBOOKS = [
    # AI Agents
    NotebookInfo(
        id="agent_framework",
        name="Intelligence Results Framework",
        description="SQL-based intelligent decisioning system for smart routing, retry optimization, decline analysis, risk assessment, and performance recommendations.",
        category=NotebookCategory.INTELLIGENCE,
        workspace_path=get_notebook_path("src/payment_analysis/agents/agent_framework.py"),
        job_name="Smart Routing, Smart Retry, Decline Analysis, Risk Assessment, Performance Recommendations",
        tags=["intelligence", "decisioning", "routing", "retry", "analysis"],
    ),
    
    # ML Training
    NotebookInfo(
        id="train_models",
        name="ML Model Training",
        description="Trains all 4 ML models: approval propensity, risk scoring, smart routing policy, and smart retry policy with MLflow tracking.",
        category=NotebookCategory.ML_TRAINING,
        workspace_path=get_notebook_path("src/payment_analysis/ml/train_models.py"),
        job_name="Train Payment Approval ML Models",
        tags=["ml", "training", "mlflow", "models", "propensity", "risk"],
    ),
    
    # Streaming & Ingestion
    NotebookInfo(
        id="transaction_simulator",
        name="Transaction Stream Simulator",
        description="Generates realistic synthetic payment transaction events for testing and demonstration purposes.",
        category=NotebookCategory.STREAMING,
        workspace_path=get_notebook_path("src/payment_analysis/streaming/transaction_simulator.py"),
        job_name="Payment Transaction Stream Simulator",
        tags=["streaming", "simulator", "synthetic-data", "testing"],
    ),
    NotebookInfo(
        id="bronze_ingest",
        name="Bronze Layer Ingestion",
        description="Lakeflow for ingesting raw payment events into the bronze layer with data quality checks.",
        category=NotebookCategory.STREAMING,
        workspace_path=get_notebook_path("src/payment_analysis/streaming/bronze_ingest.py"),
        job_name="Payment Analysis Lakeflow",
        tags=["lakeflow", "bronze", "ingestion", "data-quality"],
    ),
    NotebookInfo(
        id="realtime_pipeline",
        name="Real-Time Streaming Pipeline",
        description="Lakeflow continuous streaming pipeline for real-time payment processing (Bronze → Silver → Gold).",
        category=NotebookCategory.STREAMING,
        workspace_path=get_notebook_path("src/payment_analysis/streaming/realtime_pipeline.py"),
        job_name="Payment Analysis Lakeflow",
        tags=["lakeflow", "streaming", "realtime", "cdc", "continuous"],
    ),
    NotebookInfo(
        id="continuous_processor",
        name="Continuous Stream Processor",
        description="Structured streaming processor for continuous payment event processing with windowed aggregations.",
        category=NotebookCategory.STREAMING,
        workspace_path=get_notebook_path("src/payment_analysis/streaming/continuous_processor.py"),
        job_name=None,
        tags=["streaming", "continuous", "aggregations", "windows"],
    ),
    
    # Transformations
    NotebookInfo(
        id="silver_transform",
        name="Silver Layer Transformations",
        description="Lakeflow transformations for cleaning, enriching, and validating payment data in the silver layer.",
        category=NotebookCategory.TRANSFORMATION,
        workspace_path=get_notebook_path("src/payment_analysis/transform/silver_transform.py"),
        job_name="Payment Analysis Lakeflow",
        tags=["lakeflow", "silver", "transformation", "enrichment", "validation"],
    ),
    NotebookInfo(
        id="gold_views",
        name="Gold Analytics Views",
        description="Creates aggregated gold-layer views optimized for dashboards and analytics (12+ views including KPIs, trends, and performance metrics).",
        category=NotebookCategory.TRANSFORMATION,
        workspace_path=get_notebook_path("src/payment_analysis/transform/gold_views.py"),
        job_name="Create Payment Analysis Gold Views",
        tags=["lakeflow", "gold", "views", "aggregations", "analytics"],
    ),
    NotebookInfo(
        id="gold_views_sql",
        name="Gold Views SQL Definitions",
        description="SQL definitions for dashboard, Genie & agent gold views (v_executive_kpis, v_top_decline_reasons, v_solution_performance, etc.).",
        category=NotebookCategory.TRANSFORMATION,
        workspace_path=get_notebook_path("src/payment_analysis/transform/gold_views.sql"),
        job_name="Create Payment Analysis Gold Views",
        tags=["sql", "gold", "views", "definitions"],
    ),
]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/notebooks", response_model=NotebookList, operation_id="listNotebooks")
async def list_notebooks(
    category: NotebookCategory | None = None,
) -> NotebookList:
    """
    List all Databricks notebooks in the payment analysis platform.
    
    Args:
        category: Optional filter by category
        
    Returns:
        List of notebooks with metadata
    """
    filtered = NOTEBOOKS
    
    if category:
        filtered = [n for n in filtered if n.category == category]
    
    # Count by category
    by_category = {}
    for notebook in NOTEBOOKS:
        cat = notebook.category.value
        by_category[cat] = by_category.get(cat, 0) + 1
    
    return NotebookList(
        notebooks=filtered,
        total=len(filtered),
        by_category=by_category,
    )


@router.get("/notebooks/{notebook_id}", response_model=NotebookInfo, operation_id="getNotebook")
async def get_notebook(notebook_id: str) -> NotebookInfo:
    """Get details for a specific notebook."""
    for notebook in NOTEBOOKS:
        if notebook.id == notebook_id:
            return notebook
    
    raise HTTPException(status_code=404, detail=f"Notebook '{notebook_id}' not found")


class NotebookUrlOut(BaseModel):
    notebook_id: str
    name: str
    url: str
    workspace_path: str
    category: str


@router.get("/notebooks/{notebook_id}/url", response_model=NotebookUrlOut, operation_id="getNotebookUrl")
async def get_notebook_url(
    notebook_id: str,
    request: Request,
    config: ConfigDep,
) -> NotebookUrlOut:
    """Return absolute Databricks workspace URL for the notebook (opens in workspace)."""
    notebook = await get_notebook(notebook_id)
    base_url = _workspace_base_url_for_request(request, config)
    workspace_path = notebook.workspace_path
    full_url = f"{base_url}/workspace{workspace_path}" if base_url else ""
    return NotebookUrlOut(
        notebook_id=notebook_id,
        name=notebook.name,
        url=full_url,
        workspace_path=workspace_path,
        category=notebook.category.value,
    )


# Workspace folder IDs to relative paths (under src/payment_analysis/)
WORKSPACE_FOLDERS: dict[str, str] = {
    "ml": "src/payment_analysis/ml",
    "streaming": "src/payment_analysis/streaming",
    "transform": "src/payment_analysis/transform",
    "agents": "src/payment_analysis/agents",
    "genie": "src/payment_analysis/genie",
}


class FolderUrlOut(BaseModel):
    folder_id: str
    url: str
    workspace_path: str


@router.get("/notebooks/folders/{folder_id}/url", response_model=FolderUrlOut, operation_id="getNotebookFolderUrl")
async def get_folder_url(
    folder_id: str,
    request: Request,
    config: ConfigDep,
) -> FolderUrlOut:
    """Return absolute Databricks workspace URL for the folder (opens in workspace)."""
    if folder_id not in WORKSPACE_FOLDERS:
        raise HTTPException(
            status_code=404,
            detail=f"Folder '{folder_id}' not found. Valid: {list(WORKSPACE_FOLDERS.keys())}",
        )
    relative = WORKSPACE_FOLDERS[folder_id]
    workspace_path = get_notebook_path(relative)
    base_url = _workspace_base_url_for_request(request, config)
    full_url = f"{base_url}/workspace{workspace_path}" if base_url else ""
    return FolderUrlOut(
        folder_id=folder_id,
        url=full_url,
        workspace_path=workspace_path,
    )


@router.get("/notebooks/categories/summary", response_model=dict[str, Any], operation_id="getNotebookCategorySummary")
async def get_category_summary() -> dict[str, Any]:
    """
    Get summary of notebooks by category with descriptions.
    
    Returns counts and notebook lists for each category.
    """
    summary = {}
    
    for category in NotebookCategory:
        notebooks_in_cat = [n for n in NOTEBOOKS if n.category == category]
        summary[category.value] = {
            "name": category.value.replace("_", " ").title(),
            "count": len(notebooks_in_cat),
            "notebooks": [
                {
                    "id": n.id,
                    "name": n.name,
                    "job_name": n.job_name,
                }
                for n in notebooks_in_cat
            ],
        }
    
    return {
        "categories": summary,
        "total_notebooks": len(NOTEBOOKS),
    }
