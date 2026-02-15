/** Sidebar layout and breadcrumb — Getnet Global Payments Command Center (Pro-Dark, glassmorphism). */
import { useState } from "react";
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
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import SidebarUserFooter from "@/components/apx/sidebar-user-footer";
import { ModeToggle } from "@/components/apx/mode-toggle";
import { MockDataToggle } from "@/components/apx/mock-data-toggle";
import { CountrySelect } from "@/components/apx/country-select";
import { DateRangePresetSelect, type DateRangePreset } from "@/components/apx/date-range-preset";
import Logo from "@/components/apx/logo";
import { cn } from "@/lib/utils";
import { AssistantProvider, useAssistant } from "@/contexts/assistant-context";
import { AIChatbot, GenieAssistant } from "@/components/chat";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Bot, Sparkles } from "lucide-react";
import { NotificationBell } from "@/components/apx/notification-bell";

const PATH_LABELS: Record<string, string> = {
  /* Overview */
  "/command-center": "Overview",
  "/dashboard": "Overview",
  "/initiatives": "Overview",
  /* Analytics */
  "/dashboards": "Performance Dashboards",
  "/declines": "Declines",
  "/reason-codes": "Reason Codes",
  "/data-quality": "Monitoring & Quality",
  "/incidents": "Monitoring & Quality",
  "/alerts-data-quality": "Monitoring & Quality",
  /* Optimization */
  "/smart-checkout": "Smart Checkout",
  "/smart-retry": "Smart Retry",
  "/decisioning": "Decisioning",
  /* AI & ML */
  "/ai-agents": "AI Agents",
  "/models": "ML Models",
  "/experiments": "Experiments",
  /* Administration */
  "/rules": "Rules",
  "/notebooks": "Notebooks",
  "/setup": "Setup & Run",
  /* Other */
  "/about": "About this platform",
  "/profile": "Profile",
};

// Friendly names for embedded dashboard breadcrumb (id -> label)
const DASHBOARD_EMBED_LABELS: Record<string, string> = {
  data_quality_unified: "Data & Quality",
  ml_optimization_unified: "ML & Optimization",
  executive_trends_unified: "Executive & Trends",
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
    <nav className={cn("flex items-center gap-1.5 text-sm text-muted-foreground min-w-0 flex-1", path === "/command-center" && "md:opacity-70")} aria-label="Breadcrumb">
      <Tooltip>
        <TooltipTrigger asChild>
          <Link to="/command-center" className="link-anchor hover:text-foreground transition-colors truncate max-w-[8rem] sm:max-w-none" aria-label="Command Center">
            Overview
          </Link>
        </TooltipTrigger>
        <TooltipContent>Main hub: KPIs, dashboards, alerts, and AI chat.</TooltipContent>
      </Tooltip>
      <span aria-hidden className="shrink-0">/</span>
      {path === "/dashboards" && embedId ? (
        <>
          <Link to="/dashboards" className="link-anchor hover:text-foreground transition-colors truncate max-w-[6rem] sm:max-w-none">
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

/** Two floating chat dialogs: Approval Rate Accelerator (orchestrator-only); Genie Assistant → lakehouse data. */
function GlobalChatPanels() {
  const {
    openAIChatbot,
    setOpenAIChatbot,
    openGenieAssistant,
    setOpenGenieAssistant,
  } = useAssistant();
  return (
    <>
      <AIChatbot
        open={openAIChatbot}
        onOpenChange={setOpenAIChatbot}
        position="left"
      />
      <GenieAssistant
        open={openGenieAssistant}
        onOpenChange={setOpenGenieAssistant}
        position="right"
      />
    </>
  );
}

interface SidebarLayoutProps {
  children?: ReactNode;
}

function HeaderActions() {
  const { openAIChatbotPanel, openGenieAssistantPanel } = useAssistant();
  return (
    <div className="flex items-center gap-2">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={openAIChatbotPanel}
            aria-label="Open AI chat"
          >
            <Bot className="h-4 w-4" />
            <span className="hidden sm:inline">AI chat</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>Approval Rate Accelerator: recommendations, semantic search, and intelligence from the orchestrator</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={openGenieAssistantPanel}
            aria-label="Open Genie Assistant"
          >
            <Sparkles className="h-4 w-4" />
            <span className="hidden sm:inline">Genie Assistant</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>Chat with Databricks Genie for lakehouse data and insights</TooltipContent>
      </Tooltip>
    </div>
  );
}

function SidebarLayout({ children }: SidebarLayoutProps) {
  const [dateRange, setDateRange] = useState<DateRangePreset>("30");
  return (
    <AssistantProvider>
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader className="sidebar-header">
          <div className="sidebar-header-inner">
            <Logo to="/" showText />
            <p className="text-[11px] font-medium text-primary tracking-wide px-2 pt-0.5" aria-hidden>Approval rates optimizations</p>
          </div>
        </SidebarHeader>
        <SidebarContent>{children}</SidebarContent>
        <SidebarFooter className="border-t border-sidebar-border pt-3 px-3 pb-3">
          <p className="text-[11px] text-muted-foreground leading-snug" aria-hidden>
            Powered by Databricks · Live data from your workspace
          </p>
          <SidebarUserFooter />
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
      <SidebarInset className="flex flex-col h-screen">
        <header
          role="banner"
          className="sticky top-0 z-50 bg-card/95 backdrop-blur-md border-b border-border flex min-h-[3.75rem] shrink-0 items-center gap-4 px-4 md:px-6 py-3 transition-colors duration-200 shadow-sm overflow-visible"
          aria-label="App header"
        >
          <SidebarTrigger className="-ml-1 cursor-pointer rounded-lg p-2 transition-colors hover:bg-sidebar-accent/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" aria-label="Toggle sidebar" />
          <div className="flex flex-col min-w-0 flex-1 md:flex-row md:items-center md:gap-4">
            <h1 className="text-base md:text-lg font-semibold text-foreground truncate order-2 md:order-1">
              Global Payments Command Center
            </h1>
            <Breadcrumb />
          </div>
          <div className="flex items-center gap-2 shrink-0" role="group" aria-label="Top bar filters and profile">
            <HeaderActions />
            <NotificationBell />
            <CountrySelect className="hidden sm:flex" />
            <DateRangePresetSelect value={dateRange} onChange={setDateRange} className="hidden md:flex" />
            <MockDataToggle />
            <ModeToggle />
            <Tooltip>
              <TooltipTrigger asChild>
                <Link
                  to="/profile"
                  className="flex items-center gap-2 rounded-full bg-muted/80 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors border border-border/60"
                  aria-label="CEO profile"
                >
                  <Avatar className="h-6 w-6 border border-border">
                    <AvatarFallback className="text-[10px] bg-primary/20 text-primary">CEO</AvatarFallback>
                  </Avatar>
                  <span className="hidden sm:inline">CEO profile</span>
                </Link>
              </TooltipTrigger>
              <TooltipContent>CEO profile and settings.</TooltipContent>
            </Tooltip>
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
            className="page-container flex flex-1 flex-col gap-6 py-6 md:py-8 w-full"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          >
            <Outlet />
          </motion.div>
        </main>
        <GlobalChatPanels />
      </SidebarInset>
    </SidebarProvider>
    </AssistantProvider>
  );
}
export default SidebarLayout;
