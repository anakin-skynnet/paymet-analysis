#!/usr/bin/env bash
# Databricks bundle and verification: validate, deploy, deploy-app, or run full verify.
#
# Two-phase deployment:
#   deploy | redeploy  → Deploy all resources EXCEPT the App. Then run jobs 5 and 6, then run "deploy app".
#   deploy app         → Validate app dependencies, uncomment model_serving and app serving bindings, deploy App.
#
# Flags (apply to any command):
#   --skip-build   Skip the frontend build (use cached .build/dist)
#   --skip-clean   Skip workspace dashboard cleanup (faster when dashboards unchanged)
#   --parallel     Run build, dashboard prep, and clean concurrently (default in deploy)
#
# Usage: ./scripts/bundle.sh {validate|deploy|redeploy|deploy app|verify} [target] [flags]
#   target: dev (default) or prod
set -e
cd "$(dirname "$0")/.."

# ---- Timing helper ----
_start_ts=$(date +%s)
_step_ts=$_start_ts
step_time() {
  local now
  now=$(date +%s)
  local elapsed=$(( now - _step_ts ))
  _step_ts=$now
  echo "  ⏱  ${1:-step}: ${elapsed}s"
}
total_time() {
  local now
  now=$(date +%s)
  local elapsed=$(( now - _start_ts ))
  echo ""
  echo "  ⏱  Total: ${elapsed}s"
}

# ---- Parse args ----
if [[ -z "${1:-}" ]]; then
  echo "Usage: ./scripts/bundle.sh {validate|deploy|redeploy|deploy app|verify} [target] [--skip-build] [--skip-clean]"
  echo "  deploy / redeploy: deploy all resources except the App"
  echo "  deploy app:        deploy the App with model serving and all resources uncommented"
  echo "  target: dev (default) or prod"
  exit 1
fi

CMD="$1"
SKIP_BUILD=false
SKIP_CLEAN=false
SKIP_PUBLISH=false

# Support "deploy app" as second word
if [[ "${1:-}" == "deploy" && "${2:-}" == "app" ]]; then
  CMD="deploy-app"
  shift 2
  TARGET="${1:-dev}"
  [[ "$TARGET" == --* ]] && TARGET="dev"  # handle flag as first positional
  shift 2>/dev/null || true
elif [[ "${1:-}" == "deploy" || "${1:-}" == "redeploy" ]]; then
  CMD="deploy"
  shift
  TARGET="${1:-dev}"
  [[ "$TARGET" == --* ]] && TARGET="dev"
  shift 2>/dev/null || true
else
  shift
  TARGET="${1:-dev}"
  [[ "$TARGET" == --* ]] && TARGET="dev"
  shift 2>/dev/null || true
fi

# Parse remaining flags
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=true ;;
    --skip-clean) SKIP_CLEAN=true ;;
    --skip-publish) SKIP_PUBLISH=true ;;
  esac
done

DATABRICKS_YML="databricks.yml"
BACKUP="${DATABRICKS_YML}.bundle_phase1.bak"

# ---- Cached workspace path ----
# Resolves workspace path once and caches it, avoiding a redundant `bundle validate`.
_WORKSPACE_PATH=""
get_workspace_path() {
  if [[ -n "$_WORKSPACE_PATH" ]]; then
    echo "$_WORKSPACE_PATH"
    return
  fi
  _WORKSPACE_PATH=$(databricks bundle validate -t "$TARGET" 2>/dev/null \
    | sed -n 's/.*Path:[[:space:]]*\([^[:space:]]*\).*/\1/p' | head -1)
  echo "$_WORKSPACE_PATH"
}

