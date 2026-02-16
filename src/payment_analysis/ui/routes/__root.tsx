import { ThemeProvider } from "@/components/apx/theme-provider";
import { Button } from "@/components/ui/button";
import { WorkspaceUrlBootstrapper } from "@/components/apx/workspace-url-bootstrapper";
import { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { ErrorBoundary, type FallbackProps } from "react-error-boundary";
import { Suspense } from "react";
import { Toaster } from "sonner";

function RootErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 p-6 md:p-10 text-center bg-background">
      <div className="rounded-2xl border border-border/80 bg-card p-6 md:p-8 shadow-lg max-w-md w-full space-y-6 container-fit-x">
        <div className="flex justify-center">
          <div className="rounded-full bg-destructive/10 p-4 media-container">
            <svg className="h-10 w-10 text-destructive shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
        </div>
        <div className="space-y-2" role="alert" aria-live="assertive">
          <h1 className="text-xl font-semibold font-heading">Something went wrong loading this view</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">{message}</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Button onClick={resetErrorBoundary} className="min-w-[140px]">
            Try again
          </Button>
          <Button variant="outline" onClick={() => window.location.assign("/")} className="min-w-[140px]">
            Go to home
          </Button>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient;
}>()({
  component: () => (
    <ThemeProvider defaultTheme="dark" storageKey="apx-ui-theme">
      <WorkspaceUrlBootstrapper />
      <ErrorBoundary FallbackComponent={RootErrorFallback}>
        {import.meta.env.DEV && (
          <>
            <TanStackRouterDevtools position="bottom-right" />
          </>
        )}
        <Suspense fallback={
          <div className="flex min-h-screen items-center justify-center bg-background">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        }>
          <Outlet />
        </Suspense>
      </ErrorBoundary>
      <Toaster richColors />
    </ThemeProvider>
  ),
});
