import { useQuery, useSuspenseQuery, useMutation } from "@tanstack/react-query";
import type { UseQueryOptions, UseSuspenseQueryOptions, UseMutationOptions } from "@tanstack/react-query";

export interface ApprovalPredictionOut {
  approval_probability: number;
  model_version: string;
  should_approve: boolean;
}

export interface ApprovalTrendOut {
  approval_rate_pct: number;
  approved_count: number;
  avg_fraud_score: number;
  hour: string;
  total_value: number;
  transaction_count: number;
}

export interface AssignIn {
  subject_key: string;
  variant: string;
}

export interface AuthDecisionOut {
  audit_id: string;
  path: AuthPath;
  reason: string;
  risk_tier: RiskTier;
}

export const AuthPath = {
  none: "none",
  "3ds_frictionless": "3ds_frictionless",
  "3ds_challenge": "3ds_challenge",
  passkey: "passkey",
} as const;

export type AuthPath = (typeof AuthPath)[keyof typeof AuthPath];

export interface AuthorizationEvent {
  amount_minor: number;
  attempt_number?: number;
  card_bin?: string | null;
  created_at?: string;
  currency: string;
  decline_code_raw?: string | null;
  decline_reason?: string | null;
  entry_mode?: string | null;
  id?: number | null;
  is_retry?: boolean;
  issuer_country?: string | null;
  merchant_id: string;
  network?: string | null;
  result: string;
}

export interface ComplexValue {
  display?: string | null;
  primary?: boolean | null;
  ref?: string | null;
  type?: string | null;
  value?: string | null;
}

export interface DatabricksKPIOut {
  approval_rate: number;
  avg_fraud_score: number;
  period_end: string;
  period_start: string;
  total_transactions: number;
  total_value: number;
}

export interface DecisionContext {
  amount_minor: number;
  attempt_number?: number;
  card_bin?: string | null;
  currency: string;
  device_trust_score?: number | null;
  entry_mode?: string | null;
  is_recurring?: boolean;
  issuer_country?: string | null;
  merchant_id: string;
  metadata?: Record<string, unknown>;
  network?: string | null;
  previous_decline_code?: string | null;
  previous_decline_reason?: string | null;
  risk_score?: number | null;
  supports_passkey?: boolean;
}

export interface DecisionLog {
  audit_id?: string;
  created_at?: string;
  decision_type: string;
  id?: number | null;
  request?: Record<string, unknown>;
  response?: Record<string, unknown>;
}

export interface DeclineBucketOut {
  count: number;
  key: string;
  pct_of_declines?: number | null;
  recoverable_pct?: number | null;
  total_value?: number | null;
}

export interface Experiment {
  created_at?: string;
  description?: string | null;
  ended_at?: string | null;
  id?: string;
  name: string;
  started_at?: string | null;
  status?: string;
}

export interface ExperimentAssignment {
  created_at?: string;
  experiment_id: string;
  id?: number | null;
  subject_key: string;
  variant: string;
}

