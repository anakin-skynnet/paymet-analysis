"""Read app_config and app_settings from Lakebase (Postgres). Used at startup so backend processes use these before calling Lakehouse."""
# pyright: reportDeprecated=false  # session.execute() with text() for raw SQL; exec() is for ORM select

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from .logger import logger

if TYPE_CHECKING:
    from .runtime import Runtime


def load_app_config_and_settings(runtime: Runtime) -> tuple[tuple[str, str] | None, dict[str, str]]:
    """
    Read app_config (catalog, schema) and app_settings (key-value) from Lakebase.
    Returns ((catalog, schema) or None, settings_dict). Use at startup before any Lakehouse calls.
    """
    config = runtime.config
    schema_name = (config.db.db_schema or "app").strip() or "app"
    if not runtime._db_configured():
        return (None, {})

    uc_config: tuple[str, str] | None = None
    settings: dict[str, str] = {}

    try:
        with runtime.get_session() as session:
            # Quoted identifier for PostgreSQL schema
            q = text(f'SELECT catalog, schema FROM "{schema_name}".app_config LIMIT 1')
            result = session.execute(q)
            row = result.fetchone()
            if row:
                c, s = str(row[0] or "").strip(), str(row[1] or "").strip()
                if c and s:
                    uc_config = (c, s)

            q2 = text(f'SELECT key, value FROM "{schema_name}".app_settings')
            result2 = session.execute(q2)
            for r in result2.fetchall():
                if r and len(r) >= 2:
                    settings[str(r[0])] = str(r[1] or "")
    except Exception as e:
        logger.warning("Could not read app_config/app_settings from Lakebase: %s", e)

    return (uc_config, settings)


def write_app_config(runtime: Runtime, catalog: str, schema: str) -> bool:
    """Write catalog and schema to Lakebase app_config and app_settings. Call after user saves config."""
    config = runtime.config
    schema_name = (config.db.db_schema or "app").strip() or "app"
    if not runtime._db_configured():
        return False
    try:
        with runtime.get_session() as session:
            q = text(
                f"""
                INSERT INTO "{schema_name}".app_config (id, catalog, schema)
                VALUES (1, :catalog, :schema)
                ON CONFLICT (id) DO UPDATE SET catalog = EXCLUDED.catalog, schema = EXCLUDED.schema, updated_at = current_timestamp
                """
            )
            session.execute(q, {"catalog": catalog, "schema": schema})
            for key, val in [("catalog", catalog), ("schema", schema)]:
                q2 = text(
                    f"""
                    INSERT INTO "{schema_name}".app_settings (key, value)
                    VALUES (:key, :value)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = current_timestamp
                    """
                )
                session.execute(q2, {"key": key, "value": val})
            session.commit()
        return True
    except Exception as e:
        logger.warning("Could not write app_config to Lakebase: %s", e)
        return False


def get_approval_rules_from_lakebase(
    runtime: Runtime,
    *,
    rule_type: str | None = None,
    active_only: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]] | None:
    """Read approval_rules from Lakebase. Returns list of dicts, or None on error/unconfigured (caller should fall back to Lakehouse)."""
    config = runtime.config
    schema_name = (config.db.db_schema or "app").strip() or "app"
    if not runtime._db_configured():
        return None
    limit = max(1, min(limit, 500))
    try:
        with runtime.get_session() as session:
            where = "WHERE is_active = true" if active_only else ""
            if rule_type:
                where += f" AND rule_type = :rule_type" if where else "WHERE rule_type = :rule_type"
            q = text(
                f"""
                SELECT id, name, rule_type, condition_expression, action_summary, priority, is_active, created_at, updated_at
                FROM "{schema_name}".approval_rules
                {where}
                ORDER BY priority ASC, updated_at DESC
                LIMIT :limit
                """
            )
            params: dict[str, Any] = {"limit": limit}
            if rule_type:
                params["rule_type"] = rule_type
            result = session.execute(q, params)
            rows = result.fetchall()
            return [
                {
                    "id": str(r[0]),
                    "name": str(r[1]),
                    "rule_type": str(r[2]),
                    "condition_expression": str(r[3]) if r[3] else None,
                    "action_summary": str(r[4]),
                    "priority": int(r[5]) if r[5] is not None else 100,
                    "is_active": bool(r[6]) if r[6] is not None else True,
                    "created_at": r[7],
                    "updated_at": r[8],
                }
                for r in rows
            ]
    except Exception as e:
        logger.debug("Could not read approval_rules from Lakebase: %s", e)
        return None


def get_online_features_from_lakebase(
    runtime: Runtime,
    *,
    source: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]] | None:
    """Read online_features from Lakebase (last 24h). Returns list of dicts, or None on error (caller should fall back to Lakehouse)."""
    config = runtime.config
    schema_name = (config.db.db_schema or "app").strip() or "app"
    if not runtime._db_configured():
        return None
    limit = max(1, min(limit, 500))
    try:
        with runtime.get_session() as session:
            where = "WHERE created_at >= current_timestamp - interval '24 hours'"
            if source and source.lower() in ("ml", "agent"):
                where += " AND source = :source"
            q = text(
                f"""
                SELECT id, source, feature_set, feature_name, feature_value, feature_value_str, entity_id, created_at
                FROM "{schema_name}".online_features
                {where}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            )
            params: dict[str, Any] = {"limit": limit}
            if source and source.lower() in ("ml", "agent"):
                params["source"] = source.lower()
            result = session.execute(q, params)
            rows = result.fetchall()
            return [
                {
                    "id": str(r[0]),
                    "source": str(r[1]),
                    "feature_set": str(r[2]) if r[2] else None,
                    "feature_name": str(r[3]),
                    "feature_value": float(r[4]) if r[4] is not None else None,
                    "feature_value_str": str(r[5]) if r[5] else None,
                    "entity_id": str(r[6]) if r[6] else None,
                    "created_at": r[7],
                }
                for r in rows
            ]
    except Exception as e:
        logger.debug("Could not read online_features from Lakebase: %s", e)
        return None
