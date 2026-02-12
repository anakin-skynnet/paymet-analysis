/**
 * Mock data for UI when backend is unavailable.
 * Types mirror backend Pydantic models (API client types from OpenAPI).
 * Use for fallback only; prefer fetching from backend via useListDashboards, useGetKpisSuspense, etc.
 */

import type { DashboardInfo, DashboardCategory } from "@/lib/api";

/** Mock dashboards list (mirrors DashboardList.dashboards from backend). */
export const MOCK_DASHBOARDS: DashboardInfo[] = [
  {
    id: "data_quality_unified",
    name: "Data & Quality",
    description: "Stream ingestion, data quality, real-time monitoring, alerts, and country coverage.",
    category: "technical" as DashboardCategory,
    tags: ["streaming", "data-quality", "countries", "risks"],
    url_path: "/sql/dashboards/data_quality_unified",
  },
  {
    id: "ml_optimization_unified",
    name: "ML & Optimization",
    description: "Predictions, behavior, smart retry impact, smart checkout, routing, decline, fraud, 3DS, financial impact.",
    category: "analytics" as DashboardCategory,
    tags: ["ml", "predictions", "routing", "decline", "fraud", "approval-rates"],
    url_path: "/sql/dashboards/ml_optimization_unified",
  },
  {
    id: "executive_trends_unified",
    name: "Executive & Trends",
    description: "KPIs, approval rates, trends, merchant performance, and latency for business analysis.",
    category: "executive" as DashboardCategory,
    tags: ["kpi", "overview", "executive", "approval-rates"],
    url_path: "/sql/dashboards/executive_trends_unified",
  },
];
