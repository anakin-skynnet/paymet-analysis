"""Configuration for the payment-analysis Databricks App.

Workspace URL can be set via DATABRICKS_HOST or derived from the request Host when
the app is served from a Databricks Apps URL (see workspace_url_from_apps_host).
See: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/configuration
"""

import os
import re
from importlib import resources
from pathlib import Path
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from .._metadata import app_name, app_slug
except Exception:
    # Safe defaults for local tooling / before APX generates metadata.
    app_name = "payment-analysis"
    app_slug = "payment_analysis"

# Project root is the parent of the src folder; resolve for consistent paths.
project_root = Path(__file__).resolve().parent.parent.parent.parent
env_file = project_root / ".env"

if env_file.exists():
    # Optional dependency: allow clean checkouts to run without python-dotenv.
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_file)
    except Exception:
        pass


# Placeholder when DATABRICKS_HOST is unset; API must not return it so the UI can fall back to window.location.origin.
WORKSPACE_URL_PLACEHOLDER = "https://example.databricks.com"


def ensure_absolute_workspace_url(url: str) -> str:
    """Return workspace URL with scheme. If url is host-only (no scheme), prepend https:// so links open in the workspace, not relative to the app origin."""
    u = (url or "").strip().rstrip("/")
    if not u:
        return u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return f"https://{u}"


def workspace_url_from_apps_host(host: str, app_name_with_hyphen: str = "payment-analysis") -> str:
    """
    Derive the Databricks workspace URL from the request Host when the app is served from
    a Databricks Apps URL (e.g. payment-analysis-984752964297111.11.azure.databricksapps.com
    or payment_analysis-984752964297111.11.azure.databricksapps.com).
    Returns empty string if host is not a recognized Apps host pattern.
    """
    if not host:
        return ""
    host = host.split(":")[0].strip().lower()
    parts = host.split(".")
    # Try both hyphen and underscore app name (Apps URL may use either)
    prefixes = [f"{app_name_with_hyphen}-"]
    if "_" not in app_name_with_hyphen:
        prefixes.append(f"{app_name_with_hyphen.replace('-', '_')}-")
    # *.azure.databricksapps.com -> https://adb-<id>.<region>.azuredatabricks.net
    if len(parts) >= 5 and parts[-3] == "azure" and parts[-2] == "databricksapps" and parts[-1] == "com":
        first_label = parts[0]
        for prefix in prefixes:
            if first_label.startswith(prefix) and len(first_label) > len(prefix):
                suffix = first_label[len(prefix):]
                if len(parts) >= 2:
                    region = parts[1]
                    return f"https://adb-{suffix}.{region}.azuredatabricks.net"
    # *.databricksapps.com (AWS) - similar pattern if needed
    if len(parts) >= 3 and parts[-2] == "databricksapps" and parts[-1] == "com":
        first_label = parts[0]
        for prefix in prefixes:
            if first_label.startswith(prefix) and len(first_label) > len(prefix):
                suffix = first_label[len(prefix):]
                return f"https://{suffix}.cloud.databricks.com"
    return ""


def workspace_id_from_workspace_url(workspace_url: str) -> str | None:
    """
    Derive workspace ID from workspace URL when DATABRICKS_WORKSPACE_ID is not set.
    Azure: https://adb-984752964297111.11.azuredatabricks.net -> 984752964297111
    AWS: https://dbc-a1b2c3d4-e5f6.cloud.databricks.com -> a1b2c3d4-e5f6 (return as-is).
    """
    if not workspace_url:
        return None
    host = (workspace_url or "").strip().rstrip("/").lower()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/")[0].split(":")[0]
    # Azure: adb-<number>.<region>.azuredatabricks.net
    m = re.match(r"^adb-(\d+)\.", host)
    if m:
        return m.group(1)
    # AWS: dbc-xxx-yyy.cloud.databricks.com
    m = re.match(r"^(dbc-[a-z0-9-]+)\.", host)
    if m:
        return m.group(1)
    return None


# Default entity/country code for analytics filters (e.g. reason codes, smart checkout). UI and Lakehouse can override.
DEFAULT_ENTITY = "BR"

# Canonical schema name — always "payment_analysis" (no per-user prefix).
SCHEMA_BASE_NAME = "payment_analysis"


