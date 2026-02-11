# Payment Services Context & Solution Map

This document consolidates **business context** (Getnet payment services, initiatives, data foundation) and a **requirement → solution map** for the Payment Analysis platform. For architecture and deploy steps see [GUIDE.md](GUIDE.md) and [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Payment services context

In the e‑commerce context, a payment transaction can leverage several complementary services, provided by Getnet or by third parties. These services aim to increase security, improve user experience, and/or positively impact approval rates. Some of the main services are:

- **Antifraud** — Risk and fraud detection
- **Vault** — Tokenization and secure storage
- **3DS** — Strong customer authentication (e.g. mandatory for debit in Brazil)
- **Data Only** — Data-driven decisions without extra friction
- **Recurrence** — Recurring/subscription payments
- **Network Token** — Card network tokenization (e.g. mandatory for VISA at Getnet)
- **IdPay (Único)** — Biometric recognition
- **Passkey** — Passwordless authentication (under development at Getnet)
- **Click to Pay** — Streamlined checkout

---

## Data foundation for the initiatives

The three initiatives — **Smart Checkout**, **Reason Codes**, and **Smart Retry** — all rely on data mapping, data treatment, and data quality to generate relevant and actionable insights. Without a strong and well-aligned data foundation, the value extracted from these use cases will be limited.

This solution provides that foundation: medallion (Bronze → Silver → Gold) pipelines, gold views, and a single control panel so all initiatives consume the same clean, timely data.

---

## Geographic distribution

From a geographic perspective, **Brazil accounts for more than 70%** of Getnet’s total transaction volume. Most concrete data points and early initiatives are therefore Brazil‑focused. The platform supports catalog/schema and entity filters so you can focus on Brazil or other regions.

---

## Smart Checkout – Current view

The first phase of Smart Checkout is designed for **payment link transactions**, with an initial focus on Brazil:

- ~ 5 million transactions per year  
- ~ 73% overall approval rate  
- Indicators vary significantly by seller profile  

**Breakdown by service (Payment Link – Brazil):**

| Service | Notes |
|--------|--------|
| **Antifraud** | Accounts for ~40–50% of all declined transactions. |
| **3DS** | Mandatory for debit in Brazil; debit volume &lt;100k tx/year. In a 2025 controlled test: ~80% of transactions routed to 3DS experienced friction; 60% sent to 3DS were successfully authenticated; 80% of authenticated were approved by issuer. |
| **IdPay (Único)** | Not yet live in production. Provider reports biometric success between 60–80%. |
| **Data Only** | No concrete data yet on approval rate uplift. |
| **Network Token** | Mandatory for VISA; currently VISA and Mastercard at Getnet. |
| **Passkey** | Under development at Getnet; no production data yet. |

---

## Reason Codes – Current view and data scope

Reason Codes is developed with a **Brazil‑focused** scope and requires visibility over the **full set of e‑commerce transactions** to identify decline reasons across the entire approval chain.

**Transaction coverage and entry points**

Four entry systems act as gates for merchant transactions:

- **Checkout** — Checkout BR
- **PD (Digital Platform)**
- **WS (WebService)**
- **SEP (Single Entry Point)**

Each channel returns the final response to the merchant. Example flows:

- Payment Link: Checkout BR → PD → WS → Base24 → Issuer  
- Recurring: PD → WS → Base24 → Issuer  
- Legacy: WS → Base24 → Issuer  
- Payment Link via SEP: Checkout Global → SEP → Payments Core → Base24 → Issuer  

**Transaction distribution by entry channel (Brazil – monthly):** PD ~62%, WS ~34%, SEP ~3%, Checkout ~1%.

**Expected outcome:** A data- and AI-driven intelligence layer that:

1. Consolidates declines across flows and systems visible to Getnet  
2. Standardizes decline reasons into a single taxonomy  
3. Identifies approval rate degradation patterns and root causes  
4. Translates patterns into actionable insights (recommended actions, estimated uplift)  
5. Enables a feedback loop (executed actions and results) to improve model and insight quality  

This supports not only descriptive/diagnostic analytics but also **prescriptive and learning-based** decision making.

---

## Counter metrics – Insight quality control

To ensure quality and reliability of insights:

**False Insights (quality metric)**  
- **Metric:** Percentage of insights marked invalid or non‑actionable by domain specialists after review.  
- Balances speed vs. accuracy in early phases and keeps expert validation in the learning loop.

---

## Smart Retry – Initial context

Smart Retry has two recurrence‑related scenarios:

1. **Payment Recurrence** — Scheduled or subscription-based (e.g. monthly charges).  
2. **Payment Retry (Reattempts)** — Cardholder retries after a decline (same card, amount, merchant).  

In Brazil, **more than 1 million transactions per month** fall under one of these scenarios. The platform surfaces recoverable declines and recommends when and how to retry.

---

## Business requirement → Solution → Description

| Business requirement | Solution in this platform | Brief description |
|----------------------|---------------------------|--------------------|
| **Data foundation for all initiatives** | Medallion pipelines (Bronze → Silver → Gold), gold views, Unity Catalog | Single source of truth; clean, timely data for Smart Checkout, Reason Codes, Smart Retry, and analytics. |
| **Unified decline visibility & reason codes** | Reason Codes initiative, decline dashboards, top decline reasons & recovery opportunities views, Decline Analyst agent | Consolidate declines; standardize reason codes; identify top decline reasons and recoverable value; AI recommendations. |
| **Smart Checkout (payment link, Brazil)** | Smart Checkout UI, 3DS funnel, solution performance, routing dashboards, Smart Routing agent | Visibility into approval rates by solution; 3DS funnel and routing performance; optimize service mix (Antifraud, 3DS, Network Token, etc.). |
| **Smart Retry (recurrence & reattempts)** | Smart Retry UI, retry performance view, Smart Retry agent, decisioning API | Surface recoverable declines; recommend retry timing and strategy; 1M+ recurrence/retry tx/month in scope. |
| **Actionable insights & recommendations** | Decisioning API, Recommendations UI, orchestrator + 5 AI agents, rules engine | Prescriptive insights; recommended actions and estimated uplift; rules + ML + agents in one decision layer. |
| **Feedback loop (actions & results)** | Experiments, incidents, rules CRUD, model retraining (jobs) | Capture executed actions and outcomes; A/B experiments; continuous improvement of models and insights. |
| **Insight quality control** | Experiments, domain validation workflow, False Insights metric (concept) | Track validity of insights; balance speed vs. accuracy; expert review in the loop. |
| **Geographic focus (e.g. Brazil)** | Catalog/schema, entity/country filters, geography dashboards, choropleth views | Filter by country/region; Brazil ~70% volume; dashboards and KPIs by geography. |
| **Multi-entry visibility (Checkout, PD, WS, SEP)** | Entry-system distribution analytics, gold views and dashboards | Visibility by entry channel; support consolidation without double-counting. |
| **Real-time & historical analytics** | 12 dashboards (executive, trends, declines, routing, retry, risk, etc.), real-time by-second views | KPIs, trends, reason codes, solution performance; real-time and historical. |
| **Single control panel** | FastAPI + React app: Setup & Run, Dashboards, Rules, Decisioning, Reason Codes, Smart Checkout, Smart Retry, AI agents | One place to run jobs, manage rules, view recommendations and dashboards, and operate the stack. |
| **AI-driven intelligence** | 7 AI agents (orchestrator, Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender), Genie | Natural-language analytics; routing/retry/decline recommendations; learning-based decision support. |

---

## Where to read more

| Topic | Document |
|--------|----------|
| Architecture, use cases, technology map | [GUIDE.md](GUIDE.md) |
| Deploy, env, troubleshooting | [DEPLOYMENT.md](DEPLOYMENT.md) |
| All docs index | [INDEX.md](INDEX.md) |
| Agent framework (Job 6, AgentBricks) | [DATABRICKS.md Part 3](DATABRICKS.md#part-3--agent-framework-agentbricks) |
