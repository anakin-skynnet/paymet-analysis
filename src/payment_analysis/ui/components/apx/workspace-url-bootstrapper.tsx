import { useEffect } from "react";
import { setWorkspaceUrlFromApi, loadDashboardIds } from "@/config/workspace";
import { getWorkspaceConfig } from "@/lib/api";

/**
 * Fetches workspace URL from backend (GET /api/config/workspace) and caches it so getWorkspaceUrl()
 * and all UI links (jobs, pipelines, dashboards, Genie, MLflow) resolve correctly.
 * Also loads dashboard IDs from the backend for portable cross-workspace links.
 * Uses credentials: "include" so the request is sent with the same context as the Databricks App.
 * Renders nothing; run once at app root.
 */
export function WorkspaceUrlBootstrapper() {
  useEffect(() => {
    // Fetch workspace URL
    getWorkspaceConfig({ credentials: "include" })
      .then(({ data }) => {
        if (data?.workspace_url) {
          setWorkspaceUrlFromApi(data.workspace_url);
        }
      })
      .catch(() => {
        // Ignore: getWorkspaceUrl() will use env or window.location when on workspace host
      });

    // Fetch dashboard IDs from backend (auto-discovered or from env vars)
    loadDashboardIds().catch(() => {
      // Ignore: dashboard links will be empty until IDs are available
    });
  }, []);
  return null;
}