def get_default_schema() -> str:
    """Unity Catalog schema name. Uses DATABRICKS_SCHEMA env var if set; else returns 'payment_analysis'."""
    explicit = os.getenv("DATABRICKS_SCHEMA", "").strip()
    if explicit:
        return explicit
    return SCHEMA_BASE_NAME


# Reference workspace and Lakeview dashboard (Azure) for aligning app dashboard links.
# When set, executive_overview uses the Lakeview v3 published URL: /dashboardsv3/<id>/published?o=<workspace_id>
# Override via env: DATABRICKS_REFERENCE_WORKSPACE_HOST, DATABRICKS_REFERENCE_WORKSPACE_ID, DATABRICKS_REFERENCE_LAKEVIEW_ID_EXECUTIVE
REFERENCE_WORKSPACE_HOST = os.getenv("DATABRICKS_REFERENCE_WORKSPACE_HOST", "")
REFERENCE_WORKSPACE_ID = os.getenv("DATABRICKS_REFERENCE_WORKSPACE_ID", "")
REFERENCE_LAKEVIEW_DASHBOARD_ID_EXECUTIVE = os.getenv("DATABRICKS_REFERENCE_LAKEVIEW_ID_EXECUTIVE", "")


class DatabricksConfig(BaseSettings):
    """Databricks workspace configuration."""
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore",
    )
    workspace_url: str = Field(
        default=WORKSPACE_URL_PLACEHOLDER,
        description="Databricks workspace URL",
        validation_alias="DATABRICKS_HOST"
    )
    workspace_id: str | None = Field(
        default=None,
        description="Workspace ID (e.g. for dashboard embed URL query param 'o'). Set DATABRICKS_WORKSPACE_ID.",
        validation_alias="DATABRICKS_WORKSPACE_ID",
    )
    lakeview_id_executive_overview: str | None = Field(
        default=None,
        description="Lakeview dashboard ID for Executive Overview (dashboardsv3 URL). Set DATABRICKS_LAKEVIEW_ID_EXECUTIVE_OVERVIEW. When unset, reference ID may be used if workspace matches.",
        validation_alias="DATABRICKS_LAKEVIEW_ID_EXECUTIVE_OVERVIEW",
    )


class DatabaseConfig(BaseSettings):
    """Postgres / Databricks SQL warehouse database configuration."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore",
    )
    port: int = Field(
        description="The port of the database", default=5432, validation_alias="PGPORT"
    )
    database_name: str = Field(
        description="Postgres database name inside the Lakebase instance (match bundle lakebase_database_name)",
        default="payment_analysis",
        validation_alias="LAKEBASE_DATABASE_NAME",
    )
    postgres_project_id: str = Field(
        default="",
        description="Lakebase Autoscaling project ID (required with postgres_branch_id and postgres_endpoint_id; set in app Environment).",
        validation_alias="LAKEBASE_PROJECT_ID",
    )
    postgres_branch_id: str = Field(
        default="",
        description="Lakebase Autoscaling branch ID.",
        validation_alias="LAKEBASE_BRANCH_ID",
    )
    postgres_endpoint_id: str = Field(
        default="",
        description="Lakebase Autoscaling endpoint ID (compute).",
        validation_alias="LAKEBASE_ENDPOINT_ID",
    )
    db_schema: str = Field(
        default="payment_analysis",
        description="Postgres schema for app tables (avoid 'public' if app has no CREATE there). Set LAKEBASE_SCHEMA.",
        validation_alias="LAKEBASE_SCHEMA",
    )
    connection_string: str = Field(
        default="",
        description="Optional direct Postgres URL for Lakebase (e.g. postgresql://user@host/databricks_postgres?sslmode=require). When set, app uses this instead of project/branch/endpoint discovery. Set LAKEBASE_OAUTH_TOKEN in Environment as the password (never commit the token).",
        validation_alias="LAKEBASE_CONNECTION_STRING",
    )


class AppConfig(BaseSettings):
    """Application settings: app name, database, and Databricks workspace config."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=env_file,
        env_prefix=f"{app_slug.upper()}_",
        extra="ignore",
        env_nested_delimiter="__",
    )
    app_name: str = Field(default=app_name)
    db: DatabaseConfig = DatabaseConfig()
    databricks: DatabricksConfig = DatabricksConfig()

    @property
    def static_assets_path(self) -> Path:
        return Path(str(resources.files(app_slug))).joinpath("__dist__")

    def __hash__(self) -> int:
        return hash(self.app_name)
