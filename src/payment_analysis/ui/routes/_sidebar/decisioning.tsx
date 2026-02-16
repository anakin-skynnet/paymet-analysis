import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ErrorBoundary } from "react-error-boundary";

import {
  type DecisionContext,
  useDecideAuthentication,
  useDecideRetry,
  useDecideRouting,
  useGetRecommendations,
  usePredictApproval,
  usePredictRisk,
  usePredictRouting,
  usePredictRetry,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ExternalLink, Code2, Brain, Database, Sparkles, ArrowRight, Target, AlertCircle, TrendingUp, Shield, Waypoints, RotateCcw } from "lucide-react";
import { openNotebookInDatabricks } from "@/lib/notebooks";

function DecisioningErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
  return (
    <div className="p-6">
      <Card className="glass-card border border-border/80 border-l-4 border-l-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Something went wrong</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : String(error)}</p>
          <Button variant="outline" size="sm" onClick={resetErrorBoundary}>Try again</Button>
        </CardContent>
      </Card>
    </div>
  );
}

export const Route = createFileRoute("/_sidebar/decisioning")({
  component: () => (
    <ErrorBoundary FallbackComponent={DecisioningErrorFallback}>
      <Decisioning />
    </ErrorBoundary>
  ),
});

function Decisioning() {
  const [ctx, setCtx] = useState<DecisionContext & { experiment_id?: string; subject_key?: string }>({
    merchant_id: "m_demo",
    amount_minor: 1999,
    currency: "USD",
    network: "visa",
    card_bin: "411111",
    issuer_country: "US",
    entry_mode: "ecom",
    is_recurring: false,
    attempt_number: 0,
    risk_score: 0.3,
    device_trust_score: 0.95,
    supports_passkey: true,
    metadata: {},
  });

  const auth = useDecideAuthentication();
  const retry = useDecideRetry();
  const routing = useDecideRouting();
  const predictApproval = usePredictApproval();
  const predictRisk = usePredictRisk();
  const predictRouting = usePredictRouting();
  const predictRetry = usePredictRetry();
  const { data: recommendationsData, isLoading: recommendationsLoading, isError: recommendationsError } = useGetRecommendations({
    params: { limit: 20 },
    query: { refetchInterval: 30_000 },
  });
  const recommendations = recommendationsData?.data ?? [];

  const mlFeatures = {
    amount: (ctx.amount_minor ?? 0) / 100,
    fraud_score: ctx.risk_score ?? 0.1,
    device_trust_score: ctx.device_trust_score ?? 0.8,
    is_cross_border: (ctx.issuer_country ?? "US") !== "US",
    retry_count: ctx.attempt_number ?? 0,
    uses_3ds: false,
    merchant_segment: "retail",
    card_network: (ctx.network as string) ?? "visa",
  };

  const runAllPredictions = () => {
    predictApproval.mutate(mlFeatures);
    predictRisk.mutate(mlFeatures);
    predictRouting.mutate(mlFeatures);
    predictRetry.mutate(mlFeatures);
  };

  const predictionsPending =
    predictApproval.isPending ||
    predictRisk.isPending ||
    predictRouting.isPending ||
    predictRetry.isPending;

  return (
    <div className="space-y-6">
      {/* Hero: actionable next steps for leadership */}
      <header className="page-header">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <p className="section-label text-primary font-semibold mb-1">Recommendations &amp; actions</p>
            <h1 className="page-section-title text-2xl md:text-3xl font-bold">What to do next</h1>
            <p className="mt-1 text-base font-medium text-primary">
              Clear next steps to accelerate approval rates — policies, rules, and data-driven recommendations
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Test authentication, retry, and routing policies. Configure rules and use similar-case insights to recover more approvals.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebookInDatabricks("train_models")}
            >
              <Brain className="w-4 h-4 mr-2" />
              ML Models
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebookInDatabricks("agent_framework")}
            >
              <Code2 className="w-4 h-4 mr-2" />
              Agent Framework
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
      </header>

      <Card className="glass-card border border-border/80 business-value-card content-section border-l-4 border-l-primary border-primary/25 bg-gradient-to-r from-primary/10 to-primary/5 shadow-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
            <Target className="w-5 h-5 text-primary shrink-0" />
            How this accelerates approval rates
          </CardTitle>
          <CardDescription className="text-base">
            The platform recommends and automates actions to increase approvals. Use the levers below:
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="flex items-start gap-2">
            <span className="font-medium shrink-0">1.</span>
            <span>Run authentication, retry, and routing decisions below — they apply policies that reduce friction and recover soft declines.</span>
          </p>
          <p className="flex items-start gap-2">
            <span className="font-medium shrink-0">2.</span>
            <span>Define and apply <Link to="/rules" className="text-primary hover:underline inline-flex items-center gap-1">Rules <ArrowRight className="w-3 h-3" /></Link> (Lakehouse). AI agents and batch jobs use them to accelerate approvals.</span>
          </p>
          <p className="flex items-start gap-2">
            <span className="font-medium shrink-0">3.</span>
            <span>Follow the <strong>recommendations</strong> in the card below — they come from similar cases (Vector Search) and rules.</span>
          </p>
          <p className="flex items-start gap-2">
            <span className="font-medium shrink-0">4.</span>
            <span>Act on <Link to="/reason-codes" className="text-primary hover:underline inline-flex items-center gap-1">Reason Codes <ArrowRight className="w-3 h-3" /></Link> insights to fix conditions that delay approvals (e.g. issuer, decline reason).</span>
          </p>
        </CardContent>
      </Card>

      {/* P2 #11: Preset scenarios for quick testing */}
      <Card className="glass-card border border-border/80">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Quick presets</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {([
            { label: "High-risk cross-border", ctx: { merchant_id: "m_intl_travel", amount_minor: 250000, currency: "EUR", issuer_country: "NG", risk_score: 0.82, device_trust_score: 0.45, is_recurring: false, attempt_number: 0, supports_passkey: false, network: "mastercard" } },
            { label: "Subscription retry", ctx: { merchant_id: "m_streaming", amount_minor: 1499, currency: "BRL", issuer_country: "BR", risk_score: 0.1, device_trust_score: 0.92, is_recurring: true, attempt_number: 2, supports_passkey: true, previous_decline_code: "51", previous_decline_reason: "insufficient funds", network: "visa" } },
            { label: "Low-value retail", ctx: { merchant_id: "m_retail_br", amount_minor: 599, currency: "BRL", issuer_country: "BR", risk_score: 0.05, device_trust_score: 0.98, is_recurring: false, attempt_number: 0, supports_passkey: true, network: "elo" } },
            { label: "Fraud-suspected", ctx: { merchant_id: "m_gaming", amount_minor: 50000, currency: "USD", issuer_country: "RU", risk_score: 0.91, device_trust_score: 0.2, is_recurring: false, attempt_number: 0, supports_passkey: false, network: "visa" } },
          ] as const).map((preset) => (
            <Button
              key={preset.label}
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => setCtx({ ...ctx, ...preset.ctx, metadata: {} })}
            >
              {preset.label}
            </Button>
          ))}
        </CardContent>
      </Card>

      <Card className="glass-card border border-border/80">
        <CardHeader>
          <CardTitle>Context</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <Label className="text-muted-foreground">Merchant</Label>
            <Input
              value={ctx.merchant_id}
              onChange={(e) => setCtx({ ...ctx, merchant_id: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label className="text-muted-foreground">Amount (minor)</Label>
            <Input
              type="number"
              value={ctx.amount_minor}
              onChange={(e) =>
                setCtx({ ...ctx, amount_minor: Number(e.target.value) })
              }
            />
          </div>
          <div className="space-y-2">
            <Label className="text-muted-foreground">Currency</Label>
            <Input
              value={ctx.currency}
              onChange={(e) => setCtx({ ...ctx, currency: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label className="text-muted-foreground">Risk score (0-1)</Label>
            <Input
              type="number"
              step="0.01"
              value={ctx.risk_score ?? 0}
              onChange={(e) =>
                setCtx({ ...ctx, risk_score: Number(e.target.value) })
              }
            />
          </div>
          <div className="space-y-2">
            <Label className="text-muted-foreground">A/B Experiment ID (optional)</Label>
            <Input
              placeholder="e.g. experiment-uuid"
              value={ctx.experiment_id ?? ""}
              onChange={(e) =>
                setCtx({ ...ctx, experiment_id: e.target.value || undefined })
              }
            />
          </div>
          <div className="space-y-2">
            <Label className="text-muted-foreground">Subject key (optional, default: merchant_id)</Label>
            <Input
              placeholder="default: merchant_id"
              value={ctx.subject_key ?? ""}
              onChange={(e) =>
                setCtx({ ...ctx, subject_key: e.target.value || undefined })
              }
            />
          </div>

          <div className="flex flex-wrap gap-2 pt-2 md:col-span-2">
            <Button onClick={() => auth.mutate(ctx)} disabled={auth.isPending}>
              Decide authentication
            </Button>
            <Button
              variant="secondary"
              onClick={() => retry.mutate(ctx)}
              disabled={retry.isPending}
            >
              Decide retry
            </Button>
            <Button
              variant="secondary"
              onClick={() => routing.mutate(ctx)}
              disabled={routing.isPending}
            >
              Decide routing
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <DecisionCard title="Authentication" result={auth.data?.data} notebookId="agent_framework" error={auth.error as Error | null} onRetry={() => auth.mutate(ctx)} />
        <DecisionCard title="Retry" result={retry.data?.data} notebookId="agent_framework" error={retry.error as Error | null} onRetry={() => retry.mutate(ctx)} />
        <DecisionCard title="Routing" result={routing.data?.data} notebookId="agent_framework" error={routing.error as Error | null} onRetry={() => routing.mutate(ctx)} />
      </div>

      <Card className="glass-card border border-border/80">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            Similar cases & recommendations (Lakehouse)
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Recommendations from Lakebase or Lakehouse. Run Job 1 (Create Data Repositories) to seed Lakebase; use with Rules to accelerate approval rates.
          </p>
        </CardHeader>
        <CardContent>
          {recommendationsLoading && (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full rounded-lg" />
              ))}
            </div>
          )}
          {recommendationsError && (
            <Alert variant="destructive" className="rounded-lg">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Could not load recommendations</AlertTitle>
              <AlertDescription>
                Data comes from Databricks (Lakehouse or Lakebase). Check connection and run the Gold Views job.
              </AlertDescription>
            </Alert>
          )}
          {!recommendationsLoading && !recommendationsError && recommendations.length === 0 && (
            <p className="text-sm text-muted-foreground">No recommendations yet. Run the gold views and populate approval_recommendations in the Lakehouse.</p>
          )}
          {!recommendationsLoading && !recommendationsError && recommendations.length > 0 && (
            <ul className="space-y-3">
              {recommendations.map((r) => (
                <li key={r.id} className="rounded-lg border p-3 space-y-2">
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{r.context_summary}</p>
                      <p className="text-sm text-muted-foreground mt-1">{r.recommended_action}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={r.source_type === "vector_search" ? "default" : "secondary"} className="gap-1">
                        {r.source_type === "vector_search" ? <Sparkles className="w-3 h-3" /> : null}
                        {r.source_type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{(r.score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  {/* P1 #7: Actionable buttons — bridge data-to-action gap */}
                  <div className="flex gap-2 pt-1">
                    <Button variant="outline" size="sm" className="h-7 text-xs" asChild>
                      <Link to="/rules">
                        Create Rule
                        <ArrowRight className="w-3 h-3 ml-1" />
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => {
                        setCtx({
                          ...ctx,
                          risk_score: r.score ?? ctx.risk_score,
                          metadata: { ...ctx.metadata, agent_recommendation: r.recommended_action },
                        });
                      }}
                    >
                      Apply to Context
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="glass-card border border-border/80 border-primary/20 bg-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            Live ML predictions (Model Serving)
          </CardTitle>
          <CardDescription>
            Run real-time inference with the same context as above. Approval propensity, risk score, smart routing, and smart retry models accelerate approval rates by guiding authentication, routing, and recovery decisions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            onClick={runAllPredictions}
            disabled={predictionsPending}
          >
            {predictionsPending ? "Running…" : "Run all ML predictions"}
          </Button>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <PredictionCard
              title="Approval propensity"
              icon={<TrendingUp className="w-4 h-4" />}
              result={predictApproval.data?.data}
              render={(d) => d && `${(d.approval_probability * 100).toFixed(1)}% approve · ${d.should_approve ? "Approve" : "Decline"}`}
              error={predictApproval.error as Error | null}
              onRetry={() => predictApproval.mutate(mlFeatures)}
            />
            <PredictionCard
              title="Risk score"
              icon={<Shield className="w-4 h-4" />}
              result={predictRisk.data?.data}
              render={(d) => d && `${(d.risk_score * 100).toFixed(1)}% risk · ${d.risk_tier}`}
              error={predictRisk.error as Error | null}
              onRetry={() => predictRisk.mutate(mlFeatures)}
            />
            <PredictionCard
              title="Smart routing"
              icon={<Waypoints className="w-4 h-4" />}
              result={predictRouting.data?.data}
              render={(d) => d && `${d.recommended_solution} (${(d.confidence * 100).toFixed(0)}%)`}
              error={predictRouting.error as Error | null}
              onRetry={() => predictRouting.mutate(mlFeatures)}
            />
            <PredictionCard
              title="Smart retry"
              icon={<RotateCcw className="w-4 h-4" />}
              result={predictRetry.data?.data}
              render={(d) => d && `${d.should_retry ? "Retry" : "No retry"} · ${(d.retry_success_probability * 100).toFixed(1)}% success`}
              error={predictRetry.error as Error | null}
              onRetry={() => predictRetry.mutate(mlFeatures)}
            />
          </div>
        </CardContent>
      </Card>

      <ApprovalSimulator />
    </div>
  );
}

function PredictionCard<T>({
  title,
  icon,
  result,
  render,
  error,
  onRetry,
}: {
  title: string;
  icon: React.ReactNode;
  result: T | undefined;
  render: (d: T) => string;
  error?: Error | null;
  onRetry?: () => void;
}) {
  const isMock = result && typeof result === "object" && "_source" in result && (result as Record<string, unknown>)._source === "mock";
  const hasError = !!error && !result;
  return (
    <Card className={hasError ? "glass-card border border-border/80 border-destructive/40" : isMock ? "glass-card border border-border/80 border-amber-500/40" : "glass-card border border-border/80"}>
      <CardHeader className="py-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          {icon}
          {title}
          {hasError && (
            <Badge variant="outline" className="ml-auto text-[10px] font-normal border-destructive/60 text-destructive">
              error
            </Badge>
          )}
          {isMock && !hasError && (
            <Badge variant="outline" className="ml-auto text-[10px] font-normal border-amber-500/60 text-amber-600 dark:text-amber-400">
              heuristic
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="py-2">
        {hasError ? (
          <div className="space-y-1">
            <p className="text-xs text-destructive">{error.message.length > 80 ? `${error.message.slice(0, 80)}…` : error.message}</p>
            {onRetry && (
              <button onClick={onRetry} className="text-xs text-primary underline underline-offset-2 hover:text-primary/80">
                Retry
              </button>
            )}
          </div>
        ) : result ? (
          <p className="text-sm text-muted-foreground">{render(result)}</p>
        ) : (
          <p className="text-xs text-muted-foreground">Run predictions to see result.</p>
        )}
      </CardContent>
    </Card>
  );
}

function DecisionCard({
  title,
  result,
  notebookId,
  error,
  onRetry,
}: {
  title: string;
  result?: unknown;
  notebookId?: string;
  error?: Error | null;
  onRetry?: () => void;
}) {
  const hasError = !!error && !result;
  const obj = typeof result === "object" && result != null ? (result as Record<string, unknown>) : null;
  const variant = obj?.variant as string | undefined;
  const experimentId = obj?.experiment_id as string | undefined;
  const handleCardClick = () => notebookId && openNotebookInDatabricks(notebookId);

  const factors = extractDecisionFactors(obj);

  return (
    <Card
      className={`glass-card border border-border/80 ${notebookId ? "cursor-pointer hover:shadow-md transition-shadow" : ""}`}
      onClick={notebookId ? handleCardClick : undefined}
      role={notebookId ? "button" : undefined}
      tabIndex={notebookId ? 0 : undefined}
      onKeyDown={notebookId ? (e) => e.key === "Enter" && handleCardClick() : undefined}
    >
      <CardHeader>
        <CardTitle className="flex items-center justify-between flex-wrap gap-2">
          <span>{title}</span>
          <div className="flex items-center gap-2">
            {variant != null && (
              <Badge variant="secondary">A/B: {variant}</Badge>
            )}
            {obj?.audit_id != null && (
              <Badge variant="outline">{String(obj.audit_id)}</Badge>
            )}
          </div>
        </CardTitle>
        {experimentId != null && (
          <p className="text-xs text-muted-foreground mt-1">Experiment: {experimentId}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {hasError ? (
          <div className="space-y-2">
            <p className="text-xs text-destructive">{error.message.length > 100 ? `${error.message.slice(0, 100)}…` : error.message}</p>
            {onRetry && (
              <button onClick={(e) => { e.stopPropagation(); onRetry(); }} className="text-xs text-primary underline underline-offset-2 hover:text-primary/80">
                Retry
              </button>
            )}
          </div>
        ) : result ? (
          <>
            {factors.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Decision factors</p>
                {factors.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div
                      className={`w-2 h-2 rounded-full shrink-0 ${
                        f.impact === "positive" ? "bg-green-500" : f.impact === "negative" ? "bg-red-500" : "bg-amber-500"
                      }`}
                    />
                    <span className="text-muted-foreground">{f.label}:</span>
                    <span className="font-medium">{f.value}</span>
                  </div>
                ))}
              </div>
            )}
            {/* Decision Explainability: Why this decision? */}
            {obj?.reason && (
              <div className="rounded-lg bg-primary/5 border border-primary/20 p-2.5 space-y-1">
                <p className="text-xs font-medium text-primary uppercase tracking-wider">Why this decision</p>
                <p className="text-xs text-foreground">{String(obj.reason)}</p>
              </div>
            )}
            {(obj?.agent_recommendation || obj?.vs_similar_count || obj?.matched_rule_name || obj?.ml_approval_probability != null) && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Decision context</p>
                {obj?.ml_approval_probability != null && (
                  <div className="flex items-center gap-2 text-xs">
                    <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                    <span className="text-muted-foreground">ML approval:</span>
                    <span className="font-medium">{(Number(obj.ml_approval_probability) * 100).toFixed(1)}%</span>
                  </div>
                )}
                {obj?.ml_risk_score != null && (
                  <div className="flex items-center gap-2 text-xs">
                    <div className="w-2 h-2 rounded-full bg-orange-500 shrink-0" />
                    <span className="text-muted-foreground">ML risk:</span>
                    <span className="font-medium">{(Number(obj.ml_risk_score) * 100).toFixed(1)}%</span>
                  </div>
                )}
                {obj?.matched_rule_name != null && (
                  <div className="flex items-center gap-2 text-xs">
                    <div className="w-2 h-2 rounded-full bg-purple-500 shrink-0" />
                    <span className="text-muted-foreground">Rule:</span>
                    <span className="font-medium">{String(obj.matched_rule_name)}</span>
                  </div>
                )}
                {obj?.vs_similar_count != null && (
                  <div className="flex items-center gap-2 text-xs">
                    <div className="w-2 h-2 rounded-full bg-cyan-500 shrink-0" />
                    <span className="text-muted-foreground">Similar cases:</span>
                    <span className="font-medium">{String(obj.vs_similar_count)} found {obj.vs_similar_avg_approval_rate != null ? `(${Number(obj.vs_similar_avg_approval_rate).toFixed(1)}% avg approval)` : ""}</span>
                  </div>
                )}
                {obj?.agent_recommendation != null && (
                  <div className="flex items-center gap-2 text-xs">
                    <div className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                    <span className="text-muted-foreground">Agent:</span>
                    <span className="font-medium">{String(obj.agent_recommendation)}</span>
                  </div>
                )}
              </div>
            )}
            <details className="text-xs">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground">Raw JSON</summary>
              <pre className="mt-1 whitespace-pre-wrap break-words text-muted-foreground">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            Run a decision to see output and an audit id.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

type Factor = { label: string; value: string; impact: "positive" | "negative" | "neutral" };

function extractDecisionFactors(obj: Record<string, unknown> | null): Factor[] {
  if (!obj) return [];
  const factors: Factor[] = [];

  if (obj.risk_level != null) {
    const rl = String(obj.risk_level).toLowerCase();
    factors.push({
      label: "Risk level",
      value: String(obj.risk_level),
      impact: rl === "low" ? "positive" : rl === "high" ? "negative" : "neutral",
    });
  }
  if (obj.method != null) {
    factors.push({ label: "Auth method", value: String(obj.method), impact: "neutral" });
  }
  if (obj.should_retry != null) {
    factors.push({
      label: "Should retry",
      value: obj.should_retry ? "Yes" : "No",
      impact: obj.should_retry ? "positive" : "negative",
    });
  }
  if (obj.retry_delay_seconds != null) {
    factors.push({ label: "Retry delay", value: `${obj.retry_delay_seconds}s`, impact: "neutral" });
  }
  if (obj.recommended_solution != null) {
    factors.push({ label: "Recommended route", value: String(obj.recommended_solution), impact: "positive" });
  }
  if (obj.reason != null) {
    factors.push({ label: "Reason", value: String(obj.reason), impact: "neutral" });
  }
  if (typeof obj.metadata === "object" && obj.metadata) {
    const meta = obj.metadata as Record<string, unknown>;
    if (meta.ml_risk_score != null) {
      const score = Number(meta.ml_risk_score);
      factors.push({
        label: "ML risk score",
        value: `${(score * 100).toFixed(1)}%`,
        impact: score > 0.5 ? "negative" : score > 0.3 ? "neutral" : "positive",
      });
    }
    if (meta.ml_approval_probability != null) {
      const prob = Number(meta.ml_approval_probability);
      factors.push({
        label: "ML approval probability",
        value: `${(prob * 100).toFixed(1)}%`,
        impact: prob > 0.7 ? "positive" : prob > 0.4 ? "neutral" : "negative",
      });
    }
    if (meta.agent_recommendation) {
      factors.push({
        label: "Agent recommendation",
        value: String(meta.agent_recommendation),
        impact: "positive",
      });
    }
    if (meta.vs_similar_avg_approval_rate != null) {
      factors.push({
        label: "Similar cases approval",
        value: `${Number(meta.vs_similar_avg_approval_rate).toFixed(1)}%`,
        impact: Number(meta.vs_similar_avg_approval_rate) > 70 ? "positive" : "neutral",
      });
    }
    if (meta.matched_rule_name) {
      factors.push({ label: "Matched rule", value: String(meta.matched_rule_name), impact: "neutral" });
    }
  }
  return factors;
}

function ApprovalSimulator() {
  const [riskScore, setRiskScore] = useState(0.3);
  const [amount, setAmount] = useState(1999);
  const [deviceTrust, setDeviceTrust] = useState(0.95);
  const [is3ds, setIs3ds] = useState(true);
  const predictApproval = usePredictApproval();

  // Call the ML model serving endpoint for a real prediction
  const runSimulation = () => {
    predictApproval.mutate({
      amount: amount / 100,
      fraud_score: riskScore,
      device_trust_score: deviceTrust,
      is_cross_border: false,
      retry_count: 0,
      uses_3ds: is3ds,
      merchant_segment: "retail",
      card_network: "visa",
    });
  };

  // Use ML model result when available, otherwise compute a local heuristic as preview
  const mlResult = predictApproval.data?.data as { approval_probability?: number; should_approve?: boolean; _source?: string } | undefined;
  const mlProb = mlResult?.approval_probability;
  const isFromModel = mlResult != null && mlResult._source !== "mock";

  const heuristicProb = Math.min(
    0.99,
    Math.max(
      0.05,
      0.7 + 0.15 * deviceTrust - 0.25 * riskScore - 0.05 * (amount > 50000 ? 1 : 0) + 0.08 * (is3ds ? 1 : 0),
    ),
  );
  const simApprovalProb = mlProb ?? heuristicProb;

  const riskLevel = riskScore > 0.75 ? "High" : riskScore > 0.35 ? "Medium" : "Low";
  const riskColor = riskScore > 0.75 ? "text-red-500" : riskScore > 0.35 ? "text-amber-500" : "text-green-500";
  const approvalColor = simApprovalProb > 0.7 ? "text-green-500" : simApprovalProb > 0.4 ? "text-amber-500" : "text-red-500";

  return (
    <Card className="glass-card border border-border/80">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          Approval Rate Simulator
          {isFromModel ? (
            <Badge variant="default" className="ml-auto text-[10px]">ML Model</Badge>
          ) : mlResult ? (
            <Badge variant="outline" className="ml-auto text-[10px] border-amber-500/60 text-amber-500">heuristic</Badge>
          ) : null}
        </CardTitle>
        <CardDescription>
          Adjust parameters and run a prediction against the Databricks Model Serving endpoint.
          The approval propensity model scores transactions in real time.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label className="text-muted-foreground">Risk Score: <span className={`font-medium ${riskColor}`}>{riskScore.toFixed(2)}</span></Label>
            <input
              type="range" min="0" max="1" step="0.01"
              value={riskScore}
              onChange={(e) => setRiskScore(Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-muted-foreground">Amount (minor): <span className="font-medium">{amount}</span></Label>
            <input
              type="range" min="100" max="100000" step="100"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-muted-foreground">Device Trust: <span className="font-medium">{deviceTrust.toFixed(2)}</span></Label>
            <input
              type="range" min="0" max="1" step="0.01"
              value={deviceTrust}
              onChange={(e) => setDeviceTrust(Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
          <div className="flex items-center gap-2 pt-4">
            <input
              type="checkbox" id="sim3ds" checked={is3ds}
              onChange={(e) => setIs3ds(e.target.checked)}
              className="accent-primary"
            />
            <Label htmlFor="sim3ds" className="text-muted-foreground cursor-pointer">3D Secure enabled</Label>
          </div>
        </div>
        <Button onClick={runSimulation} disabled={predictApproval.isPending} size="sm">
          {predictApproval.isPending ? "Predicting…" : "Run ML prediction"}
        </Button>
        <div className="grid grid-cols-3 gap-3 pt-2">
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground">Estimated Approval</p>
            <p className={`text-2xl font-bold tabular-nums ${approvalColor}`}>{(simApprovalProb * 100).toFixed(1)}%</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground">Risk Level</p>
            <p className={`text-2xl font-bold ${riskColor}`}>{riskLevel}</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground">Suggested Action</p>
            <p className="text-lg font-bold text-foreground">
              {mlResult?.should_approve != null
                ? mlResult.should_approve ? "Approve" : "Challenge"
                : simApprovalProb > 0.7 ? "Approve" : simApprovalProb > 0.4 ? "Review" : "Challenge"}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

