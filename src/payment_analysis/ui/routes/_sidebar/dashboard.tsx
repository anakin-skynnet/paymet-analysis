import { Suspense } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGetKpisSuspense,
  useGetApprovalTrendsSuspense,
  useGetSolutionPerformanceSuspense,
  useRecentDecisionsSuspense,
} from "@/lib/api";
import selector from "@/lib/selector";
import { friendlyReason } from "@/lib/reasoning";
import {
  ExternalLink,
  Code2,
  TrendingUp,
  Database,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  MessageSquareText,
  Cpu,
} from "lucide-react";
import { getDashboardUrl, getGenieUrl } from "@/config/workspace";

const openInDatabricks = (url: string) => {
  if (url) window.open(url, "_blank");
};

export const Route = createFileRoute("/_sidebar/dashboard")({
  component: () => (
    <Suspense fallback={<DashboardSkeleton />}>
      <Dashboard />
    </Suspense>
  ),
});

const openNotebook = async (notebookId: string) => {
  try {
    const response = await fetch(`/api/notebooks/notebooks/${notebookId}/url`);
    const data = await response.json();
    window.open(data.url, "_blank");
  } catch (error) {
    console.error("Failed to open notebook:", error);
  }
};

const openDashboard = () => {
  const dashboardUrl = getDashboardUrl("/sql/dashboards/executive_overview");
  window.open(dashboardUrl, "_blank");
};

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96 mt-2" />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-36" />
          </CardHeader>
          <CardContent className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-48" />
          </CardHeader>
          <CardContent className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-56" />
          <Skeleton className="h-4 w-full mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function formatDecisionTime(iso: string | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffM = Math.floor(diffMs / 60000);
  if (diffM < 1) return "Just now";
  if (diffM < 60) return `${diffM}m ago`;
  const diffH = Math.floor(diffM / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function Dashboard() {
  const { data: kpis } = useGetKpisSuspense(selector());
  const { data: trends } = useGetApprovalTrendsSuspense(selector());
  const { data: solutions } = useGetSolutionPerformanceSuspense(selector());
  const { data: decisions } = useRecentDecisionsSuspense({
    params: { limit: 20 },
  });

  const pct = (kpis.approval_rate * 100).toFixed(2);
  const decisionList = decisions?.data ?? [];
  const getReason = (log: { response?: Record<string, unknown> }) =>
    friendlyReason(log.response?.reason as string);
  const getVariant = (log: { response?: Record<string, unknown> }) =>
    log.response?.variant as string | undefined;
  const getPath = (log: { response?: Record<string, unknown> }) =>
    log.response?.path as string | undefined;
  const getRiskTier = (log: { response?: Record<string, unknown> }) =>
    log.response?.risk_tier as string | undefined;

  return (
    <div className="space-y-6">
      {/* Header with Links */}
      <div>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h1 className="text-2xl font-semibold">Approval performance</h1>
          <div className="flex gap-2 flex-wrap">
            <Button variant="outline" size="sm" onClick={openDashboard}>
              <TrendingUp className="w-4 h-4 mr-2" />
              Executive Dashboard
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebook("gold_views_sql")}
            >
              <Database className="w-4 h-4 mr-2" />
              SQL Views
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebook("realtime_pipeline")}
            >
              <Code2 className="w-4 h-4 mr-2" />
              Lakeflow
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          KPIs, approval trends, and Lakehouse data (online features, recommendations). After Setup steps 1–6, data appears here.
        </p>
      </div>

      {/* KPI Cards — click opens Executive dashboard in Databricks */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total auths
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {kpis.total.toLocaleString()}
            </p>
          </CardContent>
        </Card>
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Approved
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {kpis.approved.toLocaleString()}
            </p>
          </CardContent>
        </Card>
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Approval rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{pct}%</p>
          </CardContent>
        </Card>
      </div>

      {/* Trends + Solutions */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Approval Trends — click opens Daily Trends dashboard */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/daily_trends"))}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/daily_trends"))}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Approval Trends (Hourly)
            </CardTitle>
            <CardDescription>
              Transaction volume and approval rates by hour
            </CardDescription>
          </CardHeader>
          <CardContent>
            {trends.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No trend data available yet.
              </p>
            ) : (
              <div className="space-y-3">
                {trends.slice(0, 8).map((t) => (
                  <div
                    key={t.hour}
                    className="flex items-center justify-between"
                  >
                    <span className="text-sm font-mono w-20 shrink-0">
                      {t.hour}
                    </span>
                    <div className="flex-1 mx-3">
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className="bg-primary rounded-full h-2 transition-all"
                          style={{
                            width: `${Math.min(t.approval_rate_pct, 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant="outline" className="font-mono text-xs">
                        {t.approval_rate_pct.toFixed(1)}%
                      </Badge>
                      <span className="text-xs text-muted-foreground w-16 text-right">
                        {t.transaction_count.toLocaleString()} txn
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Solution Performance — click opens Smart Routing dashboard */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Solution Performance
            </CardTitle>
            <CardDescription>
              Approval rates by payment solution
            </CardDescription>
          </CardHeader>
          <CardContent>
            {solutions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No solution data available yet.
              </p>
            ) : (
              <div className="space-y-3">
                {solutions.map((s) => (
                  <div
                    key={s.payment_solution}
                    className="flex items-center justify-between"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {s.payment_solution}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {s.transaction_count.toLocaleString()} transactions
                        &middot; avg ${s.avg_amount.toFixed(2)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-3 shrink-0">
                      {s.approval_rate_pct >= 80 ? (
                        <ArrowUpRight className="w-3 h-3 text-green-600" />
                      ) : (
                        <ArrowDownRight className="w-3 h-3 text-red-500" />
                      )}
                      <Badge
                        variant={
                          s.approval_rate_pct >= 80
                            ? "default"
                            : s.approval_rate_pct >= 60
                              ? "secondary"
                              : "destructive"
                        }
                      >
                        {s.approval_rate_pct.toFixed(1)}%
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Online features (Lakehouse) — from ML and AI processes */}
      <OnlineFeaturesCard />

      {/* ML & decision reasoning — click opens Genie in Databricks */}
      <Card
        className="cursor-pointer hover:shadow-md transition-shadow"
        onClick={() => openInDatabricks(getGenieUrl())}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getGenieUrl())}
      >
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareText className="w-4 h-4" />
            ML & decision reasoning
          </CardTitle>
          <CardDescription>
            Recent policy and model reasoning from authentication, retry, and routing decisions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {decisionList.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No recent decisions. Use the Decisioning playground to generate decisions and reasoning.
            </p>
          ) : (
            <ul className="space-y-4">
              {decisionList.slice(0, 15).map((log) => {
                const reason = getReason(log);
                const variant = getVariant(log);
                const path = getPath(log);
                const riskTier = getRiskTier(log);
                return (
                  <li key={log.audit_id ?? log.id ?? Math.random()} className="border-b border-border/60 pb-4 last:border-0 last:pb-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <Badge variant="secondary" className="font-mono text-xs">
                        {log.decision_type}
                      </Badge>
                      {(variant ?? path ?? riskTier) && (
                        <span className="text-xs text-muted-foreground">
                          {[variant && `A/B: ${variant}`, path, riskTier].filter(Boolean).join(" · ")}
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground ml-auto">
                        {formatDecisionTime(log.created_at)}
                      </span>
                    </div>
                    <p className="text-sm text-foreground">{reason}</p>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

type OnlineFeature = {
  id: string;
  source: string;
  feature_set?: string | null;
  feature_name: string;
  feature_value?: number | null;
  feature_value_str?: string | null;
  entity_id?: string | null;
  created_at?: string | null;
};

async function fetchOnlineFeatures(limit = 50): Promise<OnlineFeature[]> {
  const res = await fetch(`/api/analytics/online-features?limit=${limit}`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

function OnlineFeaturesCard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["/api/analytics/online-features", 50],
    queryFn: () => fetchOnlineFeatures(50),
  });
  const features = data ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Cpu className="w-4 h-4" />
          Online features (Lakehouse)
        </CardTitle>
        <CardDescription>
          Features from ML and AI stored in the Lakehouse (Setup step 5: run lakehouse_bootstrap.sql). Populate from jobs or decisioning.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        )}
        {isError && (
          <p className="text-sm text-destructive">Failed to load online features.</p>
        )}
        {!isLoading && !isError && features.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No features yet. Complete Setup step 5 (run lakehouse_bootstrap.sql), then populate from ML or agent jobs.
          </p>
        )}
        {!isLoading && !isError && features.length > 0 && (
          <ul className="space-y-2">
            {features.slice(0, 20).map((f) => (
              <li key={f.id} className="flex flex-wrap items-center gap-2 rounded border px-3 py-2 text-sm">
                <Badge variant={f.source === "ml" ? "default" : "secondary"}>{f.source}</Badge>
                {f.feature_set && <span className="text-muted-foreground">{f.feature_set}</span>}
                <span className="font-medium">{f.feature_name}</span>
                {f.feature_value != null && <span className="text-muted-foreground">= {f.feature_value}</span>}
                {f.feature_value_str != null && <span className="text-muted-foreground">= {f.feature_value_str}</span>}
                {f.entity_id && <span className="text-xs text-muted-foreground truncate">({f.entity_id})</span>}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
