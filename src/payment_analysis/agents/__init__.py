"""Payment Analysis AI Agents.

Multi-agent framework for automated payment approval optimization:
- Smart Routing Agent (routing & cascading)
- Smart Retry Agent (recovery strategies)
- Decline Analyst Agent
- Risk Assessor Agent
- Performance Recommender Agent
- Orchestrator Agent
"""

from .agent_framework import (
    BaseAgent,
    SmartRoutingAgent,
    SmartRetryAgent,
    DeclineAnalystAgent,
    RiskAssessorAgent,
    PerformanceRecommenderAgent,
    OrchestratorAgent,
    setup_agent_framework,
)

# Backward compatibility alias
RoutingOptimizerAgent = SmartRoutingAgent

__all__ = [
    "BaseAgent",
    "SmartRoutingAgent",
    "SmartRetryAgent",
    "DeclineAnalystAgent",
    "RiskAssessorAgent",
    "PerformanceRecommenderAgent",
    "RoutingOptimizerAgent",  # Alias for backward compatibility
    "OrchestratorAgent",
    "setup_agent_framework",
]
