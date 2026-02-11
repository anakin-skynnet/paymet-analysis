import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useGetReasonCodeInsights,
  useGetEntrySystemDistribution,
  useGetFalseInsightsMetric,
  useSubmitInsightFeedback,
} from "@/lib/api";
import { getDashboardUrl, openInDatabricks } from "@/config/workspace";
import { useEntity } from "@/contexts/entity-context";
import { ExternalLink, CheckCircle2, AlertTriangle, Target } from "lucide-react";

export const Route = createFileRoute("/_sidebar/reason-codes")({
  component: () => <ReasonCodes />,
});

const ENTRY_DISTRIBUTION = [
  { system: "PD (Digital Platform)", pct: "~62%", desc: "Monthly volume" },
  { system: "WS (WebService)", pct: "~34%", desc: "Monthly volume" },
  { system: "SEP", pct: "~3%", desc: "Single Entry Point" },
  { system: "Checkout", pct: "~1%", desc: "Monthly volume" },
] as const;

const INTELLIGENCE_OUTCOMES = [
  "Consolidate declines across Checkout, PD, WS, SEP into one view",
  "Standardize decline reasons into a single taxonomy (reason codes)",
  "Identify approval-rate degradation patterns and root causes",
  "Translate patterns into actionable insights with recommended actions and estimated uplift",
  "Feedback loop: capture expert reviews and results to improve model accuracy",
];

