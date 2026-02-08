import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/apx/navbar";
import Logo from "@/components/apx/logo";
import { motion } from "motion/react";
import { BarChart3, ArrowRight, CheckCircle2, LogIn, CreditCard, ListChecks, RotateCcw, Database, MessageSquareText } from "lucide-react";
import { BubbleBackground } from "@/components/backgrounds/bubble";
import { getWorkspaceUrl } from "@/config/workspace";
import { useGetAuthStatus } from "@/lib/api";

export const Route = createFileRoute("/")({
  component: () => <Index />,
});

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

const valueProps = [
  "Higher approval rates and conversion with smart routing and retry.",
  "Reduced risk and fraud via ML models and real-time decisioning.",
  "Full portfolio visibility with live dashboards and executive KPIs.",
  "Actionable insights so you know where to act next.",
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

function Index() {
  const { data } = useGetAuthStatus();
  const workspaceUrl = getWorkspaceUrl();
  const authenticated = data?.data?.authenticated ?? null;
  const showSignIn = authenticated === false && workspaceUrl;

  return (
    <div className="relative h-screen w-screen overflow-hidden flex flex-col bg-background">
      <Navbar leftContent={<Logo to="/" showText />} />

      <main className="flex-1 grid md:grid-cols-2 min-h-0">
        <BubbleBackground interactive />

        <div className="relative flex flex-col items-center justify-center p-8 md:p-12 lg:p-16 border-l border-border/50 bg-gradient-to-b from-background/98 via-background/95 to-background/98 backdrop-blur-md overflow-y-auto">
          <motion.div
            className="max-w-xl w-full space-y-8 text-center md:text-left"
            variants={container}
            initial="hidden"
            animate="show"
          >
            {showSignIn && (
              <motion.div
                variants={item}
                className="rounded-xl border border-primary/30 bg-primary/5 p-4 text-left"
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
                  onClick={() => window.open(workspaceUrl, "_blank")}
                >
                  <LogIn className="h-4 w-4" />
                  Open workspace to sign in
                </Button>
              </motion.div>
            )}

            {/* North star: accelerate approval rates */}
            <motion.div variants={item} className="space-y-1">
              <p className="text-base md:text-lg font-medium text-primary">
                Accelerate approval rates. Identify what’s delaying them. Act on recommendations.
              </p>
              <p className="text-sm text-muted-foreground">
                One platform for Getnet to maximize conversion and control.
              </p>
            </motion.div>

            <motion.h1
              variants={item}
              className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-foreground leading-tight font-heading"
            >
              Risk & Portfolio Intelligence for Getnet
            </motion.h1>
            <motion.p
              variants={item}
              className="text-sm text-muted-foreground"
            >
              Discover conditions and factors that delay approval rates; get recommendations and automated processes to accelerate them — all in one place.
            </motion.p>

            {/* Value proposition */}
            <motion.div variants={item} className="text-left">
              <p className="text-sm font-semibold text-foreground mb-3">
                What this solution does for Getnet
              </p>
              <ul className="space-y-2">
                {valueProps.map((text, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
            </motion.div>

            {/* Data foundation & geography */}
            <motion.div
              variants={item}
              className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground"
            >
              <span className="inline-flex items-center gap-1.5 rounded-md bg-muted/80 px-2.5 py-1">
                <Database className="h-3.5 w-3.5" />
                Data foundation for all initiatives
              </span>
              <span className="rounded-md bg-muted/80 px-2.5 py-1">
                Brazil · ~70% of Getnet volume
              </span>
            </motion.div>

            {/* Initiative cards — one per business objective */}
            <motion.div variants={item} className="space-y-3">
              <p className="text-sm font-semibold text-foreground">Key initiatives</p>
              <div className="grid gap-3 sm:grid-cols-1">
                {initiatives.map((init) => {
                  const Icon = init.icon;
                  return (
                    <Link
                      key={init.to}
                      to={init.to}
                      className="group flex items-start gap-4 rounded-xl border border-border/80 bg-card p-4 text-left transition-all hover:border-primary/40 hover:shadow-md hover:bg-card/95"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-foreground group-hover:text-primary">
                          {init.title}
                        </p>
                        <p className="mt-0.5 text-sm text-muted-foreground">
                          {init.description}
                        </p>
                      </div>
                      <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-transform" />
                    </Link>
                  );
                })}
              </div>
            </motion.div>

            {/* Primary CTAs: how to accelerate approval rates */}
            <motion.div
              variants={item}
              className="flex flex-col sm:flex-row gap-3 justify-center md:justify-start pt-2"
            >
              <Button
                size="lg"
                className="gap-2 min-w-[220px] h-12 text-base font-semibold shadow-lg hover:shadow-xl hover:shadow-primary/20 transition-all duration-200"
                asChild
              >
                <Link to="/dashboard">
                  <BarChart3 className="h-5 w-5" />
                  See how to accelerate
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="gap-2 min-w-[180px] h-12 text-base font-medium"
                asChild
              >
                <Link to="/decisioning">
                  <MessageSquareText className="h-5 w-5" />
                  Recommendations & actions
                </Link>
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
