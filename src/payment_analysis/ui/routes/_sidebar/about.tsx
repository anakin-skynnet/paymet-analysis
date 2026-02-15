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
    "A unified, AI-powered platform that accelerates payment approval rates, recovers lost revenue from false declines, and optimizes routing and retry strategies across all channels.",
  kpis: [
    { label: "AI Agents", value: "7", detail: "Orchestrator + 5 specialists" },
    { label: "ML Models", value: "7", detail: "Real-time serving endpoints" },
    { label: "Dashboards", value: "3", detail: "Unified AI/BI analytics" },
    { label: "Compute", value: "100%", detail: "Serverless infrastructure" },
  ],
};

const CHALLENGE = {
  title: "The Business Challenge",
  intro:
    "Every declined transaction that should have been approved is lost revenue. Every suboptimal route increases friction. Every missed retry is a recovery opportunity left on the table.",
  points: [
    {
      icon: DollarSign,
      title: "False declines cost revenue",
      description:
        "Conservative fraud rules and fragmented data lead to legitimate transactions being declined. With millions of monthly transactions, even a 1% improvement in approval rate translates to significant recovered revenue.",
    },
    {
      icon: Globe,
      title: "Complexity across channels and regions",
      description:
        "Multiple entry systems (Checkout, PD, WS, SEP), multiple services (Antifraud, 3DS, Network Token, IdPay, Passkey), and region-specific behaviors (Brazil accounts for over 70% of volume) make optimization challenging without unified visibility.",
    },
    {
      icon: RotateCcw,
      title: "Missed retry and recurrence opportunities",
      description:
        "Millions of transactions fail each month that could be successfully retried. Without intelligent retry logic and timing, recoverable revenue is left on the table.",
    },
    {
      icon: ListChecks,
      title: "Fragmented decline data",
      description:
        "Decline reasons come from different systems with different codes. Without standardization, it is impossible to see the full picture and prioritize the highest-impact improvements.",
    },
  ],
};

const SOLUTION_OVERVIEW = {
  title: "What We Built",
  intro:
    "An end-to-end platform on Databricks that unifies data, intelligence, and decision-making into a single control center. Every component is designed around one goal: accelerate approval rates.",
  layers: [
    {
      icon: Database,
      label: "Data Foundation",
      title: "Real-time medallion architecture",
      description:
        "All payment data flows through Bronze, Silver, and Gold layers in under 5 seconds. Continuous serverless pipelines ensure every dashboard, model, and agent sees the same clean, up-to-date data.",
      tech: ["Lakeflow", "Unity Catalog", "Delta Lake", "Serverless"],
    },
    {
      icon: Brain,
      label: "Intelligence Layer",
      title: "ML models + AI agents + Vector Search",
      description:
        "Four ML models predict approval probability, fraud risk, optimal routing, and retry success in real time. Seven AI agents analyze patterns and recommend actions. Vector Search finds similar historical transactions to inform decisions.",
      tech: ["MLflow", "Model Serving", "LangGraph", "Vector Search", "Lakebase"],
    },
    {
      icon: Zap,
      label: "Decision Layer",
      title: "Real-time decisioning API",
      description:
        "A unified API combines ML scores, business rules, and AI recommendations into a single decision for each transaction: authenticate, route, retry, or escalate. Rules can be adjusted without code.",
      tech: ["FastAPI", "Rules Engine", "Lakebase", "A/B Experiments"],
    },
    {
      icon: BarChart3,
      label: "Analytics & Control",
      title: "Dashboards, agents, and control panel",
      description:
        "Three unified AI/BI dashboards provide executive KPIs, ML performance metrics, and data quality monitoring. The control panel lets teams run jobs, manage rules, view recommendations, and interact with AI agents, all from one place.",
      tech: ["AI/BI Dashboards", "React App", "Genie", "Orchestrator Chat"],
    },
  ],
};

const CAPABILITIES: { icon: typeof Target; title: string; description: string; link: string; linkLabel: string }[] = [
  {
    icon: Target,
    title: "Command Center",
    description: "Real-time KPIs, approval rates, entry system throughput, top declines, alerts, and AI recommendations. The executive view of platform health.",
    link: "/command-center",
    linkLabel: "Open Command Center",
  },
  {
    icon: ListChecks,
    title: "Reason Codes & Declines",
    description: "Unified decline taxonomy across all entry systems. See top reasons, recoverable segments, and where routing or rule changes have the highest impact.",
    link: "/declines",
    linkLabel: "View Declines",
  },
  {
    icon: CreditCard,
    title: "Smart Checkout",
    description: "Performance by solution path (Antifraud, 3DS, Network Token, Passkey). 3DS funnel analysis. Optimize the mix of security services to maximize approval with minimum friction.",
    link: "/smart-checkout",
    linkLabel: "View Smart Checkout",
  },
  {
    icon: RotateCcw,
    title: "Smart Retry",
    description: "Identify which declined transactions are worth retrying, when to retry, and the expected recovery. Covers both payment recurrence and cardholder reattempts.",
    link: "/smart-retry",
    linkLabel: "View Smart Retry",
  },
  {
    icon: Shield,
    title: "Decisioning & Rules",
    description: "Real-time authentication, routing, and retry decisions combining ML predictions, business rules, and risk scores. Rules are configurable without code. A/B experiments measure impact.",
    link: "/decisioning",
    linkLabel: "Open Decisioning",
  },
  {
    icon: Bot,
    title: "AI Agents",
    description: "Ask questions in natural language. The orchestrator coordinates five specialist agents (Routing, Retry, Decline, Risk, Performance) that analyze data and recommend specific actions.",
    link: "/ai-agents",
    linkLabel: "Open AI Agents",
  },
];

