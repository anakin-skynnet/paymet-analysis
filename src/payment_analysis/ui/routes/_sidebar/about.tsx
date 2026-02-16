import { createFileRoute, Link } from "@tanstack/react-router";
import { ErrorBoundary } from "react-error-boundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Database,
  CreditCard,
  ListChecks,
  RotateCcw,
  BarChart3,
  Shield,
  Globe,
  ArrowRight,
  Target,
  TrendingUp,
  Zap,
  Brain,
  Server,
  Activity,
  CheckCircle2,
  DollarSign,
  Bot,
  AlertTriangle,
  Beaker,
  BookOpen,
  Gauge,
  FileBarChart,
  Settings,
} from "lucide-react";

export const Route = createFileRoute("/_sidebar/about")({
  component: () => (
    <ErrorBoundary fallback={<div className="p-8 text-center text-muted-foreground">Something went wrong. Please refresh.</div>}>
      <About />
    </ErrorBoundary>
  ),
});

/* ---------- Data ---------- */

const HERO = {
  headline: "Payment Approval Rate Optimization",
  subline:
    "A unified, AI-powered platform built entirely on Databricks that accelerates payment approval rates, recovers lost revenue from false declines, and optimizes routing and retry strategies across all channels for Getnet. Features a closed-loop DecisionEngine with parallel ML + Vector Search enrichment, streaming features, agent write-back, and a 90% target-line executive dashboard.",
  kpis: [
    { label: "AI Agents", value: "6", detail: "All with write-back tools" },
    { label: "ML Models", value: "4", detail: "HistGradientBoosting + 14 features" },
    { label: "Dashboards", value: "3", detail: "Unified AI/BI Lakeview" },
    { label: "Gold Views", value: "16+", detail: "Including retry-by-reason" },
  ],
};

const CHALLENGE = {
  title: "The Business Challenge",
  intro:
    "Getnet processes millions of payment transactions daily. Every declined transaction that should have been approved is lost revenue. Every suboptimal route increases friction. Every missed retry is a recovery opportunity left on the table.",
  points: [
    {
      icon: DollarSign,
      title: "False declines cost revenue",
      description:
        "Conservative fraud rules and fragmented data lead to legitimate transactions being declined. With millions of monthly transactions, even a 1% improvement in approval rate translates to significant recovered revenue for Getnet and its merchants.",
    },
    {
      icon: Globe,
      title: "Complexity across channels and regions",
      description:
        "Multiple entry systems (Checkout, PD, WS, SEP), multiple services (Antifraud, 3DS, Network Token, IdPay, Passkey), and region-specific behaviors make optimization challenging without unified visibility across all payment flows.",
    },
    {
      icon: RotateCcw,
      title: "Missed retry and recurrence opportunities",
      description:
        "Millions of transactions fail each month that could be successfully retried with the right timing and strategy. Without intelligent retry logic, recoverable revenue is permanently lost.",
    },
    {
      icon: ListChecks,
      title: "Fragmented decline data across systems",
      description:
        "Decline reasons come from different acquirers, networks, and issuers with inconsistent codes. Without standardization and unified taxonomy, it is impossible to see the full picture and prioritize the highest-impact improvements.",
    },
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
      title: "Real-time medallion architecture (Bronze \u2192 Silver \u2192 Gold)",
      description:
        "All payment transaction data flows through Bronze (raw ingestion), Silver (enriched and validated), and Gold (business-ready views and aggregates) layers in under 5 seconds. Continuous serverless Lakeflow pipelines and Delta Live Tables ensure every dashboard, model, and agent sees the same clean, governed, up-to-date data through Unity Catalog.",
      tech: ["Lakeflow", "Delta Live Tables", "Unity Catalog", "Delta Lake", "Serverless SQL"],
    },
    {
      icon: Brain,
      label: "Intelligence Layer",
      title: "4 ML models + 6 AI agents + Vector Search",
      description:
        "Four HistGradientBoosting ML models predict approval probability, fraud risk, optimal routing, and retry success using 14 engineered features (temporal, merchant/solution approval rates, network encoding, risk interactions). All six AI agents (Orchestrator + 5 specialists) have write-back tools to propose recommendations and config changes to Lakebase. Vector Search finds similar historical transactions to inform every decision with experience replay.",
      tech: ["MLflow", "Model Serving", "Responses Agent", "UC Functions", "Vector Search", "Lakebase"],
    },
    {
      icon: Zap,
      label: "Decision Layer",
      title: "Closed-loop decisioning engine with parallel enrichment",
      description:
        "A unified DecisionEngine combines ML predictions, configurable business rules, agent recommendations, Vector Search similarity, and streaming real-time features into a single decision per transaction. ML and Vector Search run in parallel (asyncio.gather) with thread-safe caching. Policies actively use VS approval rates and agent confidence to adjust borderline decisions. Outcomes are recorded via POST /api/decision/outcome closing the feedback loop for continuous improvement.",
      tech: ["FastAPI", "Rules Engine", "Lakebase", "A/B Experiments", "Feedback Loop", "Streaming Features"],
    },
    {
      icon: BarChart3,
      label: "Analytics & Control",
      title: "AI/BI dashboards, Genie, and full-stack control panel",
      description:
        "Three unified AI/BI Lakeview dashboards provide embeddable analytics. The Databricks App control center features a Command Center with top-3 actionable recommendations, 90% target reference lines, and last-updated indicators; Smart Checkout with contextual guidance; Decisioning with preset scenarios and actionable recommendations; Reason Codes with inline expert review buttons; and Smart Retry with recovery gap analysis \u2014 16 pages in total.",
      tech: ["AI/BI Dashboards", "Databricks App", "Genie Space", "React + FastAPI"],
    },
  ],
};

