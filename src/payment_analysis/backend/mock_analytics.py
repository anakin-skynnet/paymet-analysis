"""Mock analytics data for when Databricks is unavailable.

Every function returns realistic payment analytics data using the same Pydantic
models as the real endpoints.  This module is used **only** as a fallback — the
backend always tries Databricks first.

When real data is available from Databricks, this module is never called.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _ts_str(dt: datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------------------
# KPIs (used by /kpis when local DB is also empty)
# ---------------------------------------------------------------------------

def mock_kpis() -> dict[str, Any]:
    return {
        "total": 148_520,
        "approved": 131_390,
        "approval_rate": 0.8847,
    }


# ---------------------------------------------------------------------------
# Approval trends (last hour, per-second)
# ---------------------------------------------------------------------------

def mock_approval_trends(seconds: int = 3600) -> list[dict[str, Any]]:
    now = _now()
    step = max(1, seconds // 60)
    points: list[dict[str, Any]] = []
    import random
    rng = random.Random(42)
    for i in range(0, seconds, step):
        ts = now - timedelta(seconds=seconds - i)
        rate = 0.85 + rng.uniform(-0.04, 0.06)
        txn = rng.randint(20, 60)
        approved = int(txn * rate)
        points.append({
            "event_second": _ts_str(ts),
            "transaction_count": txn,
            "approved_count": approved,
            "approval_rate_pct": round(rate * 100, 2),
            "avg_fraud_score": round(rng.uniform(0.05, 0.35), 3),
            "total_value": round(txn * rng.uniform(80, 250), 2),
        })
    return points


# ---------------------------------------------------------------------------
# Daily trends (14-day)
# ---------------------------------------------------------------------------

def mock_daily_trends(days: int = 14) -> list[dict[str, Any]]:
    import random
    rng = random.Random(77)
    now = _now()
    rows: list[dict[str, Any]] = []
    for d in range(days, 0, -1):
        dt = now - timedelta(days=d)
        total = rng.randint(8_000, 15_000)
        rate = round(rng.uniform(84.0, 92.0), 1)
        approved = int(total * rate / 100)
        rows.append({
            "event_date": _date_str(dt),
            "total_transactions": total,
            "approved_count": approved,
            "approval_rate": rate,
        })
    return rows


# ---------------------------------------------------------------------------
# Decline buckets
# ---------------------------------------------------------------------------

def mock_decline_summary() -> list[dict[str, Any]]:
    return [
        {"key": "Insufficient Funds", "count": 3_420, "pct_of_declines": 28.5, "total_value": 512_800.0, "recoverable_pct": 65.0},
        {"key": "Do Not Honor", "count": 2_180, "pct_of_declines": 18.2, "total_value": 345_000.0, "recoverable_pct": 40.0},
        {"key": "Card Expired", "count": 1_540, "pct_of_declines": 12.8, "total_value": 198_000.0, "recoverable_pct": 20.0},
        {"key": "Fraud Suspected", "count": 1_320, "pct_of_declines": 11.0, "total_value": 285_000.0, "recoverable_pct": 15.0},
        {"key": "Invalid Card", "count": 980, "pct_of_declines": 8.2, "total_value": 142_000.0, "recoverable_pct": 10.0},
        {"key": "Transaction Not Permitted", "count": 820, "pct_of_declines": 6.8, "total_value": 118_000.0, "recoverable_pct": 55.0},
        {"key": "Exceeds Amount Limit", "count": 640, "pct_of_declines": 5.3, "total_value": 320_000.0, "recoverable_pct": 70.0},
        {"key": "Restricted Card", "count": 420, "pct_of_declines": 3.5, "total_value": 67_000.0, "recoverable_pct": 5.0},
    ]


# ---------------------------------------------------------------------------
# Recovery opportunities
# ---------------------------------------------------------------------------

def mock_decline_recovery_opportunities() -> list[dict[str, Any]]:
    return [
        {"decline_reason": "Insufficient Funds", "transaction_count": 3_420, "recoverable_amount": 333_320, "recovery_strategy": "Smart Retry (24h delay)"},
        {"decline_reason": "Do Not Honor", "transaction_count": 2_180, "recoverable_amount": 138_000, "recovery_strategy": "Alternate Routing"},
        {"decline_reason": "Exceeds Amount Limit", "transaction_count": 640, "recoverable_amount": 224_000, "recovery_strategy": "Split Payment"},
        {"decline_reason": "Transaction Not Permitted", "transaction_count": 820, "recoverable_amount": 64_900, "recovery_strategy": "3DS Authentication"},
        {"decline_reason": "Card Expired", "transaction_count": 1_540, "recoverable_amount": 39_600, "recovery_strategy": "Account Updater"},
        {"decline_reason": "Fraud Suspected", "transaction_count": 1_320, "recoverable_amount": 42_750, "recovery_strategy": "3DS + Risk Review"},
    ]


# ---------------------------------------------------------------------------
# Card network performance
# ---------------------------------------------------------------------------

def mock_card_network_performance() -> list[dict[str, Any]]:
    return [
        {"card_network": "Visa", "transaction_count": 62_400, "approval_rate": 91.2},
        {"card_network": "Mastercard", "transaction_count": 48_300, "approval_rate": 89.5},
        {"card_network": "Elo", "transaction_count": 18_700, "approval_rate": 86.3},
        {"card_network": "Amex", "transaction_count": 9_800, "approval_rate": 84.1},
        {"card_network": "Hipercard", "transaction_count": 5_200, "approval_rate": 82.7},
        {"card_network": "Diners", "transaction_count": 2_100, "approval_rate": 80.4},
    ]


# ---------------------------------------------------------------------------
# Merchant segment performance
# ---------------------------------------------------------------------------

def mock_merchant_segment_performance() -> list[dict[str, Any]]:
    return [
        {"merchant_segment": "E-commerce", "transaction_count": 52_100, "approval_rate": 90.3, "avg_transaction_amount": 185.50},
        {"merchant_segment": "Travel & Airlines", "transaction_count": 18_400, "approval_rate": 86.7, "avg_transaction_amount": 620.00},
        {"merchant_segment": "Subscriptions", "transaction_count": 28_900, "approval_rate": 93.1, "avg_transaction_amount": 45.80},
        {"merchant_segment": "Gaming", "transaction_count": 15_200, "approval_rate": 82.4, "avg_transaction_amount": 32.00},
        {"merchant_segment": "Retail POS", "transaction_count": 22_300, "approval_rate": 95.2, "avg_transaction_amount": 78.30},
        {"merchant_segment": "Marketplaces", "transaction_count": 11_600, "approval_rate": 88.9, "avg_transaction_amount": 142.00},
    ]


# ---------------------------------------------------------------------------
# Solution performance
# ---------------------------------------------------------------------------

def mock_solution_performance() -> list[dict[str, Any]]:
    return [
        {"payment_solution": "Standard", "transaction_count": 68_200, "approved_count": 58_892, "approval_rate_pct": 86.36, "avg_amount": 145.20, "total_value": 9_898_640.0},
        {"payment_solution": "3DS", "transaction_count": 42_100, "approved_count": 38_731, "approval_rate_pct": 92.00, "avg_amount": 210.50, "total_value": 8_862_050.0},
        {"payment_solution": "Network Token", "transaction_count": 22_800, "approved_count": 21_432, "approval_rate_pct": 94.00, "avg_amount": 175.00, "total_value": 3_990_000.0},
        {"payment_solution": "Passkey", "transaction_count": 15_420, "approved_count": 14_649, "approval_rate_pct": 95.00, "avg_amount": 198.00, "total_value": 3_053_160.0},
    ]


# ---------------------------------------------------------------------------
# Reason code insights
# ---------------------------------------------------------------------------

def mock_reason_code_insights() -> list[dict[str, Any]]:
    return [
        {"entry_system": "PD", "flow_type": "Authorize", "decline_reason_standard": "Insufficient Funds",
         "decline_reason_group": "Soft Decline", "recommended_action": "Retry after 24h with updated BIN routing",
         "decline_count": 3_420, "pct_of_declines": 28.5, "total_declined_value": 512_800.0,
         "estimated_recoverable_declines": 2_223, "estimated_recoverable_value": 333_320.0, "priority": 1},
        {"entry_system": "PD", "flow_type": "Authorize", "decline_reason_standard": "Do Not Honor",
         "decline_reason_group": "Hard Decline", "recommended_action": "Route through alternate acquirer or enable 3DS",
         "decline_count": 2_180, "pct_of_declines": 18.2, "total_declined_value": 345_000.0,
         "estimated_recoverable_declines": 872, "estimated_recoverable_value": 138_000.0, "priority": 2},
        {"entry_system": "WS", "flow_type": "Authorize", "decline_reason_standard": "Fraud Suspected",
         "decline_reason_group": "Fraud", "recommended_action": "Enable 3DS for transactions above $100; review risk thresholds",
         "decline_count": 1_320, "pct_of_declines": 11.0, "total_declined_value": 285_000.0,
         "estimated_recoverable_declines": 198, "estimated_recoverable_value": 42_750.0, "priority": 3},
        {"entry_system": "PD", "flow_type": "Authorize", "decline_reason_standard": "Transaction Not Permitted",
         "decline_reason_group": "Configuration", "recommended_action": "Update MCC configuration and enable card-level controls",
         "decline_count": 820, "pct_of_declines": 6.8, "total_declined_value": 118_000.0,
         "estimated_recoverable_declines": 451, "estimated_recoverable_value": 64_900.0, "priority": 4},
        {"entry_system": "SEP", "flow_type": "Capture", "decline_reason_standard": "Exceeds Amount Limit",
         "decline_reason_group": "Soft Decline", "recommended_action": "Implement split-payment or installment flow",
         "decline_count": 640, "pct_of_declines": 5.3, "total_declined_value": 320_000.0,
         "estimated_recoverable_declines": 448, "estimated_recoverable_value": 224_000.0, "priority": 5},
    ]


# ---------------------------------------------------------------------------
# Entry system distribution
# ---------------------------------------------------------------------------

def mock_entry_system_distribution() -> list[dict[str, Any]]:
    return [
        {"entry_system": "PD", "transaction_count": 92_040, "approved_count": 81_795, "approval_rate_pct": 88.87, "total_value": 14_500_000.0},
        {"entry_system": "WS", "transaction_count": 50_510, "approved_count": 44_449, "approval_rate_pct": 88.00, "total_value": 7_200_000.0},
        {"entry_system": "SEP", "transaction_count": 4_450, "approved_count": 3_916, "approval_rate_pct": 88.00, "total_value": 980_000.0},
        {"entry_system": "Checkout", "transaction_count": 1_520, "approved_count": 1_230, "approval_rate_pct": 80.92, "total_value": 420_000.0},
    ]


# ---------------------------------------------------------------------------
# Geography (world map)
# ---------------------------------------------------------------------------

def mock_geography() -> list[dict[str, Any]]:
    return [
        {"country": "BR", "transaction_count": 95_000, "approval_rate_pct": 88.5, "total_transaction_value": 15_200_000.0},
        {"country": "MX", "transaction_count": 18_200, "approval_rate_pct": 85.2, "total_transaction_value": 2_800_000.0},
        {"country": "US", "transaction_count": 12_400, "approval_rate_pct": 92.1, "total_transaction_value": 3_500_000.0},
        {"country": "AR", "transaction_count": 8_700, "approval_rate_pct": 81.3, "total_transaction_value": 1_100_000.0},
        {"country": "CL", "transaction_count": 6_200, "approval_rate_pct": 87.9, "total_transaction_value": 890_000.0},
        {"country": "CO", "transaction_count": 4_100, "approval_rate_pct": 83.6, "total_transaction_value": 520_000.0},
        {"country": "PE", "transaction_count": 2_800, "approval_rate_pct": 84.1, "total_transaction_value": 350_000.0},
        {"country": "DE", "transaction_count": 1_120, "approval_rate_pct": 93.5, "total_transaction_value": 280_000.0},
    ]


# ---------------------------------------------------------------------------
# Active alerts
# ---------------------------------------------------------------------------

def mock_active_alerts() -> list[dict[str, Any]]:
    now = _now()
    return [
        {"alert_type": "Approval Rate Drop", "severity": "high", "metric_name": "approval_rate",
         "current_value": 82.3, "threshold_value": 85.0,
         "alert_message": "Approval rate dropped below 85% for Gaming segment in the last 15 minutes",
         "first_detected": _ts_str(now - timedelta(minutes=12))},
        {"alert_type": "Fraud Score Spike", "severity": "medium", "metric_name": "avg_fraud_score",
         "current_value": 0.42, "threshold_value": 0.35,
         "alert_message": "Average fraud score elevated for cross-border transactions from AR",
         "first_detected": _ts_str(now - timedelta(minutes=28))},
        {"alert_type": "Latency Warning", "severity": "low", "metric_name": "processing_time_ms",
         "current_value": 450.0, "threshold_value": 400.0,
         "alert_message": "P95 processing latency above 400ms for 3DS flow",
         "first_detected": _ts_str(now - timedelta(minutes=45))},
    ]


# ---------------------------------------------------------------------------
# False insights metric
# ---------------------------------------------------------------------------

def mock_false_insights_metric() -> list[dict[str, Any]]:
    now = _now()
    rows: list[dict[str, Any]] = []
    for d in range(7, 0, -1):
        dt = now - timedelta(days=d)
        rows.append({
            "event_date": _date_str(dt),
            "reviewed_insights": 120 + d * 5,
            "false_insights": 8 + d,
            "false_insights_pct": round((8 + d) / (120 + d * 5) * 100, 1),
        })
    return rows


# ---------------------------------------------------------------------------
# Retry performance
# ---------------------------------------------------------------------------

def mock_retry_performance() -> list[dict[str, Any]]:
    return [
        {"retry_scenario": "PaymentRetry", "decline_reason_standard": "Insufficient Funds",
         "retry_count": 1_840, "retry_attempts": 2_200, "success_rate_pct": 62.5,
         "recovered_value": 245_000.0, "avg_fraud_score": 0.12,
         "avg_time_since_last_attempt_s": 86400.0, "avg_prior_approvals": 3.2,
         "baseline_approval_pct": 45.0, "incremental_lift_pct": 17.5, "effectiveness": "high"},
        {"retry_scenario": "PaymentRecurrence", "decline_reason_standard": "Insufficient Funds",
         "retry_count": 2_100, "retry_attempts": 2_500, "success_rate_pct": 71.0,
         "recovered_value": 312_000.0, "avg_fraud_score": 0.08,
         "avg_time_since_last_attempt_s": 2592000.0, "avg_prior_approvals": 5.1,
         "baseline_approval_pct": 50.0, "incremental_lift_pct": 21.0, "effectiveness": "high"},
        {"retry_scenario": "PaymentRetry", "decline_reason_standard": "Do Not Honor",
         "retry_count": 920, "retry_attempts": 1_800, "success_rate_pct": 38.2,
         "recovered_value": 98_000.0, "avg_fraud_score": 0.22,
         "avg_time_since_last_attempt_s": 3600.0, "avg_prior_approvals": 1.8,
         "baseline_approval_pct": 30.0, "incremental_lift_pct": 8.2, "effectiveness": "medium"},
    ]


# ---------------------------------------------------------------------------
# 3DS funnel
# ---------------------------------------------------------------------------

def mock_3ds_funnel() -> list[dict[str, Any]]:
    now = _now()
    return [
        {"event_date": _date_str(now - timedelta(days=1)),
         "total_transactions": 42_100, "three_ds_routed_count": 42_100,
         "three_ds_friction_count": 8_420, "three_ds_authenticated_count": 38_731,
         "issuer_approved_after_auth_count": 35_241,
         "three_ds_friction_rate_pct": 20.0, "three_ds_authentication_rate_pct": 92.0,
         "issuer_approval_post_auth_rate_pct": 91.0},
    ]


# ---------------------------------------------------------------------------
# Smart Checkout service paths
# ---------------------------------------------------------------------------

def mock_smart_checkout_service_paths() -> list[dict[str, Any]]:
    return [
        {"service_path": "Standard → Visa Direct", "transaction_count": 28_400, "approved_count": 25_560,
         "approval_rate_pct": 90.0, "avg_fraud_score": 0.12, "total_value": 4_260_000.0,
         "antifraud_declines": 850, "antifraud_pct_of_declines": 29.9},
        {"service_path": "3DS → Mastercard", "transaction_count": 18_200, "approved_count": 16_744,
         "approval_rate_pct": 92.0, "avg_fraud_score": 0.09, "total_value": 3_822_000.0,
         "antifraud_declines": 290, "antifraud_pct_of_declines": 19.9},
        {"service_path": "Token → Elo", "transaction_count": 8_300, "approved_count": 7_802,
         "approval_rate_pct": 94.0, "avg_fraud_score": 0.07, "total_value": 1_245_000.0,
         "antifraud_declines": 100, "antifraud_pct_of_declines": 20.1},
    ]


# ---------------------------------------------------------------------------
# Smart Checkout path performance
# ---------------------------------------------------------------------------

def mock_smart_checkout_path_performance() -> list[dict[str, Any]]:
    return [
        {"recommended_path": "3DS + Network Token", "transaction_count": 22_800, "approved_count": 21_432,
         "approval_rate_pct": 94.0, "total_value": 3_990_000.0},
        {"recommended_path": "Standard + Smart Retry", "transaction_count": 38_500, "approved_count": 33_880,
         "approval_rate_pct": 88.0, "total_value": 5_582_500.0},
        {"recommended_path": "Passkey + Direct Auth", "transaction_count": 15_420, "approved_count": 14_649,
         "approval_rate_pct": 95.0, "total_value": 3_053_160.0},
    ]


# ---------------------------------------------------------------------------
# Streaming TPS
# ---------------------------------------------------------------------------

def mock_streaming_tps() -> list[dict[str, Any]]:
    now = _now()
    import random
    rng = random.Random(99)
    return [
        {"event_second": _ts_str(now - timedelta(seconds=60 - i)), "records_per_second": rng.randint(15, 45)}
        for i in range(60)
    ]


# ---------------------------------------------------------------------------
# Command-center entry throughput
# ---------------------------------------------------------------------------

def mock_entry_throughput() -> list[dict[str, Any]]:
    now = _now()
    import random
    rng = random.Random(55)
    return [
        {
            "ts": _ts_str(now - timedelta(seconds=60 - i)),
            "PD": rng.randint(15, 35),
            "WS": rng.randint(8, 20),
            "SEP": rng.randint(1, 5),
            "Checkout": rng.randint(0, 3),
        }
        for i in range(60)
    ]


# ---------------------------------------------------------------------------
# Online features, countries, models (for toggle = mock when no Lakebase/UC)
# ---------------------------------------------------------------------------

def mock_online_features(limit: int = 100) -> list[dict[str, Any]]:
    """Mock online feature rows for UI when mock toggle is on."""
    now = _now()
    return [
        {"id": "of-1", "source": "ml", "feature_set": "approval", "feature_name": "fraud_score", "feature_value": 0.12, "feature_value_str": None, "entity_id": "tx-001", "created_at": _ts_str(now)},
        {"id": "of-2", "source": "ml", "feature_set": "approval", "feature_name": "amount", "feature_value": 89.5, "feature_value_str": None, "entity_id": "tx-001", "created_at": _ts_str(now)},
        {"id": "of-3", "source": "agent", "feature_set": "context", "feature_name": "merchant_segment", "feature_value": None, "feature_value_str": "retail", "entity_id": "tx-002", "created_at": _ts_str(now - timedelta(minutes=5))},
    ][:limit]


def mock_countries(limit: int = 200) -> list[dict[str, Any]]:
    """Mock country/entity rows for filter dropdown when mock toggle is on."""
    return [
        {"code": "BR", "name": "Brazil"},
        {"code": "US", "name": "United States"},
        {"code": "MX", "name": "Mexico"},
        {"code": "CO", "name": "Colombia"},
        {"code": "AR", "name": "Argentina"},
    ][:limit]


def mock_models(entity: str = "BR") -> list[dict[str, Any]]:
    """Mock ML model list when mock toggle is on."""
    return [
        {"id": "approval-propensity", "name": "Approval Propensity", "description": "Predicts approval probability", "model_type": "classification", "features": ["amount", "fraud_score", "device_trust_score"], "catalog_path": "catalog.schema.approval_propensity", "metrics": [{"name": "accuracy", "value": "0.89"}]},
        {"id": "risk-scoring", "name": "Risk Scoring", "description": "Fraud risk score", "model_type": "regression", "features": ["amount", "merchant_segment"], "catalog_path": "catalog.schema.risk_scoring", "metrics": [{"name": "rmse", "value": "0.12"}]},
    ]


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def mock_recommendations() -> list[dict[str, Any]]:
    now = _now()
    return [
        {"id": "rec-001", "context_summary": "Gaming merchants with high decline rates on cross-border Visa transactions",
         "recommended_action": "Enable 3DS authentication for transactions above $50 in Gaming segment to reduce fraud-related declines by ~15%",
         "score": 0.92, "source_type": "ml_agent", "created_at": _ts_str(now - timedelta(hours=2))},
        {"id": "rec-002", "context_summary": "Subscriptions with recurring insufficient funds declines",
         "recommended_action": "Implement smart retry with 24h delay and account updater integration to recover ~65% of soft declines",
         "score": 0.88, "source_type": "rule_engine", "created_at": _ts_str(now - timedelta(hours=5))},
        {"id": "rec-003", "context_summary": "Travel segment experiencing Do Not Honor declines on Mastercard",
         "recommended_action": "Route high-value travel transactions through alternate acquirer and enable network tokenization",
         "score": 0.85, "source_type": "ml_agent", "created_at": _ts_str(now - timedelta(hours=8))},
    ]


# ---------------------------------------------------------------------------
# Last hour / last 60 seconds performance
# ---------------------------------------------------------------------------

def mock_last_hour_performance() -> dict[str, Any]:
    return {
        "transactions_last_hour": 4_280,
        "approval_rate_pct": 88.4,
        "avg_fraud_score": 0.18,
        "total_value": 642_000.0,
        "active_segments": 6,
        "high_risk_transactions": 145,
        "declines_last_hour": 497,
    }


def mock_last_60_seconds_performance() -> dict[str, Any]:
    return {
        "transactions_last_60s": 72,
        "approval_rate_pct": 90.3,
        "avg_fraud_score": 0.14,
        "total_value": 10_800.0,
        "declines_last_60s": 7,
    }


# ---------------------------------------------------------------------------
# Data quality summary
# ---------------------------------------------------------------------------

def mock_data_quality_summary() -> dict[str, Any]:
    now = _now()
    return {
        "bronze_last_24h": 148_520,
        "silver_last_24h": 142_400,
        "retention_pct_24h": 95.9,
        "latest_bronze_ingestion": _ts_str(now - timedelta(seconds=15)),
        "latest_silver_event": _ts_str(now - timedelta(seconds=45)),
    }
