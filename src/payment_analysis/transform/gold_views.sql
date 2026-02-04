-- ============================================================================
-- Gold Views for Payment Analysis Platform
-- ============================================================================
-- Catalog: ${catalog}
-- Schema: payment_analysis_${environment}
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
-- RETRY ANALYTICS VIEWS
-- ===========================================================================

-- View 10: Retry Performance
CREATE OR REPLACE VIEW v_retry_performance AS
SELECT 
    decline_reason,
    retry_count,
    COUNT(*) as retry_attempts,
    ROUND(SUM(CASE WHEN is_approved THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as retry_success_rate_pct,
    ROUND(AVG(fraud_score), 3) as avg_fraud_score,
    ROUND(SUM(CASE WHEN is_approved THEN amount ELSE 0 END), 2) as recovered_value,
    CASE
        WHEN AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) > 0.4 THEN 'Effective'
        WHEN AVG(CASE WHEN is_approved THEN 1.0 ELSE 0.0 END) > 0.2 THEN 'Moderate'
        ELSE 'Low'
    END as effectiveness
FROM payments_enriched_silver
WHERE is_retry = true
  AND event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY decline_reason, retry_count
ORDER BY decline_reason, retry_count;

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
-- SUMMARY: 12 views created for dashboards and analytics
-- ===========================================================================
