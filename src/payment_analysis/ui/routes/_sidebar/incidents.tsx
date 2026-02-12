import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createIncident,
  listIncidents,
  useGetLastHourPerformance,
  useGetStreamingTps,
  type Incident,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ExternalLink, Code2, AlertTriangle, Activity, HelpCircle } from "lucide-react";
import { getDashboardUrl, openInDatabricks } from "@/config/workspace";

const REFRESH_MS = 5000;

export const Route = createFileRoute("/_sidebar/incidents")({
  component: () => <Incidents />,
});

const openNotebook = async (notebookId: string) => {
  try {
    const response = await fetch(`/api/notebooks/notebooks/${notebookId}/url`);
    const data = await response.json();
    openInDatabricks(data?.url);
  } catch (error) {
    console.error("Failed to open notebook:", error);
  }
};

const openDashboard = () => {
  openInDatabricks(getDashboardUrl("/sql/dashboards/realtime_monitoring"));
};

function Incidents() {
  const qc = useQueryClient();
  const [category, setCategory] = useState("mid_failure");
  const [key, setKey] = useState("MID=demo");

  const q = useQuery({
    queryKey: ["incidents"],
    queryFn: () => listIncidents(),
  });
  const lastHourQ = useGetLastHourPerformance({ query: { refetchInterval: REFRESH_MS } });
  const tpsQ = useGetStreamingTps({ params: { limit_seconds: 120 }, query: { refetchInterval: REFRESH_MS } });

  const create = useMutation({
    mutationFn: () => createIncident({ category, key, severity: "medium", details: {} }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });

  const items = q.data?.data ?? [];
  const lastHour = lastHourQ.data?.data;
  const eventsPerSec = lastHour?.transactions_last_hour != null ? Math.round(lastHour.transactions_last_hour / 3600) : null;
  const tpsPoints = tpsQ.data?.data ?? [];
  const latestTps = tpsPoints.length > 0 ? tpsPoints[tpsPoints.length - 1]?.records_per_second : null;

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            Real-Time Monitor
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground" aria-label="What is Real-Time Monitor?">
                  <HelpCircle className="h-4 w-4" />
                </span>
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-xs">
                Live payment throughput, last-hour volume, and incident tracking. Use this page to monitor streaming TPS, create or view incidents (e.g. MID failures, processor issues), and open the Real-Time Monitoring dashboard or pipeline in Databricks.
              </TooltipContent>
            </Tooltip>
          </h1>
          <div className="flex gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="sm" onClick={openDashboard}>
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Monitoring Dashboard
                  <ExternalLink className="w-3 h-3 ml-2" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                Open the Real-Time Monitoring dashboard in Databricks (volume by second, latency, alerts, and data quality).
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="sm" onClick={() => openNotebook("realtime_pipeline")}>
                  <Code2 className="w-4 h-4 mr-2" />
                  Alert Pipeline
                  <ExternalLink className="w-3 h-3 ml-2" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                Open the real-time pipeline notebook in the workspace (streaming payment events and alert processing).
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          Live view: Simulate Transaction Events → Payment Analysis ETL &amp; Payment Real-Time Stream. Refresh every 5s.
        </p>
      </div>

      {/* Real-time stats strip */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Tooltip>
          <TooltipTrigger asChild>
            <Card className="border border-[var(--neon-cyan)]/20 bg-[var(--neon-cyan)]/5 cursor-help">
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Activity className="h-4 w-4 text-[var(--neon-cyan)]" />
                  TPS (live)
                </div>
                <p className="mt-1 text-2xl font-bold tabular-nums text-[var(--neon-cyan)]">
                  {tpsQ.isLoading ? "—" : (latestTps ?? eventsPerSec ?? "—")}
                </p>
                <p className="text-xs text-muted-foreground">transactions/sec</p>
              </CardContent>
            </Card>
          </TooltipTrigger>
          <TooltipContent>
            Live transactions per second from the streaming pipeline. Reflects current throughput (or last-hour average if live TPS is unavailable).
          </TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Card className="cursor-help">
              <CardContent className="pt-4">
                <div className="text-sm text-muted-foreground">Last hour volume</div>
                <p className="mt-1 text-2xl font-bold tabular-nums">
                  {lastHourQ.isLoading ? "—" : (lastHour?.transactions_last_hour?.toLocaleString() ?? "—")}
                </p>
                <p className="text-xs text-muted-foreground">approval {lastHour?.approval_rate_pct != null ? `${lastHour.approval_rate_pct.toFixed(1)}%` : "—"}</p>
              </CardContent>
            </Card>
          </TooltipTrigger>
          <TooltipContent>
            Total transactions and approval rate in the last hour. Helps you spot volume and approval trends at a glance.
          </TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Card className="cursor-help">
              <CardContent className="pt-4">
                <div className="text-sm text-muted-foreground">Incidents</div>
                <p className="mt-1 text-2xl font-bold tabular-nums">{items.length}</p>
                <p className="text-xs text-muted-foreground">open + resolved</p>
              </CardContent>
            </Card>
          </TooltipTrigger>
          <TooltipContent>
            Number of recorded incidents (open and resolved). Use &quot;Create incident&quot; below to add new ones for tracking and remediation.
          </TooltipContent>
        </Tooltip>
      </div>

      <Tooltip>
        <TooltipTrigger asChild>
          <Card className="cursor-help">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Create incident
                <HelpCircle className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden />
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2 md:grid-cols-3">
              <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Category (e.g. mid_failure)" />
              <Input value={key} onChange={(e) => setKey(e.target.value)} placeholder="Key (e.g. MID=demo)" />
              <Button onClick={() => create.mutate()} disabled={create.isPending}>
                Create
              </Button>
            </CardContent>
          </Card>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-sm">
          Record a payment or system incident (e.g. MID failure, processor outage) for tracking and remediation. Incidents appear in the list below and can be opened in the Real-Time Monitoring dashboard. Category and key identify the issue (e.g. <code className="rounded bg-muted px-1">mid_failure</code>, <code className="rounded bg-muted px-1">MID=demo</code>).
        </TooltipContent>
      </Tooltip>

      <div className="space-y-3">
        {items.length === 0 ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <p className="text-sm text-muted-foreground cursor-help inline-flex items-center gap-1.5">
                No incidents yet.
                <HelpCircle className="h-3.5 w-3.5" aria-hidden />
              </p>
            </TooltipTrigger>
            <TooltipContent>
              Recorded incidents appear here. Use &quot;Create incident&quot; above to add one; click a card to open the Real-Time Monitoring dashboard.
            </TooltipContent>
          </Tooltip>
        ) : (
          <>
            <Tooltip>
              <TooltipTrigger asChild>
                <p className="text-sm font-medium text-muted-foreground cursor-help inline-flex items-center gap-1.5 w-fit">
                  Incident list
                  <HelpCircle className="h-3.5 w-3.5" aria-hidden />
                </p>
              </TooltipTrigger>
              <TooltipContent>
                Recorded incidents. Click a card to open the Real-Time Monitoring dashboard in Databricks. Resolve via the API or your ops process.
              </TooltipContent>
            </Tooltip>
            {items.map((inc) => <IncidentRow key={inc.id} inc={inc} />)}
          </>
        )}
      </div>
    </div>
  );
}

const MONITORING_DASHBOARD_PATH = "/sql/dashboards/realtime_monitoring";

function IncidentRow({ inc }: { inc: Incident }) {
  const openInWorkspace = () => {
    const url = getDashboardUrl(MONITORING_DASHBOARD_PATH);
    openInDatabricks(url);
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

