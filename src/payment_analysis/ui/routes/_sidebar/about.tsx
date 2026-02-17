import { createFileRoute } from "@tanstack/react-router";
import { ErrorBoundary } from "react-error-boundary";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Database,
  BarChart3,
  Zap,
  Brain,
  TrendingUp,
  Server,
} from "lucide-react";

export const Route = createFileRoute("/_sidebar/about")({
  component: () => (
    <ErrorBoundary
      FallbackComponent={({ resetErrorBoundary }) => (
        <div className="flex flex-col items-center gap-4 p-8 text-center text-muted-foreground">
          <p>Something went wrong loading the About page.</p>
          <button
            onClick={resetErrorBoundary}
            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
          >
            Try again
          </button>
        </div>
      )}
    >
      <About />
    </ErrorBoundary>
  ),
});

/* ---------- Data ---------- */

const HERO = {
  headline: "Payment Approval Rate Optimization",
  subline:
    "A unified, AI-powered platform built entirely on Databricks that accelerates payment approval rates, recovers lost revenue from false declines, and optimizes routing and retry strategies across all channels for Getnet. Features 7 orchestration jobs, 2 Lakeflow pipelines, 5 serving endpoints, a closed-loop DecisionEngine with parallel ML + Vector Search enrichment, streaming features, agent write-back, and real-time executive dashboards.",
  kpis: [
    { label: "AI Agents", value: "8", detail: "1 ResponsesAgent, 2 Genie, 3 Serving, 2 Gateway" },
    { label: "ML Models", value: "4", detail: "Approval, Risk, Routing, Retry" },
    { label: "Dashboards", value: "3", detail: "Unified AI/BI Lakeview (13 pages, 57 widgets)" },
    { label: "Gold Views", value: "26", detail: "Real-time streaming analytics" },
    { label: "Jobs", value: "7", detail: "Orchestration & setup (serverless)" },
    { label: "Pipelines", value: "2", detail: "Continuous Lakeflow (Bronze → Silver → Gold)" },
    { label: "Serving Endpoints", value: "5", detail: "4 ML + 1 Agent (serverless)" },
    { label: "Genie Space", value: "1", detail: "Natural-language payment analytics" },
  ],
};

const SOLUTION_OVERVIEW = {
  title: "What We Built",
  intro:
    "An end-to-end platform on Databricks that unifies data, intelligence, and decision-making into a single control center. Every component is purpose-built around one goal: accelerate payment approval rates for Getnet.",
  layers: [
    {
      icon: Database,
      label: "Data Foundation",
      title: "Lakehouse + Lakebase + Vector Search",
      description:
        "Unity Catalog governs a full medallion architecture (Bronze → Silver → Gold) with 26 gold views. Two continuous Lakeflow pipelines (Pipeline 8: ETL, Pipeline 9: Real-time stream) process payment events in under 5 seconds. Lakebase (managed PostgreSQL) stores operational data — approval rules, experiments, incidents, decision logs, and agent proposals. Vector Search enables similarity lookup for experience replay in the DecisionEngine.",
      tech: ["Unity Catalog", "Delta Lake", "Lakeflow Pipelines (2)", "Lakebase (PostgreSQL)", "Vector Search", "Serverless SQL Warehouse"],
    },
    {
      icon: Brain,
      label: "Intelligence Layer",
      title: "4 ML models + 8 AI agents + Genie Space",
      description:
        "Four HistGradientBoosting ML models (14 engineered features each) serve approval probability, fraud risk, optimal routing, and retry success predictions via 4 Model Serving endpoints. The ResponsesAgent (payment-response-agent) provides AI-powered recommendations through 10 Unity Catalog tools and python_exec. Two AI Gateway endpoints (Claude Opus 4.6 for orchestration, Sonnet 4.5 for specialists) and a Genie Space enable natural-language payment analytics over gold views.",
      tech: ["MLflow", "4 Model Serving Endpoints", "ResponsesAgent", "10 UC Functions", "Vector Search", "Genie Space", "AI Gateway"],
    },
    {
      icon: Zap,
      label: "Decision Layer",
      title: "Closed-loop decisioning engine with parallel enrichment",
      description:
        "A unified DecisionEngine combines ML predictions, configurable business rules, agent recommendations, Vector Search similarity, and streaming real-time features into a single decision per transaction. ML and Vector Search run in parallel with thread-safe caching. Outcomes are recorded via POST /api/decision/outcome, closing the feedback loop. Rules, experiments, and incidents are managed via the Lakebase-backed CRUD UI.",
      tech: ["FastAPI", "Rules Engine", "Lakebase CRUD", "A/B Experiments", "Feedback Loop", "Streaming Features"],
    },
    {
      icon: BarChart3,
      label: "Analytics & Control",
      title: "3 AI/BI dashboards (57 widgets) + full-stack Databricks App",
      description:
        "Three unified AI/BI Lakeview dashboards with 13 pages and 57 widgets (counters, bars, lines, tables, choropleths, heatmaps, pies) covering Executive & Trends, ML & Optimization, and Data & Quality. The Databricks App control center features Command Center KPIs, Smart Checkout, Decisioning, Reason Codes, Smart Retry, Models, Notebooks, and two floating AI chat dialogs (Orchestrator Agent + Genie Assistant).",
      tech: ["3 AI/BI Dashboards (13 pages)", "Databricks App", "Genie Assistant", "AI Chat", "React + FastAPI"],
    },
  ],
};

