import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface PageHeaderProps {
  /** Optional section label above the title (e.g. "Key metrics") */
  sectionLabel?: string;
  /** Main page title */
  title: string;
  /** Optional description below the title */
  description?: string;
  /** Optional actions (buttons, badges) on the right */
  actions?: ReactNode;
  /** Optional badge or status next to title */
  badge?: ReactNode;
  /** Optional id for the h1 (for anchor links or skip target) */
  titleId?: string;
  /** Extra class for the wrapper */
  className?: string;
}

export function PageHeader({
  sectionLabel,
  title,
  description,
  actions,
  badge,
  titleId,
  className,
}: PageHeaderProps) {
  return (
    <header className={cn("page-header space-y-2 min-w-0", className)}>
      {sectionLabel && (
        <p className="section-label text-muted-foreground" aria-hidden>
          {sectionLabel}
        </p>
      )}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <h1 id={titleId} className="page-section-title text-2xl md:text-3xl font-bold truncate">
              {title}
            </h1>
            {badge}
          </div>
          {description && (
            <p className="page-section-description max-w-2xl">{description}</p>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
      </div>
    </header>
  );
}

export default PageHeader;
