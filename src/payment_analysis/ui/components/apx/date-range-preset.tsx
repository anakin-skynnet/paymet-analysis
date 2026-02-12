/**
 * Top-Bar date range preset (Global Payments Command Center).
 * Default: Brazil; date range drives analytics and dashboards.
 */
import { cn } from "@/lib/utils";
import { Calendar } from "lucide-react";

export type DateRangePreset = "7" | "30" | "90";

const PRESETS: { value: DateRangePreset; label: string }[] = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
];

export interface DateRangePresetSelectProps {
  value?: DateRangePreset;
  onChange?: (value: DateRangePreset) => void;
  className?: string;
  "aria-label"?: string;
}

export function DateRangePresetSelect({
  value = "30",
  onChange,
  className,
  "aria-label": ariaLabel = "Date range for reports",
}: DateRangePresetSelectProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Calendar className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden />
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value as DateRangePreset)}
        aria-label={ariaLabel}
        title="Filter reports by date range"
        className={cn(
          "flex h-9 min-w-[8rem] rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-[border-color,box-shadow] duration-200",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          "cursor-pointer appearance-none bg-[length:12px] bg-[right_0.5rem_center] bg-no-repeat pr-8",
          "bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 viewBox=%220 0 12 12%22%3E%3Cpath fill=%22%236b7280%22 d=%22M6 8L1 3h10z%22/%3E%3C/svg%3E')]",
        )}
      >
        {PRESETS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>
    </div>
  );
}
