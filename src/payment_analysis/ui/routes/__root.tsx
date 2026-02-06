import { ThemeProvider } from "@/components/apx/theme-provider";
import { Button } from "@/components/ui/button";
import { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { ErrorBoundary } from "react-error-boundary";
import { Toaster } from "sonner";

function RootErrorFallback({
  error,
  resetErrorBoundary,
}: {
  error: Error;
  resetErrorBoundary: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-xl font-semibold">Something went wrong</h1>
      <p className="max-w-md text-sm text-muted-foreground">{error.message}</p>
      <Button onClick={resetErrorBoundary}>Try again</Button>
      <Button variant="outline" onClick={() => window.location.assign("/")}>
        Go to home
      </Button>
    </div>
  );
}

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient;
}>()({
  component: () => (
    <ThemeProvider defaultTheme="dark" storageKey="apx-ui-theme">
      <ErrorBoundary FallbackComponent={RootErrorFallback}>
        {import.meta.env.DEV && (
          <>
            <TanStackRouterDevtools position="bottom-right" />
          </>
        )}
        <Outlet />
      </ErrorBoundary>
      <Toaster richColors />
    </ThemeProvider>
  ),
});
