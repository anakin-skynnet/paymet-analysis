import { Suspense } from "react";
import type { CSSProperties } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ErrorBoundary } from "react-error-boundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGetKpisSuspense,
  useGetSolutionPerformanceSuspense,
  useGetThreeDsFunnel,
  useGetEntrySystemDistribution,
  useHealthDatabricks,
} from "@/lib/api";
import selector from "@/lib/selector";
import { useEntity } from "@/contexts/entity-context";
import { DataSourceBadge } from "@/components/apx/data-source-badge";
import { GeographyWorldMap } from "@/components/geography/geography-world-map";
import {
  Shield,
  CreditCard,
  Database,
  Fingerprint,
  Settings2,
  Brain,
  Gauge,
  RotateCcw,
  Calendar,
  ArrowRight,
} from "lucide-react";

function InitiativesErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
  return (
    <Card className="glass-card border border-destructive/30 max-w-lg mx-auto mt-12">
      <CardContent className="py-8 text-center space-y-4">
        <p className="text-lg font-semibold">Failed to load Initiatives</p>
        <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : "Unknown error"}</p>
        <Button onClick={resetErrorBoundary}>Try again</Button>
      </CardContent>
    </Card>
  );
}

export const Route = createFileRoute("/_sidebar/initiatives")({
  component: () => (
    <ErrorBoundary FallbackComponent={InitiativesErrorFallback}>
      <Suspense fallback={<InitiativesSkeleton />}>
        <Initiatives />
      </Suspense>
    </ErrorBoundary>
  ),
});

const PAYMENT_SERVICES = [
  { id: "antifraud", name: "Antifraud", icon: Shield },
  { id: "3ds", name: "3DS", icon: CreditCard },
  { id: "vault", name: "Vault", icon: Database },
  { id: "data_only", name: "Data Only", icon: Database },
  { id: "network_token", name: "Network Token", icon: CreditCard },
  { id: "idpay", name: "IdPay", icon: Fingerprint },
  { id: "click_to_pay", name: "Click to Pay", icon: CreditCard },
] as const;

const EXPECTED_OUTCOMES = [
  "Consolidate Declines",
  "Standardize Taxonomy",
  "Identify Degradation",
  "Actionable Insights",
  "Feedback Loop",
];

