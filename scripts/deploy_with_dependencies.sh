#!/usr/bin/env bash
# Two-phase deploy: deploy all resources except the app, run Job 5 & 6, then deploy the app.
# This ensures model serving endpoints exist before the app is bound to them.
#
# Usage: ./scripts/deploy_with_dependencies.sh [target]
#   target: dev (default) or prod
#
# Phase 1: Deploy all resources EXCEPT the App (jobs, pipelines, dashboards, etc.).
#          Run Job 5 (Train Models) and Job 6 (Deploy Agents); wait for completion.
# Phase 2: Validate app dependencies, uncomment model_serving and app serving bindings, deploy App.
#          Notify that the app is deployed with all dependencies and resources assigned and uncommented.
set -e
cd "$(dirname "$0")/.."
TARGET="${1:-dev}"
DATABRICKS_YML="databricks.yml"
BACKUP="${DATABRICKS_YML}.deploy_with_deps.bak"

prepare_dashboards() {
  echo "Preparing dashboards for target=$TARGET..."
  if [[ "$TARGET" == "prod" ]]; then
    uv run python scripts/dashboards.py prepare --catalog prod_catalog --schema payment_analysis
  else
    uv run python scripts/dashboards.py prepare --catalog ahs_demos_catalog --schema payment_analysis
  fi
}

comment_out_app_and_serving() {
  if [[ -f "$BACKUP" ]]; then
    echo "Restoring $DATABRICKS_YML from previous run..."
    cp "$BACKUP" "$DATABRICKS_YML"
  fi
  cp "$DATABRICKS_YML" "$BACKUP"
  # Comment out so phase 1 deploy skips model serving and app (portable sed)
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i 's|^  - resources/model_serving.yml|  # - resources/model_serving.yml|' "$DATABRICKS_YML"
    sed -i 's|^  - resources/fastapi_app.yml|  # - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  else
    sed -i '' 's|^  - resources/model_serving.yml|  # - resources/model_serving.yml|' "$DATABRICKS_YML"
    sed -i '' 's|^  - resources/fastapi_app.yml|  # - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  fi
  echo "Commented out model_serving and fastapi_app in $DATABRICKS_YML for phase 1."
}

restore_app_and_serving() {
  # Uncomment so phase 2 deploy includes model serving and app (portable sed)
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i 's|^  # - resources/model_serving.yml|  - resources/model_serving.yml|' "$DATABRICKS_YML"
    sed -i 's|^  # - resources/fastapi_app.yml|  - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  else
    sed -i '' 's|^  # - resources/model_serving.yml|  - resources/model_serving.yml|' "$DATABRICKS_YML"
    sed -i '' 's|^  # - resources/fastapi_app.yml|  - resources/fastapi_app.yml|' "$DATABRICKS_YML"
  fi
  echo "Restored model_serving and fastapi_app in $DATABRICKS_YML for phase 2."
}

echo "=== Two-phase deploy (target=$TARGET) ==="
echo ""

# ---------------------------------------------------------------------------
# Phase 1: Deploy all resources EXCEPT the App
# ---------------------------------------------------------------------------
echo "--- Phase 1: Deploy all resources except the App ---"
comment_out_app_and_serving
echo "Building web UI..."
uv run apx build
echo "Cleaning workspace dashboards..."
WORKSPACE_PATH=$(databricks bundle validate -t "$TARGET" 2>/dev/null | sed -n 's/.*Path:[[:space:]]*\([^[:space:]]*\).*/\1/p' | head -1)
if [[ -n "$WORKSPACE_PATH" ]]; then
  uv run python scripts/dashboards.py clean-workspace-except-dbdemos --path "$WORKSPACE_PATH" 2>/dev/null || true
else
  uv run python scripts/dashboards.py clean-workspace-except-dbdemos 2>/dev/null || true
fi
prepare_dashboards
echo "Deploying bundle (phase 1)..."
EXTRA_VARS=()
[[ -n "${LAKEBASE_INSTANCE_NAME:-}" ]] && EXTRA_VARS+=(--var "lakebase_instance_name=${LAKEBASE_INSTANCE_NAME}")
databricks bundle deploy -t "$TARGET" --force --auto-approve "${EXTRA_VARS[@]}"
echo "Phase 1 deploy complete."
echo ""
echo "all resources deployed except the App. Run jobs 5 and 6. After completion, write the prompt \"deploy app\""
echo ""

# ---------------------------------------------------------------------------
# Run Job 5 (Train Models) and Job 6 (Deploy Agents); wait for completion
# ---------------------------------------------------------------------------
echo "--- Running Job 5 (Train Models) and Job 6 (Deploy Agents) ---"
echo "Job 5: Training models and registering to UC (this may take several minutes)..."
if ! uv run python scripts/run_and_validate_jobs.py --job job_5_train_models_and_serving; then
  echo "ERROR: Job 5 failed. Fix the job run in Databricks, then re-run this script or run phase 2 manually."
  restore_app_and_serving
  exit 1
fi
echo "Job 5 completed."
echo "Job 6: Deploying agents (register AgentBricks, etc.)..."
if ! uv run python scripts/run_and_validate_jobs.py --job job_6_deploy_agents; then
  echo "ERROR: Job 6 failed. Fix the job run in Databricks, then re-run this script or run phase 2 manually."
  restore_app_and_serving
  exit 1
fi
echo "Job 6 completed."
echo ""

# ---------------------------------------------------------------------------
# Phase 2: Validate and deploy the App with all dependencies and resources
# ---------------------------------------------------------------------------
echo "--- Phase 2: Deploy the App with all dependencies and resources ---"
echo "Validating that the App can be deployed with all dependencies and resources assigned and uncommented..."
uv run python scripts/toggle_app_resources.py --check-app-deployable
echo ""
restore_app_and_serving
echo "Uncommenting serving endpoint bindings in fastapi_app.yml..."
uv run python scripts/toggle_app_resources.py --enable-serving-endpoints
echo "Deploying bundle (phase 2: model serving + app with bindings)..."
databricks bundle deploy -t "$TARGET" --force --auto-approve "${EXTRA_VARS[@]}"
echo ""
echo "================================================================================"
echo "App deployed with all dependencies and resources assigned and uncommented."
echo "================================================================================"
echo ""

echo "Publishing dashboards..."
if uv run python scripts/dashboards.py publish 2>/dev/null; then
  echo "Dashboards published."
else
  echo "Dashboard publish skipped or failed."
fi

rm -f "$BACKUP"
echo "=== Two-phase deploy finished ==="
echo "Set ORCHESTRATOR_SERVING_ENDPOINT=payment-analysis-orchestrator in app.yml or App Environment to use AgentBricks chat."
