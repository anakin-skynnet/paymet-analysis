import { createFileRoute, Link } from "@tanstack/react-router";
import { Suspense } from "react";

import {
  useDeclineSummarySuspense,
  useGetReasonCodeInsightsSuspense,
  useGetFactorsDelayingApprovalSuspense,
  useGetKpisSuspense,
  useGetDeclineRecoveryOpportunitiesSuspense,
  useGetCardNetworkPerformanceSuspense,
  type ReasonCodeInsightOut,
  type DeclineBucketOut,
} from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  DollarSign,
  CreditCard,
  RefreshCw,
} from "lucide-react";
import { Bar, BarChart, XAxis, YAxis, CartesianGrid, Cell } from "recharts";
import { getLakeviewDashboardUrl, openInDatabricks } from "@/config/workspace";
import { openNotebookInDatabricks } from "@/lib/notebooks";
import { useEntity } from "@/contexts/entity-context";

export const Route = createFileRoute("/_sidebar/declines")({
  component: () => <Declines />,
});

const openDashboard = () => {
  openInDatabricks(getLakeviewDashboardUrl("decline_analysis"));
};

/** Refresh analytics from backend/Databricks every 15s for real-time feel. */
const REFRESH_ANALYTICS_MS = 15_000;

const DECLINE_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
  "hsl(220 70% 50%)",
  "hsl(340 75% 55%)",
  "hsl(30 80% 55%)",
];

const declineChartConfig = {
  count: { label: "Declines", color: "var(--color-chart-1)" },
} satisfies ChartConfig;

const factorsChartConfig = {
  decline_count: { label: "Decline Count", color: "var(--color-chart-2)" },
} satisfies ChartConfig;

/* ----- KPI Header (Suspense-wrapped) ----- */
function DeclineKPIs() {
  const { data: kpisResp } = useGetKpisSuspense();
  const kpis = kpisResp?.data;
  const total = kpis?.total ?? 0;
  const approved = kpis?.approved ?? 0;
  const declined = total - approved;
  const declineRate = total > 0 ? ((declined / total) * 100).toFixed(1) : "0.0";
  const approvalRate = kpis?.approval_rate != null ? (kpis.approval_rate * 100).toFixed(1) : "—";

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
          <Bar dataKey="decline_count" fill="var(--color-chart-2)" radius={[4, 4, 0, 0]} />
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

/* ----- Recovery Opportunities (Suspense-wrapped, real Databricks data) ----- */
function RecoveryOpportunities() {
  const { data: resp } = useGetDeclineRecoveryOpportunitiesSuspense({
    params: { limit: 10 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const opportunities = (resp?.data ?? []) as Array<Record<string, unknown>>;

  if (opportunities.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No recovery opportunity data yet. Run gold views and the ETL pipeline to identify recoverable transactions.
      </p>
    );
  }

  const totalRecoverable = opportunities.reduce(
    (sum, o) => sum + (Number(o.potential_recovery_value ?? o.recoverable_amount ?? o.estimated_recovery ?? 0)),
    0,
  );
  const totalTransactions = opportunities.reduce(
    (sum, o) => sum + (Number(o.transaction_count ?? o.decline_count ?? 0)),
    0,
  );

  return (
    <div className="space-y-4">
      {/* Summary KPIs */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex items-center gap-3 rounded-lg border border-green-200 dark:border-green-900 bg-green-500/5 p-3">
          <DollarSign className="h-5 w-5 text-green-600 dark:text-green-400 shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">Estimated Recoverable</p>
            <p className="text-lg font-bold text-green-600 dark:text-green-400">
              ${totalRecoverable.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg border border-border p-3">
          <RefreshCw className="h-5 w-5 text-primary shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">Recoverable Transactions</p>
            <p className="text-lg font-bold">{totalTransactions.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Opportunities Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Decline Reason</TableHead>
            <TableHead className="text-right">Count</TableHead>
            <TableHead className="text-right">Recoverable</TableHead>
            <TableHead>Strategy</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {opportunities.slice(0, 8).map((o, i) => {
            const reason = String(o.decline_reason ?? o.reason_code ?? o.category ?? `Group ${i + 1}`);
            const count = Number(o.transaction_count ?? o.decline_count ?? 0);
            const amount = Number(o.potential_recovery_value ?? o.recoverable_amount ?? o.estimated_recovery ?? 0);
            const strategy = String(o.recovery_strategy ?? o.recommended_action ?? o.strategy ?? "Smart Retry");
            return (
              <TableRow key={`${reason}-${i}`}>
                <TableCell className="font-medium text-sm">{reason}</TableCell>
                <TableCell className="text-right tabular-nums">{count.toLocaleString()}</TableCell>
                <TableCell className="text-right tabular-nums text-green-600 dark:text-green-400">
                  ${amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs">{strategy}</Badge>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

/* ----- Card Network Performance (Suspense-wrapped, real Databricks data) ----- */
function CardNetworkPerformance() {
  const { data: resp } = useGetCardNetworkPerformanceSuspense({
    params: { limit: 10 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const networks = (resp?.data ?? []) as Array<Record<string, unknown>>;

  if (networks.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No card network data yet. Run gold views and the ETL pipeline to see performance by network.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {networks.slice(0, 6).map((n, i) => {
        const network = String(n.card_network ?? n.network ?? n.name ?? `Network ${i + 1}`);
        const approvalRate = Number(n.approval_rate_pct ?? n.approval_rate ?? n.approval_pct ?? 0);
        const volume = Number(n.transaction_count ?? n.total_transactions ?? n.volume ?? 0);
        const isTop = i === 0;
        return (
          <div key={`${network}-${i}`} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <CreditCard className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="font-medium">{network}</span>
                {isTop && <Badge variant="default" className="text-[10px] px-1.5 py-0">Top</Badge>}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground tabular-nums">{volume.toLocaleString()} txns</span>
                <span className={`font-semibold tabular-nums ${approvalRate >= 90 ? "text-green-600 dark:text-green-400" : approvalRate >= 80 ? "text-yellow-600 dark:text-yellow-400" : "text-destructive"}`}>
                  {approvalRate.toFixed(1)}%
                </span>
              </div>
            </div>
            <Progress value={approvalRate} className="h-2" />
          </div>
        );
      })}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-2 py-2">
      {[1, 2, 3, 4].map((i) => (
        <Skeleton key={i} className="h-10 w-full rounded" />
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

      {/* Recovery Opportunities + Card Network Performance — side by side */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-green-600 dark:text-green-400" />
              Recovery Opportunities
            </CardTitle>
            <CardDescription>
              Declined transactions with high recovery potential. Estimated revenue recoverable through smart retry and routing optimization.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Suspense fallback={<TableSkeleton />}>
              <RecoveryOpportunities />
            </Suspense>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-primary" />
              Approval Rate by Card Network
            </CardTitle>
            <CardDescription>
              Compare approval rates across card networks. Identify underperforming networks for targeted optimization.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Suspense fallback={<ListSkeleton />}>
              <CardNetworkPerformance />
            </Suspense>
          </CardContent>
        </Card>
      </div>

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
