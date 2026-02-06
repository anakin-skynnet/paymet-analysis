import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Code2, Brain, TrendingUp, Shield, Waypoints, RotateCcw } from "lucide-react";
import { getMLflowUrl, getWorkspaceUrl } from "@/config/workspace";

export const Route = createFileRoute("/_sidebar/models")({
  component: () => <Models />,
});

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

interface ModelInfo {
  id: string;
  name: string;
  description: string;
  modelType: string;
  features: string[];
  metrics: { name: string; value: string }[];
  icon: React.ReactNode;
  color: string;
  catalogPath: string;
}

const models: ModelInfo[] = [
  {
    id: "approval_propensity",
    name: "Approval Propensity Model",
    description: "Predicts the likelihood of transaction approval based on payment characteristics and risk signals. Uses Random Forest Classifier to optimize routing decisions.",
    modelType: "RandomForestClassifier",
    features: ["amount", "fraud_score", "device_trust_score", "is_cross_border", "retry_count", "uses_3ds"],
    metrics: [
      { name: "Accuracy", value: "~92%" },
      { name: "Precision", value: "~89%" },
      { name: "Recall", value: "~94%" },
      { name: "ROC AUC", value: "~0.96" },
    ],
    icon: <TrendingUp className="w-5 h-5" />,
    color: "text-green-500",
    catalogPath: "ahs_demos_catalog.ahs_demo_payment_analysis_dev.approval_propensity_model",
  },
  {
    id: "risk_scoring",
    name: "Risk Scoring Model",
    description: "Evaluates transaction risk by combining fraud indicators, AML signals, and behavioral patterns. Identifies high-risk transactions for review.",
    modelType: "RandomForestClassifier",
    features: ["amount", "fraud_score", "aml_risk_score", "is_cross_border", "processing_time_ms", "device_trust_score"],
    metrics: [
      { name: "Accuracy", value: "~88%" },
      { name: "Precision", value: "~85%" },
      { name: "Recall", value: "~90%" },
      { name: "ROC AUC", value: "~0.93" },
    ],
    icon: <Shield className="w-5 h-5" />,
    color: "text-red-500",
    catalogPath: "ahs_demos_catalog.ahs_demo_payment_analysis_dev.risk_scoring_model",
  },
  {
    id: "smart_routing",
    name: "Smart Routing Policy",
    description: "Determines optimal payment solution (standard, 3DS, network token, passkey) based on merchant segment, risk profile, and historical performance.",
    modelType: "RandomForestClassifier",
    features: ["amount", "fraud_score", "is_cross_border", "uses_3ds", "device_trust_score", "merchant_segment_*"],
    metrics: [
      { name: "Accuracy", value: "~75%" },
      { name: "Classes", value: "4" },
      { name: "Solutions", value: "standard, 3ds, network_token, passkey" },
    ],
    icon: <Waypoints className="w-5 h-5" />,
    color: "text-blue-500",
    catalogPath: "ahs_demos_catalog.ahs_demo_payment_analysis_dev.smart_routing_policy",
  },
  {
    id: "smart_retry",
    name: "Smart Retry Policy",
    description: "Identifies declined transactions with high recovery potential. Recommends optimal retry timing and strategy based on decline reason and transaction context.",
    modelType: "RandomForestClassifier",
    features: ["decline_encoded", "retry_count", "amount", "is_recurring", "fraud_score", "device_trust_score"],
    metrics: [
      { name: "Accuracy", value: "~81%" },
      { name: "Precision", value: "~78%" },
      { name: "Recall", value: "~83%" },
      { name: "Recovery Rate", value: "+15-25%" },
    ],
    icon: <RotateCcw className="w-5 h-5" />,
    color: "text-purple-500",
    catalogPath: "ahs_demos_catalog.ahs_demo_payment_analysis_dev.smart_retry_policy",
  },
];

function Models() {
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

      {/* Info Card */}
      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <Brain className="w-5 h-5 text-primary mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium">
                All models are trained using scikit-learn and registered to Unity Catalog
              </p>
              <p className="text-xs text-muted-foreground">
                Click "Training Notebook" to view the complete training pipeline, including feature engineering,
                model evaluation, and Unity Catalog registration. All models can be served via Databricks Model Serving.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Models Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {models.map((model) => (
          <Card key={model.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <div className={model.color}>{model.icon}</div>
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
                <Badge variant="secondary">{model.modelType}</Badge>
              </div>

              {/* Unity Catalog Path */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">Unity Catalog</p>
                <code className="text-xs bg-muted px-2 py-1 rounded block font-mono break-all">
                  {model.catalogPath}
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
                <div className="grid grid-cols-2 gap-2">
                  {model.metrics.map((metric) => (
                    <div key={metric.name} className="bg-muted/50 px-2 py-1.5 rounded text-center">
                      <p className="text-xs text-muted-foreground">{metric.name}</p>
                      <p className="text-sm font-semibold">{metric.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="default"
                  size="sm"
                  className="flex-1 min-w-0"
                  onClick={() => openModelInRegistry(model.catalogPath)}
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

      {/* Additional Info */}
      <Card>
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
