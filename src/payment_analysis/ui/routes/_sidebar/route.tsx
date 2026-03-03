/**
 * Sidebar navigation — Payment Platform Command Center.
 *
 * Groups are organised by user intent:
 *   1. Overview        – single hub
 *   2. Analytics       – dashboards, declines, reason-codes, monitoring
 *   3. Optimization    – checkout, retry, decisioning
 *   4. AI & ML         – agents, models, experiments
 *   5. Administration  – rules, notebooks, setup
 *
 * "About" is accessible from the sidebar footer (reference, not a workflow page).
 * "Profile" lives in the header avatar; not repeated here.
 */
import { createFileRoute, Link, useLocation } from "@tanstack/react-router";
import {
  Activity,
  BadgeX,
  Bot,
  Brain,
  Code2,
  CreditCard,
  FlaskConical,
  Info,
  LayoutDashboard,
  ListChecks,
  PanelTop,
  RefreshCw,
  Scale,
  Settings,
  ShieldCheck,
} from "lucide-react";
import SidebarLayout from "@/components/apx/sidebar-layout";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_sidebar")({
  component: () => <Layout />,
});

type NavItem = {
  to: string;
  label: string;
  icon: React.ReactNode;
  tooltip: string;
  match: (path: string) => boolean;
};

function NavLink({ item, isActive }: { item: NavItem; isActive: boolean }) {
  const link = (
    <Link
      to={item.to}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 min-w-0 min-h-[2.5rem]",
        "border-l-[3px] border-transparent -ml-[3px]",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground border-sidebar-primary shadow-sm"
          : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground hover:border-sidebar-primary/30",
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <span className="shrink-0 size-5 flex items-center justify-center [&>svg]:size-[1.125rem] text-current">{item.icon}</span>
      <span className="truncate">{item.label}</span>
    </Link>
  );
  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right" className="max-w-[220px]">
        {item.tooltip}
      </TooltipContent>
    </Tooltip>
  );
}

function Layout() {
  const location = useLocation();

  /* ── 1. Overview (single hub) ── */
  const overviewItems: NavItem[] = [
    {
      to: "/command-center",
      label: "Overview",
      icon: <LayoutDashboard size={16} />,
      tooltip: "Executive hub: KPIs, approval trends, dashboards, alerts, and AI chat.",
      match: (p) => p === "/command-center" || p === "/dashboard" || p === "/initiatives",
    },
  ];

  /* ── 2. Analytics ── */
  const analyticsItems: NavItem[] = [
    {
      to: "/dashboards",
      label: "Performance Dashboards",
      icon: <PanelTop size={16} />,
      tooltip: "Embedded BI dashboards and performance deep-dives.",
      match: (p) => p === "/dashboards",
    },
    {
      to: "/declines",
      label: "Declines",
      icon: <BadgeX size={16} />,
      tooltip: "Decline analytics: KPIs, buckets, factors, recovery, and card network performance.",
      match: (p) => p === "/declines",
    },
    {
      to: "/reason-codes",
      label: "Reason Codes",
      icon: <ListChecks size={16} />,
      tooltip: "Standardised reason-code taxonomy, false-insight metrics, and expert review.",
      match: (p) => p === "/reason-codes",
    },
    {
      to: "/data-quality",
      label: "Monitoring & Quality",
      icon: <Activity size={16} />,
      tooltip: "Real-time TPS, data quality health, active alerts, and incident tracking.",
      match: (p) => p === "/data-quality" || p === "/incidents" || p === "/alerts-data-quality",
    },
  ];

  /* ── 3. Optimization ── */
  const optimizationItems: NavItem[] = [
    {
      to: "/smart-checkout",
      label: "Smart Checkout",
      icon: <CreditCard size={16} />,
      tooltip: "3DS funnel, service-path performance, and optimal checkout configuration.",
      match: (p) => p === "/smart-checkout",
    },
    {
      to: "/smart-retry",
      label: "Smart Retry",
      icon: <RefreshCw size={16} />,
      tooltip: "Retry KPIs, success rates by scenario, and recovered revenue.",
      match: (p) => p === "/smart-retry",
    },
    {
      to: "/decisioning",
      label: "Decisioning",
      icon: <Scale size={16} />,
      tooltip: "Test auth, retry, and routing decisions. ML predictions and recommendations.",
      match: (p) => p === "/decisioning",
    },
  ];

  /* ── 4. AI & ML ── */
  const aiMlItems: NavItem[] = [
    {
      to: "/ai-agents",
      label: "AI Agents",
      icon: <Bot size={16} />,
      tooltip: "Orchestrator, specialist agents, and Genie integration.",
      match: (p) => p === "/ai-agents",
    },
    {
      to: "/models",
      label: "ML Models",
      icon: <Brain size={16} />,
      tooltip: "Unity Catalog model registry: versions, status, and serving endpoints.",
      match: (p) => p === "/models",
    },
    {
      to: "/experiments",
      label: "Experiments",
      icon: <FlaskConical size={16} />,
      tooltip: "A/B experiments and MLflow run tracking.",
      match: (p) => p === "/experiments",
    },
  ];

  /* ── 5. Administration ── */
  const adminItems: NavItem[] = [
    {
      to: "/rules",
      label: "Rules",
      icon: <ShieldCheck size={16} />,
      tooltip: "Approval and routing business rules (CRUD).",
      match: (p) => p === "/rules",
    },
    {
      to: "/notebooks",
      label: "Notebooks",
      icon: <Code2 size={16} />,
      tooltip: "Browse and open workspace notebooks (ETL, ML, agents).",
      match: (p) => p === "/notebooks",
    },
    {
      to: "/setup",
      label: "Setup & Run",
      icon: <Settings size={16} />,
      tooltip: "Jobs, pipelines, catalog/schema config, and connection status.",
      match: (p) => p === "/setup",
    },
  ];

  const renderGroup = (label: string, items: NavItem[]) => (
    <SidebarGroup aria-label={label}>
      <SidebarGroupLabel className="nav-group-label">{label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => (
            <SidebarMenuItem key={item.to}>
              <NavLink item={item} isActive={item.match(location.pathname)} />
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );

  return (
    <SidebarLayout>
      <nav aria-label="Primary navigation" className="contents">
        {renderGroup("Overview", overviewItems)}
        <SidebarSeparator className="mx-3" />
        {renderGroup("Analytics", analyticsItems)}
        <SidebarSeparator className="mx-3" />
        {renderGroup("Optimization", optimizationItems)}
        <SidebarSeparator className="mx-3" />
        {renderGroup("AI & ML", aiMlItems)}
        <SidebarSeparator className="mx-3" />
        {renderGroup("Administration", adminItems)}

        {/* About — reference link at the bottom */}
        <SidebarGroup aria-label="Help" className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <NavLink
                  item={{
                    to: "/about",
                    label: "About this platform",
                    icon: <Info size={16} />,
                    tooltip: "Business purpose, capabilities, and documentation links.",
                    match: (p) => p === "/about",
                  }}
                  isActive={location.pathname === "/about"}
                />
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </nav>
    </SidebarLayout>
  );
}
