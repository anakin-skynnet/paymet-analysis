"""Shared API response models: version, workspace config, auth status."""

from pydantic import BaseModel

from .. import __version__


class VersionOut(BaseModel):
    version: str

    @classmethod
    def from_metadata(cls):
        return cls(version=__version__)


class WorkspaceConfigOut(BaseModel):
    """Workspace URL for building links to jobs, pipelines, dashboards, etc."""

    workspace_url: str


class AuthStatusOut(BaseModel):
    """Whether the request is authenticated (e.g. via Databricks user authorization / OBO)."""

    authenticated: bool
