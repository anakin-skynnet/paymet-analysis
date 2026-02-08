import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { declineSummary, useGetReasonCodeInsights, type ReasonCodeInsightOut } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExternalLink, Code2, TrendingUp, Target, ArrowRight } from "lucide-react";
import { getDashboardUrl } from "@/config/workspace";
import { useEntity } from "@/contexts/entity-context";

export const Route = createFileRoute("/_sidebar/declines")({
  component: () => <Declines />,
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
  const dashboardUrl = getDashboardUrl("/sql/dashboards/decline_analysis");
  window.open(dashboardUrl, "_blank");
};

function Declines() {
  const { entity } = useEntity();
  const q = useQuery({
    queryKey: ["declines", "summary"],
    queryFn: () => declineSummary(),
  });
  const { data: reasonCodeData } = useGetReasonCodeInsights({ params: { entity, limit: 5 } });
  const recommendedActions = reasonCodeData?.data ?? [];

  const buckets = q.data?.data ?? [];

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
              onClick={() => openNotebook("gold_views_sql")}
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
          {buckets.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No decline data yet. Post some `AuthorizationEvent`s via the Analytics
              API to populate this.
            </p>
          ) : (
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
          {recommendedActions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No reason-code insights yet. Run gold views and open Reason Codes for full insights and recommended actions.
            </p>
          ) : (
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

