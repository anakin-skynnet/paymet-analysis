import { createFileRoute, Link } from "@tanstack/react-router";
import { Suspense } from "react";

import {
  useDeclineSummarySuspense,
  useGetReasonCodeInsightsSuspense,
  useGetFactorsDelayingApprovalSuspense,
  useGetKpisSuspense,
  type ReasonCodeInsightOut,
  type DeclineBucketOut,
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
  Code2,
  TrendingDown,
  Target,
  ArrowRight,
  AlertCircle,
  BarChart3,
  Lightbulb,
} from "lucide-react";
import { Bar, BarChart, XAxis, YAxis, CartesianGrid, Cell } from "recharts";
import { getDashboardUrl, openInDatabricks } from "@/config/workspace";
import { openNotebookInDatabricks } from "@/lib/notebooks";
import { useEntity } from "@/contexts/entity-context";

export const Route = createFileRoute("/_sidebar/declines")({
  component: () => <Declines />,
});

const openDashboard = () => {
  openInDatabricks(getDashboardUrl("/sql/dashboards/decline_analysis"));
};

/** Refresh analytics from backend/Databricks every 15s for real-time feel. */
const REFRESH_ANALYTICS_MS = 15_000;

const DECLINE_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(220 70% 50%)",
  "hsl(340 75% 55%)",
  "hsl(30 80% 55%)",
];

const declineChartConfig = {
  count: { label: "Declines", color: "hsl(var(--chart-1))" },
} satisfies ChartConfig;

const factorsChartConfig = {
  decline_count: { label: "Decline Count", color: "hsl(var(--chart-2))" },
} satisfies ChartConfig;

/* ----- KPI Header (Suspense-wrapped) ----- */
function DeclineKPIs() {
  const { data: kpisResp } = useGetKpisSuspense();
  const kpis = kpisResp?.data;
  const total = kpis?.total ?? 0;
  const approved = kpis?.approved ?? 0;
  const declined = total - approved;
  const declineRate = total > 0 ? ((declined / total) * 100).toFixed(1) : "0.0";
  const approvalRate = kpis?.approval_rate != null ? kpis.approval_rate.toFixed(1) : "—";

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Total Transactions</p>
          <p className="text-2xl font-bold">{total.toLocaleString()}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Declined</p>
          <p className="text-2xl font-bold text-destructive">{declined.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">{declineRate}% decline rate</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Approval Rate</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{approvalRate}%</p>
        </CardContent>
      </Card>
    </div>
  );
}

function KPISkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {[1, 2, 3].map((i) => (
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

/* ----- Decline Buckets Chart (Suspense-wrapped) ----- */
function DeclineBucketsChart() {
  const { data: resp } = useDeclineSummarySuspense();
  const buckets: DeclineBucketOut[] = resp?.data ?? [];

  if (buckets.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No decline data yet. Run the simulator and ETL pipeline to populate decline buckets.
      </p>
    );
  }

  const chartData = buckets.slice(0, 8).map((b, i) => ({
    reason: b.key.length > 20 ? b.key.slice(0, 18) + "…" : b.key,
    fullReason: b.key,
    count: b.count,
    fill: DECLINE_COLORS[i % DECLINE_COLORS.length],
  }));

  return (
    <div className="space-y-4">
      <ChartContainer config={declineChartConfig} className="h-[300px] w-full">
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20 }}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" />
          <YAxis dataKey="reason" type="category" width={130} tick={{ fontSize: 11 }} />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(_v, payload) => {
                  const item = payload?.[0]?.payload;
                  return item?.fullReason ?? _v;
                }}
              />
            }
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ChartContainer>

      {/* Legend below chart */}
      <div className="flex flex-wrap gap-2">
        {buckets.map((b) => (
          <div key={b.key} className="flex items-center gap-1.5">
            <span className="font-mono text-xs">{b.key}</span>
            <Badge variant="secondary" className="text-xs">{b.count}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="space-y-3 py-2">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-5 w-28" />
          <Skeleton className="h-5 flex-1" style={{ maxWidth: `${90 - i * 12}%` }} />
        </div>
      ))}
    </div>
  );
}