prepare_dashboards() {
  echo "Preparing dashboards for target=$TARGET..."
  local _catalog="${DATABRICKS_CATALOG:-ahs_demos_catalog}"
  local _schema="${DATABRICKS_SCHEMA:-payment_analysis}"
  if [[ "$TARGET" == "prod" ]]; then
    _catalog="${DATABRICKS_CATALOG:-prod_catalog}"
  fi
  uv run python scripts/dashboards.py prepare --catalog "$_catalog" --schema "$_schema"
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

# Restore only fastapi_app in databricks.yml (after phase 1)
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

# Ensure model_serving and fastapi_app are uncommented in databricks.yml
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
    step_time "validate"
    ;;
  deploy)
    echo "=== Phase 1: Deploy all resources EXCEPT the App ==="
    echo ""
    comment_out_app_and_serving

    # ---- Parallel pre-deploy tasks ----
    # Run build, dashboard prep, and workspace clean concurrently.
    PIDS=()
    LOGS_DIR=$(mktemp -d)

    if [[ "$SKIP_BUILD" == "false" ]]; then
      echo "Starting web UI build (background)..."
      uv run apx build > "$LOGS_DIR/build.log" 2>&1 &
      PIDS+=("$!:build")
    else
      echo "Skipping web UI build (--skip-build)."
    fi

    echo "Starting dashboard preparation (background)..."
    prepare_dashboards > "$LOGS_DIR/dashboards.log" 2>&1 &
    PIDS+=("$!:dashboards")

    if [[ "$SKIP_CLEAN" == "false" ]]; then
      echo "Starting workspace cleanup (background)..."
      (
        WORKSPACE_PATH=$(get_workspace_path)
        if [[ -n "$WORKSPACE_PATH" ]]; then
          uv run python scripts/dashboards.py clean-workspace-except-dbdemos --path "$WORKSPACE_PATH" 2>/dev/null
        else
          uv run python scripts/dashboards.py clean-workspace-except-dbdemos 2>/dev/null
        fi
      ) > "$LOGS_DIR/clean.log" 2>&1 &
      PIDS+=("$!:clean")
    else
      echo "Skipping workspace cleanup (--skip-clean)."
    fi

    # Wait for all background tasks
    FAILED=""
    for entry in "${PIDS[@]}"; do
      PID="${entry%%:*}"
      NAME="${entry#*:}"
      if wait "$PID"; then
        echo "  ✓ $NAME completed"
      else
        echo "  ✗ $NAME failed (see $LOGS_DIR/$NAME.log)"
        FAILED="$FAILED $NAME"
      fi
    done

    if [[ -n "$FAILED" ]]; then
      echo ""
      echo "Pre-deploy task failures:$FAILED"
      echo "Logs in: $LOGS_DIR/"
      for entry in "${PIDS[@]}"; do
        NAME="${entry#*:}"
        if [[ -f "$LOGS_DIR/$NAME.log" ]]; then
          echo "--- $NAME ---"
          tail -20 "$LOGS_DIR/$NAME.log"
        fi
      done
      # Don't exit; dashboard prep may have failed but deploy could still work
    fi
    step_time "parallel pre-deploy (build + dashboards + clean)"

    # ---- Bundle deploy ----
    echo ""
    echo "Deploying bundle (-t $TARGET) without app..."
    EXTRA_VARS=()
    [[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]] && EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")
    databricks bundle deploy -t "$TARGET" --force --auto-approve "${EXTRA_VARS[@]}"
    restore_fastapi_app_only
    rm -f "$BACKUP"
    step_time "bundle deploy (phase 1)"

    # ---- Post-deploy: publish dashboards ----
    if [[ "$SKIP_PUBLISH" == "false" ]]; then
      echo ""
      echo "Publishing dashboards..."
      uv run python scripts/dashboards.py publish 2>/dev/null || true
      step_time "dashboard publish"
    fi

    echo ""
    echo "--- Validation: app can be deployed with all dependencies and resources ---"
    uv run python scripts/toggle_app_resources.py --check-app-deployable || true
    echo ""
    echo "================================================================================"
    echo "Phase 1 complete. All resources deployed except the App."
    echo ""
    echo "Next steps:"
    echo "  1. Run Jobs 5 & 6 in parallel:"
    echo "     uv run python scripts/run_and_validate_jobs.py --jobs job_5_train_models_and_serving job_6_deploy_agents"
    echo "  2. After jobs complete:"
    echo "     ./scripts/bundle.sh deploy app $TARGET"
    echo "================================================================================"
    total_time
    # Cleanup temp logs
    rm -rf "$LOGS_DIR"
    ;;
  deploy-app)
    echo "=== Phase 2: Deploy the App with all dependencies and resources ==="
    echo "Validating that the App can be deployed with all dependencies and resources assigned and uncommented..."
    uv run python scripts/toggle_app_resources.py --check-app-deployable
    step_time "pre-validation"
    echo ""
    echo "Uncommenting model_serving and serving endpoint bindings..."
    ensure_app_and_serving_included
    uv run python scripts/toggle_app_resources.py --enable-serving-endpoints

    # Skip redundant dashboard preparation — already done in Phase 1.
    # Only re-prepare if the user explicitly requests it or .build/dashboards is missing.
    if [[ ! -d ".build/dashboards" ]] || [[ -z "$(ls -A .build/dashboards/ 2>/dev/null)" ]]; then
      echo "Dashboard build artifacts missing; re-preparing..."
      prepare_dashboards
    else
      echo "Skipping dashboard preparation (cached from Phase 1)."
    fi

    echo "Deploying bundle (-t $TARGET) with App and model serving..."
    EXTRA_VARS=()
    [[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]] && EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")
    databricks bundle deploy -t "$TARGET" --force --auto-approve "${EXTRA_VARS[@]}"
    step_time "bundle deploy (phase 2 — app + serving)"
    echo ""
    echo "================================================================================"
    echo "App deployed with all dependencies and resources assigned and uncommented."
    echo "================================================================================"
    total_time
    ;;
  verify)
    echo "=== Verification (target=$TARGET) ==="
    echo ""
    echo "1. TypeScript + Python (apx dev check)..."
    uv run apx dev check
    step_time "type checks"
    echo ""
    echo "2. Production build (apx build)..."
    uv run apx build
    step_time "production build"
    echo ""
    echo "3. Backend app import smoke test..."
    uv run python -c "
