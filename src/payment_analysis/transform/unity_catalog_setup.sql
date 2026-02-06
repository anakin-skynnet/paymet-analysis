-- ============================================================================
-- Unity Catalog Setup for Payment Analysis Platform
-- ============================================================================
-- Run this after Lakeflow pipeline creates tables to configure:
-- - Data Classification Tags
-- - Business Metrics
-- - Data Quality Monitors
-- - Predictive Optimization
-- - Rich Metadata for Genie
-- ============================================================================

-- ============================================================================
-- 1. TABLE COMMENTS & METADATA FOR GENIE
-- ============================================================================

-- Bronze table metadata
ALTER TABLE payments_raw_bronze SET TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'comment' = 'Raw payment events from all sources. Each row represents a single payment authorization attempt. Use this table for debugging and audit trails. For analytics, use payments_enriched_silver instead.'
);

COMMENT ON TABLE payments_raw_bronze IS 
'Raw payment authorization events ingested from streaming sources. 
Contains unprocessed transaction data including amounts, merchant info, 
card details, and approval status. Updated in real-time at ~1000 events/second.

Key columns for Genie:
- transaction_id: Unique identifier for each payment attempt
- amount: Transaction value in currency units
- is_approved: Whether the transaction was approved (true/false)
- fraud_score: ML-predicted fraud probability (0-1, higher = more risky)
- decline_reason: Why transaction was declined (if applicable)';

-- Silver table metadata
ALTER TABLE payments_enriched_silver SET TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'comment' = 'Cleaned and enriched payment transactions. This is the primary analytics table. Includes merchant enrichment, risk scoring, and derived features.'
);

COMMENT ON TABLE payments_enriched_silver IS
'Enriched payment transactions for analytics and reporting.
Includes data quality validations, merchant dimension joins, 
and derived features like risk_tier and amount_bucket.

RECOMMENDED for Genie queries about:
- Transaction volumes and trends
- Approval rates by segment/country/network
- Fraud and risk patterns
- Payment solution performance

Key columns:
- is_approved: Transaction approval status
- approval_rate = COUNT(is_approved=true) / COUNT(*)
- fraud_score: Risk score (0=safe, 1=high risk)
- risk_tier: Categorized as low/medium/high
- merchant_segment: Business category (Travel, Retail, Gaming, etc.)
- payment_solution: Method used (standard, 3ds, passkey, etc.)';

-- ============================================================================
-- 2. COLUMN COMMENTS FOR GENIE UNDERSTANDING
-- ============================================================================

-- Add column-level comments for key fields
COMMENT ON COLUMN payments_enriched_silver.transaction_id IS 'Unique transaction identifier (format: txn_XXXX)';
COMMENT ON COLUMN payments_enriched_silver.merchant_id IS 'Merchant identifier - join with merchants_dim for details';
COMMENT ON COLUMN payments_enriched_silver.amount IS 'Transaction amount in currency units. Typical range: $10-$1000';
COMMENT ON COLUMN payments_enriched_silver.currency IS 'ISO currency code (USD, EUR, GBP, etc.)';
COMMENT ON COLUMN payments_enriched_silver.is_approved IS 'TRUE if transaction approved, FALSE if declined. Key metric for approval rate calculations';
COMMENT ON COLUMN payments_enriched_silver.fraud_score IS 'ML fraud prediction score. Range 0-1. Above 0.7 = high risk, below 0.3 = low risk';
COMMENT ON COLUMN payments_enriched_silver.decline_reason IS 'Reason for decline (INSUFFICIENT_FUNDS, FRAUD_SUSPECTED, etc.). NULL if approved';
COMMENT ON COLUMN payments_enriched_silver.merchant_segment IS 'Business category: Travel, Retail, Gaming, Digital, Entertainment, Grocery, Fuel, Subscription';
COMMENT ON COLUMN payments_enriched_silver.payment_solution IS 'Payment method: standard, 3ds, network_token, passkey, apple_pay, google_pay';
COMMENT ON COLUMN payments_enriched_silver.card_network IS 'Card brand: visa, mastercard, amex, discover';
COMMENT ON COLUMN payments_enriched_silver.issuer_country IS 'Cardholder bank country (ISO code)';
COMMENT ON COLUMN payments_enriched_silver.risk_tier IS 'Categorized risk level: low (fraud_score < 0.3), medium (0.3-0.7), high (> 0.7)';
COMMENT ON COLUMN payments_enriched_silver.is_cross_border IS 'TRUE if issuer country differs from merchant country';

-- ============================================================================
-- 3. DATA CLASSIFICATION TAGS
-- ============================================================================

-- Tag PII columns
ALTER TABLE payments_enriched_silver ALTER COLUMN cardholder_id SET TAGS ('pii.contains_pii' = 'true', 'pii.data_category' = 'personal_identifier');
ALTER TABLE payments_enriched_silver ALTER COLUMN card_bin SET TAGS ('pii.contains_pii' = 'true', 'pii.data_category' = 'financial', 'compliance.pci_scope' = 'true');
ALTER TABLE payments_enriched_silver ALTER COLUMN ip_address SET TAGS ('pii.contains_pii' = 'true', 'pii.data_category' = 'personal_identifier');
ALTER TABLE payments_enriched_silver ALTER COLUMN device_fingerprint SET TAGS ('pii.contains_pii' = 'true', 'pii.data_category' = 'behavioral');

