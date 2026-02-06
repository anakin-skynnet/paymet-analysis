import { Suspense } from "react";
import { createFileRoute } from "@tanstack/react-router";
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
} from "@/lib/api";
import selector from "@/lib/selector";
import {
  ExternalLink,
  Code2,
  TrendingUp,
  Database,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { getDashboardUrl } from "@/config/workspace";

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
    </div>
  );
}

function Dashboard() {
  const { data: kpis } = useGetKpisSuspense(selector());
  const { data: trends } = useGetApprovalTrendsSuspense(selector());
  const { data: solutions } = useGetSolutionPerformanceSuspense(selector());

  const pct = (kpis.approval_rate * 100).toFixed(2);

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
              DLT Pipeline
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          Real-time KPIs from Unity Catalog via Lakeflow Declarative Pipeline
          streaming
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
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
        <Card>
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
        <Card>
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
        {/* Approval Trends */}
        <Card>
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

        {/* Solution Performance */}
        <Card>
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
    </div>
  );
}
