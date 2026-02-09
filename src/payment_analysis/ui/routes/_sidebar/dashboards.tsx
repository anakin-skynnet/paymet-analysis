import React, { useState } from "react";
import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3, TrendingUp, Shield, DollarSign, Gauge, Users, Calendar, Lock, Award, Zap, ExternalLink, Code2, Activity, MessageSquareText, ArrowRight, Globe, LayoutGrid, ArrowLeft } from "lucide-react";
import { getWorkspaceUrl, getGenieUrl, openWorkspaceUrl } from "@/config/workspace";
import { DataSourceBadge } from "@/components/apx/data-source-badge";
import { PageHeader } from "@/components/layout";
import { friendlyReason } from "@/lib/reasoning";
import { useListDashboards, useRecentDecisions, getNotebookUrl, useGetDashboardUrl, type DashboardCategory, type DashboardInfo } from "@/lib/api";

export const Route = createFileRoute("/_sidebar/dashboards")({
  validateSearch: (s: Record<string, unknown>): { embed?: string } => ({
    embed: typeof s.embed === "string" ? s.embed : undefined,
  }),
  component: Component,
});

// Use DashboardInfo from api.ts; keep a local alias for the click handler
type Dashboard = DashboardInfo;

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
  streaming_data_quality: Activity,
  global_coverage: Globe,
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
  streaming_data_quality: ["bronze_ingest", "silver_transform", "gold_views_sql"],
  global_coverage: ["gold_views_sql"],
};

