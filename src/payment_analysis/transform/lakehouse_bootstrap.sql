-- ============================================================================
-- Lakehouse bootstrap – run once in target catalog/schema (same as gold views)
-- ============================================================================
-- Run in SQL Warehouse or a notebook. Order: app_config → vector_search &
-- recommendations → approval_rules → online_features. Enables Rules, Decisioning
-- recommendations, and Dashboard features. See docs/DEPLOYMENT.md Step 5.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. App config (catalog/schema used by the app)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_config (
    id INT NOT NULL DEFAULT 1,
    catalog STRING NOT NULL COMMENT 'Unity Catalog name used by the app',
    schema STRING NOT NULL COMMENT 'Schema name used by the app',
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Single-row config: catalog and schema for the Payment Approval app. Updated via UI or API.';

INSERT INTO app_config (id, catalog, schema)
SELECT 1, CURRENT_CATALOG(), CURRENT_SCHEMA()
WHERE (SELECT COUNT(*) FROM app_config) = 0;

-- ----------------------------------------------------------------------------
-- 2. Vector Search source & Lakehouse recommendations
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transaction_summaries_for_search (
    transaction_id STRING NOT NULL,
    summary_text STRING NOT NULL COMMENT 'Concatenated context for embedding',
    outcome STRING NOT NULL,
    amount DOUBLE,
    network STRING,
    merchant_segment STRING,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
)
COMMENT 'Source for Vector Search index. Create index from resources/vector_search.yml if needed.';

CREATE TABLE IF NOT EXISTS approval_recommendations (
    id STRING NOT NULL,
    context_summary STRING NOT NULL,
    recommended_action STRING NOT NULL,
    score DOUBLE,
    source_type STRING,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
COMMENT 'Recommendations from similar transactions and rules; shown in app Decisioning.';

CREATE OR REPLACE VIEW v_recommendations_from_lakehouse AS
SELECT id, context_summary, recommended_action, score, source_type, created_at
FROM approval_recommendations
ORDER BY created_at DESC
LIMIT 100;

-- ----------------------------------------------------------------------------
-- 3. Approval rules (editable from app, used by ML/Agents)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approval_rules (
    id STRING NOT NULL,
    name STRING NOT NULL,
    rule_type STRING NOT NULL COMMENT 'authentication | retry | routing',
    condition_expression STRING,
    action_summary STRING NOT NULL,
    priority INT NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Business rules for approval/retry/routing. Written from the app; consumed by decision API and AI agents.';

CREATE OR REPLACE VIEW v_approval_rules_active AS
SELECT id, name, rule_type, condition_expression, action_summary, priority, created_at, updated_at
FROM approval_rules
WHERE is_active = true
ORDER BY priority ASC, updated_at DESC;

-- Seed default approval rules only when table is empty (aligned with Lakebase defaults)
INSERT INTO approval_rules (id, name, rule_type, condition_expression, action_summary, priority, is_active)
SELECT id, name, rule_type, condition_expression, action_summary, priority, is_active FROM (
    SELECT 'default-auth-1' AS id, 'Default 3DS for high value' AS name, 'authentication' AS rule_type,
           'amount_cents >= 50000' AS condition_expression,
           'Require 3DS for transactions >= 500.00; reduces fraud and false declines' AS action_summary,
           100 AS priority, true AS is_active
    UNION ALL
    SELECT 'default-retry-1', 'Retry after soft decline', 'retry',
           'decline_reason IN (''INSUFFICIENT_FUNDS'',''TEMPORARY_FAILURE'')',
           'Retry once after 2h for soft declines; improves approval rate', 90, true
    UNION ALL
    SELECT 'default-routing-1', 'Primary acquirer routing', 'routing',
           'merchant_country = ''BR''',
           'Route Brazil e-commerce to primary acquirer; fallback to backup on timeout', 110, true
) seed
WHERE (SELECT COUNT(*) FROM approval_rules) = 0;

-- ----------------------------------------------------------------------------
-- 3b. Countries / entities (for UI dropdown filter; editable by users)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS countries (
    code STRING NOT NULL COMMENT 'ISO-style entity/country code (e.g. BR, MX)',
    name STRING NOT NULL COMMENT 'Display name for the entity or country',
    display_order INT NOT NULL DEFAULT 0 COMMENT 'Sort order in dropdown (lower first)',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Countries/entities for the report filter dropdown. Add or remove rows to change options in the UI.';

-- Seed default Getnet entities (insert only when table is empty)
INSERT INTO countries (code, name, display_order)
SELECT code, name, display_order FROM (
    SELECT 'BR' AS code, 'Brazil' AS name, 1 AS display_order
    UNION ALL SELECT 'MX', 'Mexico', 2
    UNION ALL SELECT 'AR', 'Argentina', 3
    UNION ALL SELECT 'CL', 'Chile', 4
    UNION ALL SELECT 'CO', 'Colombia', 5
    UNION ALL SELECT 'PE', 'Peru', 6
    UNION ALL SELECT 'EC', 'Ecuador', 7
    UNION ALL SELECT 'UY', 'Uruguay', 8
    UNION ALL SELECT 'PY', 'Paraguay', 9
    UNION ALL SELECT 'BO', 'Bolivia', 10
) seed
WHERE (SELECT COUNT(*) FROM countries) = 0;

-- ----------------------------------------------------------------------------
-- 4. Online features (ML and AI output for app UI)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS online_features (
    id STRING NOT NULL,
    source STRING NOT NULL COMMENT 'ml | agent',
    feature_set STRING,
    feature_name STRING NOT NULL,
    feature_value DOUBLE,
    feature_value_str STRING,
    entity_id STRING,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Online features from ML and AI; presented in the app Dashboard.';

CREATE OR REPLACE VIEW v_online_features_latest AS
SELECT id, source, feature_set, feature_name, feature_value, feature_value_str, entity_id, created_at
FROM online_features
WHERE created_at >= current_timestamp() - INTERVAL 24 HOURS
ORDER BY created_at DESC
LIMIT 200;
