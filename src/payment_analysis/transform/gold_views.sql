-- ============================================================================
-- Gold Views — Dashboards, Genie & Agent Analytics
-- ============================================================================
-- Lightweight SQL VIEWs created by Job 3 (run_gold_views.py).
-- Consumed by: dashboards, Genie spaces, agent framework.
--
-- Backend API gold tables (retry cohorts, Brazil analytics, quality metrics)
-- live in gold_views.py and are managed by the Lakeflow ETL pipeline.
-- The two sets use **distinct names** so they never conflict.
-- ============================================================================

-- ===========================================================================
-- EXECUTIVE KPI VIEWS
-- ===========================================================================

-- View 1: Executive KPIs Summary
CREATE OR REPLACE VIEW v_executive_kpis AS
SELECT 
    COUNT(*) as total_transactions,
    COUNT(DISTINCT merchant_id) as unique_merchants,
    COUNT(DISTINCT issuer_country) as unique_countries,
    SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) as approved_count,
    SUM(CASE WHEN NOT is_approved THEN 1 ELSE 0 END) as declined_count,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate_pct,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(AVG(aml_risk_score), 3) as avg_aml_risk_score,
    ROUND(SUM(amount), 2) as total_transaction_value,
    ROUND(SUM(CASE WHEN is_approved THEN amount ELSE 0 END), 2) as approved_value,
    ROUND(SUM(CASE WHEN NOT is_approved THEN amount ELSE 0 END), 2) as declined_value,
    ROUND(AVG(amount), 2) as avg_transaction_amount,
    ROUND(SUM(CASE WHEN uses_3ds THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as auth_3ds_usage_pct,
    MIN(event_time) as period_start,
    MAX(event_time) as period_end
FROM payments_enriched_silver;

-- View 2: Approval Trends by Hour
CREATE OR REPLACE VIEW v_approval_trends_hourly AS
SELECT 
    DATE_TRUNC('hour', event_time) as hour,
    COUNT(*) as transaction_count,
    SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) as approved_count,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate_pct,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(SUM(amount), 2) as total_value,
    COUNT(DISTINCT merchant_segment) as active_segments
FROM payments_enriched_silver
WHERE event_time >= CURRENT_TIMESTAMP() - INTERVAL 7 DAYS
GROUP BY DATE_TRUNC('hour', event_time)
ORDER BY hour DESC;

-- View 3: Performance by Geography
CREATE OR REPLACE VIEW v_performance_by_geography AS
SELECT 
    issuer_country as country,
    COUNT(*) as transaction_count,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate_pct,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(SUM(amount), 2) as total_transaction_value,
    COUNT(DISTINCT merchant_id) as unique_merchants
FROM payments_enriched_silver
GROUP BY issuer_country
HAVING COUNT(*) >= 10
ORDER BY transaction_count DESC;

-- ===========================================================================
-- DECLINE ANALYSIS VIEWS
-- ===========================================================================

-- View 4: Top Decline Reasons
CREATE OR REPLACE VIEW v_top_decline_reasons AS
SELECT 
    decline_reason,
    COUNT(*) as decline_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct_of_declines,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(AVG(amount), 2) as avg_amount,
    ROUND(SUM(amount), 2) as total_declined_value,
    COUNT(DISTINCT merchant_id) as affected_merchants,
    SUM(CASE WHEN fraud_score < 0.3 THEN 1 ELSE 0 END) as low_risk_declines,
    ROUND(SUM(CASE WHEN fraud_score < 0.3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as recoverable_pct
FROM payments_enriched_silver
WHERE NOT is_approved
GROUP BY decline_reason
ORDER BY decline_count DESC;

-- View 5: Decline Recovery Opportunities
CREATE OR REPLACE VIEW v_decline_recovery_opportunities AS
SELECT 
    decline_reason,
    merchant_segment,
    card_network,
    COUNT(*) as decline_count,
    ROUND(SUM(amount), 2) as potential_recovery_value,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(AVG(device_trust_score), 3) as avg_device_trust,
    CASE
        WHEN AVG(fraud_score) < 0.2 AND AVG(device_trust_score) > 0.7 THEN 'HIGH'
        WHEN AVG(fraud_score) < 0.4 AND AVG(device_trust_score) > 0.5 THEN 'MEDIUM'
        ELSE 'LOW'
    END as recovery_likelihood,
    CASE
        WHEN decline_reason IN ('INSUFFICIENT_FUNDS', 'CARD_EXPIRED') THEN 'Enable Smart Retry'
        WHEN decline_reason IN ('DO_NOT_HONOR', 'ISSUER_UNAVAILABLE') THEN 'Route to Alternative'
        ELSE 'Manual Review'
    END as recommended_action
FROM payments_enriched_silver
WHERE NOT is_approved
  AND event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY decline_reason, merchant_segment, card_network
HAVING COUNT(*) >= 5
ORDER BY potential_recovery_value DESC;

-- ===========================================================================
-- REAL-TIME MONITORING VIEWS
-- ===========================================================================

-- View 6: Last Hour Performance
CREATE OR REPLACE VIEW v_last_hour_performance AS
SELECT 
    COUNT(*) as transactions_last_hour,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate_pct,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(SUM(amount), 2) as total_value,
    COUNT(DISTINCT merchant_segment) as active_segments,
    SUM(CASE WHEN fraud_score > 0.7 THEN 1 ELSE 0 END) as high_risk_transactions,
    SUM(CASE WHEN NOT is_approved THEN 1 ELSE 0 END) as declines_last_hour
FROM payments_enriched_silver
WHERE event_time >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR;

-- View 7: Active Alerts
CREATE OR REPLACE VIEW v_active_alerts AS
SELECT 
    alert_type,
    severity,
    metric_name,
    current_value,
    threshold_value,
    alert_message,
    first_detected
FROM (
    SELECT 
        'APPROVAL_RATE_DROP' as alert_type,
        CASE WHEN approval_rate_pct < 80 THEN 'CRITICAL' WHEN approval_rate_pct < 85 THEN 'HIGH' ELSE 'MEDIUM' END as severity,
        'approval_rate_pct' as metric_name,
        approval_rate_pct as current_value,
        85.0 as threshold_value,
        CONCAT('Approval rate dropped to ', CAST(approval_rate_pct AS STRING), '%') as alert_message,
        CURRENT_TIMESTAMP() as first_detected
    FROM v_last_hour_performance
    WHERE approval_rate_pct < 85
    
    UNION ALL
    
    SELECT 
        'HIGH_FRAUD_RATE' as alert_type,
        CASE WHEN high_risk_transactions > 50 THEN 'CRITICAL' ELSE 'HIGH' END as severity,
        'high_risk_transactions' as metric_name,
        CAST(high_risk_transactions AS DOUBLE) as current_value,
        20.0 as threshold_value,
        CONCAT(CAST(high_risk_transactions AS STRING), ' high-risk transactions in last hour') as alert_message,
        CURRENT_TIMESTAMP() as first_detected
    FROM v_last_hour_performance
    WHERE high_risk_transactions > 20
);

-- ===========================================================================
-- PAYMENT SOLUTION & ROUTING VIEWS
-- ===========================================================================

-- View 8: Solution Performance
CREATE OR REPLACE VIEW v_solution_performance AS
SELECT 
    payment_solution,
    COUNT(*) as transaction_count,
    SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) as approved_count,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate_pct,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(AVG(amount), 2) as avg_amount,
    ROUND(SUM(amount), 2) as total_value,
    ROUND(AVG(processing_time_ms), 2) as avg_latency_ms
FROM payments_enriched_silver
WHERE event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY payment_solution
ORDER BY transaction_count DESC;

-- View 9: Card Network Performance
CREATE OR REPLACE VIEW v_card_network_performance AS
SELECT 
    card_network,
    COUNT(*) as transaction_count,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate_pct,
    ROUND(AVG(amount), 2) as avg_amount,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(AVG(processing_time_ms), 2) as avg_latency_ms
FROM payments_enriched_silver
WHERE event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY card_network
ORDER BY transaction_count DESC;

-- ===========================================================================
-- NOTE: v_retry_performance is a Lakeflow-managed gold table (gold_views.py).
-- It is NOT created here to avoid conflicts with the pipeline.
-- ===========================================================================

-- ===========================================================================
-- MERCHANT SEGMENT VIEWS
-- ===========================================================================

-- View 11: Merchant Segment Performance
CREATE OR REPLACE VIEW v_merchant_segment_performance AS
SELECT 
    merchant_segment,
    COUNT(*) as transaction_count,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate_pct,
    COUNT(DISTINCT merchant_id) as unique_merchants,
    ROUND(AVG(amount), 2) as avg_transaction_amount,
    ROUND(SUM(amount), 2) as total_value,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(SUM(CASE WHEN uses_3ds THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as auth_3ds_usage_pct
FROM payments_enriched_silver
WHERE event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY merchant_segment
ORDER BY transaction_count DESC;

-- ===========================================================================
-- DAILY TRENDS
-- ===========================================================================

-- View 12: Daily Trend Analysis
CREATE OR REPLACE VIEW v_daily_trends AS
SELECT 
    event_date,
    COUNT(*) as transactions,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(SUM(amount), 2) as total_value,
    COUNT(*) - LAG(COUNT(*), 1) OVER (ORDER BY event_date) as dod_volume_change
FROM payments_enriched_silver
WHERE event_date >= CURRENT_DATE() - INTERVAL 90 DAYS
GROUP BY event_date
ORDER BY event_date DESC;

-- ===========================================================================
-- STREAMING & DATA QUALITY VIEWS
-- ===========================================================================

-- View 13: Streaming ingestion by hour (bronze layer)
CREATE OR REPLACE VIEW v_streaming_ingestion_hourly AS
SELECT
    DATE_TRUNC('hour', _ingested_at) AS hour,
    COUNT(*) AS bronze_record_count
FROM payments_raw_bronze
WHERE _ingested_at >= CURRENT_TIMESTAMP() - INTERVAL 7 DAYS
GROUP BY DATE_TRUNC('hour', _ingested_at)
ORDER BY hour DESC;

-- View 14: Silver processed by hour (enriched records)
CREATE OR REPLACE VIEW v_silver_processed_hourly AS
SELECT
    DATE_TRUNC('hour', event_timestamp) AS hour,
    COUNT(*) AS silver_record_count
FROM payments_enriched_silver
WHERE event_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 7 DAYS
GROUP BY DATE_TRUNC('hour', event_timestamp)
ORDER BY hour DESC;

-- View 14b: Incoming streaming volume per second (rate from hourly bronze ingestion)
CREATE OR REPLACE VIEW v_streaming_volume_per_second AS
SELECT
    hour,
    ROUND(bronze_record_count / 3600.0, 2) AS records_per_second
FROM v_streaming_ingestion_hourly
ORDER BY hour DESC
LIMIT 168;

-- View 15: Data quality summary (single row: volumes and retention)
CREATE OR REPLACE VIEW v_data_quality_summary AS
SELECT
    (SELECT COUNT(*) FROM payments_raw_bronze WHERE _ingested_at >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY) AS bronze_last_24h,
    (SELECT COUNT(*) FROM payments_enriched_silver WHERE event_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY) AS silver_last_24h,
    ROUND(
        (SELECT COUNT(*) FROM payments_enriched_silver WHERE event_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY) * 100.0
        / NULLIF((SELECT COUNT(*) FROM payments_raw_bronze WHERE _ingested_at >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY), 0),
        2
    ) AS retention_pct_24h,
    (SELECT MAX(_ingested_at) FROM payments_raw_bronze) AS latest_bronze_ingestion,
    (SELECT MAX(event_timestamp) FROM payments_enriched_silver) AS latest_silver_event;

-- ===========================================================================
-- UNITY CATALOG DATA QUALITY MONITORING METRICS
-- ===========================================================================
-- View 16: Latest Unity Catalog data quality results per table.
-- Source: system.data_quality_monitoring.table_results (freshness, completeness, downstream impact).
-- Requires: Unity Catalog data quality monitoring enabled and SELECT on system.data_quality_monitoring.
-- If the system table is not available, comment out this view or grant access.
-- ===========================================================================
CREATE OR REPLACE VIEW v_uc_data_quality_metrics AS
WITH latest AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY table_id ORDER BY event_time DESC) AS rn
    FROM system.data_quality_monitoring.table_results
    WHERE catalog_name = CURRENT_CATALOG()
      AND schema_name = CURRENT_SCHEMA()
)
SELECT
    event_time,
    catalog_name,
    schema_name,
    table_name,
    status AS overall_status,
    freshness.status AS freshness_status,
    completeness.status AS completeness_status,
    COALESCE(downstream_impact.impact_level, 0) AS impact_level,
    COALESCE(downstream_impact.num_downstream_tables, 0) AS num_downstream_tables,
    COALESCE(downstream_impact.num_queries_on_affected_tables, 0) AS num_queries_affected
FROM latest
WHERE rn = 1
ORDER BY table_name;

-- ===========================================================================
-- UNITY CATALOG METRIC VIEWS (WITH METRICS LANGUAGE YAML)
-- ===========================================================================
-- Semantic layer for dashboards and Genie: dimensions + measures on payment data.
-- Source: payments_enriched_silver. Query as normal views; dimensions/measures
-- provide consistent business semantics across dashboards.
-- ===========================================================================

-- Metric View 1: Payment transaction metrics (executive KPIs, trends, geography)
CREATE OR REPLACE VIEW payment_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "Payment transaction metrics for approval analysis and executive dashboards"
source: payments_enriched_silver
dimensions:
  - name: Merchant Segment
    expr: merchant_segment
    comment: "Merchant segment (e.g. SMB, Enterprise)"
  - name: Card Network
    expr: card_network
    comment: "Card network (Visa, Mastercard, etc.)"
  - name: Issuer Country
    expr: issuer_country
    comment: "Issuer country code"
  - name: Event Date
    expr: event_date
    comment: "Date of the transaction"
  - name: Decline Reason
    expr: decline_reason
    comment: "Reason code when transaction is declined"
measures:
  - name: Total Transactions
    expr: COUNT(1)
    comment: "Total number of transactions"
  - name: Approved Count
    expr: COUNT_IF(is_approved = true)
    comment: "Number of approved transactions"
  - name: Declined Count
    expr: COUNT_IF(is_approved = false)
    comment: "Number of declined transactions"
  - name: Approval Rate Pct
    expr: ROUND(COUNT_IF(is_approved = true) * 100.0 / COUNT(1), 2)
    comment: "Approval rate percentage"
  - name: Total Amount
    expr: ROUND(SUM(amount), 2)
    comment: "Total transaction value"
  - name: Approved Value
    expr: ROUND(SUM(CASE WHEN is_approved THEN amount ELSE 0 END), 2)
    comment: "Total value of approved transactions"
  - name: Declined Value
    expr: ROUND(SUM(CASE WHEN NOT is_approved THEN amount ELSE 0 END), 2)
    comment: "Total value of declined transactions"
  - name: Avg Fraud Score
    expr: ROUND(AVG(fraud_score), 3)
    comment: "Average fraud risk score"
  - name: Unique Merchants
    expr: COUNT(DISTINCT merchant_id)
    comment: "Number of distinct merchants"
$$;

-- Metric View 2: Decline-focused metrics (decline analysis dashboard)
CREATE OR REPLACE VIEW decline_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "Decline-specific metrics for recovery and reason-code analysis"
source: payments_enriched_silver
filter: "NOT is_approved"
dimensions:
  - name: Decline Reason
    expr: decline_reason
    comment: "Reason code for the decline"
  - name: Merchant Segment
    expr: merchant_segment
    comment: "Merchant segment"
  - name: Card Network
    expr: card_network
    comment: "Card network"
measures:
  - name: Decline Count
    expr: COUNT(1)
    comment: "Number of declines"
  - name: Total Declined Value
    expr: ROUND(SUM(amount), 2)
    comment: "Total value of declined transactions"
  - name: Avg Fraud Score
    expr: ROUND(AVG(fraud_score), 3)
    comment: "Average fraud score for declines"
  - name: Avg Amount
    expr: ROUND(AVG(amount), 2)
    comment: "Average declined transaction amount"
  - name: Affected Merchants
    expr: COUNT(DISTINCT merchant_id)
    comment: "Number of distinct merchants with declines"
$$;

-- Metric View 3: Merchant segment metrics (merchant performance dashboard)
CREATE OR REPLACE VIEW merchant_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "Merchant segment performance metrics for segmentation dashboards"
source: payments_enriched_silver
dimensions:
  - name: Merchant Segment
    expr: merchant_segment
    comment: "Merchant segment"
measures:
  - name: Transaction Count
    expr: COUNT(1)
    comment: "Total transactions per segment"
  - name: Approved Count
    expr: COUNT_IF(is_approved = true)
    comment: "Approved transactions per segment"
  - name: Approval Rate Pct
    expr: ROUND(COUNT_IF(is_approved = true) * 100.0 / COUNT(1), 2)
    comment: "Approval rate percentage per segment"
  - name: Unique Merchants
    expr: COUNT(DISTINCT merchant_id)
    comment: "Distinct merchants per segment"
  - name: Total Value
    expr: ROUND(SUM(amount), 2)
    comment: "Total transaction value per segment"
  - name: Avg Fraud Score
    expr: ROUND(AVG(fraud_score), 3)
    comment: "Average fraud score per segment"
  - name: Auth 3DS Usage Pct
    expr: ROUND(COUNT_IF(uses_3ds = true) * 100.0 / COUNT(1), 2)
    comment: "Percentage of transactions using 3DS authentication"
$$;

-- ===========================================================================
-- SUMMARY: 15 standard views + 3 metric views for dashboards, Genie & agents
-- (v_retry_performance is managed by the Lakeflow pipeline — see gold_views.py)
-- ===========================================================================
