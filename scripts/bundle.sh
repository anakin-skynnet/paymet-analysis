#!/usr/bin/env bash
# Databricks bundle and verification: validate, deploy, deploy-app, or run full verify.
#
# Two-phase deployment (app is always UPDATED, never destroyed/recreated):
#   deploy | redeploy  → Deploy all resources (app updated without serving bindings). Then run jobs 5 and 6, then run "deploy app".
#   deploy app         → Validate app dependencies, enable model_serving and serving bindings, update App.
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

# Restore databricks.yml and serving bindings if the script exits unexpectedly (Ctrl+C, error, etc.)
DATABRICKS_YML="databricks.yml"
BACKUP="${DATABRICKS_YML}.bundle_phase1.bak"

cleanup_on_exit() {
  local exit_code=$?
  if [[ -f "$BACKUP" && $exit_code -ne 0 ]]; then
    echo ""
    echo "⚠️  Restoring databricks.yml from backup after error (exit code $exit_code)..."
    cp "$BACKUP" "$DATABRICKS_YML"
    rm -f "$BACKUP"
    uv run python scripts/toggle_app_resources.py --enable-serving-endpoints 2>/dev/null || true
  fi
}
trap cleanup_on_exit EXIT

if [[ -z "${1:-}" ]]; then
  echo "Usage: ./scripts/bundle.sh {validate|deploy|redeploy|deploy app|verify} [target]"
  echo "  deploy / redeploy: update all resources (app without serving bindings); then run jobs 5 and 6 and run 'deploy app'"
  echo "  deploy app:        update the App with model serving and serving bindings enabled"
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

prepare_dashboards() {
  echo "Preparing dashboards for target=$TARGET..."
  if [[ "$TARGET" == "prod" ]]; then
    uv run python scripts/dashboards.py prepare --catalog prod_catalog --schema payment_analysis
  else
    uv run python scripts/dashboards.py prepare --catalog ahs_demos_catalog --schema payment_analysis
  fi
}

# Pre-deploy: verify all resources, reconcile state, capture serving endpoint status.
# Sets SERVING_ENDPOINTS_EXIST=true|false for use by prepare_phase1_config.
SERVING_ENDPOINTS_EXIST=""
run_pre_deploy_check() {
  echo "Running pre-deploy resource check (target=$TARGET)..."
  local output
  output=$(uv run python scripts/pre_deploy_check.py --target "$TARGET" --fix)
  echo "$output"
  if echo "$output" | grep -q "SERVING_ENDPOINTS_EXIST=true"; then
    SERVING_ENDPOINTS_EXIST=true
  else
    SERVING_ENDPOINTS_EXIST=false
  fi
}

# Phase 1 config: disable serving bindings in the app.
# All resources stay in the bundle so Terraform UPDATES them, never destroys/recreates.
# model_serving.yml is only excluded when endpoints don't exist yet (first deploy).
prepare_phase1_config() {
  if [[ -f "$BACKUP" ]]; then cp "$BACKUP" "$DATABRICKS_YML"; fi
  cp "$DATABRICKS_YML" "$BACKUP"
  uv run python scripts/toggle_app_resources.py --disable-serving-endpoints
  if [[ "$SERVING_ENDPOINTS_EXIST" == "true" ]]; then
    echo "Model serving endpoints exist — keeping model_serving.yml (update in place)."
  else
    echo "Model serving endpoints not found (first deploy) — excluding model_serving.yml."
    if sed --version 2>/dev/null | grep -q GNU; then
      sed -i 's|^  - resources/model_serving.yml|  # - resources/model_serving.yml|' "$DATABRICKS_YML"
    else
      sed -i '' 's|^  - resources/model_serving.yml|  # - resources/model_serving.yml|' "$DATABRICKS_YML"
    fi
  fi
  echo "Phase 1 config ready: serving bindings disabled, app stays in bundle."
}

