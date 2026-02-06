import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createExperiment,
  listExperiments,
  startExperiment,
  stopExperiment,
  type Experiment,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Code2, FlaskConical } from "lucide-react";
import { getMLflowUrl } from "@/config/workspace";

export const Route = createFileRoute("/_sidebar/experiments")({
  component: () => <Experiments />,
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

function Experiments() {
  const qc = useQueryClient();
  const [name, setName] = useState("Routing bandit v0");

  const q = useQuery({
    queryKey: ["experiments"],
    queryFn: () => listExperiments(),
  });

  const create = useMutation({
    mutationFn: () => createExperiment({ name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["experiments"] }),
  });
  const start = useMutation({
    mutationFn: (experiment_id: string) => startExperiment({ experiment_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["experiments"] }),
  });
  const stop = useMutation({
    mutationFn: (experiment_id: string) => stopExperiment({ experiment_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["experiments"] }),
  });

  const items = q.data?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Header with Links */}
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Experiments</h1>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebook("train_models")}
            >
              <FlaskConical className="w-4 h-4 mr-2" />
              ML Training
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebook("agent_framework")}
            >
              <Code2 className="w-4 h-4 mr-2" />
              Agent Tests
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          A/B testing and routing experiments with MLflow tracking
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Create experiment</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
          <Button onClick={() => create.mutate()} disabled={create.isPending}>
            Create
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No experiments yet. Create one above.
          </p>
        ) : (
          items.map((exp) => (
            <ExperimentRow
              key={exp.id ?? exp.name}
              exp={exp}
              onStart={() => exp.id && start.mutate(exp.id)}
              onStop={() => exp.id && stop.mutate(exp.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function ExperimentRow({
  exp,
  onStart,
  onStop,
}: {
  exp: Experiment;
  onStart: () => void;
  onStop: () => void;
}) {
  const id = exp.id ?? "";
  const openInWorkspace = () => {
    const url = getMLflowUrl();
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
            <div className="truncate">{exp.name}</div>
            <div className="text-xs text-muted-foreground font-mono truncate">
              {id || "(no id)"}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={exp.status === "running" ? "default" : "secondary"}>
              {exp.status}
            </Badge>
            <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden />
          </div>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">Click to open MLflow in Databricks</p>
      </CardHeader>
      <CardContent className="flex gap-2" onClick={(e) => e.stopPropagation()}>
        <Button
          variant="secondary"
          onClick={onStart}
          disabled={!id || exp.status === "running"}
        >
          Start
        </Button>
        <Button
          variant="secondary"
          onClick={onStop}
          disabled={!id || exp.status !== "running"}
        >
          Stop
        </Button>
      </CardContent>
    </Card>
  );
}

