#!/usr/bin/env bash
# Run all local checks and validations (no deploy, no live Databricks required for most steps).
# Usage: ./scripts/verify_all.sh [target]
#   target: dev (default) or prod — used for dashboard prep and bundle validate
set -e
cd "$(dirname "$0")/.."
TARGET="${1:-dev}"
echo "=== Verification (target=$TARGET) ==="

echo ""
echo "1. TypeScript + Python (apx dev check)..."
uv run apx dev check

echo ""
echo "2. Production build (apx build)..."
uv run apx build

echo ""
echo "3. Backend app import smoke test..."
uv run python -c "
from payment_analysis.backend.app import app
from payment_analysis.backend.router import api
assert app is not None and len(api.routes) > 0
print('   Backend app and API router import OK.')
"

echo ""
echo "4. Prepare dashboards and validate dashboard assets..."
if [[ "$TARGET" == "prod" ]]; then
  uv run python scripts/prepare_dashboards.py --catalog prod_catalog --schema ahs_demo_payment_analysis_prod
else
  uv run python scripts/prepare_dashboards.py
fi
uv run python scripts/validate_dashboard_assets.py --catalog "${DATABRICKS_CATALOG:-ahs_demos_catalog}" --schema "${DATABRICKS_SCHEMA:-ahs_demo_payment_analysis_dev}"
echo "   Dashboard assets OK."

echo ""
echo "5. Databricks bundle validate..."
databricks bundle validate -t "$TARGET"

echo ""
echo "=== All verifications passed ==="
