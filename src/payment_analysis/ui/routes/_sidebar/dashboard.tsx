import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useGetKpisSuspense } from "@/lib/api";
import selector from "@/lib/selector";

export const Route = createFileRoute("/_sidebar/dashboard")({
  component: () => <Dashboard />,
});

function Dashboard() {
  const { data } = useGetKpisSuspense(selector());

  const pct = (data.approval_rate * 100).toFixed(2);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Approval performance</h1>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Total auths</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-bold">{data.total}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Approved</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-bold">{data.approved}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Approval rate</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-bold">{pct}%</CardContent>
        </Card>
      </div>

      <p className="text-sm text-muted-foreground">
        This is backed by Lakebase tables in the scaffold. In production, you’d
        feed these from Lakeflow streaming and slice by merchant/BIN/geo/network.
      </p>
    </div>
  );
}

