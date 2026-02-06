-- ============================================================================
-- Vector Search source table & Lakehouse recommendations (approval acceleration)
-- ============================================================================
-- Run after gold views. Creates:
-- 1. transaction_summaries_for_search: source for Vector Search index (similar transactions)
-- 2. approval_recommendations: Lakehouse table for recommendations shown in the app
-- ============================================================================

-- Source table for Vector Search index (similar-transaction lookup to accelerate approval decisions)
CREATE TABLE IF NOT EXISTS transaction_summaries_for_search (
    transaction_id STRING NOT NULL,
    summary_text STRING NOT NULL COMMENT 'Concatenated context for embedding: amount, network, outcome, risk, etc.',
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
COMMENT 'Source for Vector Search index: similar-transaction retrieval to recommend actions and accelerate approval rates. Populate from silver/gold via job or pipeline.';

-- Lakehouse table: recommendations from similar cases (Vector Search + rules) for app to display
CREATE TABLE IF NOT EXISTS approval_recommendations (
    id STRING NOT NULL,
    context_summary STRING NOT NULL,
    recommended_action STRING NOT NULL,
    score DOUBLE,
    source_type STRING COMMENT 'e.g. vector_search, rule, model',
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
)
COMMENT 'Recommendations from similar transactions (Vector Search) and rules. Shown in app to accelerate approval decisions.';

-- View for app: latest recommendations from Lakehouse database
CREATE OR REPLACE VIEW v_recommendations_from_lakehouse AS
SELECT id, context_summary, recommended_action, score, source_type, created_at
FROM approval_recommendations
ORDER BY created_at DESC
LIMIT 100;
