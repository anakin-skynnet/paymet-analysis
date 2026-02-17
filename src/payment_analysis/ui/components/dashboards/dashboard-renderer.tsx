/**
 * DashboardRenderer — renders Databricks Lakeview dashboard data natively in the app.
 *
 * Fetches data from GET /api/dashboards/{id}/data (which runs dashboard SQL queries
 * against the SQL warehouse) and renders charts using recharts, matching the widget
 * types defined in the dashboard JSON (area, bar, pie, line, table, scatter).
 */
import React from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

// Colors for chart series (Tailwind-inspired)
const CHART_COLORS = [
  "hsl(var(--chart-1, 220 70% 50%))",
  "hsl(var(--chart-2, 160 60% 45%))",
  "hsl(var(--chart-3, 30 80% 55%))",
  "hsl(var(--chart-4, 280 65% 60%))",
  "hsl(var(--chart-5, 340 75% 55%))",
  "hsl(var(--chart-6, 200 70% 50%))",
  "hsl(var(--chart-7, 120 60% 40%))",
  "hsl(var(--chart-8, 45 80% 50%))",
];

// --- Types matching the backend DashboardDataOut model ---

interface DatasetResult {
  name: string;
  display_name: string;
  columns: string[];
  rows: Record<string, unknown>[];
  error: string | null;
}

interface WidgetSpec {
  dataset_name: string;
  widget_type: string;
  title: string;
  encodings: Record<string, unknown>;
}

interface DashboardData {
  dashboard_id: string;
  dashboard_name: string;
  datasets: DatasetResult[];
  widgets: WidgetSpec[];
}

// --- Encoding helpers ---

function getFieldName(enc: Record<string, unknown>, key: string): string {
  const val = enc[key];
  if (!val || typeof val !== "object") return "";
  const field = (val as Record<string, unknown>).fieldName;
  if (typeof field !== "string") return "";
  // Strip aggregate wrapper: "sum(col)" → "col"
  const m = field.match(/^\w+\((.+)\)$/);
  return m ? m[1] : field;
}

function getColorField(enc: Record<string, unknown>): string {
  // color encoding can be in 'color' key for various chart types
  const color = enc.color;
  if (color && typeof color === "object") {
    const fn = (color as Record<string, unknown>).fieldName;
    if (typeof fn === "string") return fn;
  }
  return "";
}

function getTableColumns(enc: Record<string, unknown>): string[] {
  const cols = enc.columns;
  if (!Array.isArray(cols)) return [];
  return cols
    .map((c: unknown) => {
      if (typeof c === "object" && c !== null) {
        return (c as Record<string, string>).fieldName ?? (c as Record<string, string>).name ?? "";
      }
      return "";
    })
    .filter(Boolean);
}

/** Cast row values to numbers for chart data. */
function numericRows(rows: Record<string, unknown>[], fields: string[]): Record<string, unknown>[] {
  return rows.map((row) => {
    const out: Record<string, unknown> = { ...row };
    for (const f of fields) {
      const v = row[f];
      if (v !== null && v !== undefined && v !== "") {
        const n = Number(v);
        if (!isNaN(n)) out[f] = n;
      }
    }
    return out;
  });
}

/** Truncate long axis labels. */
function shortLabel(val: unknown): string {
  const s = String(val ?? "");
  return s.length > 18 ? s.slice(0, 16) + "…" : s;
}

// --- Widget renderers ---

