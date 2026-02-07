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


class DatabricksConfig(BaseSettings):
    """Databricks workspace configuration."""
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore",
    )
    workspace_url: str = Field(
        default="https://example.databricks.com",
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


class AppConfig(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=env_file,
        env_prefix=f"{app_slug.upper()}_",
        extra="ignore",
        env_nested_delimiter="__",
    )
    app_name: str = Field(default=app_name)
    db: DatabaseConfig = DatabaseConfig()  # type: ignore
    databricks: DatabricksConfig = DatabricksConfig()

    @property
    def static_assets_path(self) -> Path:
        return Path(str(resources.files(app_slug))).joinpath("__dist__")

    def __hash__(self) -> int:
        return hash(self.app_name)
