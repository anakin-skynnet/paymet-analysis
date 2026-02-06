#!/usr/bin/env bash
# Prepare dashboard JSONs (required for bundle validate/deploy) then validate the Databricks bundle.
# Usage: ./scripts/validate_bundle.sh [target]
#   target: dev (default) or prod
set -e
cd "$(dirname "$0")/.."
TARGET="${1:-dev}"
echo "Preparing dashboards for target=$TARGET..."
if [[ "$TARGET" == "prod" ]]; then
  uv run python scripts/prepare_dashboards.py --catalog prod_catalog --schema ahs_demo_payment_analysis_prod
else
  uv run python scripts/prepare_dashboards.py
fi
echo "Validating bundle (-t $TARGET)..."
databricks bundle validate -t "$TARGET"
echo "Validation OK!"
