import { createFileRoute } from "@tanstack/react-router";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  useGetSmartCheckoutServicePathsBr,
  useGetThreeDsFunnelBr,
  useGetSmartCheckoutPathPerformanceBr,
} from "@/lib/api";
import { getDashboardUrl } from "@/config/workspace";

const openInDatabricks = (url: string) => {
  if (url) window.open(url, "_blank");
};

export const Route = createFileRoute("/_sidebar/smart-checkout")({
  component: () => <SmartCheckout />,
});

function SmartCheckout() {
  const servicePathsQ = useGetSmartCheckoutServicePathsBr({
    params: { limit: 25 },
  });

  const funnelQ = useGetThreeDsFunnelBr({ params: { days: 30 } });

  const pathPerfQ = useGetSmartCheckoutPathPerformanceBr({
    params: { limit: 20 },
  });

  const servicePaths = servicePathsQ.data?.data ?? [];
  const funnel = funnelQ.data?.data ?? [];
  const latest = funnel[0];
  const pathPerf = pathPerfQ.data?.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Smart Checkout (Brazil)</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Service-path observability for payment-link flows (demo scaffold).
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/authentication_security"))} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/authentication_security"))}>
          <CardHeader>
            <CardTitle>3DS friction</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {latest?.three_ds_friction_rate_pct != null
              ? `${latest.three_ds_friction_rate_pct}%`
              : "—"}
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/authentication_security"))} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/authentication_security"))}>
          <CardHeader>
            <CardTitle>3DS authentication</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {latest?.three_ds_authentication_rate_pct != null
              ? `${latest.three_ds_authentication_rate_pct}%`
              : "—"}
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/authentication_security"))} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/authentication_security"))}>
          <CardHeader>
            <CardTitle>Issuer approval (post-auth)</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {latest?.issuer_approval_post_auth_rate_pct != null
              ? `${latest.issuer_approval_post_auth_rate_pct}%`
              : "—"}
          </CardContent>
        </Card>
      </div>

      <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))}>
        <CardHeader>
          <CardTitle>Top service paths (payment links)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {servicePathsQ.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : servicePathsQ.isError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load Smart Checkout data.
            </p>
          ) : servicePaths.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No data yet. Run the simulator + Lakeflow to
              populate UC views.
            </p>
          ) : (
            servicePaths.map((r) => (
              <div
                key={r.service_path}
                className="flex items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="font-mono text-xs truncate">
                    {r.service_path}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    antifraud declines: {r.antifraud_declines}
                    {r.antifraud_pct_of_declines != null
                      ? ` (${r.antifraud_pct_of_declines}%)`
                      : ""}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{r.transaction_count}</Badge>
                  <Badge>{r.approval_rate_pct}%</Badge>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openInDatabricks(getDashboardUrl("/sql/dashboards/routing_optimization"))}>
        <CardHeader>
          <CardTitle>Recommended path performance</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {pathPerfQ.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : pathPerfQ.isError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load recommended path performance.
            </p>
          ) : pathPerf.length === 0 ? (
            <p className="text-sm text-muted-foreground">No data yet.</p>
          ) : (
            pathPerf.map((r) => (
              <div
                key={r.recommended_path}
                className="flex items-center justify-between gap-3"
              >
                <div className="font-mono text-sm">{r.recommended_path}</div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{r.transaction_count}</Badge>
                  <Badge>{r.approval_rate_pct}%</Badge>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
