import { Outlet, useLocation, Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { motion } from "motion/react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import SidebarUserFooter from "@/components/apx/sidebar-user-footer";
import { ModeToggle } from "@/components/apx/mode-toggle";
import { CountrySelect } from "@/components/apx/country-select";
import Logo from "@/components/apx/logo";

const PATH_LABELS: Record<string, string> = {
  "/dashboard": "KPI overview",
  "/dashboards": "Dashboards",
  "/setup": "Setup & run",
  "/notebooks": "Notebooks",
  "/models": "ML models",
  "/ai-agents": "AI agents",
  "/decisioning": "Recommendations & decisions",
  "/rules": "Rules",
  "/experiments": "Experiments",
  "/incidents": "Incidents",
  "/declines": "Declines",
  "/smart-checkout": "Smart Checkout",
  "/reason-codes": "Reason Codes",
  "/smart-retry": "Smart Retry",
  "/profile": "Profile",
};

// Friendly names for embedded dashboard breadcrumb (id -> label)
const DASHBOARD_EMBED_LABELS: Record<string, string> = {
  executive_overview: "Executive Overview",
  decline_analysis: "Decline Analysis",
  realtime_monitoring: "Realtime Monitoring",
  fraud_risk_analysis: "Fraud Risk Analysis",
  merchant_performance: "Merchant Performance",
  routing_optimization: "Routing Optimization",
  daily_trends: "Daily Trends",
  authentication_security: "Authentication & Security",
  financial_impact: "Financial Impact",
  performance_latency: "Performance & Latency",
  streaming_data_quality: "Streaming Data Quality",
  global_coverage: "Global Coverage",
};

function Breadcrumb() {
  const location = useLocation();
  const path = location.pathname;
  const embedId =
    path === "/dashboards" && location.search
      ? new URLSearchParams(location.search).get("embed")
      : null;
  const baseLabel = PATH_LABELS[path] ?? "Overview";
  const embedLabel = embedId ? DASHBOARD_EMBED_LABELS[embedId] ?? embedId.replace(/_/g, " ") : null;
  const label = embedLabel ? `${baseLabel} / ${embedLabel}` : baseLabel;
  return (
    <nav className="flex items-center gap-1.5 text-sm text-muted-foreground min-w-0" aria-label="Breadcrumb">
      <Link to="/" className="hover:text-foreground transition-colors truncate focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded">
        Home
      </Link>
      <span aria-hidden className="shrink-0">/</span>
      {path === "/dashboards" && embedId ? (
        <>
          <Link to="/dashboards" className="hover:text-foreground transition-colors truncate focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded">
            Dashboards
          </Link>
          <span aria-hidden className="shrink-0">/</span>
          <span className="truncate font-medium text-foreground">{embedLabel}</span>
        </>
      ) : (
        <span className="truncate font-medium text-foreground">{label}</span>
      )}
    </nav>
  );
}

interface SidebarLayoutProps {
  children?: ReactNode;
}

function SidebarLayout({ children }: SidebarLayoutProps) {
  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader className="sidebar-header">
          <div className="sidebar-header-inner flex flex-col gap-0.5">
            <Logo to="/" showText />
            <p className="text-[11px] font-medium text-primary tracking-wide px-2" aria-hidden>Accelerate approval rates</p>
          </div>
        </SidebarHeader>
        <SidebarContent>{children}</SidebarContent>
        <SidebarFooter className="border-t border-sidebar-border pt-3">
          <p className="px-3 pb-2 text-[11px] text-muted-foreground leading-snug" aria-hidden>
            Data &amp; results from your Databricks workspace
          </p>
          <SidebarUserFooter />
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
      <SidebarInset className="flex flex-col h-screen">
        <header
          role="banner"
          className="sticky top-0 z-50 bg-background/95 backdrop-blur-md border-b border-border flex h-14 min-h-14 shrink-0 items-center gap-4 px-4 md:px-6 transition-colors duration-200 shadow-sm"
          aria-label="App header"
        >
          <SidebarTrigger className="-ml-1 cursor-pointer rounded-lg p-2 transition-colors hover:bg-sidebar-accent/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" aria-label="Toggle sidebar" />
          <Breadcrumb />
          <div className="flex-1 min-w-0" aria-hidden />
          <div className="flex items-center gap-2 shrink-0" role="group" aria-label="Workspace and appearance">
            <CountrySelect className="flex" />
            <ModeToggle />
          </div>
        </header>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2.5 focus:bg-primary focus:text-primary-foreground focus:rounded-lg focus:font-medium focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          Skip to main content
        </a>
        <main
          id="main-content"
          role="main"
          className="flex flex-1 justify-center overflow-auto min-h-0 main-content-area scrollbar-thin"
          tabIndex={-1}
        >
          <motion.div
            className="page-container flex flex-1 flex-col gap-6 p-6 md:p-8 w-full"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          >
            <Outlet />
          </motion.div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
export default SidebarLayout;