const BUSINESS_IMPACT = {
  title: "Business Impact for Getnet",
  items: [
    { metric: "Approval Rate Uplift", description: "ML-powered smart routing and retry strategies optimize every transaction path, directly increasing approval rates across all channels and payment solutions." },
    { metric: "False Decline Recovery", description: "Reason code analysis, recoverable decline detection (74%+ recoverable rate), and automated retry reduce revenue lost to unnecessary declines." },
    { metric: "Real-time Fraud Detection", description: "Streaming fraud scoring with sub-second latency flags high-risk transactions before authorization, protecting merchants and issuers without blocking legitimate payments." },
    { metric: "Operational Efficiency", description: "Automated decisioning replaces manual review queues. AI agents provide actionable recommendations, and A/B experiments measure rule impact before rollout." },
    { metric: "Executive Visibility", description: "Real-time dashboards with 57 widgets across 13 pages give executives, analysts, and operations teams instant insight into approval rates, decline patterns, and optimization opportunities." },
  ],
};

const RESOURCE_INVENTORY = {
  title: "Databricks Resources Inventory",
  groups: [
    {
      category: "Orchestration Jobs (7)",
      icon: Server,
      items: [
        "Job 1: Create Data Repositories (Lakehouse, Vector Search, Lakebase)",
        "Job 2: Simulate Transaction Events (1000 events/sec producer)",
        "Job 3: Initialize Ingestion (lakehouse, Lakebase, Vector Search)",
        "Job 4: Deploy Dashboards (prepare, publish 3 unified dashboards)",
        "Job 5: Train Models (4 ML models → Model Serving)",
        "Job 6: Deploy Agents (ResponsesAgent + Agent Framework)",
        "Job 7: Genie Space Sync (config + sample questions)",
      ],
    },
    {
      category: "Lakeflow Pipelines (2)",
      icon: Database,
      items: [
        "Pipeline 8: Payment Analysis ETL (Bronze → Silver → Gold, continuous)",
        "Pipeline 9: Real-time Stream Processor (sub-second latency)",
      ],
    },
    {
      category: "Model Serving (5 endpoints)",
      icon: Brain,
      items: [
        "approval-propensity — Predicts transaction approval likelihood",
        "risk-scoring — Fraud and risk assessment scoring",
        "smart-routing — Optimal payment solution routing",
        "smart-retry — Retry success probability for soft declines",
        "payment-response-agent — ResponsesAgent with 10 UC tools + python_exec",
      ],
    },
    {
      category: "AI & Analytics",
      icon: Brain,
      items: [
        "AI Gateway: Claude Opus 4.6 (orchestrator) + Sonnet 4.5 (specialists/Genie)",
        "Genie Space: Payment Analytics — natural-language queries over gold views",
        "Vector Search: Similar transaction lookup for experience replay",
        "Unity Catalog Functions: 10 agent tools (read/write Lakebase, query gold views)",
      ],
    },
    {
      category: "Data Infrastructure",
      icon: Database,
      items: [
        "Unity Catalog: ahs_demos_catalog.payment_analysis (26 gold views, 3 layers)",
        "SQL Warehouse: Serverless, payment-optimized query engine",
        "Lakebase: Managed PostgreSQL (rules, experiments, incidents, decisions, proposals)",
        "Delta Lake: ACID tables with streaming + batch in medallion architecture",
      ],
    },
    {
      category: "Dashboards & App",
      icon: BarChart3,
      items: [
        "Executive & Trends: 19 widgets — KPIs, approval trends, geography, merchant performance",
        "ML & Optimization: 24 widgets — routing, declines, fraud, 3DS, financial impact",
        "Data & Quality: 14 widgets — streaming metrics, real-time monitoring, data quality",
        "Databricks App: React + FastAPI control center with 2 AI chat dialogs",
      ],
    },
  ],
};

