import { createFileRoute } from "@tanstack/react-router";
import { Suspense } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ExternalLink, Code2, Brain, TrendingUp, Shield, Waypoints, RotateCcw, AlertCircle } from "lucide-react";
import { getMLflowUrl, getWorkspaceUrl, openInDatabricks, getLakeviewDashboardUrl } from "@/config/workspace";
import { DataSourceBadge } from "@/components/apx/data-source-badge";
import { useGetModelsSuspense, type ModelOut } from "@/lib/api";
import { useEntity } from "@/contexts/entity-context";
import { openNotebookInDatabricks, openFolderInDatabricks } from "@/lib/notebooks";
import { ErrorBoundary } from "react-error-boundary";

function ModelsPageErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
  return (
    <Card className="glass-card border border-destructive/30 max-w-lg mx-auto mt-12">
      <CardContent className="py-8 text-center space-y-4">
        <Brain className="w-10 h-10 text-destructive mx-auto" />
        <h2 className="text-lg font-semibold">Failed to load ML Models</h2>
        <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : "Unknown error"}</p>
        <Button onClick={resetErrorBoundary}>Try again</Button>
      </CardContent>
    </Card>
  );
}

export const Route = createFileRoute("/_sidebar/models")({
  component: () => (
    <ErrorBoundary FallbackComponent={ModelsPageErrorFallback}>
      <Models />
    </ErrorBoundary>
  ),
});

const openMLflow = () => openInDatabricks(getMLflowUrl());

const openModelInRegistry = (catalogPath: string) => {
  const base = getWorkspaceUrl();
  if (base && catalogPath) openInDatabricks(`${base}/ml/models/${catalogPath}`);
};

const modelIdIcon: Record<string, React.ReactNode> = {
  approval_propensity: <TrendingUp className="w-5 h-5" />,
  risk_scoring: <Shield className="w-5 h-5" />,
  smart_routing: <Waypoints className="w-5 h-5" />,
  smart_retry: <RotateCcw className="w-5 h-5" />,
};
const modelIdColor: Record<string, string> = {
  approval_propensity: "text-green-500",
  risk_scoring: "text-red-500",
  smart_routing: "text-blue-500",
  smart_retry: "text-purple-500",
};

/** Refresh model list from backend/Databricks every 30s for real-time visibility. */
const REFRESH_MODELS_MS = 30_000;

function ModelsGridSkeleton() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i} className="glass-card border border-border/80">
          <CardHeader>
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full mt-2" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-20 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ModelsErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
  return (
    <Card className="glass-card border border-destructive/30">
      <CardContent className="py-6 flex items-center gap-2">
        <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
        <p className="text-sm text-destructive flex-1">
          Failed to load models: {error instanceof Error ? error.message : "Unknown error"}
        </p>
        <Button variant="outline" size="sm" onClick={resetErrorBoundary}>
          Try again
        </Button>
      </CardContent>
    </Card>
  );
}

