# Payment Analysis — Business Requirements

Business context, use cases, and how each component accelerates payment approval rates. For architecture and technical details see [Technical Solution](TECHNICAL_SOLUTION.md); for deploy and configuration see [Reference Guide](REFERENCE_GUIDE.md).

---

## 1. Business overview

**Primary goal:** Accelerate payment approval rates and reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities.

**Approach:** Real-time ML (4 HistGradientBoosting models with 14 engineered features), closed-loop decisioning with parallel enrichment, streaming features, a ResponsesAgent (MLflow, 10 UC tools + python_exec) with write-back capabilities, and actionable analytics so every decision (auth, retry, routing) is data-driven, continuously improving, and consistent with business policy.

---

## 2. Use cases and impact on approval rates

| Use case | What it does | Impact on accelerating approval rates |
|----------|----------------|---------------------------------------|
| **Smart Retry** | Retry logic, timing, cohorts; ML retry model; recovery gap analysis; `v_retry_success_by_reason` gold view | Surfaces recoverable declines with recovery gap per cohort; granular retry success by decline reason and scenario. |
| **Smart Checkout** | 3DS funnel with contextual guidance, service-path performance, Brazil payment links | Balances friction vs risk with threshold-based recommendations on each metric. |
| **Reason codes & declines** | Unified decline taxonomy, inline expert review (Valid/Invalid/Non-Actionable), recovery opportunities | Identifies top decline reasons with direct feedback; Decline Analyst writes recommendations to Lakebase. |
| **Risk & fraud** | Risk tier, fraud score, Risk Assessor agent with write-back tools | Enables risk-based auth; agent proposes config changes to Lakebase. |
| **Routing optimization** | Routing performance, VS top-route boosting, Smart Routing agent, model serving | Routes to best solution using VS approval rates and agent confidence. |
| **Decisioning** | Closed-loop auth/retry/routing; parallel ML + VS + streaming features; outcome recording | Unifies all signals; policies adjust borderline decisions; feedback loop via POST /outcome. |

---

## 3. Technology map

| Technology | Role | How it accelerates approval rates |
|------------|------|-----------------------------------|
| **Lakeflow (Bronze → Silver → Gold)** | Ingestion and transforms | Clean, timely data for ML and analytics. |
| **Unity Catalog** | Tables, governance, gold views | Single source of truth for KPIs and model inputs. |
| **ML models** (4 HistGradientBoosting, 14 features) | Real-time scores with training-inference parity | Decisions based on predicted likelihood and risk; `_build_ml_features()` ensures exact match. |
| **Rules engine** (Lakebase/Lakehouse) | Configurable business rules + config API | Operators tune without code; config exposed via GET /api/decision/config. |
| **Vector Search** | Similar-transaction lookup + policy integration | VS approval rates adjust borderline risk tiers in policies. |
| **ResponsesAgent** (10 UC tools + python_exec) | Data-driven analytics, recommendations, config proposals | Agent queries UC functions, writes recommendations and proposes config changes to Lakebase. Served as `payment-response-agent`. |
| **3 unified dashboards + 24 gold views + 9 gold DLT tables** | KPIs, funnels, reason codes, retry-by-reason | Visibility into approvals/declines; v_retry_success_by_reason for granular retry analysis. |
| **Streaming features** | Real-time behavioral features | approval_rate_5m, txn_velocity_1m feed into authentication decisions. |
| **FastAPI + React app** | Closed-loop decision API and actionable control panel | Preset scenarios, inline expert review, recovery gap, top-3 actions, 90% target lines. |
| **Outcome feedback loop** | POST /api/decision/outcome | Records actual outcomes; system continuously improves. |
| **Dual-write sync** | Approval rules synced between Lakebase and Lakehouse | Rules changes in the UI propagate to agents (and vice versa) via BackgroundTasks. |

**High-level flow:** Simulator or real pipelines → Lakeflow → Unity Catalog → Intelligence (ML + rules + Vector Search + AI agents) → Application (FastAPI backend + React UI).

---

## 4. Component-by-component impact

