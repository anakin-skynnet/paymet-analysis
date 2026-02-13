#!/usr/bin/env python3
"""
Run and validate all payment-analysis Databricks jobs.

Uses the same job name matching as the app (setup.py). Runs each job, waits for
completion, and reports success/failure. Exits with 1 if any run fails.

Prerequisites: Unity Catalog and schema must exist (default ahs_demos_catalog.payment_analysis).
See docs/DEPLOYMENT.md. Set DATABRICKS_CATALOG / DATABRICKS_SCHEMA if different.

If jobs fail with "Catalog ... or schema ... not found": create the catalog in the workspace
(or use an existing one via --var catalog=... at deploy), then deploy the bundle so the schema
is created (resources/unity_catalog.yml). Re-run jobs after that.

Usage:
  uv run python scripts/run_and_validate_jobs.py [--dry-run] [--job KEY] [--jobs KEY1 KEY2 ...] [--run-pipelines] [--no-wait] [--results-file PATH]
  uv run python scripts/run_and_validate_jobs.py status [--results-file PATH] [--once]
  uv run python scripts/run_and_validate_jobs.py pipelines
  DATABRICKS_HOST=... DATABRICKS_TOKEN=... uv run python scripts/run_and_validate_jobs.py --run-pipelines

Options:
  --dry-run        List matched jobs only, do not run.
  --job KEY        Run only this job key (e.g. job_3_initialize_ingestion).
  --jobs KEY1 KEY2 Run multiple specific jobs in parallel (e.g. --jobs job_5_train_models_and_serving job_6_deploy_agents).
  --run-pipelines  Run ETL pipeline (8. Payment Analysis ETL) and wait until idle before jobs. Use before job_3 so payments_enriched_silver exists.
  --no-wait        Start runs but do not wait for completion.
  --results-file   Write run_id per key (JSON) so "status" can poll later.
  status           Poll run status from last --results-file. Use --once to report current state and exit (no wait).
  pipelines        List pipelines matching bundle names; exit 1 if any missing.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_FILE = REPO_ROOT / ".databricks_job_runs.json"
MAX_POLL_RETRIES = 6
POLL_RETRY_DELAY = 30
PIPELINE_ETL_WAIT_TIMEOUT_MINUTES = 25


def _state_str(x):
    """Normalize API state (enum or str) to string for comparison and display."""
    if x is None:
        return ""
    if hasattr(x, "value"):
        return getattr(x, "value", str(x))
    return str(x)

# Same step names as backend setup.py _STEP_JOB_SUBSTRINGS (bundle job names).
# One key per job; running each key runs the full job (all tasks).
JOB_NAME_SUBSTRINGS: dict[str, str] = {
    "job_1_create_data_repositories": "1. Create Data Repositories",
    "job_2_simulate_transaction_events": "2. Simulate Transaction Events",
    "job_3_initialize_ingestion": "3. Initialize Ingestion",
    "job_4_deploy_dashboards": "4. Deploy Dashboards",
    "job_5_train_models_and_serving": "5. Train Models",
    "job_6_deploy_agents": "6. Deploy Agents",  # Matches "[dev] 6. Deploy Agents (Orchestrator & Specialists)" (AgentBricks)
    "job_7_genie_sync": "7. Genie Space Sync",
}

# Pipeline name substrings (bundle: 8. Payment Analysis ETL, 9. Payment Real-Time Stream).
PIPELINE_NAME_SUBSTRINGS: dict[str, str] = {
    "pipeline_8_etl": "8. Payment Analysis ETL",
    "pipeline_9_realtime": "9. Payment Real-Time Stream",
}


def _get_run_with_retry(ws, run_id):
    """Call ws.jobs.get_run(run_id) with retries on connection/timeout errors."""
    last_err: BaseException | None = None
    for attempt in range(MAX_POLL_RETRIES):
        try:
            return ws.jobs.get_run(run_id)
        except BaseException as e:
            last_err = e
            if attempt < MAX_POLL_RETRIES - 1:
                time.sleep(POLL_RETRY_DELAY)
    raise last_err if last_err is not None else RuntimeError("get_run failed after retries")


def _resolve_pipelines(ws) -> dict[str, tuple[str, str]]:
    """Resolve pipeline keys to (pipeline_id, name) by listing and matching names."""
    key_to_pipeline: dict[str, tuple[str, str]] = {}
    for p in ws.pipelines.list_pipelines():
        name = (p.name or "") if getattr(p, "name", None) else ""
        pipeline_id = getattr(p, "pipeline_id", None)
        if not name or not pipeline_id:
            continue
        for key, substr in PIPELINE_NAME_SUBSTRINGS.items():
            if substr in name:
                key_to_pipeline[key] = (str(pipeline_id), name)
                break
    return key_to_pipeline


def _run_etl_pipeline_and_wait(ws, pipeline_id: str, name: str) -> None:
    """Start the ETL pipeline update and wait until pipeline is idle (so silver table exists)."""
    print(f"Starting pipeline {name!r} ({pipeline_id})...")
    try:
        ws.pipelines.start_update(pipeline_id=pipeline_id)
    except Exception as e:
        raise RuntimeError(f"Failed to start pipeline {pipeline_id}: {e}") from e
    print("Waiting for pipeline to become idle (creates payments_enriched_silver)...")
    try:
        ws.pipelines.wait_get_pipeline_idle(
            pipeline_id=pipeline_id,
            timeout=datetime.timedelta(minutes=PIPELINE_ETL_WAIT_TIMEOUT_MINUTES),
        )
    except Exception as e:
        raise RuntimeError(
            f"Pipeline {pipeline_id} did not complete in time or failed: {e}. "
            "Check the pipeline run in the workspace; ensure catalog/schema exist and pipeline has run at least once."
        ) from e
    print("Pipeline idle; payments_enriched_silver should exist. Proceeding with jobs.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and validate payment-analysis Databricks jobs")
    parser.add_argument("--dry-run", action="store_true", help="List jobs only, do not run")
    parser.add_argument("--job", type=str, metavar="KEY", help="Run only this job key")
    parser.add_argument("--jobs", type=str, nargs="+", metavar="KEY", help="Run multiple specific jobs in parallel (e.g. --jobs job_5_train_models_and_serving job_6_deploy_agents)")
    parser.add_argument("--no-wait", action="store_true", help="Start runs but do not wait")
    parser.add_argument("--run-pipelines", action="store_true", help="Run ETL pipeline (8. Payment Analysis ETL) and wait until idle before running jobs. Required for job_3_initialize_ingestion unless pipeline was run separately.")
    parser.add_argument("--results-file", type=str, default=str(DEFAULT_RESULTS_FILE), help="Write/read run IDs (JSON) for status command")
    parser.add_argument("command", nargs="?", choices=["status", "pipelines"], help="Use 'status' to poll runs; 'pipelines' to list/validate pipelines")
    parser.add_argument("--once", action="store_true", help="(status only) Report current state once and exit without waiting for all to complete")
    args = parser.parse_args()

    # pipelines subcommand: list pipelines matching bundle names
    if args.command == "pipelines":
        try:
            from databricks.sdk import WorkspaceClient
        except ImportError:
            print("databricks-sdk not installed. Run: uv sync", file=sys.stderr)
            return 1
        ws = WorkspaceClient()
        try:
            key_to_pipeline = _resolve_pipelines(ws)
        except Exception as e:
            print(f"Failed to list pipelines: {e}", file=sys.stderr)
            return 1
        if not key_to_pipeline:
            print("No payment-analysis pipelines found in workspace.", file=sys.stderr)
            print("Expected names containing: " + ", ".join(PIPELINE_NAME_SUBSTRINGS.values()), file=sys.stderr)
            return 1
        print("Matched pipelines:")
        for key in sorted(key_to_pipeline):
            pid, name = key_to_pipeline[key]
            print(f"  {key}: {pid}  {name[:70]}...")
        missing = set(PIPELINE_NAME_SUBSTRINGS) - set(key_to_pipeline)
        if missing:
            print(f"\nMissing pipelines (deploy bundle to create): {', '.join(sorted(missing))}", file=sys.stderr)
            return 1
        print("\nAll pipelines found.")
        return 0

    # status subcommand: read results file and poll
    if args.command == "status":
        results_path = Path(args.results_file)
        if not results_path.exists():
            print(f"Results file not found: {results_path}. Run without --no-wait or with --results-file first.", file=sys.stderr)
            return 1
        try:
            from databricks.sdk import WorkspaceClient
        except ImportError:
            print("databricks-sdk not installed. Run: uv sync", file=sys.stderr)
            return 1
        data = json.loads(results_path.read_text())
        runs = data.get("runs") or []
        if not runs:
            print("No run IDs in results file.", file=sys.stderr)
            return 1
        ws = WorkspaceClient()
        run_results = {}
        once = getattr(args, "once", False)
        while len(run_results) < len(runs):
            for key, run_id in runs:
                if key in run_results:
                    continue
                try:
                    run = _get_run_with_retry(ws, run_id)
                except Exception as e:
                    print(f"  {key}: ERROR polling run_id={run_id}  {e}", file=sys.stderr)
                    run_results[key] = "ERROR"
                    continue
                state = _state_str(run.state.life_cycle_state if run.state else None)
                result = _state_str(run.state.result_state if run.state else None)
                if state == "TERMINATED":
                    run_results[key] = result if result == "SUCCESS" else "FAILED"
                    status = "SUCCESS" if result == "SUCCESS" else f"FAILED (result_state={result})"
                    print(f"  {key}: {status}  run_id={run_id}")
                elif state in ("INTERNAL_ERROR", "SKIPPED"):
                    run_results[key] = state
                    msg = (run.state.state_message or "") if run.state else ""
                    extra = f"  ({msg[:80]}...)" if len(msg or "") > 80 else (f"  ({msg})" if msg else "")
                    print(f"  {key}: {state}  run_id={run_id}{extra}")
                elif once:
                    run_results[key] = state or "UNKNOWN"
                    print(f"  {key}: {state or 'PENDING'}  run_id={run_id}")
            if once:
                break
            if len(run_results) < len(runs):
                time.sleep(10)
        failed = [k for k, v in run_results.items() if v != "SUCCESS"]
        # Terminal failures only (not RUNNING/PENDING)
        failed_terminal = [k for k, v in run_results.items() if v in ("FAILED", "INTERNAL_ERROR", "SKIPPED", "ERROR")]
        if failed and not once:
            print(f"\nFailed jobs: {', '.join(failed)}", file=sys.stderr)
            return 1
        if failed_terminal and once:
            print("\nHint: If failures mention catalog/schema not found, see docs/DEPLOYMENT.md#fix-catalog-or-schema-not-found", file=sys.stderr)
        if not once and not failed:
            print("\nAll jobs completed successfully.")
        return 0

    try:
        from databricks.sdk import WorkspaceClient
    except ImportError:
        print("databricks-sdk not installed. Run: uv sync", file=sys.stderr)
        return 1

    catalog = os.getenv("DATABRICKS_CATALOG", "ahs_demos_catalog")
    schema = os.getenv("DATABRICKS_SCHEMA", "payment_analysis")
    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID", "")

    def _job_id_env(key: str) -> str:
        return os.getenv("DATABRICKS_JOB_ID_" + key.upper(), "")

    ws = WorkspaceClient()
    # Prefer job IDs from env (DATABRICKS_JOB_ID_LAKEHOUSE_BOOTSTRAP etc.); else resolve by listing
    key_to_job: dict[str, tuple[int, str]] = {}
    for key in JOB_NAME_SUBSTRINGS:
        jid = _job_id_env(key)
        if jid and jid != "0":
            try:
                job_id = int(jid)
                job = ws.jobs.get(job_id)
                name = (job.settings.name or "") if job.settings else str(job_id)
                key_to_job[key] = (job_id, name)
            except Exception:
                pass
    if not key_to_job or (args.job and args.job not in key_to_job):
        # Resolve by listing (single page to avoid slow full scan)
        try:
            for job in ws.jobs.list(limit=100):
                name = (job.settings.name or "") if job.settings else ""
                for key, substr in JOB_NAME_SUBSTRINGS.items():
                    if substr in name and job.job_id:
                        key_to_job[key] = (job.job_id, name)
                        break
        except Exception as e:
            print(f"Failed to list jobs: {e}", file=sys.stderr)
            return 1

    if args.job:
        if args.job not in key_to_job:
            print(f"Job key {args.job!r} not found. Available: {', '.join(sorted(key_to_job))}", file=sys.stderr)
            return 1
        key_to_job = {args.job: key_to_job[args.job]}
    elif args.jobs:
        missing = [k for k in args.jobs if k not in key_to_job]
        if missing:
            print(f"Job key(s) not found: {', '.join(missing)}. Available: {', '.join(sorted(key_to_job))}", file=sys.stderr)
            return 1
        key_to_job = {k: key_to_job[k] for k in args.jobs}

    if not key_to_job:
        print("No payment-analysis jobs found in workspace.", file=sys.stderr)
        return 1

    print("Matched jobs:")
    for key in sorted(key_to_job):
        jid, name = key_to_job[key]
        print(f"  {key}: {jid}  {name[:60]}...")
    if args.dry_run:
        return 0

    # Job 3 (Initialize Ingestion) requires payments_enriched_silver from the ETL pipeline.
    run_job_3 = "job_3_initialize_ingestion" in key_to_job
    if run_job_3 and getattr(args, "run_pipelines", False):
        key_to_pipeline = _resolve_pipelines(ws)
        if "pipeline_8_etl" not in key_to_pipeline:
            print("--run-pipelines set but pipeline '8. Payment Analysis ETL' not found. Deploy bundle to create it.", file=sys.stderr)
            return 1
        pipeline_id, pipeline_name = key_to_pipeline["pipeline_8_etl"]
        _run_etl_pipeline_and_wait(ws, pipeline_id, pipeline_name)
    elif run_job_3:
        print(
            "\nNote: job_3_initialize_ingestion requires payments_enriched_silver. "
            "Run the pipeline '8. Payment Analysis ETL' first, or use --run-pipelines to run it automatically.",
            file=sys.stderr,
        )

    notebook_params = {"catalog": catalog, "schema": schema}
    if warehouse_id:
        notebook_params["warehouse_id"] = warehouse_id

    runs: list[tuple[str, int, int]] = []  # (key, job_id, run_id)
    for key in sorted(key_to_job):
        job_id, name = key_to_job[key]
        try:
            run = ws.jobs.run_now(
                job_id=job_id,
                notebook_params=notebook_params,
            )
            runs.append((key, job_id, run.run_id))
            print(f"Started {key}  job_id={job_id}  run_id={run.run_id}")
        except Exception as e:
            print(f"Failed to start {key}: {e}", file=sys.stderr)
            return 1

    results_path = Path(args.results_file)
    results_path.write_text(
        json.dumps(
            {"runs": [[k, r] for k, _jid, r in runs], "catalog": catalog, "schema": schema},
            indent=2,
        )
    )
    print(f"Run IDs written to {results_path}")

    if args.no_wait:
        print("Runs started (--no-wait). Poll later: uv run python scripts/run_and_validate_jobs.py status")
        return 0

    # Wait for all runs (poll all in parallel so total time = max(run times))
    print("\nWaiting for runs to complete...")
    run_results: dict[str, str] = {}  # key -> "SUCCESS" | "FAILED" | "INTERNAL_ERROR" | "SKIPPED"
    while len(run_results) < len(runs):
        for key, job_id, run_id in runs:
            if key in run_results:
                continue
            try:
                run = _get_run_with_retry(ws, run_id)
            except Exception as e:
                print(f"  {key}: ERROR polling run_id={run_id}  {e}", file=sys.stderr)
                run_results[key] = "ERROR"
                continue
            state = _state_str(run.state.life_cycle_state if run.state else None)
            result = _state_str(run.state.result_state if run.state else None)
            if state == "TERMINATED":
                run_results[key] = result if result == "SUCCESS" else "FAILED"
                status = "SUCCESS" if result == "SUCCESS" else f"FAILED (result_state={result})"
                print(f"  {key}: {status}  run_id={run_id}")
            elif state in ("INTERNAL_ERROR", "SKIPPED"):
                run_results[key] = state
                msg = (run.state.state_message or "") if run.state else ""
                extra = f"  ({msg[:80]}...)" if len(msg or "") > 80 else (f"  ({msg})" if msg else "")
                print(f"  {key}: {state}  run_id={run_id}{extra}")
        if len(run_results) < len(runs):
            time.sleep(10)
    failed = [k for k, v in run_results.items() if v != "SUCCESS"]
    if failed:
        print(f"\nFailed jobs: {', '.join(failed)}", file=sys.stderr)
        # Hint for common catalog/schema error
        try:
            for key in failed:
                _, _, run_id = next((r for r in runs if r[0] == key), (None, None, None))
                if run_id is None:
                    continue
                run = ws.jobs.get_run(run_id)
                msg = (run.state.state_message or "") if run.state else ""
                if "catalog" in msg.lower() and ("not found" in msg.lower() or "cannot be found" in msg.lower()):
                    print(
                        "\nHint: Catalog/schema not found. Create the Unity Catalog (Data → Catalogs) and redeploy the bundle so the schema exists. See docs/DEPLOYMENT.md#fix-catalog-or-schema-not-found",
                        file=sys.stderr,
                    )
                    break
        except Exception:
            pass
        return 1
    print("\nAll jobs completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
