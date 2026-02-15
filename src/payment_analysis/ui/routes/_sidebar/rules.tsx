import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";
import { Database, Plus, Pencil, Trash2 } from "lucide-react";

import {
  type ApprovalRuleIn,
  type ApprovalRuleUpdate,
  listApprovalRulesKey,
  useListApprovalRules,
  useCreateApprovalRule,
  useUpdateApprovalRule,
  useDeleteApprovalRule,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

function RulesErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
  return (
    <div className="p-6">
      <Card className="glass-card border border-border/80 border-l-4 border-l-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Something went wrong</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : String(error)}</p>
          <Button variant="outline" size="sm" onClick={resetErrorBoundary}>Try again</Button>
        </CardContent>
      </Card>
    </div>
  );
}

export const Route = createFileRoute("/_sidebar/rules")({
  component: () => (
    <ErrorBoundary FallbackComponent={RulesErrorFallback}>
      <Rules />
    </ErrorBoundary>
  ),
});

const RULE_TYPES = [
  { value: "authentication", label: "Authentication" },
  { value: "retry", label: "Retry" },
  { value: "routing", label: "Routing" },
] as const;

function Rules() {
  const qc = useQueryClient();
  const [filterType, setFilterType] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    rule_type: "authentication",
    action_summary: "",
    condition_expression: "",
    priority: 100,
    is_active: true,
  });

  const rulesQuery = useListApprovalRules({
    params: filterType ? { rule_type: filterType } : undefined,
    query: { refetchInterval: 30_000 },
  });
  const createMut = useCreateApprovalRule({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: listApprovalRulesKey() });
        setShowForm(false);
        setForm({ name: "", rule_type: "authentication", action_summary: "", condition_expression: "", priority: 100, is_active: true });
      },
    },
  });
  const updateMut = useUpdateApprovalRule({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: listApprovalRulesKey() });
        setEditingId(null);
      },
    },
  });
  const deleteMut = useDeleteApprovalRule({
    mutation: {
      onSuccess: () => qc.invalidateQueries({ queryKey: listApprovalRulesKey() }),
    },
  });

  const rules = rulesQuery.data?.data ?? [];
  const isPending = rulesQuery.isLoading;

  return (
    <div className="space-y-6">
      {/* Hero: rules that automatically accelerate approval rates */}
      <div>
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Database className="w-6 h-6" />
          Approval rules (Lakehouse)
        </h1>
        <p className="mt-1 text-sm font-medium text-primary">
          Conditions and actions that automatically accelerate approval rates or constrain risk
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          Rules are used by the decision engine and AI agents. Stored in Lakebase (seeded by Job 1) or Lakehouse. Run Job 1 (Create Data Repositories) to create Lakebase Autoscaling and seed default rules.
        </p>
      </div>

      <Card className="glass-card border border-border/80">
        <CardHeader>
          <CardTitle>Rules</CardTitle>
          <div className="flex flex-wrap gap-2 items-center">
            <select
              className="rounded-md border bg-background px-3 py-1.5 text-sm"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
            >
              <option value="">All types</option>
              {RULE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <Button size="sm" onClick={() => setShowForm(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add rule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {rulesQuery.isError && (
            <Alert variant="destructive" className="rounded-lg">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Failed to load rules</AlertTitle>
              <AlertDescription>
                Run Job 1 (Create Data Repositories) to seed Lakebase and ensure Databricks connection is configured in Setup & Run.
              </AlertDescription>
            </Alert>
          )}
          {isPending && (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          )}
          {!isPending && rules.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No rules yet. Run Job 1 (Create Data Repositories) to seed default rules in Lakebase, or add rules here. ML and AI agents will use them.
            </p>
          )}
          {!isPending && rules.length > 0 && (
            <ul className="space-y-3">
              {rules.map((r) => (
                <li
                  key={r.id}
                  className="rounded-lg border p-4 flex flex-col gap-2"
                >
                  <div className="flex items-start justify-between gap-2 flex-wrap">
                    <div>
                      <span className="font-medium">{r.name}</span>
                      <Badge variant="secondary" className="ml-2">
                        {r.rule_type}
                      </Badge>
                      {!r.is_active && (
                        <Badge variant="outline" className="ml-2">
                          Inactive
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground ml-2">
                        priority {r.priority}
                      </span>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingId(r.id);
                          setForm({
                            name: r.name,
                            rule_type: r.rule_type,
                            action_summary: r.action_summary,
                            condition_expression: r.condition_expression ?? "",
                            priority: r.priority,
                            is_active: r.is_active,
                          });
                        }}
                      >
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeleteTarget(r.id)}
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">{r.action_summary}</p>
                  {r.condition_expression && (
                    <p className="text-xs text-muted-foreground font-mono truncate">
                      {r.condition_expression}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {showForm && (
        <Card className="glass-card border border-border/80">
          <CardHeader>
            <CardTitle>Add rule to Lakehouse</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-sm text-muted-foreground">Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Low risk skip 3DS"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Rule type</label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={form.rule_type}
                onChange={(e) => setForm((f) => ({ ...f, rule_type: e.target.value }))}
              >
                {RULE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Action summary</label>
              <Input
                value={form.action_summary}
                onChange={(e) => setForm((f) => ({ ...f, action_summary: e.target.value }))}
                placeholder="e.g. Route standard; no 3DS for low risk"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Condition (optional, JSON or text)</label>
              <Input
                value={form.condition_expression}
                onChange={(e) => setForm((f) => ({ ...f, condition_expression: e.target.value }))}
                placeholder='e.g. {"risk_tier":"LOW"}'
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Priority (lower = higher)</label>
              <Input
                type="number"
                value={form.priority}
                onChange={(e) => setForm((f) => ({ ...f, priority: Number(e.target.value) || 100 }))}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              <label htmlFor="is_active" className="text-sm">Active</label>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() =>
                  createMut.mutate({
                    name: form.name,
                    rule_type: form.rule_type,
                    action_summary: form.action_summary,
                    condition_expression: form.condition_expression || undefined,
                    priority: form.priority,
                    is_active: form.is_active,
                  } as ApprovalRuleIn)
                }
                disabled={!form.name.trim() || !form.action_summary.trim() || createMut.isPending}
              >
                Save to Lakehouse
              </Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
            {createMut.isError && (
              <p className="text-sm text-destructive">{String(createMut.error)}</p>
            )}
          </CardContent>
        </Card>
      )}

      {editingId && (
        <Card className="glass-card border border-border/80">
          <CardHeader>
            <CardTitle>Edit rule</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-sm text-muted-foreground">Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Rule type</label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={form.rule_type}
                onChange={(e) => setForm((f) => ({ ...f, rule_type: e.target.value }))}
              >
                {RULE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Action summary</label>
              <Input
                value={form.action_summary}
                onChange={(e) => setForm((f) => ({ ...f, action_summary: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Condition (optional)</label>
              <Input
                value={form.condition_expression}
                onChange={(e) => setForm((f) => ({ ...f, condition_expression: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Priority</label>
              <Input
                type="number"
                value={form.priority}
                onChange={(e) => setForm((f) => ({ ...f, priority: Number(e.target.value) || 100 }))}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="edit_is_active"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              <label htmlFor="edit_is_active" className="text-sm">Active</label>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() =>
                  updateMut.mutate({
                    params: { rule_id: editingId! },
                    data: {
                      name: form.name,
                      rule_type: form.rule_type,
                      action_summary: form.action_summary,
                      condition_expression: form.condition_expression || undefined,
                      priority: form.priority,
                      is_active: form.is_active,
                    } as ApprovalRuleUpdate,
                  })
                }
                disabled={!form.name.trim() || !form.action_summary.trim() || updateMut.isPending}
              >
                Update
              </Button>
              <Button variant="outline" onClick={() => setEditingId(null)}>
                Cancel
              </Button>
            </div>
            {updateMut.isError && (
              <p className="text-sm text-destructive">{String(updateMut.error)}</p>
            )}
          </CardContent>
        </Card>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <Card className="glass-card border border-border/80 w-full max-w-sm p-6">
            <CardTitle className="text-base mb-2">Delete rule?</CardTitle>
            <p className="text-sm text-muted-foreground mb-4">This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteMut.isPending}
                onClick={() => {
                  deleteMut.mutate(
                    { params: { rule_id: deleteTarget } },
                    { onSettled: () => setDeleteTarget(null) }
                  );
                }}
              >
                Delete
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