const CAPABILITIES: { icon: typeof Target; title: string; description: string; link: string; linkLabel: string }[] = [
  {
    icon: Target,
    title: "Command Center",
    description: "Real-time KPIs with top-3 actionable recommendations, approval rate trend with 90% target reference line, last-updated indicators, entry system throughput, top decline reasons, and active alerts. The executive view for immediate action.",
    link: "/command-center",
    linkLabel: "Open Command Center",
  },
  {
    icon: ListChecks,
    title: "Reason Codes & Declines",
    description: "Unified decline taxonomy with inline expert review buttons (Valid / Invalid / Non-Actionable) for each insight. Top decline reasons, recoverable segments, decline recovery value, and where routing or rule changes have the highest impact.",
    link: "/reason-codes",
    linkLabel: "View Reason Codes",
  },
  {
    icon: CreditCard,
    title: "Smart Checkout",
    description: "Performance by solution path with contextual 'So What' guidance on every metric (e.g. 'High friction: consider frictionless 3DS flow'). 3DS funnel analysis with threshold-based recommendations to optimize the mix of security services.",
    link: "/smart-checkout",
    linkLabel: "View Smart Checkout",
  },
  {
    icon: RotateCcw,
    title: "Smart Retry",
    description: "Identify which declined transactions are worth retrying with recovery gap analysis per cohort (estimated vs. actually recovered value). New v_retry_success_by_reason gold view provides granular insights by decline reason and retry scenario.",
    link: "/smart-retry",
    linkLabel: "View Smart Retry",
  },
  {
    icon: Shield,
    title: "Decisioning & Rules",
    description: "Closed-loop decisioning with preset scenario buttons, actionable recommendation cards ('Create Rule', 'Apply to Context'), and a config API. DecisionEngine parallelizes ML + Vector Search, reads streaming features, and records outcomes for continuous improvement.",
    link: "/decisioning",
    linkLabel: "Open Decisioning",
  },
  {
    icon: Bot,
    title: "AI Agents",
    description: "Ask questions in natural language. All six agents have write-back tools: Decline Analyst and Risk Assessor can write recommendations and propose config changes to Lakebase. The orchestrator coordinates all specialists with full read+write capability.",
    link: "/ai-agents",
    linkLabel: "Open AI Agents",
  },
  {
    icon: Beaker,
    title: "A/B Experiments",
    description: "Create and manage experiments to measure the impact of policy changes. Statistical analysis (lift, p-value, significance) with automated recommendations to graduate, stop, or extend experiments.",
    link: "/experiments",
    linkLabel: "View Experiments",
  },
  {
    icon: AlertTriangle,
    title: "Incidents & Alerts",
    description: "Track incidents when approval rates drop or anomalies are detected. Create, resolve, and sync incidents to the Lakehouse for historical analysis and audit trail.",
    link: "/incidents",
    linkLabel: "View Incidents",
  },
  {
    icon: Gauge,
    title: "Data Quality & Monitoring",
    description: "Monitor Bronze and Silver data volumes, retention rates, streaming throughput, and pipeline health. Ensure the data foundation is healthy before trusting analytics and decisions.",
    link: "/data-quality",
    linkLabel: "View Data Quality",
  },
  {
    icon: FileBarChart,
    title: "AI/BI Dashboards",
    description: "Three unified Lakeview dashboards published with embed credentials: Executive & Trends, ML & Optimization, and Data & Quality. Real-time views powered by Gold layer views.",
    link: "/dashboards",
    linkLabel: "Open Dashboards",
  },
  {
    icon: BookOpen,
    title: "ML Models & Notebooks",
    description: "View registered ML models in Unity Catalog, their versions, and serving status. Browse and launch Databricks notebooks for ad-hoc analysis, model training, and data exploration.",
    link: "/models",
    linkLabel: "View Models",
  },
  {
    icon: Settings,
    title: "Setup & Administration",
    description: "Run Databricks jobs (data repos, streaming, gold views, model training, agent deployment, Genie sync), manage pipelines, configure the SQL warehouse, and control the full infrastructure lifecycle.",
    link: "/setup",
    linkLabel: "Open Setup",
  },
];

