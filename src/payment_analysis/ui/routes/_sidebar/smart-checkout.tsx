import { createFileRoute } from "@tanstack/react-router";
import { ErrorBoundary } from "react-error-boundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGetSmartCheckoutServicePaths,
  useGetThreeDsFunnel,
  useGetSmartCheckoutPathPerformance,
  useGetKpis,
} from "@/lib/api";
import { getLakeviewDashboardUrl, openInDatabricks } from "@/config/workspace";
import { useEntity } from "@/contexts/entity-context";
import { ExternalLink, Shield, CreditCard, Fingerprint, Key, Database } from "lucide-react";

export const Route = createFileRoute("/_sidebar/smart-checkout")({
  component: () => (
    <ErrorBoundary FallbackComponent={SmartCheckoutErrorFallback}>
      <SmartCheckout />
    </ErrorBoundary>
  ),
});

const PAYMENT_SERVICES = [
  { id: "antifraud", name: "Antifraud", note: "~40–50% of declined transactions (Payment Link BR)", icon: Shield },
  { id: "3ds", name: "3DS", note: "Mandatory for debit (BR). ~80% friction; 60% authenticated; 80% approved post-auth", icon: CreditCard },
  { id: "idpay", name: "IdPay (Único)", note: "Biometric; provider reports 60–80% recognition success. Not yet live", icon: Fingerprint },
  { id: "network_token", name: "Network Token", note: "Mandatory for VISA. Available for VISA & Mastercard at Getnet", icon: Database },
  { id: "passkey", name: "Passkey", note: "Under development at Getnet. No production data yet", icon: Key },
  { id: "vault", name: "Vault", note: "Tokenization and secure storage", icon: Database },
  { id: "data_only", name: "Data Only", note: "Approval uplift data not yet available", icon: Database },
] as const;

function SmartCheckoutErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
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

/** Refresh analytics from backend/Databricks every 15s for real-time data. */
const REFRESH_ANALYTICS_MS = 15_000;