| Component | What it is | How it accelerates approval rates |
|-----------|------------|-----------------------------------|
| **Medallion (Bronze → Silver → Gold)** | Lakeflow pipelines, 24 gold SQL views, and 9 gold DLT tables: `payments_raw_bronze`, `merchants_dim_bronze` (100 merchants, 8 segments), `payments_enriched_silver`, gold views (KPIs, trends, reason codes, retry performance, `v_retry_success_by_reason`). | Provides clean, timely data so ML models, rules, and dashboards see accurate patterns; `v_retry_success_by_reason` enables granular retry analysis by decline reason and scenario. |
| **Unity Catalog & Lakehouse** | Catalog/schema, volumes, `app_config`, gold views, and (optionally) rules/recommendations in Delta tables. | Single source of truth for catalog/schema and config; gold views feed dashboards and agents; rules and recommendations drive approve/decline/retry behavior. |
| **Lakebase (Postgres)** | Managed Postgres for `app_config`, `approval_rules`, `app_settings`, `online_features`, experiments, incidents. | Stores business rules and config that ML and agents read; experiments support A/B tests (e.g. 3DS strategy); operators tune rules without code to approve more good transactions and block more fraud. |
| **Rules engine (approval rules)** | Configurable rules (conditions + actions) from Lakebase or Lakehouse; exposed via `/api/rules`. **Dual-write:** changes sync between Lakebase and Lakehouse via BackgroundTasks so both the UI and agents see the same rules. | Lets operators define when to approve, decline, or retry; ML and agents use these rules so every decision is consistent with policy and optimized for approval rate vs risk. |
| **ML models (4)** | HistGradientBoosting with 14 engineered features (temporal, merchant/solution approval rates, network encoding, risk-amount interaction) — trained on `payments_enriched_silver`, registered in Unity Catalog, served via model serving endpoints. `_build_ml_features()` ensures training-inference feature parity. | **Approval propensity:** predicts likelihood of approval. **Risk:** enables risk-based auth. **Routing:** picks the solution maximizing approval for the segment. **Retry:** predicts retry success and timing. |
| **Decisioning API** | Closed-loop endpoints (`/api/decision/authentication`, `/retry`, `/routing`, `/outcome`, `/config`) powered by `DecisionEngine`: parallel ML + VS enrichment (`asyncio.gather`), streaming real-time features (approval_rate_5m, txn_velocity_1m), Lakebase config, rule evaluation, thread-safe caching (`threading.Lock`). Policies use VS approval rates and agent confidence to adjust borderline decisions. POST `/outcome` records actual outcomes. GET `/config` exposes current thresholds. | Single decision layer with continuous improvement; parallel enrichment for production performance; outcome feedback loop ensures the system learns from every decision. Falls back to pure-policy heuristics when Lakebase/ML is unavailable. |
| **Vector Search** | Delta-sync index `similar_transactions_index` on `transaction_summaries_for_search`; similar-case lookup via `VECTOR_SEARCH()` TVF. | Powers "similar cases" recommendations; feeds recommendations into the Decisioning UI and agents to suggest actions that accelerate approvals. |
| **ResponsesAgent + Agent Framework** | **ResponsesAgent** (`payment-response-agent`): MLflow ResponsesAgent with 10 UC tools (5 consolidated + 5 operational) + `python_exec`; primary AI Chat backend. **Agent Framework** (Job 6 fallback): custom Python orchestrator + 5 specialists with write-back tools. 17 individual UC functions + 5 consolidated. 4 ML + 1 agent endpoint. | Answer questions with live data; suggest and write routing, retry, and rule changes; propose config changes that operators review from the UI. |
| **3 unified dashboards** | Data & Quality, ML & Optimization, Executive & Trends in Databricks AI/BI (Lakeview). Embeddable in the app via `/embed/dashboardsv3/` path. | Give visibility into approval rates, decline reasons, solution performance, and recovery; operators see where to act and track impact. |
| **FastAPI + React app** | 16-page control panel with actionable UI: Command Center (top-3 actions, 90% target lines, last-updated), Smart Checkout (contextual guidance), Decisioning (preset scenarios, actionable recommendations with "Create Rule"/"Apply to Context"), Reason Codes (inline expert review: Valid/Invalid/Non-Actionable), Smart Retry (recovery gap analysis). All routes have `ErrorBoundary` wrappers, `Suspense` on root `Outlet` for lazy-loaded routes, auth loading state, error retry fallbacks, and `glass-card` styling. | One place to operate the full stack with every data point telling operators what to do next. |
| **Genie** | Natural-language "Ask Data" in the workspace, synced with sample questions (approval rate, trends, segments). | Extends visibility: ask questions in the lakehouse context, supporting the same goal of accelerating approval rates. |
| **Experiments & incidents** | A/B experiments (e.g. 3DS treatment vs control) and incident/remediation tracking in Lakebase. | Experiments measure impact of policy changes on approval rate; incidents track production issues that might hurt approvals so they can be fixed. |

---

## 5. Payment services context (payment platform)

Payment transactions can use several services (Antifraud, Vault, 3DS, Data Only, Recurrence, Network Token, IdPay, Passkey, Click to Pay). **Smart Checkout**, **Reason Codes**, and **Smart Retry** rely on a shared data foundation: medallion pipelines, gold views, and a single control panel. **Brazil** accounts for most volume; the platform supports catalog/schema and country filters. **Entry systems:** Checkout, PD, WS, SEP; each returns the final response to the merchant. **Smart Retry** covers recurrence and reattempts (e.g. 1M+ such transactions per month in Brazil). **False Insights** is a quality metric (insights marked invalid by specialists) to balance speed vs accuracy.

