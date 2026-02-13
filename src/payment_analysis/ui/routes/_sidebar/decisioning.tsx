import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";

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

export const Route = createFileRoute("/_sidebar/decisioning")({
  component: () => <Decisioning />,
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

      <Card className="business-value-card content-section border-l-4 border-l-primary border-primary/25 bg-gradient-to-r from-primary/10 to-primary/5 shadow-md">
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

      <Card>
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
        <DecisionCard title="Authentication" result={auth.data?.data} notebookId="agent_framework" />
        <DecisionCard title="Retry" result={retry.data?.data} notebookId="agent_framework" />
        <DecisionCard title="Routing" result={routing.data?.data} notebookId="agent_framework" />
      </div>

      <Card>
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
                <li key={r.id} className="flex items-start gap-3 rounded-lg border p-3">
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
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="border-primary/20 bg-primary/5">
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
            />
            <PredictionCard
              title="Risk score"
              icon={<Shield className="w-4 h-4" />}
              result={predictRisk.data?.data}
              render={(d) => d && `${(d.risk_score * 100).toFixed(1)}% risk · ${d.risk_tier}`}
            />
            <PredictionCard
              title="Smart routing"
              icon={<Waypoints className="w-4 h-4" />}
              result={predictRouting.data?.data}
              render={(d) => d && `${d.recommended_solution} (${(d.confidence * 100).toFixed(0)}%)`}
            />
            <PredictionCard
              title="Smart retry"
              icon={<RotateCcw className="w-4 h-4" />}
              result={predictRetry.data?.data}
              render={(d) => d && `${d.should_retry ? "Retry" : "No retry"} · ${(d.retry_success_probability * 100).toFixed(1)}% success`}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PredictionCard<T>({
  title,
  icon,
  result,
  render,
}: {
  title: string;
  icon: React.ReactNode;
  result: T | undefined;
  render: (d: T) => string;
}) {
  const isMock = result && typeof result === "object" && "_source" in result && (result as Record<string, unknown>)._source === "mock";
  return (
    <Card className={isMock ? "border-amber-500/40" : undefined}>
      <CardHeader className="py-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          {icon}
          {title}
          {isMock && (
            <Badge variant="outline" className="ml-auto text-[10px] font-normal border-amber-500/60 text-amber-600 dark:text-amber-400">
              heuristic
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="py-2">
        {result ? (
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
}: {
  title: string;
  result?: unknown;
  notebookId?: string;
}) {
  const obj = typeof result === "object" && result != null ? (result as Record<string, unknown>) : null;
  const variant = obj?.variant as string | undefined;
  const experimentId = obj?.experiment_id as string | undefined;
  const handleCardClick = () => notebookId && openNotebookInDatabricks(notebookId);
  return (
    <Card
      className={notebookId ? "cursor-pointer hover:shadow-md transition-shadow" : undefined}
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
      <CardContent>
        {result ? (
          <pre className="text-xs whitespace-pre-wrap break-words">
            {JSON.stringify(result, null, 2)}
          </pre>
        ) : (
          <p className="text-sm text-muted-foreground">
            Run a decision to see output and an audit id.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

