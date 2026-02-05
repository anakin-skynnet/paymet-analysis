# Payment Approval Optimization Platform

A Databricks-powered solution that maximizes payment approval rates through real-time analytics, machine learning, and AI-driven recommendations.

---

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [🚀 Deployment Guide](docs/DEPLOYMENT_GUIDE.md) | **All** | **Step-by-step deployment instructions** (START HERE) |
| [Executive Summary](docs/EXECUTIVE_SUMMARY.md) | CEO / Business | Project objectives, business value, and Databricks technology overview |
| [AI Agents Guide](docs/AI_AGENTS_GUIDE.md) | Product / Engineering | 7 AI agents for approval rate optimization with ROI analysis |
| [Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md) | Engineers | Architecture, resource definitions, deployment, and best practices |
| [Data Flow](docs/DATA_FLOW.md) | All | End-to-end journey from transaction ingestion to user-facing insights |
| [UI/UX Validation](docs/UI_UX_VALIDATION.md) | Engineering | Complete component-to-notebook mapping and validation report |

---

## Quick Start

```bash
# Install dependencies
uv sync && bun install

# Validate bundle
databricks bundle validate

# Deploy to development
databricks bundle deploy --target dev

# Run locally
uv run apx dev
```

---

## Architecture

```
Transactions ──▶ DLT Pipeline ──▶ ML Models ──▶ AI Agents ──▶ Web App
                      │                             │
                      ▼                             ▼
                 Gold Views ──────────────▶ Dashboards & Genie
```

---

## Key Features

- **Real-Time Processing**: 1000+ transactions/second with sub-second latency
- **Smart Routing**: ML-driven processor selection
- **Smart Retry**: Automated recovery for soft declines
- **AI Agents**: 7 specialized agents (Genie, Model Serving, AI Gateway) for continuous optimization
- **Self-Service Analytics**: Dashboards + natural language queries (Genie)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Data | Delta Lake, Unity Catalog, DLT |
| ML | MLflow, Model Serving |
| AI | Databricks Agents, Llama 3.1 |
| Backend | FastAPI, SQLModel |
| Frontend | React, Vite, TanStack Router |
| Deploy | Databricks Asset Bundles |
