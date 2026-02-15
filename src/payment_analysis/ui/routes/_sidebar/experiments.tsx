import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { ErrorBoundary } from "react-error-boundary";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  createExperiment,
  listExperimentsKey,
  useListExperiments,
  startExperiment,
  stopExperiment,
  type Experiment,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ExternalLink, Code2, FlaskConical } from "lucide-react";
import { getMLflowUrl, openInDatabricks } from "@/config/workspace";
import { openNotebookInDatabricks } from "@/lib/notebooks";

function ExperimentsErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
  return (
    <div className="p-6">
      <Card className="glass-card border border-border/80 border-l-4 border-l-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Something went wrong</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : String(error)}</p>
          <Button variant="outline" size="sm" onClick={resetErrorBoundary}>Try again</Button>
        </CardContent>
      </Card>
    </div>
  );
}

export const Route = createFileRoute("/_sidebar/experiments")({
  component: () => (
    <ErrorBoundary FallbackComponent={ExperimentsErrorFallback}>
      <Experiments />
    </ErrorBoundary>
  ),
});

function Experiments() {
  const qc = useQueryClient();
  const [name, setName] = useState("Routing bandit v0");

  const q = useListExperiments({ query: { refetchInterval: 30_000 } });

  const create = useMutation({
    mutationFn: () => createExperiment({ name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: listExperimentsKey() }),
  });
  const start = useMutation({
    mutationFn: (experiment_id: string) => startExperiment({ experiment_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: listExperimentsKey() }),
  });
  const stop = useMutation({
    mutationFn: (experiment_id: string) => stopExperiment({ experiment_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: listExperimentsKey() }),
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
              onClick={() => openNotebookInDatabricks("train_models")}
            >
              <FlaskConical className="w-4 h-4 mr-2" />
              ML Training
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebookInDatabricks("agent_framework")}
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

      <Card className="glass-card border border-border/80">
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
        {q.isLoading ? (
          <>
            {[1, 2, 3].map((i) => (
              <Card key={i} className="glass-card border border-border/80">
                <CardHeader className="py-4 space-y-2">
                  <Skeleton className="h-5 w-48" />
                  <Skeleton className="h-3 w-32" />
                </CardHeader>
                <CardContent className="flex gap-2">
                  <Skeleton className="h-9 w-16" />
                  <Skeleton className="h-9 w-16" />
                </CardContent>
              </Card>
            ))}
          </>
        ) : items.length === 0 ? (
          <Card className="glass-card border border-border/80">
            <CardContent className="py-8 text-center">
              <FlaskConical className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">No experiments yet. Create one above.</p>
            </CardContent>
          </Card>
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
  const openInWorkspace = () => openInDatabricks(getMLflowUrl());
  return (
    <Card
      className="glass-card border border-border/80 cursor-pointer hover:shadow-md transition-shadow"
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

