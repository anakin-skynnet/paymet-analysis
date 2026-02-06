-- ============================================================================
-- Online features table (Lakehouse) – features from ML and AI processes
-- ============================================================================
-- Store features produced by ML models and AI agents; present in the app UI.
-- Populate from decisioning, model serving, or agent jobs (same catalog/schema).
-- ============================================================================

CREATE TABLE IF NOT EXISTS online_features (
    id STRING NOT NULL,
    source STRING NOT NULL COMMENT 'ml | agent',
    feature_set STRING COMMENT 'e.g. approval_propensity, smart_routing, risk_assessor',
    feature_name STRING NOT NULL,
    feature_value DOUBLE,
    feature_value_str STRING COMMENT 'optional string value',
    entity_id STRING COMMENT 'e.g. transaction_id, merchant_id, request_id',
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true'
)
COMMENT 'Online features from ML and AI; stored in Lakehouse and presented in the app UI.';

-- View: latest features for UI (last 24h, limit 200)
CREATE OR REPLACE VIEW v_online_features_latest AS
SELECT id, source, feature_set, feature_name, feature_value, feature_value_str, entity_id, created_at
FROM online_features
WHERE created_at >= current_timestamp() - INTERVAL 24 HOURS
ORDER BY created_at DESC
LIMIT 200;