from payment_analysis.backend.app import app
from payment_analysis.backend.router import api
assert app is not None and len(api.routes) > 0
print('   Backend app and API router import OK.')
"
    step_time "backend smoke test"
    echo ""
    echo "4. Prepare dashboards and validate dashboard assets..."
    prepare_dashboards
    VA_SCHEMA="${DATABRICKS_SCHEMA:-payment_analysis}"
    uv run python scripts/dashboards.py validate-assets --catalog "${DATABRICKS_CATALOG:-ahs_demos_catalog}" --schema "$VA_SCHEMA"
    echo "   Dashboard assets OK."
    step_time "dashboard validation"
    echo ""
    echo "5. Databricks bundle validate..."
    databricks bundle validate -t "$TARGET"
    step_time "bundle validate"
    echo ""
    echo "6. Jobs dry-run (workspace must be configured)..."
    uv run python scripts/run_and_validate_jobs.py --dry-run
    step_time "jobs dry-run"
    echo ""
    echo "7. Pipelines validation..."
    uv run python scripts/run_and_validate_jobs.py pipelines
    step_time "pipelines validate"
    echo ""
    echo "=== All verifications passed ==="
    total_time
    ;;
  *)
    echo "Usage: ./scripts/bundle.sh {validate|deploy|redeploy|deploy app|verify} [target] [--skip-build] [--skip-clean]"
    echo "  deploy / redeploy: deploy all resources except the App; then run jobs 5 and 6, then: ./scripts/bundle.sh deploy app [target]"
    echo "  deploy app:        deploy the App with model serving and all resources uncommented (run after jobs 5 and 6)"
    echo "  target: dev (default) or prod"
    echo ""
    echo "Flags:"
    echo "  --skip-build    Skip frontend build (use cached dist)"
    echo "  --skip-clean    Skip workspace dashboard cleanup"
    echo "  --skip-publish  Skip dashboard publishing after deploy"
    exit 1
    ;;
esac
