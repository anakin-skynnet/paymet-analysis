/**
 * Mock data for Global Payments Command Center.
 * Simulates Databricks SQL Warehouse with standardized Reason Code taxonomy
 * and country filter (WHERE country = ?). Use for UI when live API is unavailable.
 */

export type ReasonCodeCategory = "Antifraud" | "Technical" | "Issuer Decline";

export interface ReasonCodeSummary {
  category: ReasonCodeCategory;
  count: number;
  pct: number;
}

export interface EntrySystemPoint {
  ts: string;
  PD: number;
  WS: number;
  SEP: number;
  Checkout: number;
}

export interface FrictionFunnelStep {
  label: string;
  value: number;
  pct: number;
}

export interface RetryRecurrenceRow {
  type: "scheduled_recurrence" | "manual_retry";
  label: string;
  volume: number;
  pct: number;
}

const ENTRY_SHARES = { PD: 0.62, WS: 0.34, SEP: 0.03, Checkout: 0.01 } as const;

function genTimeSeries(minutes: number, baseTps: number): EntrySystemPoint[] {
  const points: EntrySystemPoint[] = [];
  const now = Date.now();
  for (let i = minutes; i >= 0; i--) {
    const t = new Date(now - i * 60 * 1000);
    const jitter = 0.9 + Math.random() * 0.2;
    const total = Math.round(baseTps * jitter * (1 + Math.sin(i / 5) * 0.1));
    points.push({
      ts: t.toISOString(),
      PD: Math.round(total * ENTRY_SHARES.PD),
      WS: Math.round(total * ENTRY_SHARES.WS),
      SEP: Math.round(total * ENTRY_SHARES.SEP),
      Checkout: Math.round(total * ENTRY_SHARES.Checkout),
    });
  }
  return points;
}

/** Gross Approval Rate (benchmark 73%), False Decline Rate, Data Quality Health — by country */
export function getCommandCenterKpis(countryCode: string): {
  grossApprovalRatePct: number;
  falseDeclineRatePct: number;
  dataQualityHealthPct: number;
} {
  const seed = countryCode === "BR" ? 0.73 : countryCode === "MX" ? 0.71 : 0.69;
  return {
    grossApprovalRatePct: Math.round(seed * 100) / 100,
    falseDeclineRatePct: Math.round((1 - seed) * 4.2 * 10) / 10,
    dataQualityHealthPct: countryCode === "BR" ? 98 : 96,
  };
}

/** Real-time throughput by entry system (PD 62%, WS 34%, SEP 3%, Checkout 1%) — last N minutes */
export function getEntrySystemThroughput(countryCode: string, limitMinutes: number = 30): EntrySystemPoint[] {
  const baseTps = countryCode === "BR" ? 420 : countryCode === "MX" ? 180 : 90;
  return genTimeSeries(limitMinutes, baseTps);
}

/** 3DS Friction Funnel: Total → 80% Friction → 60% Auth → 80% Approved */
export function getFrictionFunnel(countryCode: string): FrictionFunnelStep[] {
  const total = countryCode === "BR" ? 100000 : countryCode === "MX" ? 45000 : 20000;
  const friction = Math.round(total * 0.8);
  const auth = Math.round(friction * 0.6);
  const approved = Math.round(auth * 0.8);
  return [
    { label: "Total", value: total, pct: 100 },
    { label: "Friction", value: friction, pct: 80 },
    { label: "Auth", value: auth, pct: 60 },
    { label: "Approved", value: approved, pct: 80 },
  ];
}

/** Reason Code taxonomy: Antifraud, Technical, Issuer Decline */
export function getReasonCodeSummary(countryCode: string): ReasonCodeSummary[] {
  const byCountry: Record<string, ReasonCodeSummary[]> = {
    BR: [
      { category: "Antifraud", count: 1200, pct: 28 },
      { category: "Technical", count: 1800, pct: 42 },
      { category: "Issuer Decline", count: 1200, pct: 30 },
    ],
    MX: [
      { category: "Antifraud", count: 420, pct: 26 },
      { category: "Technical", count: 720, pct: 44 },
      { category: "Issuer Decline", count: 480, pct: 30 },
    ],
    AR: [
      { category: "Antifraud", count: 180, pct: 24 },
      { category: "Technical", count: 380, pct: 50 },
      { category: "Issuer Decline", count: 200, pct: 26 },
    ],
  };
  return byCountry[countryCode] ?? byCountry.BR;
}

/** False Insights: % of AI-generated recommendations marked non-actionable by domain specialists (Learning Loop) */
export function getFalseInsightsPct(countryCode: string): number {
  const seed = countryCode === "BR" ? 12 : countryCode === "MX" ? 14 : 16;
  return seed;
}

/** Retry & Recurrence: Scheduled (subscriptions) vs Manual (reattempts) — deduplicated for volume */
export function getRetryRecurrence(countryCode: string): RetryRecurrenceRow[] {
  const scheduled = countryCode === "BR" ? 8500 : countryCode === "MX" ? 3200 : 1400;
  const manual = countryCode === "BR" ? 4200 : countryCode === "MX" ? 1800 : 800;
  const total = scheduled + manual;
  return [
    { type: "scheduled_recurrence", label: "Scheduled Recurrence", volume: scheduled, pct: Math.round((scheduled / total) * 100) },
    { type: "manual_retry", label: "Manual Retry", volume: manual, pct: Math.round((manual / total) * 100) },
  ];
}

/** Entry gate telemetry path labels */
export const ENTRY_GATE_PATH = ["Checkout BR", "PD", "WS", "Base24", "Issuer"] as const;

/** Simulated latency/throughput per gate (for visualization) */
export function getEntryGateTelemetry(_countryCode: string): { gate: string; throughputPct: number; latencyMs: number }[] {
  return [
    { gate: "Checkout BR", throughputPct: 100, latencyMs: 45 },
    { gate: "PD", throughputPct: 62, latencyMs: 120 },
    { gate: "WS", throughputPct: 34, latencyMs: 95 },
    { gate: "Base24", throughputPct: 28, latencyMs: 180 },
    { gate: "Issuer", throughputPct: 22, latencyMs: 320 },
  ];
}