const OUTCOMES: { metric: string; description: string; icon: typeof TrendingUp }[] = [
  {
    metric: "Higher approval rates",
    description: "Reduce false declines using ML-predicted approval probability, risk-based authentication, and experience replay from Vector Search. Every percentage point recovered translates directly to revenue for Getnet merchants.",
    icon: TrendingUp,
  },
  {
    metric: "Recovered revenue from intelligent retries",
    description: "ML-powered retry logic identifies the best candidates, optimal timing, and expected success rate. Transactions that would otherwise be permanently lost are recovered systematically.",
    icon: DollarSign,
  },
  {
    metric: "Optimized routing per transaction segment",
    description: "ML-driven routing selects the best path using 14 engineered features and Vector Search top-route boosting. Policies use VS similar approval rates and agent confidence to adjust borderline decisions, maximizing approval while controlling fraud.",
    icon: Zap,
  },
  {
    metric: "Real-time insight, not stale reports",
    description: "Streaming features (approval_rate_5m, txn_velocity_1m) feed directly into decisions. Top-3 actionable recommendations, 90% target reference lines, contextual guidance on every metric, and inline expert review make every data point actionable.",
    icon: Activity,
  },
  {
    metric: "Closed-loop continuous improvement",
    description: "Outcome recording (POST /api/decision/outcome), agent write-back tools, A/B experiments, and config proposals form a complete feedback loop. Every decision's outcome is recorded and the system learns automatically over time.",
    icon: CheckCircle2,
  },
  {
    metric: "Zero infrastructure overhead",
    description: "100% serverless: compute, SQL, pipelines, model serving, and the application itself. No clusters to size, no jobs to babysit. Databricks Asset Bundles manage the entire stack as code.",
    icon: Server,
  },
];

