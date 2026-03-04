#!/usr/bin/env bash
# Databricks bundle and verification: validate, deploy, deploy-app, or run full verify.
#
# Two-phase deployment:
#   deploy | redeploy  → Deploy all resources EXCEPT the App. Then run jobs 5 and 6, then run "deploy app".
#   deploy app         → Validate app dependencies, uncomment model_serving and app serving bindings, deploy App.
#
# Usage: ./scripts/bundle.sh {validate|deploy|redeploy|deploy app|verify} [target]
#   target: dev (default) or prod
#
# Performance (faster deploys):
#   - Phase 1: apx build, dashboards prepare, and workspace path resolution run in parallel (~20–60s saved).
#   - Phase 1: after deploy, dashboard publish and check-app-deployable run in parallel (~10–30s saved).
#   - Phase 2: dashboard prepare runs in parallel with check-app-deployable and YAML toggles (~20–50s saved).
#   - Phase 2: set SKIP_DASHBOARD_PREPARE=1 when running "deploy app" right after phase 1 (dashboards already prepared).
#   - Phase 2: set SKIP_BUNDLE_VALIDATE=1 to skip "bundle validate" before deploy (~5–15s saved).
set -e
cd "$(dirname "$0")/.."

# Restore databricks.yml from backup if the script exits unexpectedly (Ctrl+C, error, etc.)
cleanup_on_exit() {
  local exit_code=$?
  if [[ -f "$DATABRICKS_YML.bundle_phase1.bak" && $exit_code -ne 0 ]]; then
    echo ""
    echo "⚠️  Restoring databricks.yml from backup after error (exit code $exit_code)..."
    cp "$DATABRICKS_YML.bundle_phase1.bak" "$DATABRICKS_YML"
    rm -f "$DATABRICKS_YML.bundle_phase1.bak"
  fi
}
DATABRICKS_YML="databricks.yml"
trap cleanup_on_exit EXIT

if [[ -z "${1:-}" ]]; then
  echo "Usage: ./scripts/bundle.sh {validate|deploy|redeploy|deploy app|verify} [target]"
  echo "  deploy / redeploy: deploy all resources except the App; then run jobs 5 and 6 and run 'deploy app'"
  echo "  deploy app:        validate and deploy the App with model serving and all resources uncommented"
  echo "  target: dev (default) or prod"
  exit 1
fi
CMD="$1"
# Support "deploy app" as second word
if [[ "${1:-}" == "deploy" && "${2:-}" == "app" ]]; then
  CMD="deploy-app"
  TARGET="${3:-dev}"
elif [[ "${1:-}" == "deploy" || "${1:-}" == "redeploy" ]]; then
  CMD="deploy"
  TARGET="${2:-dev}"
else
  TARGET="${2:-dev}"
fi

BACKUP="${DATABRICKS_YML}.bundle_phase1.bak"

prepare_dashboards() {
  echo "Preparing dashboards for target=$TARGET..."
  if [[ "$TARGET" == "prod" ]]; then
    uv run python scripts/dashboards.py prepare --catalog prod_catalog --schema payment_analysis
  else
    uv run python scripts/dashboards.py prepare --catalog ahs_demos_catalog --schema payment_analysis
  fi
}

# Comment out app and model_serving in databricks.yml for phase 1 (deploy without app)
comment_out_app_and_serving() {
  if [[ -f "$BACKUP" ]]; then cp "$BACKUP" "$DATABRICKS_YML"; fi
  cp "$DATABRICKS_YML" "$BACKUP"
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i 's|^  - resources/model_serving.yml|  # - resources/model_serving.yml|' "$DATABRICKS_YML"
    sed -i 's|^  - resources/fastapi_app.yml|  # - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  else
    sed -i '' 's|^  - resources/model_serving.yml|  # - resources/model_serving.yml|' "$DATABRICKS_YML"
    sed -i '' 's|^  - resources/fastapi_app.yml|  # - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  fi
  echo "Commented out model_serving and fastapi_app for phase 1 (no app deploy)."
}