# Restore everything after Phase 1: undo databricks.yml backup and re-enable serving bindings.
restore_after_phase1() {
  if [[ -f "$BACKUP" ]]; then
    cp "$BACKUP" "$DATABRICKS_YML"
    rm -f "$BACKUP"
  fi
  uv run python scripts/toggle_app_resources.py --enable-serving-endpoints 2>/dev/null || true
  echo "Restored databricks.yml and serving endpoint bindings after Phase 1."
}

# Ensure model_serving.yml is included in databricks.yml (for Phase 2 deploy app).
ensure_serving_included() {
  if grep -q '^  # - resources/model_serving.yml' "$DATABRICKS_YML" 2>/dev/null; then
    if sed --version 2>/dev/null | grep -q GNU; then
      sed -i 's|^  # - resources/model_serving.yml|  - resources/model_serving.yml|' "$DATABRICKS_YML"
    else
      sed -i '' 's|^  # - resources/model_serving.yml|  - resources/model_serving.yml|' "$DATABRICKS_YML"
    fi
    echo "Uncommented model_serving.yml in databricks.yml."
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
    echo "=== Phase 1: Deploy all resources (app updated without serving bindings) ==="
    run_pre_deploy_check
    prepare_phase1_config
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
    echo "Deploying bundle (-t $TARGET) — updating all resources in place..."
    EXTRA_VARS=()
    [[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]] && EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")
    databricks bundle deploy -t "$TARGET" --force --auto-approve --force-lock "${EXTRA_VARS[@]}"
    restore_after_phase1
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
    echo "All resources deployed. App updated (no serving bindings yet)."
    echo "Run jobs 5 and 6. After completion, write the prompt \"deploy app\""
    echo "================================================================================"
    ;;
  deploy-app)
    echo "=== Phase 2: Update the App with serving bindings and model_serving ==="
    run_pre_deploy_check
    if [[ -z "${SKIP_DASHBOARD_PREPARE:-}" ]]; then
      echo "Preparing dashboards in background (while running YAML checks)..."
      prepare_dashboards &
      PREPARE_PID=$!
    fi
    echo "Validating that the App can be deployed with all dependencies and resources assigned and uncommented..."
    uv run python scripts/toggle_app_resources.py --check-app-deployable
    echo ""
    echo "Ensuring model_serving.yml is included and enabling serving endpoint bindings..."
    ensure_serving_included
    SKIP_ARGS=()
    # Auto-detect non-existent serving endpoints to skip their app bindings
    for ep in payment-response-agent approval-propensity risk-scoring smart-routing smart-retry; do
      if ! databricks serving-endpoints get "$ep" >/dev/null 2>&1; then
        SKIP_ARGS+=(--skip-endpoint "$ep")
        echo "  Auto-skipping binding for '$ep' (endpoint not found)"
      fi
    done
    # Also honour explicit SKIP_SERVING_ENDPOINTS env var
    if [[ -n "${SKIP_SERVING_ENDPOINTS:-}" ]]; then
      IFS=',' read -ra SKIP_LIST <<< "$SKIP_SERVING_ENDPOINTS"
      for ep in "${SKIP_LIST[@]}"; do
        SKIP_ARGS+=(--skip-endpoint "$ep")
      done
      echo "  Explicit skip: ${SKIP_SERVING_ENDPOINTS}"
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
    echo "Deploying bundle (-t $TARGET) — updating existing app with serving bindings..."
    EXTRA_VARS=()
    [[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]] && EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")
    databricks bundle deploy -t "$TARGET" --force --auto-approve --force-lock "${EXTRA_VARS[@]}"
    echo ""
    echo "Granting permissions to the App's Service Principal (background)..."
    (uv run python scripts/grant_sp_permissions.py 2>&1 || echo "⚠️  SP permission grant had issues (non-fatal). Check logs.") &
    GRANT_PID=$!
    echo "================================================================================"
    echo "App updated with all dependencies and resources assigned and uncommented."
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
    echo "  deploy / redeploy: update all resources (app without serving bindings); then run jobs 5 and 6, then: ./scripts/bundle.sh deploy app [target]"
    echo "  deploy app:        update the App with model serving and serving bindings enabled (run after jobs 5 and 6)"
    echo "  target: dev (default) or prod"
    exit 1
    ;;
esac
