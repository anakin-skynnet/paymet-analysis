#!/usr/bin/env python3
"""
Toggle app resource includes and serving endpoint bindings for two-phase deploy.

Usage:
  uv run python scripts/toggle_app_resources.py --enable-serving-endpoints   # Uncomment serving blocks in fastapi_app.yml
  uv run python scripts/toggle_app_resources.py --disable-serving-endpoints # Comment serving blocks
  uv run python scripts/toggle_app_resources.py --check-app-deployable     # Validate app can be deployed (deps + resources)
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATABRICKS_YML = REPO_ROOT / "databricks.yml"
FASTAPI_APP_YML = REPO_ROOT / "resources" / "fastapi_app.yml"
MODEL_SERVING_YML = REPO_ROOT / "resources" / "model_serving.yml"


def _serving_block_lines() -> list[tuple[str, str]]:
    """Pairs of (commented, uncommented) line patterns for the 7 serving endpoint blocks."""
    # (resource name, endpoint name in YAML)
    names = [
        ("serving-orchestrator", "payment-analysis-orchestrator"),
        ("serving-response-agent", "payment-response-agent"),
        ("serving-decline-analyst", "decline-analyst"),
        ("serving-approval-prop", "approval-propensity"),
        ("serving-risk-scoring", "risk-scoring"),
        ("serving-smart-routing", "smart-routing"),
        ("serving-smart-retry", "smart-retry"),
    ]
    pairs = []
    for name, endpoint in names:
        pairs.append((f"        # - name: {name}", f"        - name: {name}"))
        pairs.append((f'        #   serving_endpoint: {{ name: "{endpoint}", permission: CAN_QUERY }}', f'          serving_endpoint: {{ name: "{endpoint}", permission: CAN_QUERY }}'))
    return pairs


def enable_serving_endpoints() -> bool:
    """Uncomment the 7 model serving endpoint blocks in resources/fastapi_app.yml."""
    text = FASTAPI_APP_YML.read_text()
    for commented, uncommented in _serving_block_lines():
        if commented in text:
            text = text.replace(commented, uncommented, 1)
    FASTAPI_APP_YML.write_text(text)
    return True


def disable_serving_endpoints() -> bool:
    """Comment the 7 model serving endpoint blocks in resources/fastapi_app.yml."""
    text = FASTAPI_APP_YML.read_text()
    for commented, uncommented in _serving_block_lines():
        if uncommented in text:
            text = text.replace(uncommented, commented, 1)
    FASTAPI_APP_YML.write_text(text)
    return True


def check_app_deployable() -> tuple[bool, list[str]]:
    """
    Validate that the app can be deployed with all dependencies and resources.
    Returns (ok, list of messages).
    """
    messages = []
    ok = True

    if not FASTAPI_APP_YML.exists():
        messages.append(f"Missing {FASTAPI_APP_YML.relative_to(REPO_ROOT)}")
        ok = False
    else:
        messages.append(f"Found {FASTAPI_APP_YML.name}")

    if not MODEL_SERVING_YML.exists():
        messages.append(f"Missing {MODEL_SERVING_YML.relative_to(REPO_ROOT)}")
        ok = False
    else:
        messages.append(f"Found {MODEL_SERVING_YML.name}")

    if not DATABRICKS_YML.exists():
        messages.append(f"Missing {DATABRICKS_YML.name}")
        ok = False
    else:
        content = DATABRICKS_YML.read_text()
        if "resources/model_serving.yml" in content and not re.search(r"^\s*#\s*-\s*resources/model_serving\.yml", content, re.M):
            messages.append("model_serving.yml is included in databricks.yml (uncommented)")
        else:
            messages.append("model_serving.yml is commented in databricks.yml (will be uncommented for deploy app)")

        if "resources/fastapi_app.yml" in content and not re.search(r"^\s*#\s*-\s*resources/fastapi_app\.yml", content, re.M):
            messages.append("fastapi_app.yml is included in databricks.yml (uncommented)")
        else:
            messages.append("fastapi_app.yml is commented in databricks.yml (excluded in phase 1)")

    app_content = FASTAPI_APP_YML.read_text() if FASTAPI_APP_YML.exists() else ""
    if "serving-endpoint" in app_content or "serving_endpoint" in app_content:
        if re.search(r"^\s*-\s+name:\s+serving-", app_content, re.M):
            messages.append("Serving endpoint bindings are uncommented in fastapi_app.yml")
        else:
            messages.append("Serving endpoint bindings are commented in fastapi_app.yml (will be uncommented for deploy app)")

    return ok, messages


def main() -> None:
    parser = argparse.ArgumentParser(description="Toggle app resources for two-phase deploy")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable-serving-endpoints", action="store_true", help="Uncomment serving endpoint blocks in fastapi_app.yml")
    group.add_argument("--disable-serving-endpoints", action="store_true", help="Comment serving endpoint blocks in fastapi_app.yml")
    group.add_argument("--check-app-deployable", action="store_true", help="Validate app can be deployed with all dependencies and resources")
    args = parser.parse_args()

    if args.enable_serving_endpoints:
        enable_serving_endpoints()
        print("Serving endpoint bindings enabled in resources/fastapi_app.yml")
    elif args.disable_serving_endpoints:
        disable_serving_endpoints()
        print("Serving endpoint bindings disabled in resources/fastapi_app.yml")
    elif args.check_app_deployable:
        ok, messages = check_app_deployable()
        for m in messages:
            print(m)
        if not ok:
            raise SystemExit(1)
        print("App is deployable with all dependencies and resources when model_serving and serving blocks are uncommented.")


if __name__ == "__main__":
    main()
