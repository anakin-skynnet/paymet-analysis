"""
Isolated code handler for healthcheck (Databricks Apps Cookbook).
Implementation: src/payment_analysis/backend/routes/v1/healthcheck.py.
Exposes GET /api/v1/healthcheck.
"""
from payment_analysis.backend.routes.v1.healthcheck import router

__all__ = ["router"]
