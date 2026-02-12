import { createFileRoute, Navigate } from "@tanstack/react-router";

/** Executive overview merged into Overview (command-center). Redirect so bookmarks and links still work. */
export const Route = createFileRoute("/_sidebar/dashboard")({
  component: () => <Navigate to="/command-center" replace />,
});
