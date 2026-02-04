# Payment Approval Analysis Platform

A Databricks-native platform for optimizing payment approval rates using real-time analytics, machine learning, and AI agents.

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [Executive Summary](EXECUTIVE_SUMMARY.md) | Business Leaders | Project objectives, ROI, and Databricks capabilities |
| [Technical Documentation](TECHNICAL_DOCUMENTATION.md) | Engineers | Architecture, resources, code structure, best practices |

## Quick Start

```bash
# Install dependencies
uv sync && bun install

# Build the application
uv run apx build

# Deploy to Databricks
databricks bundle deploy --target dev

# View deployed resources
databricks bundle summary
```

## Development

```bash
# Start development servers
uv run apx dev start

# Run type checks
uv run apx dev check

# View logs
uv run apx dev logs -f
```

## Deployed Resources

- **12 Jobs**: AI agents, ML training, stream processing
- **2 DLT Pipelines**: Batch ETL and real-time streaming
- **SQL Warehouse**: Analytics compute
- **Unity Catalog Schema**: Tables, views, and volumes
- **3 Dashboards**: Executive, Decline Analysis, Real-Time Monitoring

## Tech Stack

| Layer | Technology |
|-------|------------|
| Data | Delta Lake, Unity Catalog |
| Streaming | Structured Streaming, Delta Live Tables |
| ML | MLflow, Model Serving |
| AI | LLM Agents (6 specialized) |
| Backend | Python, FastAPI |
| Frontend | React, TypeScript, shadcn/ui |
| Deployment | Databricks Asset Bundles |

---

Built with [APX](https://github.com/databricks-solutions/apx) on Databricks
