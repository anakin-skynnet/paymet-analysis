#!/usr/bin/env bash
# Two-phase deploy: deploy jobs first, run Job 5 & 6 to register models/agents, then deploy app.
# This ensures model serving endpoints exist before the app is bound to them.
#
# Usage: ./scripts/deploy_with_dependencies.sh [target]
#   target: dev (default) or prod
#
# Phase 1: Exclude model_serving and app from bundle; deploy (jobs, pipelines, dashboards, etc.).
#          Run Job 5 (Train Models) and Job 6 (Deploy Agents); wait for completion.
# Phase 2: Restore model_serving and app; deploy again (endpoints + app with correct bindings).
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
# Phase 1: Deploy jobs (and other resources) without model serving or app
# ---------------------------------------------------------------------------
echo "--- Phase 1: Deploy jobs and resources (no model serving, no app) ---"
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
# Phase 2: Deploy model serving and app (endpoints exist now)
# ---------------------------------------------------------------------------
echo "--- Phase 2: Deploy model serving endpoints and app ---"
restore_app_and_serving
echo "Deploying bundle (phase 2: endpoints + app)..."
databricks bundle deploy -t "$TARGET" --force --auto-approve "${EXTRA_VARS[@]}"
echo "Phase 2 deploy complete."
echo ""

echo "Publishing dashboards..."
if uv run python scripts/dashboards.py publish 2>/dev/null; then
  echo "Dashboards published."
else
  echo "Dashboard publish skipped or failed."
fi

rm -f "$BACKUP"
echo ""
echo "=== Two-phase deploy finished ==="
echo "Set ORCHESTRATOR_SERVING_ENDPOINT=payment-analysis-orchestrator in the app Environment to use AgentBricks chat."
