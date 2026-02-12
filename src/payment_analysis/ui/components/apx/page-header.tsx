import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Page header: icon + title + description. Use variant="executive" for larger, CEO-facing pages. */
export function PageHeader({
  icon,
  title,
  description,
  actions,
  variant = "default",
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  actions?: ReactNode;
  variant?: "default" | "executive";
  className?: string;
}) {
  const isExecutive = variant === "executive";
  return (
    <div
      className={cn(
        "flex flex-wrap items-start justify-between gap-4",
        isExecutive && "pb-1",
        className
      )}
    >
      <div className="flex gap-3 min-w-0">
        {icon != null && (
          <span
            className={cn(
              "flex-shrink-0 text-primary",
              isExecutive ? "[&>svg]:w-9 [&>svg]:h-9" : "[&>svg]:w-8 [&>svg]:h-8"
            )}
            aria-hidden
          >
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <h1
            className={cn(
              "font-bold tracking-tight font-heading",
              isExecutive ? "text-2xl md:text-4xl" : "text-2xl md:text-3xl"
            )}
          >
            {title}
          </h1>
          {description != null && (
            <p
              className={cn(
                "text-muted-foreground mt-1",
                isExecutive ? "text-sm md:text-lg max-w-2xl" : "text-sm md:text-base"
              )}
            >
              {description}
            </p>
          )}
        </div>
      </div>
      {actions != null && <div className="flex shrink-0 gap-2">{actions}</div>}
    </div>
  );
}
