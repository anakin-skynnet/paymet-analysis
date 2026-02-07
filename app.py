"""
Main FastAPI application entrypoint (Databricks Apps Cookbook).
Uses package app; run with: uvicorn app:app (PYTHONPATH=src) or
uvicorn payment_analysis.backend.app:app (PYTHONPATH=src).
"""
from payment_analysis.backend.app import app

__all__ = ["app"]
