import os
from functools import cached_property

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from sqlalchemy import Engine, create_engine, event
from sqlmodel import SQLModel, Session, text

from .config import AppConfig
from .lakebase_helpers import discover_endpoint_name, resolve_endpoint_host, _get_postgres_api
from .logger import logger


class Runtime:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    @cached_property
    def _dev_db_port(self) -> int | None:
        """Check for APX_DEV_DB_PORT environment variable for local development."""
        port = os.environ.get("APX_DEV_DB_PORT")
        return int(port) if port else None

    @cached_property
    def ws(self) -> WorkspaceClient:
        # When PAT is set, use explicit host+token+auth_type=pat so the SDK does not
        # read DATABRICKS_CLIENT_ID/SECRET from env and trigger OAuth scope errors.
        host = (self.config.databricks.workspace_url or "").strip().rstrip("/")
        token = os.environ.get("DATABRICKS_TOKEN")
        if host and token and "example.databricks.com" not in host:
            from .databricks_client_helpers import workspace_client_pat_only

            return workspace_client_pat_only(host=host, token=token)
        # Otherwise use default (e.g. DATABRICKS_CONFIG_PROFILE or OAuth in dev)
        return WorkspaceClient()

    def _use_lakebase_autoscaling(self) -> bool:
        """True if Lakebase Autoscaling (postgres project/branch/endpoint) is configured."""
        c = self.config.db
        return bool(
            c.postgres_project_id and c.postgres_branch_id and c.postgres_endpoint_id
        )

    def _db_configured(self) -> bool:
        """True if a database is configured (local dev or Lakebase Autoscaling)."""
        if self._dev_db_port:
            return True
        return self._use_lakebase_autoscaling()

    @cached_property
    def _endpoint_name(self) -> str:
        """Actual Lakebase endpoint resource name (auto-discovers if configured name doesn't match).

        Lakebase auto-generates endpoint names (e.g. ep-xxx) when a project is
        created. The configured endpoint_id may not match, so we discover the
        actual endpoint name on the branch.
        """
        c = self.config.db
        return discover_endpoint_name(self.ws, c.postgres_project_id, c.postgres_branch_id, c.postgres_endpoint_id)

    @cached_property
    def engine_url(self) -> str:
        # Check if we're in local dev mode with APX_DEV_DB_PORT
        if self._dev_db_port:
            logger.info(f"Using local dev database at localhost:{self._dev_db_port}")
            username = "postgres"
            password = os.environ.get("APX_DEV_DB_PWD")
            if password is None:
                raise ValueError(
                    "APX server didn't provide a password, please check the dev server logs"
                )
            return f"postgresql+psycopg://{username}:{password}@localhost:{self._dev_db_port}/postgres?sslmode=disable"

        # Production: Lakebase Autoscaling only (created by Job 1 create_lakebase_autoscaling)
        if not self._db_configured():
            raise ValueError(
                "Database not configured. Set LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID "
                "in the app Environment (same values as Job 1 create_lakebase_autoscaling)."
            )
        prefix = "postgresql+psycopg"
        port = self.config.db.port
        # Lakebase Autoscaling projects always have a default "databricks_postgres" database.
        # The config may say "payment_analysis" (the Postgres *schema*); map to the real DB name.
        database = (self.config.db.database_name or "").strip()
        database = "databricks_postgres" if database in ("", "payment_analysis") else database
        username = (
            self.ws.config.client_id
            if self.ws.config.client_id
            else (self.ws.current_user.me().user_name if self.ws.current_user else "postgres")
        )
        logger.info("Using Lakebase Autoscaling (postgres): %s", self._endpoint_name)
        host = resolve_endpoint_host(self.ws, self._endpoint_name)
        return f"{prefix}://{username}:@{host}:{port}/{database}"

    def _before_connect(self, dialect, conn_rec, cargs, cparams):
        """SQLAlchemy ``do_connect`` hook — inject a fresh OAuth token per connection."""
        postgres_api = _get_postgres_api(self.ws)
        cred = postgres_api.generate_database_credential(endpoint=self._endpoint_name)
        cparams["password"] = cred.token

    @cached_property
    def engine(self) -> Engine:
        if not self._db_configured():
            raise ValueError(
                "Database not configured. Set LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID in the app Environment."
            )
        # In dev mode: no SSL, no password callback, single connection (PGlite limit)
        # In production: require SSL and use Databricks credential callback
        if self._dev_db_port:
            engine = create_engine(
                self.engine_url,
                pool_recycle=10,
                pool_size=4,
            )
        else:
            # Lakebase: token injected per connection (OAuth expires ~1h). pool_recycle < 1h.
            # See https://apps-cookbook.dev/docs/fastapi/getting_started/lakebase_connection
            engine = create_engine(
                self.engine_url,
                pool_recycle=45 * 60,
                connect_args={"sslmode": "require"},
                pool_size=4,
            )
            event.listens_for(engine, "do_connect")(self._before_connect)
        return engine

    def get_session(self) -> Session:
        if not self._db_configured():
            raise RuntimeError(
                "Database not configured. Set LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID in the app Environment."
            )
        return Session(self.engine)

    def validate_db(self) -> None:
        if not self._db_configured():
            logger.info("Database not configured (LAKEBASE_* unset); skipping validation.")
            return
        # In dev mode, skip Databricks-specific validation
        if self._dev_db_port:
            logger.info(
                f"Validating local dev database connection at localhost:{self._dev_db_port}"
            )
        else:
            # _endpoint_name uses discover_endpoint_name() which already
            # validates the endpoint exists (tries configured name, then
            # lists endpoints on the branch). If it raises ValueError,
            # no endpoints exist at all.
            try:
                endpoint_name = self._endpoint_name
            except ValueError as e:
                raise ValueError(
                    f"Lakebase Autoscaling endpoint not found. {e} "
                    "Run Job 1 create_lakebase_autoscaling first."
                ) from e
            logger.info("Validating Lakebase Autoscaling endpoint: %s", endpoint_name)

        # check if a connection to the database can be established
        try:
            with self.get_session() as session:
                session.connection().execute(text("SELECT 1"))
                session.close()

        except Exception as db_err:
            err_msg = str(db_err).lower()
            if "password authentication failed" in err_msg:
                raise ConnectionError(
                    "Postgres authentication failed. The app's service principal likely "
                    "does not have a Lakebase Postgres role. Re-run Job 1 "
                    "(lakebase_data_init) to auto-create the role, or manually run: "
                    "CREATE EXTENSION IF NOT EXISTS databricks_auth; "
                    "SELECT databricks_create_role('<sp-application-id>', 'SERVICE_PRINCIPAL');"
                ) from db_err
            raise ConnectionError(
                f"Failed to connect to the database: {db_err}"
            ) from db_err

        if self._dev_db_port:
            logger.info("Local dev database connection validated successfully")
        else:
            logger.info("Lakebase Autoscaling database connection validated successfully")

    def initialize_models(self) -> None:
        if not self._db_configured():
            logger.info("Database not configured; skipping table creation.")
            return
        raw_schema = (self.config.db.db_schema or "payment_analysis").strip()
        schema_name = raw_schema if raw_schema.replace("_", "").isalnum() else "payment_analysis"
        logger.info("Initializing database models (schema=%s)", schema_name)
        # Ensure SQLModel tables are registered before create_all().
        # Import is intentionally inside the method to avoid import-time side effects.
        from . import db_models  # noqa: F401

        # Use a dedicated schema so we don't need CREATE on public (Lakebase often denies public).
        # Tables are created at import time with schema=None; we must set each table's schema
        # so create_all() emits CREATE TABLE "schema".table, not public.
        SQLModel.metadata.schema = schema_name
        for table in SQLModel.metadata.tables.values():
            table.schema = schema_name
        with self.engine.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            conn.commit()
        SQLModel.metadata.create_all(self.engine)
        logger.info("Database models initialized successfully")
