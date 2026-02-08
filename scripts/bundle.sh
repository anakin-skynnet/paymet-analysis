#!/usr/bin/env bash
# Databricks bundle and verification: validate, deploy, or run full verify.
# Usage: ./scripts/bundle.sh {validate|deploy|verify} [target]
#   target: dev (default) or prod
set -e
cd "$(dirname "$0")/.."
if [[ -z "${1:-}" ]]; then
  echo "Usage: ./scripts/bundle.sh {validate|deploy|verify} [target]"
  echo "  target: dev (default) or prod"
  exit 1
fi
CMD="$1"
TARGET="${2:-dev}"

prepare_dashboards() {
  echo "Preparing dashboards for target=$TARGET..."
  if [[ "$TARGET" == "prod" ]]; then
    uv run python scripts/dashboards.py prepare --catalog prod_catalog --schema ahs_demo_payment_analysis_prod
  else
    uv run python scripts/dashboards.py prepare
  fi
}

case "$CMD" in
  validate)
    prepare_dashboards
    echo "Validating bundle (-t $TARGET)..."
    databricks bundle validate -t "$TARGET"
    echo "Validation OK!"
    ;;
  deploy)
    prepare_dashboards
    echo "Deploying bundle (-t $TARGET)..."
    EXTRA_VARS=()
    if [[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]]; then
      EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")
    fi
    databricks bundle deploy -t "$TARGET" --force --auto-approve "${EXTRA_VARS[@]}"
    echo "Deployment complete!"
    ;;
  verify)
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
    prepare_dashboards
    uv run python scripts/dashboards.py validate-assets --catalog "${DATABRICKS_CATALOG:-ahs_demos_catalog}" --schema "${DATABRICKS_SCHEMA:-payment_analysis}"
    echo "   Dashboard assets OK."
    echo ""
    echo "5. Databricks bundle validate..."
    databricks bundle validate -t "$TARGET"
    echo ""
    echo "=== All verifications passed ==="
    ;;
  *)
    echo "Usage: ./scripts/bundle.sh {validate|deploy|verify} [target]"
    echo "  target: dev (default) or prod"
    exit 1
    ;;
esac
