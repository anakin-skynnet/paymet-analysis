import React, { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkles, Bot, Brain, Zap, MessageSquare, ExternalLink, TrendingUp, Shield, RotateCcw, BarChart3, Lightbulb } from "lucide-react";

export const Route = createFileRoute("/_sidebar/ai-agents")({
  component: () => <AIAgents />,
});

interface Agent {
  id: string;
  name: string;
  description: string;
  agent_type: string;
  capabilities: string[];
  use_case: string;
  databricks_resource: string;
  workspace_url: string | null;
  tags: string[];
  example_queries: string[];
}

interface AgentList {
  agents: Agent[];
  total: number;
  by_type: Record<string, number>;
}

const agentTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  genie: Sparkles,
  model_serving: Brain,
  custom_llm: Bot,
  ai_gateway: Zap,
};

const agentTypeColors: Record<string, string> = {
  genie: "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800",
  model_serving: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800",
  custom_llm: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800",
  ai_gateway: "bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-800",
};

const agentIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  approval_optimizer_genie: TrendingUp,
  decline_insights_genie: BarChart3,
  approval_propensity_predictor: Brain,
  smart_routing_advisor: Zap,
  smart_retry_optimizer: RotateCcw,
  payment_intelligence_assistant: MessageSquare,
  risk_assessment_advisor: Shield,
  performance_recommender: Lightbulb,
};

function AIAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [types, setTypes] = useState<Record<string, number>>({});

  useEffect(() => {
    fetchAgents();
  }, [selectedType]);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const typeParam = selectedType ? `?agent_type=${selectedType}` : "";
      const response = await fetch(`/api/agents/agents${typeParam}`);
      const data: AgentList = await response.json();
      setAgents(data.agents);
      setTypes(data.by_type);
    } catch (error) {
      console.error("Failed to fetch agents:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAgentClick = async (agentId: string) => {
    try {
      const response = await fetch(`/api/agents/agents/${agentId}/url`);
      const data = await response.json();
      if (data.url) {
        window.open(data.url, "_blank");
      }
    } catch (error) {
      console.error("Failed to open agent:", error);
    }
  };

  const openAgentsFolder = async () => {
    try {
      const response = await fetch(`/api/notebooks/notebooks/folders/agents/url`);
      const data = await response.json();
      if (data.url) window.open(data.url, "_blank");
    } catch (error) {
      console.error("Failed to open agents folder:", error);
    }
  };

  const getTypeLabel = (type: string): string => {
    return type.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex gap-3">
            <Bot className="w-8 h-8 text-primary flex-shrink-0" />
            <div>
              <h1 className="text-3xl font-bold">Databricks AI Agents</h1>
              <p className="text-muted-foreground mt-1">
                AI-powered agents to accelerate payment approval rates using Genie, Model Serving, and LLM intelligence
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={openAgentsFolder}
          >
            <ExternalLink className="w-4 h-4 mr-2" />
            Open agents folder in Workspace
          </Button>
        </div>
      </div>

      {/* Info Card */}
      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <Sparkles className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
            <div className="space-y-2">
              <p className="text-sm font-medium">
                Leverage Databricks AI capabilities to optimize payment approval rates
              </p>
              <ul className="text-xs text-muted-foreground space-y-1 ml-4 list-disc">
                <li><strong>Genie:</strong> Ask questions in natural language to explore payment data</li>
                <li><strong>Model Serving:</strong> Real-time ML predictions for routing and retry optimization</li>
                <li><strong>AI Gateway:</strong> LLM-powered insights and recommendations (Llama 3.1 70B)</li>
                <li><strong>Custom Agents:</strong> Domain-specific payment intelligence</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Type Filter */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={selectedType === null ? "default" : "outline"}
          size="sm"
          onClick={() => setSelectedType(null)}
        >
          <Bot className="w-4 h-4 mr-2" />
          All Agents ({Object.values(types).reduce((a, b) => a + b, 0)})
        </Button>
        {Object.entries(types).map(([type, count]) => {
          const IconComponent = agentTypeIcons[type];
          return (
            <Button
              key={type}
              variant={selectedType === type ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedType(type)}
            >
              {IconComponent && <IconComponent className="w-4 h-4 mr-2" />}
              {getTypeLabel(type)} ({count})
            </Button>
          );
        })}
      </div>

      {/* Agents Grid */}
      {loading ? (
        <div className="grid gap-6 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-full" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {agents.map((agent) => {
            const IconComponent = agentIcons[agent.id] || Bot;
            const TypeIcon = agentTypeIcons[agent.agent_type];
            const typeColor = agentTypeColors[agent.agent_type];

            return (
              <Card
                key={agent.id}
                className="hover:shadow-lg transition-shadow cursor-pointer group"
                onClick={() => handleAgentClick(agent.id)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 flex-1">
                      <IconComponent className="w-5 h-5 text-primary flex-shrink-0" />
                      <CardTitle className="text-lg">{agent.name}</CardTitle>
                    </div>
                    <Badge variant="outline" className={`${typeColor} flex-shrink-0`}>
                      {TypeIcon && <TypeIcon className="w-3 h-3 mr-1" />}
                      {getTypeLabel(agent.agent_type)}
                    </Badge>
                  </div>
                  <CardDescription className="text-sm leading-relaxed mt-2">
                    {agent.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Use Case */}
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">💡 Use Case</p>
                    <p className="text-sm">{agent.use_case}</p>
                  </div>

                  {/* Databricks Resource */}
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">🔗 Databricks Resource</p>
                    <code className="text-xs bg-muted px-2 py-1 rounded block font-mono break-all">
                      {agent.databricks_resource}
                    </code>
                  </div>

                  {/* Capabilities */}
                  {agent.capabilities && agent.capabilities.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">🎯 Capabilities</p>
                      <div className="flex flex-wrap gap-1">
                        {agent.capabilities.slice(0, 3).map((cap, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            {cap.replace(/_/g, " ")}
                          </Badge>
                        ))}
                        {agent.capabilities.length > 3 && (
                          <Badge variant="secondary" className="text-xs">
                            +{agent.capabilities.length - 3} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Example Queries */}
                  {agent.example_queries && agent.example_queries.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">💬 Example Queries</p>
                      <div className="space-y-1">
                        {agent.example_queries.slice(0, 2).map((query, idx) => (
                          <p key={idx} className="text-xs italic text-muted-foreground pl-3 border-l-2 border-muted">
                            "{query}"
                          </p>
                        ))}
                        {agent.example_queries.length > 2 && (
                          <p className="text-xs text-muted-foreground pl-3">
                            +{agent.example_queries.length - 2} more examples
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Action Button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full group-hover:bg-primary/10"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAgentClick(agent.id);
                    }}
                  >
                    Open in Databricks
                    <ExternalLink className="w-4 h-4 ml-2" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!loading && agents.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Bot className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No agents found for this filter</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
