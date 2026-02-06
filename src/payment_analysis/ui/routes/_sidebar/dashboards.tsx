import React, { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3, TrendingUp, Shield, DollarSign, Gauge, Users, Calendar, Lock, Award, Zap, ExternalLink, Code2 } from "lucide-react";
import { getWorkspaceUrl } from "@/config/workspace";

export const Route = createFileRoute("/_sidebar/dashboards")({
  component: Component,
});

interface Dashboard {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  url_path: string | null;
}

interface DashboardList {
  dashboards: Dashboard[];
  total: number;
  categories: Record<string, number>;
}

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  executive: Award,
  operations: Zap,
  analytics: BarChart3,
  technical: Gauge,
};

const dashboardIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  executive_overview: BarChart3,
  decline_analysis: TrendingUp,
  realtime_monitoring: Gauge,
  fraud_risk_analysis: Shield,
  merchant_performance: Users,
  routing_optimization: Zap,
  daily_trends: Calendar,
  authentication_security: Lock,
  financial_impact: DollarSign,
  performance_latency: Gauge,
};

// Map dashboards to their underlying notebooks
const dashboardNotebooks: Record<string, string[]> = {
  executive_overview: ["gold_views_sql"],
  decline_analysis: ["gold_views_sql", "silver_transform"],
  realtime_monitoring: ["realtime_pipeline", "gold_views_sql"],
  fraud_risk_analysis: ["train_models", "gold_views_sql"],
  merchant_performance: ["gold_views_sql", "silver_transform"],
  routing_optimization: ["train_models", "gold_views_sql", "agent_framework"],
  daily_trends: ["gold_views_sql"],
  authentication_security: ["silver_transform", "gold_views_sql"],
  financial_impact: ["gold_views_sql"],
  performance_latency: ["gold_views_sql"],
};

export function Component() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [categories, setCategories] = useState<Record<string, number>>({});

  useEffect(() => {
    fetchDashboards();
  }, [selectedCategory]);

  const fetchDashboards = async () => {
    try {
      setLoading(true);
      const categoryParam = selectedCategory ? `?category=${selectedCategory}` : "";
      const response = await fetch(`/api/dashboards/dashboards${categoryParam}`);
      const data: DashboardList = await response.json();
      setDashboards(data.dashboards);
      setCategories(data.categories);
    } catch (error) {
      console.error("Failed to fetch dashboards:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDashboardClick = (dashboard: Dashboard) => {
    if (dashboard.url_path) {
      // Open in new tab pointing to Databricks workspace
      const databricksUrl = `${getWorkspaceUrl()}${dashboard.url_path}`;
      window.open(databricksUrl, "_blank");
    }
  };

  const handleNotebookClick = async (notebookId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent dashboard card click
    try {
      const response = await fetch(`/api/notebooks/notebooks/${notebookId}/url`);
      const data = await response.json();
      window.open(data.url, "_blank");
    } catch (error) {
      console.error("Failed to open notebook:", error);
    }
  };

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      executive: "bg-purple-500/10 text-purple-700 dark:text-purple-400",
      operations: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
      analytics: "bg-green-500/10 text-green-700 dark:text-green-400",
      technical: "bg-orange-500/10 text-orange-700 dark:text-orange-400",
    };
    return colors[category] || "bg-gray-500/10 text-gray-700 dark:text-gray-400";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Analytics Dashboards</h1>
        <p className="text-muted-foreground mt-2">
          Access all payment analysis dashboards powered by Databricks AI/BI
        </p>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={selectedCategory === null ? "default" : "outline"}
          size="sm"
          onClick={() => setSelectedCategory(null)}
        >
          All Dashboards ({Object.values(categories).reduce((a, b) => a + b, 0)})
        </Button>
        {Object.entries(categories).map(([category, count]) => {
          const IconComponent = categoryIcons[category];
          return (
            <Button
              key={category}
              variant={selectedCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category)}
            >
              {IconComponent && <IconComponent className="w-4 h-4 mr-2" />}
              {category.charAt(0).toUpperCase() + category.slice(1)} ({count})
            </Button>
          );
        })}
      </div>

      {/* Dashboard Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader>
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {dashboards.map((dashboard) => {
            const IconComponent = dashboardIcons[dashboard.id] || BarChart3;
            const notebookIds = dashboardNotebooks[dashboard.id] || [];
            return (
              <Card
                key={dashboard.id}
                className="cursor-pointer hover:shadow-lg transition-all hover:scale-[1.02] group"
                onClick={() => handleDashboardClick(dashboard)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <IconComponent className="w-8 h-8 text-primary mb-2 group-hover:scale-110 transition-transform" />
                    <Badge className={getCategoryColor(dashboard.category)}>
                      {dashboard.category}
                    </Badge>
                  </div>
                  <CardTitle className="text-lg">{dashboard.name}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {dashboard.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1 mb-3">
                    {dashboard.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                    {dashboard.tags.length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{dashboard.tags.length - 3}
                      </Badge>
                    )}
                  </div>
                  
                  {/* Notebook Links */}
                  {notebookIds.length > 0 && (
                    <div className="mb-3 p-2 bg-muted/50 rounded-md">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                        <Code2 className="w-3 h-3" />
                        <span>Source Notebooks:</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {notebookIds.map((notebookId) => (
                          <Button
                            key={notebookId}
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs hover:bg-primary/10"
                            onClick={(e) => handleNotebookClick(notebookId, e)}
                          >
                            {notebookId.replace(/_/g, " ")}
                            <ExternalLink className="w-3 h-3 ml-1" />
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <Button className="w-full" size="sm">
                    Open Dashboard
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!loading && dashboards.length === 0 && (
        <Card className="p-12 text-center">
          <BarChart3 className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
          <h3 className="text-xl font-semibold mb-2">No Dashboards Found</h3>
          <p className="text-muted-foreground">
            {selectedCategory
              ? `No dashboards available in the ${selectedCategory} category.`
              : "No dashboards are currently available."}
          </p>
          {selectedCategory && (
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => setSelectedCategory(null)}
            >
              View All Dashboards
            </Button>
          )}
        </Card>
      )}

      {/* Info Card */}
      <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
        <CardHeader>
          <CardTitle className="text-sm">About These Dashboards</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <p>
            All dashboards are powered by Databricks AI/BI and provide real-time insights into
            your payment processing operations. Click any dashboard to open it in a new tab.
          </p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Data refreshes automatically based on your DLT pipeline schedule</li>
            <li>All dashboards use Unity Catalog for governed data access</li>
            <li>Click notebook links to view the underlying data transformations</li>
            <li>Export functionality available for reporting</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
