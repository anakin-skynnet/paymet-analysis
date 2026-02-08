import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { DEFAULT_ENTITY_CODE, FALLBACK_COUNTRIES } from "@/config/countries";
import { useEntity } from "@/contexts/entity-context";
import { useGetCountries } from "@/lib/api";
import { Globe } from "lucide-react";

/** Cache countries list for 5 minutes; list is editable in Lakehouse and doesn't change per request. */
const COUNTRIES_STALE_MS = 5 * 60 * 1000;

export function CountrySelect({ className }: { className?: string }) {
  const { entity, setEntity } = useEntity();
  const { data, isLoading } = useGetCountries({
    query: { staleTime: COUNTRIES_STALE_MS },
  });
  const options = data?.data?.length ? data.data : FALLBACK_COUNTRIES;
  const entityInList = options.some((c) => c.code === entity);
  const selectedCode = entityInList ? entity : DEFAULT_ENTITY_CODE;

  // When the loaded list no longer contains the stored entity (e.g. row removed in Lakehouse), reset to default.
  useEffect(() => {
    if (!isLoading && !entityInList && selectedCode === DEFAULT_ENTITY_CODE) {
      setEntity(DEFAULT_ENTITY_CODE);
    }
  }, [isLoading, entityInList, selectedCode, setEntity]);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Globe className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden />
      <select
        value={selectedCode}
        onChange={(e) => setEntity(e.target.value)}
        disabled={isLoading}
        aria-label="Select country or entity to filter reports"
        title="Filter reports and data by country or entity"
        className={cn(
          "flex h-9 min-w-[7rem] sm:min-w-[140px] rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-[border-color,box-shadow] duration-200",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "cursor-pointer appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 viewBox=%220 0 12 12%22%3E%3Cpath fill=%22%236b7280%22 d=%22M6 8L1 3h10z%22/%3E%3C/svg%3E')] bg-[length:12px] bg-[right_0.5rem_center] bg-no-repeat pr-8",
          className,
        )}
      >
        {options.map(({ code, name }) => (
          <option key={code} value={code}>
            {name} ({code})
          </option>
        ))}
      </select>
    </div>
  );
}
