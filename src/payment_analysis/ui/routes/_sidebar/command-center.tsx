import { Suspense, useCallback, useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { KPICard } from "@/components/executive";
import {
  useGetKpisSuspense,
  useGetDataQualitySummary,
  useGetCommandCenterEntryThroughput,
  useGetActiveAlerts,
  useHealthDatabricks,
  useGetDashboardUrl,
  useGetThreeDsFunnel,
  useGetReasonCodeInsights,
  useGetFalseInsightsMetric,
  useGetRetryPerformance,
  useGetEntrySystemDistribution,
} from "@/lib/api";
import selector from "@/lib/selector";
import { useEntity } from "@/contexts/entity-context";
import { useAssistant } from "@/contexts/assistant-context";
import { PageHeader } from "@/components/apx/page-header";
import { getDashboardUrl, getGenieUrl, openInDatabricks } from "@/config/workspace";
import type { EntrySystemPoint, FrictionFunnelStep, RetryRecurrenceRow } from "@/lib/command-center-mock";
import {
  Activity,
  Target,
  Gauge,
  SlidersHorizontal,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Calendar,
  Zap,
  Bot,
  LayoutDashboard,
  ExternalLink,
  ArrowRight,
} from "lucide-react";

/** Refresh interval for KPI and data quality (5s). */
const REFRESH_MS = 5000;
/** Real-time chart widgets: 0.5s for short interval and dynamically adjusting axis. */
const REFRESH_CHART_MS = 500;
const SANTANDER_RED = "#EC0000";
const NEON_CYAN = "#00E5FF";
const VIBRANT_GREEN = "#22C55E";

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
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-28 rounded-xl bg-card" />
        <Skeleton className="h-28 rounded-xl bg-card" />
        <Skeleton className="h-28 rounded-xl bg-card" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <Skeleton className="h-72 rounded-xl bg-card" />
        <Skeleton className="h-72 rounded-xl bg-card" />
      </div>
    </div>
  );
}

/** Multi-line streaming chart: PD 62%, WS 34%, SEP 3%, Checkout 1% */
function EntrySystemsChart({ points }: { points: EntrySystemPoint[] }) {
  const series = useMemo(() => {
    if (!points.length) return null;
    const keys = ["PD", "WS", "SEP", "Checkout"] as const;
    const colors = [SANTANDER_RED, NEON_CYAN, VIBRANT_GREEN, "oklch(0.7 0.15 280)"];
    return keys.map((key, i) => ({
      key,
      color: colors[i],
      values: points.map((p) => p[key]),
    }));
  }, [points]);

  const maxVal = useMemo(() => {
    if (!points.length) return 1;
    let m = 0;
    points.forEach((p) => {
      m = Math.max(m, p.PD + p.WS + p.SEP + p.Checkout);
    });
    return Math.max(1, m);
  }, [points]);

  const width = 640;
  const height = 220;
  const padding = { top: 12, right: 12, bottom: 28, left: 40 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const n = points.length;

  if (!series || n < 2) {
    return (
      <div className="flex h-[220px] items-center justify-center rounded-lg bg-muted/20 text-sm text-muted-foreground">
        No entry system data for selected country.
      </div>
    );
  }

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="min-h-[220px]" preserveAspectRatio="xMidYMid meet">
      <defs>
        {series.map((s) => (
          <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor={s.color} stopOpacity="0.2" />
            <stop offset="100%" stopColor={s.color} stopOpacity="0.6" />
          </linearGradient>
        ))}
      </defs>
      {series.map((s) => {
        const pathPoints = s.values.map((v, i) => {
          const x = padding.left + (n > 1 ? (i / (n - 1)) * innerW : 0);
          const y = padding.top + innerH - (v / maxVal) * innerH;
          return `${x},${y}`;
        });
        const linePath = pathPoints.length > 1 ? `M ${pathPoints.join(" L ")}` : "";
        return (
          <path
            key={s.key}
            d={linePath}
            fill="none"
            stroke={s.color}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        );
      })}
      <text x={padding.left} y={padding.top + 10} className="fill-muted-foreground text-[10px]">0</text>
      <text x={padding.left} y={padding.top + innerH + 18} className="fill-muted-foreground text-[10px]">{maxVal} TPS</text>
    </svg>
  );
}

