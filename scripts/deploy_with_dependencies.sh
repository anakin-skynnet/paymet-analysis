#!/usr/bin/env bash
# Two-phase deploy: all resources are always UPDATED in place, never destroyed/recreated.
# Phase 1 keeps the app in the bundle (only disables serving bindings).
# model_serving.yml is kept when endpoints exist; excluded only on first deploy.
#
# Usage: ./scripts/deploy_with_dependencies.sh [target]
#   target: dev (default) or prod
#
# Phase 1: Deploy all resources (app updated without serving bindings).
#          Run Job 5 (Train Models) and Job 6 (Deploy Agents); wait for completion.
# Phase 2: Enable serving bindings + model_serving, update the App.
set -e
cd "$(dirname "$0")/.."
TARGET="${1:-dev}"
DATABRICKS_YML="databricks.yml"
BACKUP="${DATABRICKS_YML}.deploy_with_deps.bak"

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

prepare_dashboards() {
  echo "Preparing dashboards for target=$TARGET..."
  if [[ "$TARGET" == "prod" ]]; then
    uv run python scripts/dashboards.py prepare --catalog prod_catalog --schema payment_analysis
  else
    uv run python scripts/dashboards.py prepare --catalog ahs_demos_catalog --schema payment_analysis
  fi
}

# Pre-deploy: verify all resources, reconcile state, capture serving endpoint status.
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

# Phase 1 config: disable serving bindings in the app; keep all resources in bundle.
# model_serving.yml is only excluded when endpoints don't exist yet (first deploy).
prepare_phase1_config() {
  if [[ -f "$BACKUP" ]]; then
    echo "Restoring $DATABRICKS_YML from previous run..."
    cp "$BACKUP" "$DATABRICKS_YML"
  fi
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
  fi
  uv run python scripts/toggle_app_resources.py --enable-serving-endpoints 2>/dev/null || true
  echo "Restored databricks.yml and serving endpoint bindings."
}

# Ensure model_serving.yml is included in databricks.yml (for Phase 2).
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

EXTRA_VARS=()
[[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]] && EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")

echo "=== Two-phase deploy (target=$TARGET) ==="
echo ""

# ---------------------------------------------------------------------------
# Phase 1: Deploy all resources (app updated without serving bindings)
# ---------------------------------------------------------------------------
echo "--- Phase 1: Deploy all resources (app updated, serving bindings disabled) ---"
run_pre_deploy_check
prepare_phase1_config

# Resolve workspace path in background
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
echo "Deploying bundle (phase 1) — updating all resources in place..."
databricks bundle deploy -t "$TARGET" --force --auto-approve --force-lock "${EXTRA_VARS[@]}"
restore_after_phase1
echo "Phase 1 deploy complete."
echo ""

# ---------------------------------------------------------------------------
# Run Job 5 (Train Models) and Job 6 (Deploy Agents); wait for completion
# ---------------------------------------------------------------------------
echo "--- Running Job 5 (Train Models) and Job 6 (Deploy Agents) ---"
echo "Job 5: Training models and registering to UC (this may take several minutes)..."
if ! uv run python scripts/run_and_validate_jobs.py --job job_5_train_models_and_serving; then
  echo "ERROR: Job 5 failed. Fix the job run in Databricks, then re-run this script or run phase 2 manually."
  exit 1
fi
echo "Job 5 completed."
echo "Job 6: Deploying agents (register AgentBricks, etc.)..."
if ! uv run python scripts/run_and_validate_jobs.py --job job_6_deploy_agents; then
  echo "ERROR: Job 6 failed. Fix the job run in Databricks, then re-run this script or run phase 2 manually."
  exit 1
fi
echo "Job 6 completed."
echo ""

# ---------------------------------------------------------------------------
# Phase 2: Update the App with serving bindings and model_serving
# ---------------------------------------------------------------------------
echo "--- Phase 2: Update the App with serving bindings and model_serving ---"
run_pre_deploy_check
echo "Validating that the App can be deployed with all dependencies and resources assigned and uncommented..."
uv run python scripts/toggle_app_resources.py --check-app-deployable
echo ""
ensure_serving_included
echo "Enabling serving endpoint bindings in fastapi_app.yml..."
SKIP_ARGS=()
for ep in payment-response-agent approval-propensity risk-scoring smart-routing smart-retry; do
  if ! databricks serving-endpoints get "$ep" >/dev/null 2>&1; then
    SKIP_ARGS+=(--skip-endpoint "$ep")
    echo "  Auto-skipping binding for '$ep' (endpoint not found)"
  fi
done
uv run python scripts/toggle_app_resources.py --enable-serving-endpoints "${SKIP_ARGS[@]}"
echo "Deploying bundle (phase 2) — updating existing app with serving bindings..."
echo "(Skipping dashboard prepare — already done in phase 1.)"
databricks bundle deploy -t "$TARGET" --force --auto-approve --force-lock "${EXTRA_VARS[@]}"
echo ""
echo "================================================================================"
echo "App updated with all dependencies and resources assigned and uncommented."
echo "================================================================================"
echo ""

echo "Publishing dashboards and granting SP permissions in parallel..."
uv run python scripts/dashboards.py publish 2>/dev/null || echo "Dashboard publish skipped or failed." &
PUBLISH_PID=$!
(uv run python scripts/grant_sp_permissions.py 2>&1 || echo "⚠️  SP permission grant had issues (non-fatal). Check logs.") &
GRANT_PID=$!
wait "$PUBLISH_PID" 2>/dev/null || true
wait "$GRANT_PID" 2>/dev/null || true

rm -f "$BACKUP"
echo "=== Two-phase deploy finished ==="
