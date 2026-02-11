import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useGetRetryPerformance } from "@/lib/api";
import { getDashboardUrl, openInDatabricks } from "@/config/workspace";
import { ExternalLink, RefreshCw, Calendar, Repeat } from "lucide-react";

export const Route = createFileRoute("/_sidebar/smart-retry")({
  component: () => <SmartRetry />,
});

const SCENARIOS = [
  {
    id: "recurrence",
    title: "Payment Recurrence",
    desc: "Scheduled or subscription-based payments (e.g. monthly charges).",
    icon: Calendar,
  },
  {
    id: "retry",
    title: "Payment Retry (Reattempts)",
    desc: "Cardholder has a transaction declined and performs a new attempt under the same conditions — same card, amount, and merchant.",
    icon: RefreshCw,
  },
] as const;

function SmartRetry() {
  const q = useGetRetryPerformance({ params: { limit: 50 } });
  const rows = q.data?.data ?? [];

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div>
        <h1 className="text-2xl font-bold font-heading tracking-tight text-foreground">
          Smart Retry
        </h1>
        <p className="mt-1 text-sm font-medium text-muted-foreground">
          Recurrence & reattempts · Brazil · Recover more approvals
        </p>
        <div className="mt-4 rounded-lg border border-border/80 bg-muted/30 px-4 py-2 text-sm">
          <span className="text-muted-foreground">Volume: </span>
          <span className="font-semibold text-foreground">1M+ transactions/month</span>
          <span className="text-muted-foreground"> in Brazil (recurrence or retry scenarios)</span>
        </div>
      </div>

      {/* Two scenarios */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Two scenarios in scope</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Smart Retry addresses both recurring payments and one-off retries after a decline.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          {SCENARIOS.map((s) => {
            const Icon = s.icon;
            return (
              <Card key={s.id} className="border-border/80">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Icon className="h-4 w-4 text-primary" />
                    {s.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{s.desc}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Top retry cohorts */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Top retry cohorts</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Performance by scenario, decline reason, and attempt number. Success rate, incremental lift vs baseline, and recovered value.
        </p>
        <Card className="border-border/80">
          <CardContent className="pt-6">
            {q.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : q.isError ? (
              <p className="text-sm text-destructive">Failed to load retry performance.</p>
            ) : rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data yet. Run the simulator and ETL to populate views.</p>
            ) : (
              <ul className="space-y-4">
                {rows.map((r) => (
                  <li
                    key={`${r.retry_scenario}-${r.decline_reason_standard}-${r.retry_count}`}
                    className="rounded-lg border border-border/60 p-3 space-y-2"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">
                        <Repeat className="h-3 w-3 mr-1" />
                        {r.retry_scenario}
                      </Badge>
                      <span className="font-mono text-sm">{r.decline_reason_standard}</span>
                      <Badge variant="outline">Attempt {r.retry_count}</Badge>
                      <Badge>{r.success_rate_pct}% success</Badge>
                      {r.incremental_lift_pct != null && (
                        <Badge variant={r.incremental_lift_pct > 0 ? "default" : "destructive"}>
                          {r.incremental_lift_pct > 0 ? "+" : ""}{r.incremental_lift_pct}% vs baseline
                        </Badge>
                      )}
                      <Badge variant="outline">{r.effectiveness}</Badge>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      <span>Recovered ${r.recovered_value.toFixed(2)}</span>
                      <span>Avg fraud score {r.avg_fraud_score.toFixed(3)}</span>
                      {r.avg_time_since_last_attempt_s != null && (
                        <span>Avg wait {Math.round(r.avg_time_since_last_attempt_s)}s</span>
                      )}
                      {r.avg_prior_approvals != null && (
                        <span>Prior approvals {r.avg_prior_approvals.toFixed(1)}</span>
                      )}
                    </div>
                    <div className="flex justify-end">
                      <Badge variant="secondary">{r.retry_attempts} retries</Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Button variant="outline" size="sm" className="mt-3 gap-2" onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))}>
          Open routing dashboard <ExternalLink className="h-3.5 w-3.5" />
        </Button>
      </section>
    </div>
  );
}