const OUTCOMES: { metric: string; description: string; icon: typeof TrendingUp }[] = [
  {
    metric: "Higher approval rates",
    description: "Reduce false declines by using ML-predicted approval probability and risk-based authentication. Every percentage point recovered translates to significant revenue.",
    icon: TrendingUp,
  },
  {
    metric: "Recovered revenue from retries",
    description: "Intelligent retry timing and targeting recovers transactions that would otherwise be lost. The platform identifies the best candidates, optimal timing, and expected success rate.",
    icon: DollarSign,
  },
  {
    metric: "Optimized routing decisions",
    description: "ML-driven routing selects the best path (standard, 3DS, Network Token, Passkey) for each transaction segment, maximizing approval while controlling fraud exposure.",
    icon: Zap,
  },
  {
    metric: "Faster time to insight",
    description: "Real-time data processing (under 5 seconds) and AI agents replace manual analysis. Teams get actionable recommendations instead of raw reports.",
    icon: Activity,
  },
  {
    metric: "Consistent, data-driven decisions",
    description: "One decision layer, one set of rules, one source of truth. No more conflicting signals from different systems or teams operating on different data.",
    icon: CheckCircle2,
  },
  {
    metric: "Reduced operational overhead",
    description: "Fully serverless, self-managing infrastructure. No clusters to size, no jobs to babysit. Teams focus on business logic and strategy, not operations.",
    icon: Server,
  },
];

const TECH_SUMMARY = [
  { label: "Data Platform", value: "Databricks (Lakeflow, Unity Catalog, Delta Lake)" },
  { label: "AI & ML", value: "MLflow, Model Serving, LangGraph agents, Vector Search" },
  { label: "Database", value: "Lakebase (Postgres) for rules, experiments, incidents, features" },
  { label: "Application", value: "FastAPI + React (deployed as Databricks App)" },
  { label: "Dashboards", value: "3 unified AI/BI Lakeview dashboards (embeddable)" },
  { label: "Model Serving", value: "7 serverless endpoints (3 agents + 4 ML models)" },
  { label: "Infrastructure", value: "100% serverless compute (jobs, pipelines, SQL, serving)" },
  { label: "Deployment", value: "Databricks Asset Bundles (Infrastructure as Code)" },
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
          <h2 className="text-xl font-semibold tracking-tight">How to Use the Platform</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Six areas, each designed to help teams find and act on approval rate improvements.
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
                      need: "One trusted data source for all initiatives",
                      solution: "Real-time medallion pipelines + Unity Catalog",
                      impact: "Everyone works from the same numbers. Smart Checkout, Reason Codes, and Smart Retry share one clean, up-to-date picture.",
                    },
                    {
                      need: "See why payments fail and where to act",
                      solution: "Unified decline taxonomy + Decline Analyst agent",
                      impact: "Declines from all channels in one place, with clear reasons and recovery priorities.",
                    },
                    {
                      need: "Optimize payment-link performance (Brazil)",
                      solution: "Smart Checkout analytics + Smart Routing ML model",
                      impact: "See how each path (Antifraud, 3DS, Token, Passkey) performs. ML picks the route that maximizes approval.",
                    },
                    {
                      need: "Recover more from retries and recurrence",
                      solution: "Smart Retry analytics + ML retry model + AI agent",
                      impact: "Identify which declines are worth retrying, the best timing, and expected recovery rate.",
                    },
                    {
                      need: "Get actionable recommendations, not just reports",
                      solution: "7 AI agents + Decisioning API + Vector Search",
                      impact: "AI recommends specific actions with expected impact. Similar historical cases inform decisions.",
                    },
                    {
                      need: "Consistent decisions across the organization",
                      solution: "Rules engine + ML models + unified decision API",
                      impact: "One decision layer for auth, routing, and retry. Rules and models work together so decisions are consistent with policy.",
                    },
                    {
                      need: "Measure impact of changes",
                      solution: "A/B experiments + incident tracking + feedback loop",
                      impact: "Every policy change is measured. Experiments quantify what works. The system learns and improves over time.",
                    },
                    {
                      need: "One place to run and control everything",
                      solution: "This application (Setup, Dashboards, Rules, AI, Decisioning)",
                      impact: "Teams operate the full stack from a single control panel. No switching between tools.",
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
        <div className="flex flex-wrap gap-2">
          {[
            { to: "/command-center", label: "Command Center" },
            { to: "/dashboards", label: "Dashboards" },
            { to: "/declines", label: "Declines" },
            { to: "/smart-checkout", label: "Smart Checkout" },
            { to: "/smart-retry", label: "Smart Retry" },
            { to: "/decisioning", label: "Decisioning" },
            { to: "/ai-agents", label: "AI Agents" },
            { to: "/models", label: "ML Models" },
            { to: "/experiments", label: "Experiments" },
            { to: "/incidents", label: "Incidents" },
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
