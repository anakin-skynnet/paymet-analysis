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
 * Lakeview dashboard IDs for the three unified dashboards.
 * Must match backend (DASHBOARD_ID_* env vars in dashboards.py).
 */
export const LAKEVIEW_DASHBOARD_IDS: Record<string, string> = {
  data_quality_unified: "01f109ebdeeb18e9baad9aeff86d6789",
  ml_optimization_unified: "01f109ebdee91971a4fc4e6955b7b571",
  executive_trends_unified: "01f109ebdedd1e188386fc897aed78a5",
};

/**
 * Map legacy individual dashboard names to their unified Lakeview dashboard.
 * After dashboard consolidation, all old individual dashboards are covered by
 * one of the three unified ones.
 */
const LEGACY_TO_UNIFIED: Record<string, string> = {
  // ML & Optimization — decline, fraud, routing, 3DS, financial impact
  decline_analysis: "ml_optimization_unified",
  financial_impact: "ml_optimization_unified",
  routing_optimization: "ml_optimization_unified",
  authentication_security: "ml_optimization_unified",
  fraud_risk_analysis: "ml_optimization_unified",
  merchant_performance: "ml_optimization_unified",
  // Data & Quality — streaming, monitoring, data quality
  realtime_monitoring: "data_quality_unified",
  streaming_data_quality: "data_quality_unified",
  daily_trends: "data_quality_unified",
  // Executive
  executive_overview: "executive_trends_unified",
};

/**
 * Build a Lakeview published dashboard URL for the workspace.
 * Accepts a unified dashboard ID (e.g. "ml_optimization_unified") or a legacy
 * dashboard name (e.g. "decline_analysis") and resolves to the correct
 * /dashboardsv3/<id>/published workspace path.
 */
export function getLakeviewDashboardUrl(dashboardName: string): string {
  const unifiedKey = LEGACY_TO_UNIFIED[dashboardName] ?? dashboardName;
  const lakeviewId = LAKEVIEW_DASHBOARD_IDS[unifiedKey] ?? dashboardName;
  return getWorkspacePath(`/dashboardsv3/${lakeviewId}/published`);
}

/**
 * Construct a dashboard URL.
 * @deprecated Use getLakeviewDashboardUrl() for Lakeview dashboard links.
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
