/**
 * Workspace Configuration (Databricks App)
 *
 * Resolves the Databricks workspace base URL for all UI links (jobs, pipelines,
 * dashboards, Genie, MLflow). When the app is opened from Compute → Apps, the
 * backend returns the workspace URL (derived from request headers). Never use
 * the app origin (*.databricksapps.com) as workspace URL so links open in the workspace.
 */

/** Cache for workspace URL from GET /api/config/workspace (set at app load). */
let workspaceUrlFromApi: string | null = null;

/** Placeholder returned by backend when DATABRICKS_HOST is unset; do not cache so getWorkspaceUrl() can fall back to window.location.origin. */
const PLACEHOLDER_HOST = "example.databricks.com";

/**
 * If url has no scheme, prepend https:// so links open in the workspace, not relative to the app.
 * Exported so Setup and other pages can normalize workspace_host from the API before building Open links.
 */
export function ensureAbsoluteWorkspaceUrl(url: string): string {
  const u = (url || "").trim().replace(/\/+$/, "");
  if (!u) return u;
  if (u.startsWith("http://") || u.startsWith("https://")) return u;
  return `https://${u}`;
}

const toAbsoluteWorkspaceUrl = ensureAbsoluteWorkspaceUrl;

/**
 * Set workspace base URL from backend (e.g. after GET /api/config/workspace).
 * Call this once at app load so getWorkspaceUrl() returns the correct host.
 * Does not cache placeholder URLs. Cached value is normalized to an absolute URL.
 */
export function setWorkspaceUrlFromApi(url: string): void {
  const raw = (url || "").trim().replace(/\/+$/, "");
  if (!raw || raw.includes(PLACEHOLDER_HOST)) {
    workspaceUrlFromApi = null;
    return;
  }
  workspaceUrlFromApi = toAbsoluteWorkspaceUrl(raw);
}

/**
 * Get the Databricks workspace base URL (no trailing slash), always absolute.
 * Order: env → API cache → window.origin only when on workspace host (not Apps) → "".
 * Never use the app origin (*.databricksapps.com) as workspace URL so links open in the real workspace.
 */
export function getWorkspaceUrl(): string {
  const envUrl = import.meta.env.VITE_DATABRICKS_HOST;
  if (envUrl) return toAbsoluteWorkspaceUrl(envUrl as string);
  if (workspaceUrlFromApi) return workspaceUrlFromApi;
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    // Only use origin when we're on the workspace host (e.g. adb-*.azuredatabricks.net), not on the Apps host (*.databricksapps.com)
    if (hostname.includes("databricks") && !hostname.includes("databricksapps")) {
      return window.location.origin;
    }
  }
  return "";
}

/**
 * Construct a full Databricks workspace URL for a given path.
 */
export function getWorkspacePath(path: string): string {
  const baseUrl = getWorkspaceUrl();
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

/**
 * Construct a dashboard URL.
 */
export function getDashboardUrl(dashboardPath: string): string {
  return getWorkspacePath(dashboardPath);
}

/**
 * Construct an MLflow URL.
 */
export function getMLflowUrl(path: string = '/ml/experiments'): string {
  return getWorkspacePath(path);
}

/**
 * Construct a Genie URL.
 */
export function getGenieUrl(): string {
  return getWorkspacePath('/genie');
}

/**
 * Open a Databricks resource URL in a new tab only if it is an absolute URL.
 * Use for all notebook, folder, job, pipeline, and dashboard links so they open in the workspace.
 */
export function openWorkspaceUrl(url: string | null | undefined): void {
  if (url && (url.startsWith("http://") || url.startsWith("https://"))) {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

/**
 * Alias for openWorkspaceUrl for UI click handlers (open link in Databricks workspace).
 * Use with getDashboardUrl(), getGenieUrl(), getMLflowUrl(), or any workspace path.
 */
export const openInDatabricks = openWorkspaceUrl;
