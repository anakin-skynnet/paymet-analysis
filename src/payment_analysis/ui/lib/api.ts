import { useQuery, useSuspenseQuery, useMutation } from "@tanstack/react-query";
import type { UseQueryOptions, UseSuspenseQueryOptions, UseMutationOptions } from "@tanstack/react-query";

export const AgentCapability = {
  natural_language_analytics: "natural_language_analytics",
  predictive_scoring: "predictive_scoring",
  conversational_insights: "conversational_insights",
  automated_recommendations: "automated_recommendations",
  real_time_decisioning: "real_time_decisioning",
} as const;

export type AgentCapability = (typeof AgentCapability)[keyof typeof AgentCapability];

export interface AgentInfo {
  agent_type: AgentType;
  capabilities: AgentCapability[];
  databricks_resource: string;
  description: string;
  example_queries?: string[];
  id: string;
  name: string;
  tags?: string[];
  use_case: string;
  workspace_url?: string | null;
}

export interface AgentList {
  agents: AgentInfo[];
  by_type: Record<string, number>;
  total: number;
}

export const AgentType = {
  genie: "genie",
  model_serving: "model_serving",
  custom_llm: "custom_llm",
  ai_gateway: "ai_gateway",
} as const;

export type AgentType = (typeof AgentType)[keyof typeof AgentType];

export interface AgentUrlOut {
  agent_id: string;
  agent_type: string;
  databricks_resource?: string | null;
  name: string;
  url: string;
}

export interface ApprovalPredictionOut {
  approval_probability: number;
  model_version: string;
  should_approve: boolean;
}

export interface ApprovalRuleIn {
  action_summary: string;
  condition_expression?: string | null;
  is_active?: boolean;
  name: string;
  priority?: number;
  rule_type: string;
}

export interface ApprovalRuleOut {
  action_summary: string;
  condition_expression?: string | null;
  created_at?: string | null;
  id: string;
  is_active: boolean;
  name: string;
  priority: number;
  rule_type: string;
  updated_at?: string | null;
}

export interface ApprovalRuleUpdate {
  action_summary?: string | null;
  condition_expression?: string | null;
  is_active?: boolean | null;
  name?: string | null;
  priority?: number | null;
  rule_type?: string | null;
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
  experiment_id?: string | null;
  path: AuthPath;
  reason: string;
  risk_tier: RiskTier;
  variant?: string | null;
}

export const AuthPath = {
  none: "none",
  "3ds_frictionless": "3ds_frictionless",
  "3ds_challenge": "3ds_challenge",
  passkey: "passkey",
} as const;

export type AuthPath = (typeof AuthPath)[keyof typeof AuthPath];

export interface AuthStatusOut {
  authenticated: boolean;
}

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

export interface CountryOut {
  code: string;
  name: string;
}

export const DashboardCategory = {
  executive: "executive",
  operations: "operations",
  analytics: "analytics",
  technical: "technical",
} as const;

export type DashboardCategory = (typeof DashboardCategory)[keyof typeof DashboardCategory];

export interface DashboardInfo {
  category: DashboardCategory;
  description: string;
  embed_url?: string | null;
  id: string;
  name: string;
  tags?: string[];
  url_path?: string | null;
}

