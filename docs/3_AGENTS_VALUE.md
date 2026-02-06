# 3. AI Agents & Business Value

Seven agents to increase approval rates (e.g. 85% → 90%+).

## Agent Catalog

| # | Agent | Type | Purpose | Impact |
|---|-------|------|---------|--------|
| 1 | Approval Optimizer | Genie | Explore approval data without SQL | ~80% faster insights; 100+ users |
| 2 | Decline Insights | Genie | Understand/reduce declines via NL | +15–25% recovery; automated reports |
| 3 | Approval Propensity Predictor | Model Serving | Real-time approval probability | <50ms p95; ~40% less manual review |
| 4 | Smart Routing Advisor | Model Serving | Recommend solution (3DS, token, etc.) | +2–5% approval; $2–5M/year @ $1B vol |
| 5 | Smart Retry Optimizer | Model Serving | Which declines to retry, when | +15–25% vs random; $1.5–2.5M/year @ $1B |
| 6 | Payment Intelligence Assistant | Mosaic AI Gateway (Llama 3.1) | Explain data, root cause, recommendations | ~90% faster root cause; 10–20 h/week saved |
| 7 | Risk Assessment Advisor | Mosaic AI Gateway (Llama 3.1) | Risk explanation, mitigation | 20–30% fewer false positives |

## Aggregate Impact

| Initiative | Approval lift | Revenue (annual, $1B vol) |
|------------|----------------|---------------------------|
| Smart routing / Retry / False positive reduction / Network token / 3DS | +2–5% / +1–2% / +1–2% / +1–3% / +0.5–1% | **$6.5–13.5M total** |
| Operational | ~80% faster analyst; 100+ Genie; ~20 h/week reporting; ~40% fewer manual reviews | |

**ROI (illustrative):** Cost ~$300K/year; benefit $6.5–13.5M → payback <3 weeks.

## Success Metrics & Security

**Primary:** Approval 90%+; revenue recovery; false positive <2%. **Secondary:** Genie 100+ MAU; query success >85%; model <50ms. **Security:** Unity Catalog; no raw card to LLMs; GDPR consent/explainability; audit logging.

## Accelerating approval rates with Agent Bricks and Mosaic AI

You can use [Agent Bricks](https://www.databricks.com/blog/introducing-agent-bricks), the [Mosaic AI Agent Framework](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/create-agent), and [Mosaic AI product capabilities](https://www.databricks.com/product/artificial-intelligence) to further accelerate approval rates and reduce manual tuning.

| Databricks capability | How it helps approval rates | Use in this solution |
|-----------------------|------------------------------|----------------------|
| **Agent Bricks** (auto-optimized agents) | Declare the task in natural language; automatic evaluation and optimization (prompts, models, retrieval) so agents improve approval-related decisions without endless manual tuning. | Optimize **Smart Retry** (“when to retry”), **Smart Routing** (“which path”), and **Decline Analyst** agents: connect Lakehouse data, define “maximize approval/recovery” and let Agent Bricks build evaluation and tune. |
| **Agent Bricks – structured extraction** | Extract structured data from unstructured text (e.g. decline reasons, merchant feedback, dispute text). | Turn decline narratives, reason-code notes, and merchant feedback into structured signals for rules and ML (better features → better approval/retry decisions). |
| **Agent Learning from Human Feedback (ALHF)** | Natural language guidance (e.g. “ignore retries for code X in region Y”) is translated into technical optimizations (retrieval, prompts, filters). | Let ops/merchant-success give feedback in plain language; improve retry and routing behavior without rewriting code. |
| **Agent Framework + authoring in code** | Build and deploy production agents (LangGraph/LangChain, LlamaIndex, or custom) with MLflow and evaluation. | Extend the existing **agent jobs** (orchestrator, specialist agents in `agents.yml`) with tool-calling or multi-step flows; keep evaluation and deployment in one platform. |
| **Agent Evaluation** | AI judges and human feedback to measure agent output quality; trace issues and redeploy. | Evaluate “approval rate” and “recovery rate” as agent objectives; grade routing/retry recommendations and root-cause answers; iterate with confidence. |
| **AI Playground** | Low-code prototype with LLMs and tools, then export to code. | Quickly prototype a “should we retry?” or “explain this decline” agent, wire to Lakehouse rules and Vector Search, then export for production. |
| **Vector Search** (create manually; see `resources/vector_search.yml`) | Similar-transaction lookup for recommendations. | Agent Bricks or custom agents can use the same index to “find similar approved transactions” and suggest routing/retry; optimize retrieval and prompts for approval quality. |
| **AI Gateway + Model Serving** (already in bundle) | Govern and serve models used by agents. | Keep LLM and ML traffic governed; rate limits and guardrails apply to any new Agent Bricks–backed or custom agents. |

**Practical next steps**

1. **Agent Bricks (beta):** For a focused use case (e.g. “retry decision agent” or “decline reason extraction”), define the task and connect catalog/schema; use automatic evaluation and optimization to improve approval/recovery metrics. See [Introducing Agent Bricks](https://www.databricks.com/blog/introducing-agent-bricks) and product docs.
2. **Evaluate current agents:** Use [Agent Framework and Evaluation](https://www.databricks.com/product/artificial-intelligence) to add evaluation suites for the existing Smart Routing, Smart Retry, and Payment Intelligence agents; tune for approval rate and cost.
3. **ALHF for ops feedback:** When ops or merchants give natural language rules (“don’t retry code 51 after 2 attempts”), feed that into an Agent Bricks– or Agent Framework–based flow so behavior updates without manual prompt/rule edits.

---

**Next:** [5_DEMO_SETUP](5_DEMO_SETUP.md) · [4_TECHNICAL](4_TECHNICAL.md)
