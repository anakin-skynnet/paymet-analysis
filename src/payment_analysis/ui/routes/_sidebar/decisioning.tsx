import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import {
  type DecisionContext,
  useDecideAuthentication,
  useDecideRetry,
  useDecideRouting,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Code2, Brain } from "lucide-react";

export const Route = createFileRoute("/_sidebar/decisioning")({
  component: () => <Decisioning />,
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

  return (
    <div className="space-y-6">
      {/* Header with Notebook Links */}
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Decisioning playground</h1>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebook("train_models")}
            >
              <Brain className="w-4 h-4 mr-2" />
              ML Models
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebook("agent_framework")}
            >
              <Code2 className="w-4 h-4 mr-2" />
              Agent Framework
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          Test ML-powered decision policies for authentication, retry, and routing
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Context</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Merchant</label>
            <Input
              value={ctx.merchant_id}
              onChange={(e) => setCtx({ ...ctx, merchant_id: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Amount (minor)</label>
            <Input
              type="number"
              value={ctx.amount_minor}
              onChange={(e) =>
                setCtx({ ...ctx, amount_minor: Number(e.target.value) })
              }
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Currency</label>
            <Input
              value={ctx.currency}
              onChange={(e) => setCtx({ ...ctx, currency: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Risk score (0-1)</label>
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
            <label className="text-sm text-muted-foreground">A/B Experiment ID (optional)</label>
            <Input
              placeholder="e.g. experiment-uuid"
              value={ctx.experiment_id ?? ""}
              onChange={(e) =>
                setCtx({ ...ctx, experiment_id: e.target.value || undefined })
              }
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Subject key (optional, default: merchant_id)</label>
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
    </div>
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
  const handleCardClick = () => notebookId && openNotebook(notebookId);
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

