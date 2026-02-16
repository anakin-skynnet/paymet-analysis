import { createFileRoute, Link } from "@tanstack/react-router";
import { ErrorBoundary } from "react-error-boundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import Navbar from "@/components/apx/navbar";
import Logo from "@/components/apx/logo";
import {
  BarChart3,
  ArrowRight,
  CreditCard,
  ListChecks,
  RotateCcw,
  MessageSquareText,
  Zap,
  Shield,
  LineChart,
  Eye,
  Layers,
  LogIn,
} from "lucide-react";
import { BubbleBackground } from "@/components/backgrounds/bubble";
import { getWorkspaceUrl } from "@/config/workspace";
import { useGetAuthStatus } from "@/lib/api";
import { ScrollArea } from "@/components/ui/scroll-area";

export const Route = createFileRoute("/")({
  component: () => (
    <ErrorBoundary fallbackRender={({ resetErrorBoundary }) => (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background text-foreground gap-4 p-6">
        <p className="text-muted-foreground">Something went wrong loading the dashboard.</p>
        <Button onClick={resetErrorBoundary} variant="outline">Try again</Button>
      </div>
    )}>
      <Index />
    </ErrorBoundary>
  ),
});

const initiatives = [
  {
    to: "/smart-checkout",
    title: "Smart Checkout",
    description: "Optimize approval rates with the right service mix.",
    icon: CreditCard,
  },
  {
    to: "/reason-codes",
    title: "Reason Codes",
    description: "Unified decline intelligence and actionable insights.",
    icon: ListChecks,
  },
  {
    to: "/smart-retry",
    title: "Smart Retry",
    description: "Recover more approvals with recurrence and retries.",
    icon: RotateCcw,
  },
];

function Index() {
  const { data, isLoading: authLoading } = useGetAuthStatus();
  const workspaceUrl = getWorkspaceUrl();
  const authenticated = data?.data?.authenticated ?? null;
  const showSignIn = !authLoading && authenticated === false && workspaceUrl;

  return (
    <div className="flex min-h-screen w-full flex-col overflow-x-hidden bg-background">
      <Navbar leftContent={<Logo to="/" showText />} />

      <main
        className="grid flex-1 min-h-0 md:grid-cols-2"
        id="landing-main"
        aria-label="Landing page content"
      >
        <BubbleBackground interactive />

        <div className="relative flex min-h-0 flex-1 flex-col border-l border-border/40 bg-gradient-to-b from-background/98 via-background/95 to-background/98 backdrop-blur-sm">
          <ScrollArea className="flex-1 min-h-0">
            <div className="mx-auto flex w-full max-w-lg flex-col gap-10 px-6 py-10 pb-20 text-center md:max-w-xl md:px-10 md:py-14 md:pb-24 md:text-left lg:px-12 lg:py-16">
              {showSignIn && (
                <Card className="landing-stagger-item delay-0 border-primary/25 bg-primary/5 py-3">
                  <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-sm text-foreground">
                      Open from your workspace (Compute → Apps) to sign in with Databricks.
                    </p>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="gap-2 shrink-0"
                      onClick={() =>
                        window.open(workspaceUrl, "_blank", "noopener,noreferrer")
                      }
                    >
                      <LogIn className="h-4 w-4" />
                      Open workspace
                    </Button>
                  </CardContent>
                </Card>
              )}

              <div className="landing-stagger-item delay-1 space-y-6">
                <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-2 text-xs font-medium text-primary">
                  <Zap className="h-4 w-4" />
                  Payment approval intelligence
                </div>

                <div className="space-y-4">
                  <h1 className="hero-impact font-heading text-4xl font-bold leading-[1.1] tracking-tight text-foreground md:text-5xl lg:text-6xl">
                    Accelerate approval rates
                  </h1>
                  <p className="hero-impact-sub font-heading text-lg font-semibold text-primary md:text-xl">
                    One platform for risk, routing, and portfolio visibility.
                  </p>
                  <p className="text-sm leading-relaxed text-muted-foreground max-w-md md:max-w-lg">
                    See what’s driving or delaying approvals, get clear next steps, and align retry and risk strategies with a single view of your portfolio.
                  </p>
                </div>

                <div className="flex flex-wrap justify-center gap-2 md:justify-start">
                  {[
                    { icon: LineChart, label: "Smart routing" },
                    { icon: RotateCcw, label: "Retry recovery" },
                    { icon: Shield, label: "Risk control" },
                    { icon: Eye, label: "Full visibility" },
                  ].map(({ icon: Icon, label }) => (
                    <span
                      key={label}
                      className="inline-flex items-center gap-2 rounded-lg border border-border/70 bg-card/60 px-3 py-2 text-xs font-medium text-foreground"
                    >
                      <Icon className="h-4 w-4 text-primary" />
                      {label}
                    </span>
                  ))}
                </div>
              </div>

              <div className="landing-stagger-item delay-2 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-center md:justify-start">
                <Button
                  size="lg"
                  className="cta-glow h-12 min-w-[200px] gap-2 rounded-xl px-6 text-base font-semibold shadow-md"
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
                  className="h-12 min-w-[180px] gap-2 rounded-xl border-2 font-medium"
                  asChild
                >
                  <Link to="/decisioning">
                    <MessageSquareText className="h-5 w-5" />
                    Recommendations
                  </Link>
                </Button>
              </div>

              <section
                className="landing-stagger-item delay-3 space-y-4"
                aria-labelledby="initiatives-heading"
              >
                <h2
                  id="initiatives-heading"
                  className="text-xs font-semibold uppercase tracking-widest text-muted-foreground"
                >
                  Where to act
                </h2>
                <div className="grid gap-3">
                  {initiatives.map((init) => {
                    const Icon = init.icon;
                    return (
                      <Link
                        key={init.to}
                        to={init.to}
                        className="group flex items-center gap-4 rounded-xl border border-border/80 bg-card/50 p-4 text-left transition-all hover:border-primary/30 hover:bg-card/80 hover:shadow-sm"
                      >
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                          <Icon className="h-5 w-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-foreground group-hover:text-primary">
                            {init.title}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {init.description}
                          </p>
                        </div>
                        <ArrowRight className="h-5 w-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                      </Link>
                    );
                  })}
                </div>
              </section>

              <footer className="landing-stagger-item delay-4 flex flex-col items-center gap-4 border-t border-border/60 pt-8 md:flex-row md:justify-between md:items-end">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Layers className="h-4 w-4 text-primary/70" />
                  <span>Powered by Databricks Lakehouse</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Data foundation for all initiatives · Brazil
                </p>
              </footer>
            </div>
          </ScrollArea>
        </div>
      </main>
    </div>
  );
}
