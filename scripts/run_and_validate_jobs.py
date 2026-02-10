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
  uv run python scripts/run_and_validate_jobs.py [--dry-run] [--job KEY] [--no-wait] [--results-file PATH]
  uv run python scripts/run_and_validate_jobs.py status [--results-file PATH] [--once]
  DATABRICKS_HOST=... DATABRICKS_TOKEN=... uv run python scripts/run_and_validate_jobs.py

Options:
  --dry-run        List matched jobs only, do not run.
  --job KEY        Run only this job key (e.g. job_1_create_data_repositories).
  --no-wait        Start runs but do not wait for completion.
  --results-file   Write run_id per key (JSON) so "status" can poll later.
  status           Poll run status from last --results-file. Use --once to report current state and exit (no wait).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_FILE = REPO_ROOT / ".databricks_job_runs.json"
MAX_POLL_RETRIES = 6
POLL_RETRY_DELAY = 30


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
    "job_6_deploy_agents": "6. Deploy AgentBricks",
    "job_7_genie_sync": "7. Genie Space Sync",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and validate payment-analysis Databricks jobs")
    parser.add_argument("--dry-run", action="store_true", help="List jobs only, do not run")
    parser.add_argument("--job", type=str, metavar="KEY", help="Run only this job key")
    parser.add_argument("--no-wait", action="store_true", help="Start runs but do not wait")
    parser.add_argument("--results-file", type=str, default=str(DEFAULT_RESULTS_FILE), help="Write/read run IDs (JSON) for status command")
    parser.add_argument("command", nargs="?", choices=["status"], help="Use 'status' to poll runs from last --results-file")
    parser.add_argument("--once", action="store_true", help="(status only) Report current state once and exit without waiting for all to complete")
    args = parser.parse_args()

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
                if key in run_results and not once:
                    continue
                if key in run_results and once:
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
        if failed and not once:
            print(f"\nFailed jobs: {', '.join(failed)}", file=sys.stderr)
            return 1
        if failed and once:
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

    if not key_to_job:
        print("No payment-analysis jobs found in workspace.", file=sys.stderr)
        return 1

    print("Matched jobs:")
    for key in sorted(key_to_job):
        jid, name = key_to_job[key]
        print(f"  {key}: {jid}  {name[:60]}...")
    if args.dry_run:
        return 0

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
