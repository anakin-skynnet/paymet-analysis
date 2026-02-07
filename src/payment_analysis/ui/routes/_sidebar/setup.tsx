import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Play,
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
} from "lucide-react";

export const Route = createFileRoute("/_sidebar/setup")({
  component: () => <SetupRun />,
});

const API_BASE = "/api/setup";

type SetupDefaults = {
  warehouse_id: string;
  catalog: string;
  schema: string;
  jobs: Record<string, string>;
  pipelines: Record<string, string>;
  workspace_host: string;
};

type RunJobResult = {
  job_id: string;
  run_id: number;
  run_page_url: string;
  message: string;
};

type RunPipelineResult = {
  pipeline_id: string;
  update_id: string;
  pipeline_page_url: string;
  message: string;
};

async function fetchDefaults(): Promise<SetupDefaults> {
  const res = await fetch(`${API_BASE}/defaults`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function runJob(body: {
  job_id: string;
  catalog?: string;
  schema?: string;
  warehouse_id?: string;
  events_per_second?: string;
  duration_minutes?: string;
}): Promise<RunJobResult> {
  const res = await fetch(`${API_BASE}/run-job`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

async function runPipeline(body: { pipeline_id: string }): Promise<RunPipelineResult> {
  const res = await fetch(`${API_BASE}/run-pipeline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
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
  const { data: defaults, isLoading: loadingDefaults } = useQuery({
    queryKey: ["setup", "defaults"],
    queryFn: fetchDefaults,
  });

  const [warehouseId, setWarehouseId] = useState("");
  const [catalog, setCatalog] = useState("");
  const [schema, setSchema] = useState("");
  const [lastResult, setLastResult] = useState<{
    type: "job" | "pipeline" | "config";
    url?: string;
    message: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (defaults) {
      setWarehouseId(defaults.warehouse_id);
      setCatalog(defaults.catalog);
      setSchema(defaults.schema);
    }
  }, [defaults]);

  const runJobMutation = useMutation({
    mutationFn: runJob,
    onSuccess: (data) => {
      setLastResult({
        type: "job",
        url: data.run_page_url,
        message: data.message,
      });
      setError(null);
      qc.invalidateQueries({ queryKey: ["setup"] });
    },
    onError: (e: Error) => {
      setError(e.message);
      setLastResult(null);
    },
  });

  const runPipelineMutation = useMutation({
    mutationFn: runPipeline,
    onSuccess: (data) => {
      setLastResult({
        type: "pipeline",
        url: data.pipeline_page_url,
        message: data.message,
      });
      setError(null);
      qc.invalidateQueries({ queryKey: ["setup"] });
    },
    onError: (e: Error) => {
      setError(e.message);
      setLastResult(null);
    },
  });

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

  const params = {
    catalog,
    schema,
    warehouse_id: warehouseId,
  };

  const triggerJob = (jobKey: string) => {
    const jobId = defaults?.jobs?.[jobKey];
    if (!jobId) return;
    runJobMutation.mutate({ job_id: jobId, ...params });
  };

  const triggerPipeline = (pipelineKey: string) => {
    const pipelineId = defaults?.pipelines?.[pipelineKey];
    if (!pipelineId) return;
    runPipelineMutation.mutate({ pipeline_id: pipelineId });
  };

  const saveConfig = () => {
    updateConfigMutation.mutate({ catalog, schema });
  };

  const pending = runJobMutation.isPending || runPipelineMutation.isPending;
  const host = defaults?.workspace_host || "";
  const openJobRun = (jobKey: string) => {
    const id = defaults?.jobs?.[jobKey];
    if (id && host) window.open(`${host}/#job/${id}/run`, "_blank");
  };
  const openPipeline = (pipelineKey: string) => {
    const id = defaults?.pipelines?.[pipelineKey];
    if (id && host) window.open(`${host}/pipelines/${id}`, "_blank");
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
      <div>
        <h1 className="text-2xl font-semibold">Setup & Run</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Follow steps 1–6 in order: deploy bundle first, then data ingestion, ETL, gold views, Lakehouse SQL, ML training, and optional AI agents. See docs for full guide.
        </p>
      </div>

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
                <td className="py-2 pr-4 align-top">Dashboards (11 Lakeview)</td>
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
              placeholder="e.g. bf12ee0011ea4ced"
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
              placeholder="ahs_demo_payment_analysis_dev"
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
          {lastResult.type !== "config" && lastResult.url && (
            <Button
              variant="link"
              size="sm"
              className="ml-auto"
              onClick={() => window.open(lastResult!.url, "_blank")}
            >
              Open <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          )}
        </div>
      )}

      {/* Steps — order matches docs/DEPLOYMENT.md (Demo setup) */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium">Execution steps (1–7)</h2>
        <p className="text-sm text-muted-foreground">
          Run in order. Step 4 is SQL in the warehouse; steps 5–6 register models and agents.
        </p>

        {/* Step 1: Data ingestion — click opens job run in Databricks */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openJobRun("transaction_stream_simulator")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobRun("transaction_stream_simulator")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4" />
                1. Data ingestion (transaction simulator)
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Events simulator: generate test payment events (e.g. 1000/sec). Uses catalog and schema above.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => triggerJob("transaction_stream_simulator")}
              disabled={pending}
            >
              {runJobMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Run simulator
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/#job/${defaults?.jobs?.transaction_stream_simulator}/run`,
                  "_blank"
                )
              }
            >
              Open job (run) <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 2: Ingestion / Lakeflow pipeline — click opens pipeline in Databricks */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openPipeline("payment_analysis_etl")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openPipeline("payment_analysis_etl")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                2. Ingestion & ETL (Lakeflow pipeline, Bronze → Silver → Gold)
              </CardTitle>
              <Badge variant="secondary">Pipeline</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Ingestion Lakeflow pipeline: process raw data into silver and gold tables. Start a pipeline update.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              variant="default"
              onClick={() => triggerPipeline("payment_analysis_etl")}
              disabled={pending}
            >
              {runPipelineMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Start ETL pipeline
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/pipelines/${defaults?.pipelines?.payment_analysis_etl}`,
                  "_blank"
                )
              }
            >
              Open pipeline <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 3: Gold views — click opens job run in Databricks */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openJobRun("create_gold_views")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobRun("create_gold_views")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <LayoutDashboard className="h-4 w-4" />
                3. Create gold views (analytics)
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Create 12+ analytical views for dashboards (v_executive_kpis, decline patterns, etc.). Uses warehouse and schema.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => triggerJob("create_gold_views")}
              disabled={pending}
            >
              {runJobMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Run gold views job
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/#job/${defaults?.jobs?.create_gold_views}/run`,
                  "_blank"
                )
              }
            >
              Open job (run) <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 4: Lakehouse tables (SQL) — open SQL Warehouse to run scripts */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() =>
            window.open(
              `${defaults?.workspace_host || ""}/sql/warehouses/${warehouseId || defaults?.warehouse_id}`,
              "_blank"
            )
          }
          role="button"
          tabIndex={0}
          onKeyDown={(e) =>
            e.key === "Enter" &&
            window.open(
              `${defaults?.workspace_host || ""}/sql/warehouses/${warehouseId || defaults?.warehouse_id}`,
              "_blank"
            )
          }
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4" />
                4. Lakehouse tables (SQL)
              </CardTitle>
              <Badge variant="outline">SQL</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              In SQL Warehouse run lakehouse_bootstrap.sql (same catalog/schema). Enables Rules, recommendations, and Dashboard features.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/sql/warehouses/${warehouseId || defaults?.warehouse_id}`,
                  "_blank"
                )
              }
            >
              Open SQL Warehouse <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/explore/data/${catalog || defaults?.catalog}/${schema || defaults?.schema}`,
                  "_blank"
                )
              }
            >
              Explore schema
            </Button>
          </CardContent>
        </Card>

        {/* Step 5: Train ML models — click opens job run in Databricks */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openJobRun("train_ml_models")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobRun("train_ml_models")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="h-4 w-4" />
                5. Train ML models
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Train approval propensity, risk scoring, routing, and retry models. Uses catalog and schema.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => triggerJob("train_ml_models")}
              disabled={pending}
            >
              {runJobMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Run ML training
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/#job/${defaults?.jobs?.train_ml_models}/run`,
                  "_blank"
                )
              }
            >
              Open job (run) <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 5: Orchestrator agent — click opens job run in Databricks */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openJobRun("orchestrator_agent")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openJobRun("orchestrator_agent")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Bot className="h-4 w-4" />
                6. Run AI orchestrator
              </CardTitle>
              <Badge variant="secondary">Job</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Start the orchestrator to coordinate all AI agents (routing, retry, risk, decline, performance).
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              onClick={() => triggerJob("orchestrator_agent")}
              disabled={pending}
            >
              {runJobMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Run orchestrator
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/#job/${defaults?.jobs?.orchestrator_agent}/run`,
                  "_blank"
                )
              }
            >
              Open job (run) <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        {/* Step 6b: Run specialist agents (one-click each) */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Bot className="h-4 w-4" />
                6b. Run specialist agents
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
              <div key={key} className="flex gap-1 items-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => triggerJob(key)}
                  disabled={pending || !defaults?.jobs?.[key]}
                >
                  {runJobMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Play className="h-3 w-3 mr-1" />}
                  {label}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2"
                  onClick={() => defaults?.jobs?.[key] && window.open(`${defaults?.workspace_host || ""}/#job/${defaults.jobs[key]}/run`, "_blank")}
                  disabled={!defaults?.jobs?.[key]}
                >
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Step 7: Real-time Lakeflow pipeline (optional) — click opens pipeline in Databricks */}
        <Card
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => openPipeline("payment_realtime_pipeline")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && openPipeline("payment_realtime_pipeline")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                7. Real-time streaming (Lakeflow pipeline, optional)
              </CardTitle>
              <Badge variant="outline">Pipeline</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Start the continuous real-time payment stream pipeline in Lakeflow.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              variant="secondary"
              onClick={() => triggerPipeline("payment_realtime_pipeline")}
              disabled={pending}
            >
              {runPipelineMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Start real-time pipeline
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/pipelines/${defaults?.pipelines?.payment_realtime_pipeline}`,
                  "_blank"
                )
              }
            >
              Open pipeline <ExternalLink className="ml-1 h-3 w-3" />
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
            onClick={() =>
              window.open(
                `${defaults?.workspace_host || ""}/#job`,
                "_blank"
              )
            }
          >
            Jobs <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              window.open(
                `${defaults?.workspace_host || ""}/pipelines`,
                "_blank"
              )
            }
          >
            Pipelines <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              window.open(
                `${defaults?.workspace_host || ""}/sql/warehouses/${warehouseId || defaults?.warehouse_id}`,
                "_blank"
              )
            }
          >
            SQL Warehouse
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              window.open(
                `${defaults?.workspace_host || ""}/explore/data/${catalog || defaults?.catalog}/${schema || defaults?.schema}`,
                "_blank"
              )
            }
          >
            Explore schema
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              window.open(
                `${defaults?.workspace_host || ""}/genie`,
                "_blank"
              )
            }
          >
            Genie (Ask Data) <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              window.open(
                `${defaults?.workspace_host || ""}/#job/${defaults?.jobs?.continuous_stream_processor}/run`,
                "_blank"
              )
            }
          >
            Stream processor (run)
          </Button>
          {defaults?.jobs?.test_agent_framework && defaults.jobs.test_agent_framework !== "0" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${defaults?.workspace_host || ""}/#job/${defaults?.jobs?.test_agent_framework}/run`,
                  "_blank"
                )
              }
            >
              Test Agent Framework <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open(`${defaults?.workspace_host || ""}/#job`, "_blank")}
          >
            All jobs
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
