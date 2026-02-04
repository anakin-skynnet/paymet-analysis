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

export const Route = createFileRoute("/_sidebar/experiments")({
  component: () => <Experiments />,
});

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
      <h1 className="text-2xl font-semibold">Experiments</h1>

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
  return (
    <Card>
      <CardHeader className="py-4">
        <CardTitle className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate">{exp.name}</div>
            <div className="text-xs text-muted-foreground font-mono truncate">
              {id || "(no id)"}
            </div>
          </div>
          <Badge variant={exp.status === "running" ? "default" : "secondary"}>
            {exp.status}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex gap-2">
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