-- Tag financial data
ALTER TABLE payments_enriched_silver ALTER COLUMN amount SET TAGS ('pii.contains_pii' = 'false', 'pii.data_category' = 'financial');
ALTER TABLE payments_enriched_silver ALTER COLUMN fraud_score SET TAGS ('ml.model_output' = 'true', 'ml.model_name' = 'fraud_detection');

-- Tag compliance columns
ALTER TABLE payments_enriched_silver SET TAGS ('compliance.gdpr_relevant' = 'true', 'compliance.pci_scope' = 'true', 'compliance.data_retention_days' = '2555');

-- ============================================================================
-- 4. PRIMARY KEYS AND RELATIONSHIPS
-- ============================================================================

-- Add primary key constraints (for documentation/Genie)
ALTER TABLE payments_enriched_silver ADD CONSTRAINT pk_payments PRIMARY KEY (transaction_id);
ALTER TABLE merchants_dim_bronze ADD CONSTRAINT pk_merchants PRIMARY KEY (merchant_id);

-- Add foreign key relationships (informational)
ALTER TABLE payments_enriched_silver ADD CONSTRAINT fk_merchant 
    FOREIGN KEY (merchant_id) REFERENCES merchants_dim_bronze(merchant_id);

-- ============================================================================
-- 5. ENABLE PREDICTIVE OPTIMIZATION
-- ============================================================================

-- Enable predictive optimization for automatic maintenance
ALTER TABLE payments_enriched_silver SET TBLPROPERTIES ('delta.enableDeletionVectors' = 'true');
ALTER TABLE payments_raw_bronze SET TBLPROPERTIES ('delta.enableDeletionVectors' = 'true');

-- Note: Predictive Optimization is enabled at schema/catalog level via:
-- ALTER SCHEMA payment_analysis_dev ENABLE PREDICTIVE OPTIMIZATION;

-- ============================================================================
-- 6. CREATE LAKEHOUSE MONITORS
-- ============================================================================

-- Create quality monitor for silver table
CREATE OR REFRESH MONITOR payments_quality_monitor
ON TABLE payments_enriched_silver
ANALYSIS_TYPES (
    DATA_PROFILE,      -- Column statistics
    DATA_DRIFT,        -- Detect distribution changes
    MISSING_VALUES,    -- Track null/missing data
    VOLUME_ANOMALY     -- Detect unusual row counts
)
SCHEDULE CRON '0 */4 * * *'  -- Every 4 hours
BASELINE_TABLE_NAME 'payments_enriched_silver_baseline'
WITH SLICING EXPR (
    merchant_segment,
    payment_solution,
    risk_tier
);

-- Create KPI monitor for executive metrics
CREATE OR REFRESH MONITOR kpi_threshold_monitor
ON TABLE v_executive_kpis
ANALYSIS_TYPES (DATA_PROFILE)
CUSTOM_METRICS (
    STRUCT(
        'approval_rate_check' as name,
        approval_rate_pct as value,
        CASE WHEN approval_rate_pct < 85 THEN 'ALERT: Low approval rate' ELSE 'OK' END as status
    )
);

-- ============================================================================
-- 7. BUSINESS METRICS DEFINITIONS
-- ============================================================================

-- These are documented for Genie understanding
COMMENT ON VIEW v_executive_kpis IS 
'Executive KPIs for payment operations.

Business Metrics:
- approval_rate_pct: Percentage of approved transactions. Target: > 85%
- total_transactions: Volume of payment attempts
- total_transaction_value: Sum of all transaction amounts
- avg_fraud_score: Average ML fraud prediction score. Target: < 0.15

Use for: Executive dashboards, daily standups, board reports.
Update frequency: Real-time';

COMMENT ON VIEW v_top_decline_reasons IS
'Top reasons why transactions are being declined.

Business Metrics:
- decline_count: Number of declines per reason
- pct_of_declines: Share of total declines
- recoverable_pct: Estimated recovery potential via retry/routing

Use for: Decline analysis, recovery optimization, issuer negotiations.
Actionable insights for reducing false declines.';

COMMENT ON VIEW v_solution_performance IS
'Performance comparison across payment solutions (3DS, passkeys, etc.).

Business Metrics:
- approval_rate_pct: Success rate per solution
- avg_latency_ms: Processing speed
- total_value: Revenue processed

Use for: Solution selection, A/B testing, vendor negotiations.';

-- ============================================================================
-- 8. GENIE SAMPLE QUERIES (as comments for training)
-- ============================================================================

/*
GENIE SAMPLE QUERIES:

Q: "What is the current approval rate?"
A: SELECT approval_rate_pct FROM v_executive_kpis LIMIT 1

Q: "Show me approval rate by country"
A: SELECT country, approval_rate_pct, transaction_count 
   FROM v_performance_by_geography 
   ORDER BY transaction_count DESC

Q: "Why are transactions being declined?"
A: SELECT decline_reason, decline_count, pct_of_declines, recoverable_pct
   FROM v_top_decline_reasons 
   ORDER BY decline_count DESC

Q: "Which payment solution has the best performance?"
A: SELECT payment_solution, approval_rate_pct, avg_latency_ms
   FROM v_solution_performance 
   ORDER BY approval_rate_pct DESC

Q: "Are there any alerts?"
A: SELECT * FROM v_active_alerts ORDER BY severity

Q: "How many high risk transactions today?"
A: SELECT COUNT(*) FROM payments_enriched_silver 
   WHERE event_date = CURRENT_DATE AND risk_tier = 'high'

Q: "What's the trend this week?"
A: SELECT event_date, transactions, approval_rate 
   FROM v_daily_trends 
   WHERE event_date >= CURRENT_DATE - 7
*/

-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================
