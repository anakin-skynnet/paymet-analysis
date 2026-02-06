# 0. Business Challenges & Value

## Business Challenge

Every declined legitimate transaction is lost revenue. Key pain points: **false declines**, **static rules**, **suboptimal routing**, **manual analysis**.

## Solution

Databricks-powered platform: (1) real-time ML on every transaction, (2) smart routing, (3) intelligent retry, (4) 7 AI agents, (5) Genie for natural-language analytics.

## Payment Services Context

| Service | Description | Status |
|---------|-------------|--------|
| Antifraud | Risk scoring; ~40–50% of declines | Active |
| 3DS | SCA; 60% auth success, 80% authenticated approved | Active |
| Vault, Data Only, Recurrence, Network Token, Click to Pay | Tokenization, enrichment, subscriptions, etc. | Active |
| IdPay, Passkey | Biometric, FIDO2 | Pre-prod / Dev |

**Requirement:** treat each payment attempt as a **service-composed flow** (Getnet + third parties) that affects **risk**, **friction**, and **approval**.

**How this platform represents it (instrumentation fields):**
- **Antifraud**: `antifraud_used`, `antifraud_result`, `fraud_score`
- **3DS**: `three_ds_routed`, `three_ds_friction`, `three_ds_authenticated` (plus `uses_3ds`)
- **Vault**: `vault_used`
- **Data Only**: `data_only_used`
- **Recurrence**: `is_recurring` (and scenario split `retry_scenario`)
- **Network Token**: `is_network_token`
- **IdPay**: `idpay_invoked`, `idpay_success`
- **Passkey**: `has_passkey`
- **Click to Pay**: `click_to_pay_used`

All flows are tracked end-to-end: **simulator → bronze → silver → gold → API → UI**.

## Data Foundation

**Smart Checkout**, **Reason Codes**, **Smart Retry** depend on: canonical data model, dedup (`canonical_transaction_key`), reason-code mapping, service-path tracking.

## Geography & Channels

Brazil >70% volume. Entry channels (Brazil): PD ~62%, WS ~34%, SEP ~3%, Checkout ~1%. Flows: Checkout BR → PD → WS → Base24 → Issuer; recurring/legacy variants.

**Brazil-first requirement (how we operationalize it):**
- `geo_country = 'BR'` is the default cohort for early initiative views and UI pages.
- Coverage is monitored by **entry system** (Checkout/PD/WS/SEP) so consolidation gaps show up early.
- Gold views that are explicitly Brazil-scoped are suffixed with `_br` (e.g., Smart Checkout, Reason Codes).

## Initiatives

| Initiative | Scope | Platform deliverables |
|------------|--------|------------------------|
| **Smart Checkout** | Payment links, Brazil | Service-path breakdown, 3DS funnel, antifraud attribution, decision logging |
| **Reason Codes** | Full e-commerce, Brazil | Consolidated declines (4 entry systems), unified taxonomy, actionable insights, feedback loop, False Insights counter-metric |
| **Smart Retry** | Brazil | Recurrence vs reattempt (`retry_scenario`), features, success rate, effectiveness (Effective/Moderate/Low) |

## Business requirements → solution mapping (point-by-point)

### 1) Payment services context (cross-cutting)
- **Business requirement**: persist which services were invoked per attempt, their outcomes, and where the final response was produced.
- **Solution**:
  - **Provenance**: `entry_system`, `flow_type`, `transaction_stage`, `merchant_response_code`
  - **Service path label**: `service_path` (compact “what happened” string per attempt)
- **Where**:
  - Generator: `src/payment_analysis/streaming/transaction_simulator.py`
  - Enrichment: `src/payment_analysis/transform/silver_transform.py` (`service_path`)
  - Smart Checkout gold: `src/payment_analysis/transform/gold_views.py` (`v_smart_checkout_service_path_br`)
- **Acceptance**: you can answer “approval + declines by service path” without manual joins.

### 2) Data foundation (mapping, treatment, quality)
- **Business requirement**: insights must be based on aligned, deduplicated, high-quality attempts.
- **Solution**:
  - **Canonical attempt key**: `canonical_transaction_key` (used to dedup across intermediation paths)
  - **Data quality expectations**: Lakeflow Declarative Pipelines expectations on required identifiers, amounts, provenance fields
  - **Merchant-visible consolidation**: a single attempt record per merchant-visible outcome (used by Reason Codes)
- **Where**:
  - Silver expectations + canonical key: `src/payment_analysis/transform/silver_transform.py`
  - Reason Codes inputs: `merchant_visible_attempts_silver` (created in silver; consumed in gold)
- **Acceptance**: Reason Codes views are stable (no obvious multi-entry double counting).

### 3) Geographic distribution (Brazil-first)
- **Business requirement**: Brazil is first-class for early initiatives (70%+ volume) but remains extensible.
- **Solution**: `geo_country` is a core dimension; gold views include Brazil-first versions for key initiatives.
- **Where**:
  - Generator distribution: `src/payment_analysis/streaming/transaction_simulator.py`
  - Gold cohort views: `src/payment_analysis/transform/gold_views.py` (`*_br` tables)
