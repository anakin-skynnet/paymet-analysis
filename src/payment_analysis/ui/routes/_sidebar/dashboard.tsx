import { Suspense } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
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
  useGetReasonCodeInsightsBr,
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
  GitBranch,
  ArrowRight,
  AlertCircle,
  Target,
} from "lucide-react";
import { getDashboardUrl, getGenieUrl } from "@/config/workspace";

const dashboardStagger = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const dashboardItem = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

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
  const { data: reasonCodeData } = useGetReasonCodeInsightsBr({ params: { limit: 5 } });
  const factorsDelayingApproval = reasonCodeData?.data ?? [];

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

  const openExecutive = () => openInDatabricks(getDashboardUrl("/sql/dashboards/executive_overview"));

  return (
    <motion.div
      className="space-y-8"
      variants={dashboardStagger}
      initial="hidden"
      animate="show"
    >
      {/* Hero: one place to monitor approval rates and discover what’s delaying them */}
      <motion.div variants={dashboardItem}>
        <p className="text-base font-medium text-foreground">
          Monitor approval rates, discover factors delaying approvals, and see where to act.
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          Portfolio performance in the last 30 days — key metrics, trends, and actionable insights for the Getnet team.
        </p>
      </motion.div>

      {/* Data flow & storytelling — one system */}
      <motion.div variants={dashboardItem}>
        <Card className="border-primary/20 bg-muted/30">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <GitBranch className="w-4 h-4 text-primary" />
              One Lakehouse-based decision system
            </CardTitle>
            <CardDescription>
              Smart Checkout, Reason Code Performance, and Smart Retry work together to increase approval rates and control risk. Transactions → enrichment → decision → dashboards.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2 pt-0">
            <Button variant="outline" size="sm" asChild>
              <Link to="/dashboards" search={{}}>
                DBSQL dashboards <ArrowRight className="w-3 h-3 ml-1" />
              </Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/smart-checkout">Smart Checkout</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/reason-codes">Reason codes</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/smart-retry">Smart Retry</Link>
            </Button>
          </CardContent>
        </Card>
      </motion.div>

      {/* Header with Links */}
      <motion.div variants={dashboardItem}>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight font-heading">
            Portfolio overview
          </h1>
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
      </motion.div>

      {/* What is happening — Hero KPI first, then supporting KPIs */}
      <motion.div variants={dashboardItem}>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
          What is happening
        </h2>
      </motion.div>
      <motion.div variants={dashboardStagger} className="grid gap-4 md:grid-cols-3">
        {/* Hero KPI — extra visual emphasis; presentation moment: tap to open full dashboard */}
        <motion.div
          variants={dashboardItem}
          className="md:col-span-1"
          whileTap={{ scale: 0.98 }}
          transition={{ duration: 0.15 }}
        >
          <Card
            className="cursor-pointer relative overflow-hidden border-2 border-primary/50 bg-primary/10 hover:shadow-xl hover:shadow-primary/20 hover:border-primary/70 transition-all duration-300 elevation-2"
            onClick={openExecutive}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && openExecutive()}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/15 to-transparent pointer-events-none" />
            <CardHeader className="pb-2 relative">
              <CardTitle className="text-sm font-semibold text-primary">
                Portfolio approval rate
              </CardTitle>
            </CardHeader>
            <CardContent className="relative">
              <p className="text-4xl md:text-5xl font-bold text-primary">{pct}%</p>
              <p className="text-xs text-muted-foreground mt-2">
                Core metric for Getnet — higher rate means more revenue and better customer experience.
              </p>
            </CardContent>
          </Card>
        </motion.div>
        <motion.div variants={dashboardItem}>
          <Card
            className="cursor-pointer hover:shadow-lg hover:border-primary/30 transition-all duration-300"
            onClick={openExecutive}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && openExecutive()}
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
        </motion.div>
        <motion.div variants={dashboardItem}>
          <Card
            className="cursor-pointer hover:shadow-lg hover:border-primary/30 transition-all duration-300"
            onClick={openExecutive}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && openExecutive()}
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
        </motion.div>
      </motion.div>

      {/* Why — trends and solution performance */}
      <motion.div variants={dashboardItem}>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
          Why
        </h2>
      </motion.div>
      <motion.div variants={dashboardStagger} className="grid gap-4 md:grid-cols-2">
        <motion.div variants={dashboardItem}>
        {/* Approval Trends — click opens Daily Trends dashboard */}
        <Card
          className="cursor-pointer hover:shadow-lg hover:border-primary/30 transition-all duration-300"
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
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <BarChart3 className="h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">No trend data yet.</p>
                <p className="text-xs text-muted-foreground">Complete setup steps 1–6; data will appear here.</p>
              </div>
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
        </motion.div>

        <motion.div variants={dashboardItem}>
        {/* Solution Performance — click opens Smart Routing dashboard */}
        <Card
          className="cursor-pointer hover:shadow-lg hover:border-primary/30 transition-all duration-300"
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
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <TrendingUp className="h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">No solution data yet.</p>
                <p className="text-xs text-muted-foreground">Run the pipeline to see performance by solution.</p>
              </div>
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
        </motion.div>
      </motion.div>

      {/* Factors that may be delaying approvals — discover conditions and recommended actions */}
      <motion.div variants={dashboardItem}>
        <Card className="border-amber-200 dark:border-amber-800 bg-amber-50/30 dark:bg-amber-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              Factors that may be delaying approvals
            </CardTitle>
            <CardDescription>
              Top conditions from Reason Codes with recommended actions. Act on these to accelerate approval rates.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {factorsDelayingApproval.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No reason-code data yet. Run gold views and Reason Codes pipeline; then open Reason Codes for full insights.
              </p>
            ) : (
              <ul className="space-y-3">
                {factorsDelayingApproval.map((r) => (
                  <li key={`${r.entry_system}-${r.decline_reason_standard}-${r.priority}`} className="flex items-start gap-3 rounded-lg border border-border/60 p-2.5">
                    <Target className="w-4 h-4 shrink-0 text-primary mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{r.decline_reason_standard}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{r.recommended_action}</p>
                      {r.estimated_recoverable_value != null && r.estimated_recoverable_value > 0 && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Est. recoverable: ${r.estimated_recoverable_value.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <Button variant="outline" size="sm" className="mt-3" asChild>
              <Link to="/reason-codes">
                View all Reason Codes <ArrowRight className="w-3 h-3 ml-1" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </motion.div>

      {/* Where to act — operations and insights */}
      <motion.div variants={dashboardItem}>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
          Where to act
        </h2>
      </motion.div>

      <motion.div variants={dashboardItem}>
        <OnlineFeaturesCard />
      </motion.div>

      <motion.div variants={dashboardItem}>
      <Card
        className="cursor-pointer hover:shadow-lg hover:border-primary/30 transition-all duration-300"
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
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <MessageSquareText className="h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">No recent decisions.</p>
              <p className="text-xs text-muted-foreground">Use the Decisioning playground to generate decisions and reasoning.</p>
            </div>
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
      </motion.div>
    </motion.div>
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
          Features from ML and AI stored in the Lakehouse (Setup & Run step 4: run lakehouse_bootstrap.sql). Populate from jobs or decisioning.
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
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <Cpu className="h-10 w-10 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">No features yet.</p>
            <p className="text-xs text-muted-foreground">Complete Setup & Run step 4 (run lakehouse_bootstrap.sql), then populate from ML or agent jobs.</p>
          </div>
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
