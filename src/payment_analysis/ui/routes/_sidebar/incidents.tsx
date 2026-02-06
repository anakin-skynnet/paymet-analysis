import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createIncident,
  listIncidents,
  type Incident,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Code2, AlertTriangle } from "lucide-react";
import { getDashboardUrl } from "@/config/workspace";

export const Route = createFileRoute("/_sidebar/incidents")({
  component: () => <Incidents />,
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
  const dashboardUrl = getDashboardUrl("/sql/dashboards/realtime_monitoring");
  window.open(dashboardUrl, "_blank");
};

function Incidents() {
  const qc = useQueryClient();
  const [category, setCategory] = useState("mid_failure");
  const [key, setKey] = useState("MID=demo");

  const q = useQuery({
    queryKey: ["incidents"],
    queryFn: () => listIncidents(),
  });

  const create = useMutation({
    mutationFn: () => createIncident({ category, key, severity: "medium", details: {} }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });

  const items = q.data?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Header with Links */}
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Incidents</h1>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={openDashboard}
            >
              <AlertTriangle className="w-4 h-4 mr-2" />
              Monitoring Dashboard
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebook("realtime_pipeline")}
            >
              <Code2 className="w-4 h-4 mr-2" />
              Alert Pipeline
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          Track and manage payment processing incidents and alerts
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Create incident</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-3">
          <Input value={category} onChange={(e) => setCategory(e.target.value)} />
          <Input value={key} onChange={(e) => setKey(e.target.value)} />
          <Button onClick={() => create.mutate()} disabled={create.isPending}>
            Create
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No incidents yet.</p>
        ) : (
          items.map((inc) => <IncidentRow key={inc.id} inc={inc} />)
        )}
      </div>
    </div>
  );
}

const MONITORING_DASHBOARD_PATH = "/sql/dashboards/realtime_monitoring";

function IncidentRow({ inc }: { inc: Incident }) {
  const openInWorkspace = () => {
    const url = getDashboardUrl(MONITORING_DASHBOARD_PATH);
    if (url) window.open(url, "_blank");
  };
  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={openInWorkspace}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && openInWorkspace()}
    >
      <CardHeader className="py-4">
        <CardTitle className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate">
              {inc.category} — {inc.key}
            </div>
            <div className="text-xs text-muted-foreground font-mono truncate">
              {inc.id}
            </div>
          </div>
          <div className="flex gap-2 items-center">
            <Badge variant="secondary">{inc.severity}</Badge>
            <Badge variant={inc.status === "open" ? "default" : "secondary"}>
              {inc.status}
            </Badge>
            <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden />
          </div>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">Click to open Real-Time Monitoring in Databricks</p>
      </CardHeader>
    </Card>
  );
}

