import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ExternalLink, Code2, Brain, TrendingUp, Shield, Waypoints, RotateCcw, AlertCircle } from "lucide-react";
import { getMLflowUrl, getWorkspaceUrl } from "@/config/workspace";

export const Route = createFileRoute("/_sidebar/models")({
  component: () => <Models />,
});

/** API response shape for GET /api/analytics/models */
interface ModelOut {
  id: string;
  name: string;
  description: string;
  model_type: string;
  features: string[];
  catalog_path: string;
  metrics: { name: string; value: string }[];
}

async function fetchModels(): Promise<ModelOut[]> {
  const res = await fetch("/api/analytics/models");
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const openNotebook = async (notebookId: string) => {
  try {
    const response = await fetch(`/api/notebooks/notebooks/${notebookId}/url`);
    const data = await response.json();
    window.open(data.url, "_blank");
  } catch (error) {
    console.error("Failed to open notebook:", error);
  }
};

const openFolder = async (folderId: string) => {
  try {
    const response = await fetch(`/api/notebooks/notebooks/folders/${folderId}/url`);
    const data = await response.json();
    window.open(data.url, "_blank");
  } catch (error) {
    console.error("Failed to open folder:", error);
  }
};

const openMLflow = () => {
  const mlflowUrl = getMLflowUrl();
  window.open(mlflowUrl, "_blank");
};

const openModelInRegistry = (catalogPath: string) => {
  const base = getWorkspaceUrl();
  window.open(`${base}/ml/models/${catalogPath}`, "_blank");
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

function Models() {
  const { data: models, isLoading, isError, error } = useQuery({
    queryKey: ["analytics", "models"],
    queryFn: fetchModels,
  });
  const modelList = models ?? [];

  return (
    <div className="space-y-6">
      {/* Header with Links */}
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">ML Models</h1>
            <p className="text-sm text-muted-foreground mt-2">
              Production ML models trained on Unity Catalog data and tracked with MLflow
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => openFolder("ml")}
            >
              <Code2 className="w-4 h-4 mr-2" />
              Open ML folder in Workspace
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => openNotebook("train_models")}
            >
              <Code2 className="w-4 h-4 mr-2" />
              Training Notebook
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={openMLflow}
            >
              <Brain className="w-4 h-4 mr-2" />
              MLflow Experiments
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </div>
      </div>

      {/* Info Card — real values from Databricks */}
      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <Brain className="w-5 h-5 text-primary mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium">
                All models are trained using scikit-learn and registered to Unity Catalog
              </p>
              <p className="text-xs text-muted-foreground">
                Model list, catalog paths, and metrics are fetched from the backend; the backend uses your Databricks config (catalog/schema) for Unity Catalog. Configure DATABRICKS_* for connectivity and data access. Open <strong>MLflow</strong> or <strong>Model Registry</strong> for latest run metrics, or use <strong>Decisioning</strong> for live predictions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {isError && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="py-6 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
            <p className="text-sm text-destructive">
              Failed to load models: {error instanceof Error ? error.message : "Unknown error"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Models Grid — data from backend */}
      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
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
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {modelList.map((model) => (
            <Card
              key={model.id}
              className="cursor-pointer hover:shadow-lg transition-shadow"
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
                <CardDescription className="text-sm leading-relaxed">
                  {model.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Model Type */}
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Model Type</p>
                  <Badge variant="secondary">{model.model_type}</Badge>
                </div>

                {/* Unity Catalog Path — from backend (config catalog/schema) */}
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

                {/* Metrics — from backend (empty until training writes to a view) */}
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2">Performance Metrics</p>
                  {model.metrics.length > 0 ? (
                    <div className="grid grid-cols-2 gap-2">
                      {model.metrics.map((metric) => (
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
                <div className="flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="default"
                    size="sm"
                    className="flex-1 min-w-0"
                    onClick={() => openModelInRegistry(model.catalog_path)}
                  >
                    Open in Model Registry
                    <ExternalLink className="w-3 h-3 ml-2" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 min-w-0"
                    onClick={() => openNotebook("train_models")}
                  >
                    <Code2 className="w-4 h-4 mr-2" />
                    Training Notebook
                    <ExternalLink className="w-3 h-3 ml-2" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Combined business impact — click opens Financial Impact dashboard */}
      <Card
        className="cursor-pointer hover:shadow-md transition-shadow"
        onClick={() => getWorkspaceUrl() && window.open(getWorkspaceUrl() + "/sql/dashboards/financial_impact", "_blank")}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && getWorkspaceUrl() && window.open(getWorkspaceUrl() + "/sql/dashboards/financial_impact", "_blank")}
      >
        <CardHeader>
          <CardTitle className="text-lg">Combined business impact</CardTitle>
          <CardDescription>
            Together, approval propensity, risk scoring, smart routing, and smart retry drive higher approval rates, fewer false declines, and better recovery. View the Financial Impact and Smart Routing dashboards in Databricks for real metrics from your workspace.
          </CardDescription>
        </CardHeader>
        <CardContent onClick={(e) => e.stopPropagation()}>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => window.open(getWorkspaceUrl() + "/sql/dashboards/financial_impact", "_blank")}>
              Financial Impact dashboard
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.open(getWorkspaceUrl() + "/sql/dashboards/routing_optimization", "_blank")}>
              Smart Routing dashboard
              <ExternalLink className="w-3 h-3 ml-2" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Model Training Pipeline — click opens MLflow in Databricks */}
      <Card
        className="cursor-pointer hover:shadow-md transition-shadow"
        onClick={() => getMLflowUrl() && window.open(getMLflowUrl(), "_blank")}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && getMLflowUrl() && window.open(getMLflowUrl(), "_blank")}
      >
        <CardHeader>
          <CardTitle className="text-lg">Model Training Pipeline</CardTitle>
          <CardDescription>
            Automated training workflow using Databricks Jobs and Unity Catalog
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
                  Loads training data from Unity Catalog Silver tables (payments_enriched_silver)
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
                  Extracts and transforms features, handles missing values, encodes categorical variables
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
                  Trains Random Forest models, evaluates using train/test split, logs metrics to MLflow
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
                  Registers models to Unity Catalog with signatures, making them available for serving and inference
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