function WidgetAreaChart({ ds, enc }: { ds: DatasetResult; enc: Record<string, unknown> }) {
  const xField = getFieldName(enc, "x") || ds.columns[0] || "";
  const yField = getFieldName(enc, "y") || ds.columns[1] || "";
  if (!xField || !yField) return <NoFieldsMessage />;
  const data = numericRows(ds.rows, [yField]).slice(0, 200);
  if (!data.length) return <NoDataMessage />;
  // Reverse time-series so oldest is left
  const sorted = [...data].reverse();
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={sorted} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xField} tick={{ fontSize: 10 }} tickFormatter={shortLabel} />
        <YAxis tick={{ fontSize: 10 }} width={50} />
        <Tooltip />
        <defs>
          <linearGradient id={`grad-${ds.name}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS[0]} stopOpacity={0.3} />
            <stop offset="95%" stopColor={CHART_COLORS[0]} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey={yField}
          stroke={CHART_COLORS[0]}
          fill={`url(#grad-${ds.name})`}
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function WidgetBarChart({ ds, enc }: { ds: DatasetResult; enc: Record<string, unknown> }) {
  const xField = getFieldName(enc, "x") || ds.columns[0] || "";
  const yField = getFieldName(enc, "y") || ds.columns[1] || "";
  if (!xField || !yField) return <NoFieldsMessage />;

  // Detect horizontal bars: x is quantitative (the value), y is categorical (the label)
  const xScale = (enc.x && typeof enc.x === "object" ? (enc.x as Record<string, unknown>).scale : null) as Record<string, unknown> | null;
  const yScale = (enc.y && typeof enc.y === "object" ? (enc.y as Record<string, unknown>).scale : null) as Record<string, unknown> | null;
  const isHorizontal = xScale?.type === "quantitative" && yScale?.type === "categorical";

  const numField = isHorizontal ? xField : yField;
  const catField = isHorizontal ? yField : xField;
  const data = numericRows(ds.rows, [numField]).slice(0, 30);
  if (!data.length) return <NoDataMessage />;

  if (isHorizontal) {
    return (
      <ResponsiveContainer width="100%" height={Math.max(240, data.length * 32)}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10 }} />
          <YAxis dataKey={catField} type="category" tick={{ fontSize: 10 }} width={120} tickFormatter={shortLabel} />
          <Tooltip />
          <Bar dataKey={numField} radius={[0, 4, 4, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xField} tick={{ fontSize: 10 }} tickFormatter={shortLabel} />
        <YAxis tick={{ fontSize: 10 }} width={60} />
        <Tooltip />
        <Bar dataKey={yField} radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function WidgetPieChart({ ds, enc }: { ds: DatasetResult; enc: Record<string, unknown> }) {
  const angleField = getFieldName(enc, "angle") || ds.columns[1] || "";
  const colorField = getColorField(enc) || ds.columns[0] || "";
  if (!angleField) return <NoFieldsMessage />;
  const data = numericRows(ds.rows, [angleField]).slice(0, 20);
  if (!data.length) return <NoDataMessage />;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          dataKey={angleField}
          nameKey={colorField}
          cx="50%"
          cy="50%"
          outerRadius={90}
          innerRadius={40}
          paddingAngle={2}
          label={({ name, percent }) => `${shortLabel(name)} ${(percent * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

function WidgetLineChart({ ds, enc }: { ds: DatasetResult; enc: Record<string, unknown> }) {
  const xField = getFieldName(enc, "x") || ds.columns[0] || "";
  const yField = getFieldName(enc, "y") || ds.columns[1] || "";
  if (!xField || !yField) return <NoFieldsMessage />;
  const data = numericRows(ds.rows, [yField]).slice(0, 200);
  if (!data.length) return <NoDataMessage />;
  const sorted = [...data].reverse();
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={sorted} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xField} tick={{ fontSize: 10 }} tickFormatter={shortLabel} />
        <YAxis tick={{ fontSize: 10 }} width={50} />
        <Tooltip />
        <Line type="monotone" dataKey={yField} stroke={CHART_COLORS[0]} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function WidgetScatterChart({ ds, enc }: { ds: DatasetResult; enc: Record<string, unknown> }) {
  const xField = getFieldName(enc, "x") || ds.columns[0] || "";
  const yField = getFieldName(enc, "y") || ds.columns[1] || "";
  if (!xField || !yField) return <NoFieldsMessage />;
  const data = numericRows(ds.rows, [xField, yField]).slice(0, 100);
  if (!data.length) return <NoDataMessage />;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ScatterChart margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={xField} name={xField} tick={{ fontSize: 10 }} />
        <YAxis dataKey={yField} name={yField} tick={{ fontSize: 10 }} width={50} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} />
        <Scatter data={data} fill={CHART_COLORS[0]} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function WidgetTable({ ds, enc }: { ds: DatasetResult; enc: Record<string, unknown> }) {
  const tableCols = getTableColumns(enc);
  const cols = tableCols.length > 0 ? tableCols : ds.columns;
  if (!cols.length) return <NoFieldsMessage />;
  const rows = ds.rows.slice(0, 50);
  if (!rows.length) return <NoDataMessage />;

  const formatValue = (v: unknown): string => {
    if (v === null || v === undefined) return "—";
    if (typeof v === "number") {
      if (Number.isInteger(v)) return v.toLocaleString();
      return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
    const s = String(v);
    return s.length > 40 ? s.slice(0, 38) + "…" : s;
  };

  return (
    <div className="overflow-x-auto rounded-md border border-border/60 max-h-[300px] overflow-y-auto">
      <table className="w-full text-xs">
        <thead className="bg-muted/60 sticky top-0">
          <tr>
            {cols.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">
                {col.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-border/40 hover:bg-muted/30">
              {cols.map((col) => (
                <td key={col} className="px-3 py-1.5 whitespace-nowrap">
                  {formatValue(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WidgetCounter({ ds, enc }: { ds: DatasetResult; enc: Record<string, unknown> }) {
  const valueField = getFieldName(enc, "value") || ds.columns[0] || "";
  if (!valueField || !ds.rows.length) return <NoDataMessage />;
  const raw = ds.rows[0][valueField];
  const displayName =
    (enc.value && typeof enc.value === "object"
      ? (enc.value as Record<string, unknown>).displayName
      : null) as string | null;
  const num = Number(raw);
  let formatted: string;
  if (raw === null || raw === undefined) {
    formatted = "—";
  } else if (!isNaN(num)) {
    if (Number.isInteger(num) && num > 1000) {
      formatted = num.toLocaleString();
    } else if (!Number.isInteger(num)) {
      formatted = num.toLocaleString(undefined, { maximumFractionDigits: 3 });
    } else {
      formatted = String(num);
    }
  } else {
    formatted = String(raw);
  }

  return (
    <div className="flex flex-col items-center justify-center py-4 gap-1">
      <span className="text-3xl font-bold tracking-tight">{formatted}</span>
      {displayName && (
        <span className="text-xs text-muted-foreground">{displayName}</span>
      )}
    </div>
  );
}

function NoFieldsMessage() {
  return <p className="text-xs text-muted-foreground italic py-4 text-center">No fields configured</p>;
}
function NoDataMessage() {
  return <p className="text-xs text-muted-foreground italic py-4 text-center">No data available — run the ETL pipeline to populate</p>;
}

// --- Widget type router ---

function WidgetChart({ widget, dataset }: { widget: WidgetSpec; dataset: DatasetResult }) {
  if (dataset.error) {
    return (
      <div className="flex items-center gap-2 p-3 rounded-md bg-destructive/10 text-destructive text-xs">
        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
        <span className="line-clamp-2">{dataset.error}</span>
      </div>
    );
  }

  const enc = widget.encodings;
  switch (widget.widget_type) {
    case "counter":
      return <WidgetCounter ds={dataset} enc={enc} />;
    case "area":
      return <WidgetAreaChart ds={dataset} enc={enc} />;
    case "bar":
      return <WidgetBarChart ds={dataset} enc={enc} />;
    case "pie":
      return <WidgetPieChart ds={dataset} enc={enc} />;
    case "line":
      return <WidgetLineChart ds={dataset} enc={enc} />;
    case "scatter":
      return <WidgetScatterChart ds={dataset} enc={enc} />;
    case "table":
      return <WidgetTable ds={dataset} enc={enc} />;
    case "choropleth":
    case "heatmap":
      return <WidgetTable ds={dataset} enc={enc} />;
    default:
      return <WidgetTable ds={dataset} enc={enc} />;
  }
}

// --- Widget type badge ---

const WIDGET_TYPE_LABELS: Record<string, string> = {
  counter: "KPI",
  area: "Area",
  bar: "Bar",
  pie: "Pie",
  line: "Line",
  scatter: "Scatter",
  table: "Table",
  choropleth: "Map",
  heatmap: "Heatmap",
};

// --- Main component ---

interface DashboardRendererProps {
  dashboardId: string;
  dashboardName?: string;
}

export function DashboardRenderer({ dashboardId, dashboardName }: DashboardRendererProps) {
  const [data, setData] = React.useState<DashboardData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/dashboards/${dashboardId}/data`);
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(body.detail || `HTTP ${resp.status}`);
      }
      const json = await resp.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [dashboardId]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="glass-card border border-border/80">
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-1/3" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-[200px] w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="glass-card border border-destructive/30">
        <CardContent className="flex flex-col items-center justify-center py-12 gap-4">
          <AlertCircle className="w-8 h-8 text-destructive" />
          <div className="text-center space-y-1">
            <p className="font-medium">Failed to load dashboard data</p>
            <p className="text-sm text-muted-foreground max-w-md">{error}</p>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData} className="gap-2">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.widgets.length) {
    return (
      <Card className="glass-card border border-border/80">
        <CardContent className="py-12 text-center text-muted-foreground">
          No dashboard widgets available
        </CardContent>
      </Card>
    );
  }

  const datasetMap = new Map(data.datasets.map((d) => [d.name, d]));
  const name = dashboardName || data.dashboard_name;

  // Deduplicate widgets by dataset_name (same dataset can appear multiple times)
  const seen = new Set<string>();
  const uniqueWidgets = data.widgets.filter((w) => {
    const key = `${w.dataset_name}:${w.widget_type}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Separate counters from charts for different grid layouts
  const counters = uniqueWidgets.filter((w) => w.widget_type === "counter");
  const charts = uniqueWidgets.filter((w) => w.widget_type !== "counter");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{name}</h2>
        <Button variant="ghost" size="sm" onClick={fetchData} className="gap-2 text-xs">
          <RefreshCw className="w-3 h-3" /> Refresh
        </Button>
      </div>

      {/* KPI counters in a 4-column grid */}
      {counters.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {counters.map((widget, i) => {
            const dataset = datasetMap.get(widget.dataset_name);
            if (!dataset) return null;
            return (
              <Card key={`ctr-${widget.dataset_name}-${i}`} className="glass-card border border-border/80">
                <CardContent className="pt-4 pb-3 px-4">
                  <WidgetChart widget={widget} dataset={dataset} />
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Charts in a 2-column grid */}
      {charts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {charts.map((widget, i) => {
            const dataset = datasetMap.get(widget.dataset_name);
            if (!dataset) return null;
            return (
              <Card key={`${widget.dataset_name}-${i}`} className="glass-card border border-border/80 overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">{dataset.display_name}</CardTitle>
                    <Badge variant="secondary" className="text-[10px]">
                      {WIDGET_TYPE_LABELS[widget.widget_type] || widget.widget_type}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <WidgetChart widget={widget} dataset={dataset} />
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
