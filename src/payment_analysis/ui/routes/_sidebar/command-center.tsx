import { Suspense } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGetKpisSuspense,
  useGetLastHourPerformance,
  useGetSolutionPerformanceSuspense,
  useGetApprovalTrendsSuspense,
  useDeclineSummary,
  useGetDataQualitySummary,
  useHealthDatabricks,
  useGetDashboardUrl,
} from "@/lib/api";
import selector from "@/lib/selector";
import { getDashboardUrl, getWorkspaceUrl, openInDatabricks } from "@/config/workspace";
import { GetnetAIAssistant, AgentOrchestratorChat } from "@/components/chat";
import {
  Lock,
  Activity,
  Target,
  Globe,
  AlertTriangle,
  CheckCircle2,
  Gauge,
  Download,
  FileText,
  Share2,
  RefreshCw,
} from "lucide-react";

/** Active alert from backend (Databricks v_active_alerts or mock). */
export interface ActiveAlertOut {
  alert_type: string;
  severity: string;
  metric_name: string;
  current_value: number;
  threshold_value: number;
  alert_message: string;
  first_detected: string;
}

async function fetchActiveAlerts(): Promise<ActiveAlertOut[]> {
  const res = await fetch("/api/analytics/active-alerts?limit=20");
  if (!res.ok) return [];
  return res.json();
}

function useActiveAlerts() {
  return useQuery({
    queryKey: ["/api/analytics/active-alerts"],
    queryFn: fetchActiveAlerts,
  });
}

export const Route = createFileRoute("/_sidebar/command-center")({
  component: () => (
    <Suspense fallback={<CommandCenterSkeleton />}>
      <CommandCenter />
    </Suspense>
  ),
});

function CommandCenterSkeleton() {
  return (
    <div className="space-y-6 p-4">
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-64 lg:col-span-2" />
        <div className="space-y-4">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    </div>
  );
}

