import React, { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Code2, Bot, Brain, Zap, Database, BarChart3, ExternalLink, PlayCircle } from "lucide-react";
import { useListNotebooks, getNotebookUrl, type NotebookCategory } from "@/lib/api";

export const Route = createFileRoute("/_sidebar/notebooks")({
  component: Component,
});

// Types come from auto-generated api.ts (NotebookInfo, NotebookList)

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  agents: Bot,
  ml_training: Brain,
  streaming: Zap,
  transformation: Database,
  analytics: BarChart3,
};

const categoryColors: Record<string, string> = {
  intelligence: "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800",
  ml_training: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800",
  streaming: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800",
  transformation: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800",
  analytics: "bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-800",
};

export function Component() {
  const [selectedCategory, setSelectedCategory] = useState<NotebookCategory | null>(null);

  const { data: notebookList, isLoading: loading, isError } = useListNotebooks({
    params: selectedCategory ? { category: selectedCategory } : undefined,
  });

  const notebooks = notebookList?.data.notebooks ?? [];
  const categories = notebookList?.data.by_category ?? {};

  const handleNotebookClick = async (notebookId: string) => {
    try {
      const { data } = await getNotebookUrl({ notebook_id: notebookId });
      window.open(data.url, "_blank");
    } catch (error) {
      console.error("Failed to open notebook:", error);
    }
  };

  const getCategoryLabel = (category: string): string => {
    return category.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Databricks Notebooks</h1>
        <p className="text-muted-foreground mt-2">
          Browse and access all notebooks powering the payment analysis platform
        </p>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={selectedCategory === null ? "default" : "outline"}
          size="sm"
          onClick={() => setSelectedCategory(null)}
        >
          <Code2 className="w-4 h-4 mr-2" />
          All Notebooks ({Object.values(categories).reduce((a, b) => a + b, 0)})
        </Button>
        {Object.entries(categories).map(([category, count]) => {
          const IconComponent = categoryIcons[category];
          return (
            <Button
              key={category}
              variant={selectedCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category as NotebookCategory)}
            >
              {IconComponent && <IconComponent className="w-4 h-4 mr-2" />}
              {getCategoryLabel(category)} ({count})
            </Button>
          );
        })}
      </div>

      {/* Error State */}
      {isError && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="py-8 text-center">
            <p className="text-destructive font-medium">Failed to load notebooks. Check that the backend is running.</p>
          </CardContent>
        </Card>
      )}

      {/* Notebooks List */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {notebooks.map((notebook) => {
            const IconComponent = categoryIcons[notebook.category] || Code2;
            const categoryColor = categoryColors[notebook.category] || categoryColors.analytics;
            
            return (
              <Card
                key={notebook.id}
                className="hover:shadow-lg transition-all group border-l-4"
                style={{ borderLeftColor: categoryColor.split(" ")[0].replace("bg-", "").replace("/10", "") }}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      <div className={`p-2 rounded-lg ${categoryColor}`}>
                        <IconComponent className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <CardTitle className="text-xl">{notebook.name}</CardTitle>
                          <Badge className={categoryColor}>
                            {getCategoryLabel(notebook.category)}
                          </Badge>
                        </div>
                        <CardDescription className="text-sm">
                          {notebook.description}
                        </CardDescription>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap items-center gap-3">
                    {/* Tags */}
                    <div className="flex flex-wrap gap-1 flex-1">
                      {(notebook.tags ?? []).map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                    
                    {/* Job Info */}
                    {notebook.job_name && (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <PlayCircle className="w-3 h-3" />
                        <span className="truncate max-w-xs" title={notebook.job_name}>
                          Scheduled: {notebook.job_name}
                        </span>
                      </div>
                    )}
                    
                    {/* Action Button */}
                    <Button
                      size="sm"
                      onClick={() => handleNotebookClick(notebook.id)}
                      className="ml-auto"
                    >
                      Open Notebook
                      <ExternalLink className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!loading && notebooks.length === 0 && (
        <Card className="p-12 text-center">
          <Code2 className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
          <h3 className="text-xl font-semibold mb-2">No Notebooks Found</h3>
          <p className="text-muted-foreground">
            {selectedCategory
              ? `No notebooks available in the ${getCategoryLabel(selectedCategory)} category.`
              : "No notebooks are currently available."}
          </p>
          {selectedCategory && (
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => setSelectedCategory(null)}
            >
              View All Notebooks
            </Button>
          )}
        </Card>
      )}

      {/* Category Descriptions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="border-purple-200 dark:border-purple-800">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              <CardTitle className="text-sm">AI Agents</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Multi-agent system for intelligent payment optimization, routing, and analysis
          </CardContent>
        </Card>

        <Card className="border-blue-200 dark:border-blue-800">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <CardTitle className="text-sm">ML Training</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Machine learning model training for fraud detection, approval prediction, and routing optimization
          </CardContent>
        </Card>

        <Card className="border-yellow-200 dark:border-yellow-800">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
              <CardTitle className="text-sm">Streaming</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Real-time payment processing with Lakeflow Declarative Pipelines and structured streaming
          </CardContent>
        </Card>

        <Card className="border-green-200 dark:border-green-800">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-green-600 dark:text-green-400" />
              <CardTitle className="text-sm">Transformation</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Data transformations from bronze to gold layer with quality checks and enrichment
          </CardContent>
        </Card>

        <Card className="border-orange-200 dark:border-orange-800">
          <CardHeader>
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-orange-600 dark:text-orange-400" />
              <CardTitle className="text-sm">Analytics</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Aggregated views and metrics powering dashboards and business intelligence
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