/* ----- Factors Delaying Approval (Suspense-wrapped) ----- */
function FactorsDelayingApproval() {
  const { entity } = useEntity();
  const { data: factorsResp } = useGetFactorsDelayingApprovalSuspense({
    params: { entity, limit: 8 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const factors = factorsResp?.data ?? [];

  if (factors.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No factor data yet. Run gold views and the ETL pipeline to identify factors delaying approval.
      </p>
    );
  }

  const chartData = factors.map((f: ReasonCodeInsightOut) => ({
    factor: (f.decline_reason_standard ?? "Unknown").slice(0, 20),
    decline_count: f.decline_count ?? 0,
  }));

  return (
    <div className="space-y-4">
      <ChartContainer config={factorsChartConfig} className="h-[250px] w-full">
        <BarChart data={chartData} margin={{ left: 10, right: 20 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" />
          <XAxis dataKey="factor" tick={{ fontSize: 10 }} height={50} />
          <YAxis tick={{ fontSize: 11 }} />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Bar dataKey="decline_count" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ChartContainer>

      <ul className="space-y-2">
        {factors.slice(0, 5).map((f: ReasonCodeInsightOut) => (
          <li key={`${f.entry_system}-${f.decline_reason_standard}-${f.priority}`} className="rounded-lg border border-border/60 p-2.5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">{f.decline_reason_standard}</p>
              <Badge variant="secondary">{f.decline_count.toLocaleString()}</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{f.recommended_action}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ----- Recommended Actions (Suspense-wrapped) ----- */
function RecommendedActions() {
  const { entity } = useEntity();
  const { data: reasonCodeResp } = useGetReasonCodeInsightsSuspense({
    params: { entity, limit: 5 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const recommendedActions = reasonCodeResp?.data ?? [];

  if (recommendedActions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No reason-code insights yet. Run gold views and open Reason Codes for full insights.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {recommendedActions.map((r: ReasonCodeInsightOut) => (
        <li key={`${r.entry_system}-${r.decline_reason_standard}-${r.priority}`} className="rounded-lg border border-border/60 p-2.5">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-3.5 h-3.5 text-yellow-500 shrink-0" />
            <p className="text-sm font-medium">{r.decline_reason_standard}</p>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 ml-5.5">{r.recommended_action}</p>
        </li>
      ))}
    </ul>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-14 w-full rounded-lg" />
      ))}
    </div>
  );
}

/* ----- Main Page ----- */
function Declines() {
  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold font-heading">Declines</h1>
          <p className="mt-1 text-sm font-medium text-primary">
            Discover conditions and factors delaying approvals
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Decline patterns and recovery insights from Databricks. Use charts below to identify top issues and recommended actions to accelerate approval rates.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={openDashboard}>
            <TrendingDown className="w-4 h-4 mr-2" />
            Decline Dashboard
            <ExternalLink className="w-3 h-3 ml-2" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => openNotebookInDatabricks("gold_views_sql")}
          >
            <Code2 className="w-4 h-4 mr-2" />
            SQL Views
            <ExternalLink className="w-3 h-3 ml-2" />
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <Suspense fallback={<KPISkeleton />}>
        <DeclineKPIs />
      </Suspense>

      {/* Decline Buckets Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-primary" />
            Top Decline Reasons
          </CardTitle>
          <CardDescription>
            Breakdown by reason code. Click the dashboard button to explore in Databricks.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<ChartSkeleton />}>
            <DeclineBucketsChart />
          </Suspense>
        </CardContent>
      </Card>

      {/* Factors Delaying Approval */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-orange-500" />
            Factors Delaying Approval
          </CardTitle>
          <CardDescription>
            Top conditions preventing transactions from being approved. Volume per factor and recommended actions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<ChartSkeleton />}>
            <FactorsDelayingApproval />
          </Suspense>
        </CardContent>
      </Card>

      {/* Recommended Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-4 h-4 text-primary" />
            Recommended Actions
          </CardTitle>
          <CardDescription>
            Actionable insights to accelerate approvals. Apply these via Decisioning for real-time auth/retry/routing.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Suspense fallback={<ListSkeleton />}>
            <RecommendedActions />
          </Suspense>
          <div className="flex flex-wrap gap-2 mt-3">
            <Button variant="outline" size="sm" asChild>
              <Link to="/reason-codes">Reason Codes <ArrowRight className="w-3 h-3 ml-1" /></Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/decisioning">Decisioning playground <ArrowRight className="w-3 h-3 ml-1" /></Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/smart-retry">Smart Retry <ArrowRight className="w-3 h-3 ml-1" /></Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