function ReasonCodes() {
  const { entity } = useEntity();
  const entryQ = useGetEntrySystemDistribution({ params: { entity } });
  const q = useGetReasonCodeInsights({ params: { entity, limit: 30 } });
  const falseQ = useGetFalseInsightsMetric({ params: { days: 30 } });
  const submitFeedback = useSubmitInsightFeedback();

  const [insightId, setInsightId] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [verdict, setVerdict] = useState<"valid" | "invalid" | "non_actionable">("valid");
  const [reason, setReason] = useState("");
  const [submitMsg, setSubmitMsg] = useState<string | null>(null);

  const rows = q.data?.data ?? [];
  const entryRows = entryQ.data?.data ?? [];
  const falseRows = falseQ.data?.data ?? [];

  return (
    <div className="space-y-8">
      {/* Hero: identify reasons and factors impacting approval rates */}
      <div>
        <h1 className="text-2xl font-bold font-heading tracking-tight text-foreground">
          Reason Codes
        </h1>
        <p className="mt-1 text-sm font-medium text-primary">
          Identify reasons and factors impacting approval rates
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Unified decline intelligence · Brazil · Full e‑commerce visibility across entry systems
        </p>
        <p className="mt-3 text-sm text-muted-foreground max-w-2xl">
          Consolidate declines from Checkout, PD, WS, and SEP into one view; standardize reason codes and get recommended actions to accelerate approvals. Data is mapped from four entry systems that act as gates for merchant transactions.
        </p>
      </div>

      {/* Entry systems & distribution */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Entry systems & transaction distribution</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Brazil, monthly view. Checkout, PD, WS, and SEP return the final response to the merchant; consolidation must avoid double-counting.
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-4">
          {ENTRY_DISTRIBUTION.map((e) => (
            <Card key={e.system} className="border-border/80">
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">{e.system}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xl font-semibold tabular-nums">{e.pct}</p>
                <p className="text-xs text-muted-foreground">{e.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
        <Card className="border-border/80">
          <CardHeader>
            <CardTitle className="text-base">Entry system coverage (live data)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {entryQ.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : entryQ.isError ? (
              <p className="text-sm text-destructive">Failed to load entry system distribution.</p>
            ) : entryRows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data yet.</p>
            ) : (
              entryRows.map((r) => (
                <div key={r.entry_system} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                  <Badge variant="secondary">{r.entry_system}</Badge>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-muted-foreground">Approval {r.approval_rate_pct}%</span>
                    <Badge variant="outline">{r.transaction_count} tx</Badge>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
        <Button variant="outline" size="sm" className="mt-3 gap-2" onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/decline_analysis"))}>
          Open decline analysis dashboard <ExternalLink className="h-3.5 w-3.5" />
        </Button>
      </section>

      {/* Intelligence layer – outcomes */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Intelligence layer – what we deliver</h2>
        <p className="text-sm text-muted-foreground mb-4">
          A data- and AI-driven layer that supports descriptive, diagnostic, and prescriptive decision making.
        </p>
        <ul className="space-y-2">
          {INTELLIGENCE_OUTCOMES.map((outcome, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-primary mt-0.5" />
              <span className="text-muted-foreground">{outcome}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Counter metric: False Insights */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Counter metric: False Insights</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Percentage of insights marked as invalid or non‑actionable by domain specialists after review. Keeps speed vs. accuracy balanced and embeds expert validation in the learning loop.
        </p>
        <Card className="border-border/80">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              False insights rate (quality control)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {falseQ.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : falseQ.isError ? (
              <p className="text-sm text-destructive">Failed to load metric.</p>
            ) : falseRows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No feedback data yet. Expert reviews populate this metric.</p>
            ) : (
              falseRows.map((r) => (
                <div key={r.event_date} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                  <span className="text-sm font-mono">{r.event_date}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant={(r.false_insights_pct ?? 0) > 20 ? "destructive" : "secondary"}>
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
      </section>

      {/* Top standardized decline reasons & recommended actions */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Insights & recommended actions</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Top standardized decline reasons with suggested remediation and estimated recoverable value.
        </p>
        <Card className="border-border/80">
          <CardContent className="pt-6 space-y-4">
            {q.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : q.isError ? (
              <p className="text-sm text-destructive">Failed to load reason codes.</p>
            ) : rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data yet. Run the simulator and ETL to populate views.</p>
            ) : (
              rows.map((r) => (
                <div
                  key={`${r.entry_system}-${r.flow_type}-${r.decline_reason_standard}-${r.priority}`}
                  className="rounded-lg border border-border/60 p-3 space-y-2"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-medium">{r.decline_reason_standard}</span>
                    <Badge variant="outline">{r.decline_reason_group}</Badge>
                    <Badge variant="secondary">{r.entry_system}</Badge>
                    <Badge variant="secondary">{r.flow_type}</Badge>
                    {r.pct_of_declines != null && <Badge>{r.pct_of_declines}% of declines</Badge>}
                    <Badge variant="outline">Priority {r.priority}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    <Target className="h-3.5 w-3.5 inline mr-1" />
                    Action: {r.recommended_action}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Est. recoverable: {r.estimated_recoverable_declines} declines · ${r.estimated_recoverable_value.toFixed(2)}
                  </p>
                  <div className="flex justify-end">
                    <Badge variant="secondary">{r.decline_count} declines</Badge>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>

      {/* Expert review – learning loop */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Expert review (learning loop)</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Mark an insight as valid, invalid, or non‑actionable. This updates the False Insights counter‑metric and improves future recommendations.
        </p>
        <Card className="border-border/80">
          <CardContent className="pt-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Insight ID</label>
                <Input value={insightId} onChange={(e) => setInsightId(e.target.value)} placeholder="ins-001" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Reviewer</label>
                <Input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="analyst@company.com" />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Verdict</label>
              <div className="flex flex-wrap gap-2">
                {(["valid", "invalid", "non_actionable"] as const).map((v) => (
                  <Button key={v} type="button" variant={verdict === v ? "default" : "secondary"} onClick={() => setVerdict(v)}>
                    {v.replace("_", " ")}
                  </Button>
                ))}
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Reason (optional)</label>
              <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this insight invalid or non-actionable?" />
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
                      setSubmitMsg("Not accepted (Databricks unavailable). Configure workspace access and retry.");
                    }
                  } catch {
                    setSubmitMsg("Failed to submit feedback.");
                  }
                }}
              >
                {submitFeedback.isPending ? "Submitting…" : "Submit review"}
              </Button>
              {submitMsg && <span className="text-sm text-muted-foreground">{submitMsg}</span>}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
