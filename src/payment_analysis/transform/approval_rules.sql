-- ============================================================================
-- Approval rules table (Lakehouse) – editable from the app, used by ML/Agents
-- ============================================================================
-- Run in the same catalog/schema as gold views. App writes rules here;
-- decisioning and AI agents read from this table to accelerate approval rates.
-- ============================================================================

CREATE TABLE IF NOT EXISTS approval_rules (
    id STRING NOT NULL,
    name STRING NOT NULL,
    rule_type STRING NOT NULL COMMENT 'authentication | retry | routing',
    condition_expression STRING COMMENT 'JSON or text: e.g. {"risk_tier":"LOW","amount_max":5000}',
    action_summary STRING NOT NULL COMMENT 'Human-readable recommended action',
    priority INT NOT NULL DEFAULT 100 COMMENT 'Lower = higher priority',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true'
)
COMMENT 'Business rules for approval/retry/routing. Written from the app; consumed by decision API and AI agents to accelerate approval rates.';

-- View for active rules (used by app and agents)
CREATE OR REPLACE VIEW v_approval_rules_active AS
SELECT id, name, rule_type, condition_expression, action_summary, priority, created_at, updated_at
FROM approval_rules
WHERE is_active = true
ORDER BY priority ASC, updated_at DESC;