const TECH_SUMMARY = [
  { label: "Data Platform", value: "Databricks (Lakeflow, Delta Live Tables, Unity Catalog, Delta Lake)" },
  { label: "AI & ML", value: "MLflow, Model Serving (4 endpoints), 14-feature models, Responses Agent, UC Functions, Vector Search" },
  { label: "AI Agents", value: "6 agents with write-back tools (Orchestrator + Routing, Retry, Decline, Risk, Performance)" },
  { label: "Database", value: "Lakebase (managed PostgreSQL) for rules, experiments, incidents, features, proposals, outcomes" },
  { label: "Application", value: "Databricks App: FastAPI backend + React frontend (16 pages, preset scenarios, inline review)" },
  { label: "Dashboards", value: "3 unified AI/BI Lakeview dashboards + 16+ gold views (including v_retry_success_by_reason)" },
  { label: "Decision Engine", value: "Parallel ML + VS enrichment, streaming features, thread-safe caching, outcome feedback loop" },
  { label: "Infrastructure", value: "100% serverless compute \u2014 deployed via Databricks Asset Bundles (IaC)" },
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

      {/* Business Challenge */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">{CHALLENGE.title}</h2>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            {CHALLENGE.intro}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {CHALLENGE.points.map((point) => {
            const Icon = point.icon;
            return (
              <Card key={point.title} className="glass-card border border-destructive/20">
                <CardContent className="flex gap-3 pt-5">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{point.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      {point.description}
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <Separator />

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

      {/* Platform Capabilities */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Platform Capabilities</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Twelve key areas across analytics, optimization, AI, experimentation, and operations &mdash; each designed to help teams find and act on approval rate improvements.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap) => {
            const Icon = cap.icon;
            return (
              <Card key={cap.title} className="glass-card border border-border/80 group card-interactive flex flex-col">
                <CardHeader className="pb-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary mb-2 group-hover:scale-110 transition-transform">
                    <Icon className="h-4 w-4" />
                  </div>
                  <CardTitle className="text-sm">{cap.title}</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col justify-between">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {cap.description}
                  </p>
                  <Link
                    to={cap.link}
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline mt-3"
                  >
                    {cap.linkLabel}
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <Separator />

      {/* Expected Outcomes */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Expected Outcomes</h2>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            How this platform accelerates approval rates and delivers measurable business value.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {OUTCOMES.map((outcome) => {
            const Icon = outcome.icon;
            return (
              <Card key={outcome.metric} className="glass-card border border-green-200/50 dark:border-green-900/30">
                <CardContent className="flex gap-3 pt-5">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-green-900 dark:text-green-300">
                      {outcome.metric}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      {outcome.description}
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <Separator />

      {/* Business Requirement → Solution Map */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">
            Business Requirement to Solution Map
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Each business need is addressed by a specific part of the platform.
          </p>
        </div>
        <Card className="glass-card border border-border/80">
          <CardContent className="pt-5">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="py-2.5 pr-4 font-semibold text-foreground text-xs uppercase tracking-wider">
                      Business Need
                    </th>
                    <th className="py-2.5 pr-4 font-semibold text-foreground text-xs uppercase tracking-wider">
                      Solution
                    </th>
                    <th className="py-2.5 font-semibold text-foreground text-xs uppercase tracking-wider">
                      Impact
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    {
                      need: "Single source of truth for all payment data",
                      solution: "Real-time medallion pipelines (Bronze \u2192 Silver \u2192 Gold) + Unity Catalog governance",
                      impact: "Every team works from the same governed data. Smart Checkout, Reason Codes, Smart Retry, and all dashboards share one clean, up-to-date picture refreshed in under 5 seconds.",
                    },
                    {
                      need: "Understand why payments fail and where to act first",
                      solution: "Unified decline taxonomy + Decline Analyst AI agent + Reason Codes page",
                      impact: "Declines from all entry systems and networks in one place, with standardized reasons, recovery value estimates, and AI-prioritized improvement actions.",
                    },
                    {
                      need: "Optimize payment-link and checkout performance",
                      solution: "Smart Checkout analytics + Smart Routing ML model + 3DS funnel analysis",
                      impact: "See how each path (Antifraud, 3DS, Network Token, Passkey) performs by segment. ML picks the route that maximizes approval while controlling fraud.",
                    },
                    {
                      need: "Recover more revenue from retries and recurrence",
                      solution: "Smart Retry analytics + ML retry model + Retry AI agent",
                      impact: "ML predicts which declines are worth retrying, the optimal timing window, and the expected recovery rate. Tracks both payment recurrence and cardholder reattempts.",
                    },
                    {
                      need: "Get actionable recommendations, not just reports",
                      solution: "6 AI agents with write-back tools + inline expert review + preset decisioning scenarios",
                      impact: "Agents write recommendations and propose config changes directly to Lakebase. Top-3 actions on Command Center, contextual guidance on Smart Checkout, inline review on Reason Codes, and recovery gap on Smart Retry make every insight actionable.",
                    },
                    {
                      need: "Make consistent, explainable decisions at scale",
                      solution: "Closed-loop DecisionEngine with parallel ML + VS + streaming features + outcome recording",
                      impact: "One decision layer for authentication, routing, and retry. Policies use VS approval rates and agent confidence to adjust borderline decisions. POST /outcome closes the feedback loop. Thread-safe caching and parallel enrichment ensure production performance.",
                    },
                    {
                      need: "Measure and validate the impact of every change",
                      solution: "A/B experiments + outcome feedback loop + v_retry_success_by_reason gold view + config API",
                      impact: "Every policy change is measured via control/treatment groups. Decision outcomes are recorded and fed back. New retry-by-reason view enables granular analysis of retry strategies by decline reason and scenario.",
                    },
                    {
                      need: "Monitor data pipeline health and quality",
                      solution: "Data Quality page + streaming TPS monitors + Gold view validation + active alerts",
                      impact: "Teams can verify that Bronze ingestion, Silver enrichment, and Gold aggregates are healthy before trusting any analytics or model predictions.",
                    },
                    {
                      need: "One place to operate and control everything",
                      solution: "Databricks App with 16 pages (Setup, Dashboards, Rules, AI, Decisioning, Experiments, Incidents, Notebooks)",
                      impact: "Teams operate the full stack from a single application. Run jobs, manage rules, chat with AI, view dashboards, and track experiments without switching tools.",
                    },
                  ].map((row, i) => (
                    <tr key={i} className="border-b border-border/50 last:border-0">
                      <td className="py-2.5 pr-4 text-foreground font-medium align-top text-xs">
                        {row.need}
                      </td>
                      <td className="py-2.5 pr-4 text-muted-foreground align-top text-xs">
                        {row.solution}
                      </td>
                      <td className="py-2.5 text-muted-foreground align-top text-xs">
                        {row.impact}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
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

      {/* Quick Navigation */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">Explore the Platform</h2>
        <p className="text-sm text-muted-foreground">
          Navigate to any section of the application. All pages are accessible from the sidebar.
        </p>
        <div className="flex flex-wrap gap-2">
          {[
            { to: "/command-center", label: "Command Center" },
            { to: "/dashboards", label: "AI/BI Dashboards" },
            { to: "/declines", label: "Declines" },
            { to: "/reason-codes", label: "Reason Codes" },
            { to: "/data-quality", label: "Data Quality" },
            { to: "/smart-checkout", label: "Smart Checkout" },
            { to: "/smart-retry", label: "Smart Retry" },
            { to: "/decisioning", label: "Decisioning" },
            { to: "/rules", label: "Rules" },
            { to: "/ai-agents", label: "AI Agents" },
            { to: "/models", label: "ML Models" },
            { to: "/notebooks", label: "Notebooks" },
            { to: "/experiments", label: "Experiments" },
            { to: "/incidents", label: "Incidents" },
            { to: "/setup", label: "Setup & Jobs" },
          ].map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted/50 hover:border-primary/30 transition-all"
            >
              {link.label}
              <ArrowRight className="h-3 w-3" />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