# Restore only fastapi_app in databricks.yml (after phase 1: app was excluded; leave model_serving commented until "deploy app")
restore_fastapi_app_only() {
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i 's|^  # - resources/fastapi_app.yml|  - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  else
    sed -i '' 's|^  # - resources/fastapi_app.yml|  - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  fi
  echo "Restored fastapi_app in databricks.yml (model_serving stays commented until 'deploy app')."
}

# Uncomment both model_serving and fastapi_app in databricks.yml (for phase 2 deploy app)
restore_app_and_serving() {
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i 's|^  # - resources/model_serving.yml|  - resources/model_serving.yml|' "$DATABRICKS_YML"
    sed -i 's|^  # - resources/fastapi_app.yml|  - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  else
    sed -i '' 's|^  # - resources/model_serving.yml|  - resources/model_serving.yml|' "$DATABRICKS_YML"
    sed -i '' 's|^  # - resources/fastapi_app.yml|  - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  fi
  echo "Restored model_serving and fastapi_app in databricks.yml."
}

# Ensure model_serving and fastapi_app are uncommented in databricks.yml (for deploy app)
ensure_app_and_serving_included() {
  if grep -q '^  # - resources/model_serving.yml' "$DATABRICKS_YML" 2>/dev/null; then
    restore_app_and_serving
  elif ! grep -q '^  - resources/fastapi_app.yml' "$DATABRICKS_YML" 2>/dev/null; then
    restore_app_and_serving
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
    echo "=== Phase 1: Deploy all resources EXCEPT the App ==="
    comment_out_app_and_serving
    WORKSPACE_PATH_FILE=$(mktemp)
    WORKSPACE_FOLDER="${BUNDLE_VAR_workspace_folder:-payment-analysis}"
    (
      PATH_VAL=$(databricks current-user me -o json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('userName',''); print(f'/Workspace/Users/{u}/${WORKSPACE_FOLDER}' if u else '')" 2>/dev/null || true)
      [[ -z "$PATH_VAL" ]] && PATH_VAL=$(databricks bundle validate -t "$TARGET" 2>/dev/null | sed -n 's/.*Path:[[:space:]]*\([^[:space:]]*\).*/\1/p' | head -1)
      echo "$PATH_VAL" > "$WORKSPACE_PATH_FILE"
    ) &
    PATH_PID=$!
    echo "Building web UI and preparing dashboards (and resolving workspace path) in parallel..."
    uv run apx build &
    BUILD_PID=$!
    prepare_dashboards &
    PREPARE_PID=$!
    wait "$BUILD_PID" || exit $?
    wait "$PREPARE_PID" || exit $?
    wait "$PATH_PID" 2>/dev/null || true
    WORKSPACE_PATH=$(cat "$WORKSPACE_PATH_FILE" 2>/dev/null || true)
    rm -f "$WORKSPACE_PATH_FILE"
    echo "Cleaning workspace dashboards (except dbdemos*)..."
    if [[ -n "$WORKSPACE_PATH" ]]; then
      uv run python scripts/dashboards.py clean-workspace-except-dbdemos --path "$WORKSPACE_PATH" 2>/dev/null || true
    else
      uv run python scripts/dashboards.py clean-workspace-except-dbdemos 2>/dev/null || true
    fi
    echo "Deploying bundle (-t $TARGET) without app..."
    EXTRA_VARS=()
    [[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]] && EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")
    databricks bundle deploy -t "$TARGET" --force --auto-approve --force-lock "${EXTRA_VARS[@]}"
    restore_fastapi_app_only
    rm -f "$BACKUP"
    echo ""
    echo "Publishing dashboards and checking app deployability in parallel..."
    uv run python scripts/dashboards.py publish 2>/dev/null || true &
    PUBLISH_PID=$!
    uv run python scripts/toggle_app_resources.py --check-app-deployable || true &
    CHECK_PID=$!
    wait "$PUBLISH_PID" 2>/dev/null || true
    wait "$CHECK_PID" 2>/dev/null || true
    echo ""
    echo "================================================================================"
    echo "all resources deployed except the App. Run jobs 5 and 6. After completion, write the prompt \"deploy app\""
    echo "================================================================================"
    ;;
  deploy-app)
    echo "=== Phase 2: Deploy the App with all dependencies and resources ==="
    if [[ -z "${SKIP_DASHBOARD_PREPARE:-}" ]]; then
      echo "Preparing dashboards in background (while running YAML checks)..."
      prepare_dashboards &
      PREPARE_PID=$!
    fi
    echo "Validating that the App can be deployed with all dependencies and resources assigned and uncommented..."
    uv run python scripts/toggle_app_resources.py --check-app-deployable
    echo ""
    echo "Uncommenting model_serving and serving endpoint bindings..."
    ensure_app_and_serving_included
    # Enable all serving endpoint bindings (Jobs 5 & 6 should have run before this phase).
    # To skip specific endpoints (e.g. if a job failed), set SKIP_SERVING_ENDPOINTS="endpoint1,endpoint2".
    SKIP_ARGS=()
    if [[ -n "${SKIP_SERVING_ENDPOINTS:-}" ]]; then
      IFS=',' read -ra SKIP_LIST <<< "$SKIP_SERVING_ENDPOINTS"
      for ep in "${SKIP_LIST[@]}"; do
        SKIP_ARGS+=(--skip-endpoint "$ep")
      done
      echo "Skipping endpoints: ${SKIP_SERVING_ENDPOINTS}"
    fi
    uv run python scripts/toggle_app_resources.py --enable-serving-endpoints "${SKIP_ARGS[@]}"
    if [[ -z "${SKIP_DASHBOARD_PREPARE:-}" ]]; then
      wait "$PREPARE_PID" || exit $?
    else
      echo "Skipping dashboard prepare (SKIP_DASHBOARD_PREPARE=1)."
    fi
    if [[ -z "${SKIP_BUNDLE_VALIDATE:-}" ]]; then
      echo "Validating bundle (-t $TARGET)..."
      databricks bundle validate -t "$TARGET"
    else
      echo "Skipping bundle validate (SKIP_BUNDLE_VALIDATE=1)."
    fi
    echo "Deploying bundle (-t $TARGET) with App and model serving..."
    EXTRA_VARS=()
    [[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]] && EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")
    databricks bundle deploy -t "$TARGET" --force --auto-approve --force-lock "${EXTRA_VARS[@]}"
    echo ""
    echo "Granting permissions to the App's Service Principal (background)..."
    (uv run python scripts/grant_sp_permissions.py 2>&1 || echo "⚠️  SP permission grant had issues (non-fatal). Check logs.") &
    GRANT_PID=$!
    echo "================================================================================"
    echo "App deployed with all dependencies and resources assigned and uncommented."
    echo "================================================================================"
    echo "Waiting for SP permissions to finish..."
    wait "$GRANT_PID" 2>/dev/null || true
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
    VA_SCHEMA="${DATABRICKS_SCHEMA:-payment_analysis}"
    uv run python scripts/dashboards.py validate-assets --catalog "${DATABRICKS_CATALOG:-ahs_demos_catalog}" --schema "$VA_SCHEMA"
    echo "   Dashboard assets OK."
    echo ""
    echo "5. Databricks bundle validate..."
    databricks bundle validate -t "$TARGET"
    echo ""
    echo "6. Jobs dry-run (workspace must be configured)..."
    uv run python scripts/run_and_validate_jobs.py --dry-run
    echo ""
    echo "7. Pipelines validation..."
    uv run python scripts/run_and_validate_jobs.py pipelines
    echo ""
    echo "=== All verifications passed ==="
    ;;
  *)
    echo "Usage: ./scripts/bundle.sh {validate|deploy|redeploy|deploy app|verify} [target]"
    echo "  deploy / redeploy: deploy all resources except the App; then run jobs 5 and 6, then: ./scripts/bundle.sh deploy app [target]"
    echo "  deploy app:        deploy the App with model serving and all resources uncommented (run after jobs 5 and 6)"
    echo "  target: dev (default) or prod"
    exit 1
    ;;
esac