function ModelCard({ model }: { model: ModelOut }) {
  return (
    <Card
      className="glass-card border border-border/80 cursor-pointer card-interactive"
      onClick={() => openModelInRegistry(model.catalog_path)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && openModelInRegistry(model.catalog_path)}
    >
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className={modelIdColor[model.id] ?? "text-foreground"}>{modelIdIcon[model.id] ?? <Brain className="w-5 h-5" />}</div>
          {model.name}
        </CardTitle>
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Purpose</p>
          <CardDescription className="text-sm leading-relaxed mt-0">
            {model.description}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Model Type */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Model Type</p>
          <Badge variant="secondary">{model.model_type}</Badge>
        </div>

        {/* Unity Catalog Path */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Unity Catalog</p>
          <code className="text-xs bg-muted px-2 py-1 rounded block font-mono break-all">
            {model.catalog_path}
          </code>
        </div>

        {/* Features */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Features ({model.features.length})</p>
          <div className="flex flex-wrap gap-1">
            {model.features.map((feature) => (
              <Badge key={feature} variant="outline" className="text-xs">
                {feature}
              </Badge>
            ))}
          </div>
        </div>

        {/* Metrics */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Performance Metrics</p>
          {(model.metrics?.length ?? 0) > 0 ? (
            <div className="grid grid-cols-2 gap-2">
              {(model.metrics ?? []).map((metric) => (
                <div key={metric.name} className="bg-muted/50 px-2 py-1.5 rounded text-center">
                  <p className="text-xs text-muted-foreground">{metric.name}</p>
                  <p className="text-sm font-semibold">{metric.value}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No metrics from last run. Open MLflow or Model Registry for latest run metrics.</p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
          <Button variant="default" size="sm" className="w-full justify-center" onClick={() => openModelInRegistry(model.catalog_path)}>
            Open in Model Registry
            <ExternalLink className="w-3 h-3 ml-1.5" />
          </Button>
          <Button variant="outline" size="sm" className="w-full justify-center" onClick={() => openNotebookInDatabricks("train_models")}>
            <Code2 className="w-4 h-4 mr-1.5" />
            Training Notebook
            <ExternalLink className="w-3 h-3 ml-1.5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ModelsGrid() {
  const { entity } = useEntity();
  const { data: resp } = useGetModelsSuspense({
    params: { entity },
    query: { refetchInterval: REFRESH_MODELS_MS },
  });
  const modelList: ModelOut[] = resp?.data ?? [];

  if (modelList.length === 0) {
    return (
      <Card className="glass-card border border-border/80">
        <CardContent className="py-12 text-center">
          <Brain className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No models registered yet. Run Setup & Run step 7 to train and register models.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {modelList.map((model) => (
        <ModelCard key={model.id} model={model} />
      ))}
    </div>
  );
}

function Models() {
  return (
    <div className="space-y-6">
      {/* Header with Links */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="page-section-title text-2xl font-semibold">ML Models</h1>
              <DataSourceBadge label="From UC & MLflow" />
            </div>
            <p className="page-section-description">
              Four models (approval propensity, risk, routing, retry) from Setup & Run step 7. All are <strong>HistGradientBoostingClassifier</strong> (scikit-learn), trained in one MLflow experiment on Unity Catalog data; use in Decisioning and with Rules.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => openFolderInDatabricks("ml")}>
              <Code2 className="w-4 h-4 mr-2" />
              Open ML folder
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => openNotebookInDatabricks("train_models")}>
              <Code2 className="w-4 h-4 mr-2" />
              Training Notebook
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button variant="outline" size="sm" onClick={openMLflow}>
              <Brain className="w-4 h-4 mr-2" />
              MLflow Experiments
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
      </div>

      {/* Info Card */}
      <Card className="glass-card border border-primary/20 bg-primary/5">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <Brain className="w-5 h-5 text-primary mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium">
                Model types: all four are HistGradientBoostingClassifier (scikit-learn), trained and registered to Unity Catalog
              </p>
              <p className="text-xs text-muted-foreground">
                Each card shows the purpose of the model experiment, feature set, and catalog path. The backend uses your Databricks config (catalog/schema). Open <strong>MLflow</strong> or <strong>Model Registry</strong> for latest run metrics, or use <strong>Decisioning</strong> for live predictions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Models Grid — Suspense-wrapped */}
      <ErrorBoundary FallbackComponent={ModelsErrorFallback}>
        <Suspense fallback={<ModelsGridSkeleton />}>
          <ModelsGrid />
        </Suspense>
      </ErrorBoundary>

      {/* Combined business impact — click opens Financial Impact dashboard */}
      <Card
        className="glass-card border border-border/80 cursor-pointer card-interactive"
        onClick={() => openInDatabricks(getLakeviewDashboardUrl("financial_impact"))}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter") openInDatabricks(getLakeviewDashboardUrl("financial_impact")); }}
      >
        <CardHeader>
          <CardTitle className="text-lg">Combined business impact</CardTitle>
          <CardDescription>
            Together, approval propensity, risk scoring, smart routing, and smart retry drive higher approval rates, fewer false declines, and better recovery. View the Financial Impact and Smart Routing dashboards in Databricks for real metrics from your workspace.
          </CardDescription>
        </CardHeader>
        <CardContent onClick={(e) => e.stopPropagation()}>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => openInDatabricks(getLakeviewDashboardUrl("financial_impact"))}>
              Financial Impact dashboard
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => openInDatabricks(getLakeviewDashboardUrl("routing_optimization"))}>
              Smart Routing dashboard
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Model Training Pipeline — click opens MLflow in Databricks */}
      <Card
        className="glass-card border border-border/80 cursor-pointer card-interactive"
        onClick={() => openInDatabricks(getMLflowUrl())}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter") openInDatabricks(getMLflowUrl()); }}
      >
        <CardHeader>
          <CardTitle className="text-lg">Model Training Pipeline</CardTitle>
          <CardDescription>
            Automated training workflow (Setup & Run step 7). All four models are HistGradientBoostingClassifier; trained in one MLflow experiment and registered to Unity Catalog.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-semibold">1</span>
              </div>
              <div>
                <p className="font-medium">Data Loading</p>
                <p className="text-xs text-muted-foreground">
                  Loads training data from Unity Catalog Silver table (payments_enriched_silver, last 30 days)
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-semibold">2</span>
              </div>
              <div>
                <p className="font-medium">Feature Engineering</p>
                <p className="text-xs text-muted-foreground">
                  Per-model feature sets; missing values filled, categoricals encoded (e.g. decline_reason, merchant_segment one-hot)
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-semibold">3</span>
              </div>
              <div>
                <p className="font-medium">Model Training & Evaluation</p>
                <p className="text-xs text-muted-foreground">
                  Trains four HistGradientBoostingClassifier models (approval propensity, risk scoring, smart routing, smart retry), train/test split, logs params and metrics to MLflow
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-semibold">4</span>
              </div>
              <div>
                <p className="font-medium">Unity Catalog Registration</p>
                <p className="text-xs text-muted-foreground">
                  Registers each model to UC with signature (approval_propensity_model, risk_scoring_model, smart_routing_policy, smart_retry_policy) for serving and Decisioning
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