export interface ExperimentIn {
  description?: string | null;
  name: string;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface Incident {
  category: string;
  created_at?: string;
  details?: Record<string, unknown>;
  id?: string;
  key: string;
  severity?: string;
  status?: string;
}

export interface IncidentIn {
  category: string;
  details?: Record<string, unknown>;
  key: string;
  severity?: string;
}

export interface KPIOut {
  approval_rate: number;
  approved: number;
  total: number;
}

export interface MLPredictionInput {
  amount: number;
  card_network?: string;
  device_trust_score?: number;
  fraud_score?: number;
  is_cross_border?: boolean;
  merchant_segment?: string;
  retry_count?: number;
  uses_3ds?: boolean;
}

export interface Name {
  family_name?: string | null;
  given_name?: string | null;
}

export interface RemediationTask {
  action?: string | null;
  created_at?: string;
  id?: string;
  incident_id?: string | null;
  owner?: string | null;
  status?: string;
  title: string;
}

export interface RetryDecisionOut {
  audit_id: string;
  max_attempts?: number;
  reason: string;
  retry_after_seconds?: number | null;
  should_retry: boolean;
}

export interface RiskPredictionOut {
  is_high_risk: boolean;
  risk_score: number;
  risk_tier: string;
}

export const RiskTier = {
  low: "low",
  medium: "medium",
  high: "high",
} as const;

export type RiskTier = (typeof RiskTier)[keyof typeof RiskTier];

export interface RoutingDecisionOut {
  audit_id: string;
  candidates: string[];
  primary_route: string;
  reason: string;
  should_cascade: boolean;
}

export interface RoutingPredictionOut {
  alternatives: string[];
  confidence: number;
  recommended_solution: string;
}

export interface SolutionPerformanceOut {
  approval_rate_pct: number;
  approved_count: number;
  avg_amount: number;
  payment_solution: string;
  total_value: number;
  transaction_count: number;
}

export interface TaskIn {
  action?: string | null;
  owner?: string | null;
  title: string;
}

export interface User {
  active?: boolean | null;
  display_name?: string | null;
  emails?: ComplexValue[] | null;
  entitlements?: ComplexValue[] | null;
  external_id?: string | null;
  groups?: ComplexValue[] | null;
  id?: string | null;
  name?: Name | null;
  roles?: ComplexValue[] | null;
  schemas?: UserSchema[] | null;
  user_name?: string | null;
}

export const UserSchema = {
  "urn:ietf:params:scim:schemas:core:2.0:User": "urn:ietf:params:scim:schemas:core:2.0:User",
  "urn:ietf:params:scim:schemas:extension:workspace:2.0:User": "urn:ietf:params:scim:schemas:extension:workspace:2.0:User",
} as const;

export type UserSchema = (typeof UserSchema)[keyof typeof UserSchema];

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface VersionOut {
  version: string;
}

export interface RecentDecisionsParams {
  limit?: number;
  decision_type?: string | null;
}

export interface DeclineSummaryParams {
  limit?: number;
}

export interface GetApprovalTrendsParams {
  hours?: number;
}

export interface CurrentUserParams {
  "X-Forwarded-Access-Token"?: string | null;
}

export interface ListExperimentsParams {
  limit?: number;
}

export interface AssignExperimentParams {
  experiment_id: string;
}

export interface ListExperimentAssignmentsParams {
  experiment_id: string;
  limit?: number;
}

export interface StartExperimentParams {
  experiment_id: string;
}

export interface StopExperimentParams {
  experiment_id: string;
}

export interface ListIncidentsParams {
  limit?: number;
  status?: string | null;
}

export interface ResolveIncidentParams {
  incident_id: string;
}

export interface ListRemediationTasksParams {
  incident_id: string;
  limit?: number;
}

export interface CreateRemediationTaskParams {
  incident_id: string;
}

export class ApiError extends Error {
  status: number;
  statusText: string;
  body: unknown;

