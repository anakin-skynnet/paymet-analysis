import React, { useState } from "react";
import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { BarChart3, Gauge, Award, Zap, ExternalLink, Code2, Activity, MessageSquareText, ArrowRight, LayoutGrid, ArrowLeft, AlertCircle } from "lucide-react";
import { getWorkspaceUrl, getGenieUrl, openInDatabricks, getLakeviewDashboardUrl } from "@/config/workspace";
import { DataSourceBadge } from "@/components/apx/data-source-badge";
import { PageHeader } from "@/components/layout";
import { DashboardTable } from "@/components/dashboards";
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
  data_quality_unified: Activity,
  ml_optimization_unified: Zap,
  executive_trends_unified: BarChart3,
};

// Map dashboards to their underlying notebooks
const dashboardNotebooks: Record<string, string[]> = {
  data_quality_unified: ["bronze_ingest", "silver_transform", "gold_views_sql", "realtime_pipeline"],
  ml_optimization_unified: ["train_models", "gold_views_sql", "agent_framework", "silver_transform"],
  executive_trends_unified: ["gold_views_sql", "silver_transform"],
};

export function Component() {
  const [selectedCategory, setSelectedCategory] = useState<DashboardCategory | null>(null);
  const search = useSearch({ from: "/_sidebar/dashboards" });
  const navigate = useNavigate();
  const embedId = search.embed;

  const { data: dashboardList, isLoading: loading, isError } = useListDashboards({
    params: selectedCategory ? { category: selectedCategory } : undefined,
    query: { refetchInterval: 30_000 },
  });

  const { data: embedUrlData, isLoading: embedLoading, isError: embedError } = useGetDashboardUrl({
    params: { dashboard_id: embedId ?? "", embed: true },
    query: { enabled: !!embedId },
  });

  const dashboards = dashboardList?.data.dashboards ?? [];
  const categories = dashboardList?.data.categories ?? {};
  const { data: decisionsData } = useRecentDecisions({
    params: { limit: 5 },
    query: { refetchInterval: 15_000 },
  });
  const recentDecisions = decisionsData?.data ?? [];

  const handleDashboardClick = (dashboard: Dashboard) => {
    if (dashboard.url_path) {
      const base = getWorkspaceUrl();
      if (base) {
        window.open(`${base}${dashboard.url_path}`, "_blank", "noopener,noreferrer");
      }
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
      openInDatabricks(data?.url);
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

  // Three unified dashboards: Data & Quality, ML & Optimization, Executive & Trends
  const coreDashboardIds = [
    "executive_trends_unified",
    "ml_optimization_unified",
    "data_quality_unified",
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
              <>
                <iframe
                  title={embedDashboard?.name || "Dashboard"}
                  src={String(iframeSrc)}
                  className="w-full h-[78vh] border-0"
                  allowFullScreen
                />
                <p className="text-xs text-muted-foreground px-2 py-1.5 border-t border-border bg-muted/20">
                  If the dashboard shows &quot;refused to connect&quot;, the workspace must allow embedding:{" "}
                  <span className="font-medium">Settings → Security → Embed dashboards</span> → set to <strong>Allow</strong> or add <code className="text-[11px]">*.databricksapps.com</code> to approved domains.
                </p>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-[70vh] text-muted-foreground gap-3 p-4 max-w-md">
                <p className="text-center text-sm">
                  {embedError
                    ? "Dashboard not found or embed not available."
                    : "Dashboard embed needs a workspace URL. Open this app from Databricks (Compute → Apps) so your workspace is detected, or set DATABRICKS_HOST to your workspace URL."}
                </p>
                {embedId && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const u = getLakeviewDashboardUrl(embedId!);
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
        sectionLabel="Analytics"
        title="Performance Dashboards"
        description="Approval rate, declines, fraud, routing, and real-time monitoring. Open or embed Databricks dashboards."
        badge={<DataSourceBadge />}
      />

      {/* Core approval & operations (6) */}
      {coreDashboards.length > 0 && (
        <section className="content-section space-y-3">
          <h2 className="section-label">
            Approval & operations
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {coreDashboards.map((dashboard) => {
              const IconComponent = dashboardIcons[dashboard.id] || BarChart3;
              const notebookIds = dashboardNotebooks[dashboard.id] || [];
              return (
                <Card
                  key={dashboard.id}
                  className="glass-card card-interactive cursor-pointer border border-border/80 hover:shadow-lg transition-all hover:border-primary/30 group"
                  onClick={() => handleDashboardClick(dashboard)}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:scale-110 transition-transform">
                        <IconComponent className="w-5 h-5" />
                      </div>
                      <Badge className={getCategoryColor(dashboard.category)}>
                        {dashboard.category}
                      </Badge>
                    </div>
                    <CardTitle className="text-lg mt-2">{dashboard.name}</CardTitle>
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
                    </div>
                    {notebookIds.length > 0 && (
                      <div className="mb-3 p-2 bg-muted/40 rounded-lg border border-border/60">
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

      {/* Error state: backend unavailable */}
      {isError && (
        <Alert variant="destructive" className="border-destructive/50">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load dashboards</AlertTitle>
          <AlertDescription>
            Could not fetch dashboard metadata from the backend. Verify the backend is running and can reach Databricks.
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="cards" className="space-y-4">
        <TabsList className="bg-muted/50">
          <TabsTrigger value="cards">Cards</TabsTrigger>
          <TabsTrigger value="table">Table</TabsTrigger>
        </TabsList>
        <TabsContent value="table" className="space-y-4">
          <DashboardTable
            dashboards={dashboards}
            isLoading={loading}
            onViewInApp={openEmbed}
            onOpenInTab={(d) => d.url_path && handleDashboardClick(d)}
          />
        </TabsContent>
        <TabsContent value="cards" className="space-y-6">
      {/* More dashboards (when viewing All) or full grid (when category selected) */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="glass-card border border-border/80">
              <CardHeader>
                <div className="flex items-start justify-between mb-2">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
                <Skeleton className="h-5 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </CardHeader>
              <CardContent>
                <div className="flex gap-1 mb-3">
                  <Skeleton className="h-5 w-14 rounded-full" />
                  <Skeleton className="h-5 w-14 rounded-full" />
                </div>
                <div className="flex gap-2">
                  <Skeleton className="h-8 flex-1 rounded-md" />
                  <Skeleton className="h-8 flex-1 rounded-md" />
                </div>
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
        className="glass-card border border-border/80 cursor-pointer card-interactive hover:shadow-md transition-all"
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
              {recentDecisions.map((log, index) => {
                const reason = friendlyReason(log.response?.reason as string);
                const variant = log.response?.variant as string | undefined;
                return (
                  <li key={log.audit_id ?? log.id ?? `decision-${index}`} className="text-sm border-b border-border/50 pb-3 last:border-0 last:pb-0">
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
      <Card className="glass-card border border-blue-200/60 dark:border-blue-800/60">
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
        </TabsContent>
        </Tabs>
        </>
      )}
    </div>
  );
}
