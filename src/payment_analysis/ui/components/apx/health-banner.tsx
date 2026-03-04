/**
 * Global connection/health banner when backend or Databricks is unreachable.
 * Shown on sidebar layout so users see a single "connection issue" message
 * instead of many sections stuck in loading or empty.
 */
import { useHealthDatabricks, healthDatabricksKey } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

const HEALTH_REFETCH_MS = 30_000;

export function HealthBanner() {
  const queryClient = useQueryClient();
  const { isError, isPending, refetch } = useHealthDatabricks({
    query: {
      refetchInterval: HEALTH_REFETCH_MS,
      retry: 2,
      retryDelay: 5000,
    },
  });

  if (!isError) return null;

  const handleRetry = () => {
    queryClient.invalidateQueries({ queryKey: healthDatabricksKey() });
    refetch();
  };

  return (
    <Alert
      variant="destructive"
      className="rounded-none border-x-0 border-t-0 border-destructive/50 bg-destructive/10"
      role="status"
      aria-live="polite"
    >
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>Can&apos;t reach Databricks</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center gap-2">
        <span>Some data may be missing. Open the app from Compute → Apps in your workspace, or check your connection.</span>
        <Button
          variant="outline"
          size="sm"
          className="shrink-0 border-destructive/50 text-destructive hover:bg-destructive/20"
          onClick={handleRetry}
          disabled={isPending}
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isPending ? "animate-spin" : ""}`} />
          Retry
        </Button>
      </AlertDescription>
    </Alert>
  );
}
