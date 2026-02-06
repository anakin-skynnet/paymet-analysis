#!/usr/bin/env bash
# Ensure .build/dashboards and .build/transform exist so bundle validate/deploy/run do not fail
# with "failed to read serialized dashboard from file_path .build/dashboards/...."
# Usage: ./scripts/ensure_dashboards.sh [target]
#   target: dev (default) or prod
set -e
cd "$(dirname "$0")/.."
TARGET="${1:-dev}"
BUILD_DASH="$PWD/.build/dashboards"
if [[ ! -d "$BUILD_DASH" ]] || [[ -z "$(ls -A "$BUILD_DASH"/*.lvdash.json 2>/dev/null)" ]]; then
  echo "Creating .build/dashboards (required for bundle)..."
  if [[ "$TARGET" == "prod" ]]; then
    uv run python scripts/prepare_dashboards.py --catalog prod_catalog --schema ahs_demo_payment_analysis_prod
  else
    uv run python scripts/prepare_dashboards.py
  fi
else
  echo ".build/dashboards already exists."
fi
