import os
import uuid
from functools import cached_property

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from sqlalchemy import Engine, create_engine, event
from sqlmodel import SQLModel, Session, text

from .config import AppConfig
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
        """True if a database is configured (local dev, Lakebase Autoscaling, or Provisioned)."""
        if self._dev_db_port:
            return True
        if self._use_lakebase_autoscaling():
            return True
        return bool(self.config.db.instance_name and self.config.db.instance_name.strip())

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

        # Production: Lakebase Autoscaling (postgres) or Provisioned (database instance)
        if not self._db_configured():
            raise ValueError(
                "Database not configured. Set Lakebase Autoscaling (LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID) "
                "or PGAPPNAME to your Lakebase instance name (Databricks App)."
            )
        prefix = "postgresql+psycopg"
        port = self.config.db.port
        database = self.config.db.database_name or "databricks_postgres"
        username = (
            self.ws.config.client_id
            if self.ws.config.client_id
            else (self.ws.current_user.me().user_name if self.ws.current_user else "postgres")
        )

        if self._use_lakebase_autoscaling():
            postgres_api = getattr(self.ws, "postgres", None)
            if postgres_api is None:
                raise AttributeError(
                    "WorkspaceClient has no attribute 'postgres'. Lakebase Autoscaling requires "
                    "databricks-sdk==0.84.0. Upgrade the app's databricks-sdk dependency."
                )
            endpoint_name = (
                f"projects/{self.config.db.postgres_project_id}/branches/"
                f"{self.config.db.postgres_branch_id}/endpoints/{self.config.db.postgres_endpoint_id}"
            )
            logger.info("Using Lakebase Autoscaling (postgres): %s", endpoint_name)
            endpoint = postgres_api.get_endpoint(name=endpoint_name)
            status = getattr(endpoint, "status", None)
            hosts = getattr(status, "hosts", None) if status else None
            if hosts is not None and isinstance(hosts, list) and len(hosts) > 0:
                host = getattr(hosts[0], "host", None) or getattr(hosts[0], "hostname", None)
            else:
                host = (
                    getattr(hosts, "host", None) or getattr(hosts, "hostname", None)
                    if hosts
                    else None
                )
            if not host:
                raise ValueError("Lakebase Autoscaling endpoint has no host; ensure the compute is running.")
            return f"{prefix}://{username}:@{host}:{port}/{database}"
        # Provisioned (Database Instances API)
        db_api = getattr(self.ws, "database", None)
        if db_api is None:
            raise AttributeError(
                "WorkspaceClient has no attribute 'database'. Use Lakebase Autoscaling (set "
                "LAKEBASE_PROJECT_ID, LAKEBASE_BRANCH_ID, LAKEBASE_ENDPOINT_ID) or upgrade databricks-sdk."
            )
        logger.info("Using Databricks Lakebase instance: %s", self.config.db.instance_name)
        instance = db_api.get_database_instance(name=self.config.db.instance_name)
        host = instance.read_write_dns
        return f"{prefix}://{username}:@{host}:{port}/{database}"

    def _before_connect(self, dialect, conn_rec, cargs, cparams):
        if self._use_lakebase_autoscaling():
            postgres_api = getattr(self.ws, "postgres", None)
            if postgres_api is None:
                raise AttributeError(
                    "WorkspaceClient has no attribute 'postgres'. Lakebase Autoscaling requires databricks-sdk==0.84.0."
                )
            endpoint_name = (
                f"projects/{self.config.db.postgres_project_id}/branches/"
                f"{self.config.db.postgres_branch_id}/endpoints/{self.config.db.postgres_endpoint_id}"
            )
            cred = postgres_api.generate_database_credential(endpoint=endpoint_name)
            cparams["password"] = cred.token
        else:
            db_api = getattr(self.ws, "database", None)
            if db_api is None:
                raise AttributeError(
                    "WorkspaceClient has no attribute 'database'. Use Lakebase Autoscaling or upgrade databricks-sdk."
                )
            cred = db_api.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[self.config.db.instance_name],
            )
            cparams["password"] = cred.token

    @cached_property
    def engine(self) -> Engine:
        if not self._db_configured():
            raise ValueError("Database not configured (set PGAPPNAME for Databricks App).")
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
                "Database not configured. Set PGAPPNAME to your Lakebase instance name (Databricks App)."
            )
        return Session(self.engine)

    def validate_db(self) -> None:
        if not self._db_configured():
            logger.info("Database not configured (PGAPPNAME unset); skipping validation.")
            return
        # In dev mode, skip Databricks-specific validation
        if self._dev_db_port:
            logger.info(
                f"Validating local dev database connection at localhost:{self._dev_db_port}"
            )
        else:
            if self._use_lakebase_autoscaling():
                endpoint_name = (
                    f"projects/{self.config.db.postgres_project_id}/branches/"
                    f"{self.config.db.postgres_branch_id}/endpoints/{self.config.db.postgres_endpoint_id}"
                )
                logger.info("Validating Lakebase Autoscaling endpoint: %s", endpoint_name)
                try:
                    self.ws.postgres.get_endpoint(name=endpoint_name)
                except NotFound:
                    raise ValueError(
                        f"Lakebase Autoscaling endpoint does not exist: {endpoint_name}"
                    )
            else:
                logger.info(
                    "Validating database connection to instance %s",
                    self.config.db.instance_name,
                )
                db_api = getattr(self.ws, "database", None)
                if db_api is None:
                    raise AttributeError(
                        "WorkspaceClient has no attribute 'database'. Use Lakebase Autoscaling or upgrade databricks-sdk."
                    )
                try:
                    db_api.get_database_instance(name=self.config.db.instance_name)
                except NotFound:
                    raise ValueError(
                        f"Database instance {self.config.db.instance_name} does not exist"
                    )

        # check if a connection to the database can be established
        try:
            with self.get_session() as session:
                session.connection().execute(text("SELECT 1"))
                session.close()

        except Exception:
            raise ConnectionError("Failed to connect to the database")

        if self._dev_db_port:
            logger.info("Local dev database connection validated successfully")
        elif self._use_lakebase_autoscaling():
            logger.info("Lakebase Autoscaling database connection validated successfully")
        else:
            logger.info(
                "Database connection to instance %s validated successfully",
                self.config.db.instance_name,
            )

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
