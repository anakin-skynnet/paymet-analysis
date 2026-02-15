import { Suspense } from "react";
import type { CSSProperties } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  createIncident,
  listIncidentsKey,
  useListIncidents,
  useGetDataQualitySummary,
  useGetLastHourPerformance,
  useGetLast60SecondsPerformance,
  useGetStreamingTps,
  useGetActiveAlerts,
  type Incident,
} from "@/lib/api";
import { getLakeviewDashboardUrl, openInDatabricks } from "@/config/workspace";
import { openNotebookInDatabricks } from "@/lib/notebooks";
import {
  AlertTriangle,
  CheckCircle2,
  Code2,
  ExternalLink,
  Gauge,
  HelpCircle,
  Activity,
} from "lucide-react";

function DataQualityErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
  return (
    <Card className="glass-card border border-destructive/30 max-w-lg mx-auto mt-12">
      <CardContent className="py-8 text-center space-y-4">
        <Activity className="w-10 h-10 text-destructive mx-auto" />
        <h2 className="text-lg font-semibold">Failed to load Monitoring & Quality</h2>
        <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : "Unknown error"}</p>
        <Button onClick={resetErrorBoundary}>Try again</Button>
      </CardContent>
    </Card>
  );
}

export const Route = createFileRoute("/_sidebar/data-quality")({
  component: () => (
    <ErrorBoundary FallbackComponent={DataQualityErrorFallback}>
      <Suspense fallback={<DataQualitySkeleton />}>
        <DataQualityPage />
      </Suspense>
    </ErrorBoundary>
  ),
});

const REFRESH_MS = 5000;
const MONITORING_DASHBOARD_NAME = "realtime_monitoring";

function DataQualitySkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-64" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    </div>
  );
}

function IncidentRow({ inc }: { inc: Incident }) {
  const openInWorkspace = () => {
    const url = getLakeviewDashboardUrl(MONITORING_DASHBOARD_NAME);
    openInDatabricks(url);
  };
  return (
    <Card
      className="glass-card border border-border/80 cursor-pointer card-interactive"
      onClick={openInWorkspace}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && openInWorkspace()}
    >
      <CardHeader className="py-4">
        <CardTitle className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate">
              {inc.category} — {inc.key}
            </div>
            <div className="text-xs text-muted-foreground font-mono truncate">
              {inc.id}
            </div>
          </div>
          <div className="flex gap-2 items-center">
            <Badge variant="secondary">{inc.severity}</Badge>
            <Badge variant={inc.status === "open" ? "default" : "secondary"}>
              {inc.status}
            </Badge>
            <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden />
          </div>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">Click to open Real-Time Monitoring in Databricks</p>
      </CardHeader>
    </Card>
  );
}

