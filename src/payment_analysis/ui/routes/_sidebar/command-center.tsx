import { Suspense, useMemo, useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import {
  useGetKpisSuspense,
  useGetDataQualitySummary,
  useHealthDatabricks,
} from "@/lib/api";
import selector from "@/lib/selector";
import { GetnetAIAssistant } from "@/components/chat";
import { useEntity } from "@/contexts/entity-context";
import {
  getCommandCenterKpis,
  getEntrySystemThroughput,
  getFrictionFunnel,
  getFalseInsightsPct,
  getRetryRecurrence,
  getEntryGateTelemetry,
  type EntrySystemPoint,
  type FrictionFunnelStep,
} from "@/lib/command-center-mock";
import {
  Activity,
  Target,
  Gauge,
  SlidersHorizontal,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  HelpCircle,
  AlertTriangle,
  RotateCcw,
  Calendar,
  Zap,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const REFRESH_MS = 5000;
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

/** 3DS Friction Funnel: Total → 80% Friction → 60% Auth → 80% Approved */
function FrictionFunnelWidget({ steps }: { steps: FrictionFunnelStep[] }) {
  const maxVal = Math.max(...steps.map((s) => s.value), 1);
  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <div key={step.label} className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">{step.label}</span>
            <span className="font-medium tabular-nums">{step.value.toLocaleString()} ({step.pct}%)</span>
          </div>
          <div className="h-2 rounded-full bg-muted/50 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${(step.value / maxVal) * 100}%`,
                backgroundColor: i === 0 ? NEON_CYAN : i === steps.length - 1 ? VIBRANT_GREEN : "oklch(0.6 0.15 280)",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Entry Gate Telemetry: Checkout BR → PD → WS → Base24 → Issuer */
function EntryGateTelemetry({ countryCode }: { countryCode: string }) {
  const gates = getEntryGateTelemetry(countryCode);
  return (
    <div className="flex flex-wrap items-center gap-2">
      {gates.map((g, i) => (
        <span key={g.gate} className="flex items-center gap-1.5">
          <span className="rounded-md bg-muted/60 px-2 py-1 text-xs font-medium">
            {g.gate}
          </span>
          <span className="text-[10px] text-muted-foreground tabular-nums">{g.throughputPct}% · {g.latencyMs}ms</span>
          {i < gates.length - 1 && <span className="text-muted-foreground/60" aria-hidden>→</span>}
        </span>
      ))}
    </div>
  );
}

function CommandCenter() {
  const { entity: countryCode } = useEntity();
  const [controlOpen, setControlOpen] = useState(false);
  const [smartRouting, setSmartRouting] = useState(true);
  const [fraudShadowMode, setFraudShadowMode] = useState(false);
  const [triggerRetryLogic, setTriggerRetryLogic] = useState(false);

  const [entryPoints, setEntryPoints] = useState<EntrySystemPoint[]>([]);
  useEffect(() => {
    setEntryPoints(getEntrySystemThroughput(countryCode, 30));
    const t = setInterval(() => setEntryPoints(getEntrySystemThroughput(countryCode, 30)), REFRESH_MS);
    return () => clearInterval(t);
  }, [countryCode]);

  const { data: kpis } = useGetKpisSuspense(selector());
  const dataQualityQ = useGetDataQualitySummary({ query: { refetchInterval: REFRESH_MS } });
  const { data: healthData } = useHealthDatabricks();

  const mockKpis = getCommandCenterKpis(countryCode);
  const approvalPct = kpis ? (kpis.approval_rate * 100).toFixed(1) : String(mockKpis.grossApprovalRatePct);
  const falseDeclinePct = kpis ? ((1 - kpis.approval_rate) * 100).toFixed(1) : String(mockKpis.falseDeclineRatePct);
  const dataQuality = dataQualityQ.data?.data;
  const dqScore = dataQuality?.retention_pct_24h != null
    ? Math.min(100, Math.round(dataQuality.retention_pct_24h))
    : mockKpis.dataQualityHealthPct;

  const funnelSteps = getFrictionFunnel(countryCode);
  const falseInsightsPct = getFalseInsightsPct(countryCode);
  const retryRecurrence = getRetryRecurrence(countryCode);
  const fromDatabricks = healthData?.data?.analytics_source === "Unity Catalog";

  return (
    <div className="flex min-h-full flex-col bg-background">
      <main className="flex-1 space-y-6 p-4 md:p-6" role="main">
        {/* KPI Row: GAR (73% benchmark), False Decline, Data Quality — Pro-Dark glass cards, Santander Red / Neon Cyan / Green */}
        <section aria-labelledby="kpi-heading" className="grid gap-4 md:grid-cols-3">
          <h2 id="kpi-heading" className="sr-only">Strategic KPIs</h2>
          <Card className="glass-card border-2 border-[var(--getnet-red)]/40 bg-[var(--getnet-red)]/10 dark:bg-[var(--getnet-red)]/15">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="text-sm font-medium text-muted-foreground flex items-center gap-1 cursor-help">
                      Gross Approval Rate
                      <HelpCircle className="h-3.5 w-3 opacity-60" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-[240px]">
                    Percentage of transactions approved. Benchmark 73%. Used to track payment success.
                  </TooltipContent>
                </Tooltip>
                <Target className="h-4 w-4 shrink-0" style={{ color: SANTANDER_RED }} aria-hidden />
              </div>
              <p className="mt-2 text-4xl font-bold tabular-nums" style={{ color: SANTANDER_RED }}>
                {approvalPct}%
              </p>
              <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                <span>Benchmark 73%</span>
                <span className="inline-flex items-center" style={{ color: VIBRANT_GREEN }}>
                  <TrendingUp className="h-3 w-3" /> +3.1% YoY
                </span>
              </p>
            </CardContent>
          </Card>
          <Card className="glass-card border-2 border-orange-500/50 bg-orange-500/10 dark:bg-orange-500/15">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="text-sm font-medium text-muted-foreground flex items-center gap-1 cursor-help">
                      False Decline Rate
                      <HelpCircle className="h-3.5 w-3 opacity-60" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-[240px]">
                    Share of declines that could have been approved. Lower is better.
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="mt-2 text-4xl font-bold text-orange-500 tabular-nums">
                {falseDeclinePct}%
              </p>
              <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                <span>Target &lt;1.2%</span>
                <span className="inline-flex items-center" style={{ color: VIBRANT_GREEN }}>
                  <TrendingDown className="h-3 w-3" /> -17% YoY
                </span>
              </p>
            </CardContent>
          </Card>
          <Card className="glass-card border-2 border-[var(--neon-cyan)]/40 bg-[var(--neon-cyan)]/5 dark:bg-[var(--neon-cyan)]/10">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="text-sm font-medium text-muted-foreground flex items-center gap-1 cursor-help">
                      Data Quality Health
                      <HelpCircle className="h-3.5 w-3 opacity-60" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-[240px]">
                    Bronze/silver freshness, retention, pipeline flow. Ensures analytics are reliable.
                  </TooltipContent>
                </Tooltip>
                <Gauge className="h-4 w-4 shrink-0" style={{ color: NEON_CYAN }} aria-hidden />
              </div>
              <p className="mt-2 text-4xl font-bold tabular-nums" style={{ color: NEON_CYAN }}>
                {dataQualityQ.isLoading ? "—" : `${dqScore}%`}
              </p>
              <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                <CheckCircle2 className="h-3 w-3 shrink-0" style={{ color: VIBRANT_GREEN }} />
                Freshness · Schema · PII masking
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Real-Time Monitor: throughput by entry system (PD 62%, WS 34%, SEP 3%, Checkout 1%) */}
        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <Card className="glass-card overflow-hidden border border-border/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4" style={{ color: NEON_CYAN }} />
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="flex items-center gap-1 cursor-help">
                      Real-Time Monitor — Entry Systems Throughput
                      <HelpCircle className="h-3.5 w-3 opacity-60" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-[280px]">
                    PD 62%, WS 34%, SEP 3%, Checkout 1%. Transaction path: Checkout BR → PD → WS → Base24 → Issuer.
                  </TooltipContent>
                </Tooltip>
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Throughput (TPS) by entry system. Refresh every 5s. Country filter applied (Databricks SQL parameter).
              </p>
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

          {/* Friction Funnel: 3DS journey */}
          <Card className="glass-card border border-border/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Zap className="h-4 w-4 text-primary" />
                3DS Friction Funnel
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Total → 80% Friction → 60% Auth → 80% Approved
              </p>
            </CardHeader>
            <CardContent>
              <FrictionFunnelWidget steps={funnelSteps} />
            </CardContent>
          </Card>
        </div>

        {/* Entry Gate Telemetry: Intermediate layers path */}
        <Card className="glass-card border border-border/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Unified Entry Gate Telemetry</CardTitle>
            <p className="text-xs text-muted-foreground">
              Transaction path — identify where bottlenecks occur: Checkout BR → PD → WS → Base24 → Issuer
            </p>
          </CardHeader>
          <CardContent>
            <EntryGateTelemetry countryCode={countryCode} />
          </CardContent>
        </Card>

        {/* Quality Control: False Insights + Retry/Recurrence */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="glass-card border border-border/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-orange-500" />
                Quality Control — False Insights Tracker
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                % of AI-generated recommendations marked non-actionable by domain specialists (Learning Loop)
              </p>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold tabular-nums text-orange-500">{falseInsightsPct}%</span>
                <span className="text-sm text-muted-foreground">non-actionable</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">Target: reduce via feedback and model tuning</p>
            </CardContent>
          </Card>

          <Card className="glass-card border border-border/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <RotateCcw className="h-4 w-4 text-primary" />
                Smart Retry & Recurrence Monitoring
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Scheduled Recurrence (subscriptions) vs Manual Retry (reattempts). Deduplicated for volume.
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {retryRecurrence.map((row) => (
                <div key={row.type} className="flex items-center justify-between rounded-lg bg-muted/30 px-3 py-2">
                  <span className="flex items-center gap-2 text-sm">
                    {row.type === "scheduled_recurrence" ? <Calendar className="h-4 w-4 text-muted-foreground" /> : <RotateCcw className="h-4 w-4 text-muted-foreground" />}
                    {row.label}
                  </span>
                  <span className="text-sm font-medium tabular-nums">{row.volume.toLocaleString()} ({row.pct}%)</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Control Panel — right-aligned trigger */}
        <div className="flex justify-end">
          <Sheet open={controlOpen} onOpenChange={setControlOpen}>
            <Tooltip>
              <TooltipTrigger asChild>
                <SheetTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2">
                    <SlidersHorizontal className="h-4 w-4" />
                    Control Panel
                  </Button>
                </SheetTrigger>
              </TooltipTrigger>
              <TooltipContent>
                Activate Smart Routing, Deploy Fraud Shadow Model, Trigger Retry Logic.
              </TooltipContent>
            </Tooltip>
            <SheetContent side="right" className="w-[320px] sm:max-w-sm">
              <SheetHeader>
                <SheetTitle>Control Panel</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div className="flex items-center justify-between">
                  <label htmlFor="smart-routing" className="text-sm font-medium">
                    Activate Smart Routing
                  </label>
                  <Switch id="smart-routing" checked={smartRouting} onCheckedChange={setSmartRouting} />
                </div>
                <div className="flex items-center justify-between">
                  <label htmlFor="fraud-shadow" className="text-sm font-medium">
                    Deploy Fraud Shadow Model
                  </label>
                  <Switch id="fraud-shadow" checked={fraudShadowMode} onCheckedChange={setFraudShadowMode} />
                </div>
                <div className="flex items-center justify-between">
                  <label htmlFor="retry-logic" className="text-sm font-medium">
                    Trigger Retry Logic
                  </label>
                  <Switch id="retry-logic" checked={triggerRetryLogic} onCheckedChange={setTriggerRetryLogic} />
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>

        <footer className="flex items-center justify-between border-t border-border/80 px-4 py-2 text-xs text-muted-foreground">
          <span>Country filter: global dimension · Refresh every 5s</span>
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

      <GetnetAIAssistant />
    </div>
  );
}