const TECH_SUMMARY = [
  { label: "Data Platform", value: "Databricks (Unity Catalog, Delta Lake, 2 Lakeflow Pipelines, Serverless SQL)" },
  { label: "AI & ML", value: "MLflow, 4 Model Serving endpoints, 14-feature HistGradientBoosting, Vector Search" },
  { label: "AI Agents", value: "8 agents — 1 ResponsesAgent (10 UC tools), 2 Genie, 3 Serving, 2 AI Gateway" },
  { label: "LLM Strategy", value: "Claude Opus 4.6 (orchestrator / fallback) + Claude Sonnet 4.5 (Genie / specialists)" },
  { label: "Lakebase", value: "Managed PostgreSQL — approval rules, experiments, incidents, decision logs, proposals" },
  { label: "Application", value: "Databricks App: FastAPI backend + React frontend + 2 floating AI chat dialogs" },
  { label: "Dashboards", value: "3 unified AI/BI Lakeview dashboards (13 pages, 57 widgets) + 26 gold views" },
  { label: "Decision Engine", value: "Parallel ML + VS enrichment, streaming features, thread-safe caching, outcome feedback" },
  { label: "Jobs & Pipelines", value: "7 serverless orchestration jobs + 2 continuous Lakeflow pipelines" },
  { label: "Infrastructure", value: "100% serverless compute — deployed via Databricks Asset Bundles (IaC)" },
];

/* ---------- Component ---------- */

function About() {
  return (
    <div className="space-y-8 max-w-5xl">
      {/* Hero */}
      <section className="rounded-xl bg-gradient-to-br from-primary/90 to-primary px-6 py-8 text-primary-foreground">
        <Badge variant="secondary" className="mb-3 bg-white/20 text-white border-white/30 hover:bg-white/30">
          Getnet Payment Analytics
        </Badge>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
          {HERO.headline}
        </h1>
        <p className="mt-3 text-sm md:text-base opacity-90 max-w-3xl leading-relaxed">
          {HERO.subline}
        </p>
        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          {HERO.kpis.map((kpi) => (
            <div
              key={kpi.label}
              className="rounded-lg bg-white/10 backdrop-blur-sm px-4 py-3 text-center border border-white/10"
            >
              <p className="text-2xl md:text-3xl font-bold">{kpi.value}</p>
              <p className="text-xs font-medium mt-0.5 opacity-90">{kpi.label}</p>
              <p className="text-[10px] opacity-70 mt-0.5">{kpi.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Solution Overview */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">{SOLUTION_OVERVIEW.title}</h2>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            {SOLUTION_OVERVIEW.intro}
          </p>
        </div>
        <div className="space-y-3">
          {SOLUTION_OVERVIEW.layers.map((layer, i) => {
            const Icon = layer.icon;
            return (
              <Card key={layer.label} className="glass-card border border-border/80 overflow-hidden">
                <CardContent className="flex gap-4 pt-5">
                  <div className="flex flex-col items-center gap-1 pt-0.5">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-sm">
                      {i + 1}
                    </div>
                    {i < SOLUTION_OVERVIEW.layers.length - 1 && (
                      <div className="w-px flex-1 bg-border" />
                    )}
                  </div>
                  <div className="flex-1 pb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className="text-xs gap-1">
                        <Icon className="h-3 w-3" />
                        {layer.label}
                      </Badge>
                    </div>
                    <p className="text-sm font-semibold mt-2">{layer.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed max-w-2xl">
                      {layer.description}
                    </p>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {layer.tech.map((t) => (
                        <Badge key={t} variant="secondary" className="text-[10px] font-normal">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <Separator />

      {/* Business Impact */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          {BUSINESS_IMPACT.title}
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {BUSINESS_IMPACT.items.map((item) => (
            <Card key={item.metric} className="glass-card border border-border/80">
              <CardContent className="pt-5">
                <p className="text-sm font-semibold text-primary">{item.metric}</p>
                <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{item.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <Separator />

      {/* Resource Inventory */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">{RESOURCE_INVENTORY.title}</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {RESOURCE_INVENTORY.groups.map((group) => {
            const Icon = group.icon;
            return (
              <Card key={group.category} className="glass-card border border-border/80">
                <CardContent className="pt-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className="h-4 w-4 text-primary" />
                    <p className="text-sm font-semibold">{group.category}</p>
                  </div>
                  <ul className="space-y-1.5">
                    {group.items.map((item) => (
                      <li key={item} className="text-xs text-muted-foreground leading-relaxed flex gap-1.5">
                        <span className="text-primary/60 mt-0.5 shrink-0">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <Separator />

      {/* Technology Summary */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">Technology at a Glance</h2>
        <Card className="glass-card border border-border/80">
          <CardContent className="pt-5">
            <div className="grid gap-3 sm:grid-cols-2">
              {TECH_SUMMARY.map((item) => (
                <div key={item.label} className="flex gap-2">
                  <span className="text-xs font-semibold text-foreground whitespace-nowrap min-w-[120px]">
                    {item.label}
                  </span>
                  <span className="text-xs text-muted-foreground">{item.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