function DataQualityPage() {
  const qc = useQueryClient();
  const [category, setCategory] = useState("mid_failure");
  const [key, setKey] = useState("MID=demo");

  const dataQualityQ = useGetDataQualitySummary({ query: { refetchInterval: REFRESH_MS } });
  const dataQuality = dataQualityQ.data?.data;
  const retentionPct = dataQuality?.retention_pct_24h;
  const dqScore = retentionPct != null ? Math.min(100, Math.round(retentionPct)) : null;

  const incidentsQ = useListIncidents({});
  const lastHourQ = useGetLastHourPerformance({ query: { refetchInterval: REFRESH_MS } });
  const last60sQ = useGetLast60SecondsPerformance({ query: { refetchInterval: REFRESH_MS } });
  const tpsQ = useGetStreamingTps({ params: { limit_seconds: 120 }, query: { refetchInterval: REFRESH_MS } });
  const alertsQ = useGetActiveAlerts({ params: { limit: 20 }, query: { refetchInterval: REFRESH_MS } });
  const activeAlerts = alertsQ.data?.data ?? [];
  const create = useMutation({
    mutationFn: () => createIncident({ category, key, severity: "medium", details: {} }),
    onSuccess: () => qc.invalidateQueries({ queryKey: listIncidentsKey() }),
  });

  const items = incidentsQ.data?.data ?? [];
  const lastHour = lastHourQ.data?.data;
  const last60s = last60sQ.data?.data;
  const eventsPerSec =
    lastHour?.transactions_last_hour != null ? Math.round(lastHour.transactions_last_hour / 3600) : null;
  const tpsPoints = tpsQ.data?.data ?? [];
  const latestTps = tpsPoints.length > 0 ? tpsPoints[tpsPoints.length - 1]?.records_per_second : null;
  const liveTps = latestTps ?? (last60s?.transactions_last_60s != null ? Math.round(last60s.transactions_last_60s / 60) : null) ?? eventsPerSec;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          Monitoring & Data Quality
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground" aria-label="What is this page?">
                <HelpCircle className="h-4 w-4" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-xs">
              Real-time monitoring, TPS, last-hour volume, data quality health, alerts, and incident tracking from Unity Catalog. Auto-refresh every 5s.
            </TooltipContent>
          </Tooltip>
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Live metrics, data quality health, alerts, and incidents in one place.
        </p>
      </div>

      {/* Real-time stats strip (from incidents) */}
      <section aria-labelledby="live-stats-heading">
        <h2 id="live-stats-heading" className="text-lg font-semibold mb-3">Live metrics</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Tooltip>
            <TooltipTrigger asChild>
              <Card className="glass-card border border-[var(--neon-cyan)]/20 cursor-help">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Activity className="h-4 w-4 text-[var(--neon-cyan)]" />
                    TPS (live)
                  </div>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-[var(--neon-cyan)]">
                    {tpsQ.isLoading && !last60sQ.data ? "—" : (liveTps ?? "—")}
                  </p>
                  <p className="text-xs text-muted-foreground">transactions/sec (real-time)</p>
                </CardContent>
              </Card>
            </TooltipTrigger>
            <TooltipContent>Live transactions per second from the streaming pipeline.</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Card className="glass-card border border-[var(--neon-cyan)]/20 cursor-help">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Activity className="h-4 w-4 text-[var(--neon-cyan)]" />
                    Last 60s (live)
                  </div>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-[var(--neon-cyan)]">
                    {last60sQ.isLoading ? "—" : (last60s?.transactions_last_60s?.toLocaleString() ?? "—")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    approval {last60s?.approval_rate_pct != null ? `${last60s.approval_rate_pct.toFixed(1)}%` : "—"}
                  </p>
                </CardContent>
              </Card>
            </TooltipTrigger>
            <TooltipContent>Real-time volume and approval rate from the last 60 seconds (v_last_60_seconds_performance).</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Card className="glass-card border border-border/80 cursor-help">
                <CardContent className="pt-4">
                  <div className="text-sm text-muted-foreground">Last hour volume</div>
                  <p className="mt-1 text-2xl font-bold tabular-nums">
                    {lastHourQ.isLoading ? "—" : (lastHour?.transactions_last_hour?.toLocaleString() ?? "—")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    approval {lastHour?.approval_rate_pct != null ? `${lastHour.approval_rate_pct.toFixed(1)}%` : "—"}
                  </p>
                </CardContent>
              </Card>
            </TooltipTrigger>
            <TooltipContent>Total transactions and approval rate in the last hour.</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Card className="glass-card border border-border/80 cursor-help">
                <CardContent className="pt-4">
                  <div className="text-sm text-muted-foreground">Incidents</div>
                  <p className="mt-1 text-2xl font-bold tabular-nums">{items.length}</p>
                  <p className="text-xs text-muted-foreground">open + resolved</p>
                </CardContent>
              </Card>
            </TooltipTrigger>
            <TooltipContent>Recorded incidents. Create new ones below for tracking.</TooltipContent>
          </Tooltip>
        </div>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Alerts & Data Quality Health (from alerts-data-quality) */}
        <Card className="glass-card border-2 border-[var(--neon-cyan)]/30">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Gauge className="h-4 w-4 text-[var(--neon-cyan)]" />
              Data Quality Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            {dataQualityQ.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : !dataQuality || (dataQuality.bronze_last_24h === 0 && dataQuality.silver_last_24h === 0 && dqScore == null) ? (
              <div className="flex h-32 items-center justify-center rounded-lg bg-muted/20 text-sm text-muted-foreground">
                No data quality metrics yet. Run the streaming pipeline to populate.
              </div>
            ) : (
              <>
                <div className="mb-4 flex items-center gap-3">
                  <div
                    className="gauge-conic-cyan h-16 w-16 rounded-full border-2 border-[var(--neon-cyan)]/50 flex items-center justify-center text-xl font-bold tabular-nums text-neon-cyan"
                    style={{ ["--gauge-pct"]: `${dqScore ?? 0}%` } as CSSProperties}
                  >
                    <span className="bg-card rounded-full h-12 w-12 flex items-center justify-center text-sm">
                      {dqScore != null ? `${dqScore}%` : "—"}
                    </span>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Freshness · Schema · PII masking (Unity Catalog)
                  </div>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      Retention (24h)
                    </span>
                    <span className="tabular-nums font-medium">
                      {retentionPct != null ? `${retentionPct.toFixed(1)}%` : "—"}
                    </span>
                  </li>
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      Bronze (24h)
                    </span>
                    <span className="tabular-nums font-medium">
                      {dataQuality?.bronze_last_24h != null ? dataQuality.bronze_last_24h.toLocaleString() : "—"}
                    </span>
                  </li>
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      Silver (24h)
                    </span>
                    <span className="tabular-nums font-medium">
                      {dataQuality?.silver_last_24h != null ? dataQuality.silver_last_24h.toLocaleString() : "—"}
                    </span>
                  </li>
                </ul>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => openInDatabricks(getLakeviewDashboardUrl("streaming_data_quality"))}
                >
                  Data Quality Dashboard
                  <ExternalLink className="h-3 w-3 ml-2" />
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {/* Alerts card — inline list from /api/analytics/active-alerts + links */}
        <Card className="glass-card border border-border/80">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-[var(--getnet-red)]" />
              Active Alerts
              {activeAlerts.length > 0 && (
                <Badge variant="destructive" className="ml-auto text-xs">{activeAlerts.length}</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {alertsQ.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : activeAlerts.length === 0 ? (
              <div className="flex items-center gap-2 rounded-md bg-green-500/10 px-3 py-2 text-sm">
                <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                <span className="text-muted-foreground">No active alerts — all clear.</span>
              </div>
            ) : (
              <ul className="space-y-2 max-h-64 overflow-y-auto">
                {activeAlerts.map((a, i) => (
                  <li key={i} className="rounded-md border border-border/60 bg-muted/30 px-3 py-2">
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge variant={a.severity === "high" ? "destructive" : a.severity === "medium" ? "default" : "secondary"} className="text-[10px]">
                        {a.severity}
                      </Badge>
                      <span className="text-sm font-medium">{a.alert_type}</span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">{a.alert_message}</p>
                    <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                      {a.metric_name}: {a.current_value} (threshold: {a.threshold_value})
                    </p>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-2 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => openInDatabricks(getLakeviewDashboardUrl(MONITORING_DASHBOARD_NAME))}
              >
                Real-Time Monitoring
                <ExternalLink className="h-3 w-3 ml-2" />
              </Button>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="sm" onClick={() => openNotebookInDatabricks("realtime_pipeline")}>
                    <Code2 className="h-3 w-3 mr-2" />
                    Alert Pipeline
                    <ExternalLink className="h-3 w-3 ml-2" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Open the real-time pipeline notebook in the workspace.</TooltipContent>
              </Tooltip>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Create incident (from incidents) */}
      <section aria-labelledby="create-incident-heading">
        <h2 id="create-incident-heading" className="text-lg font-semibold mb-3">Create incident</h2>
        <Card className="glass-card border border-border/80">
          <CardContent className="pt-6 grid gap-2 md:grid-cols-3">
            <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Category (e.g. mid_failure)" />
            <Input value={key} onChange={(e) => setKey(e.target.value)} placeholder="Key (e.g. MID=demo)" />
            <Button onClick={() => create.mutate()} disabled={create.isPending}>
              Create
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Incident list (from incidents) */}
      <section aria-labelledby="incident-list-heading">
        <h2 id="incident-list-heading" className="text-lg font-semibold mb-3">Incident list</h2>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No incidents yet. Use &quot;Create incident&quot; above to add one.</p>
        ) : (
          <div className="space-y-3">
            {items.map((inc) => (
              <IncidentRow key={inc.id} inc={inc} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
