import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Database,
  CreditCard,
  ListChecks,
  RotateCcw,
  BarChart3,
  MessageSquareText,
  Shield,
  Globe,
  ArrowRight,
  Target,
} from "lucide-react";

export const Route = createFileRoute("/_sidebar/about")({
  component: About,
});

const BUSINESS_PURPOSE = {
  title: "Why this platform exists",
  intro:
    "Getnet processes millions of payment transactions every year. Each transaction can use several services — such as Antifraud, 3DS, Network Token, or IdPay — to improve security and approval rates. Making the right choices at the right time is complex: different entry systems (Checkout, PD, WS, SEP), different seller profiles, and different regions (Brazil alone is over 70% of volume) all affect outcomes.",
  goals: [
    "Give teams one place to see what is driving or delaying approval rates.",
    "Unify decline reasons across systems so we can act on the biggest opportunities.",
    "Recommend when and how to retry declined transactions and how to route the next one.",
    "Keep data clean and consistent so every initiative (Smart Checkout, Reason Codes, Smart Retry) runs on the same foundation.",
  ],
};

const WHAT_THE_PLATFORM_DOES = {
  title: "What the platform does (in simple terms)",
  items: [
    {
      icon: Database,
      title: "Single data foundation",
      description:
        "All payment-related data is ingested, cleaned, and stored in one place. Dashboards, AI, and recommendations use this same source so numbers and insights stay aligned.",
    },
    {
      icon: BarChart3,
      title: "Dashboards and KPIs",
      description:
        "Executive overview, approval trends, decline reasons, routing performance, and data quality are available in real time. You can focus on Brazil or other regions.",
    },
    {
      icon: ListChecks,
      title: "Reason codes and declines",
      description:
        "Declines from different entry systems are consolidated and standardized. You see top decline reasons and where recovery or routing changes can have the most impact.",
    },
    {
      icon: CreditCard,
      title: "Smart Checkout",
      description:
        "Visibility into how payment-link transactions perform by solution (Antifraud, 3DS, Network Token, etc.) so you can balance security, friction, and approval rates.",
    },
    {
      icon: RotateCcw,
      title: "Smart Retry",
      description:
        "Surfaces transactions that are good candidates for a retry (recurrence or cardholder reattempts) and suggests when and how to retry to recover more approvals.",
    },
    {
      icon: MessageSquareText,
      title: "Recommendations and AI",
      description:
        "AI agents and the decisioning layer suggest next steps — for example, routing changes, rule updates, or retry strategies — with the goal of accelerating approval rates.",
    },
    {
      icon: Shield,
      title: "Rules and control",
      description:
        "Business rules (who to approve, when to retry, how to route) can be configured without code. Experiments help measure the impact of changes.",
    },
    {
      icon: Globe,
      title: "Geographic focus",
      description:
        "Brazil-first by default (most of Getnet volume). You can filter and analyze by country or region so local teams get relevant insights.",
    },
  ],
};

const REQUIREMENT_MAP_INTRO =
  "Each business need is addressed by a specific part of the platform. The table below summarizes how.";

const REQUIREMENT_MAP: { requirement: string; solution: string; description: string }[] = [
  {
    requirement: "Data foundation for all initiatives",
    solution: "Medallion pipelines and gold views",
    description: "One source of truth so Smart Checkout, Reason Codes, and Smart Retry use the same clean data.",
  },
  {
    requirement: "Unified decline visibility and reason codes",
    solution: "Reason Codes, decline dashboards, Decline Analyst agent",
    description: "Consolidate declines, standardize codes, and see top reasons and recovery opportunities.",
  },
  {
    requirement: "Smart Checkout (payment link, Brazil)",
    solution: "Smart Checkout UI, 3DS funnel, routing, Smart Routing agent",
    description: "See approval by solution and optimize the mix of Antifraud, 3DS, Network Token, etc.",
  },
  {
    requirement: "Smart Retry (recurrence and reattempts)",
    solution: "Smart Retry UI, retry performance, Smart Retry agent",
    description: "Find recoverable declines and get recommendations on when and how to retry.",
  },
  {
    requirement: "Actionable insights and recommendations",
    solution: "Decisioning API, Recommendations UI, orchestrator and 5 AI agents, rules",
    description: "Prescriptive next steps and estimated impact, with rules and ML in one decision layer.",
  },
  {
    requirement: "Single control panel",
    solution: "This app: Setup & Run, Dashboards, Rules, Decisioning, Reason Codes, Smart Checkout, Smart Retry, AI agents",
    description: "One place to run jobs, manage rules, view dashboards, and act on recommendations.",
  },
];

function About() {
  return (
    <div className="space-y-6 p-4 md:p-6 max-w-4xl">
      <header className="rounded-lg bg-primary px-4 py-3 text-primary-foreground">
        <h1 className="text-lg font-semibold">About this platform</h1>
        <p className="text-sm opacity-90 mt-1">
          Business purpose and how the solution meets it — in plain language.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Target className="h-4 w-4" />
            {BUSINESS_PURPOSE.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">{BUSINESS_PURPOSE.intro}</p>
          <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
            {BUSINESS_PURPOSE.goals.map((goal, i) => (
              <li key={i}>{goal}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{WHAT_THE_PLATFORM_DOES.title}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-1">
          {WHAT_THE_PLATFORM_DOES.items.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="flex gap-3 rounded-lg border border-border/80 bg-muted/30 p-3"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">{item.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Business requirement → Solution</CardTitle>
          <p className="text-sm text-muted-foreground font-normal">{REQUIREMENT_MAP_INTRO}</p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 pr-4 font-medium text-foreground">Business requirement</th>
                  <th className="py-2 pr-4 font-medium text-foreground">Solution in this platform</th>
                  <th className="py-2 font-medium text-foreground">Brief description</th>
                </tr>
              </thead>
              <tbody>
                {REQUIREMENT_MAP.map((row, i) => (
                  <tr key={i} className="border-b border-border/60">
                    <td className="py-2 pr-4 text-muted-foreground align-top">{row.requirement}</td>
                    <td className="py-2 pr-4 text-foreground align-top">{row.solution}</td>
                    <td className="py-2 text-muted-foreground align-top">{row.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-muted/30">
        <CardHeader>
          <CardTitle className="text-base">Documentation</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            <strong>For leadership:</strong> The repository <strong>README</strong> includes a &quot;Map for business users&quot; table: business purpose, technical solution, and a brief plain-language &quot;What you get&quot; for each capability (no technical jargon).
          </p>
          <p>
            Full documentation (deploy, architecture, Databricks, agents) is in the <code className="rounded bg-muted px-1">docs/</code> folder. Start with <code className="rounded bg-muted px-1">docs/INDEX.md</code> for the document map.
          </p>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Link
          to="/command-center"
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted/50 transition-colors"
        >
          Overview
          <ArrowRight className="h-4 w-4" />
        </Link>
        <Link
          to="/initiatives"
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted/50 transition-colors"
        >
          Payment Services &amp; Data
          <ArrowRight className="h-4 w-4" />
        </Link>
        <Link
          to="/decisioning"
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted/50 transition-colors"
        >
          Recommendations
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
