"""Entrypoint for uvicorn app:app (PYTHONPATH=src). Re-exports payment_analysis.backend.app."""
from payment_analysis.backend.app import app

__all__ = ["app"]
