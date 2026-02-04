import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { declineSummary } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/_sidebar/declines")({
  component: () => <Declines />,
});

function Declines() {
  const q = useQuery({
    queryKey: ["declines", "summary"],
    queryFn: () => declineSummary(),
  });

  const buckets = q.data?.data ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Declines & remediation</h1>

      <Card>
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
    </div>
  );
}

