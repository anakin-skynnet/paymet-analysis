#!/usr/bin/env python3
"""Verify that package versions match across pyproject.toml, uv.lock, requirements.txt, and requirements-databricks-minimal.txt."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIREMENTS_FILES = ("requirements.txt", "requirements-databricks-minimal.txt")


def parse_pyproject_versions() -> dict[str, str]:
    """Extract dependency versions from pyproject.toml (project.dependencies)."""
    path = REPO_ROOT / "pyproject.toml"
    text = path.read_text()
    deps: dict[str, str] = {}
    # Match "name==X.Y.Z" or "name[extras]==X.Y.Z"
    for m in re.finditer(r'^\s*"([a-zA-Z0-9_-]+)(?:\[[^\]]*\])?\s*==\s*([^"]+)"', text, re.MULTILINE):
        name = m.group(1).lower().replace("_", "-")
        deps[name] = m.group(2).strip()
    return deps


def parse_uv_lock_versions() -> dict[str, str]:
    """Extract package name -> version from uv.lock."""
    path = REPO_ROOT / "uv.lock"
    text = path.read_text()
    deps: dict[str, str] = {}
    name = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("name = "):
            name = line.split("=", 1)[1].strip().strip('"')
        elif name and line.startswith("version = "):
            version = line.split("=", 1)[1].strip().strip('"')
            deps[name] = version
            name = None
    return deps


def parse_requirements_versions(path: Path) -> dict[str, str]:
    """Extract package==version from a requirements file (skip comments and empty lines)."""
    if not path.exists():
        return {}
    deps: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" in line:
            name, version = line.split("==", 1)
            deps[name.strip().lower().replace("_", "-")] = version.strip()
    return deps


def main() -> int:
    pyproject = parse_pyproject_versions()
    lock = parse_uv_lock_versions()

    errors: list[str] = []
    all_reqs: dict[str, str] = {}

    for req_file in REQUIREMENTS_FILES:
        path = REPO_ROOT / req_file
        reqs = parse_requirements_versions(path)
        for name, req_version in reqs.items():
            all_reqs[name] = req_version
            if name not in lock:
                errors.append(f"{req_file} has {name}=={req_version} but uv.lock has no package '{name}'")
            elif lock[name] != req_version:
                errors.append(
                    f"Version mismatch: {name} {req_file}=={req_version} vs uv.lock=={lock[name]}"
                )

    reqs = all_reqs

    # Direct deps from pyproject should be in lock and match
    for name, proj_version in pyproject.items():
        if name not in lock:
            errors.append(f"pyproject.toml depends on {name}=={proj_version} but uv.lock has no '{name}'")
        elif lock[name] != proj_version:
            errors.append(
                f"Version mismatch: {name} pyproject.toml=={proj_version} vs uv.lock=={lock[name]}"
            )

    if errors:
        print("Version verification FAILED:\n")
        for e in errors:
            print(f"  • {e}")
        return 1

    print("Version verification passed.")
    print("  pyproject.toml direct deps:", len(pyproject))
    print("  uv.lock packages:", len(lock))
    print("  requirements files:", ", ".join(REQUIREMENTS_FILES))
    print("  combined pinned packages:", len(reqs))
    print("\nAll requirements vs uv.lock (must match):")
    for name in sorted(reqs.keys()):
        print(f"  {name}=={reqs[name]}  (lock: {lock.get(name, 'MISSING')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
