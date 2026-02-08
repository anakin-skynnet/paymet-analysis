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

function Breadcrumb() {
  const location = useLocation();
  const path = location.pathname;
  const label = PATH_LABELS[path] ?? "Overview";
  return (
    <nav className="flex items-center gap-1.5 text-sm text-muted-foreground min-w-0" aria-label="Breadcrumb">
      <Link to="/" className="hover:text-foreground transition-colors truncate">
        Home
      </Link>
      <span aria-hidden className="shrink-0">/</span>
      <span className="truncate font-medium text-foreground">{label}</span>
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
        <SidebarHeader>
          <div className="px-2 py-2">
            <Logo to="/" showText />
          </div>
        </SidebarHeader>
        <SidebarContent>{children}</SidebarContent>
        <SidebarFooter>
          <SidebarUserFooter />
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
      <SidebarInset className="flex flex-col h-screen">
        <header className="sticky top-0 z-50 bg-background/85 backdrop-blur-md border-b flex h-16 shrink-0 items-center gap-4 px-4 transition-colors duration-200">
          <SidebarTrigger className="-ml-1 cursor-pointer rounded-md transition-opacity hover:opacity-80 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" />
          <Breadcrumb />
          <div className="flex-1 min-w-0" />
          <ModeToggle />
        </header>
        <div className="flex flex-1 justify-center overflow-auto min-h-0">
          <motion.div
            className="flex flex-1 flex-col gap-6 p-6 md:p-8 max-w-7xl w-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            <Outlet />
          </motion.div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
export default SidebarLayout;
