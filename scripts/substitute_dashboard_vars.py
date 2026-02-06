#!/usr/bin/env python3
"""
Substitute bundle variables in dashboard JSON files for deployment.

DAB does not substitute ${var.*} inside file_path contents, so Terraform
sees undeclared variable references. This script writes dashboard JSON
with resolved values to .build/dashboards/ for use by the bundle.

Usage:
  uv run python scripts/substitute_dashboard_vars.py
  BUNDLE_VAR_warehouse_id=<id> uv run python scripts/substitute_dashboard_vars.py

Reads variables from BUNDLE_VAR_* env or databricks.yml defaults.
If warehouse_id is "auto", attempts to resolve via `databricks sql warehouses list`.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def load_bundle_defaults(root: Path) -> dict:
    """Load default variable values from databricks.yml."""
    try:
        import yaml
    except ImportError:
        return {}
    yml = root / "databricks.yml"
    if not yml.exists():
        return {}
    with open(yml) as f:
        data = yaml.safe_load(f)
    variables = data.get("variables") or {}
    target_vars = {}
    for target_name, target_config in (data.get("targets") or {}).items():
        for k, v in (target_config.get("variables") or {}).items():
            target_vars[k] = v
    defaults = {}
    for name, config in variables.items():
        if isinstance(config, dict) and "default" in config:
            defaults[name] = config["default"]
        elif isinstance(config, dict):
            continue
        else:
            defaults[name] = config
    defaults.update(target_vars)
    return defaults


def _extract_warehouse_id(w: dict) -> str | None:
    sid = w.get("id") or w.get("warehouse_id")
    return str(sid) if sid is not None else None


def resolve_warehouse_id(warehouse_id: str, root: Path) -> str:
    """If warehouse_id is 'auto', try to get SQL warehouse id (by name or first in list)."""
    if warehouse_id != "auto":
        return warehouse_id
    try:
        out = subprocess.run(
            ["databricks", "warehouses", "list", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=root,
        )
        if out.returncode != 0:
            print("Warning: databricks warehouses list failed; using 'auto'", file=sys.stderr)
            return "auto"
        data = json.loads(out.stdout)
        warehouses = data if isinstance(data, list) else data.get("warehouses", data)
        if not isinstance(warehouses, list) or len(warehouses) == 0:
            print("Warning: no warehouses in list; using 'auto'", file=sys.stderr)
            return "auto"
        # Prefer one named like "[dev ...] Payment Analysis Warehouse" (bundle-created)
        for w in warehouses:
            if not isinstance(w, dict):
                continue
            name = w.get("name") or ""
            if "Payment Analysis Warehouse" in name:
                wid = _extract_warehouse_id(w)
                if wid:
                    return wid
        # Otherwise use first warehouse
        wid = _extract_warehouse_id(warehouses[0])
        if wid:
            return wid
    except Exception as e:
        print(f"Warning: could not resolve warehouse_id: {e}", file=sys.stderr)
    return "auto"


def get_variables(root: Path) -> tuple[str, str, str]:
    """Return (catalog, schema, warehouse_id) with env override and defaults."""
    defaults = load_bundle_defaults(root)
    catalog = os.environ.get("BUNDLE_VAR_catalog", defaults.get("catalog", "ahs_demos_catalog"))
    schema = os.environ.get("BUNDLE_VAR_schema", defaults.get("schema", "ahs_demo_payment_analysis_dev"))
    warehouse_id = os.environ.get("BUNDLE_VAR_warehouse_id", defaults.get("warehouse_id", "auto"))
    warehouse_id = resolve_warehouse_id(warehouse_id, root)
    return catalog, schema, warehouse_id


def substitute_in_content(content: str, catalog: str, schema: str, warehouse_id: str) -> str:
    """Replace ${var.catalog}, ${var.schema}, ${var.warehouse_id} in string."""
    # Replace combined pattern first (datasetName), then singles
    content = content.replace("${var.catalog}.${var.schema}", f"{catalog}.{schema}")
    content = content.replace("${var.catalog}", catalog)
    content = content.replace("${var.schema}", schema)
    content = content.replace("${var.warehouse_id}", warehouse_id)
    return content


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    source_dir = root / "resources" / "dashboards"
    build_dir = root / ".build" / "dashboards"

    catalog, schema, warehouse_id = get_variables(root)
    print(f"Using catalog={catalog!r}, schema={schema!r}, warehouse_id={warehouse_id!r}")

    if not source_dir.is_dir():
        print(f"Source directory not found: {source_dir}", file=sys.stderr)
        return 1

    build_dir.mkdir(parents=True, exist_ok=True)
    files = list(source_dir.glob("*.lvdash.json"))
    if not files:
        print(f"No *.lvdash.json found in {source_dir}", file=sys.stderr)
        return 1

    for path in sorted(files):
        content = path.read_text()
        new_content = substitute_in_content(content, catalog, schema, warehouse_id)
        out_path = build_dir / path.name
        out_path.write_text(new_content)
        print(f"  Wrote {out_path.relative_to(root)}")

    print(f"Substituted {len(files)} dashboard(s) into {build_dir.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
