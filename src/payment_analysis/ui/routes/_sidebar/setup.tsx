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
          <h1 className="page-section-title text-2xl font-semibold">Setup & Run</h1>
          <DataSourceBadge label="Jobs & pipelines from workspace" />
        </div>
        <p className="page-section-description">
          Follow the steps in order. Click <strong>Run</strong> to start the job or pipeline and open the run view in Databricks. Use <strong>Open</strong> to view the job or pipeline in the workspace without running.
        </p>
      </div>

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
            <strong>1. Your credentials (recommended):</strong> Open this app from <strong>Compute → Apps → payment-analysis</strong> so Databricks forwards your token. No PAT needed when user authorization (OBO) is enabled for the app.
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
                        No app settings loaded. Run Job 1 (Create Data Repositories) to seed Lakebase.
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

      {/* Steps — jobs 1–6: create repositories → simulate events → initialize ingestion → deploy dashboards → train models → deploy agents; optional Genie and pipelines */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium">Execution steps (1–10)</h2>
        <p className="text-sm text-muted-foreground">
          Run in order. Jobs 1–6: Create repositories → Simulate events → Initialize ingestion → Deploy dashboards → Train models → Deploy agents. Optionally run Genie sync and start Lakeflow pipelines when needed.
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

        {/* Step 1: Lakehouse bootstrap — creates app_config, rules, recommendations */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openJobPage("lakehouse_bootstrap")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobPage("lakehouse_bootstrap")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4" />
                1. Lakehouse bootstrap
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Run once to create app_config, approval_rules, approval_recommendations, and online_features. Enables Rules, Decisioning, and Dashboard. Save catalog &amp; schema above works after this (or table is created on first save).
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunJob("lakehouse_bootstrap")}
              disabled={!host || !isJobConfigured("lakehouse_bootstrap")}
            >
              {runningStepKey === "lakehouse_bootstrap" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openJobPage("lakehouse_bootstrap")}
              disabled={!host}
            >
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={openWarehouse}
              disabled={!host}
            >
              SQL Warehouse <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 2: Vector Search index */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openJobPage("vector_search_index")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobPage("vector_search_index")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4" />
                2. Vector Search index
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Create endpoint and delta-sync index from transaction_summaries_for_search. Powers similar-case recommendations in Decisioning. Run after Lakehouse Bootstrap.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunJob("vector_search_index")}
              disabled={!host || !isJobConfigured("vector_search_index")}
            >
              {runningStepKey === "vector_search_index" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button variant="outline" size="sm" onClick={() => openJobPage("vector_search_index")} disabled={!host}>
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 3: Gold views (data repos) */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openJobPage("create_gold_views")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobPage("create_gold_views")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <LayoutDashboard className="h-4 w-4" />
                3. Create gold views (data repos)
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Create 12+ analytical views for dashboards (v_executive_kpis, decline patterns, etc.). Uses warehouse and schema.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunJob("create_gold_views")}
              disabled={!host || !isJobConfigured("create_gold_views")}
            >
              {runningStepKey === "create_gold_views" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button variant="outline" size="sm" onClick={() => openJobPage("create_gold_views")} disabled={!host}>
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 4: Events producer simulator */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openJobPage("transaction_stream_simulator")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobPage("transaction_stream_simulator")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4" />
                4. Events producer (transaction simulator)
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Events simulator: generate test payment events (e.g. 1000/sec). Uses catalog and schema above.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunJob("transaction_stream_simulator")}
              disabled={!host || !isJobConfigured("transaction_stream_simulator")}
            >
              {runningStepKey === "transaction_stream_simulator" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button variant="outline" size="sm" onClick={() => openJobPage("transaction_stream_simulator")} disabled={!host}>
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 5: Optional real-time streaming */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openPipelinePage("payment_realtime_pipeline")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openPipelinePage("payment_realtime_pipeline")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                5. Optional: real-time streaming
              </CardTitle>
              <Badge variant="outline">Pipeline / Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Real-time Lakeflow pipeline and continuous stream processor for live payment events. Run when you need real-time analytics.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunPipeline("payment_realtime_pipeline")}
              disabled={!host || !defaults?.pipelines?.payment_realtime_pipeline || defaults.pipelines.payment_realtime_pipeline === "0"}
            >
              {runningStepKey === "payment_realtime_pipeline" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run (pipeline)
            </Button>
            <Button variant="outline" size="sm" onClick={() => openPipelinePage("payment_realtime_pipeline")} disabled={!host}>
              Open pipeline <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
            <Button
              variant="outline"
              onClick={() => handleRunJob("continuous_stream_processor")}
              disabled={!host || !isJobConfigured("continuous_stream_processor")}
            >
              {runningStepKey === "continuous_stream_processor" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run (stream processor)
            </Button>
            <Button variant="outline" size="sm" onClick={() => openJobPage("continuous_stream_processor")} disabled={!host}>
              Open job <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 6: Ingestion Lakeflow ETL pipeline */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openPipelinePage("payment_analysis_etl")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openPipelinePage("payment_analysis_etl")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                6. Ingestion & ETL (Lakeflow pipeline, Bronze → Silver → Gold)
              </CardTitle>
              <Badge variant="secondary">Pipeline</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Ingestion Lakeflow pipeline: process raw data into silver and gold tables and feed Vector Search. Start a pipeline update.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunPipeline("payment_analysis_etl")}
              disabled={!host || !defaults?.pipelines?.payment_analysis_etl || defaults.pipelines.payment_analysis_etl === "0"}
            >
              {runningStepKey === "payment_analysis_etl" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button variant="outline" size="sm" onClick={() => openPipelinePage("payment_analysis_etl")} disabled={!host}>
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 7: Train ML models */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openJobPage("train_ml_models")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobPage("train_ml_models")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="h-4 w-4" />
                7. Train ML models
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Train approval propensity, risk scoring, routing, and retry models. Uses catalog and schema.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunJob("train_ml_models")}
              disabled={!host || !isJobConfigured("train_ml_models")}
            >
              {runningStepKey === "train_ml_models" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button variant="outline" size="sm" onClick={() => openJobPage("train_ml_models")} disabled={!host}>
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Optional: Genie space sync — create/prepare Genie space */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openJobPage("genie_sync")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobPage("genie_sync")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <LayoutDashboard className="h-4 w-4" />
                Genie space sync (optional)
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Sync Genie space configuration and sample questions for natural language analytics over payment data.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunJob("genie_sync")}
              disabled={!host || !isJobConfigured("genie_sync")}
            >
              {runningStepKey === "genie_sync" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button variant="outline" size="sm" onClick={() => openJobPage("genie_sync")} disabled={!host}>
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 9: Orchestrator agent */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openJobPage("orchestrator_agent")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobPage("orchestrator_agent")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Bot className="h-4 w-4" />
                9. Run AI orchestrator
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Start the orchestrator to coordinate all AI agents (routing, retry, risk, decline, performance).
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunJob("orchestrator_agent")}
              disabled={!host || !isJobConfigured("orchestrator_agent")}
            >
              {runningStepKey === "orchestrator_agent" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button variant="outline" size="sm" onClick={() => openJobPage("orchestrator_agent")} disabled={!host}>
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 9b: Specialist agents */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Bot className="h-4 w-4" />
                9b. Run specialist agents
              </CardTitle>
              <Badge variant="secondary">Jobs</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Run individual AI agents: Smart Routing, Smart Retry, Decline Analyst, Risk Assessor, Performance Recommender. Each uses the Lakehouse Rules when configured.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            {[
              { key: "smart_routing_agent", label: "Smart Routing" },
              { key: "smart_retry_agent", label: "Smart Retry" },
              { key: "decline_analyst_agent", label: "Decline Analyst" },
              { key: "risk_assessor_agent", label: "Risk Assessor" },
              { key: "performance_recommender_agent", label: "Performance Recommender" },
            ].map(({ key, label }) => (
              <span key={key} className="inline-flex items-center gap-1">
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => handleRunJob(key)}
                  disabled={!host || !isJobConfigured(key)}
                  title={`Run ${label} and open run view`}
                >
                  {runningStepKey === key ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Play className="h-3 w-3 mr-1" />}
                  Run
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openJobPage(key)}
                  disabled={!host}
                  title={`Open ${label} job in Databricks workspace`}
                >
                  {label}
                  <ExternalLink className="ml-1 h-3 w-3" />
                </Button>
              </span>
            ))}
          </CardContent>
        </Card>

        {/* Step 10: Publish dashboards (embed credentials for app UI) */}
        <Card
          className="card-interactive cursor-pointer"
          onClick={() => openJobPage("publish_dashboards")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobPage("publish_dashboards")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <LayoutDashboard className="h-4 w-4" />
                10. Update dashboards (publish for embed)
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Publish dashboards with embed credentials so the app can embed AI/BI dashboards. Run after bundle deploy or when you need to refresh published state.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => handleRunJob("publish_dashboards")}
              disabled={!host || !isJobConfigured("publish_dashboards")}
            >
              {runningStepKey === "publish_dashboards" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Run
            </Button>
            <Button variant="outline" size="sm" onClick={() => openJobPage("publish_dashboards")} disabled={!host}>
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>
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
          <Button
            variant="outline"
            size="sm"
            onClick={openJobsList}
            disabled={!host}
          >
            All jobs <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