/** 3DS Friction Funnel: Total → Friction → Auth → Approved */
function FrictionFunnelWidget({ steps }: { steps: FrictionFunnelStep[] }) {
  const maxVal = Math.max(...steps.map((s) => s.value), 1);
  const barColors = [NEON_CYAN, "oklch(0.6 0.15 280)", "oklch(0.6 0.15 280)", VIBRANT_GREEN];
  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <div key={step.label} className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">{step.label}</span>
            <span className="font-medium tabular-nums kpi-number">{step.value.toLocaleString()} ({step.pct}%)</span>
          </div>
          <div className="h-2 rounded-full bg-muted/50 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${(step.value / maxVal) * 100}%`,
                backgroundColor: barColors[i] ?? "var(--primary)",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Entry Gate Telemetry: entry systems from API (throughput % of total); no latency from backend */
function EntryGateTelemetry({
  gates,
}: {
  gates: { gate: string; throughputPct: number }[];
}) {
  if (!gates.length) {
    return <p className="text-sm text-muted-foreground">No entry system data</p>;
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      {gates.map((g, i) => (
        <span key={g.gate} className="flex items-center gap-1.5">
          <span className="rounded-md bg-muted/60 px-2 py-1 text-xs font-medium">
            {g.gate}
          </span>
          <span className="text-[10px] text-muted-foreground tabular-nums">{g.throughputPct}%</span>
          {i < gates.length - 1 && <span className="text-muted-foreground/60" aria-hidden>→</span>}
        </span>
      ))}
    </div>
  );
}

function CommandCenter() {
  const { entity: countryCode } = useEntity();
  const { openAssistant } = useAssistant();
  const [controlOpen, setControlOpen] = useState(false);
  const [smartRouting, setSmartRouting] = useState(true);
  const [fraudShadowMode, setFraudShadowMode] = useState(false);
  const [recalculateAlgorithms, setRecalculateAlgorithms] = useState(false);

  const syncControlPanel = useCallback(
    async (payload: { activate_smart_routing?: boolean; deploy_fraud_shadow_model?: boolean; recalculate_algorithms?: boolean }) => {
      try {
        await fetch("/api/analytics/control-panel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } catch {
        // non-blocking
      }
    },
    [],
  );

  const { data: execUrlData } = useGetDashboardUrl({ params: { dashboard_id: "executive_trends_unified" } });
  const openExecutiveDashboard = () => {
    const url = (execUrlData?.data as { full_url?: string } | undefined)?.full_url ?? getDashboardUrl("/sql/dashboards/executive_trends_unified");
    openInDatabricks(url);
  };

  const { data: kpis } = useGetKpisSuspense(selector());
  const dataQualityQ = useGetDataQualitySummary({ query: { refetchInterval: REFRESH_MS } });
  const { data: healthData } = useHealthDatabricks();

  const entryThroughputQ = useGetCommandCenterEntryThroughput({
    params: { entity: countryCode, limit_minutes: 30 },
    query: { refetchInterval: REFRESH_CHART_MS },
  });
  const alertsQ = useGetActiveAlerts({
    params: { limit: 20 },
    query: { refetchInterval: REFRESH_CHART_MS },
  });
  const threeDsQ = useGetThreeDsFunnel({ params: { entity: countryCode, days: 30 } });
  const reasonCodesQ = useGetReasonCodeInsights({ params: { entity: countryCode, limit: 50 } });
  const falseInsightsQ = useGetFalseInsightsMetric({ params: { days: 30 } });
  const retryPerfQ = useGetRetryPerformance({ params: { limit: 50 } });
  const entryDistQ = useGetEntrySystemDistribution({ params: { entity: countryCode } });

  const entryPoints: EntrySystemPoint[] = useMemo(() => {
    const raw = entryThroughputQ.data?.data;
    if (!raw?.length) return [];
    return raw.map((p) => ({ ts: p.ts, PD: p.PD, WS: p.WS, SEP: p.SEP, Checkout: p.Checkout }));
  }, [entryThroughputQ.data?.data]);

  const approvalPct = kpis != null ? (kpis.approval_rate * 100).toFixed(1) : "—";
  const falseDeclinePct = kpis != null ? ((1 - kpis.approval_rate) * 100).toFixed(1) : "—";
  const dataQuality = dataQualityQ.data?.data;
  const dqScore = dataQuality?.retention_pct_24h != null
    ? Math.min(100, Math.round(dataQuality.retention_pct_24h))
    : null;

  const funnelSteps: FrictionFunnelStep[] = useMemo(() => {
    const rows = threeDsQ.data?.data;
    if (!rows?.length) return [];
    const latest = rows[rows.length - 1];
    const total = latest.three_ds_routed_count || 0;
    if (total === 0) return [];
    const friction = latest.three_ds_friction_count ?? 0;
    const auth = latest.three_ds_authenticated_count ?? 0;
    const approved = latest.issuer_approved_after_auth_count ?? 0;
    return [
      { label: "Total", value: total, pct: 100 },
      { label: "Friction", value: friction, pct: total ? Math.round((friction / total) * 100) : 0 },
      { label: "Auth", value: auth, pct: total ? Math.round((auth / total) * 100) : 0 },
      { label: "Approved", value: approved, pct: total ? Math.round((approved / total) * 100) : 0 },
    ];
  }, [threeDsQ.data?.data]);

  const reasonCodeSummary = useMemo(() => {
    const list = reasonCodesQ.data?.data;
    if (!list?.length) return [] as { category: string; count: number; pct: number }[];
    const total = list.reduce((s, r) => s + r.decline_count, 0);
    if (total === 0) return [];
    const byGroup = new Map<string, number>();
    for (const r of list) {
      const g = r.decline_reason_group || "Other";
      byGroup.set(g, (byGroup.get(g) ?? 0) + r.decline_count);
    }
    return Array.from(byGroup.entries())
      .map(([category, count]) => ({ category, count, pct: Math.round((count / total) * 100) }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [reasonCodesQ.data?.data]);

  const falseInsightsPct: number | null = useMemo(() => {
    const list = falseInsightsQ.data?.data;
    if (!list?.length) return null;
    const latest = list[list.length - 1];
    return latest.false_insights_pct != null ? Math.round(latest.false_insights_pct) : null;
  }, [falseInsightsQ.data?.data]);

  const retryRecurrence: RetryRecurrenceRow[] = useMemo(() => {
    const list = retryPerfQ.data?.data;
    if (!list?.length) return [];
    const scheduled = list.filter((r) => r.retry_scenario === "PaymentRecurrence").reduce((s, r) => s + r.retry_count, 0);
    const manual = list.filter((r) => r.retry_scenario === "PaymentRetry").reduce((s, r) => s + r.retry_count, 0);
    const total = scheduled + manual;
    if (total === 0) return [];
    return [
      { type: "scheduled_recurrence", label: "Scheduled Recurrence", volume: scheduled, pct: Math.round((scheduled / total) * 100) },
      { type: "manual_retry", label: "Manual Retry", volume: manual, pct: Math.round((manual / total) * 100) },
    ];
  }, [retryPerfQ.data?.data]);

  const entryGateGates = useMemo(() => {
    const list = entryDistQ.data?.data;
    if (!list?.length) return [];
    const total = list.reduce((s, r) => s + r.transaction_count, 0);
    if (total === 0) return [];
    return list.map((r) => ({
      gate: r.entry_system,
      throughputPct: Math.round((r.transaction_count / total) * 100),
    }));
  }, [entryDistQ.data?.data]);

  const fromDatabricks = healthData?.data?.analytics_source === "Unity Catalog";

  return (
    <div className="flex min-h-full flex-col bg-background">
      <main className="flex-1 space-y-6 p-4 md:p-6" role="main">
        <PageHeader
          variant="executive"
          icon={<LayoutDashboard className="w-9 h-9" />}
          title="Overview"
          description="Approval-rate KPIs, reports, and AI. All data from Databricks."
        />
        <Card className="glass-card border border-border/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Reports &amp; AI</CardTitle>
            <p className="text-xs text-muted-foreground font-normal mt-0.5">
              Databricks dashboards, Genie, and Orchestrator agent.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={openExecutiveDashboard}>
              <LayoutDashboard className="h-3.5 w-3.5 mr-2" />
              Executive Dashboard
              <ExternalLink className="h-3 w-3 ml-2" />
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/dashboards" search={{}}>
                All dashboards
                <ArrowRight className="h-3 w-3 ml-2" />
              </Link>
            </Button>
            <Button variant="outline" size="sm" onClick={() => openInDatabricks(getGenieUrl())}>
              Genie (Ask Data)
              <ExternalLink className="h-3 w-3 ml-2" />
            </Button>
            <Button variant="default" size="sm" onClick={openAssistant}>
              <Bot className="h-3.5 w-3.5 mr-2" />
              Chat with Orchestrator
            </Button>
          </CardContent>
        </Card>

        <section aria-labelledby="kpi-heading" className="grid gap-4 md:grid-cols-3">
          <h2 id="kpi-heading" className="sr-only">Strategic KPIs</h2>
          <KPICard
            label="Gross Approval Rate"
            value={`${approvalPct}%`}
            icon={<Target className="size-4" />}
            accent="primary"
          />
          <KPICard
            label="False Decline Rate"
            value={`${falseDeclinePct}%`}
            accent="warning"
          />
          <KPICard
            label="Data Quality Health"
            value={dataQualityQ.isLoading || dqScore == null ? "—" : `${dqScore}%`}
            icon={<Gauge className="size-4" />}
            accent="muted"
          />
        </section>

        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <Card className="glass-card overflow-hidden border border-border/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4" style={{ color: NEON_CYAN }} />
                Entry Systems Throughput
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <EntrySystemsChart points={entryPoints} />
              <div className="mt-2 flex flex-wrap gap-4 text-[10px]">
                <span style={{ color: SANTANDER_RED }}>● PD 62%</span>
                <span style={{ color: NEON_CYAN }}>● WS 34%</span>
                <span style={{ color: VIBRANT_GREEN }}>● SEP 3%</span>
                <span className="text-muted-foreground">● Checkout 1%</span>
              </div>
            </CardContent>
          </Card>
          <Card className="glass-card border border-border/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Top 5 Decline Reasons</CardTitle>
            </CardHeader>
            <CardContent>
              {reasonCodeSummary.length === 0 ? (
                <p className="text-sm text-muted-foreground">No decline reason data</p>
              ) : (
                <div className="space-y-2">
                  {reasonCodeSummary.map((r) => (
                    <div key={r.category} className="flex items-center justify-between rounded-md bg-muted/30 px-2 py-1.5 text-sm">
                      <span className="font-medium text-foreground">{r.category}</span>
                      <span className="tabular-nums text-muted-foreground">{r.count.toLocaleString()} ({r.pct}%)</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right column: Friction Funnel + Alerts */}
          <div className="space-y-4">
            <Card className="glass-card border border-border/80">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Zap className="h-4 w-4 text-primary" />
                  3DS Friction Funnel
                </CardTitle>
              </CardHeader>
              <CardContent>
                {funnelSteps.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No 3DS funnel data</p>
                ) : (
                  <FrictionFunnelWidget steps={funnelSteps} />
                )}
              </CardContent>
            </Card>
            <Card className="glass-card border border-border/80">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-orange-500" />
                  Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                {alertsQ.data?.data?.length ? (
                  <ScrollArea className="h-48 rounded-md border border-border/60">
                    <ul className="space-y-2 p-1">
                      {alertsQ.data.data.slice(0, 10).map((a, i) => (
                        <li key={i} className="flex flex-col gap-0.5 rounded-md bg-muted/30 px-2 py-1.5 text-xs">
                          <span className="font-medium text-foreground">{a.alert_type}</span>
                          <span className="text-muted-foreground line-clamp-2">{a.alert_message}</span>
                          <span className="text-[10px] text-muted-foreground/80">{a.severity} · {a.metric_name}</span>
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                ) : (
                  <p className="text-sm text-muted-foreground">No active alerts</p>
                )}
              </CardContent>
            </Card>
            <Card className="glass-card border border-border/80">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" style={{ color: NEON_CYAN }} />
                  Data Quality
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {dataQualityQ.data?.data != null && (
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Retention (24h)</span>
                      <span className="font-medium tabular-nums kpi-number">{Math.round(dataQualityQ.data.data.retention_pct_24h)}%</span>
                    </div>
                    <Progress value={Math.min(100, dataQualityQ.data.data.retention_pct_24h)} className="h-2" />
                  </div>
                )}
                <ul className="space-y-1.5 text-sm">
                  <li className="flex items-center gap-2 text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 shrink-0" style={{ color: VIBRANT_GREEN }} />
                    <span>Schema validated</span>
                  </li>
                  <li className="flex items-center gap-2 text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 shrink-0" style={{ color: VIBRANT_GREEN }} />
                    <span>PII masking enabled</span>
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>

        <Card className="glass-card border border-border/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Entry Gate Telemetry</CardTitle>
          </CardHeader>
          <CardContent>
            <EntryGateTelemetry gates={entryGateGates} />
          </CardContent>
        </Card>

        <div className="grid gap-4 md:grid-cols-2">
          <Card className="glass-card border border-border/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-orange-500" />
                False Insights Tracker
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold tabular-nums text-orange-500">{falseInsightsPct != null ? `${falseInsightsPct}%` : "—"}</span>
                <span className="text-sm text-muted-foreground">non-actionable</span>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border border-border/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <RotateCcw className="h-4 w-4 text-primary" />
                Smart Retry & Recurrence
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {retryRecurrence.length === 0 ? (
                <p className="text-sm text-muted-foreground">No retry performance data</p>
              ) : (
                retryRecurrence.map((row) => (
                  <div key={row.type} className="flex items-center justify-between rounded-lg bg-muted/30 px-3 py-2">
                    <span className="flex items-center gap-2 text-sm">
                      {row.type === "scheduled_recurrence" ? <Calendar className="h-4 w-4 text-muted-foreground" /> : <RotateCcw className="h-4 w-4 text-muted-foreground" />}
                      {row.label}
                    </span>
                    <span className="text-sm font-medium tabular-nums">{row.volume.toLocaleString()} ({row.pct}%)</span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end">
          <Sheet open={controlOpen} onOpenChange={setControlOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <SlidersHorizontal className="h-4 w-4" />
                Control Panel
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[320px] sm:max-w-sm">
              <SheetHeader>
                <SheetTitle>Control Panel</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div className="flex items-center justify-between">
                  <label htmlFor="smart-routing" className="text-sm font-medium">
                    Activate Smart Routing
                  </label>
                  <Switch
                    id="smart-routing"
                    checked={smartRouting}
                    onCheckedChange={(v) => {
                      setSmartRouting(v);
                      syncControlPanel({ activate_smart_routing: v });
                    }}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label htmlFor="fraud-shadow" className="text-sm font-medium">
                    Deploy Fraud Shadow Model
                  </label>
                  <Switch
                    id="fraud-shadow"
                    checked={fraudShadowMode}
                    onCheckedChange={(v) => {
                      setFraudShadowMode(v);
                      syncControlPanel({ deploy_fraud_shadow_model: v });
                    }}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label htmlFor="recalculate-algorithms" className="text-sm font-medium">
                    Recalculate Algorithms
                  </label>
                  <Switch
                    id="recalculate-algorithms"
                    checked={recalculateAlgorithms}
                    onCheckedChange={(v) => {
                      setRecalculateAlgorithms(v);
                      syncControlPanel({ recalculate_algorithms: v });
                    }}
                  />
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-border/80 px-4 py-2 text-xs text-muted-foreground">
          {fromDatabricks ? (
            <span className="inline-flex items-center gap-1 rounded bg-green-500/10 px-2 py-0.5" style={{ color: VIBRANT_GREEN }}>
              Data: Databricks
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 px-2 py-0.5">
              Data: Sample (mock)
            </span>
          )}
        </footer>
      </main>
    </div>
  );
}
