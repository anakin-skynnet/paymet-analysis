import { createFileRoute } from "@tanstack/react-router";
import { Suspense } from "react";

import {
  useGetRetryPerformanceSuspense,
  useGetKpisSuspense,
  type RetryPerformanceOut,
} from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  ExternalLink,
  RefreshCw,
  Calendar,
  Repeat,
  DollarSign,
  TrendingUp,
  BarChart3,
  CheckCircle,
} from "lucide-react";
import { Bar, BarChart, XAxis, YAxis, CartesianGrid, Cell } from "recharts";
import { getLakeviewDashboardUrl, openInDatabricks } from "@/config/workspace";

export const Route = createFileRoute("/_sidebar/smart-retry")({
  component: () => <SmartRetry />,
});

const SCENARIOS = [
  {
    id: "recurrence",
    title: "Payment Recurrence",
    desc: "Scheduled or subscription-based payments (e.g. monthly charges).",
    icon: Calendar,
  },
  {
    id: "retry",
    title: "Payment Retry (Reattempts)",
    desc: "Cardholder has a transaction declined and performs a new attempt under the same conditions — same card, amount, and merchant.",
    icon: RefreshCw,
  },
] as const;

const REFRESH_ANALYTICS_MS = 15_000;

const retryChartConfig = {
  success_rate_pct: { label: "Success Rate %", color: "#2563eb" },
  recovered_value: { label: "Recovered Value", color: "#16a34a" },
} satisfies ChartConfig;

const SCENARIO_COLORS: Record<string, string> = {
  PaymentRetry: "#2563eb",
  PaymentRecurrence: "#16a34a",
  Retry: "#ea580c",
  Recurrence: "#8b5cf6",
};

