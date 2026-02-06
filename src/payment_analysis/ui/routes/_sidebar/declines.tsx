import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { declineSummary } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExternalLink, Code2, TrendingUp } from "lucide-react";
import { getDashboardUrl } from "@/config/workspace";

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
  const q = useQuery({
    queryKey: ["declines", "summary"],
    queryFn: () => declineSummary(),
  });

  const buckets = q.data?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Header with Links */}
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Declines & remediation</h1>
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
        <p className="text-sm text-muted-foreground mt-2">
          Analyze decline patterns from Unity Catalog views
        </p>
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
    </div>
  );
}

