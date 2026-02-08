from importlib import resources
from pathlib import Path
from typing import ClassVar
import os

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
    a Databricks Apps URL (e.g. payment-analysis-984752964297111.11.azure.databricksapps.com).
    Returns empty string if host is not a recognized Apps host pattern.
    """
    if not host:
        return ""
    host = host.split(":")[0].strip().lower()
    parts = host.split(".")
    # *.azure.databricksapps.com -> https://adb-<id>.<region>.azuredatabricks.net
    if len(parts) >= 5 and parts[-3] == "azure" and parts[-2] == "databricksapps" and parts[-1] == "com":
        first_label = parts[0]
        prefix = f"{app_name_with_hyphen}-"
        if first_label.startswith(prefix) and len(first_label) > len(prefix):
            suffix = first_label[len(prefix):]
            if len(parts) >= 2:
                region = parts[1]
                return f"https://adb-{suffix}.{region}.azuredatabricks.net"
    # *.databricksapps.com (AWS) - similar pattern if needed
    if len(parts) >= 3 and parts[-2] == "databricksapps" and parts[-1] == "com":
        first_label = parts[0]
        prefix = f"{app_name_with_hyphen}-"
        if first_label.startswith(prefix) and len(first_label) > len(prefix):
            suffix = first_label[len(prefix):]
            return f"https://{suffix}.cloud.databricks.com"
    return ""

# Default entity/country code for analytics filters (e.g. reason codes, smart checkout). UI and Lakehouse can override.
DEFAULT_ENTITY = "BR"


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
    workspace_path: str = Field(
        description="Workspace deployment path",
        default="/Workspace/Users/${workspace.current_user.userName}/payment-analysis"
    )

    def get_notebook_path(self, relative_path: str) -> str:
        """Construct full notebook workspace path dynamically."""
        user_email = os.getenv("DATABRICKS_USER", "${workspace.current_user.userName}")
        folder = os.getenv("BUNDLE_FOLDER", "payment-analysis")
        base_path = f"/Workspace/Users/{user_email}/{folder}/files"
        return f"{base_path}/{relative_path}"
    
    def get_workspace_url(self, path: str) -> str:
        """Construct full workspace URL dynamically."""
        return f"{self.workspace_url}/workspace{path}"


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
    instance_name: str = Field(
        default="",
        description="The name of the Lakebase/database instance (set PGAPPNAME in Databricks App)",
        validation_alias="PGAPPNAME",
    )
    db_schema: str = Field(
        default="app",
        description="Postgres schema for app tables (avoid 'public' if app has no CREATE there). Set LAKEBASE_SCHEMA.",
        validation_alias="LAKEBASE_SCHEMA",
    )


class AppConfig(BaseSettings):
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
