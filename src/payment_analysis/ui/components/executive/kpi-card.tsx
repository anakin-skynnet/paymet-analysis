import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface KPICardProps {
  /** Label above the value (e.g. "Gross Approval Rate") */
  label: string;
  /** Main value to display (e.g. "87.2%" or "—") */
  value: string | number;
  /** Optional icon shown next to label */
  icon?: ReactNode;
  /** Accent: "primary" (Getnet red), "success", "warning", "muted" */
  accent?: "primary" | "success" | "warning" | "muted";
  /** Optional subtitle or trend below value */
  subtitle?: string;
  /** Extra class for the card */
  className?: string;
}

const accentStyles = {
  primary:
    "border-[var(--getnet-red)]/40 bg-[var(--getnet-red)]/10 dark:bg-[var(--getnet-red)]/15 [--kpi-accent:var(--getnet-red)]",
  success:
    "border-[var(--vibrant-green)]/40 bg-[var(--vibrant-green)]/10 dark:bg-[var(--vibrant-green)]/15 [--kpi-accent:var(--vibrant-green)]",
  warning:
    "border-orange-500/50 bg-orange-500/10 dark:bg-orange-500/15 [--kpi-accent:var(--tw-color-orange-500)]",
  muted:
    "border-[var(--neon-cyan)]/40 bg-[var(--neon-cyan)]/5 dark:bg-[var(--neon-cyan)]/10 [--kpi-accent:var(--neon-cyan)]",
};

export function KPICard({
  label,
  value,
  icon,
  accent = "primary",
  subtitle,
  className,
}: KPICardProps) {
  return (
    <Card
      className={cn(
        "glass-card border-2 transition-smooth kpi-card",
        accentStyles[accent],
        className
      )}
      aria-label={`${label}: ${value}`}
    >
      <CardContent className="pt-6 pb-5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-muted-foreground">
            {label}
          </span>
          {icon != null && (
            <span
              className="shrink-0 [&>svg]:size-4"
              style={{ color: "var(--kpi-accent)" }}
              aria-hidden
            >
              {icon}
            </span>
          )}
        </div>
        <p
          className="mt-2 text-4xl font-bold kpi-number font-heading tabular-nums"
          style={{ color: "var(--kpi-accent)" }}
        >
          {value}
        </p>
        {subtitle != null && (
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}
