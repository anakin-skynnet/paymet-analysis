import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useGetReasonCodeInsightsBr,
  useGetEntrySystemDistributionBr,
  useGetFalseInsightsMetric,
  useSubmitInsightFeedback,
} from "@/lib/api";

export const Route = createFileRoute("/_sidebar/reason-codes")({
  component: () => <ReasonCodes />,
});

function ReasonCodes() {
  const entryQ = useGetEntrySystemDistributionBr();
  const q = useGetReasonCodeInsightsBr({ params: { limit: 30 } });
  const falseQ = useGetFalseInsightsMetric({ params: { days: 30 } });
  const submitFeedback = useSubmitInsightFeedback();

  const [insightId, setInsightId] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [verdict, setVerdict] = useState<"valid" | "invalid" | "non_actionable">(
    "valid",
  );
  const [reason, setReason] = useState("");
  const [submitMsg, setSubmitMsg] = useState<string | null>(null);

  const rows = q.data?.data ?? [];
  const entryRows = entryQ.data?.data ?? [];
  const falseRows = falseQ.data?.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Reason Codes (Brazil)</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Unified decline taxonomy across entry systems (demo scaffold).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Entry system coverage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {entryQ.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : entryQ.isError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load entry system distribution.
            </p>
          ) : entryRows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No data yet.</p>
          ) : (
            entryRows.map((r) => (
              <div
                key={r.entry_system}
                className="flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{r.entry_system}</Badge>
                  <span className="text-sm text-muted-foreground">
                    approval {r.approval_rate_pct}%
                  </span>
                </div>
                <Badge variant="secondary">{r.transaction_count}</Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Counter-metric: False Insights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {falseQ.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : falseQ.isError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load false insights metric.
            </p>
          ) : falseRows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No feedback data yet. Expert reviews populate this metric.
            </p>
          ) : (
            falseRows.map((r) => (
              <div
                key={r.event_date}
                className="flex items-center justify-between"
              >
                <span className="text-sm font-mono">{r.event_date}</span>
                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      (r.false_insights_pct ?? 0) > 20
                        ? "destructive"
                        : "secondary"
                    }
                  >
                    {r.false_insights_pct ?? 0}% false
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {r.false_insights}/{r.reviewed_insights} reviewed
                  </span>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Top standardized decline reasons</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {q.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : q.isError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load reason codes.
            </p>
          ) : rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No data yet. Run the simulator + Lakeflow Declarative Pipeline to
              populate UC views.
            </p>
          ) : (
            rows.map((r) => (
              <div
                key={`${r.entry_system}-${r.flow_type}-${r.decline_reason_standard}-${r.priority}`}
                className="flex items-start justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm">
                      {r.decline_reason_standard}
                    </span>
                    <Badge variant="outline">{r.decline_reason_group}</Badge>
                    <Badge variant="secondary">{r.entry_system}</Badge>
                    <Badge variant="secondary">{r.flow_type}</Badge>
                    {r.pct_of_declines != null ? (
                      <Badge>{r.pct_of_declines}%</Badge>
                    ) : null}
                    <Badge variant="outline">P{r.priority}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Action: {r.recommended_action}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Est. recoverable: {r.estimated_recoverable_declines}{" "}
                    declines · ${r.estimated_recoverable_value.toFixed(2)}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <Badge variant="secondary">{r.decline_count}</Badge>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Expert review (learning loop)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Mark an insight as valid/invalid/non-actionable. This updates the
            False Insights counter-metric (when Databricks is available).
          </p>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">insight_id</div>
              <Input
                value={insightId}
                onChange={(e) => setInsightId(e.target.value)}
                placeholder="ins-001"
              />
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">reviewer</div>
              <Input
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                placeholder="analyst@company.com"
              />
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">verdict</div>
            <div className="flex flex-wrap gap-2">
              {(
                ["valid", "invalid", "non_actionable"] as Array<
                  "valid" | "invalid" | "non_actionable"
                >
              ).map((v) => (
                <Button
                  key={v}
                  type="button"
                  variant={verdict === v ? "default" : "secondary"}
                  onClick={() => setVerdict(v)}
                >
                  {v}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">reason (optional)</div>
            <Input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why is this insight invalid/non-actionable?"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              disabled={submitFeedback.isPending || insightId.trim().length === 0}
              onClick={async () => {
                setSubmitMsg(null);
                try {
                  const resp = await submitFeedback.mutateAsync({
                    insight_id: insightId.trim(),
                    insight_type: "reason_code_insight",
                    verdict,
                    reviewer: reviewer.trim().length ? reviewer.trim() : null,
                    reason: reason.trim().length ? reason.trim() : null,
                    model_version: null,
                    prompt_version: null,
                  });

                  if (resp.data.accepted) {
                    setSubmitMsg("Submitted. Thanks — counter-metric will update shortly.");
                    setReason("");
                    await falseQ.refetch();
                  } else {
                    setSubmitMsg(
                      "Not accepted (Databricks unavailable). Configure workspace access and retry.",
                    );
                  }
                } catch {
                  setSubmitMsg("Failed to submit feedback.");
                }
              }}
            >
              {submitFeedback.isPending ? "Submitting…" : "Submit review"}
            </Button>
            {submitMsg ? (
              <span className="text-sm text-muted-foreground">{submitMsg}</span>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
