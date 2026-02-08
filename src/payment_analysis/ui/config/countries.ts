/**
 * Default entity/country and fallback list when the Lakehouse countries table
 * is unavailable. The dropdown is populated from GET /api/analytics/countries
 * (Lakehouse table); this file provides defaults only.
 */

export interface CountryRow {
  code: string;
  name: string;
}

/** Default entity code when none is stored (e.g. BR). */
export const DEFAULT_ENTITY_CODE = "BR";

/** Fallback when API fails or table is empty so the dropdown still works. */
export const FALLBACK_COUNTRIES: CountryRow[] = [
  { code: "BR", name: "Brazil" },
  { code: "MX", name: "Mexico" },
  { code: "AR", name: "Argentina" },
];
