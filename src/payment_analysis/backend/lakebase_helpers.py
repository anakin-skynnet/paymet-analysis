"""Shared Lakebase Autoscaling utilities.

Centralises endpoint name construction, host resolution, and credential
generation so every consumer uses the correct SDK field paths.

SDK reference:
  - Host: ``endpoint.status.hosts.host`` (object, not a list)
  - State: ``endpoint.status.current_state``
  - Docs: https://docs.databricks.com/aws/en/oltp/projects/manage-computes
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


# ---------------------------------------------------------------------------
# Resource naming
# ---------------------------------------------------------------------------

def build_endpoint_name(project_id: str, branch_id: str, endpoint_id: str) -> str:
    """Build the hierarchical endpoint resource name expected by the Postgres API.

    Format: ``projects/{project_id}/branches/{branch_id}/endpoints/{endpoint_id}``
    """
    return f"projects/{project_id}/branches/{branch_id}/endpoints/{endpoint_id}"


# ---------------------------------------------------------------------------
# Host resolution
# ---------------------------------------------------------------------------

def resolve_endpoint_host(
    ws: WorkspaceClient,
    endpoint_name: str,
) -> str:
    """Fetch the endpoint and return its connection host.

    Raises ``ValueError`` if the endpoint has no host assigned (e.g. compute
    is suspended or still starting).

    Per the SDK docs the host lives at ``endpoint.status.hosts.host`` (the
    ``hosts`` attribute is an object, **not** a list).
    """
    postgres_api = _get_postgres_api(ws)
    endpoint = postgres_api.get_endpoint(name=endpoint_name)
    host = _extract_host(endpoint)
    if not host:
        raise ValueError(
            f"Lakebase endpoint {endpoint_name!r} has no host assigned. "
            "Ensure the compute is running (Compute → Lakebase)."
        )
    return host


def _extract_host(endpoint: object) -> str | None:
    """Extract connection host from an Endpoint object (safe attribute access)."""
    status = getattr(endpoint, "status", None)
    if status is None:
        return None
    hosts_obj = getattr(status, "hosts", None)
    return getattr(hosts_obj, "host", None) if hosts_obj else None


def get_endpoint_state(endpoint: object) -> str:
    """Extract ``current_state`` from an Endpoint object, falling back to ``state``."""
    status = getattr(endpoint, "status", None)
    if status is None:
        return "UNKNOWN"
    return (
        getattr(status, "current_state", None)
        or getattr(status, "state", None)
        or "UNKNOWN"
    )


# ---------------------------------------------------------------------------
# Postgres API guard
# ---------------------------------------------------------------------------

def _get_postgres_api(ws: WorkspaceClient):
    """Return ``ws.postgres`` or raise a clear error."""
    api = getattr(ws, "postgres", None)
    if api is None:
        raise AttributeError(
            "WorkspaceClient has no attribute 'postgres'. "
            "Lakebase Autoscaling requires databricks-sdk>=0.85.0 and a workspace with Lakebase enabled."
        )
    return api


# ---------------------------------------------------------------------------
# Schema-name validation (for raw SQL in notebooks / lakebase_config)
# ---------------------------------------------------------------------------

_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def validate_pg_identifier(name: str, label: str = "identifier") -> str:
    """Validate *name* as a safe Postgres identifier for use in quoted SQL.

    Prevents SQL injection when building ``"schema".table`` strings.
    Raises ``ValueError`` on invalid input; returns the validated name.
    """
    if not name or not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid Postgres {label}: {name!r}. "
            "Must be 1-128 chars: letters, digits, underscores; must start with a letter or underscore."
        )
    return name
