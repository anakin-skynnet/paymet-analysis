#!/usr/bin/env python3
"""Resolve the schema name for a bundle target.

Schema is always "payment_analysis" (no per-user prefix).
Usage: uv run python scripts/resolve_bundle_schema.py [target]
  target: dev (default) or prod
Prints the resolved schema name to stdout (e.g. payment_analysis).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Canonical schema name — same for all targets unless overridden in the bundle.
DEFAULT_SCHEMA = "payment_analysis"


def resolve_schema(target: str) -> str:
    """Resolve schema from bundle validate output, or fallback to default."""
    try:
        result = subprocess.run(
            ["databricks", "bundle", "validate", "-t", target, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            schema = (data.get("variables") or {}).get("schema") or {}
            if isinstance(schema, dict) and schema.get("value"):
                return schema["value"]
    except Exception:
        pass
    # Fallback: env var or default
    import os
    explicit = os.getenv("DATABRICKS_SCHEMA", "").strip()
    if explicit:
        return explicit
    return DEFAULT_SCHEMA


def main() -> int:
    target = (sys.argv[1:] or ["dev"])[0]
    print(resolve_schema(target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
