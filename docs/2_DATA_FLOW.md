# 2. Data Flow

Transaction to insight in five stages.

## Overview

```
INGESTION → PROCESSING → INTELLIGENCE → ANALYTICS → APPLICATION
  1000/s    Bronze→Gold   ML + Agents   Dashboards   Web App
                          + Genie       + Genie
```

## Stage 1: Ingestion

Simulator 1,000 events/s → Delta. Schema: transaction_id, amount, merchant, card_network, fraud_score, timestamps. Target: <1s latency.

## Stage 2: Processing (Medallion)

| Layer | Table/View | Purpose |
|-------|------------|---------|
| Bronze | `payments_raw_bronze` | Raw capture, audit |
| Silver | `payments_enriched_silver` | Clean, risk_tier, amount_bucket, composite_risk_score |
| Gold | 12+ views | `v_executive_kpis`, `v_approval_trends_hourly`, `v_top_decline_reasons`, `v_solution_performance`, `v_retry_performance`, etc. |

Target: <5s Bronze → Gold.

## Stage 3: Intelligence

**ML (Unity Catalog):** Approval propensity ~92%, risk scoring ~88%, smart routing ~75%, smart retry ~81%. Flow: Silver → features → MLflow → Registry → Serving. **AI agents:** 7 (Genie, serving, AI Gateway). Target: <50ms serving, <30s agent.

## Stage 4: Analytics

10 AI/BI dashboards (gold views); Genie natural language. Target: >85% query success, 100+ MAU.

## Stage 5: Application

Backend: FastAPI `/api/analytics`, `/api/decisioning`, `/api/notebooks`, `/api/dashboards`, `/api/agents`. Frontend: React (dashboard, dashboards, notebooks, models, ai-agents, decisioning, experiments, declines). Target: <2s page load, <500ms API.

## Example: Approval Rate KPI

Event → Bronze (~1s) → Silver (~3s) → `v_executive_kpis` (~5s) → backend query → UI. End-to-end ~7s.

## Performance Targets

| Metric | Target |
|--------|--------|
| Ingestion / Bronze→Silver / Silver→Gold | <1s / <3s / <2s |
| API query / ML inference / Agent | <2s / <100ms / <30s |

**Stack:** Delta Lake, Unity Catalog, **Lakeflow Declarative Pipelines**, MLflow, Model Serving, AI/BI Dashboards, Genie, AI Gateway, FastAPI, React. See [1_DEPLOYMENTS](1_DEPLOYMENTS.md).