export interface DashboardList {
  categories: Record<string, number>;
  dashboards: DashboardInfo[];
  total: number;
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
  experiment_id?: string | null;
  is_recurring?: boolean;
  issuer_country?: string | null;
  merchant_id: string;
  metadata?: Record<string, unknown>;
  network?: string | null;
  previous_decline_code?: string | null;
  previous_decline_reason?: string | null;
  risk_score?: number | null;
  subject_key?: string | null;
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

export interface DedupCollisionStatsOut {
  avg_entry_systems_per_key: number;
  avg_rows_per_key: number;
  avg_transaction_ids_per_key: number;
  colliding_keys: number;
}

export interface EntrySystemDistributionOut {
  approval_rate_pct: number;
  approved_count: number;
  entry_system: string;
  total_value: number;
  transaction_count: number;
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

export interface FalseInsightsMetricOut {
  event_date: string;
  false_insights: number;
  false_insights_pct?: number | null;
  reviewed_insights: number;
}

export interface FolderUrlOut {
  folder_id: string;
  url: string;
  workspace_path: string;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface HealthDatabaseOut {
  connection_healthy: boolean;
  database_instance_exists: boolean;
  status: string;
}

export interface HealthcheckOut {
  status: string;
  timestamp: string;
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

export interface InsightFeedbackIn {
  insight_id: string;
  insight_type: string;
  model_version?: string | null;
  prompt_version?: string | null;
  reason?: string | null;
  reviewer?: string | null;
  verdict: string;
}

export interface InsightFeedbackOut {
  accepted: boolean;
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

export interface ModelMetricOut {
  name: string;
  value: string;
}

export interface ModelOut {
  catalog_path: string;
  description: string;
  features: string[];
  id: string;
  metrics?: ModelMetricOut[];
  model_type: string;
  name: string;
}

export interface Name {
  family_name?: string | null;
  given_name?: string | null;
}

export const NotebookCategory = {
  intelligence: "intelligence",
  ml_training: "ml_training",
  streaming: "streaming",
  transformation: "transformation",
  analytics: "analytics",
} as const;

export type NotebookCategory = (typeof NotebookCategory)[keyof typeof NotebookCategory];

export interface NotebookInfo {
  category: NotebookCategory;
  description: string;
  documentation_url?: string | null;
  id: string;
  job_name?: string | null;
  name: string;
  tags?: string[];
  workspace_path: string;
}

export interface NotebookList {
  by_category: Record<string, number>;
  notebooks: NotebookInfo[];
  total: number;
}

export interface NotebookUrlOut {
  category: string;
  name: string;
  notebook_id: string;
  url: string;
  workspace_path: string;
}

export interface OnlineFeatureOut {
  created_at?: string | null;
  entity_id?: string | null;
  feature_name: string;
  feature_set?: string | null;
  feature_value?: number | null;
  feature_value_str?: string | null;
  id: string;
  source: string;
}

export interface ReasonCodeInsightOut {
  decline_count: number;
  decline_reason_group: string;
  decline_reason_standard: string;
  entry_system: string;
  estimated_recoverable_declines: number;
  estimated_recoverable_value: number;
  flow_type: string;
  pct_of_declines?: number | null;
  priority: number;
  recommended_action: string;
  total_declined_value: number;
}

export interface ReasonCodeOut {
  affected_merchants: number;
  avg_amount: number;
  decline_count: number;
  decline_reason_group: string;
  decline_reason_standard: string;
  entry_system: string;
  flow_type: string;
  pct_of_declines?: number | null;
  recommended_action: string;
  total_declined_value: number;
}

export interface RecommendationOut {
  context_summary: string;
  created_at?: string | null;
  id: string;
  recommended_action: string;
  score: number;
  source_type: string;
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
  experiment_id?: string | null;
  max_attempts?: number;
  reason: string;
  retry_after_seconds?: number | null;
  should_retry: boolean;
  variant?: string | null;
}

export interface RetryPerformanceOut {
  avg_fraud_score: number;
  avg_prior_approvals?: number | null;
  avg_time_since_last_attempt_s?: number | null;
  baseline_approval_pct?: number | null;
  decline_reason_standard: string;
  effectiveness: string;
  incremental_lift_pct?: number | null;
  recovered_value: number;
  retry_attempts: number;
  retry_count: number;
  retry_scenario: string;
  success_rate_pct: number;
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
  experiment_id?: string | null;
  primary_route: string;
  reason: string;
  should_cascade: boolean;
  variant?: string | null;
}

export interface RoutingPredictionOut {
  alternatives: string[];
  confidence: number;
  recommended_solution: string;
}

export interface RunJobIn {
  catalog?: string | null;
  duration_minutes?: string | null;
  events_per_second?: string | null;
  job_id: string;
  schema?: string | null;
  warehouse_id?: string | null;
}

export interface RunJobOut {
  job_id: string;
  message: string;
  run_id: number;
  run_page_url: string;
}

export interface RunPipelineIn {
  pipeline_id: string;
}

export interface RunPipelineOut {
  message: string;
  pipeline_id: string;
  pipeline_page_url: string;
  update_id: string;
}

export interface SetupConfigIn {
  catalog: string;
  schema: string;
}

export interface SetupConfigOut {
  catalog: string;
  schema: string;
}

export interface SetupDefaultsOut {
  catalog: string;
  jobs: Record<string, string>;
  pipelines: Record<string, string>;
  schema: string;
  token_received?: boolean;
  warehouse_id: string;
  workspace_host: string;
  workspace_id?: string;
  workspace_url_derived?: boolean;
}

export interface SetupSettingsOut {
  settings?: Record<string, string>;
}

export interface SmartCheckoutPathPerformanceOut {
  approval_rate_pct: number;
  approved_count: number;
  recommended_path: string;
  total_value: number;
  transaction_count: number;
}

export interface SmartCheckoutServicePathOut {
  antifraud_declines: number;
  antifraud_pct_of_declines?: number | null;
  approval_rate_pct: number;
  approved_count: number;
  avg_fraud_score: number;
  service_path: string;
  total_value: number;
  transaction_count: number;
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

export interface ThreeDSFunnelOut {
  event_date: string;
  issuer_approval_post_auth_rate_pct?: number | null;
  issuer_approved_after_auth_count: number;
  three_ds_authenticated_count: number;
  three_ds_authentication_rate_pct?: number | null;
  three_ds_friction_count: number;
  three_ds_friction_rate_pct?: number | null;
  three_ds_routed_count: number;
  total_transactions: number;
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

export interface WorkspaceConfigOut {
  workspace_url: string;
}

export interface ListAgentsParams {
  agent_type?: AgentType | null;
  entity?: string | null;
}

export interface GetAgentParams {
  agent_id: string;
}

export interface GetAgentUrlParams {
  agent_id: string;
}

export interface GetCountriesParams {
  limit?: number;
}

export interface RecentDecisionsParams {
  limit?: number;
  decision_type?: string | null;
}

export interface DeclineSummaryParams {
  limit?: number;
}

export interface GetFactorsDelayingApprovalParams {
  entity?: string;
  limit?: number;
}

export interface GetFalseInsightsMetricParams {
  days?: number;
}

export interface GetModelsParams {
  entity?: string;
}

export interface GetOnlineFeaturesParams {
  source?: string | null;
  limit?: number;
}

export interface GetReasonCodesParams {
  entity?: string;
  limit?: number;
}

export interface GetEntrySystemDistributionParams {
  entity?: string;
}

export interface GetReasonCodeInsightsParams {
  entity?: string;
  limit?: number;
}

export interface GetRecommendationsParams {
  limit?: number;
}

export interface GetRetryPerformanceParams {
  limit?: number;
}

export interface GetThreeDsFunnelParams {
  entity?: string;
  days?: number;
}

export interface GetSmartCheckoutPathPerformanceParams {
  entity?: string;
  limit?: number;
}

export interface GetSmartCheckoutServicePathsParams {
  entity?: string;
  limit?: number;
}

export interface GetApprovalTrendsParams {
  hours?: number;
}

export interface ListDashboardsParams {
  category?: DashboardCategory | null;
  tag?: string | null;
}

export interface GetDashboardParams {
  dashboard_id: string;
}

export interface GetDashboardUrlParams {
  dashboard_id: string;
  embed?: boolean;
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

export interface ListNotebooksParams {
  category?: NotebookCategory | null;
}

export interface GetNotebookFolderUrlParams {
  folder_id: string;
}

export interface GetNotebookParams {
  notebook_id: string;
}

export interface GetNotebookUrlParams {
  notebook_id: string;
}

export interface ListApprovalRulesParams {
  rule_type?: string | null;
  active_only?: boolean;
  limit?: number;
}

export interface UpdateApprovalRuleParams {
  rule_id: string;
}

export interface DeleteApprovalRuleParams {
  rule_id: string;
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

export const listAgents = async (params?: ListAgentsParams, options?: RequestInit): Promise<{ data: AgentList }> => {
  const searchParams = new URLSearchParams();
  if (params?.agent_type != null) searchParams.set("agent_type", String(params?.agent_type));
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/agents/agents?${queryString}` : `/api/agents/agents`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listAgentsKey = (params?: ListAgentsParams) => {
  return ["/api/agents/agents", params] as const;
};

export function useListAgents<TData = { data: AgentList }>(options?: { params?: ListAgentsParams; query?: Omit<UseQueryOptions<{ data: AgentList }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listAgentsKey(options?.params), queryFn: () => listAgents(options?.params), ...options?.query });
}

export function useListAgentsSuspense<TData = { data: AgentList }>(options?: { params?: ListAgentsParams; query?: Omit<UseSuspenseQueryOptions<{ data: AgentList }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listAgentsKey(options?.params), queryFn: () => listAgents(options?.params), ...options?.query });
}

export const getAgentTypeSummary = async (options?: RequestInit): Promise<{ data: Record<string, unknown> }> => {
  const res = await fetch("/api/agents/agents/types/summary", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getAgentTypeSummaryKey = () => {
  return ["/api/agents/agents/types/summary"] as const;
};

export function useGetAgentTypeSummary<TData = { data: Record<string, unknown> }>(options?: { query?: Omit<UseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getAgentTypeSummaryKey(), queryFn: () => getAgentTypeSummary(), ...options?.query });
}

export function useGetAgentTypeSummarySuspense<TData = { data: Record<string, unknown> }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getAgentTypeSummaryKey(), queryFn: () => getAgentTypeSummary(), ...options?.query });
}

export const getAgent = async (params: GetAgentParams, options?: RequestInit): Promise<{ data: AgentInfo }> => {
  const res = await fetch(`/api/agents/agents/${params.agent_id}`, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getAgentKey = (params?: GetAgentParams) => {
  return ["/api/agents/agents/{agent_id}", params] as const;
};

export function useGetAgent<TData = { data: AgentInfo }>(options: { params: GetAgentParams; query?: Omit<UseQueryOptions<{ data: AgentInfo }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getAgentKey(options.params), queryFn: () => getAgent(options.params), ...options?.query });
}

export function useGetAgentSuspense<TData = { data: AgentInfo }>(options: { params: GetAgentParams; query?: Omit<UseSuspenseQueryOptions<{ data: AgentInfo }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getAgentKey(options.params), queryFn: () => getAgent(options.params), ...options?.query });
}

export const getAgentUrl = async (params: GetAgentUrlParams, options?: RequestInit): Promise<{ data: AgentUrlOut }> => {
  const res = await fetch(`/api/agents/agents/${params.agent_id}/url`, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getAgentUrlKey = (params?: GetAgentUrlParams) => {
  return ["/api/agents/agents/{agent_id}/url", params] as const;
};

export function useGetAgentUrl<TData = { data: AgentUrlOut }>(options: { params: GetAgentUrlParams; query?: Omit<UseQueryOptions<{ data: AgentUrlOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getAgentUrlKey(options.params), queryFn: () => getAgentUrl(options.params), ...options?.query });
}

export function useGetAgentUrlSuspense<TData = { data: AgentUrlOut }>(options: { params: GetAgentUrlParams; query?: Omit<UseSuspenseQueryOptions<{ data: AgentUrlOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getAgentUrlKey(options.params), queryFn: () => getAgentUrl(options.params), ...options?.query });
}

export const getCountries = async (params?: GetCountriesParams, options?: RequestInit): Promise<{ data: CountryOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/countries?${queryString}` : `/api/analytics/countries`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getCountriesKey = (params?: GetCountriesParams) => {
  return ["/api/analytics/countries", params] as const;
};

export function useGetCountries<TData = { data: CountryOut[] }>(options?: { params?: GetCountriesParams; query?: Omit<UseQueryOptions<{ data: CountryOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getCountriesKey(options?.params), queryFn: () => getCountries(options?.params), ...options?.query });
}

export function useGetCountriesSuspense<TData = { data: CountryOut[] }>(options?: { params?: GetCountriesParams; query?: Omit<UseSuspenseQueryOptions<{ data: CountryOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getCountriesKey(options?.params), queryFn: () => getCountries(options?.params), ...options?.query });
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

export const getFactorsDelayingApproval = async (params?: GetFactorsDelayingApprovalParams, options?: RequestInit): Promise<{ data: ReasonCodeInsightOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/factors-delaying-approval?${queryString}` : `/api/analytics/factors-delaying-approval`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getFactorsDelayingApprovalKey = (params?: GetFactorsDelayingApprovalParams) => {
  return ["/api/analytics/factors-delaying-approval", params] as const;
};

export function useGetFactorsDelayingApproval<TData = { data: ReasonCodeInsightOut[] }>(options?: { params?: GetFactorsDelayingApprovalParams; query?: Omit<UseQueryOptions<{ data: ReasonCodeInsightOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getFactorsDelayingApprovalKey(options?.params), queryFn: () => getFactorsDelayingApproval(options?.params), ...options?.query });
}

export function useGetFactorsDelayingApprovalSuspense<TData = { data: ReasonCodeInsightOut[] }>(options?: { params?: GetFactorsDelayingApprovalParams; query?: Omit<UseSuspenseQueryOptions<{ data: ReasonCodeInsightOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getFactorsDelayingApprovalKey(options?.params), queryFn: () => getFactorsDelayingApproval(options?.params), ...options?.query });
}

export const getFalseInsightsMetric = async (params?: GetFalseInsightsMetricParams, options?: RequestInit): Promise<{ data: FalseInsightsMetricOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.days != null) searchParams.set("days", String(params?.days));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/insights/false-insights?${queryString}` : `/api/analytics/insights/false-insights`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getFalseInsightsMetricKey = (params?: GetFalseInsightsMetricParams) => {
  return ["/api/analytics/insights/false-insights", params] as const;
};

export function useGetFalseInsightsMetric<TData = { data: FalseInsightsMetricOut[] }>(options?: { params?: GetFalseInsightsMetricParams; query?: Omit<UseQueryOptions<{ data: FalseInsightsMetricOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getFalseInsightsMetricKey(options?.params), queryFn: () => getFalseInsightsMetric(options?.params), ...options?.query });
}

export function useGetFalseInsightsMetricSuspense<TData = { data: FalseInsightsMetricOut[] }>(options?: { params?: GetFalseInsightsMetricParams; query?: Omit<UseSuspenseQueryOptions<{ data: FalseInsightsMetricOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getFalseInsightsMetricKey(options?.params), queryFn: () => getFalseInsightsMetric(options?.params), ...options?.query });
}

export const submitInsightFeedback = async (data: InsightFeedbackIn, options?: RequestInit): Promise<{ data: InsightFeedbackOut }> => {
  const res = await fetch("/api/analytics/insights/feedback", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useSubmitInsightFeedback(options?: { mutation?: UseMutationOptions<{ data: InsightFeedbackOut }, ApiError, InsightFeedbackIn> }) {
  return useMutation({ mutationFn: (data) => submitInsightFeedback(data), ...options?.mutation });
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

export const getModels = async (params?: GetModelsParams, options?: RequestInit): Promise<{ data: ModelOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/models?${queryString}` : `/api/analytics/models`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getModelsKey = (params?: GetModelsParams) => {
  return ["/api/analytics/models", params] as const;
};

export function useGetModels<TData = { data: ModelOut[] }>(options?: { params?: GetModelsParams; query?: Omit<UseQueryOptions<{ data: ModelOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getModelsKey(options?.params), queryFn: () => getModels(options?.params), ...options?.query });
}

export function useGetModelsSuspense<TData = { data: ModelOut[] }>(options?: { params?: GetModelsParams; query?: Omit<UseSuspenseQueryOptions<{ data: ModelOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getModelsKey(options?.params), queryFn: () => getModels(options?.params), ...options?.query });
}

export const getOnlineFeatures = async (params?: GetOnlineFeaturesParams, options?: RequestInit): Promise<{ data: OnlineFeatureOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.source != null) searchParams.set("source", String(params?.source));
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/online-features?${queryString}` : `/api/analytics/online-features`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getOnlineFeaturesKey = (params?: GetOnlineFeaturesParams) => {
  return ["/api/analytics/online-features", params] as const;
};

export function useGetOnlineFeatures<TData = { data: OnlineFeatureOut[] }>(options?: { params?: GetOnlineFeaturesParams; query?: Omit<UseQueryOptions<{ data: OnlineFeatureOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getOnlineFeaturesKey(options?.params), queryFn: () => getOnlineFeatures(options?.params), ...options?.query });
}

export function useGetOnlineFeaturesSuspense<TData = { data: OnlineFeatureOut[] }>(options?: { params?: GetOnlineFeaturesParams; query?: Omit<UseSuspenseQueryOptions<{ data: OnlineFeatureOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getOnlineFeaturesKey(options?.params), queryFn: () => getOnlineFeatures(options?.params), ...options?.query });
}

export const getReasonCodes = async (params?: GetReasonCodesParams, options?: RequestInit): Promise<{ data: ReasonCodeOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/reason-codes?${queryString}` : `/api/analytics/reason-codes`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getReasonCodesKey = (params?: GetReasonCodesParams) => {
  return ["/api/analytics/reason-codes", params] as const;
};

export function useGetReasonCodes<TData = { data: ReasonCodeOut[] }>(options?: { params?: GetReasonCodesParams; query?: Omit<UseQueryOptions<{ data: ReasonCodeOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getReasonCodesKey(options?.params), queryFn: () => getReasonCodes(options?.params), ...options?.query });
}

export function useGetReasonCodesSuspense<TData = { data: ReasonCodeOut[] }>(options?: { params?: GetReasonCodesParams; query?: Omit<UseSuspenseQueryOptions<{ data: ReasonCodeOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getReasonCodesKey(options?.params), queryFn: () => getReasonCodes(options?.params), ...options?.query });
}

export const getDedupCollisionStats = async (options?: RequestInit): Promise<{ data: DedupCollisionStatsOut }> => {
  const res = await fetch("/api/analytics/reason-codes/dedup-collisions", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getDedupCollisionStatsKey = () => {
  return ["/api/analytics/reason-codes/dedup-collisions"] as const;
};

export function useGetDedupCollisionStats<TData = { data: DedupCollisionStatsOut }>(options?: { query?: Omit<UseQueryOptions<{ data: DedupCollisionStatsOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getDedupCollisionStatsKey(), queryFn: () => getDedupCollisionStats(), ...options?.query });
}

export function useGetDedupCollisionStatsSuspense<TData = { data: DedupCollisionStatsOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: DedupCollisionStatsOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getDedupCollisionStatsKey(), queryFn: () => getDedupCollisionStats(), ...options?.query });
}

export const getEntrySystemDistribution = async (params?: GetEntrySystemDistributionParams, options?: RequestInit): Promise<{ data: EntrySystemDistributionOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/reason-codes/entry-systems?${queryString}` : `/api/analytics/reason-codes/entry-systems`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getEntrySystemDistributionKey = (params?: GetEntrySystemDistributionParams) => {
  return ["/api/analytics/reason-codes/entry-systems", params] as const;
};

export function useGetEntrySystemDistribution<TData = { data: EntrySystemDistributionOut[] }>(options?: { params?: GetEntrySystemDistributionParams; query?: Omit<UseQueryOptions<{ data: EntrySystemDistributionOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getEntrySystemDistributionKey(options?.params), queryFn: () => getEntrySystemDistribution(options?.params), ...options?.query });
}

export function useGetEntrySystemDistributionSuspense<TData = { data: EntrySystemDistributionOut[] }>(options?: { params?: GetEntrySystemDistributionParams; query?: Omit<UseSuspenseQueryOptions<{ data: EntrySystemDistributionOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getEntrySystemDistributionKey(options?.params), queryFn: () => getEntrySystemDistribution(options?.params), ...options?.query });
}

export const getReasonCodeInsights = async (params?: GetReasonCodeInsightsParams, options?: RequestInit): Promise<{ data: ReasonCodeInsightOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/reason-codes/insights?${queryString}` : `/api/analytics/reason-codes/insights`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getReasonCodeInsightsKey = (params?: GetReasonCodeInsightsParams) => {
  return ["/api/analytics/reason-codes/insights", params] as const;
};

export function useGetReasonCodeInsights<TData = { data: ReasonCodeInsightOut[] }>(options?: { params?: GetReasonCodeInsightsParams; query?: Omit<UseQueryOptions<{ data: ReasonCodeInsightOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getReasonCodeInsightsKey(options?.params), queryFn: () => getReasonCodeInsights(options?.params), ...options?.query });
}

export function useGetReasonCodeInsightsSuspense<TData = { data: ReasonCodeInsightOut[] }>(options?: { params?: GetReasonCodeInsightsParams; query?: Omit<UseSuspenseQueryOptions<{ data: ReasonCodeInsightOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getReasonCodeInsightsKey(options?.params), queryFn: () => getReasonCodeInsights(options?.params), ...options?.query });
}

export const getRecommendations = async (params?: GetRecommendationsParams, options?: RequestInit): Promise<{ data: RecommendationOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/recommendations?${queryString}` : `/api/analytics/recommendations`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getRecommendationsKey = (params?: GetRecommendationsParams) => {
  return ["/api/analytics/recommendations", params] as const;
};

export function useGetRecommendations<TData = { data: RecommendationOut[] }>(options?: { params?: GetRecommendationsParams; query?: Omit<UseQueryOptions<{ data: RecommendationOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getRecommendationsKey(options?.params), queryFn: () => getRecommendations(options?.params), ...options?.query });
}

export function useGetRecommendationsSuspense<TData = { data: RecommendationOut[] }>(options?: { params?: GetRecommendationsParams; query?: Omit<UseSuspenseQueryOptions<{ data: RecommendationOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getRecommendationsKey(options?.params), queryFn: () => getRecommendations(options?.params), ...options?.query });
}

export const getRetryPerformance = async (params?: GetRetryPerformanceParams, options?: RequestInit): Promise<{ data: RetryPerformanceOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/retry/performance?${queryString}` : `/api/analytics/retry/performance`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getRetryPerformanceKey = (params?: GetRetryPerformanceParams) => {
  return ["/api/analytics/retry/performance", params] as const;
};

export function useGetRetryPerformance<TData = { data: RetryPerformanceOut[] }>(options?: { params?: GetRetryPerformanceParams; query?: Omit<UseQueryOptions<{ data: RetryPerformanceOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getRetryPerformanceKey(options?.params), queryFn: () => getRetryPerformance(options?.params), ...options?.query });
}

export function useGetRetryPerformanceSuspense<TData = { data: RetryPerformanceOut[] }>(options?: { params?: GetRetryPerformanceParams; query?: Omit<UseSuspenseQueryOptions<{ data: RetryPerformanceOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getRetryPerformanceKey(options?.params), queryFn: () => getRetryPerformance(options?.params), ...options?.query });
}

export const getThreeDsFunnel = async (params?: GetThreeDsFunnelParams, options?: RequestInit): Promise<{ data: ThreeDSFunnelOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  if (params?.days != null) searchParams.set("days", String(params?.days));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/smart-checkout/3ds-funnel?${queryString}` : `/api/analytics/smart-checkout/3ds-funnel`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getThreeDsFunnelKey = (params?: GetThreeDsFunnelParams) => {
  return ["/api/analytics/smart-checkout/3ds-funnel", params] as const;
};

export function useGetThreeDsFunnel<TData = { data: ThreeDSFunnelOut[] }>(options?: { params?: GetThreeDsFunnelParams; query?: Omit<UseQueryOptions<{ data: ThreeDSFunnelOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getThreeDsFunnelKey(options?.params), queryFn: () => getThreeDsFunnel(options?.params), ...options?.query });
}

export function useGetThreeDsFunnelSuspense<TData = { data: ThreeDSFunnelOut[] }>(options?: { params?: GetThreeDsFunnelParams; query?: Omit<UseSuspenseQueryOptions<{ data: ThreeDSFunnelOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getThreeDsFunnelKey(options?.params), queryFn: () => getThreeDsFunnel(options?.params), ...options?.query });
}

export const getSmartCheckoutPathPerformance = async (params?: GetSmartCheckoutPathPerformanceParams, options?: RequestInit): Promise<{ data: SmartCheckoutPathPerformanceOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/smart-checkout/path-performance?${queryString}` : `/api/analytics/smart-checkout/path-performance`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getSmartCheckoutPathPerformanceKey = (params?: GetSmartCheckoutPathPerformanceParams) => {
  return ["/api/analytics/smart-checkout/path-performance", params] as const;
};

export function useGetSmartCheckoutPathPerformance<TData = { data: SmartCheckoutPathPerformanceOut[] }>(options?: { params?: GetSmartCheckoutPathPerformanceParams; query?: Omit<UseQueryOptions<{ data: SmartCheckoutPathPerformanceOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getSmartCheckoutPathPerformanceKey(options?.params), queryFn: () => getSmartCheckoutPathPerformance(options?.params), ...options?.query });
}

export function useGetSmartCheckoutPathPerformanceSuspense<TData = { data: SmartCheckoutPathPerformanceOut[] }>(options?: { params?: GetSmartCheckoutPathPerformanceParams; query?: Omit<UseSuspenseQueryOptions<{ data: SmartCheckoutPathPerformanceOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getSmartCheckoutPathPerformanceKey(options?.params), queryFn: () => getSmartCheckoutPathPerformance(options?.params), ...options?.query });
}

export const getSmartCheckoutServicePaths = async (params?: GetSmartCheckoutServicePathsParams, options?: RequestInit): Promise<{ data: SmartCheckoutServicePathOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.entity != null) searchParams.set("entity", String(params?.entity));
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/analytics/smart-checkout/service-paths?${queryString}` : `/api/analytics/smart-checkout/service-paths`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getSmartCheckoutServicePathsKey = (params?: GetSmartCheckoutServicePathsParams) => {
  return ["/api/analytics/smart-checkout/service-paths", params] as const;
};

export function useGetSmartCheckoutServicePaths<TData = { data: SmartCheckoutServicePathOut[] }>(options?: { params?: GetSmartCheckoutServicePathsParams; query?: Omit<UseQueryOptions<{ data: SmartCheckoutServicePathOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getSmartCheckoutServicePathsKey(options?.params), queryFn: () => getSmartCheckoutServicePaths(options?.params), ...options?.query });
}

export function useGetSmartCheckoutServicePathsSuspense<TData = { data: SmartCheckoutServicePathOut[] }>(options?: { params?: GetSmartCheckoutServicePathsParams; query?: Omit<UseSuspenseQueryOptions<{ data: SmartCheckoutServicePathOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getSmartCheckoutServicePathsKey(options?.params), queryFn: () => getSmartCheckoutServicePaths(options?.params), ...options?.query });
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

export const getAuthStatus = async (options?: RequestInit): Promise<{ data: AuthStatusOut }> => {
  const res = await fetch("/api/auth/status", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getAuthStatusKey = () => {
  return ["/api/auth/status"] as const;
};

export function useGetAuthStatus<TData = { data: AuthStatusOut }>(options?: { query?: Omit<UseQueryOptions<{ data: AuthStatusOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getAuthStatusKey(), queryFn: () => getAuthStatus(), ...options?.query });
}

export function useGetAuthStatusSuspense<TData = { data: AuthStatusOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: AuthStatusOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getAuthStatusKey(), queryFn: () => getAuthStatus(), ...options?.query });
}

export const getWorkspaceConfig = async (options?: RequestInit): Promise<{ data: WorkspaceConfigOut }> => {
  const res = await fetch("/api/config/workspace", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getWorkspaceConfigKey = () => {
  return ["/api/config/workspace"] as const;
};

export function useGetWorkspaceConfig<TData = { data: WorkspaceConfigOut }>(options?: { query?: Omit<UseQueryOptions<{ data: WorkspaceConfigOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getWorkspaceConfigKey(), queryFn: () => getWorkspaceConfig(), ...options?.query });
}

export function useGetWorkspaceConfigSuspense<TData = { data: WorkspaceConfigOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: WorkspaceConfigOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getWorkspaceConfigKey(), queryFn: () => getWorkspaceConfig(), ...options?.query });
}

export const currentUser = async (options?: RequestInit): Promise<{ data: User }> => {
  const res = await fetch("/api/current-user", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const currentUserKey = () => {
  return ["/api/current-user"] as const;
};

export function useCurrentUser<TData = { data: User }>(options?: { query?: Omit<UseQueryOptions<{ data: User }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: currentUserKey(), queryFn: () => currentUser(), ...options?.query });
}

export function useCurrentUserSuspense<TData = { data: User }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: User }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: currentUserKey(), queryFn: () => currentUser(), ...options?.query });
}

export const listDashboards = async (params?: ListDashboardsParams, options?: RequestInit): Promise<{ data: DashboardList }> => {
  const searchParams = new URLSearchParams();
  if (params?.category != null) searchParams.set("category", String(params?.category));
  if (params?.tag != null) searchParams.set("tag", String(params?.tag));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/dashboards?${queryString}` : `/api/dashboards`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listDashboardsKey = (params?: ListDashboardsParams) => {
  return ["/api/dashboards", params] as const;
};

export function useListDashboards<TData = { data: DashboardList }>(options?: { params?: ListDashboardsParams; query?: Omit<UseQueryOptions<{ data: DashboardList }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listDashboardsKey(options?.params), queryFn: () => listDashboards(options?.params), ...options?.query });
}

export function useListDashboardsSuspense<TData = { data: DashboardList }>(options?: { params?: ListDashboardsParams; query?: Omit<UseSuspenseQueryOptions<{ data: DashboardList }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listDashboardsKey(options?.params), queryFn: () => listDashboards(options?.params), ...options?.query });
}

export const listDashboardCategories = async (options?: RequestInit): Promise<{ data: Record<string, unknown> }> => {
  const res = await fetch("/api/dashboards/categories/list", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listDashboardCategoriesKey = () => {
  return ["/api/dashboards/categories/list"] as const;
};

export function useListDashboardCategories<TData = { data: Record<string, unknown> }>(options?: { query?: Omit<UseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listDashboardCategoriesKey(), queryFn: () => listDashboardCategories(), ...options?.query });
}

export function useListDashboardCategoriesSuspense<TData = { data: Record<string, unknown> }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listDashboardCategoriesKey(), queryFn: () => listDashboardCategories(), ...options?.query });
}

export const listDashboardTags = async (options?: RequestInit): Promise<{ data: Record<string, unknown> }> => {
  const res = await fetch("/api/dashboards/tags/list", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listDashboardTagsKey = () => {
  return ["/api/dashboards/tags/list"] as const;
};

export function useListDashboardTags<TData = { data: Record<string, unknown> }>(options?: { query?: Omit<UseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listDashboardTagsKey(), queryFn: () => listDashboardTags(), ...options?.query });
}

export function useListDashboardTagsSuspense<TData = { data: Record<string, unknown> }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listDashboardTagsKey(), queryFn: () => listDashboardTags(), ...options?.query });
}

export const getDashboard = async (params: GetDashboardParams, options?: RequestInit): Promise<{ data: DashboardInfo }> => {
  const res = await fetch(`/api/dashboards/${params.dashboard_id}`, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getDashboardKey = (params?: GetDashboardParams) => {
  return ["/api/dashboards/{dashboard_id}", params] as const;
};

export function useGetDashboard<TData = { data: DashboardInfo }>(options: { params: GetDashboardParams; query?: Omit<UseQueryOptions<{ data: DashboardInfo }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getDashboardKey(options.params), queryFn: () => getDashboard(options.params), ...options?.query });
}

export function useGetDashboardSuspense<TData = { data: DashboardInfo }>(options: { params: GetDashboardParams; query?: Omit<UseSuspenseQueryOptions<{ data: DashboardInfo }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getDashboardKey(options.params), queryFn: () => getDashboard(options.params), ...options?.query });
}

export const getDashboardUrl = async (params: GetDashboardUrlParams, options?: RequestInit): Promise<{ data: Record<string, unknown> }> => {
  const searchParams = new URLSearchParams();
  if (params?.embed != null) searchParams.set("embed", String(params?.embed));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/dashboards/${params.dashboard_id}/url?${queryString}` : `/api/dashboards/${params.dashboard_id}/url`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getDashboardUrlKey = (params?: GetDashboardUrlParams) => {
  return ["/api/dashboards/{dashboard_id}/url", params] as const;
};

export function useGetDashboardUrl<TData = { data: Record<string, unknown> }>(options: { params: GetDashboardUrlParams; query?: Omit<UseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getDashboardUrlKey(options.params), queryFn: () => getDashboardUrl(options.params), ...options?.query });
}

export function useGetDashboardUrlSuspense<TData = { data: Record<string, unknown> }>(options: { params: GetDashboardUrlParams; query?: Omit<UseSuspenseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getDashboardUrlKey(options.params), queryFn: () => getDashboardUrl(options.params), ...options?.query });
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

export const listNotebooks = async (params?: ListNotebooksParams, options?: RequestInit): Promise<{ data: NotebookList }> => {
  const searchParams = new URLSearchParams();
  if (params?.category != null) searchParams.set("category", String(params?.category));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/notebooks/notebooks?${queryString}` : `/api/notebooks/notebooks`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listNotebooksKey = (params?: ListNotebooksParams) => {
  return ["/api/notebooks/notebooks", params] as const;
};

export function useListNotebooks<TData = { data: NotebookList }>(options?: { params?: ListNotebooksParams; query?: Omit<UseQueryOptions<{ data: NotebookList }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listNotebooksKey(options?.params), queryFn: () => listNotebooks(options?.params), ...options?.query });
}

export function useListNotebooksSuspense<TData = { data: NotebookList }>(options?: { params?: ListNotebooksParams; query?: Omit<UseSuspenseQueryOptions<{ data: NotebookList }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listNotebooksKey(options?.params), queryFn: () => listNotebooks(options?.params), ...options?.query });
}

export const getNotebookCategorySummary = async (options?: RequestInit): Promise<{ data: Record<string, unknown> }> => {
  const res = await fetch("/api/notebooks/notebooks/categories/summary", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getNotebookCategorySummaryKey = () => {
  return ["/api/notebooks/notebooks/categories/summary"] as const;
};

export function useGetNotebookCategorySummary<TData = { data: Record<string, unknown> }>(options?: { query?: Omit<UseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getNotebookCategorySummaryKey(), queryFn: () => getNotebookCategorySummary(), ...options?.query });
}

export function useGetNotebookCategorySummarySuspense<TData = { data: Record<string, unknown> }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: Record<string, unknown> }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getNotebookCategorySummaryKey(), queryFn: () => getNotebookCategorySummary(), ...options?.query });
}

export const getNotebookFolderUrl = async (params: GetNotebookFolderUrlParams, options?: RequestInit): Promise<{ data: FolderUrlOut }> => {
  const res = await fetch(`/api/notebooks/notebooks/folders/${params.folder_id}/url`, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getNotebookFolderUrlKey = (params?: GetNotebookFolderUrlParams) => {
  return ["/api/notebooks/notebooks/folders/{folder_id}/url", params] as const;
};

export function useGetNotebookFolderUrl<TData = { data: FolderUrlOut }>(options: { params: GetNotebookFolderUrlParams; query?: Omit<UseQueryOptions<{ data: FolderUrlOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getNotebookFolderUrlKey(options.params), queryFn: () => getNotebookFolderUrl(options.params), ...options?.query });
}

export function useGetNotebookFolderUrlSuspense<TData = { data: FolderUrlOut }>(options: { params: GetNotebookFolderUrlParams; query?: Omit<UseSuspenseQueryOptions<{ data: FolderUrlOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getNotebookFolderUrlKey(options.params), queryFn: () => getNotebookFolderUrl(options.params), ...options?.query });
}

export const getNotebook = async (params: GetNotebookParams, options?: RequestInit): Promise<{ data: NotebookInfo }> => {
  const res = await fetch(`/api/notebooks/notebooks/${params.notebook_id}`, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getNotebookKey = (params?: GetNotebookParams) => {
  return ["/api/notebooks/notebooks/{notebook_id}", params] as const;
};

export function useGetNotebook<TData = { data: NotebookInfo }>(options: { params: GetNotebookParams; query?: Omit<UseQueryOptions<{ data: NotebookInfo }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getNotebookKey(options.params), queryFn: () => getNotebook(options.params), ...options?.query });
}

export function useGetNotebookSuspense<TData = { data: NotebookInfo }>(options: { params: GetNotebookParams; query?: Omit<UseSuspenseQueryOptions<{ data: NotebookInfo }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getNotebookKey(options.params), queryFn: () => getNotebook(options.params), ...options?.query });
}

export const getNotebookUrl = async (params: GetNotebookUrlParams, options?: RequestInit): Promise<{ data: NotebookUrlOut }> => {
  const res = await fetch(`/api/notebooks/notebooks/${params.notebook_id}/url`, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getNotebookUrlKey = (params?: GetNotebookUrlParams) => {
  return ["/api/notebooks/notebooks/{notebook_id}/url", params] as const;
};

export function useGetNotebookUrl<TData = { data: NotebookUrlOut }>(options: { params: GetNotebookUrlParams; query?: Omit<UseQueryOptions<{ data: NotebookUrlOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getNotebookUrlKey(options.params), queryFn: () => getNotebookUrl(options.params), ...options?.query });
}

export function useGetNotebookUrlSuspense<TData = { data: NotebookUrlOut }>(options: { params: GetNotebookUrlParams; query?: Omit<UseSuspenseQueryOptions<{ data: NotebookUrlOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getNotebookUrlKey(options.params), queryFn: () => getNotebookUrl(options.params), ...options?.query });
}

export const listApprovalRules = async (params?: ListApprovalRulesParams, options?: RequestInit): Promise<{ data: ApprovalRuleOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.rule_type != null) searchParams.set("rule_type", String(params?.rule_type));
  if (params?.active_only != null) searchParams.set("active_only", String(params?.active_only));
  if (params?.limit != null) searchParams.set("limit", String(params?.limit));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/rules?${queryString}` : `/api/rules`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const listApprovalRulesKey = (params?: ListApprovalRulesParams) => {
  return ["/api/rules", params] as const;
};

export function useListApprovalRules<TData = { data: ApprovalRuleOut[] }>(options?: { params?: ListApprovalRulesParams; query?: Omit<UseQueryOptions<{ data: ApprovalRuleOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: listApprovalRulesKey(options?.params), queryFn: () => listApprovalRules(options?.params), ...options?.query });
}

export function useListApprovalRulesSuspense<TData = { data: ApprovalRuleOut[] }>(options?: { params?: ListApprovalRulesParams; query?: Omit<UseSuspenseQueryOptions<{ data: ApprovalRuleOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: listApprovalRulesKey(options?.params), queryFn: () => listApprovalRules(options?.params), ...options?.query });
}

export const createApprovalRule = async (data: ApprovalRuleIn, options?: RequestInit): Promise<{ data: ApprovalRuleOut }> => {
  const res = await fetch("/api/rules", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useCreateApprovalRule(options?: { mutation?: UseMutationOptions<{ data: ApprovalRuleOut }, ApiError, ApprovalRuleIn> }) {
  return useMutation({ mutationFn: (data) => createApprovalRule(data), ...options?.mutation });
}

export const updateApprovalRule = async (params: UpdateApprovalRuleParams, data: ApprovalRuleUpdate, options?: RequestInit): Promise<{ data: ApprovalRuleOut }> => {
  const res = await fetch(`/api/rules/${params.rule_id}`, { ...options, method: "PATCH", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useUpdateApprovalRule(options?: { mutation?: UseMutationOptions<{ data: ApprovalRuleOut }, ApiError, { params: UpdateApprovalRuleParams; data: ApprovalRuleUpdate }> }) {
  return useMutation({ mutationFn: (vars) => updateApprovalRule(vars.params, vars.data), ...options?.mutation });
}

export const deleteApprovalRule = async (params: DeleteApprovalRuleParams, options?: RequestInit): Promise<void> => {
  const res = await fetch(`/api/rules/${params.rule_id}`, { ...options, method: "DELETE" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return;
};

export function useDeleteApprovalRule(options?: { mutation?: UseMutationOptions<void, ApiError, { params: DeleteApprovalRuleParams }> }) {
  return useMutation({ mutationFn: (vars) => deleteApprovalRule(vars.params), ...options?.mutation });
}

export const updateSetupConfig = async (data: SetupConfigIn, options?: RequestInit): Promise<{ data: SetupConfigOut }> => {
  const res = await fetch("/api/setup/config", { ...options, method: "PATCH", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useUpdateSetupConfig(options?: { mutation?: UseMutationOptions<{ data: SetupConfigOut }, ApiError, SetupConfigIn> }) {
  return useMutation({ mutationFn: (data) => updateSetupConfig(data), ...options?.mutation });
}

export const getSetupDefaults = async (options?: RequestInit): Promise<{ data: SetupDefaultsOut }> => {
  const res = await fetch("/api/setup/defaults", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getSetupDefaultsKey = () => {
  return ["/api/setup/defaults"] as const;
};

export function useGetSetupDefaults<TData = { data: SetupDefaultsOut }>(options?: { query?: Omit<UseQueryOptions<{ data: SetupDefaultsOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getSetupDefaultsKey(), queryFn: () => getSetupDefaults(), ...options?.query });
}

export function useGetSetupDefaultsSuspense<TData = { data: SetupDefaultsOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: SetupDefaultsOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getSetupDefaultsKey(), queryFn: () => getSetupDefaults(), ...options?.query });
}

export const runSetupJob = async (data: RunJobIn, options?: RequestInit): Promise<{ data: RunJobOut }> => {
  const res = await fetch("/api/setup/run-job", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useRunSetupJob(options?: { mutation?: UseMutationOptions<{ data: RunJobOut }, ApiError, RunJobIn> }) {
  return useMutation({ mutationFn: (data) => runSetupJob(data), ...options?.mutation });
}

export const runSetupPipeline = async (data: RunPipelineIn, options?: RequestInit): Promise<{ data: RunPipelineOut }> => {
  const res = await fetch("/api/setup/run-pipeline", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useRunSetupPipeline(options?: { mutation?: UseMutationOptions<{ data: RunPipelineOut }, ApiError, RunPipelineIn> }) {
  return useMutation({ mutationFn: (data) => runSetupPipeline(data), ...options?.mutation });
}

export const getSetupSettings = async (options?: RequestInit): Promise<{ data: SetupSettingsOut }> => {
  const res = await fetch("/api/setup/settings", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getSetupSettingsKey = () => {
  return ["/api/setup/settings"] as const;
};

export function useGetSetupSettings<TData = { data: SetupSettingsOut }>(options?: { query?: Omit<UseQueryOptions<{ data: SetupSettingsOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getSetupSettingsKey(), queryFn: () => getSetupSettings(), ...options?.query });
}

export function useGetSetupSettingsSuspense<TData = { data: SetupSettingsOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: SetupSettingsOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getSetupSettingsKey(), queryFn: () => getSetupSettings(), ...options?.query });
}

export const healthDatabase = async (options?: RequestInit): Promise<{ data: HealthDatabaseOut }> => {
  const res = await fetch("/api/v1/health/database", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const healthDatabaseKey = () => {
  return ["/api/v1/health/database"] as const;
};

export function useHealthDatabase<TData = { data: HealthDatabaseOut }>(options?: { query?: Omit<UseQueryOptions<{ data: HealthDatabaseOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: healthDatabaseKey(), queryFn: () => healthDatabase(), ...options?.query });
}

export function useHealthDatabaseSuspense<TData = { data: HealthDatabaseOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: HealthDatabaseOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: healthDatabaseKey(), queryFn: () => healthDatabase(), ...options?.query });
}

export const healthcheck = async (options?: RequestInit): Promise<{ data: HealthcheckOut }> => {
  const res = await fetch("/api/v1/healthcheck", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const healthcheckKey = () => {
  return ["/api/v1/healthcheck"] as const;
};

export function useHealthcheck<TData = { data: HealthcheckOut }>(options?: { query?: Omit<UseQueryOptions<{ data: HealthcheckOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: healthcheckKey(), queryFn: () => healthcheck(), ...options?.query });
}

export function useHealthcheckSuspense<TData = { data: HealthcheckOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: HealthcheckOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: healthcheckKey(), queryFn: () => healthcheck(), ...options?.query });
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

