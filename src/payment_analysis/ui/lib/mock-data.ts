/**
 * Mock data for UI when backend is unavailable.
 * Types mirror backend Pydantic models (API client types from OpenAPI); keep in sync with backend schemas.
 * Use for fallback only; data is always fetched from backend first (useListDashboards, useGetKpisSuspense, etc.).
 */

import type { DashboardInfo, DashboardCategory } from "@/lib/api";
import { LAKEVIEW_DASHBOARD_IDS } from "@/config/workspace";

/** Mock category counts (mirrors DashboardList.categories from backend). Used with MOCK_DASHBOARDS when API fails. */
export const MOCK_DASHBOARD_CATEGORIES: Record<string, number> = {
  executive: 1,
  analytics: 1,
  technical: 1,
};

/** Mock dashboards list (mirrors DashboardList.dashboards from backend). Dashboard IDs sourced from LAKEVIEW_DASHBOARD_IDS. */
export const MOCK_DASHBOARDS: DashboardInfo[] = [
  {
    id: "data_quality_unified",
    name: "Data & Quality",
    description: "Stream ingestion, data quality, real-time monitoring, alerts, and country coverage.",
    category: "technical" as DashboardCategory,
    tags: ["streaming", "data-quality", "countries", "risks"],
    url_path: `/dashboardsv3/${LAKEVIEW_DASHBOARD_IDS.data_quality_unified}/published`,
  },
  {
    id: "ml_optimization_unified",
    name: "ML & Optimization",
    description: "Predictions, behavior, smart retry impact, smart checkout, routing, decline, fraud, 3DS, financial impact.",
    category: "analytics" as DashboardCategory,
    tags: ["ml", "predictions", "routing", "decline", "fraud", "approval-rates"],
    url_path: `/dashboardsv3/${LAKEVIEW_DASHBOARD_IDS.ml_optimization_unified}/published`,
  },
  {
    id: "executive_trends_unified",
    name: "Executive & Trends",
    description: "KPIs, approval rates, trends, merchant performance, and latency for business analysis.",
    category: "executive" as DashboardCategory,
    tags: ["kpi", "overview", "executive", "approval-rates"],
    url_path: `/dashboardsv3/${LAKEVIEW_DASHBOARD_IDS.executive_trends_unified}/published`,
  },
];
