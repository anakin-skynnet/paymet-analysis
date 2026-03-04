import os
from functools import cached_property
from urllib.parse import urlparse, urlunparse

from databricks.sdk import WorkspaceClient
from sqlalchemy import Engine, create_engine, event
from sqlmodel import SQLModel, Session, text

from .config import AppConfig
from .lakebase_helpers import discover_endpoint_name, resolve_endpoint_host, _get_postgres_api
from .logger import logger


def _normalize_lakebase_url(raw: str) -> str:
    """Ensure URL uses postgresql+psycopg for SQLAlchemy; leave password empty for injection via do_connect."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme == "postgresql" and "psycopg" not in raw:
        # Replace postgresql:// with postgresql+psycopg://
        parsed = parsed._replace(scheme="postgresql+psycopg")
    return urlunparse(parsed)


class Runtime:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    @cached_property
    def _dev_db_port(self) -> int | None:
        """Check for APX_DEV_DB_PORT environment variable for local development."""
        port = os.environ.get("APX_DEV_DB_PORT")
        if not port:
            return None
        try:
            return int(port)
        except ValueError:
            logger.warning("Invalid APX_DEV_DB_PORT=%r — must be a valid integer, ignoring", port)
            return None

    def _use_lakebase_direct_connection(self) -> bool:
        """True if LAKEBASE_CONNECTION_STRING is set (direct Postgres URL + LAKEBASE_OAUTH_TOKEN as password)."""
        return bool((self.config.db.connection_string or "").strip())

    @cached_property
    def ws(self) -> WorkspaceClient:
        # Prefer PAT, then service principal (DATABRICKS_CLIENT_ID/SECRET from Apps).
        host = (self.config.databricks.workspace_url or "").strip().rstrip("/")
        token = os.environ.get("DATABRICKS_TOKEN")
        if host and "example.databricks.com" not in host:
            from .databricks_client_helpers import workspace_client_pat_only, workspace_client_service_principal

            if token:
                return workspace_client_pat_only(host=host, token=token)
            client_id = os.environ.get("DATABRICKS_CLIENT_ID")
            client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")
            if client_id and client_secret:
                return workspace_client_service_principal(host=host, client_id=client_id, client_secret=client_secret)
        # Otherwise use default (e.g. DATABRICKS_CONFIG_PROFILE or OAuth in dev)
        return WorkspaceClient()

    def _use_lakebase_autoscaling(self) -> bool:
        """True if Lakebase Autoscaling (postgres project/branch/endpoint) is configured."""
        c = self.config.db
        return bool(
            c.postgres_project_id and c.postgres_branch_id and c.postgres_endpoint_id
        )

    def _db_configured(self) -> bool:
        """True if a database is configured (local dev, direct connection string, or Lakebase Autoscaling)."""
        if self._dev_db_port:
            return True
        if self._use_lakebase_direct_connection():
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
            logger.info("Using local dev database at localhost:%s", self._dev_db_port)
            username = "postgres"
            password = os.environ.get("APX_DEV_DB_PWD")
            if password is None:
                raise ValueError(
                    "APX server didn't provide a password, please check the dev server logs"
                )
            return f"postgresql+psycopg://{username}:{password}@localhost:{self._dev_db_port}/postgres?sslmode=disable"

        # Direct Lakebase connection via LAKEBASE_CONNECTION_STRING (password injected from LAKEBASE_OAUTH_TOKEN)
        if self._use_lakebase_direct_connection():
            url = _normalize_lakebase_url(self.config.db.connection_string)
            if not url:
                raise ValueError("LAKEBASE_CONNECTION_STRING is set but empty or invalid.")
            # Ensure sslmode=require for Lakebase; do not embed password in URL (injected in _before_connect)
            if "sslmode=" not in url:
                url = f"{url}&sslmode=require" if "?" in url else f"{url}?sslmode=require"
            logger.info("Using Lakebase direct connection (LAKEBASE_CONNECTION_STRING).")
            return url

        # Production: Lakebase Autoscaling via project/branch/endpoint (created by Job 1 create_lakebase_autoscaling)
        if not self._db_configured():
            raise ValueError(
                "Database not configured. Set LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID "
                "or LAKEBASE_CONNECTION_STRING (and LAKEBASE_OAUTH_TOKEN) in the app Environment."
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
        """SQLAlchemy ``do_connect`` hook — inject OAuth token per connection (from env for direct URL, or from SDK for Autoscaling)."""
        if self._use_lakebase_direct_connection():
            token = os.environ.get("LAKEBASE_OAUTH_TOKEN", "").strip()
            if token:
                cparams["password"] = token
            return
        postgres_api = _get_postgres_api(self.ws)
        cred = postgres_api.generate_database_credential(endpoint=self._endpoint_name)
        cparams["password"] = cred.token

    @cached_property
    def _db_schema_name(self) -> str:
        """Validated Postgres schema name used for search_path and SQLModel."""
        raw = (self.config.db.db_schema or "payment_analysis").strip()
        return raw if raw.replace("_", "").isalnum() else "payment_analysis"

    @cached_property
    def engine(self) -> Engine:
        if not self._db_configured():
            raise ValueError(
                "Database not configured. Set LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID "
                "or LAKEBASE_CONNECTION_STRING (and LAKEBASE_OAUTH_TOKEN) in the app Environment."
            )
        schema = self._db_schema_name
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
            # Set search_path so unqualified table names resolve to the app schema.
            engine = create_engine(
                self.engine_url,
                pool_recycle=45 * 60,
                connect_args={
                    "sslmode": "require",
                    "options": f"-csearch_path={schema},public",
                },
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
            logger.info("Validating local dev database at localhost:%s", self._dev_db_port)
        elif self._use_lakebase_direct_connection():
            logger.info("Validating Lakebase direct connection (LAKEBASE_CONNECTION_STRING).")
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

    def register_model_schemas(self) -> None:
        """Set the Postgres schema on all SQLModel tables so queries use qualified names.

        Must be called early (even before DB is reachable) so that SELECT/INSERT
        statements emit "schema".table instead of unqualified table names that
        default to the 'public' schema.
        """
        schema_name = self._db_schema_name
        # Import registers all table classes with SQLModel.metadata.
        from . import db_models  # noqa: F401

        SQLModel.metadata.schema = schema_name
        for table in SQLModel.metadata.tables.values():
            table.schema = schema_name
        logger.info("SQLModel schemas set to '%s' for %d table(s)", schema_name, len(SQLModel.metadata.tables))

    def initialize_models(self) -> None:
        if not self._db_configured():
            logger.info("Database not configured; skipping table creation.")
            return
        schema_name = self._db_schema_name
        logger.info("Initializing database models (schema=%s)", schema_name)

        # Ensure schemas are set (idempotent; may already be called).
        self.register_model_schemas()

        # Only create the schema in local dev. In Lakebase, the schema is created by Job 1
        # (lakebase_data_init); the app's service principal has no database-level CREATE
        # privilege (permission denied for database databricks_postgres).
        if self._dev_db_port:
            with self.engine.connect() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
                conn.commit()

        SQLModel.metadata.create_all(self.engine)
        logger.info("Database models initialized successfully")