### Business requirement → Solution

| Business need | Solution |
|---------------|----------|
| Data foundation | Medallion + gold views |
| Unified decline visibility | Reason Codes, decline dashboards, Decline Analyst agent |
| Smart Checkout (Brazil) | Smart Checkout UI, 3DS funnel, Smart Routing |
| Smart Retry | Retry UI, retry analysis, decisioning API |
| Actionable insights | Decisioning API, ResponsesAgent + agent framework, rules engine |
| Feedback loop | Experiments, incidents, rules CRUD, model retraining |
| Single control panel | FastAPI + React app (Setup & Run, Dashboards, Rules, Decisioning, AI Chat) |
| AI-driven intelligence | ResponsesAgent (10 UC tools), Genie |

---

## 6. Map for business users

| Business purpose | Technical solution | What you get (plain language) |
|------------------|--------------------|--------------------------------|
| **One trusted data base for all initiatives** | Medallion pipelines (Bronze → Silver → Gold), gold views, single catalog | Everyone works from the same numbers; Smart Checkout, Reason Codes, and Smart Retry share one clean, up-to-date picture. |
| **See why payments fail and where to act** | Reason Codes, decline dashboards, top-decline and recovery views, Decline Analyst agent | Declines from all channels in one place, with clear reasons and where recovery or routing changes will help most. |
| **Optimize payment-link performance (e.g. Brazil)** | Smart Checkout UI, 3DS funnel, solution performance and routing dashboards, Smart Routing agent | You see how each path performs and how to balance security, friction, and approvals. |
| **Recover more from retries and recurring payments** | Smart Retry UI, retry performance views, Smart Retry agent, decisioning API | You see which failed payments are worth retrying, when and how to retry, and the impact on approval rates. |
| **Get clear next steps, not just reports** | Top-3 actions, contextual guidance, preset scenarios, inline expert review, recovery gap, agent write-back | You get recommended actions with expected impact at every level; agents write recommendations directly to Lakebase. |
| **Learn from what we do and improve over time** | Outcome feedback loop (POST /outcome), experiments, incidents, agent write-back, streaming features | Decision outcomes are recorded; agents propose config changes; the system continuously improves with every decision. |
| **Keep insights reliable** | Inline expert review (Valid/Invalid/Non-Actionable), experiments, False Insights metric | Experts flag bad insights directly from Reason Codes; the system learns from every review. |
| **Focus on the regions that matter (e.g. Brazil)** | Catalog/schema and country filters, geography dashboards | You filter by country or region; Brazil's share of volume is visible by default so local teams see what's relevant. |
| **See performance across all entry channels** | Entry-system distribution analytics, gold views and dashboards | You see how each channel (Checkout, PD, WS, SEP) performs without double-counting or mixing definitions. |
| **Monitor performance in real time and over time** | 3 unified dashboards, real-time views, streaming features | You have KPIs, trends, and reason codes for both live monitoring and historical analysis. |
| **One place to run and control everything** | FastAPI + React app: Setup & Run, Dashboards, Rules, Decisioning, Reason Codes, Smart Checkout, Smart Retry, AI agents | You run jobs, manage rules, view dashboards and recommendations, and operate the full stack from a single control panel. |
| **Ask in plain language and get recommendations** | ResponsesAgent (10 UC tools + python_exec) + Genie | You ask questions in natural language and get data-driven answers and recommendations on routing, retries, declines, risk, and performance. |

---

## 7. Validation: alignment with accelerating approval rates

The solution is designed and documented around a single business objective: **accelerate payment approval rates** and reduce lost revenue from false declines, suboptimal routing, and missed retry opportunities. Each major component is wired to that goal. The implementation of 20+ QA recommendations and end-to-end verification strengthened this alignment:

1. Closed feedback loop with outcome recording
2. ML feature parity between training and inference
3. Parallel enrichment for production performance
4. Streaming real-time features
5. Policies that use VS data and agent confidence for borderline decisions
6. ResponsesAgent with 10 UC tools for data-driven analysis
7. Actionable UI with top-3 actions, target lines, contextual guidance, preset scenarios, inline expert review, and recovery gap analysis
8. Frontend resilience (Suspense, auth loading state, error retry fallbacks)
9. Data integrity (100 merchant dimensions matching the simulator)
10. Pinned dependency versions for reproducible builds

**Testing Status:** ✅ **PRODUCTION-READY** — All components validated and tested. See [Technical Solution — Testing & Validation](TECHNICAL_SOLUTION.md#9-testing--validation) for comprehensive validation results.
