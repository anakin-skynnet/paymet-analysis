# Business Overview & Impact on Approval Rates

Single entry point for **what** the platform does and **how** it accelerates approval rates using Databricks technologies.

---

## Business purpose

**Primary goal:** Accelerate payment approval rates and reduce lost revenue from:

- **False declines** — Good transactions rejected by overly conservative rules or lack of context.
- **Suboptimal routing** — Sending traffic to solutions or networks that underperform for a given context.
- **Missed retry opportunities** — Not retrying soft-declined or transient failures when it is safe and valuable to do so.

**Approach:** Use real-time ML, rules, AI agents, and unified analytics so every decision (auth, retry, routing) is data-driven and consistent with business policy.

---

## Use cases and impact on approval rates

| Use case | What it does | Impact on accelerating approval rates |
|----------|----------------|---------------------------------------|
| **Smart Retry** | Retry logic, timing, and cohorts; ML retry model; similar-case recommendations | Surfaces recoverable declines and recommends when/how to retry; reduces revenue left on the table from one-time failures. |
| **Smart Checkout** | 3DS funnel, service-path performance, Brazil payment links, antifraud attribution | Balances friction vs risk; optimizes auth and routing so more good transactions approve without unnecessary step-up. |
| **Reason codes & declines** | Unified decline taxonomy, recovery opportunities, factors delaying approval | Identifies top decline reasons and recoverable share; guides rule and process changes to turn declines into approvals. |
| **Risk & fraud** | Risk tier, fraud score, risk signals, Risk Assessor agent | Enables risk-based auth and routing; avoids over-challenging low-risk users and focuses step-up where it matters. |
| **Routing optimization** | Routing performance, Smart Routing agent, model serving | Routes transactions to the best-performing solution/network for context, improving approval rates and latency. |
| **Decisioning** | Real-time auth, retry, and routing decisions via API; rules + ML + Vector Search | Unifies all signals (rules, ML, similar cases) into one decision layer; consistent policy and fewer arbitrary declines. |

---

## Technology map: how these technologies help

| Technology | Role | How it accelerates approval rates |
|------------|------|-----------------------------------|
| **Lakeflow (Bronze → Silver → Gold)** | Reliable, scalable ingestion and transforms | Clean, timely data for ML and analytics; fewer bad decisions from stale or missing data. |
| **Unity Catalog** | Tables, governance, gold views | Single source of truth for KPIs, reason codes, and model inputs; consistent metrics and rules. |
| **ML models** (approval propensity, risk, routing, retry) | Real-time scores per transaction | Decisions based on predicted approval likelihood and risk instead of static rules only; better approve/retry/routing choices. |
| **Rules engine** (Lakebase/Lakehouse) | Configurable business rules | Operators tune approve/decline/retry without code; fast iteration to reduce false declines. |
| **Vector Search** | Similar-transaction lookup | “Similar cases” recommendations for retry and routing; learn from past outcomes. |
| **7 AI agents** (Orchestrator, Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender, Genie) | Natural-language analytics and recommendations | Explains patterns and suggests actions (e.g. retry policy, routing changes) that directly improve approval rates. |
| **12 dashboards** | KPIs, funnels, reason codes, retry performance | Visibility into what drives approvals/declines; data-driven tuning of rules and models. |
| **FastAPI + React app** | Decision API and control panel | Single place to run jobs, view dashboards, manage rules, and call the decision API; reduces operational friction. |

---

## High-level flow

**Data:** Simulator or real pipelines → Lakeflow (Bronze → Silver → Gold) → Unity Catalog.  
**Intelligence:** ML models + rules + Vector Search + AI agents.  
**Application:** FastAPI backend (decision API, analytics, dashboards, agents) + React UI (Setup & Run, dashboards, rules, decisioning).

For technical architecture, project structure, and deployment, see [Technical guide](TECHNICAL_GUIDE.md). For deploy steps and troubleshooting, see [Deployment guide](DEPLOYMENT_GUIDE.md).