export function Component() {
  const [selectedCategory, setSelectedCategory] = useState<DashboardCategory | null>(null);
  const search = useSearch({ from: "/_sidebar/dashboards" });
  const navigate = useNavigate();
  const embedId = search.embed;

  const { data: dashboardList, isLoading: loading, isError } = useListDashboards({
    params: selectedCategory ? { category: selectedCategory } : undefined,
  });

  const { data: embedUrlData, isLoading: embedLoading, isError: embedError } = useGetDashboardUrl({
    params: { dashboard_id: embedId!, embed: true },
    query: { enabled: !!embedId },
  });

  const dashboards = dashboardList?.data.dashboards ?? [];
  const categories = dashboardList?.data.categories ?? {};
  const { data: decisionsData } = useRecentDecisions({ params: { limit: 5 } });
  const recentDecisions = decisionsData?.data ?? [];

  const handleDashboardClick = (dashboard: Dashboard) => {
    if (dashboard.url_path) {
      const databricksUrl = `${getWorkspaceUrl()}${dashboard.url_path}`;
      window.open(databricksUrl, "_blank", "noopener,noreferrer");
    }
  };

  const embedDashboard = embedId ? dashboards.find((d) => d.id === embedId) : null;
  const iframeSrc =
    embedUrlData?.data?.full_embed_url ||
    (embedUrlData?.data?.embed_url && getWorkspaceUrl()
      ? `${getWorkspaceUrl()}${embedUrlData.data.embed_url as string}`
      : null);
  const showEmbedView = !!embedId;
  const goBack = () => navigate({ to: "/dashboards", search: {} });
  const openEmbed = (id: string) => navigate({ to: "/dashboards", search: { embed: id } });

  const handleNotebookClick = async (notebookId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const { data } = await getNotebookUrl({ notebook_id: notebookId });
      openWorkspaceUrl(data?.url);
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

  // Core 6 for executive storytelling: KPI, Decline, Risk & Fraud, Routing, Live, Retry/Recommendations
  const coreDashboardIds = [
    "executive_overview",
    "decline_analysis",
    "fraud_risk_analysis",
    "routing_optimization",
    "realtime_monitoring",
    "daily_trends",
  ];
  const coreDashboards = dashboards.filter((d) => coreDashboardIds.includes(d.id));
  const otherDashboards = dashboards.filter((d) => !coreDashboardIds.includes(d.id));

  return (
    <div className="space-y-8">
      {/* Embedded dashboard view (when ?embed=id) */}
      {showEmbedView && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={goBack} className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to list
            </Button>
            {embedDashboard && (
              <span className="text-sm font-medium text-muted-foreground">
                {embedDashboard.name}
              </span>
            )}
          </div>
          <div className="rounded-lg border border-border bg-muted/30 overflow-hidden min-h-embed">
            {embedLoading ? (
              <div className="flex items-center justify-center h-[70vh]">
                <Skeleton className="h-full w-full max-w-md" />
              </div>
            ) : iframeSrc ? (
              <iframe
                title={embedDashboard?.name || "Dashboard"}
                src={String(iframeSrc)}
                className="w-full h-[78vh] border-0"
                allowFullScreen
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-[70vh] text-muted-foreground gap-2 p-4">
                <p className="text-center">
                  {embedError ? "Dashboard not found or embed not available." : "Dashboard embed is not available. Set DATABRICKS_HOST and DATABRICKS_WORKSPACE_ID, or open in a new tab."}
                </p>
                {embedId && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const u = getWorkspaceUrl() ? `${getWorkspaceUrl()}/sql/dashboards/${embedId}` : null;
                      if (u) window.open(u, "_blank", "noopener,noreferrer");
                    }}
                  >
                    Open in new tab
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* List view (when not embedding) */}
      {!showEmbedView && (
        <>
      <PageHeader
        sectionLabel="Overview"
        title="DBSQL dashboards"
        description="AI/BI dashboards for executives and operations: approval rate, decline rate, fraud rate, uplift vs. baseline; visuals by geography, merchant segment, issuer, and payment solution. Loaded from your Databricks workspace (AI/BI Dashboards)."
        badge={<DataSourceBadge />}
      />

      {/* Core executive & operations (6) */}
      {coreDashboards.length > 0 && (
        <section className="content-section space-y-3">
          <h2 className="section-label">
            Core executive & operations
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {coreDashboards.map((dashboard) => {
              const IconComponent = dashboardIcons[dashboard.id] || BarChart3;
              const notebookIds = dashboardNotebooks[dashboard.id] || [];
              return (
                <Card
                  key={dashboard.id}
                  className="card-interactive cursor-pointer hover:shadow-lg transition-all hover:border-primary/30 group"
                  onClick={() => handleDashboardClick(dashboard)}
                >
                  <CardHeader className="pb-2">
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
                    <div className="flex flex-wrap gap-1 mb-2">
                      {(dashboard.tags ?? []).slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                    {notebookIds.length > 0 && (
                      <div className="mb-2 p-2 bg-muted/50 rounded-md">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                          <Code2 className="w-3 h-3" />
                          <span>Source:</span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {notebookIds.slice(0, 2).map((notebookId) => (
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
                    <div className="flex gap-2">
                      <Button className="flex-1" size="sm" onClick={(e) => { e.stopPropagation(); openEmbed(dashboard.id); }}>
                        <LayoutGrid className="w-3.5 h-3.5 mr-1.5" />
                        View in app
                      </Button>
                      <Button className="flex-1" size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); handleDashboardClick(dashboard); }}>
                        Open in new tab <ExternalLink className="w-3 h-3 ml-1" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={selectedCategory === null ? "default" : "outline"}
          size="sm"
          onClick={() => setSelectedCategory(null)}
        >
          All ({Object.values(categories).reduce((a, b) => a + b, 0)})
        </Button>
        {Object.entries(categories).map(([category, count]) => {
          const IconComponent = categoryIcons[category];
          return (
            <Button
              key={category}
              variant={selectedCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category as DashboardCategory)}
            >
              {IconComponent && <IconComponent className="w-4 h-4 mr-2" />}
              {category.charAt(0).toUpperCase() + category.slice(1)} ({count})
            </Button>
          );
        })}
      </div>

      {/* Error State — connectivity to backend / Databricks */}
      {isError && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="py-8 text-center">
            <p className="text-destructive font-medium">Failed to load dashboards.</p>
            <p className="text-sm text-muted-foreground mt-1">Check that the backend is running and can reach Databricks for dashboard metadata and data access.</p>
          </CardContent>
        </Card>
      )}

      {/* More dashboards (when viewing All) or full grid (when category selected) */}
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
        <>
          {selectedCategory === null && otherDashboards.length > 0 && (
            <section className="content-section space-y-3">
              <h2 className="section-label">
                More dashboards
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {otherDashboards.map((dashboard) => {
                  const IconComponent = dashboardIcons[dashboard.id] || BarChart3;
                  const notebookIds = dashboardNotebooks[dashboard.id] || [];
                  return (
                    <Card
                      key={dashboard.id}
                      className="card-interactive cursor-pointer hover:shadow-lg transition-all hover:scale-[1.02] group"
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
                          {(dashboard.tags ?? []).slice(0, 3).map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {(dashboard.tags ?? []).length > 3 && (
                            <Badge variant="secondary" className="text-xs">
                              +{(dashboard.tags ?? []).length - 3}
                            </Badge>
                          )}
                        </div>
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
                        <div className="flex gap-2">
                          <Button className="flex-1" size="sm" onClick={(e) => { e.stopPropagation(); openEmbed(dashboard.id); }}>
                            <LayoutGrid className="w-3.5 h-3.5 mr-1.5" />
                            View in app
                          </Button>
                          <Button className="flex-1" size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); handleDashboardClick(dashboard); }}>
                            Open in new tab <ExternalLink className="w-3 h-3 ml-1" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </section>
          )}
          {selectedCategory !== null && (
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
                        {(dashboard.tags ?? []).slice(0, 3).map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                        {(dashboard.tags ?? []).length > 3 && (
                          <Badge variant="secondary" className="text-xs">
                            +{(dashboard.tags ?? []).length - 3}
                          </Badge>
                        )}
                      </div>
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
                      <div className="flex gap-2">
                        <Button className="flex-1" size="sm" onClick={(e) => { e.stopPropagation(); openEmbed(dashboard.id); }}>
                          <LayoutGrid className="w-3.5 h-3.5 mr-1.5" />
                          View in app
                        </Button>
                        <Button className="flex-1" size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); handleDashboardClick(dashboard); }}>
                          Open in new tab <ExternalLink className="w-3 h-3 ml-1" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </>
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

      {/* ML & decision reasoning — click opens Genie in Databricks */}
      <Card
        className="cursor-pointer hover:shadow-md transition-shadow"
        onClick={() => { const u = getGenieUrl(); if (u) window.open(u, "_blank", "noopener,noreferrer"); }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter") { const u = getGenieUrl(); if (u) window.open(u, "_blank", "noopener,noreferrer"); } }}
      >
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareText className="w-4 h-4" />
            ML & decision reasoning
          </CardTitle>
          <CardDescription>
            Latest policy and model reasoning from authentication, retry, and routing decisions
          </CardDescription>
        </CardHeader>
        <CardContent onClick={(e) => e.stopPropagation()}>
          {recentDecisions.length === 0 ? (
            <p className="text-sm text-muted-foreground mb-4">
              No recent decisions. Use the Decisioning playground to generate decisions and reasoning.
            </p>
          ) : (
            <ul className="space-y-3 mb-4">
              {recentDecisions.map((log) => {
                const reason = friendlyReason(log.response?.reason as string);
                const variant = log.response?.variant as string | undefined;
                return (
                  <li key={log.audit_id ?? log.id ?? Math.random()} className="text-sm border-b border-border/50 pb-3 last:border-0 last:pb-0">
                    <div className="flex flex-wrap items-center gap-2 mb-0.5">
                      <Badge variant="secondary" className="font-mono text-xs">
                        {log.decision_type}
                      </Badge>
                      {variant != null && (
                        <span className="text-xs text-muted-foreground">A/B: {variant}</span>
                      )}
                    </div>
                    <p className="text-muted-foreground line-clamp-2">{reason}</p>
                  </li>
                );
              })}
            </ul>
          )}
          <Button variant="outline" size="sm" asChild>
            <Link to="/decisioning" onClick={(e) => e.stopPropagation()}>
              Open Decisioning <ArrowRight className="w-3 h-3 ml-1" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
        <CardHeader>
          <CardTitle className="text-sm">About These Dashboards</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <p>
            All dashboards are powered by Databricks AI/BI and provide real-time insights into
            your payment processing operations. View in app to embed, or open in a new tab.
          </p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Data refreshes automatically based on your Lakeflow schedule</li>
            <li>All dashboards use Unity Catalog for governed data access</li>
            <li>Click notebook links to view the underlying data transformations</li>
            <li>Export functionality available for reporting</li>
          </ul>
        </CardContent>
      </Card>
        </>
      )}
    </div>
  );
}
