/** Sidebar navigation — getnet Global Payments Command Center (reference layout). */
import { createFileRoute, Link, useLocation } from "@tanstack/react-router";
import {
  BarChart3,
  BadgeX,
  Brain,
  Bot,
  Code2,
  CreditCard,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  ListChecks,
  MessageSquareText,
  RotateCcw,
  ScrollText,
  Settings,
  User,
} from "lucide-react";
import SidebarLayout from "@/components/apx/sidebar-layout";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
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
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 min-w-0 min-h-[2.75rem]",
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

  // Primary nav (spec): Overview, Real-Time Monitor, Performance Deep-Dive, Data Quality
  const primaryItems: NavItem[] = [
    { to: "/command-center", label: "Overview", icon: <LayoutDashboard size={16} />, tooltip: "Executive overview: KPIs, TPS, dashboards, AI chat.", match: (p) => p === "/command-center" || p === "/dashboard" },
    { to: "/incidents", label: "Real-Time Monitor", icon: <BarChart3 size={16} />, tooltip: "Live volume and incidents.", match: (p) => p === "/incidents" },
    { to: "/dashboards", label: "Performance Deep-Dive", icon: <LayoutDashboard size={16} />, tooltip: "BI dashboards and performance analytics.", match: (p) => p === "/dashboards" },
    { to: "/alerts-data-quality", label: "Data Quality", icon: <Gauge size={16} />, tooltip: "Alerts and streaming data quality.", match: (p) => p === "/alerts-data-quality" },
  ];

  const moreItems: NavItem[] = [
    { to: "/about", label: "About", icon: <ScrollText size={16} />, tooltip: "Platform overview.", match: (p) => p === "/about" },
    { to: "/ai-agents", label: "AI agents", icon: <Bot size={16} />, tooltip: "Agents and Genie.", match: (p) => p === "/ai-agents" },
    { to: "/decisioning", label: "Recommendations & decisions", icon: <MessageSquareText size={16} />, tooltip: "Decisioning API.", match: (p) => p === "/decisioning" },
    { to: "/rules", label: "Rules", icon: <ScrollText size={16} />, tooltip: "Approval and routing rules.", match: (p) => p === "/rules" },
    { to: "/initiatives", label: "Payment Services & Data", icon: <LayoutDashboard size={16} />, tooltip: "Services and data sources.", match: (p) => p === "/initiatives" },
    { to: "/notebooks", label: "Notebooks", icon: <Code2 size={16} />, tooltip: "Notebooks and ETL.", match: (p) => p === "/notebooks" },
    { to: "/models", label: "ML models", icon: <Brain size={16} />, tooltip: "Unity Catalog models.", match: (p) => p === "/models" },
    { to: "/experiments", label: "Experiments", icon: <FlaskConical size={16} />, tooltip: "MLflow runs.", match: (p) => p === "/experiments" },
    { to: "/declines", label: "Declines", icon: <BadgeX size={16} />, tooltip: "Decline analysis.", match: (p) => p === "/declines" },
    { to: "/reason-codes", label: "Reason Codes", icon: <ListChecks size={16} />, tooltip: "Reason-code taxonomy.", match: (p) => p === "/reason-codes" },
    { to: "/smart-checkout", label: "Smart Checkout", icon: <CreditCard size={16} />, tooltip: "Checkout performance.", match: (p) => p === "/smart-checkout" },
    { to: "/smart-retry", label: "Smart Retry", icon: <RotateCcw size={16} />, tooltip: "Retry and recovery.", match: (p) => p === "/smart-retry" },
    { to: "/profile", label: "Profile", icon: <User size={16} />, tooltip: "User settings.", match: (p) => p === "/profile" },
    { to: "/setup", label: "Control panel", icon: <Settings size={16} />, tooltip: "Setup and pipelines.", match: (p) => p === "/setup" },
  ];

  return (
    <SidebarLayout>
      <nav aria-label="Primary navigation" className="contents">
        <SidebarGroup aria-label="Command Center">
          <SidebarGroupLabel className="nav-group-label">Command Center</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {primaryItems.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <NavLink item={item} isActive={item.match(location.pathname)} />
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup aria-label="More">
          <SidebarGroupLabel className="nav-group-label">More</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {moreItems.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <NavLink item={item} isActive={item.match(location.pathname)} />
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </nav>
    </SidebarLayout>
  );
}