function SmartCheckout() {
  const { entity } = useEntity();
  const kpisQ = useGetKpis({ query: { refetchInterval: REFRESH_ANALYTICS_MS } });
  const servicePathsQ = useGetSmartCheckoutServicePaths({
    params: { entity, limit: 25 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const funnelQ = useGetThreeDsFunnel({
    params: { entity, days: 30 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });
  const pathPerfQ = useGetSmartCheckoutPathPerformance({
    params: { entity, limit: 20 },
    query: { refetchInterval: REFRESH_ANALYTICS_MS },
  });

  const kpis = kpisQ.data?.data;
  const approvalPct = kpis?.approval_rate != null
    ? `${(kpis.approval_rate * 100).toFixed(1)}%`
    : null;
  const totalTx = kpis?.total != null
    ? kpis.total >= 1_000_000
      ? `${(kpis.total / 1_000_000).toFixed(1)}M`
      : kpis.total >= 1_000
        ? `${(kpis.total / 1_000).toFixed(0)}K`
        : `${kpis.total}`
    : null;

  const servicePaths = servicePathsQ.data?.data ?? [];
  const funnel = funnelQ.data?.data ?? [];
  const latest = funnel[0];
  const pathPerf = pathPerfQ.data?.data ?? [];

  return (
    <div className="space-y-8">
      {/* Hero: initiative name + context */}
      <div>
        <h1 className="text-2xl font-bold font-heading tracking-tight text-foreground">
          Smart Checkout
        </h1>
        <p className="mt-1 text-sm font-medium text-muted-foreground">
          Payment Link · Brazil · Increase approval rates with the right service mix
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <div className="rounded-lg border border-border/80 bg-muted/30 px-4 py-2 text-sm">
            <span className="text-muted-foreground">Scope: </span>
            {totalTx ? (
              <span className="font-medium">{totalTx} transactions (Payment Link)</span>
            ) : (
              <Skeleton className="inline-block h-4 w-24" />
            )}
          </div>
          <div className="rounded-lg border border-border/80 bg-muted/30 px-4 py-2 text-sm">
            <span className="text-muted-foreground">Overall approval: </span>
            {approvalPct ? (
              <>
                <span className="font-semibold text-foreground">{approvalPct}</span>
                <span className="text-muted-foreground"> (varies by seller profile)</span>
              </>
            ) : (
              <Skeleton className="inline-block h-4 w-16" />
            )}
          </div>
        </div>
      </div>

      {/* Payment services at a glance */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Payment services at a glance</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Complementary services that impact security, experience, and approval rates. Getnet and third-party.
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {PAYMENT_SERVICES.map((s) => {
            const Icon = s.icon;
            return (
              <Card key={s.id} className="glass-card border border-border/80">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Icon className="h-4 w-4 text-primary" />
                    {s.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground leading-relaxed">{s.note}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* 3DS funnel – Payment Link Brazil */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">3DS funnel (Payment Link – Brazil)</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Controlled test 2025: friction, authentication success, and issuer approval post-auth.
        </p>
        {funnel.length === 0 && (
          <p className="text-sm text-muted-foreground mb-4">
            No 3DS funnel data yet. Run the simulator and ETL pipeline to populate views.
          </p>
        )}
        <div className="grid gap-4 md:grid-cols-3">
          {[
            { label: "3DS friction rate", value: latest?.three_ds_friction_rate_pct, suffix: "%" },
            { label: "3DS authentication rate", value: latest?.three_ds_authentication_rate_pct, suffix: "%" },
            { label: "Issuer approval (post-auth)", value: latest?.issuer_approval_post_auth_rate_pct, suffix: "%" },
          ].map(({ label, value, suffix }) => (
            <Card
              key={label}
              className="glass-card border border-border/80 cursor-pointer hover:border-primary/40 hover:shadow-md transition-all"
              onClick={() => openInDatabricks(getLakeviewDashboardUrl("authentication_security"))}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getLakeviewDashboardUrl("authentication_security"))}
            >
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold tabular-nums">
                  {value != null ? `${value}${suffix}` : "—"}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
        <Button
          variant="outline"
          size="sm"
          className="mt-3 gap-2"
          onClick={() => openInDatabricks(getLakeviewDashboardUrl("authentication_security"))}
        >
          Open 3DS & authentication dashboard <ExternalLink className="h-3.5 w-3.5" />
        </Button>
      </section>

      {/* Top service paths */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Top service paths (payment links)</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Performance by service combination. Antifraud share of declines shown per path.
        </p>
        <Card className="glass-card border border-border/80">
          <CardContent className="pt-6">
            {servicePathsQ.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : servicePathsQ.isError ? (
              <p className="text-sm text-destructive">Failed to load data.</p>
            ) : servicePaths.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No data yet. Run the simulator and ETL to populate views.
              </p>
            ) : (
              <ul className="space-y-3">
                {servicePaths.map((r) => (
                  <li
                    key={r.service_path}
                    className="flex items-center justify-between gap-4 py-2 border-b border-border/50 last:border-0"
                  >
                    <div className="min-w-0">
                      <p className="font-mono text-sm truncate">{r.service_path}</p>
                      <p className="text-xs text-muted-foreground">
                        Antifraud declines: {r.antifraud_declines}
                        {r.antifraud_pct_of_declines != null ? ` (${r.antifraud_pct_of_declines}% of declines)` : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant="secondary">{r.transaction_count} tx</Badge>
                      <Badge>{r.approval_rate_pct}% approval</Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Button
          variant="outline"
          size="sm"
          className="mt-3 gap-2"
          onClick={() => openInDatabricks(getLakeviewDashboardUrl("routing_optimization"))}
        >
          Open routing dashboard <ExternalLink className="h-3.5 w-3.5" />
        </Button>
      </section>

      {/* Recommended path performance */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-3">Recommended path performance</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Approval rates for ML-recommended service paths.
        </p>
        <Card className="glass-card border border-border/80">
          <CardContent className="pt-6">
            {pathPerfQ.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : pathPerfQ.isError ? (
              <p className="text-sm text-destructive">Failed to load data.</p>
            ) : pathPerf.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data yet.</p>
            ) : (
              <ul className="space-y-2">
                {pathPerf.map((r) => (
                  <li
                    key={r.recommended_path}
                    className="flex items-center justify-between py-2 border-b border-border/50 last:border-0"
                  >
                    <span className="font-mono text-sm">{r.recommended_path}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{r.transaction_count}</Badge>
                      <Badge>{r.approval_rate_pct}%</Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
