import SidebarLayout from "@/components/apx/sidebar-layout";
import { createFileRoute, Link, useLocation } from "@tanstack/react-router";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  BarChart3,
  BadgeX,
  FlaskConical,
  User,
  Wand2,
  LayoutDashboard,
  Code2,
  Brain,
  Bot,
  Rocket,
  CreditCard,
  ListChecks,
  RotateCcw,
  ScrollText,
} from "lucide-react";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

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
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200",
        "border-l-2 border-transparent -ml-[2px]",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground border-sidebar-primary"
          : "text-sidebar-foreground hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
      )}
    >
      {item.icon}
      <span>{item.label}</span>
    </Link>
  );
}

function Layout() {
  const location = useLocation();

  const overviewItems: NavItem[] = [
    { to: "/dashboard", label: "Dashboard", icon: <BarChart3 size={16} />, match: (p) => p === "/dashboard" },
    { to: "/setup", label: "Setup & Run", icon: <Rocket size={16} />, match: (p) => p === "/setup" },
    { to: "/dashboards", label: "Analytics Dashboards", icon: <LayoutDashboard size={16} />, match: (p) => p === "/dashboards" },
    { to: "/notebooks", label: "Notebooks", icon: <Code2 size={16} />, match: (p) => p === "/notebooks" },
  ];

  const riskItems: NavItem[] = [
    { to: "/declines", label: "Declines", icon: <BadgeX size={16} />, match: (p) => p === "/declines" },
    { to: "/smart-retry", label: "Smart Retry", icon: <RotateCcw size={16} />, match: (p) => p === "/smart-retry" },
    { to: "/reason-codes", label: "Reason Codes", icon: <ListChecks size={16} />, match: (p) => p === "/reason-codes" },
    { to: "/decisioning", label: "Decisioning", icon: <Wand2 size={16} />, match: (p) => p === "/decisioning" },
  ];

  const operationsItems: NavItem[] = [
    { to: "/models", label: "ML Models", icon: <Brain size={16} />, match: (p) => p === "/models" },
    { to: "/ai-agents", label: "AI Agents", icon: <Bot size={16} />, match: (p) => p === "/ai-agents" },
    { to: "/incidents", label: "Incidents", icon: <AlertTriangle size={16} />, match: (p) => p === "/incidents" },
    { to: "/experiments", label: "Experiments", icon: <FlaskConical size={16} />, match: (p) => p === "/experiments" },
    { to: "/smart-checkout", label: "Smart Checkout", icon: <CreditCard size={16} />, match: (p) => p === "/smart-checkout" },
    { to: "/rules", label: "Rules", icon: <ScrollText size={16} />, match: (p) => p === "/rules" },
  ];

  const settingsItems: NavItem[] = [
    { to: "/profile", label: "Profile", icon: <User size={16} />, match: (p) => p === "/profile" },
  ];

  return (
    <SidebarLayout>
      <SidebarGroup>
        <SidebarGroupLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-3 py-2">
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
      <SidebarGroup>
        <SidebarGroupLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-3 py-2">
          Risk
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {riskItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <NavLink item={item} isActive={item.match(location.pathname)} />
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarGroup>
        <SidebarGroupLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-3 py-2">
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
      <SidebarGroup>
        <SidebarGroupLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-3 py-2">
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
    </SidebarLayout>
  );
}