function InitiativesSkeleton() {
  return (
    <div className="space-y-6 p-4">
      <Skeleton className="h-10 w-96" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

const REFRESH_ANALYTICS_MS = 15_000;

function Initiatives() {
  const { entity } = useEntity();
  const { data: kpis } = useGetKpisSuspense(selector());
  const { data: solutions } = useGetSolutionPerformanceSuspense(selector());
  const { data: healthData } = useHealthDatabricks({ query: { refetchInterval: REFRESH_ANALYTICS_MS } });
  const funnelQ = useGetThreeDsFunnel({
    params: { entity, days: 30 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const entryQ = useGetEntrySystemDistribution({
    params: { entity },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });

  const funnel = funnelQ.data?.data ?? [];
  const latestFunnel = funnel[0];

  const entrySystems = entryQ.data?.data ?? [];
  const totalEntry = entrySystems.reduce((s, r) => s + r.transaction_count, 0);
  const entryWithPct = totalEntry > 0 ? entrySystems.map((e) => ({ ...e, pct: Math.round((e.transaction_count / totalEntry) * 100) })) : [];

  const maxSolutionCount = Math.max(...(solutions?.map((s) => s.transaction_count) ?? [1]), 1);

  const approvalPct = kpis ? (kpis.approval_rate * 100).toFixed(1) : null;
  const totalTxn = kpis?.total ?? 0;
  const transactionsPerYear = totalTxn > 0 ? (totalTxn * (365 / 30)).toLocaleString(undefined, { maximumFractionDigits: 0 }) : null;

  const fromDatabricks = healthData?.data?.analytics_source === "Unity Catalog";

  return (
    <div className="space-y-6 p-4">
      <header className="flex items-center justify-between rounded-lg bg-primary px-4 py-3 text-primary-foreground">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-lg font-semibold">Getnet Payment Services &amp; Data Initiatives</h1>
          <DataSourceBadge label={fromDatabricks ? "From Databricks" : "Backend"} className="text-primary-foreground/90" />
        </div>
        <button type="button" className="rounded p-1 hover:bg-primary-foreground/10" aria-label="Open menu">
          <span className="inline-block h-5 w-6 border-y-2 border-current" aria-hidden />
        </button>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left column */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Payment Services Context</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {PAYMENT_SERVICES.map((s) => {
                const Icon = s.icon;
                return (
                  <div key={s.id} className="flex items-center gap-2 text-sm">
                    <span className="inline-flex h-4 w-4 shrink-0 rounded border border-muted-foreground/40" aria-hidden />
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <span>{s.name}</span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <GeographyWorldMap />

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Data Foundation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center justify-center gap-4 rounded-lg border border-border/80 bg-muted/30 p-4">
                <div className="flex flex-col items-center gap-1">
                  <Settings2 className="h-8 w-8 text-primary" />
                  <span className="text-xs text-muted-foreground">Data Treatment</span>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <div className="flex flex-col items-center gap-1">
                  <Settings2 className="h-8 w-8 text-primary" />
                  <span className="text-xs text-muted-foreground">Data Quality</span>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <div className="flex flex-col items-center gap-1">
                  <Brain className="h-8 w-8 text-primary" />
                  <span className="text-xs text-muted-foreground">Insights</span>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded border border-border/80 p-2">
                <Gauge className="h-5 w-5 text-muted-foreground" />
                <Link to="/dashboards" className="text-sm text-muted-foreground hover:text-foreground">
                  Data quality dashboards
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Smart Checkout — Brazil Focus</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-primary/10 p-4 text-center">
                  <p className="text-2xl font-bold text-primary tabular-nums">{transactionsPerYear ?? "—"}</p>
                  <p className="text-xs text-muted-foreground">Transactions/Year</p>
                </div>
                <div className="rounded-lg bg-primary/10 p-4 text-center">
                  <p className="text-2xl font-bold text-primary tabular-nums">{approvalPct != null ? `${approvalPct}%` : "—"}</p>
                  <p className="text-xs text-muted-foreground">Approval Rate</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Breakdown by Service</CardTitle>
            </CardHeader>
            <CardContent>
              {!solutions?.length ? (
                <p className="text-sm text-muted-foreground">No solution data yet.</p>
              ) : (
                <div className="space-y-2">
                  {solutions.slice(0, 6).map((s) => (
                    <div key={s.payment_solution} className="flex items-center gap-2">
                      <div
                        className="bar-fill-width h-6 min-w-[4px] rounded bg-primary"
                        style={{ ["--bar-width-pct"]: `${Math.max(4, (s.transaction_count / maxSolutionCount) * 100)}%` } as CSSProperties}
                        aria-hidden
                      />
                      <span className="w-24 shrink-0 truncate text-xs" title={s.payment_solution}>
                        {s.payment_solution}
                      </span>
                      <span className="text-xs tabular-nums text-muted-foreground">{s.approval_rate_pct.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">2025 3DS Test</CardTitle>
            </CardHeader>
            <CardContent>
              {funnelQ.isLoading ? (
                <Skeleton className="h-20" />
              ) : !latestFunnel ? (
                <p className="text-sm text-muted-foreground">No 3DS funnel data yet.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  <li className="tabular-nums">
                    {latestFunnel.three_ds_friction_rate_pct != null ? `${latestFunnel.three_ds_friction_rate_pct}%` : "—"} Friction
                  </li>
                  <li className="tabular-nums">
                    {latestFunnel.three_ds_authentication_rate_pct != null ? `${latestFunnel.three_ds_authentication_rate_pct}%` : "—"} Auth Success
                  </li>
                  <li className="tabular-nums">
                    {latestFunnel.issuer_approval_post_auth_rate_pct != null ? `${latestFunnel.issuer_approval_post_auth_rate_pct}%` : "—"} Auth Approved
                  </li>
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Reason Codes — Brazil Scope</CardTitle>
              <p className="text-xs text-muted-foreground">4 Entry Systems</p>
            </CardHeader>
            <CardContent>
              {entryQ.isLoading ? (
                <Skeleton className="h-24" />
              ) : entryWithPct.length === 0 ? (
                <p className="text-sm text-muted-foreground">No entry system data yet.</p>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  {entryWithPct.map((e, i) => (
                    <span key={e.entry_system}>
                      <span className="rounded border border-border/80 bg-muted/50 px-2 py-1 text-xs font-medium">
                        {e.entry_system} {e.pct}%
                      </span>
                      {i < entryWithPct.length - 1 && <ArrowRight className="inline h-3 w-3 mx-1 text-muted-foreground" />}
                    </span>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Counter Metrics — Insight Quality Control</CardTitle>
              <p className="text-xs text-muted-foreground">Expected Outcomes</p>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                {EXPECTED_OUTCOMES.map((o) => (
                  <li key={o}>{o}</li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Smart Retry — Initial Context</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm">Payment Recurrence e.g. Subscriptions</span>
              </div>
              <div className="flex items-center gap-2">
                <RotateCcw className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm tabular-nums">
                  Brazil: {totalTxn > 0 ? `>${(totalTxn / 1_000_000).toFixed(1)}M` : "—"} Transactions (portfolio)
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
