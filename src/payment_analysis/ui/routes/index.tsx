import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/apx/navbar";
import Logo from "@/components/apx/logo";
import { BarChart3, ArrowRight, CheckCircle2, LogIn, CreditCard, ListChecks, RotateCcw, Database, MessageSquareText, Zap, Shield, LineChart, Eye, Sparkles, Layers, GitBranch, Brain, LayoutDashboard, Bot, Gauge, TrendingUp, PlayCircle } from "lucide-react";
import { BubbleBackground } from "@/components/backgrounds/bubble";
import { getWorkspaceUrl } from "@/config/workspace";
import { useGetAuthStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  component: () => <Index />,
});

const valueProps = [
  "Increase revenue and conversion with higher approval rates and smart retry.",
  "Control risk and fraud with real-time decisioning and ML-powered scoring.",
  "One view of portfolio performance with executive dashboards and KPIs.",
  "Clear next steps: see what’s delaying approvals and act with confidence.",
];

const initiatives = [
  {
    to: "/smart-checkout",
    title: "Smart Checkout",
    description: "Payment Link (Brazil). Optimize approval rates with the right service mix: Antifraud, 3DS, Network Token, IdPay, Passkey.",
    icon: CreditCard,
  },
  {
    to: "/reason-codes",
    title: "Reason Codes",
    description: "Unified decline intelligence across entry systems (Checkout, PD, WS, SEP). Standardize reason codes and drive actionable insights.",
    icon: ListChecks,
  },
  {
    to: "/smart-retry",
    title: "Smart Retry",
    description: "Recurrence & reattempts (Brazil). Payment recurrence and cardholder retries — 1M+ transactions/month. Recover more approvals.",
    icon: RotateCcw,
  },
];

const databricksPillars = [
  { icon: Layers, label: "Lakehouse", desc: "One source of truth" },
  { icon: GitBranch, label: "Lakeflow", desc: "Streaming pipelines" },
  { icon: Brain, label: "ML & AI", desc: "Models and agents" },
  { icon: Sparkles, label: "Genie", desc: "Ask your data" },
];

