import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, Plus, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export type ApprovalRule = {
  id: string;
  name: string;
  rule_type: string;
  condition_expression?: string | null;
  action_summary: string;
  priority: number;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export const Route = createFileRoute("/_sidebar/rules")({
  component: () => <Rules />,
});

async function listRules(params?: { rule_type?: string; active_only?: boolean }): Promise<ApprovalRule[]> {
  const sp = new URLSearchParams();
  if (params?.rule_type) sp.set("rule_type", params.rule_type);
  if (params?.active_only) sp.set("active_only", "true");
  const url = `/api/rules${sp.toString() ? `?${sp}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

async function createRule(payload: {
  name: string;
  rule_type: string;
  action_summary: string;
  condition_expression?: string;
  priority: number;
  is_active: boolean;
}): Promise<ApprovalRule> {
  const res = await fetch("/api/rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}

async function updateRule(
  ruleId: string,
  payload: Partial<{
    name: string;
    rule_type: string;
    action_summary: string;
    condition_expression: string;
    priority: number;
    is_active: boolean;
  }>
): Promise<ApprovalRule> {
  const res = await fetch(`/api/rules/${ruleId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}

async function deleteRule(ruleId: string): Promise<void> {
  const res = await fetch(`/api/rules/${ruleId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(res.statusText);
}

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
  const [form, setForm] = useState({
    name: "",
    rule_type: "authentication",
    action_summary: "",
    condition_expression: "",
    priority: 100,
    is_active: true,
  });

  const rulesQuery = useQuery({
    queryKey: ["/api/rules", filterType],
    queryFn: () =>
      listRules(
        filterType ? { rule_type: filterType } : undefined
      ),
  });

  const createMut = useMutation({
    mutationFn: createRule,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/rules"] });
      setShowForm(false);
      setForm({ name: "", rule_type: "authentication", action_summary: "", condition_expression: "", priority: 100, is_active: true });
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ ruleId, payload }: { ruleId: string; payload: Parameters<typeof updateRule>[1] }) =>
      updateRule(ruleId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/rules"] });
      setEditingId(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/rules"] }),
  });

  const rules = rulesQuery.data ?? [];
  const isPending = rulesQuery.isLoading;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Database className="w-6 h-6" />
          Approval rules (Lakehouse)
        </h1>
        <p className="text-sm text-muted-foreground mt-2">
          Write rules into the Lakehouse (run lakehouse_bootstrap.sql in Setup step 5). ML and AI agents use them to accelerate approval rates.
        </p>
      </div>

      <Card>
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
            <p className="text-sm text-destructive">
              Failed to load rules. Complete Setup step 5 (run lakehouse_bootstrap.sql in SQL Warehouse) and ensure Databricks connection is configured in Setup & Run.
            </p>
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
              No rules yet. Run lakehouse_bootstrap.sql (Setup step 5), then add rules here. ML and AI agents will use them.
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
                        onClick={() => {
                          if (confirm("Delete this rule?")) deleteMut.mutate(r.id);
                        }}
                        disabled={deleteMut.isPending}
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
        <Card>
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
                  })
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
        <Card>
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
                    ruleId: editingId,
                    payload: {
                      name: form.name,
                      rule_type: form.rule_type,
                      action_summary: form.action_summary,
                      condition_expression: form.condition_expression || undefined,
                      priority: form.priority,
                      is_active: form.is_active,
                    },
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
    </div>
  );
}
