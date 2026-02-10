import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  ExternalLink,
  Database,
  GitBranch,
  LayoutDashboard,
  Brain,
  Bot,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Settings2,
  RefreshCw,
  Play,
} from "lucide-react";
import { ensureAbsoluteWorkspaceUrl, getWorkspaceUrl } from "@/config/workspace";
import { DataSourceBadge } from "@/components/apx/data-source-badge";
import {
  runSetupJob,
  runSetupPipeline,
  useGetCountries,
  useGetOnlineFeatures,
  type RunJobOut,
  type RunPipelineOut,
} from "@/lib/api";

export const Route = createFileRoute("/_sidebar/setup")({
  component: () => <SetupRun />,
});

const API_BASE = "/api/setup";

type SetupSettings = { settings: Record<string, string> };

async function fetchSettings(): Promise<SetupSettings> {
  const res = await fetch(`${API_BASE}/settings`, { credentials: "include" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

type SetupDefaults = {
  warehouse_id: string;
  catalog: string;
  schema: string;
  jobs: Record<string, string>;
  pipelines: Record<string, string>;
  workspace_host: string;
  workspace_id?: string;
  token_received?: boolean;
  workspace_url_derived?: boolean;
  lakebase_autoscaling?: boolean;
  lakebase_connection_mode?: string;
};

async function fetchDefaults(): Promise<SetupDefaults> {
  const res = await fetch(`${API_BASE}/defaults`, { credentials: "include" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

type SetupConfigResult = { catalog: string; schema: string };

async function updateConfig(body: { catalog: string; schema: string }): Promise<SetupConfigResult> {
  const res = await fetch(`${API_BASE}/config`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function SetupRun() {
  const qc = useQueryClient();
  const { data: defaults, isLoading: loadingDefaults, refetch: refetchDefaults, isRefetching: refetchingDefaults } = useQuery({
    queryKey: ["setup", "defaults"],
    queryFn: fetchDefaults,
    staleTime: 15_000,
    refetchOnWindowFocus: true,
  });

  const { data: settingsData } = useQuery({
    queryKey: ["setup", "settings"],
    queryFn: fetchSettings,
    staleTime: 30_000,
  });
  const { data: countriesData } = useGetCountries({ params: {} });
  const { data: onlineFeaturesData } = useGetOnlineFeatures({ params: { limit: 100 } });

  const [warehouseId, setWarehouseId] = useState("");
  const [catalog, setCatalog] = useState("");
  const [schema, setSchema] = useState("");
  const [lastResult, setLastResult] = useState<{
    type: "config";
    message: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** Key of the step currently running (job key or pipeline key) so we show loading on the right button */
  const [runningStepKey, setRunningStepKey] = useState<string | null>(null);

  useEffect(() => {
    if (defaults) {
      setWarehouseId(defaults.warehouse_id);
      setCatalog(defaults.catalog);
      setSchema(defaults.schema);
    }
  }, [defaults]);

  const updateConfigMutation = useMutation({
    mutationFn: updateConfig,
    onSuccess: () => {
      setLastResult({
        type: "config",
        message: "Catalog and schema saved. They will be used for all Lakehouse operations.",
      });
      setError(null);
      qc.invalidateQueries({ queryKey: ["setup", "defaults"] });
    },
    onError: (e: Error) => {
      setError(e.message);
      setLastResult(null);
    },
  });

  const runJobMutation = useMutation({
    mutationFn: async (payload: { job_id: string; catalog?: string; schema?: string; warehouse_id?: string }) => {
      const { data } = await runSetupJob({
        job_id: payload.job_id,
        catalog: payload.catalog ?? undefined,
        schema: payload.schema ?? undefined,
        warehouse_id: payload.warehouse_id ?? undefined,
      });
      return data;
    },
    onSuccess: (data: RunJobOut) => {
      setError(null);
      if (data.run_page_url) {
        window.open(data.run_page_url, "_blank", "noopener,noreferrer");
      }
      setRunningStepKey(null);
    },
    onError: (e: Error) => {
      setError(e.message);
      setLastResult(null);
      setRunningStepKey(null);
    },
  });

  const runPipelineMutation = useMutation({
    mutationFn: async (payload: { pipeline_id: string }) => {
      const { data } = await runSetupPipeline(payload);
      return data;
    },
    onSuccess: (data: RunPipelineOut) => {
      setError(null);
      if (data.pipeline_page_url) {
        window.open(data.pipeline_page_url, "_blank", "noopener,noreferrer");
      }
      setRunningStepKey(null);
    },
    onError: (e: Error) => {
      setError(e.message);
      setLastResult(null);
      setRunningStepKey(null);
    },
  });

  const isJobConfigured = (jobKey: string) => {
    const id = defaults?.jobs?.[jobKey];
    return !!id && id !== "0";
  };

  const saveConfig = () => {
    updateConfigMutation.mutate({ catalog, schema });
  };

  // Always use absolute workspace URL so Execute opens the workspace, never the app URL (databricksapps.com).
  const rawHost = defaults?.workspace_host || getWorkspaceUrl();
  const host = rawHost && !rawHost.includes("databricksapps")
    ? ensureAbsoluteWorkspaceUrl(rawHost)
    : "";
  const workspaceId = (defaults?.workspace_id || "").trim();
  /** Run job via API and open the job run view with the new run_id. */
  const handleRunJob = (jobKey: string) => {
    const id = defaults?.jobs?.[jobKey];
    if (!host || !id || id === "0") return;
    setRunningStepKey(jobKey);
    setError(null);
    runJobMutation.mutate({
      job_id: id,
      catalog: catalog || defaults?.catalog,
      schema: schema || defaults?.schema,
      warehouse_id: warehouseId || defaults?.warehouse_id,
    });
  };

  /** Open Databricks workspace: job page (runs list) when ID is resolved, otherwise jobs list. */
  const openJobPage = (jobKey: string) => {
    if (!host) return;
    const id = defaults?.jobs?.[jobKey];
    if (id && id !== "0") {
      const runPath = workspaceId ? `/jobs/${id}?o=${workspaceId}` : `/#job/${id}`;
      window.open(`${host}${runPath}`, "_blank", "noopener,noreferrer");
    } else {
      window.open(workspaceId ? `${host}/jobs?o=${workspaceId}` : `${host}/jobs`, "_blank", "noopener,noreferrer");
    }
  };
  /** Run pipeline via API and open the pipeline page (shows the update). */
  const handleRunPipeline = (pipelineKey: string) => {
    const id = defaults?.pipelines?.[pipelineKey];
    if (!host || !id || id === "0") return;
    setRunningStepKey(pipelineKey);
    setError(null);
    runPipelineMutation.mutate({ pipeline_id: id });
  };

  /** Open Databricks workspace: pipeline page when ID is resolved, otherwise pipelines list. */
  const openPipelinePage = (pipelineKey: string) => {
    if (!host) return;
    const id = defaults?.pipelines?.[pipelineKey];
    const q = workspaceId ? `?o=${workspaceId}` : "";
    if (id && id !== "0") {
      window.open(`${host}/pipelines/${id}${q}`, "_blank", "noopener,noreferrer");
    } else {
      window.open(`${host}/pipelines${q}`, "_blank", "noopener,noreferrer");
    }
  };
  /** Open Databricks workspace: SQL warehouse (specific resource). */
  const openWarehouse = () => {
    const wid = warehouseId || defaults?.warehouse_id;
    if (!host || !wid) return;
    const q = workspaceId ? `?o=${workspaceId}` : "";
    window.open(`${host}/sql/warehouses/${wid}${q}`, "_blank", "noopener,noreferrer");
  };
  /** Open Databricks workspace: data explorer for catalog.schema (specific resource). */
  const openExploreSchema = () => {
    const c = catalog || defaults?.catalog;
    const s = schema || defaults?.schema;
    if (!host || !c || !s) return;
    const q = workspaceId ? `?o=${workspaceId}` : "";
    window.open(`${host}/explore/data/${c}/${s}${q}`, "_blank", "noopener,noreferrer");
  };
  /** Open Databricks workspace: Genie (specific resource). */
  const openGenie = () => {
    if (!host) return;
    const q = workspaceId ? `?o=${workspaceId}` : "";
    window.open(`${host}/genie${q}`, "_blank", "noopener,noreferrer");
  };
  /** Open Databricks workspace Jobs list (specific resource: /jobs). Use o= when available. */
  const openJobsList = () => {
    if (!host) return;
    const q = workspaceId ? `?o=${workspaceId}` : "";
    window.open(`${host}/jobs${q}`, "_blank", "noopener,noreferrer");
  };
  /** Open Databricks workspace Pipelines list (specific resource: /pipelines). Use o= when available. */
  const openPipelinesList = () => {
    if (!host) return;
    const q = workspaceId ? `?o=${workspaceId}` : "";
    window.open(`${host}/pipelines${q}`, "_blank", "noopener,noreferrer");
  };

  if (loadingDefaults && !defaults) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="page-section-title text-2xl font-semibold">Setup &amp; Run</h1>
          <DataSourceBadge label="Jobs &amp; pipelines from workspace" />
        </div>
        <p className="page-section-description">
          Get the platform ready so your team can see approval rates and act on recommendations. Follow the steps in order; click <strong>Run</strong> to start a job or pipeline, or <strong>Open</strong> to view it in the workspace.
        </p>
      </div>

      {/* Connection status: why Run may be disabled (token, host, job IDs) */}
      {defaults && (
        <Card className={host && defaults.token_received && Object.values(defaults.jobs || {}).some((id) => id && id !== "0") ? "border-green-500/30 bg-green-500/5" : "border-amber-500/30 bg-amber-500/5"}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Connection status
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Run buttons are enabled when token is received, workspace URL is set, and job IDs are resolved from your workspace.
            </p>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <ul className="space-y-1">
              <li className="flex items-center gap-2">
                {defaults.token_received ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
                )}
                <span>
                  <strong>Token:</strong> {defaults.token_received ? "Received (X-Forwarded-Access-Token or DATABRICKS_TOKEN)" : "Not received — enable user authorization below"}
                </span>
              </li>
              <li className="flex items-center gap-2">
                {host ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
                )}
                <span>
                  <strong>Workspace URL:</strong> {host ? (defaults.workspace_url_derived ? "Derived from request" : "Set (DATABRICKS_HOST)") : "Missing — set DATABRICKS_HOST or open from Compute → Apps"}
                </span>
              </li>
              <li className="flex items-center gap-2">
                {Object.values(defaults.jobs || {}).some((id) => id && id !== "0") ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
                )}
                <span>
                  <strong>Job IDs resolved:</strong>{" "}
                  {Object.values(defaults.jobs || {}).filter((id) => id && id !== "0").length} of {Object.keys(defaults.jobs || {}).length} (requires token + workspace URL)
                </span>
              </li>
            </ul>
            {(!defaults.token_received || !host) && (
              <p className="text-amber-700 dark:text-amber-400 pt-1">
                To fix: Open this app from <strong>Compute → Apps → payment-analysis</strong> (Workspace → Apps → web). Then in <strong>Compute → Apps → payment-analysis → Edit → Configure → Authorization</strong>, enable <strong>User authorization (on-behalf-of-user)</strong> and add API scopes (e.g. <code className="rounded bg-muted px-1">all:clusters</code>, <code className="rounded bg-muted px-1">jobs</code>, <code className="rounded bg-muted px-1">sql</code>). Save, reopen the app, then click <strong>Refresh job IDs</strong> in the steps section.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Connect to Databricks — token (OAuth or PAT) required to run jobs from UI */}
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            Connect to Databricks
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            To open jobs and pipelines in the Databricks workspace, use one of:
          </p>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <p>
            <strong>1. Your credentials (recommended):</strong> Open this app from <strong>Compute → Apps → payment-analysis</strong> (or <strong>Workspace → Apps → web</strong>) so Databricks forwards your token via <code className="rounded bg-muted px-1">X-Forwarded-Access-Token</code>. Enable <strong>User authorization</strong> in the app Configure → Authorization and add scopes so the token is sent.
          </p>
          <p>
            <strong>2. Personal Access Token (PAT):</strong> In the workspace go to <strong>Settings → Developer → Access tokens</strong>, create a token, then set <code className="rounded bg-muted px-1">DATABRICKS_TOKEN</code> in <strong>Compute → Apps → payment-analysis → Edit → Environment</strong>. Also set <code className="rounded bg-muted px-1">DATABRICKS_HOST</code> and <code className="rounded bg-muted px-1">DATABRICKS_WAREHOUSE_ID</code>.
          </p>
          <p className="text-muted-foreground">
            If you open the app from Compute → Apps (option 1), do <strong>not</strong> set <code className="rounded bg-muted px-1">DATABRICKS_CLIENT_ID</code> or <code className="rounded bg-muted px-1">DATABRICKS_CLIENT_SECRET</code> in the app environment.
          </p>
          {host && (
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => window.open(workspaceId ? `${host}/?o=${workspaceId}#setting/account` : `${host}/#setting/account`, "_blank", "noopener,noreferrer")}
            >
              Open workspace Settings <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Databricks resources overview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Databricks resources & approval-rate impact</CardTitle>
          <p className="text-sm text-muted-foreground">
            Resources used in this solution, why they are added, and how they help accelerate approval rates.
          </p>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 pr-4 font-medium">Resource</th>
                <th className="text-left py-2 pr-4 font-medium">Purpose</th>
                <th className="text-left py-2 font-medium">How it accelerates approval rates</th>
              </tr>
            </thead>
            <tbody className="[&_tr]:border-b [&_tr]:border-border">
              <tr>
                <td className="py-2 pr-4 align-top">Transaction Stream Simulator</td>
                <td className="py-2 pr-4 align-top">Generate synthetic payment events at scale.</td>
                <td className="py-2 align-top">Stress-tests pipelines and decisioning; feeds analytics and ML training data.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">Lakeflow ETL pipeline</td>
                <td className="py-2 pr-4 align-top">Bronze → Silver → Gold data processing.</td>
                <td className="py-2 align-top">Clean, enriched data for KPIs, dashboards, and model training.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">Gold views (SQL)</td>
                <td className="py-2 pr-4 align-top">Analytical views for dashboards and Genie.</td>
                <td className="py-2 align-top">Visibility into approval rates, declines, and recovery opportunities.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">Lakehouse tables (approval_rules, recommendations, online_features)</td>
                <td className="py-2 pr-4 align-top">Store rules and ML/agent outputs in Unity Catalog.</td>
                <td className="py-2 align-top">Rules and similar-case recommendations feed real-time decisioning.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">ML models (approval propensity, risk, routing, retry)</td>
                <td className="py-2 pr-4 align-top">Train and register models in Unity Catalog.</td>
                <td className="py-2 align-top">Real-time scoring and routing to maximize approvals and reduce fraud.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">Model Serving</td>
                <td className="py-2 pr-4 align-top">Serve ML models with low-latency inference.</td>
                <td className="py-2 align-top">Sub-50ms approval/risk/routing predictions for live transactions.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">AI agents (Orchestrator, Smart Routing, Retry, Decline Analyst, etc.)</td>
                <td className="py-2 pr-4 align-top">Automate recommendations using ML and rules.</td>
                <td className="py-2 align-top">Suggest retries, routing, and 3DS use to recover declines and optimize flow.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">Vector Search</td>
                <td className="py-2 pr-4 align-top">Similar-transaction search over payment data.</td>
                <td className="py-2 align-top">“Similar cases” recommendations for retry and routing in the Decisioning UI.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">Dashboards (11)</td>
                <td className="py-2 pr-4 align-top">Monitor KPIs, declines, fraud, and performance.</td>
                <td className="py-2 align-top">Identify underperforming segments and act on recovery opportunities.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 align-top">Unity Catalog</td>
                <td className="py-2 pr-4 align-top">Governance, lineage, and schema for tables and models.</td>
                <td className="py-2 align-top">Secure, auditable data and models for compliance and trust.</td>
              </tr>
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Parameters — catalog/schema are persisted in app_config; Save updates the table and app-wide config */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Parameters
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Catalog and schema are used for all Lakehouse operations (analytics, rules, ML). Save to persist them in the Lakehouse config table.
          </p>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <label htmlFor="warehouse_id" className="text-sm font-medium leading-none">
              SQL Warehouse ID
            </label>
            <Input
              id="warehouse_id"
              value={warehouseId}
              onChange={(e) => setWarehouseId(e.target.value)}
              placeholder="e.g. 148ccb90800933a1"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="catalog" className="text-sm font-medium leading-none">
              Catalog
            </label>
            <Input
              id="catalog"
              value={catalog}
              onChange={(e) => setCatalog(e.target.value)}
              placeholder="ahs_demos_catalog"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="schema" className="text-sm font-medium leading-none">
              Schema
            </label>
            <Input
              id="schema"
              value={schema}
              onChange={(e) => setSchema(e.target.value)}
              placeholder="payment_analysis"
            />
          </div>
          <div className="sm:col-span-3 flex justify-end">
            <Button
              onClick={saveConfig}
              disabled={updateConfigMutation.isPending}
            >
              {updateConfigMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Save catalog & schema
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {lastResult && (
        <div className="flex items-center gap-2 rounded-lg border border-green-500/50 bg-green-500/10 px-4 py-3 text-sm text-green-700 dark:text-green-400">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{lastResult.message}</span>
        </div>
      )}

      {/* Data & config — Lakebase/Lakehouse data fetched from backend for control panel UX */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Data & config
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            App settings (Lakebase), countries, and online features from the Databricks backend. Refreshed when you load or refocus this page.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* App config (current catalog/schema) and App settings (key-value) */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium">App config & settings (Lakebase)</h3>
            <p className="text-xs text-muted-foreground">
              Effective catalog and schema above are persisted in app_config. Key-value settings below are from app_settings (job defaults, warehouse_id).
            </p>
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/50">
                    <th className="text-left py-2 px-3 font-medium">Key</th>
                    <th className="text-left py-2 px-3 font-medium">Value</th>
                  </tr>
                </thead>
                <tbody className="[&_tr]:border-b [&_tr]:border-border">
                  {defaults && (
                    <>
                      <tr>
                        <td className="py-2 px-3 font-medium text-muted-foreground">Database connection</td>
                        <td className="py-2 px-3">
                          {defaults.lakebase_connection_mode === "autoscaling" ? (
                            <Badge variant="default" className="font-normal">Lakebase Autoscaling</Badge>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium text-muted-foreground">catalog (effective)</td>
                        <td className="py-2 px-3">{defaults.catalog || "—"}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium text-muted-foreground">schema (effective)</td>
                        <td className="py-2 px-3">{defaults.schema || "—"}</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-3 font-medium text-muted-foreground">warehouse_id</td>
                        <td className="py-2 px-3">{defaults.warehouse_id || "—"}</td>
                      </tr>
                    </>
                  )}
                  {settingsData?.settings &&
                    Object.entries(settingsData.settings)
                      .filter(([k]) => !["catalog", "schema"].includes(k) || !defaults)
                      .map(([key, value]) => (
                        <tr key={key}>
                          <td className="py-2 px-3 font-medium text-muted-foreground">{key}</td>
                          <td className="py-2 px-3 break-all">{value || "—"}</td>
                        </tr>
                      ))}
                  {(!settingsData?.settings || Object.keys(settingsData.settings).length === 0) &&
                    (!defaults?.catalog && !defaults?.schema && !defaults?.warehouse_id) && (
                    <tr>
                      <td colSpan={2} className="py-4 px-3 text-center text-muted-foreground text-sm">
                        No app settings loaded. Run Job 1 (Create Data Repositories) to create Lakebase Autoscaling and seed Lakebase (app_config, approval_rules, online_features, app_settings).
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Countries (Lakehouse / Lakebase) */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Countries / entities</h3>
            <p className="text-xs text-muted-foreground">
              From Lakehouse countries table (filter dropdown). Fetched from backend.
            </p>
            <div className="overflow-x-auto rounded-md border border-border max-h-48 overflow-y-auto">
              <table className="w-full text-sm border-collapse">
                <thead className="sticky top-0 bg-muted/50">
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-3 font-medium">Code</th>
                    <th className="text-left py-2 px-3 font-medium">Name</th>
                  </tr>
                </thead>
                <tbody className="[&_tr]:border-b [&_tr]:border-border">
                  {(countriesData?.data ?? []).map((c) => (
                    <tr key={c.code}>
                      <td className="py-2 px-3">{c.code}</td>
                      <td className="py-2 px-3">{c.name}</td>
                    </tr>
                  ))}
                  {(!countriesData?.data || countriesData.data.length === 0) && (
                    <tr>
                      <td colSpan={2} className="py-4 px-3 text-center text-muted-foreground text-sm">
                        No countries. Run Job 1 to seed the Lakehouse.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Online features (ML / agent output) */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Online features (last 100)</h3>
            <p className="text-xs text-muted-foreground">
              From Lakebase or Lakehouse. ML and AI agent outputs for the app.
            </p>
            <div className="overflow-x-auto rounded-md border border-border max-h-64 overflow-y-auto">
              <table className="w-full text-sm border-collapse">
                <thead className="sticky top-0 bg-muted/50">
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-3 font-medium">Source</th>
                    <th className="text-left py-2 px-3 font-medium">Feature</th>
                    <th className="text-left py-2 px-3 font-medium">Value</th>
                    <th className="text-left py-2 px-3 font-medium">Entity</th>
                  </tr>
                </thead>
                <tbody className="[&_tr]:border-b [&_tr]:border-border">
                  {(onlineFeaturesData?.data ?? []).map((f, i) => (
                    <tr key={f.id + String(i)}>
                      <td className="py-2 px-3">{f.source}</td>
                      <td className="py-2 px-3">{f.feature_name}</td>
                      <td className="py-2 px-3">{f.feature_value != null ? String(f.feature_value) : f.feature_value_str ?? "—"}</td>
                      <td className="py-2 px-3">{f.entity_id ?? "—"}</td>
                    </tr>
                  ))}
                  {(!onlineFeaturesData?.data || onlineFeaturesData.data.length === 0) && (
                    <tr>
                      <td colSpan={4} className="py-4 px-3 text-center text-muted-foreground text-sm">
                        No online features yet. ML and agents populate this after runs.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Unified execution steps: Jobs 1–7 (one card per bundle job) + Pipelines */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium">Execution steps (Jobs 1–7 + Pipelines)</h2>
        <p className="text-sm text-muted-foreground">
          Run in order. Each card runs one Databricks job or pipeline. Job IDs are resolved from your workspace when you are signed in (open from Compute → Apps or set DATABRICKS_TOKEN).
        </p>
        {defaults && !host && (
          <p className="text-sm text-amber-600 dark:text-amber-500">
            Connect to Databricks: open this app from <strong>Workspace → Compute → Apps → payment-analysis</strong> so your token is forwarded (no env vars needed), or set <code className="rounded bg-muted px-1">DATABRICKS_HOST</code> and <code className="rounded bg-muted px-1">DATABRICKS_TOKEN</code> in the app environment.
          </p>
        )}
        {defaults && defaults.token_received === false && (
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm text-amber-600 dark:text-amber-500 flex-1 min-w-0">
              Token not received: enable <strong>user authorization (on-behalf-of-user)</strong> in <strong>Compute → Apps → payment-analysis → Edit → Configure → Authorization</strong>, add scopes (e.g. <code className="rounded bg-muted px-1">sql</code>, <code className="rounded bg-muted px-1">Jobs</code>, <code className="rounded bg-muted px-1">Pipelines</code>), then open this app again from <strong>Compute → Apps</strong>. Click <strong>Refresh job IDs</strong> after enabling.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchDefaults()}
              disabled={refetchingDefaults}
            >
              {refetchingDefaults ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              Refresh job IDs
            </Button>
          </div>
        )}
        {defaults && defaults.token_received === true && defaults.workspace_url_derived === false && (
          <p className="text-sm text-amber-600 dark:text-amber-500">
            Token received but workspace URL could not be derived. Set <code className="rounded bg-muted px-1">DATABRICKS_HOST</code> in the app environment (Compute → Apps → Edit → Environment), or ensure you opened the app from the Apps URL (e.g. <code className="rounded bg-muted px-1">payment-analysis-*.databricksapps.com</code>).
          </p>
        )}
        {defaults && host && (defaults.jobs?.lakehouse_bootstrap === "0" || !defaults.jobs?.lakehouse_bootstrap) && (
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm text-muted-foreground flex-1 min-w-0">
              <strong>Run</strong> starts the job or pipeline and opens the run view in Databricks. It is enabled when the job or pipeline exists in your workspace (IDs are resolved when you are signed in). If Run is disabled, open this app from <strong>Compute → Apps → payment-analysis</strong> so Databricks forwards your token, then click <strong>Refresh job IDs</strong> below.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchDefaults()}
              disabled={refetchingDefaults}
            >
              {refetchingDefaults ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              Refresh job IDs
            </Button>
          </div>
        )}

        {/* Job steps 1–7: one card per bundle job (backend resolves same job_id for all keys in a step) */}
        {[
          { step: 1, title: "Create Data Repositories", desc: "Create catalog/schema, create Lakebase Autoscaling (project/branch/endpoint), seed Lakebase (app_config, approval_rules, online_features, app_settings), Lakehouse tables, Vector Search. Run once to enable Rules, Decisioning, and Dashboard.", jobKey: "lakehouse_bootstrap", icon: Database },
          { step: 2, title: "Simulate Transaction Events", desc: "Generate test payment events (e.g. 1000/sec). Uses catalog and schema above.", jobKey: "transaction_stream_simulator", icon: Database },
          { step: 3, title: "Initialize Ingestion", desc: "Gold views and sync for dashboards and Vector Search. Uses warehouse and schema.", jobKey: "create_gold_views", icon: LayoutDashboard },
          { step: 4, title: "Deploy Dashboards", desc: "Publish dashboards with embed credentials so the app can embed AI/BI dashboards.", jobKey: "publish_dashboards", icon: LayoutDashboard },
          { step: 5, title: "Train Models & Serving", desc: "Train approval propensity, risk scoring, routing, and retry models. Uses catalog and schema.", jobKey: "train_ml_models", icon: Brain },
          { step: 6, title: "Deploy AgentBricks Agents", desc: "Run agent framework (orchestrator + Smart Routing, Retry, Decline Analyst, Risk, Performance). One task runs full analysis.", jobKey: "orchestrator_agent", icon: Bot },
          { step: 7, title: "Genie Space Sync", desc: "Sync Genie space and sample questions for natural language analytics over payment data.", jobKey: "genie_sync", icon: LayoutDashboard },
        ].map(({ step, title, desc, jobKey, icon: Icon }) => (
          <Card
            key={step}
            className="card-interactive cursor-pointer"
            onClick={() => openJobPage(jobKey)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && openJobPage(jobKey)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  {step}. {title}
                </CardTitle>
                <Badge variant="secondary">Job</Badge>
              </div>
              <p className="text-sm text-muted-foreground">{desc}</p>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <Button
                onClick={() => handleRunJob(jobKey)}
                disabled={!host || !isJobConfigured(jobKey)}
              >
                {runningStepKey === jobKey ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
                Run
              </Button>
              <Button variant="outline" size="sm" onClick={() => openJobPage(jobKey)} disabled={!host}>
                Open <ExternalLink className="ml-1 h-3 w-3" />
              </Button>
              {step === 1 && (
                <Button variant="outline" size="sm" onClick={openWarehouse} disabled={!host}>
                  SQL Warehouse <ExternalLink className="ml-1 h-3 w-3" />
                </Button>
              )}
            </CardContent>
          </Card>
        ))}

        {/* Pipelines */}
        <h3 className="text-base font-medium pt-2">Pipelines (Lakeflow)</h3>
        <p className="text-sm text-muted-foreground">
          Start pipeline updates when you need ETL or real-time streaming.
        </p>
        {[
          { title: "Payment Analysis ETL", desc: "Bronze → Silver → Gold; feed Vector Search and gold views.", pipelineKey: "payment_analysis_etl" as const, icon: GitBranch },
          { title: "Real-Time Stream", desc: "Live payment events pipeline. Run when you need real-time analytics.", pipelineKey: "payment_realtime_pipeline" as const, icon: GitBranch },
        ].map(({ title, desc, pipelineKey, icon: Icon }) => (
          <Card
            key={pipelineKey}
            className="card-interactive cursor-pointer"
            onClick={() => openPipelinePage(pipelineKey)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && openPipelinePage(pipelineKey)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  {title}
                </CardTitle>
                <Badge variant="outline">Pipeline</Badge>
              </div>
              <p className="text-sm text-muted-foreground">{desc}</p>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <Button
                onClick={() => handleRunPipeline(pipelineKey)}
                disabled={!host || !defaults?.pipelines?.[pipelineKey] || defaults.pipelines[pipelineKey] === "0"}
              >
                {runningStepKey === pipelineKey ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
                Run
              </Button>
              <Button variant="outline" size="sm" onClick={() => openPipelinePage(pipelineKey)} disabled={!host}>
                Open <ExternalLink className="ml-1 h-3 w-3" />
              </Button>
            </CardContent>
          </Card>
        ))}

        {/* Optional: stream processor job (same step 3 bundle; separate run if needed) */}
        {defaults && isJobConfigured("continuous_stream_processor") && (
          <Card
            className="card-interactive cursor-pointer"
            onClick={() => openJobPage("continuous_stream_processor")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && openJobPage("continuous_stream_processor")}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <GitBranch className="h-4 w-4" />
                  Stream processor (optional)
                </CardTitle>
                <Badge variant="outline">Job</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                Continuous stream processor for real-time payment events. Use with the Real-Time Stream pipeline when needed.
              </p>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <Button
                onClick={() => handleRunJob("continuous_stream_processor")}
                disabled={!host}
              >
                {runningStepKey === "continuous_stream_processor" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
                Run
              </Button>
              <Button variant="outline" size="sm" onClick={() => openJobPage("continuous_stream_processor")} disabled={!host}>
                Open <ExternalLink className="ml-1 h-3 w-3" />
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Quick links: Jobs, Pipelines, Warehouse, Genie, etc. */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick links — open in Databricks</CardTitle>
          <p className="text-sm text-muted-foreground">
            One-click to open jobs, pipelines, warehouse, Genie, and data explorer.
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={openJobsList}
            disabled={!host}
          >
            Jobs <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={openPipelinesList}
            disabled={!host}
          >
            Pipelines <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={openWarehouse}
            disabled={!host}
          >
            SQL Warehouse <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={openExploreSchema}
            disabled={!host}
          >
            Explore schema <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={openGenie}
            disabled={!host}
          >
            Genie (Ask Data) <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => openJobPage("continuous_stream_processor")}
            disabled={!host}
          >
            Stream processor job <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          {isJobConfigured("test_agent_framework") && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => openJobPage("test_agent_framework")}
              disabled={!host}
            >
              Test Agent Framework <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