function CommandCenter() {
  const { data: kpis } = useGetKpisSuspense(selector());
  const lastHourQ = useGetLastHourPerformance();
  const { data: solutions } = useGetSolutionPerformanceSuspense(selector());
  const { data: trends } = useGetApprovalTrendsSuspense({ params: { hours: 30 * 24 } });
  const declineQ = useDeclineSummary({ params: { limit: 5 } });
  const dataQualityQ = useGetDataQualitySummary();
  const { data: healthData } = useHealthDatabricks();
  const alertsQ = useActiveAlerts();
  const { data: embedUrlData } = useGetDashboardUrl({
    params: { dashboard_id: "executive_overview", embed: true },
    query: { enabled: true },
  });

  const fromDatabricks = healthData?.data?.analytics_source === "Unity Catalog";
  const approvalPct = kpis ? (kpis.approval_rate * 100).toFixed(1) : null;
  const declineRatePct = kpis ? ((1 - kpis.approval_rate) * 100).toFixed(1) : null;

  const lastHour = lastHourQ.data?.data;
  const eventsPerSecond =
    lastHour?.transactions_last_hour != null
      ? Math.round(lastHour.transactions_last_hour / 3600)
      : null;

  const routingEfficiency =
    solutions?.length && solutions[0]
      ? solutions.reduce((sum, s) => sum + s.approval_rate_pct * s.transaction_count, 0) /
        Math.max(
          1,
          solutions.reduce((sum, s) => sum + s.transaction_count, 0)
        )
      : null;

  const trendData = trends?.data ?? [];
  const topDeclines = declineQ.data?.data ?? [];
  const dataQuality = dataQualityQ.data?.data;
  const retentionPct = dataQuality?.retention_pct_24h;
  const alerts = alertsQ.data ?? [];

  const iframeSrc =
    embedUrlData?.data?.full_embed_url ??
    (embedUrlData?.data?.embed_url && getWorkspaceUrl()
      ? `${getWorkspaceUrl()}${embedUrlData.data.embed_url as string}`
      : null);

  const lastUpdated = new Date().toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });

  return (
    <div className="flex min-h-full flex-col bg-background">
      <main className="flex-1 space-y-6 p-4 md:p-6">
        {/* Top: Strategic KPIs — Gross Approval Rate, False Decline Rate (reference layout) */}
        <section aria-labelledby="kpi-heading" className="grid gap-4 md:grid-cols-2">
          <h2 id="kpi-heading" className="sr-only">
            Strategic metrics
          </h2>
          <Card className="border-2 border-green-500/50 bg-green-500/10 dark:bg-green-500/15">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">
                  Gross Approval Rate
                </span>
                <Lock className="h-4 w-4 text-muted-foreground" aria-hidden />
              </div>
              <p className="mt-2 text-4xl font-bold text-green-600 dark:text-green-400 tabular-nums">
                {approvalPct ?? "—"}%
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                From Databricks executive KPIs · Portfolio approval rate
              </p>
            </CardContent>
          </Card>
          <Card className="border-2 border-orange-500/50 bg-orange-500/10 dark:bg-orange-500/15">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">
                  False Decline Rate
                </span>
                <Lock className="h-4 w-4 text-muted-foreground" aria-hidden />
              </div>
              <p className="mt-2 text-4xl font-bold text-orange-600 dark:text-orange-400 tabular-nums">
                {declineRatePct ?? "—"}%
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Quarterly trend · From Databricks Unity Catalog
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Main content: embedded Databricks dashboard (left) + Alerts & Control Panel (right) */}
        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          {/* Embedded Databricks dashboard — all dashboards from Databricks via iframe */}
          <Card className="min-h-[420px] overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Executive Overview — Databricks AI/BI
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 h-[400px] md:h-[480px]">
              {iframeSrc ? (
                <iframe
                  title="Executive Overview Dashboard"
                  src={String(iframeSrc)}
                  className="w-full h-full border-0 rounded-b-lg"
                  allowFullScreen
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full rounded-lg bg-muted/30 text-center p-6">
                  <p className="text-sm text-muted-foreground mb-2">
                    Dashboard embed requires Databricks workspace connection.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
                  >
                    Open Executive Overview in Databricks
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right column: Alerts + Control Panel */}
          <div className="space-y-4 flex flex-col">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                {alertsQ.isLoading ? (
                  <Skeleton className="h-24 w-full" />
                ) : alerts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No active alerts.</p>
                ) : (
                  <ul className="space-y-2">
                    {alerts.slice(0, 8).map((a, i) => (
                      <li
                        key={`${a.alert_type}-${i}`}
                        className="flex items-start gap-2 text-sm"
                      >
                        <span
                          className={`inline-block w-2 h-2 rounded-full shrink-0 mt-1.5 ${
                            a.severity === "CRITICAL" ? "bg-destructive" : "bg-orange-500"
                          }`}
                          aria-hidden
                        />
                        <span className="text-muted-foreground line-clamp-2">
                          {a.alert_message}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Control Panel</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start gap-2"
                  onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
                >
                  <FileText className="h-4 w-4" />
                  Report generation
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start gap-2"
                  onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"))}
                >
                  <Download className="h-4 w-4" />
                  Download all data
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start gap-2"
                  onClick={() => window.navigator.clipboard.writeText(window.location.href)}
                >
                  <Share2 className="h-4 w-4" />
                  Share link
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start gap-2" asChild>
                  <Link to="/decisioning">
                    <RefreshCw className="h-4 w-4" />
                    Recalculate Routing
                  </Link>
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start gap-2" asChild>
                  <Link to="/setup">
                    <Target className="h-4 w-4" />
                    Control panel — jobs &amp; pipelines
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Secondary row: Real-Time Ingestion, Routing Efficiency, Data Quality */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Real-Time Ingestion
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums text-primary">
                {eventsPerSecond != null ? eventsPerSecond.toLocaleString() : "—"}
              </p>
              <p className="text-xs text-muted-foreground">
                Avg events/sec (last hour)
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Target className="h-4 w-4" />
                Routing Efficiency
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <div
                  className="h-14 w-14 rounded-full border-2 border-muted flex items-center justify-center text-lg font-bold tabular-nums"
                  style={{
                    background: `conic-gradient(hsl(var(--primary)) 0% ${routingEfficiency ?? 0}%, hsl(var(--muted)) ${routingEfficiency ?? 0}% 100%)`,
                  }}
                >
                  <span className="bg-background rounded-full h-10 w-10 flex items-center justify-center text-sm">
                    {routingEfficiency != null ? `${routingEfficiency.toFixed(1)}%` : "—"}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">Target &gt;98%</span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Gauge className="h-4 w-4" />
                Data Quality
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dataQualityQ.isLoading ? (
                <Skeleton className="h-10 w-20" />
              ) : (
                <ul className="space-y-1 text-sm">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                    <span>Retention 24h: {retentionPct != null ? `${Math.min(100, retentionPct).toFixed(1)}%` : "—"}</span>
                  </li>
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Mini trend + top declines */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Approval trends (last 30 days)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-16 flex items-end gap-0.5">
                {trendData
                  .filter((_, i) => i % 24 === 0)
                  .slice(0, 30)
                  .reverse()
                  .map((t) => (
                    <div
                      key={t.hour}
                      className="flex-1 min-w-0 rounded-t bg-primary/70"
                      style={{
                        height: `${Math.min(100, (t.approval_rate_pct ?? 0) * 1.2)}%`,
                      }}
                      title={`${t.hour}: ${t.approval_rate_pct?.toFixed(1)}%`}
                    />
                  ))}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Top decline reasons</CardTitle>
            </CardHeader>
            <CardContent>
              {declineQ.isLoading ? (
                <Skeleton className="h-20" />
              ) : topDeclines.length === 0 ? (
                <p className="text-sm text-muted-foreground">No decline data yet.</p>
              ) : (
                <div className="flex gap-2 items-end">
                  {topDeclines.slice(0, 5).map((d) => (
                    <div
                      key={d.key}
                      className="flex-1 min-w-0 rounded-t bg-primary/80"
                      style={{
                        height: `${Math.min(60, (d.pct_of_declines ?? 0) * 1.5)}px`,
                      }}
                      title={`${d.key}: ${d.pct_of_declines?.toFixed(1)}%`}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>

      <footer className="flex items-center justify-between border-t border-border/80 px-4 py-2 text-xs text-muted-foreground">
        <span>Last update: {lastUpdated}</span>
        <span className="flex items-center gap-3">
          {fromDatabricks ? (
            <span
              className="inline-flex items-center gap-1 rounded bg-green-500/10 text-green-700 dark:text-green-400 px-2 py-0.5"
              title="All numbers and dashboards from Databricks Unity Catalog"
            >
              Data: Databricks
            </span>
          ) : (
            <span
              className="inline-flex items-center gap-1 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 px-2 py-0.5"
              title="Sample or fallback data when Databricks is not connected"
            >
              Data: Sample
            </span>
          )}
          <a
            href="#feedback"
            className="hover:text-foreground underline underline-offset-2"
          >
            feedback
          </a>
        </span>
      </footer>

      <GetnetAIAssistant />
      <AgentOrchestratorChat />
    </div>
  );
}