/* ----- KPI Summary ----- */
function RetryKPIs() {
  const { data: kpisResp } = useGetKpisSuspense();
  const kpis = kpisResp?.data;
  const { data: retryResp } = useGetRetryPerformanceSuspense({
    params: { limit: 50 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const rows = retryResp?.data ?? [];

  const totalRetries = rows.reduce((sum: number, r: RetryPerformanceOut) => sum + (r.retry_attempts ?? 0), 0);
  const totalRecovered = rows.reduce((sum: number, r: RetryPerformanceOut) => sum + (r.recovered_value ?? 0), 0);
  const avgSuccessRate = rows.length > 0
    ? (rows.reduce((sum: number, r: RetryPerformanceOut) => sum + (r.success_rate_pct ?? 0), 0) / rows.length).toFixed(1)
    : "—";

  return (
    <div className="grid gap-4 sm:grid-cols-4">
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Total Transactions</p>
          <p className="text-2xl font-bold">{(kpis?.total ?? 0).toLocaleString()}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-1">
            <Repeat className="w-4 h-4 text-primary" />
            <p className="text-sm text-muted-foreground">Retry Attempts</p>
          </div>
          <p className="text-2xl font-bold">{totalRetries.toLocaleString()}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <p className="text-sm text-muted-foreground">Avg Success Rate</p>
          </div>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{avgSuccessRate}%</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-1">
            <DollarSign className="w-4 h-4 text-emerald-500" />
            <p className="text-sm text-muted-foreground">Recovered Value</p>
          </div>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            ${totalRecovered.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function KPISkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardContent className="pt-6 space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-20" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/* ----- Retry Performance Chart ----- */
function RetryPerformanceChart() {
  const { data: retryResp } = useGetRetryPerformanceSuspense({
    params: { limit: 50 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const rows = retryResp?.data ?? [];

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No retry data yet. Run the simulator and ETL to populate retry performance views.
      </p>
    );
  }

  // Aggregate by scenario for the chart
  const byScenario = new Map<string, { total: number; successWeighted: number; recovered: number }>();
  for (const r of rows) {
    const key = r.retry_scenario ?? "Unknown";
    const existing = byScenario.get(key) ?? { total: 0, successWeighted: 0, recovered: 0 };
    existing.total += r.retry_attempts ?? 0;
    existing.successWeighted += (r.success_rate_pct ?? 0) * (r.retry_attempts ?? 1);
    existing.recovered += r.recovered_value ?? 0;
    byScenario.set(key, existing);
  }

  const chartData = Array.from(byScenario.entries()).map(([scenario, agg]) => ({
    scenario,
    success_rate_pct: agg.total > 0 ? Math.round(agg.successWeighted / agg.total) : 0,
    recovered_value: Math.round(agg.recovered),
    fill: SCENARIO_COLORS[scenario] ?? "#6366f1",
  }));

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Success Rate by Scenario */}
      <div>
        <p className="text-sm font-medium mb-3">Success Rate by Scenario</p>
        <ChartContainer config={retryChartConfig} className="h-[260px] w-full">
          <BarChart data={chartData} layout="horizontal" barCategoryGap="20%" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis dataKey="scenario" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="success_rate_pct" fill="#2563eb" radius={[4, 4, 0, 0]} name="Success Rate %">
              {chartData.map((entry, index) => (
                <Cell key={`cell-sr-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ChartContainer>
      </div>

      {/* Recovered Value by Scenario */}
      <div>
        <p className="text-sm font-medium mb-3">Recovered Value by Scenario ($)</p>
        <ChartContainer config={retryChartConfig} className="h-[260px] w-full">
          <BarChart data={chartData} layout="horizontal" barCategoryGap="20%" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis dataKey="scenario" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(Number(v)/1000).toFixed(0)}k`} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="recovered_value" fill="#16a34a" radius={[4, 4, 0, 0]} name="Recovered Value">
              {chartData.map((entry, index) => (
                <Cell key={`cell-rv-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ChartContainer>
      </div>
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {[1, 2].map((i) => (
        <div key={i} className="space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-[220px] w-full rounded-lg" />
        </div>
      ))}
    </div>
  );
}

/* ----- Retry Cohorts Table ----- */
function RetryCohorts() {
  const { data: retryResp } = useGetRetryPerformanceSuspense({
    params: { limit: 50 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const rows = retryResp?.data ?? [];

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No data yet. Run the simulator and ETL to populate views.</p>
    );
  }

  return (
    <ul className="space-y-3">
      {rows.map((r: RetryPerformanceOut) => (
        <li
          key={`${r.retry_scenario}-${r.decline_reason_standard ?? "all"}-${r.retry_count}`}
          className="rounded-lg border border-border/60 p-3 space-y-2"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              <Repeat className="h-3 w-3 mr-1" />
              {r.retry_scenario}
            </Badge>
            <span className="font-mono text-sm">{r.decline_reason_standard ?? "All reasons"}</span>
            <Badge variant="outline">Attempt {r.retry_count}</Badge>
            <Badge className={r.success_rate_pct >= 50 ? "bg-green-600" : ""}>
              {r.success_rate_pct}% success
            </Badge>
            {r.incremental_lift_pct != null && (
              <Badge variant={r.incremental_lift_pct > 0 ? "default" : "destructive"}>
                {r.incremental_lift_pct > 0 ? "+" : ""}{r.incremental_lift_pct}% vs baseline
              </Badge>
            )}
            <Badge variant="outline">{r.effectiveness}</Badge>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>Recovered ${r.recovered_value.toFixed(2)}</span>
            <span>Avg fraud score {r.avg_fraud_score.toFixed(3)}</span>
            {r.avg_time_since_last_attempt_s != null && (
              <span>Avg wait {Math.round(r.avg_time_since_last_attempt_s)}s</span>
            )}
            {r.avg_prior_approvals != null && (
              <span>Prior approvals {r.avg_prior_approvals.toFixed(1)}</span>
            )}
          </div>
          <div className="flex justify-end">
            <Badge variant="secondary">{r.retry_attempts} retries</Badge>
          </div>
        </li>
      ))}
    </ul>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4].map((i) => (
        <Skeleton key={i} className="h-20 w-full rounded-lg" />
      ))}
    </div>
  );
}

/* ----- Main Page ----- */
function SmartRetry() {
  return (
    <div className="space-y-8">
      {/* Hero */}
      <div>
        <h1 className="text-2xl font-bold font-heading tracking-tight text-foreground">
          Smart Retry
        </h1>
        <p className="mt-1 text-sm font-medium text-muted-foreground">
          Recurrence & reattempts · Recover more approvals through intelligent retry strategies
        </p>
      </div>

      {/* KPI Cards */}
      <Suspense fallback={<KPISkeleton />}>
        <RetryKPIs />
      </Suspense>

      {/* Two Scenarios */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Two scenarios in scope</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Smart Retry addresses both recurring payments and one-off retries after a decline.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          {SCENARIOS.map((s) => {
            const Icon = s.icon;
            return (
              <Card key={s.id} className="border-border/80">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Icon className="h-4 w-4 text-primary" />
                    {s.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{s.desc}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Performance Charts */}
      <section>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              Retry Performance Overview
            </CardTitle>
            <CardDescription>
              Success rate and recovered value aggregated by retry scenario from Databricks.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Suspense fallback={<ChartSkeleton />}>
              <RetryPerformanceChart />
            </Suspense>
          </CardContent>
        </Card>
      </section>

      {/* Top retry cohorts */}
      <section>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Top Retry Cohorts
            </CardTitle>
            <CardDescription>
              Performance by scenario, decline reason, and attempt number. Success rate, incremental lift vs baseline, and recovered value.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Suspense fallback={<ListSkeleton />}>
              <RetryCohorts />
            </Suspense>
          </CardContent>
        </Card>
        <Button variant="outline" size="sm" className="mt-3 gap-2" onClick={() => openInDatabricks(getLakeviewDashboardUrl("routing_optimization"))}>
          Open routing dashboard <ExternalLink className="h-3.5 w-3.5" />
        </Button>
      </section>
    </div>
  );
}