function Index() {
  const { data } = useGetAuthStatus();
  const workspaceUrl = getWorkspaceUrl();
  const authenticated = data?.data?.authenticated ?? null;
  const showSignIn = authenticated === false && workspaceUrl;

  return (
    <div className="relative h-screen w-screen overflow-hidden flex flex-col bg-background">
      <Navbar leftContent={<Logo to="/" showText />} />

      <main className="flex-1 grid md:grid-cols-2 min-h-0" id="landing-main" aria-label="Landing page content">
        <BubbleBackground interactive />

        <div className="relative flex flex-col items-center justify-center p-8 md:p-12 lg:p-16 border-l border-border/50 bg-gradient-to-b from-background/98 via-background/95 to-background/98 backdrop-blur-md landing-panel-scroll">
          <div
            className="max-w-xl w-full space-y-8 text-center md:text-left landing-stagger-container"
            role="presentation"
          >
            {showSignIn && (
              <div
                className={cn("landing-stagger-item delay-0 rounded-xl border border-primary/30 bg-primary/5 p-4 text-left")}
              >
                <p className="text-sm font-medium text-foreground mb-2">
                  Use your Databricks credentials
                </p>
                <p className="text-xs text-muted-foreground mb-3">
                  Open the app from your workspace (Compute → Apps → payment-analysis) so the app can use your identity. No token needs to be set when user authorization (OBO) is enabled.
                </p>
                <Button
                  size="sm"
                  variant="secondary"
                  className="gap-2"
                  onClick={() => window.open(workspaceUrl, "_blank", "noopener,noreferrer")}
                >
                  <LogIn className="h-4 w-4" />
                  Open workspace to sign in
                </Button>
              </div>
            )}

            <div className="landing-stagger-item delay-1 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 font-heading">
              <Zap className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold text-primary">PagoNxt Getnet — Accelerate approval rates</span>
            </div>

            <h1
              className="landing-stagger-item delay-2 hero-impact font-heading text-4xl md:text-5xl lg:text-6xl text-foreground leading-tight"
            >
              Accelerate approval rates
            </h1>
            <p className="landing-stagger-item delay-3 hero-impact-sub font-heading text-xl md:text-2xl text-primary max-w-lg">
              Risk &amp; portfolio intelligence on one platform.
            </p>
            <p className="landing-stagger-item delay-4 text-sm text-muted-foreground max-w-xl">
              Understand what’s driving or delaying approval rates, get clear recommendations, and align routing, retry, and risk strategies — with a single view of your portfolio.
            </p>
            <div className="landing-stagger-item delay-5 grid grid-cols-2 md:flex md:flex-wrap gap-3">
              {[
                { icon: LineChart, label: "Smart routing" },
                { icon: RotateCcw, label: "Retry recovery" },
                { icon: Shield, label: "Risk control" },
                { icon: Eye, label: "Full visibility" },
              ].map(({ icon: Icon, label }) => (
                <div
                  key={label}
                  className="flex items-center gap-2 rounded-lg border border-border/80 bg-card/80 px-3 py-2 shadow-sm"
                >
                  <Icon className="h-4 w-4 text-primary shrink-0" />
                  <span className="text-xs font-medium text-foreground">{label}</span>
                </div>
              ))}
            </div>

            {/* Powered by Databricks — platform trust for CEO */}
            <section className="landing-stagger-item delay-6 rounded-xl border border-border/80 bg-muted/40 dark:bg-muted/20 p-4" aria-labelledby="databricks-heading">
              <h2 id="databricks-heading" className="sr-only">Powered by Databricks</h2>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Powered by Databricks</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {databricksPillars.map(({ icon: Icon, label, desc }) => (
                  <div key={label} className="flex items-start gap-2 rounded-lg bg-background/80 dark:bg-card/80 p-2.5 border border-border/60">
                    <Icon className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-semibold text-foreground">{label}</p>
                      <p className="text-[11px] text-muted-foreground">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Value proposition */}
            <section className="landing-stagger-item delay-7 text-left" aria-labelledby="value-prop-heading">
              <h2 id="value-prop-heading" className="sr-only">
                Why this matters for Getnet
              </h2>
              <p className="text-sm font-semibold text-foreground mb-3">
                Why this matters for Getnet
              </p>
              <ul className="space-y-2">
                {valueProps.map((text, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
            </section>

            {/* Data foundation & geography */}
            <div className="landing-stagger-item delay-8 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5 rounded-md bg-muted/80 px-2.5 py-1">
                <Database className="h-3.5 w-3.5" />
                Data foundation for all initiatives
              </span>
              <span className="rounded-md bg-muted/80 px-2.5 py-1">
                Brazil · ~70% of Getnet volume
              </span>
            </div>

            {/* Initiative cards — business-oriented, impactful */}
            <section className="landing-stagger-item delay-9 space-y-3" aria-labelledby="initiatives-heading">
              <h2 id="initiatives-heading" className="section-label">Where to act</h2>
              <div className="grid gap-4 sm:grid-cols-1">
                {initiatives.map((init) => {
                  const Icon = init.icon;
                  return (
                    <Link
                      key={init.to}
                      to={init.to}
                      className="business-value-card card-interactive group flex items-start gap-4 rounded-xl border border-border bg-card p-5 text-left transition-all hover:border-primary/40 hover:bg-card/98"
                    >
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/20">
                        <Icon className="h-6 w-6" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {init.title}
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
                          {init.description}
                        </p>
                      </div>
                      <ArrowRight className="h-5 w-5 shrink-0 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                    </Link>
                  );
                })}
              </div>
            </section>

            {/* For CEO & Getnet team — one place for impact metrics and discovery */}
            <section className="landing-stagger-item delay-10 rounded-xl border border-primary/20 bg-primary/5 dark:bg-primary/10 p-4 font-heading" aria-labelledby="ceo-section-heading">
              <h2 id="ceo-section-heading" className="text-sm font-semibold text-primary mb-3 tracking-tight">For CEO &amp; Getnet team</h2>
              <p className="text-xs text-muted-foreground mb-3">Ingestion volume, data quality, risk scoring, fraud signals, approval by merchant — and AI-powered discovery to accelerate approval rates.</p>
              <div className="flex flex-wrap gap-2">
                <Link to="/command-center" className="inline-flex items-center gap-1.5 rounded-lg bg-background/90 dark:bg-card px-3 py-2 text-xs font-medium border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors">
                  <BarChart3 className="h-3.5 w-3.5" />
                  Executive overview
                </Link>
                <Link to="/command-center" className="inline-flex items-center gap-1.5 rounded-lg bg-background/90 dark:bg-card px-3 py-2 text-xs font-medium border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors">
                  <TrendingUp className="h-3.5 w-3.5" />
                  Ingestion &amp; volume
                </Link>
                <Link to="/dashboards" className="inline-flex items-center gap-1.5 rounded-lg bg-background/90 dark:bg-card px-3 py-2 text-xs font-medium border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors">
                  <Gauge className="h-3.5 w-3.5" />
                  Data quality
                </Link>
                <Link to="/dashboards" className="inline-flex items-center gap-1.5 rounded-lg bg-background/90 dark:bg-card px-3 py-2 text-xs font-medium border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors">
                  <Shield className="h-3.5 w-3.5" />
                  Risk &amp; fraud
                </Link>
                <Link to="/dashboards" className="inline-flex items-center gap-1.5 rounded-lg bg-background/90 dark:bg-card px-3 py-2 text-xs font-medium border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors">
                  <LineChart className="h-3.5 w-3.5" />
                  Approval by merchant
                </Link>
                <Link to="/dashboards" className="inline-flex items-center gap-1.5 rounded-lg bg-background/90 dark:bg-card px-3 py-2 text-xs font-medium border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors">
                  <LayoutDashboard className="h-3.5 w-3.5" />
                  All dashboards
                </Link>
                <Link to="/ai-agents" className="inline-flex items-center gap-1.5 rounded-lg bg-background/90 dark:bg-card px-3 py-2 text-xs font-medium border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors">
                  <Bot className="h-3.5 w-3.5" />
                  AI agents &amp; chat
                </Link>
                <Link to="/decisioning" className="inline-flex items-center gap-1.5 rounded-lg bg-background/90 dark:bg-card px-3 py-2 text-xs font-medium border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors">
                  <MessageSquareText className="h-3.5 w-3.5" />
                  Recommendations
                </Link>
              </div>
            </section>

            {/* Primary CTAs — clear, impactful */}
            <div className="landing-stagger-item delay-11 flex flex-col sm:flex-row flex-wrap gap-3 justify-center md:justify-start pt-2">
              <Button
                size="lg"
                className="cta-glow gap-2 min-w-[240px] h-12 text-base font-semibold shadow-lg transition-all duration-200 rounded-xl px-6"
                asChild
              >
                <Link to="/command-center">
                  <BarChart3 className="h-5 w-5" />
                  Open Command Center
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="gap-2 min-w-[200px] h-12 text-base font-medium rounded-xl border-2"
                asChild
              >
                <Link to="/decisioning">
                  <MessageSquareText className="h-5 w-5" />
                  Recommendations &amp; next steps
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="gap-2 min-w-[200px] h-12 text-base font-medium rounded-xl border-2"
                asChild
              >
                <Link to="/setup">
                  <PlayCircle className="h-5 w-5" />
                  Control panel — run jobs &amp; pipelines
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
