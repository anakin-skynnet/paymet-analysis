# Payment Approval Optimization Platform

A Databricks-powered solution that maximizes payment approval rates through real-time analytics, machine learning, and AI-driven recommendations.

---

## Documentation

**📚 [Full Documentation Index](docs/README.md)** — Complete documentation hub with role-based navigation

| Document | Audience | Description |
|----------|----------|-------------|
| [0. Executive Overview](docs/0_EXECUTIVE_OVERVIEW.md) | **C-Suite / Business** | Business challenge, solution, platform capabilities, ROI, and implementation |
| [1. Deployment Guide](docs/1_DEPLOYMENT_GUIDE.md) | **DevOps / Engineering** | **Step-by-step deployment instructions** (START HERE) |
| [2. Data Flow Summary](docs/2_DATA_FLOW_SUMMARY.md) | **Data Engineers** | 5-stage data flow from ingestion to insight with lineage |
| [3. AI Agents Guide](docs/3_AI_AGENTS_GUIDE.md) | **ML Engineers / Data Scientists** | 7 Databricks AI agents with capabilities and deployment |
| [4. Technical Details](docs/4_TECHNICAL_DETAILS.md) | **Software Engineers / Architects** | Architecture, implementation, security, monitoring, and troubleshooting |

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
