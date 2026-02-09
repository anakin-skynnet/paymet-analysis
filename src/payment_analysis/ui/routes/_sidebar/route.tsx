import { createFileRoute, Link, useLocation } from "@tanstack/react-router";
import {
  AlertTriangle,
  BarChart3,
  BadgeX,
  Brain,
  Bot,
  Code2,
  CreditCard,
  FlaskConical,
  LayoutDashboard,
  ListChecks,
  MessageSquareText,
  Rocket,
  RotateCcw,
  ScrollText,
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
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_sidebar")({
  component: () => <Layout />,
});

type NavItem = {
  to: string;
  label: string;
  icon: React.ReactNode;
  match: (path: string) => boolean;
};

function NavLink({ item, isActive }: { item: NavItem; isActive: boolean }) {
  return (
    <Link
      to={item.to}
      className={cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 min-w-0",
        "border-l-[3px] border-transparent -ml-[3px]",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground border-sidebar-primary shadow-sm"
          : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground hover:border-sidebar-primary/30",
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <span className="shrink-0 size-4 flex items-center justify-center [&>svg]:size-4">{item.icon}</span>
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

function Layout() {
  const location = useLocation();

  // Overview: portfolio and dashboards (CEO at a glance)
  const overviewItems: NavItem[] = [
    { to: "/dashboard", label: "KPI overview", icon: <BarChart3 size={16} />, match: (p) => p === "/dashboard" },
    { to: "/dashboards", label: "Dashboards", icon: <LayoutDashboard size={16} />, match: (p) => p === "/dashboards" },
  ];

  // Reasons & factors: identify what impacts approval rates
  const reasonsAndFactorsItems: NavItem[] = [
    { to: "/reason-codes", label: "Reason Codes", icon: <ListChecks size={16} />, match: (p) => p === "/reason-codes" },
    { to: "/declines", label: "Declines", icon: <BadgeX size={16} />, match: (p) => p === "/declines" },
  ];

  // Recommendations & actions: how to accelerate approval rates
  const recommendationsItems: NavItem[] = [
    { to: "/decisioning", label: "Recommendations & decisions", icon: <MessageSquareText size={16} />, match: (p) => p === "/decisioning" },
    { to: "/rules", label: "Rules", icon: <ScrollText size={16} />, match: (p) => p === "/rules" },
  ];

  // Initiatives: payment conditions and retry analysis
  const initiativeItems: NavItem[] = [
    { to: "/smart-checkout", label: "Smart Checkout", icon: <CreditCard size={16} />, match: (p) => p === "/smart-checkout" },
    { to: "/smart-retry", label: "Smart Retry", icon: <RotateCcw size={16} />, match: (p) => p === "/smart-retry" },
  ];

  // AI & automation: agents that accelerate approvals
  const automationItems: NavItem[] = [
    { to: "/ai-agents", label: "AI agents", icon: <Bot size={16} />, match: (p) => p === "/ai-agents" },
  ];

  // Operations: setup, notebooks, models, incidents, experiments
  const operationsItems: NavItem[] = [
    { to: "/setup", label: "Setup & run", icon: <Rocket size={16} />, match: (p) => p === "/setup" },
    { to: "/notebooks", label: "Notebooks", icon: <Code2 size={16} />, match: (p) => p === "/notebooks" },
    { to: "/models", label: "ML models", icon: <Brain size={16} />, match: (p) => p === "/models" },
    { to: "/incidents", label: "Incidents", icon: <AlertTriangle size={16} />, match: (p) => p === "/incidents" },
    { to: "/experiments", label: "Experiments", icon: <FlaskConical size={16} />, match: (p) => p === "/experiments" },
  ];

  const settingsItems: NavItem[] = [
    { to: "/profile", label: "Profile", icon: <User size={16} />, match: (p) => p === "/profile" },
  ];

  return (
    <SidebarLayout>
      <nav aria-label="Primary navigation" className="contents">
      <SidebarGroup aria-label="Overview section">
        <SidebarGroupLabel className="nav-group-label">
          Overview
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {overviewItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <NavLink item={item} isActive={item.match(location.pathname)} />
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarGroup aria-label="Reasons and factors section">
        <SidebarGroupLabel className="nav-group-label">
          Reasons & factors
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {reasonsAndFactorsItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <NavLink item={item} isActive={item.match(location.pathname)} />
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarGroup aria-label="Recommendations and actions section">
        <SidebarGroupLabel className="nav-group-label">
          Recommendations & actions
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {recommendationsItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <NavLink item={item} isActive={item.match(location.pathname)} />
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarGroup aria-label="Initiatives section">
        <SidebarGroupLabel className="nav-group-label">
          Initiatives
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {initiativeItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <NavLink item={item} isActive={item.match(location.pathname)} />
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarGroup aria-label="AI and automation section">
        <SidebarGroupLabel className="nav-group-label">
          AI & automation
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {automationItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <NavLink item={item} isActive={item.match(location.pathname)} />
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarGroup aria-label="Operations section">
        <SidebarGroupLabel className="nav-group-label">
          Operations
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {operationsItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <NavLink item={item} isActive={item.match(location.pathname)} />
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarGroup aria-label="Settings section">
        <SidebarGroupLabel className="nav-group-label">
          Settings
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {settingsItems.map((item) => (
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
