# Overview: Business Challenges & Value

**Payment Analysis** — business context, initiatives, and AI agents.

## Business Challenge

Every declined legitimate transaction is lost revenue. Key pain points: **false declines**, **static rules**, **suboptimal routing**, **manual analysis**.

## Solution

Databricks-powered platform: (1) real-time ML on every transaction, (2) smart routing, (3) intelligent retry, (4) 7 AI agents, (5) Genie for natural-language analytics.

## Payment Services Context

| Service | Description | Status |
|---------|-------------|--------|
| Antifraud | Risk scoring; ~40–50% of declines | Active |
| 3DS | SCA; 60% auth success, 80% authenticated approved | Active |
| Vault, Data Only, Recurrence, Network Token, Click to Pay | Tokenization, enrichment, subscriptions | Active |
| IdPay, Passkey | Biometric, FIDO2 | Pre-prod / Dev |

**Instrumentation:** Each attempt is a service-composed flow. Fields: `antifraud_used`, `antifraud_result`, `fraud_score`; `three_ds_*`, `vault_used`, `data_only_used`, `is_recurring`, `retry_scenario`, `is_network_token`, `idpay_invoked`, `idpay_success`, `has_passkey`, `click_to_pay_used`. All tracked **simulator → bronze → silver → gold → API → UI**.

## Data Foundation & Geography

**Smart Checkout**, **Reason Codes**, **Smart Retry** depend on: canonical data model, dedup (`canonical_transaction_key`), reason-code mapping, service-path tracking.

Brazil >70% volume. Entry channels (Brazil): PD ~62%, WS ~34%, SEP ~3%, Checkout ~1%. Gold views Brazil-scoped are suffixed `_br`.

## Initiatives

| Initiative | Scope | Deliverables |
|------------|--------|--------------|
| **Smart Checkout** | Payment links, Brazil | Service-path breakdown, 3DS funnel, antifraud attribution |
| **Reason Codes** | Full e-commerce, Brazil | Consolidated declines (4 entry systems), unified taxonomy, insights, feedback, False Insights counter-metric |
| **Smart Retry** | Brazil | Recurrence vs reattempt (`retry_scenario`), success rate, effectiveness (Effective/Moderate/Low) |

## AI Agents & Business Value

Seven agents to increase approval rates (e.g. 85% → 90%+).

| # | Agent | Type | Purpose | Impact |
|---|-------|------|---------|--------|
| 1 | Approval Optimizer | Genie | Explore approval data without SQL | ~80% faster insights; 100+ users |
| 2 | Decline Insights | Genie | Understand/reduce declines via NL | +15–25% recovery |
| 3 | Approval Propensity Predictor | Model Serving | Real-time approval probability | <50ms p95; ~40% less manual review |
| 4 | Smart Routing Advisor | Model Serving | Recommend solution (3DS, token, etc.) | +2–5% approval; $2–5M/year @ $1B vol |
| 5 | Smart Retry Optimizer | Model Serving | Which declines to retry, when | +15–25% vs random; $1.5–2.5M/year @ $1B |
| 6 | Payment Intelligence Assistant | Mosaic AI Gateway (Llama 3.1) | Root cause, recommendations | ~90% faster root cause; 10–20 h/week saved |
| 7 | Risk Assessment Advisor | Mosaic AI Gateway (Llama 3.1) | Risk explanation, mitigation | 20–30% fewer false positives |

**Aggregate impact:** Smart routing / Retry / False positive reduction / Network token / 3DS → **$6.5–13.5M/year** (illustrative, $1B vol). Operational: ~80% faster analyst; Genie 100+ MAU; ~20 h/week reporting saved. **ROI (illustrative):** Cost ~$300K/year; payback <3 weeks.

**Success metrics:** Approval 90%+; revenue recovery; false positive <2%. Genie adoption, query success >85%, model <50ms. Security: Unity Catalog; no raw card to LLMs; audit logging.

## Accelerating with Agent Bricks & Mosaic AI

Use [Agent Bricks](https://www.databricks.com/blog/introducing-agent-bricks), [Mosaic AI Agent Framework](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/create-agent), and [Mosaic AI](https://www.databricks.com/product/artificial-intelligence) to tune agents: define “maximize approval/recovery,” connect Lakehouse data, add evaluation, and let the platform optimize. **Vector Search** (`resources/vector_search.yml`, create manually) powers similar-transaction lookups for recommendations.

---

**See also:** [DEPLOYMENT](DEPLOYMENT.md) · [TECHNICAL](TECHNICAL.md)
