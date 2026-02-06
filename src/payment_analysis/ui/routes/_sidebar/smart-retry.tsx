import { createFileRoute } from "@tanstack/react-router";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useGetRetryPerformance } from "@/lib/api";
import { getDashboardUrl } from "@/config/workspace";

const openInDatabricks = (url: string) => {
  if (url) window.open(url, "_blank");
};

export const Route = createFileRoute("/_sidebar/smart-retry")({
  component: () => <SmartRetry />,
});

function SmartRetry() {
  const q = useGetRetryPerformance({ params: { limit: 50 } });

  const rows = q.data?.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Smart Retry</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Retry performance split by recurrence vs reattempt scenarios (demo
          scaffold).
        </p>
      </div>

      <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))}>
        <CardHeader>
          <CardTitle>Top retry cohorts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {q.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : q.isError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load retry performance.
            </p>
          ) : rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No data yet. Run the simulator + Lakeflow to
              populate UC views.
            </p>
          ) : (
            rows.map((r) => (
              <div
                key={`${r.retry_scenario}-${r.decline_reason_standard}-${r.retry_count}`}
                className="flex items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{r.retry_scenario}</Badge>
                    <span className="font-mono text-sm">
                      {r.decline_reason_standard}
                    </span>
                    <Badge variant="outline">attempt {r.retry_count}</Badge>
                    <Badge>{r.success_rate_pct}%</Badge>
                    {r.incremental_lift_pct != null && (
                      <Badge
                        variant={
                          r.incremental_lift_pct > 0
                            ? "default"
                            : "destructive"
                        }
                      >
                        {r.incremental_lift_pct > 0 ? "+" : ""}
                        {r.incremental_lift_pct}% vs baseline
                      </Badge>
                    )}
                    <Badge variant="outline">{r.effectiveness}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    recovered ${r.recovered_value.toFixed(2)} · avg fraud{" "}
                    {r.avg_fraud_score.toFixed(3)}
                    {r.avg_time_since_last_attempt_s != null &&
                      ` · avg wait ${Math.round(r.avg_time_since_last_attempt_s)}s`}
                    {r.avg_prior_approvals != null &&
                      ` · prior approvals ${r.avg_prior_approvals.toFixed(1)}`}
                  </div>
                </div>
                <Badge variant="secondary">{r.retry_attempts}</Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
