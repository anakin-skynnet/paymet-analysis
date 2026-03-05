import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_sidebar/dashboards")({
  validateSearch: (s: Record<string, unknown>): { embed?: string } => ({
    embed: typeof s.embed === "string" ? s.embed : undefined,
  }),
});
