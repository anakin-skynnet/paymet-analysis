#!/usr/bin/env python3
"""
Publish all Payment Analysis dashboards in the workspace.

Lakeview dashboards deployed by the bundle are in draft by default. This script
lists dashboards under the bundle's workspace path ( .../payment-analysis/dashboards )
and publishes each with embed_credentials so they can be viewed without per-user warehouse auth.

Requires: Databricks CLI configured. Run after deploy: ./scripts/deploy.sh dev
Usage:
  uv run python scripts/publish_dashboards.py [--path /Workspace/Users/.../payment-analysis]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

PUBLISH_TIMEOUT = 60


def get_workspace_root() -> str | None:
    try:
        result = subprocess.run(
            ["databricks", "bundle", "validate", "-t", "dev"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Path is printed even when validate fails (e.g. missing .build)
        for line in result.stdout.splitlines() + result.stderr.splitlines():
            m = re.search(r"Path:\s*(\S+)", line, re.I)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish all Payment Analysis dashboards")
    parser.add_argument(
        "--path",
        default=None,
        help="Workspace root path (e.g. /Workspace/Users/you/payment-analysis). Default: from bundle validate.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only list dashboards, do not publish")
    args = parser.parse_args()

    root = args.path or get_workspace_root()
    if not root:
        print(
            "Error: could not get workspace path. Run from repo root after deploy, or pass --path /Workspace/Users/.../payment-analysis",
            file=sys.stderr,
        )
        return 1

    dashboards_path = f"{root.rstrip('/')}/dashboards"

    try:
        result = subprocess.run(
            ["databricks", "workspace", "list", dashboards_path, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        result.check_returncode()
        objects = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("Error: workspace list timed out", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse workspace list: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("Error: databricks CLI not found.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"Error: workspace list failed: {e.stderr or e}. Is the path correct? Deploy first: ./scripts/deploy.sh dev", file=sys.stderr)
        return 1

    if not isinstance(objects, list):
        objects = []

    dashboards = [o for o in objects if o.get("object_type") == "DASHBOARD"]
    if not dashboards:
        print(f"No dashboards found under {dashboards_path}. Deploy first: ./scripts/deploy.sh dev")
        return 0

    print(f"Found {len(dashboards)} dashboard(s) under {dashboards_path}:")
    for o in dashboards:
        name = o.get("path", "").split("/")[-1].replace(".lvdash.json", "")
        print(f"  - {o.get('resource_id')}  {name}")

    if args.dry_run:
        print("Dry run: skipping publish.")
        return 0

    failed = []
    for o in dashboards:
        did = o.get("resource_id")
        name = o.get("path", did).split("/")[-1]
        if not did:
            continue
        try:
            subprocess.run(
                ["databricks", "lakeview", "publish", did, "--embed-credentials"],
                check=True,
                capture_output=True,
                text=True,
                timeout=PUBLISH_TIMEOUT,
            )
            print(f"Published: {name}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to publish {name}: {e.stderr or e}", file=sys.stderr)
            failed.append(name)
        except subprocess.TimeoutExpired:
            print(f"Timeout publishing {name}", file=sys.stderr)
            failed.append(name)

    if failed:
        print(f"Failed: {len(failed)} dashboard(s).", file=sys.stderr)
        return 1
    print(f"Successfully published {len(dashboards)} dashboard(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