  constructor(status: number, statusText: string, body: unknown) {
    super(`HTTP ${status}: ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

export const recentDecisions = async (params?: RecentDecisionsParams, options?: RequestInit): Promise<{ data: DecisionLog[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  if (params?.decision_type != null) searchParams.set("decision_type", String(params?.decision_type));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/decisions/recent?${queryString}` : `/api/analytics/decisions/recent`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const recentDecisionsKey = (params?: RecentDecisionsParams) => {
  return ["/api/analytics/decisions/recent", params] as const;
};

export function useRecentDecisions<TData = { data: DecisionLog[] }>(options?: { params?: RecentDecisionsParams; query?: Omit<UseQueryOptions<{ data: DecisionLog[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: recentDecisionsKey(options?.params), queryFn: () => recentDecisions(options?.params), ...options?.query });
}

export function useRecentDecisionsSuspense<TData = { data: DecisionLog[] }>(options?: { params?: RecentDecisionsParams; query?: Omit<UseSuspenseQueryOptions<{ data: DecisionLog[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: recentDecisionsKey(options?.params), queryFn: () => recentDecisions(options?.params), ...options?.query });
}

export const getDatabricksDeclines = async (options?: RequestInit): Promise<{ data: DeclineBucketOut[] }> => {
  const res = await fetch("/api/analytics/declines/databricks", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getDatabricksDeclinesKey = () => {
  return ["/api/analytics/declines/databricks"] as const;
};

export function useGetDatabricksDeclines<TData = { data: DeclineBucketOut[] }>(options?: { query?: Omit<UseQueryOptions<{ data: DeclineBucketOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getDatabricksDeclinesKey(), queryFn: () => getDatabricksDeclines(), ...options?.query });
}

export function useGetDatabricksDeclinesSuspense<TData = { data: DeclineBucketOut[] }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: DeclineBucketOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getDatabricksDeclinesKey(), queryFn: () => getDatabricksDeclines(), ...options?.query });
}

export const declineSummary = async (params?: DeclineSummaryParams, options?: RequestInit): Promise<{ data: DeclineBucketOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/declines/summary?${queryString}` : `/api/analytics/declines/summary`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const declineSummaryKey = (params?: DeclineSummaryParams) => {
  return ["/api/analytics/declines/summary", params] as const;
};

export function useDeclineSummary<TData = { data: DeclineBucketOut[] }>(options?: { params?: DeclineSummaryParams; query?: Omit<UseQueryOptions<{ data: DeclineBucketOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: declineSummaryKey(options?.params), queryFn: () => declineSummary(options?.params), ...options?.query });
}

export function useDeclineSummarySuspense<TData = { data: DeclineBucketOut[] }>(options?: { params?: DeclineSummaryParams; query?: Omit<UseSuspenseQueryOptions<{ data: DeclineBucketOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: declineSummaryKey(options?.params), queryFn: () => declineSummary(options?.params), ...options?.query });
}

export const ingestAuthEvent = async (data: AuthorizationEvent, options?: RequestInit): Promise<{ data: AuthorizationEvent }> => {
  const res = await fetch("/api/analytics/events", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useIngestAuthEvent(options?: { mutation?: UseMutationOptions<{ data: AuthorizationEvent }, ApiError, AuthorizationEvent> }) {
  return useMutation({ mutationFn: (data) => ingestAuthEvent(data), ...options?.mutation });
}

export const getKpis = async (options?: RequestInit): Promise<{ data: KPIOut }> => {
  const res = await fetch("/api/analytics/kpis", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getKpisKey = () => {
  return ["/api/analytics/kpis"] as const;
};

export function useGetKpis<TData = { data: KPIOut }>(options?: { query?: Omit<UseQueryOptions<{ data: KPIOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getKpisKey(), queryFn: () => getKpis(), ...options?.query });
}

export function useGetKpisSuspense<TData = { data: KPIOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: KPIOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getKpisKey(), queryFn: () => getKpis(), ...options?.query });
}

export const getDatabricksKpis = async (options?: RequestInit): Promise<{ data: DatabricksKPIOut }> => {
  const res = await fetch("/api/analytics/kpis/databricks", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getDatabricksKpisKey = () => {
  return ["/api/analytics/kpis/databricks"] as const;
};

export function useGetDatabricksKpis<TData = { data: DatabricksKPIOut }>(options?: { query?: Omit<UseQueryOptions<{ data: DatabricksKPIOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getDatabricksKpisKey(), queryFn: () => getDatabricksKpis(), ...options?.query });
}

export function useGetDatabricksKpisSuspense<TData = { data: DatabricksKPIOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: DatabricksKPIOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getDatabricksKpisKey(), queryFn: () => getDatabricksKpis(), ...options?.query });
}

export const getSolutionPerformance = async (options?: RequestInit): Promise<{ data: SolutionPerformanceOut[] }> => {
  const res = await fetch("/api/analytics/solutions", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getSolutionPerformanceKey = () => {
  return ["/api/analytics/solutions"] as const;
};

export function useGetSolutionPerformance<TData = { data: SolutionPerformanceOut[] }>(options?: { query?: Omit<UseQueryOptions<{ data: SolutionPerformanceOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getSolutionPerformanceKey(), queryFn: () => getSolutionPerformance(), ...options?.query });
}

export function useGetSolutionPerformanceSuspense<TData = { data: SolutionPerformanceOut[] }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: SolutionPerformanceOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getSolutionPerformanceKey(), queryFn: () => getSolutionPerformance(), ...options?.query });
}

export const getApprovalTrends = async (params?: GetApprovalTrendsParams, options?: RequestInit): Promise<{ data: ApprovalTrendOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.hours != null) searchParams.set("hours", String(params?.hours));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/trends?${queryString}` : `/api/analytics/trends`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getApprovalTrendsKey = (params?: GetApprovalTrendsParams) => {
  return ["/api/analytics/trends", params] as const;
};

export function useGetApprovalTrends<TData = { data: ApprovalTrendOut[] }>(options?: { params?: GetApprovalTrendsParams; query?: Omit<UseQueryOptions<{ data: ApprovalTrendOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getApprovalTrendsKey(options?.params), queryFn: () => getApprovalTrends(options?.params), ...options?.query });
}

export function useGetApprovalTrendsSuspense<TData = { data: ApprovalTrendOut[] }>(options?: { params?: GetApprovalTrendsParams; query?: Omit<UseSuspenseQueryOptions<{ data: ApprovalTrendOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getApprovalTrendsKey(options?.params), queryFn: () => getApprovalTrends(options?.params), ...options?.query });
}

export const currentUser = async (params?: CurrentUserParams, options?: RequestInit): Promise<{ data: User }> => {
  const res = await fetch("/api/current-user", { ...options, method: "GET", headers: { ...(params?.["X-Forwarded-Access-Token"] != null && { "X-Forwarded-Access-Token": params["X-Forwarded-Access-Token"] }), ...options?.headers } });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const currentUserKey = (params?: CurrentUserParams) => {
  return ["/api/current-user", params] as const;
};

export function useCurrentUser<TData = { data: User }>(options?: { params?: CurrentUserParams; query?: Omit<UseQueryOptions<{ data: User }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: currentUserKey(options?.params), queryFn: () => currentUser(options?.params), ...options?.query });
}

export function useCurrentUserSuspense<TData = { data: User }>(options?: { params?: CurrentUserParams; query?: Omit<UseSuspenseQueryOptions<{ data: User }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: currentUserKey(options?.params), queryFn: () => currentUser(options?.params), ...options?.query });
}

export const decideAuthentication = async (data: DecisionContext, options?: RequestInit): Promise<{ data: AuthDecisionOut }> => {
  const res = await fetch("/api/decision/authentication", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useDecideAuthentication(options?: { mutation?: UseMutationOptions<{ data: AuthDecisionOut }, ApiError, DecisionContext> }) {
  return useMutation({ mutationFn: (data) => decideAuthentication(data), ...options?.mutation });
}

export const predictApproval = async (data: MLPredictionInput, options?: RequestInit): Promise<{ data: ApprovalPredictionOut }> => {
  const res = await fetch("/api/decision/ml/approval", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function usePredictApproval(options?: { mutation?: UseMutationOptions<{ data: ApprovalPredictionOut }, ApiError, MLPredictionInput> }) {
  return useMutation({ mutationFn: (data) => predictApproval(data), ...options?.mutation });
}

export const predictRisk = async (data: MLPredictionInput, options?: RequestInit): Promise<{ data: RiskPredictionOut }> => {
  const res = await fetch("/api/decision/ml/risk", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function usePredictRisk(options?: { mutation?: UseMutationOptions<{ data: RiskPredictionOut }, ApiError, MLPredictionInput> }) {
  return useMutation({ mutationFn: (data) => predictRisk(data), ...options?.mutation });
}

export const predictRouting = async (data: MLPredictionInput, options?: RequestInit): Promise<{ data: RoutingPredictionOut }> => {
  const res = await fetch("/api/decision/ml/routing", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function usePredictRouting(options?: { mutation?: UseMutationOptions<{ data: RoutingPredictionOut }, ApiError, MLPredictionInput> }) {
  return useMutation({ mutationFn: (data) => predictRouting(data), ...options?.mutation });
}

export const decideRetry = async (data: DecisionContext, options?: RequestInit): Promise<{ data: RetryDecisionOut }> => {
  const res = await fetch("/api/decision/retry", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useDecideRetry(options?: { mutation?: UseMutationOptions<{ data: RetryDecisionOut }, ApiError, DecisionContext> }) {
  return useMutation({ mutationFn: (data) => decideRetry(data), ...options?.mutation });
}

export const decideRouting = async (data: DecisionContext, options?: RequestInit): Promise<{ data: RoutingDecisionOut }> => {
  const res = await fetch("/api/decision/routing", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useDecideRouting(options?: { mutation?: UseMutationOptions<{ data: RoutingDecisionOut }, ApiError, DecisionContext> }) {
  return useMutation({ mutationFn: (data) => decideRouting(data), ...options?.mutation });
}

export const listExperiments = async (params?: ListExperimentsParams, options?: RequestInit): Promise<{ data: Experiment[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/experiments?${queryString}` : `/api/experiments`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listExperimentsKey = (params?: ListExperimentsParams) => {
  return ["/api/experiments", params] as const;
};

export function useListExperiments<TData = { data: Experiment[] }>(options?: { params?: ListExperimentsParams; query?: Omit<UseQueryOptions<{ data: Experiment[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listExperimentsKey(options?.params), queryFn: () => listExperiments(options?.params), ...options?.query });
}

export function useListExperimentsSuspense<TData = { data: Experiment[] }>(options?: { params?: ListExperimentsParams; query?: Omit<UseSuspenseQueryOptions<{ data: Experiment[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listExperimentsKey(options?.params), queryFn: () => listExperiments(options?.params), ...options?.query });
}

export const createExperiment = async (data: ExperimentIn, options?: RequestInit): Promise<{ data: Experiment }> => {
  const res = await fetch("/api/experiments", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useCreateExperiment(options?: { mutation?: UseMutationOptions<{ data: Experiment }, ApiError, ExperimentIn> }) {
  return useMutation({ mutationFn: (data) => createExperiment(data), ...options?.mutation });
}

export const assignExperiment = async (params: AssignExperimentParams, data: AssignIn, options?: RequestInit): Promise<{ data: ExperimentAssignment }> => {
  const res = await fetch(`/api/experiments/${params.experiment_id}/assign`, { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useAssignExperiment(options?: { mutation?: UseMutationOptions<{ data: ExperimentAssignment }, ApiError, { params: AssignExperimentParams; data: AssignIn }> }) {
  return useMutation({ mutationFn: (vars) => assignExperiment(vars.params, vars.data), ...options?.mutation });
}

export const listExperimentAssignments = async (params: ListExperimentAssignmentsParams, options?: RequestInit): Promise<{ data: ExperimentAssignment[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/experiments/${params.experiment_id}/assignments?${queryString}` : `/api/experiments/${params.experiment_id}/assignments`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listExperimentAssignmentsKey = (params?: ListExperimentAssignmentsParams) => {
  return ["/api/experiments/{experiment_id}/assignments", params] as const;
};

export function useListExperimentAssignments<TData = { data: ExperimentAssignment[] }>(options: { params: ListExperimentAssignmentsParams; query?: Omit<UseQueryOptions<{ data: ExperimentAssignment[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listExperimentAssignmentsKey(options.params), queryFn: () => listExperimentAssignments(options.params), ...options?.query });
}

export function useListExperimentAssignmentsSuspense<TData = { data: ExperimentAssignment[] }>(options: { params: ListExperimentAssignmentsParams; query?: Omit<UseSuspenseQueryOptions<{ data: ExperimentAssignment[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listExperimentAssignmentsKey(options.params), queryFn: () => listExperimentAssignments(options.params), ...options?.query });
}

export const startExperiment = async (params: StartExperimentParams, options?: RequestInit): Promise<{ data: Experiment }> => {
  const res = await fetch(`/api/experiments/${params.experiment_id}/start`, { ...options, method: "POST" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useStartExperiment(options?: { mutation?: UseMutationOptions<{ data: Experiment }, ApiError, { params: StartExperimentParams }> }) {
  return useMutation({ mutationFn: (vars) => startExperiment(vars.params), ...options?.mutation });
}

export const stopExperiment = async (params: StopExperimentParams, options?: RequestInit): Promise<{ data: Experiment }> => {
  const res = await fetch(`/api/experiments/${params.experiment_id}/stop`, { ...options, method: "POST" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useStopExperiment(options?: { mutation?: UseMutationOptions<{ data: Experiment }, ApiError, { params: StopExperimentParams }> }) {
  return useMutation({ mutationFn: (vars) => stopExperiment(vars.params), ...options?.mutation });
}

export const listIncidents = async (params?: ListIncidentsParams, options?: RequestInit): Promise<{ data: Incident[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  if (params?.status != null) searchParams.set("status", String(params?.status));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/incidents?${queryString}` : `/api/incidents`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listIncidentsKey = (params?: ListIncidentsParams) => {
  return ["/api/incidents", params] as const;
};

export function useListIncidents<TData = { data: Incident[] }>(options?: { params?: ListIncidentsParams; query?: Omit<UseQueryOptions<{ data: Incident[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listIncidentsKey(options?.params), queryFn: () => listIncidents(options?.params), ...options?.query });
}

export function useListIncidentsSuspense<TData = { data: Incident[] }>(options?: { params?: ListIncidentsParams; query?: Omit<UseSuspenseQueryOptions<{ data: Incident[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listIncidentsKey(options?.params), queryFn: () => listIncidents(options?.params), ...options?.query });
}

export const createIncident = async (data: IncidentIn, options?: RequestInit): Promise<{ data: Incident }> => {
  const res = await fetch("/api/incidents", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useCreateIncident(options?: { mutation?: UseMutationOptions<{ data: Incident }, ApiError, IncidentIn> }) {
  return useMutation({ mutationFn: (data) => createIncident(data), ...options?.mutation });
}

export const resolveIncident = async (params: ResolveIncidentParams, options?: RequestInit): Promise<{ data: Incident }> => {
  const res = await fetch(`/api/incidents/${params.incident_id}/resolve`, { ...options, method: "POST" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useResolveIncident(options?: { mutation?: UseMutationOptions<{ data: Incident }, ApiError, { params: ResolveIncidentParams }> }) {
  return useMutation({ mutationFn: (vars) => resolveIncident(vars.params), ...options?.mutation });
}

export const listRemediationTasks = async (params: ListRemediationTasksParams, options?: RequestInit): Promise<{ data: RemediationTask[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/incidents/${params.incident_id}/tasks?${queryString}` : `/api/incidents/${params.incident_id}/tasks`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listRemediationTasksKey = (params?: ListRemediationTasksParams) => {
  return ["/api/incidents/{incident_id}/tasks", params] as const;
};

export function useListRemediationTasks<TData = { data: RemediationTask[] }>(options: { params: ListRemediationTasksParams; query?: Omit<UseQueryOptions<{ data: RemediationTask[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listRemediationTasksKey(options.params), queryFn: () => listRemediationTasks(options.params), ...options?.query });
}

export function useListRemediationTasksSuspense<TData = { data: RemediationTask[] }>(options: { params: ListRemediationTasksParams; query?: Omit<UseSuspenseQueryOptions<{ data: RemediationTask[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listRemediationTasksKey(options.params), queryFn: () => listRemediationTasks(options.params), ...options?.query });
}

export const createRemediationTask = async (params: CreateRemediationTaskParams, data: TaskIn, options?: RequestInit): Promise<{ data: RemediationTask }> => {
  const res = await fetch(`/api/incidents/${params.incident_id}/tasks`, { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useCreateRemediationTask(options?: { mutation?: UseMutationOptions<{ data: RemediationTask }, ApiError, { params: CreateRemediationTaskParams; data: TaskIn }> }) {
  return useMutation({ mutationFn: (vars) => createRemediationTask(vars.params, vars.data), ...options?.mutation });
}

export const version = async (options?: RequestInit): Promise<{ data: VersionOut }> => {
  const res = await fetch("/api/version", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const versionKey = () => {
  return ["/api/version"] as const;
};

export function useVersion<TData = { data: VersionOut }>(options?: { query?: Omit<UseQueryOptions<{ data: VersionOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: versionKey(), queryFn: () => version(), ...options?.query });
}

export function useVersionSuspense<TData = { data: VersionOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: VersionOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: versionKey(), queryFn: () => version(), ...options?.query });
}

