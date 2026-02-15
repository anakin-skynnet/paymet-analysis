import { useMemo, lazy, Suspense, Component, type ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetGeography } from "@/lib/api";
import type { GeographyOut } from "@/lib/api";
import { Globe } from "lucide-react";

/* --- Error boundary for lazy-loaded world map --- */
class MapErrorBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { hasError: boolean }> {
  constructor(props: { fallback: ReactNode; children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() { return { hasError: true }; }
  render() { return this.state.hasError ? this.props.fallback : this.props.children; }
}

/** Refresh geography from backend every 15s for real-time map. */
const REFRESH_GEOGRAPHY_MS = 15_000;

/** Country code to display name (ISO 3166-1 alpha-2). */
const COUNTRY_NAMES: Record<string, string> = {
  BR: "Brazil",
  US: "United States",
  MX: "Mexico",
  AR: "Argentina",
  CO: "Colombia",
  CL: "Chile",
  GB: "United Kingdom",
  DE: "Germany",
  FR: "France",
  ES: "Spain",
  IT: "Italy",
  JP: "Japan",
  IN: "India",
  CA: "Canada",
  AU: "Australia",
  NL: "Netherlands",
  PE: "Peru",
  EC: "Ecuador",
};

function getCountryName(code: string): string {
  return COUNTRY_NAMES[code.toUpperCase()] ?? code;
}

/** Interpolate color from red (low approval) to green (high approval). */
function approvalRateToColor(rate: number): string {
  if (rate >= 85) return "var(--vibrant-green)";
  if (rate >= 75) return "oklch(0.55 0.15 145)";
  if (rate >= 65) return "oklch(0.7 0.12 85)";
  if (rate >= 55) return "oklch(0.75 0.15 55)";
  return "oklch(0.65 0.2 27)";
}

const WorldMapLazy = lazy(() =>
  import("react-svg-worldmap").then((m) => ({ default: m.default })),
);

/** Fallback when the SVG map fails to load — shows a simple list. */
function CountryListFallback({ rows }: { rows: GeographyOut[] }) {
  if (!rows.length) return null;
  return (
    <div className="w-full space-y-2">
      <p className="text-xs text-muted-foreground mb-2">Map unavailable — showing data as list</p>
      {rows
        .sort((a, b) => (b.transaction_count ?? 0) - (a.transaction_count ?? 0))
        .map((r) => (
          <div key={r.country} className="flex items-center gap-3 rounded-md bg-muted/30 px-3 py-1.5">
            <span className="text-sm font-medium w-20">{getCountryName(r.country)}</span>
            <Progress value={r.approval_rate_pct ?? 0} className="flex-1 h-2" />
            <Badge variant={
              (r.approval_rate_pct ?? 0) >= 85 ? "default" : (r.approval_rate_pct ?? 0) >= 75 ? "secondary" : "destructive"
            } className="text-[10px] tabular-nums min-w-[52px] justify-center">
              {r.approval_rate_pct?.toFixed(1) ?? "—"}%
            </Badge>
            <span className="text-xs text-muted-foreground tabular-nums w-20 text-right">
              {r.transaction_count?.toLocaleString()} tx
            </span>
          </div>
        ))}
    </div>
  );
}

export function GeographyWorldMap() {
  const { data, isLoading, isError } = useGetGeography({
    params: { limit: 100 },
    query: { refetchInterval: REFRESH_GEOGRAPHY_MS },
  });

  const mapData = useMemo(() => {
    const rows: GeographyOut[] = data?.data ?? [];
    return rows
      .filter((r) => r.country && r.country.length === 2)
      .map((r) => ({
        country: r.country.toLowerCase(),
        value: r.approval_rate_pct ?? r.transaction_count,
      }));
  }, [data?.data]);

  const byCode = useMemo(() => {
    const map = new Map<string, GeographyOut>();
    for (const r of data?.data ?? []) {
      if (r.country) map.set(r.country.toUpperCase(), r);
    }
    return map;
  }, [data?.data]);

  if (isError) {
    return (
      <Card className="overflow-hidden border border-border/80">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="h-4 w-4 text-muted-foreground" />
            Performance by country
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Could not load geography data. Check backend and Databricks connection.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading && mapData.length === 0) {
    return (
      <Card className="overflow-hidden border border-border/80">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="h-4 w-4 text-muted-foreground" />
            Performance by country
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[280px] w-full max-w-[640px] rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  if (mapData.length === 0) {
    return (
      <Card className="overflow-hidden border border-border/80">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="h-4 w-4 text-muted-foreground" />
            Performance by country
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No geography data yet. Run gold views and stream data to see approval rates by country.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden border border-border/80 bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Globe className="h-4 w-4 text-primary" />
          Performance by country
        </CardTitle>
        <p className="text-xs text-muted-foreground font-normal mt-0.5">
          Approval rate by issuer country — focus on low-rate regions to accelerate approvals
        </p>
      </CardHeader>
      <CardContent className="flex flex-col items-center">
        <MapErrorBoundary fallback={<CountryListFallback rows={data?.data ?? []} />}>
          <div className="w-full max-w-[640px] [&_svg]:max-w-full [&_svg]:h-auto">
            <Suspense
              fallback={
                <div className="flex h-[280px] items-center justify-center rounded-lg bg-muted/30">
                  <Skeleton className="h-full w-full max-w-[640px] rounded-lg" />
                </div>
              }
            >
              <WorldMapLazy
                data={mapData}
                color="var(--primary)"
                backgroundColor="transparent"
                borderColor="var(--border)"
                title=""
                valueSuffix="%"
                size="responsive"
                richInteraction
                tooltipTextFunction={({ countryCode, countryValue }) => {
                  const code = String(countryCode).toUpperCase();
                  const row = byCode.get(code);
                  const name = getCountryName(code);
                  const rate = row?.approval_rate_pct ?? (typeof countryValue === "number" ? countryValue : null);
                  const tx = row?.transaction_count;
                  const parts = [name];
                  if (rate != null) parts.push(`Approval: ${rate.toFixed(1)}%`);
                  if (tx != null) parts.push(`${tx.toLocaleString()} tx`);
                  return parts.join(" · ");
                }}
                styleFunction={({ countryValue }) => {
                  const rate = typeof countryValue === "number" ? countryValue : 0;
                  return { fill: approvalRateToColor(rate) };
                }}
              />
            </Suspense>
          </div>
        </MapErrorBoundary>
        {/* Country data list — always visible below the map */}
        <div className="mt-4 w-full space-y-2">
          {(data?.data ?? [])
            .sort((a, b) => (b.transaction_count ?? 0) - (a.transaction_count ?? 0))
            .slice(0, 8)
            .map((r) => (
              <div key={r.country} className="flex items-center gap-3 rounded-md bg-muted/30 px-3 py-1.5">
                <span className="text-sm font-medium w-20">{getCountryName(r.country)}</span>
                <Progress value={r.approval_rate_pct ?? 0} className="flex-1 h-2" />
                <Badge variant={
                  (r.approval_rate_pct ?? 0) >= 85 ? "default" : (r.approval_rate_pct ?? 0) >= 75 ? "secondary" : "destructive"
                } className="text-[10px] tabular-nums min-w-[52px] justify-center">
                  {r.approval_rate_pct?.toFixed(1) ?? "—"}%
                </Badge>
                <span className="text-xs text-muted-foreground tabular-nums w-20 text-right">
                  {r.transaction_count?.toLocaleString()} tx
                </span>
              </div>
            ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-4 rounded-sm bg-getnet-red" aria-hidden />
            Low (&lt;55%)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-4 rounded-sm bg-amber-500" aria-hidden />
            Medium
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-4 rounded-sm bg-vibrant-green" aria-hidden />
            High (85%+)
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