- **Acceptance**: KPIs/trends/declines/retry can be filtered to `geo_country = 'BR'`.

### 4) Smart Checkout (phase 1: payment link, Brazil)
- **Business requirement**: quantify service-path breakdown and 3DS funnel, and attribute antifraud declines.
- **Solution**:
  - **Service-path breakdown**: `v_smart_checkout_service_path_br`
  - **3DS funnel**: `v_3ds_funnel_br` (routed → friction → authenticated → approved)
  - **Antifraud attribution**: `antifraud_declines` and `% of declines` per service path
- **Where**:
  - Gold: `src/payment_analysis/transform/gold_views.py`
  - API: `src/payment_analysis/backend/routes/analytics.py` (`/smart-checkout/*` endpoints)
  - UI: `src/payment_analysis/ui/routes/_sidebar/smart-checkout.tsx`
- **Acceptance**: stakeholders can see the funnel percentages and antifraud decline contribution.

### 5) Reason Codes (Brazil-first, full e-comm coverage)
- **Business requirement**: consolidate final outcomes across Checkout/PD/WS/SEP and standardize to one taxonomy.
- **Solution**:
  - Standardized fields: `decline_reason_standard`, `decline_reason_group`, `recommended_action`
  - Gold outputs: `v_reason_codes_br`, `v_reason_code_insights_br`, `v_entry_system_distribution_br`
  - Coverage sanity + dedup health: entry-system distribution and dedup collision stats
- **Where**:
  - Gold: `src/payment_analysis/transform/gold_views.py`
  - API: `src/payment_analysis/backend/routes/analytics.py` (`/reason-codes/*`)
  - UI: `src/payment_analysis/ui/routes/_sidebar/reason-codes.tsx`
- **Acceptance**: UI shows top standardized reasons with segmentation and recommended actions.

### 6) Intelligence layer + learning loop (prescriptive over time)
- **Business requirement**: improve decisions by capturing actions and expert feedback over time.
- **Solution**:
  - Feedback table: `insight_feedback_silver`
  - “False Insights” counter-metric view: `v_false_insights_metric`
  - Feedback ingestion endpoint: submit expert review events via API
- **Where**:
  - Silver + gold: `src/payment_analysis/transform/silver_transform.py`, `src/payment_analysis/transform/gold_views.py`
  - API: `src/payment_analysis/backend/routes/analytics.py` (feedback + metric endpoints)
  - UI: `src/payment_analysis/ui/routes/_sidebar/reason-codes.tsx` (counter-metric card)
- **Acceptance**: false-insights % is queryable and visible in the app.

### 7) Counter-metric: False Insights (quality control)
- **Business requirement**: constrain and monitor low-quality recommendations.
- **Solution**: compute `% invalid or non_actionable` over reviewed insights and surface it.
- **Where**: `v_false_insights_metric` + `/reason-codes/false-insights-metric` API + UI card.
- **Acceptance**: metric updates as reviews are submitted; thresholds can be applied in UI.

### 8) Smart Retry (recurrence vs reattempts)
- **Business requirement**: separate PaymentRecurrence vs PaymentRetry and measure incremental lift.
- **Solution**:
  - Scenario split: `retry_scenario`
  - Features: attempt sequencing and `time_since_last_attempt_seconds`, `prior_approved_count`
  - Gold: `v_retry_performance` with baseline and `incremental_lift_pct`
- **Where**:
  - Silver features: `src/payment_analysis/transform/silver_transform.py`
  - Gold: `src/payment_analysis/transform/gold_views.py`
  - API/UI: `src/payment_analysis/backend/routes/analytics.py`, `src/payment_analysis/ui/routes/_sidebar/smart-retry.tsx`
- **Acceptance**: retry performance includes lift vs baseline and key explanatory features.

## Key Objectives & Impact

| Goal | Target | Initiative lift (approval) |
|------|--------|---------------------------|
| Approval rates | 90%+ | Smart routing +2–5%, retry +1–2%, false positive reduction +1–2%, network token +1–3%, 3DS +0.5–1% → **+6–13% total** |
| Operational | ~80% faster insights | Genie 100+ MAU; ~20 h/week reporting saved; ~40% fewer manual reviews |

## Why Databricks

Unified data + ML + apps; real-time; scalable; Unity Catalog; serverless.

## Success Metrics

**Primary:** Approval 90%+; revenue recovery; false positive <2%. **Secondary:** Genie adoption, query success >85%, model latency <50ms p95. **Counter:** False Insights rate. **Monitoring:** Real-time (serving); daily (approval/retry); weekly (Genie/drift); monthly (ROI).

---

**Next:** [1_DEPLOYMENTS](1_DEPLOYMENTS.md) · [2_DATA_FLOW](2_DATA_FLOW.md) · [3_AGENTS_VALUE](3_AGENTS_VALUE.md) · [4_TECHNICAL](4_TECHNICAL.md) · [5_DEMO_SETUP](5_DEMO_SETUP.md)
