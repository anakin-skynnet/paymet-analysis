import { createFileRoute, Link } from "@tanstack/react-router";

import { useDeclineSummary, useGetReasonCodeInsights, type ReasonCodeInsightOut } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ExternalLink, Code2, TrendingUp, Target, ArrowRight, AlertCircle } from "lucide-react";
import { getDashboardUrl, openInDatabricks } from "@/config/workspace";
import { openNotebookInDatabricks } from "@/lib/notebooks";
import { useEntity } from "@/contexts/entity-context";

export const Route = createFileRoute("/_sidebar/declines")({
  component: () => <Declines />,
});

const openDashboard = () => {
  openInDatabricks(getDashboardUrl("/sql/dashboards/decline_analysis"));
};

function Declines() {
  const { entity } = useEntity();
  const { data: summaryData, isLoading: summaryLoading, isError: summaryError } = useDeclineSummary();
  const { data: reasonCodeData, isLoading: reasonCodeLoading, isError: reasonCodeError } = useGetReasonCodeInsights({ params: { entity, limit: 5 } });
  const buckets = summaryData?.data ?? [];
  const recommendedActions = reasonCodeData?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Hero: decline patterns and factors delaying approvals */}
      <div>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h1 className="text-2xl font-bold font-heading">Declines</h1>
            <p className="mt-1 text-sm font-medium text-primary">
              Discover conditions and factors delaying approvals
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Decline patterns and recovery. Use Reason Codes for issuer vs reason heatmaps and remediation; use Smart Retry for approval with/without retry.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={openDashboard}
            >
              <TrendingUp className="w-4 h-4 mr-2" />
              Decline Dashboard
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebookInDatabricks("gold_views_sql")}
            >
              <Code2 className="w-4 h-4 mr-2" />
              SQL Views
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
      </div>

      <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={openDashboard} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openDashboard()}>
        <CardHeader>
          <CardTitle>Top decline buckets</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {summaryLoading && (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-8 w-full rounded" />
              ))}
            </div>
          )}
          {summaryError && (
            <Alert variant="destructive" className="rounded-lg">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Could not load decline summary</AlertTitle>
              <AlertDescription>
                Data comes from Databricks. Check connection and run Gold Views to populate decline buckets.
              </AlertDescription>
            </Alert>
          )}
          {!summaryLoading && !summaryError && buckets.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No decline data yet. Post some `AuthorizationEvent`s via the Analytics API to populate this.
            </p>
          )}
          {!summaryLoading && !summaryError && buckets.length > 0 && (
            buckets.map((b) => (
              <div key={b.key} className="flex items-center justify-between">
                <div className="font-mono text-sm">{b.key}</div>
                <Badge variant="secondary">{b.count}</Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-4 h-4 text-primary" />
            Recommended actions to accelerate approvals
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Top conditions delaying approvals and what to do. From Reason Codes (Brazil). Apply these and use Decisioning for real-time auth/retry/routing.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          {reasonCodeLoading && (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          )}
          {reasonCodeError && (
            <Alert variant="destructive" className="rounded-lg">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Could not load reason-code insights</AlertTitle>
              <AlertDescription>
                Data comes from Databricks. Run gold views and ensure Reason Codes table is populated.
              </AlertDescription>
            </Alert>
          )}
          {!reasonCodeLoading && !reasonCodeError && recommendedActions.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No reason-code insights yet. Run gold views and open Reason Codes for full insights and recommended actions.
            </p>
          )}
          {!reasonCodeLoading && !reasonCodeError && recommendedActions.length > 0 && (
            <ul className="space-y-2">
              {recommendedActions.map((r: ReasonCodeInsightOut) => (
                <li key={`${r.entry_system}-${r.decline_reason_standard}-${r.priority}`} className="rounded-lg border border-border/60 p-2.5">
                  <p className="text-sm font-medium">{r.decline_reason_standard}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{r.recommended_action}</p>
                </li>
              ))}
            </ul>
          )}
          <div className="flex flex-wrap gap-2 mt-3">
            <Button variant="outline" size="sm" asChild>
              <Link to="/reason-codes">Reason Codes <ArrowRight className="w-3 h-3 ml-1" /></Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/decisioning">Decisioning playground <ArrowRight className="w-3 h-3 ml-1" /></Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

