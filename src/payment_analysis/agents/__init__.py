"""Payment Analysis AI Agents.

Architecture:
  - agent.py: ResponsesAgent (MLflow 3.x, OpenAI Responses API) — the primary AI Chat
    backend deployed as "payment-response-agent" Model Serving endpoint. Uses 10 UC tools
    + python_exec for data-driven payment analysis.
  - agent_framework.py: Custom Python multi-agent orchestrator (Job 6 Path 3 fallback).
    Runs specialist agents in parallel: Smart Routing, Smart Retry, Decline Analyst,
    Risk Assessor, Performance Recommender.
  - register_responses_agent.py: Notebook that logs agent.py to MLflow, registers in UC,
    and deploys to payment-response-agent endpoint.

Note: agent_framework is run as a notebook on Databricks (Job 6 task run_agent_framework).
Do not import it from this __init__.py or Databricks raises NotebookImportException.
"""

__all__ = []
