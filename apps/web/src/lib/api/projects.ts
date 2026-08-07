import { apiFetch } from '@/lib/api/client';
import { formatBudget, formatDate } from '@/lib/api/leads';

export const PROJECT_TYPES = [
  'residential',
  'mixed_use',
  'commercial',
  'land',
  'multifamily',
  'condominium',
  'single_family',
  'townhome',
] as const;

export type ProjectType = (typeof PROJECT_TYPES)[number];

export const DEVELOPMENT_TYPES = [
  'ground_up',
  'renovation',
  'conversion',
  'value_add',
  'fix_and_flip',
  'rental',
  'land_development',
] as const;

export type DevelopmentType = (typeof DEVELOPMENT_TYPES)[number];

export const PROJECT_STATUSES = [
  'pipeline',
  'due_diligence',
  'acquisition',
  'pre_development',
  'permitting',
  'construction',
  'leasing',
  'sales',
  'stabilization',
  'completed',
  'on_hold',
  'cancelled',
] as const;

export type ProjectStatus = (typeof PROJECT_STATUSES)[number];

export const PROJECT_PRIORITIES = ['low', 'medium', 'high', 'critical'] as const;
export type ProjectPriority = (typeof PROJECT_PRIORITIES)[number];

export const DEVELOPMENT_STAGES = [
  'deal_screening',
  'due_diligence',
  'acquisition',
  'design',
  'entitlement',
  'permitting',
  'procurement',
  'construction',
  'sales',
  'lease_up',
  'stabilization',
  'exit',
  'closed',
] as const;
export type DevelopmentStage = (typeof DEVELOPMENT_STAGES)[number];

export const PROJECT_TEAM_ROLES = [
  'project_manager',
  'development_manager',
  'construction_manager',
  'acquisitions',
  'finance',
  'sales',
  'leasing',
  'marketing',
  'legal',
  'operations',
  'admin',
  'executive',
  'external_advisor',
] as const;
export type ProjectTeamRole = (typeof PROJECT_TEAM_ROLES)[number];

export const PROJECT_TEAM_STATUSES = ['active', 'inactive', 'ended'] as const;
export type ProjectTeamMemberStatus = (typeof PROJECT_TEAM_STATUSES)[number];

export interface ProjectUserSummary {
  id: string;
  full_name: string;
  email: string | null;
}

export interface ProjectTeamMember {
  id: string;
  project_id: string;
  user_id: string;
  role: ProjectTeamRole;
  is_primary: boolean;
  start_date: string | null;
  end_date: string | null;
  status: ProjectTeamMemberStatus;
  notes: string | null;
  user: ProjectUserSummary | null;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  project_code: string;
  project_name: string;
  slug: string | null;
  address: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  latitude: string | null;
  longitude: string | null;
  timezone: string | null;
  project_type: ProjectType;
  development_type: DevelopmentType;
  project_status: ProjectStatus;
  priority: ProjectPriority;
  development_stage: DevelopmentStage | null;
  ownership_entity: string | null;
  company_id: string | null;
  total_units: number | null;
  residential_units: number | null;
  commercial_units: number | null;
  gross_square_feet: number | null;
  net_sellable_square_feet: number | null;
  lot_size: string | null;
  acquisition_price: string | null;
  land_cost: string | null;
  construction_budget: string | null;
  soft_cost_budget: string | null;
  total_development_cost: string | null;
  current_project_value: string | null;
  projected_sale_value: string | null;
  equity_required: string | null;
  equity_raised: string | null;
  debt_amount: string | null;
  loan_to_cost: string | null;
  projected_revenue: string | null;
  projected_profit: string | null;
  projected_roi: string | null;
  projected_irr: string | null;
  currency: string;
  completion_percentage: string | null;
  acquisition_date: string | null;
  start_date: string | null;
  actual_start_date: string | null;
  target_completion_date: string | null;
  actual_completion_date: string | null;
  estimated_closing_date: string | null;
  assigned_project_manager: string | null;
  project_manager_user_id: string | null;
  project_manager: ProjectUserSummary | null;
  team_summary: ProjectTeamMember[];
  description: string | null;
  notes: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  created_by_user_id: string | null;
  updated_by_user_id: string | null;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ProjectStats {
  total: number;
  active: number;
  under_construction: number;
  completed: number;
  units_under_development: number;
  total_units: number;
  total_development_cost: string;
  current_portfolio_value: string;
  equity_raised: string;
}

export interface ProjectInput {
  project_code: string;
  project_name: string;
  slug?: string | null;
  address?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  timezone?: string | null;
  project_type?: ProjectType;
  development_type?: DevelopmentType;
  project_status?: ProjectStatus;
  priority?: ProjectPriority;
  development_stage?: DevelopmentStage | null;
  ownership_entity?: string | null;
  company_id?: string | null;
  total_units?: number | null;
  residential_units?: number | null;
  commercial_units?: number | null;
  gross_square_feet?: number | null;
  net_sellable_square_feet?: number | null;
  lot_size?: number | null;
  acquisition_price?: number | null;
  land_cost?: number | null;
  construction_budget?: number | null;
  soft_cost_budget?: number | null;
  total_development_cost?: number | null;
  current_project_value?: number | null;
  projected_sale_value?: number | null;
  equity_required?: number | null;
  equity_raised?: number | null;
  debt_amount?: number | null;
  loan_to_cost?: number | null;
  projected_revenue?: number | null;
  projected_profit?: number | null;
  projected_roi?: number | null;
  projected_irr?: number | null;
  currency?: string;
  completion_percentage?: number | null;
  acquisition_date?: string | null;
  start_date?: string | null;
  actual_start_date?: string | null;
  target_completion_date?: string | null;
  actual_completion_date?: string | null;
  estimated_closing_date?: string | null;
  assigned_project_manager?: string | null;
  project_manager_user_id?: string | null;
  description?: string | null;
  notes?: string | null;
}

export interface ProjectFilters {
  search?: string;
  status?: ProjectStatus | '';
  project_type?: ProjectType | '';
  development_type?: DevelopmentType | '';
  priority?: ProjectPriority | '';
  development_stage?: DevelopmentStage | '';
  city?: string;
  state?: string;
  country?: string;
  assigned_project_manager?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface ProjectTeamMemberInput {
  user_id: string;
  role: ProjectTeamRole;
  is_primary?: boolean;
  start_date?: string | null;
  end_date?: string | null;
  status?: ProjectTeamMemberStatus;
  notes?: string | null;
}

function buildQuery(filters: ProjectFilters = {}): string {
  const params = new URLSearchParams();

  if (filters.search?.trim()) params.set('search', filters.search.trim());
  if (filters.status) params.set('status', filters.status);
  if (filters.project_type) params.set('project_type', filters.project_type);
  if (filters.development_type) params.set('development_type', filters.development_type);
  if (filters.priority) params.set('priority', filters.priority);
  if (filters.development_stage) params.set('development_stage', filters.development_stage);
  if (filters.city?.trim()) params.set('city', filters.city.trim());
  if (filters.state?.trim()) params.set('state', filters.state.trim());
  if (filters.country?.trim()) params.set('country', filters.country.trim());
  if (filters.assigned_project_manager?.trim()) {
    params.set('assigned_project_manager', filters.assigned_project_manager.trim());
  }
  if (filters.include_archived) params.set('include_archived', 'true');
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));

  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchProjects(filters: ProjectFilters = {}): Promise<ProjectListResponse> {
  return apiFetch<ProjectListResponse>(`/projects${buildQuery(filters)}`);
}

export async function fetchProjectStats(): Promise<ProjectStats> {
  return apiFetch<ProjectStats>('/projects/stats');
}

export async function fetchProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`);
}

export async function createProject(input: ProjectInput): Promise<Project> {
  return apiFetch<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateProject(id: string, input: Partial<ProjectInput>): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function archiveProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`, { method: 'DELETE' });
}

export async function restoreProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}/restore`, { method: 'POST' });
}

export async function changeProjectStatus(
  id: string,
  statusValue: ProjectStatus,
  note?: string,
): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}/status`, {
    method: 'POST',
    body: JSON.stringify({ status: statusValue, note: note ?? null }),
  });
}

export async function fetchProjectStatusTransitions(
  id: string,
): Promise<{ current_status: ProjectStatus; allowed: ProjectStatus[] }> {
  return apiFetch(`/projects/${id}/status-transitions`);
}

export async function fetchProjectTeam(
  id: string,
): Promise<{ items: ProjectTeamMember[]; total: number }> {
  return apiFetch(`/projects/${id}/team`);
}

export async function addProjectTeamMember(
  id: string,
  input: ProjectTeamMemberInput,
): Promise<ProjectTeamMember> {
  return apiFetch(`/projects/${id}/team`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateProjectTeamMember(
  id: string,
  memberId: string,
  input: Partial<ProjectTeamMemberInput>,
): Promise<ProjectTeamMember> {
  return apiFetch(`/projects/${id}/team/${memberId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function removeProjectTeamMember(id: string, memberId: string): Promise<void> {
  await apiFetch(`/projects/${id}/team/${memberId}`, { method: 'DELETE' });
}

export { formatBudget as formatCurrency, formatDate };

export function formatShortDate(value: string | null, locale = 'tr'): string {
  if (!value) return '—';
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-GB';
  return new Intl.DateTimeFormat(intlLocale, { dateStyle: 'medium' }).format(new Date(value));
}

export function formatPercent(value: string | null, locale = 'tr'): string {
  if (!value) return '—';
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return new Intl.NumberFormat(intlLocale, {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(amount / 100);
}

export function formatCompletion(value: string | null, locale = 'tr'): string {
  if (!value) return '—';
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return `${new Intl.NumberFormat(intlLocale, {
    maximumFractionDigits: 1,
  }).format(amount)}%`;
}

export function formatLocation(project: Pick<Project, 'address' | 'address_line2' | 'city' | 'state' | 'postal_code' | 'country'>): string {
  const line = [project.address, project.address_line2].filter(Boolean).join(', ');
  const locality = [project.city, project.state, project.postal_code].filter(Boolean).join(', ');
  const parts = [line, locality, project.country].filter(Boolean);
  return parts.length ? parts.join(' · ') : '—';
}

export function formatNumber(value: number | null | undefined, locale = 'tr'): string {
  if (value === null || value === undefined) return '—';
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return new Intl.NumberFormat(intlLocale).format(value);
}

/* --------------------------------------------------------------------- */
/* Sprint 10A2 — Projects portfolio dashboard                            */
/* --------------------------------------------------------------------- */

export type ProjectRiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type AlertSeverity = 'info' | 'low' | 'medium' | 'high' | 'critical';
export type AlertCategory =
  | 'budget'
  | 'schedule'
  | 'document'
  | 'construction'
  | 'data_quality'
  | 'sales'
  | 'leasing'
  | 'team';
export type MilestoneType = 'closing' | 'delivery' | 'start' | 'completion' | 'acquisition';

/** Typed metric that distinguishes an unavailable/restricted value from zero. */
export interface MetricValue {
  value: string | number | null;
  available: boolean;
  reason: string | null;
}

export function metricNumber(metric: MetricValue | null | undefined): number | null {
  if (!metric || !metric.available || metric.value === null || metric.value === undefined) {
    return null;
  }
  const amount = Number(metric.value);
  return Number.isNaN(amount) ? null : amount;
}

export function formatMetricCurrency(
  metric: MetricValue | null | undefined,
  locale = 'tr',
  notAvailableLabel = '—',
): string {
  if (!metric || !metric.available) return notAvailableLabel;
  return formatBudget(metric.value === null ? null : String(metric.value), locale);
}

export function formatMetricPercent(
  metric: MetricValue | null | undefined,
  locale = 'tr',
  notAvailableLabel = '—',
): string {
  if (!metric || !metric.available) return notAvailableLabel;
  return formatPercent(metric.value === null ? null : String(metric.value), locale);
}

export function formatMetricNumber(
  metric: MetricValue | null | undefined,
  locale = 'tr',
  notAvailableLabel = '—',
): string {
  if (!metric || !metric.available) return notAvailableLabel;
  return formatNumber(metricNumber(metric), locale);
}

export interface DashboardFiltersApplied {
  status: string | null;
  project_type: string | null;
  priority: string | null;
  development_stage: string | null;
  project_manager_user_id: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  completion_year: number | null;
  include_archived: boolean;
  search: string | null;
}

export interface DashboardMeta {
  generated_at: string;
  currency_mode: string;
  financial_access: boolean;
  applied_filters: DashboardFiltersApplied;
  data_completeness: Record<string, string>;
  partial_data_warnings: string[];
}

export interface PortfolioSummary {
  total_projects: number;
  active_projects: number;
  planning_projects: number;
  under_construction_projects: number;
  completed_projects: number;
  on_hold_projects: number;
  cancelled_projects: number;
  archived_projects: number;
  total_units: number;
  residential_units: number;
  commercial_units: number;
  available_units: MetricValue;
  reserved_units: MetricValue;
  under_contract_units: MetricValue;
  sold_units: MetricValue;
  occupied_units: MetricValue;
  vacant_units: MetricValue;
  portfolio_value: MetricValue;
  total_development_budget: MetricValue;
  construction_budget: MetricValue;
  budget_spent: MetricValue;
  budget_remaining: MetricValue;
  budget_utilization_percentage: MetricValue;
  average_project_completion: MetricValue;
  projects_delayed: number;
  projects_at_risk: number;
  status_distribution: Record<string, number>;
  stage_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
}

export interface FinancialSummary {
  expected_revenue: MetricValue;
  expected_profit: MetricValue;
  current_portfolio_value: MetricValue;
  total_development_cost: MetricValue;
  construction_budget: MetricValue;
  soft_cost_budget: MetricValue;
  land_cost: MetricValue;
  equity_raised: MetricValue;
  equity_required: MetricValue;
  debt_outstanding: MetricValue;
  budget_spent: MetricValue;
  budget_remaining: MetricValue;
  budget_utilization_percentage: MetricValue;
  realized_revenue: MetricValue;
  remaining_revenue: MetricValue;
  realized_profit: MetricValue;
  roi: MetricValue;
  irr: MetricValue;
  equity_multiple: MetricValue;
  average_profit_margin: MetricValue;
  funding_gap?: MetricValue;
  cash_position?: MetricValue;
  forecast_cost?: MetricValue;
  need_30_days?: MetricValue;
  need_60_days?: MetricValue;
  need_90_days?: MetricValue;
  projects_requiring_attention?: Array<Record<string, unknown>>;
  upcoming_large_cash_events?: Array<Record<string, unknown>>;
  ai_finance_summary?: Record<string, unknown> | null;
}

export interface ConstructionProjectRow {
  project_id: string;
  project_name: string;
  status: string;
  development_stage: string | null;
  completion_percentage: string | null;
  estimated_start_date: string | null;
  actual_start_date: string | null;
  estimated_completion_date: string | null;
  actual_completion_date: string | null;
  days_remaining: number | null;
  days_delayed: number | null;
  is_delayed: boolean;
  risk: ProjectRiskLevel;
  next_milestone: string | null;
}

export interface ConstructionSummary {
  average_completion_percentage: MetricValue;
  projects_on_schedule: number;
  projects_delayed: number;
  projects_without_schedule: number;
  projects_without_progress: number;
  average_days_remaining: MetricValue;
  completion_distribution: Record<string, number>;
  stage_distribution: Record<string, number>;
  projects: ConstructionProjectRow[];
}

export interface SalesSummary {
  available_units: MetricValue;
  reserved_units: MetricValue;
  under_contract_units: MetricValue;
  sold_units: MetricValue;
  cancelled_units: MetricValue;
  sales_rate: MetricValue;
  gross_sales_volume: MetricValue;
  by_status: Record<string, number>;
}

export interface LeasingSummary {
  occupied_units: MetricValue;
  vacant_units: MetricValue;
  occupancy_rate: MetricValue;
  leases_expiring_30_days: MetricValue;
  leases_expiring_60_days: MetricValue;
  leases_expiring_90_days: MetricValue;
  monthly_rental_income: MetricValue;
  by_status: Record<string, number>;
}

export interface ProjectMilestoneItem {
  id: string;
  project_id: string;
  project_name: string;
  title: string;
  type: MilestoneType;
  description: string | null;
  date: string;
  status: string;
  priority: string;
  days_remaining: number;
  is_overdue: boolean;
  owner: string | null;
  source: string;
  action_url: string;
}

export interface ProjectAlertItem {
  id: string;
  project_id: string;
  project_name: string;
  severity: AlertSeverity;
  category: AlertCategory;
  title: string;
  message: string;
  action_required: boolean;
  recommended_action: string | null;
  created_at: string;
  due_date: string | null;
  days_remaining: number | null;
  source: string;
  action_url: string;
}

export interface ProjectActivityItem {
  id: string;
  project_id: string | null;
  project_name: string | null;
  type: string;
  title: string;
  description: string | null;
  actor: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
  action_url: string | null;
}

export interface ProjectDashboardResponse {
  portfolio: PortfolioSummary;
  financials: FinancialSummary | null;
  construction: ConstructionSummary;
  sales: SalesSummary;
  leasing: LeasingSummary;
  milestones: ProjectMilestoneItem[];
  alerts: ProjectAlertItem[];
  activity: ProjectActivityItem[];
  meta: DashboardMeta;
}

export interface ProjectMilestoneListResponse {
  items: ProjectMilestoneItem[];
  total: number;
}

export interface ProjectAlertListResponse {
  items: ProjectAlertItem[];
  total: number;
}

export interface ProjectActivityListResponse {
  items: ProjectActivityItem[];
  total: number;
}

export interface ProjectDashboardFilters {
  search?: string;
  status?: ProjectStatus | '';
  project_type?: ProjectType | '';
  priority?: ProjectPriority | '';
  development_stage?: DevelopmentStage | '';
  city?: string;
  state?: string;
  country?: string;
  project_manager_user_id?: string;
  completion_year?: number;
  include_archived?: boolean;
  milestone_days?: number;
}

function buildDashboardQuery(filters: ProjectDashboardFilters = {}): string {
  const params = new URLSearchParams();

  if (filters.search?.trim()) params.set('search', filters.search.trim());
  if (filters.status) params.set('status', filters.status);
  if (filters.project_type) params.set('project_type', filters.project_type);
  if (filters.priority) params.set('priority', filters.priority);
  if (filters.development_stage) params.set('development_stage', filters.development_stage);
  if (filters.city?.trim()) params.set('city', filters.city.trim());
  if (filters.state?.trim()) params.set('state', filters.state.trim());
  if (filters.country?.trim()) params.set('country', filters.country.trim());
  if (filters.project_manager_user_id) {
    params.set('project_manager_user_id', filters.project_manager_user_id);
  }
  if (filters.completion_year) params.set('completion_year', String(filters.completion_year));
  if (filters.include_archived) params.set('include_archived', 'true');
  if (filters.milestone_days) params.set('milestone_days', String(filters.milestone_days));

  const query = params.toString();
  return query ? `?${query}` : '';
}

/** Derives the dashboard-endpoint filter subset from the shared project list filters. */
export function toDashboardFilters(filters: ProjectFilters): ProjectDashboardFilters {
  return {
    search: filters.search,
    status: filters.status,
    project_type: filters.project_type,
    priority: filters.priority,
    development_stage: filters.development_stage,
    city: filters.city,
    state: filters.state,
    country: filters.country,
    include_archived: filters.include_archived,
  };
}

export async function fetchProjectsDashboard(
  filters: ProjectDashboardFilters = {},
): Promise<ProjectDashboardResponse> {
  return apiFetch<ProjectDashboardResponse>(`/projects/dashboard${buildDashboardQuery(filters)}`);
}

export async function fetchUpcomingMilestones(params: {
  days?: number;
  project_id?: string;
  include_archived?: boolean;
} = {}): Promise<ProjectMilestoneListResponse> {
  const query = new URLSearchParams();
  if (params.days) query.set('days', String(params.days));
  if (params.project_id) query.set('project_id', params.project_id);
  if (params.include_archived) query.set('include_archived', 'true');
  const qs = query.toString();
  return apiFetch<ProjectMilestoneListResponse>(`/projects/upcoming-milestones${qs ? `?${qs}` : ''}`);
}

export async function fetchCriticalItems(params: {
  include_archived?: boolean;
  limit?: number;
} = {}): Promise<ProjectAlertListResponse> {
  const query = new URLSearchParams();
  if (params.include_archived) query.set('include_archived', 'true');
  if (params.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return apiFetch<ProjectAlertListResponse>(`/projects/critical-items${qs ? `?${qs}` : ''}`);
}

export async function fetchRecentProjectActivity(params: {
  limit?: number;
} = {}): Promise<ProjectActivityListResponse> {
  const query = new URLSearchParams();
  if (params.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return apiFetch<ProjectActivityListResponse>(`/projects/recent-activity${qs ? `?${qs}` : ''}`);
}

/* --------------------------------------------------------------------- */
/* Sprint 10A3 — Project detail workspace                                */
/* --------------------------------------------------------------------- */

export type ProjectDetailTabKey =
  | 'overview'
  | 'financials'
  | 'schedule'
  | 'construction'
  | 'units'
  | 'sales'
  | 'leasing'
  | 'investors'
  | 'documents'
  | 'team'
  | 'activity';

export interface ProjectDetailPermissions {
  can_edit: boolean;
  can_archive: boolean;
  can_restore: boolean;
  can_manage_status: boolean;
  can_view_financial: boolean;
  can_edit_financial: boolean;
  can_view_team: boolean;
  can_manage_team: boolean;
  can_export: boolean;
}

export interface ProjectDetailNavigationItem {
  key: ProjectDetailTabKey;
  href: string;
  visible: boolean;
}

export interface ProjectDetailShell {
  project: Project;
  permissions: ProjectDetailPermissions;
  navigation: ProjectDetailNavigationItem[];
  risk: ProjectRiskLevel;
  financial_access: boolean;
  alerts_count: number;
  milestones_count: number;
  team_count: number;
  documents_count: number;
  units_count: number;
  data_completeness: Record<string, string>;
}

export interface ProjectOverviewResponse {
  shell: ProjectDetailShell;
  snapshot: Record<string, unknown>;
  schedule: Record<string, unknown>;
  financial_snapshot: Record<string, MetricValue> | null;
  construction_snapshot: Record<string, unknown>;
  sales_leasing_snapshot: Record<string, MetricValue>;
  team: ProjectTeamMember[];
  milestones: ProjectMilestoneItem[];
  alerts: ProjectAlertItem[];
  activity: ProjectActivityItem[];
  key_documents: Array<Record<string, unknown>>;
  warnings: string[];
}

export interface ProjectFinancialsResponse {
  financial_access: boolean;
  summary: Record<string, MetricValue> | null;
  budgets: Array<Record<string, unknown>>;
  capital: Array<Record<string, unknown>>;
  warnings: string[];
}

export type FinancialHealthStatus =
  | 'healthy'
  | 'watch'
  | 'at_risk'
  | 'critical'
  | 'unavailable';

export interface CashFlowHorizonBucket {
  days: number;
  outflows: MetricValue;
  inflows: MetricValue;
  net_need: MetricValue;
  item_count: number;
}

export interface CashFlowUpcomingItem {
  id: string;
  kind: string;
  direction: string;
  label: string;
  amount: string | number;
  currency: string;
  expected_date: string | null;
  status: string | null;
  source: string;
}

export interface ProjectCashFlowSummary {
  project_id: string;
  currency: string;
  as_of: string;
  horizon_30: CashFlowHorizonBucket;
  horizon_60: CashFlowHorizonBucket;
  horizon_90: CashFlowHorizonBucket;
  large_upcoming_payments: CashFlowUpcomingItem[];
  large_upcoming_receipts: CashFlowUpcomingItem[];
  data_completeness: Record<string, string>;
  warnings: string[];
}

export interface ExecutiveFinanceAlert {
  id: string;
  code: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  recommended_action: string | null;
  related_metric: string | null;
  due_date: string | null;
}

export interface ProjectExecutiveFinance {
  project_id: string;
  project_name: string;
  currency: string;
  as_of: string;
  health: FinancialHealthStatus;
  health_reasons: string[];
  expected_revenue: MetricValue;
  received_revenue: MetricValue;
  forecast_cost: MetricValue;
  actual_cost: MetricValue;
  expected_profit: MetricValue;
  profit_margin: MetricValue;
  current_cash: MetricValue;
  funding_gap: MetricValue;
  need_30_days: MetricValue;
  need_60_days: MetricValue;
  need_90_days: MetricValue;
  equity_required: MetricValue;
  equity_raised: MetricValue;
  committed_funding: MetricValue;
  funded_amount: MetricValue;
  remaining_funding: MetricValue;
  cash_flow: ProjectCashFlowSummary;
  alerts: ExecutiveFinanceAlert[];
  ai_summary: {
    project_id: string;
    project_name: string;
    health: FinancialHealthStatus;
    needs_cash: boolean;
    is_profitable: boolean | null;
    is_risky: boolean;
    missing_info: string[];
    highlights: string[];
    metrics: Record<string, MetricValue>;
    generated_at: string;
  };
  data_completeness: Record<string, string>;
  warnings: string[];
  cost_source: string;
}

export interface ProjectScheduleResponse {
  key_dates: Record<string, string | null>;
  days_remaining: number | null;
  days_delayed: number | null;
  is_delayed: boolean;
  missing_dates: string[];
  milestones: ProjectMilestoneItem[];
  risks: string[];
}

export interface ProjectConstructionResponse {
  completion_percentage: string | null;
  development_stage: string | null;
  status: string;
  is_delayed: boolean;
  days_remaining: number | null;
  budget_utilization: MetricValue;
  risk: ProjectRiskLevel;
  alerts: ProjectAlertItem[];
  warnings: string[];
}

export interface ProjectUnitsResponse {
  summary: Record<string, MetricValue>;
  items: Array<Record<string, unknown>>;
  total: number;
  page: number;
  page_size: number;
  pages: number;
  warnings: string[];
}

export interface ProjectSalesResponse {
  summary: Record<string, MetricValue>;
  opportunities: Array<Record<string, unknown>>;
  total_opportunities: number;
  by_status: Record<string, number>;
  warnings: string[];
}

export interface ProjectLeasingResponse {
  summary: Record<string, MetricValue>;
  by_status: Record<string, number>;
  items: Array<Record<string, unknown>>;
  warnings: string[];
}

export interface ProjectInvestorsResponse {
  financial_access: boolean;
  items: Array<Record<string, unknown>>;
  total: number;
  warnings: string[];
}

export interface ProjectDocumentsResponse {
  items: Array<Record<string, unknown>>;
  total: number;
  warnings: string[];
}

export interface ProjectDirectoryUser {
  id: string;
  full_name: string;
  email: string;
  job_title: string | null;
  status: string;
}

export async function fetchProjectDetail(projectId: string): Promise<ProjectDetailShell> {
  return apiFetch<ProjectDetailShell>(`/projects/${projectId}/detail`);
}

export async function fetchProjectOverview(projectId: string): Promise<ProjectOverviewResponse> {
  return apiFetch<ProjectOverviewResponse>(`/projects/${projectId}/overview`);
}

export type ProjectRelatedCampaign = {
  id: string;
  name: string;
  status: string;
  campaign_type: string;
  primary_channel?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  budget_amount?: string | null;
  budget_currency?: string | null;
};

export async function fetchProjectCampaigns(
  projectId: string,
): Promise<{ items: ProjectRelatedCampaign[]; total: number }> {
  return apiFetch<{ items: ProjectRelatedCampaign[]; total: number }>(
    `/projects/${projectId}/campaigns`,
  );
}

export async function fetchProjectFinancials(projectId: string): Promise<ProjectFinancialsResponse> {
  return apiFetch<ProjectFinancialsResponse>(`/projects/${projectId}/financials`);
}

export async function fetchProjectExecutiveFinance(
  projectId: string,
): Promise<ProjectExecutiveFinance> {
  return apiFetch<ProjectExecutiveFinance>(`/projects/${projectId}/executive-finance`);
}

export async function fetchProjectCashFlowSummary(
  projectId: string,
): Promise<ProjectCashFlowSummary> {
  return apiFetch<ProjectCashFlowSummary>(`/projects/${projectId}/cash-flow-summary`);
}

export async function fetchProjectSchedule(projectId: string): Promise<ProjectScheduleResponse> {
  return apiFetch<ProjectScheduleResponse>(`/projects/${projectId}/schedule`);
}

export async function fetchProjectConstruction(
  projectId: string,
): Promise<ProjectConstructionResponse> {
  return apiFetch<ProjectConstructionResponse>(`/projects/${projectId}/construction`);
}

export async function fetchProjectUnits(
  projectId: string,
  params: {
    search?: string;
    availability_status?: string;
    sales_status?: string;
    leasing_status?: string;
    asset_type?: string;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  } = {},
): Promise<ProjectUnitsResponse> {
  const query = new URLSearchParams();
  if (params.search?.trim()) query.set('search', params.search.trim());
  if (params.availability_status) query.set('availability_status', params.availability_status);
  if (params.sales_status) query.set('sales_status', params.sales_status);
  if (params.leasing_status) query.set('leasing_status', params.leasing_status);
  if (params.asset_type) query.set('asset_type', params.asset_type);
  if (params.page) query.set('page', String(params.page));
  if (params.page_size) query.set('page_size', String(params.page_size));
  if (params.sort_by) query.set('sort_by', params.sort_by);
  if (params.sort_order) query.set('sort_order', params.sort_order);
  const qs = query.toString();
  return apiFetch<ProjectUnitsResponse>(`/projects/${projectId}/units${qs ? `?${qs}` : ''}`);
}

export async function fetchProjectSales(projectId: string): Promise<ProjectSalesResponse> {
  return apiFetch<ProjectSalesResponse>(`/projects/${projectId}/sales`);
}

export async function fetchProjectLeasing(projectId: string): Promise<ProjectLeasingResponse> {
  return apiFetch<ProjectLeasingResponse>(`/projects/${projectId}/leasing`);
}

export async function fetchProjectInvestors(projectId: string): Promise<ProjectInvestorsResponse> {
  return apiFetch<ProjectInvestorsResponse>(`/projects/${projectId}/investors`);
}

export async function fetchProjectDocuments(
  projectId: string,
  params: { search?: string; category?: string; status?: string; page?: number; page_size?: number } = {},
): Promise<ProjectDocumentsResponse> {
  const query = new URLSearchParams();
  if (params.search?.trim()) query.set('search', params.search.trim());
  if (params.category) query.set('category', params.category);
  if (params.status) query.set('status', params.status);
  if (params.page) query.set('page', String(params.page));
  if (params.page_size) query.set('page_size', String(params.page_size));
  const qs = query.toString();
  return apiFetch<ProjectDocumentsResponse>(
    `/projects/${projectId}/documents${qs ? `?${qs}` : ''}`,
  );
}

export async function fetchProjectDetailActivity(
  projectId: string,
  params: { search?: string; page?: number; page_size?: number } = {},
): Promise<ProjectActivityListResponse> {
  const query = new URLSearchParams();
  if (params.search?.trim()) query.set('search', params.search.trim());
  if (params.page) query.set('page', String(params.page));
  if (params.page_size) query.set('page_size', String(params.page_size));
  const qs = query.toString();
  return apiFetch<ProjectActivityListResponse>(
    `/projects/${projectId}/activity${qs ? `?${qs}` : ''}`,
  );
}

export async function fetchProjectAlerts(projectId: string): Promise<ProjectAlertListResponse> {
  return apiFetch<ProjectAlertListResponse>(`/projects/${projectId}/alerts`);
}

export async function fetchProjectMilestones(
  projectId: string,
  days = 365,
): Promise<ProjectMilestoneListResponse> {
  return apiFetch<ProjectMilestoneListResponse>(
    `/projects/${projectId}/milestones?days=${days}`,
  );
}

export async function searchProjectDirectoryUsers(
  projectId: string,
  search?: string,
  limit = 20,
): Promise<{ items: ProjectDirectoryUser[]; total: number }> {
  const query = new URLSearchParams();
  if (search?.trim()) query.set('search', search.trim());
  query.set('limit', String(limit));
  return apiFetch(`/projects/${projectId}/directory-users?${query.toString()}`);
}

/* --------------------------------------------------------------------- */
/* Sprint 10A4A — Project budget foundation                              */
/* --------------------------------------------------------------------- */

export type BudgetVersionStatus =
  | 'draft'
  | 'in_review'
  | 'approved'
  | 'rejected'
  | 'superseded'
  | 'archived';

export interface BudgetPermissions {
  can_view: boolean;
  can_edit: boolean;
  can_manage: boolean;
  can_approve: boolean;
  can_export: boolean;
  can_manage_cost_codes: boolean;
}

export interface BudgetVersion {
  id: string;
  project_id: string;
  name: string;
  version_number: number;
  status: BudgetVersionStatus;
  description: string | null;
  currency: string;
  effective_date: string | null;
  is_current: boolean;
  original_budget_total: string | null;
  current_budget_total: string | null;
  approved_at: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BudgetLine {
  id: string;
  budget_version_id: string;
  category_id: string;
  cost_code_id: string | null;
  line_number: string;
  name: string;
  description: string | null;
  original_budget: string;
  approved_revisions: string;
  current_budget: string;
  category_code: string | null;
  category_name: string | null;
  cost_code: string | null;
  cost_code_name: string | null;
  notes: string | null;
  is_active: boolean;
}

export interface BudgetCategory {
  id: string;
  code: string;
  name: string;
  category_type: string;
  is_active: boolean;
  is_system: boolean;
}

export interface BudgetSummary {
  budget_version: BudgetVersion | null;
  totals: Record<string, MetricValue>;
  categories: Array<{
    category_id: string;
    category_code: string;
    category_name: string;
    category_type: string;
    original_budget: string;
    approved_revisions: string;
    current_budget: string;
    line_count: number;
  }>;
  data_completeness: Record<string, string>;
  permissions: BudgetPermissions;
  warnings: string[];
  legacy_budgets: Array<Record<string, unknown>>;
}

export async function fetchBudgetSummary(projectId: string): Promise<BudgetSummary> {
  return apiFetch<BudgetSummary>(`/projects/${projectId}/budget-summary`);
}

export async function fetchBudgetVersions(
  projectId: string,
): Promise<{ items: BudgetVersion[]; total: number }> {
  return apiFetch(`/projects/${projectId}/budgets`);
}

export async function createBudgetVersion(
  projectId: string,
  input: { name: string; description?: string | null; effective_date?: string | null },
): Promise<BudgetVersion> {
  return apiFetch(`/projects/${projectId}/budgets`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function submitBudgetVersion(projectId: string, budgetId: string): Promise<BudgetVersion> {
  return apiFetch(`/projects/${projectId}/budgets/${budgetId}/submit`, { method: 'POST' });
}

export async function approveBudgetVersion(projectId: string, budgetId: string): Promise<BudgetVersion> {
  return apiFetch(`/projects/${projectId}/budgets/${budgetId}/approve`, { method: 'POST' });
}

export async function rejectBudgetVersion(projectId: string, budgetId: string): Promise<BudgetVersion> {
  return apiFetch(`/projects/${projectId}/budgets/${budgetId}/reject`, { method: 'POST' });
}

export async function cloneBudgetVersion(projectId: string, budgetId: string): Promise<BudgetVersion> {
  return apiFetch(`/projects/${projectId}/budgets/${budgetId}/clone`, { method: 'POST' });
}

export async function fetchBudgetLines(
  projectId: string,
  budgetId: string,
): Promise<{ items: BudgetLine[]; total: number }> {
  return apiFetch(`/projects/${projectId}/budgets/${budgetId}/lines`);
}

export async function createBudgetLine(
  projectId: string,
  budgetId: string,
  input: {
    category_id: string;
    cost_code_id?: string | null;
    line_number: string;
    name: string;
    original_budget: number | string;
    notes?: string | null;
  },
): Promise<BudgetLine> {
  return apiFetch(`/projects/${projectId}/budgets/${budgetId}/lines`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function fetchBudgetCategories(): Promise<BudgetCategory[]> {
  return apiFetch<BudgetCategory[]>('/budget-categories');
}

export interface BudgetRevision {
  id: string;
  budget_version_id: string;
  revision_number: number;
  title: string;
  description: string | null;
  status: 'draft' | 'in_review' | 'approved' | 'rejected' | 'cancelled';
  amount: string;
  effective_date: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  created_at: string;
}

export async function fetchBudgetRevisions(
  projectId: string,
  budgetId: string,
): Promise<{ items: BudgetRevision[]; total: number }> {
  return apiFetch(`/projects/${projectId}/budgets/${budgetId}/revisions`);
}

export async function exportBudgetLinesCsv(projectId: string, budgetId: string): Promise<Blob> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/projects/${projectId}/budgets/${budgetId}/export`,
    { credentials: 'include' },
  );
  if (!response.ok) {
    throw new Error('Budget export failed');
  }
  return response.blob();
}

/* --------------------------------------------------------------------- */
/* Sprint 10A4B — Commitments, bills, payments, retainage                */
/* --------------------------------------------------------------------- */

export interface ProjectCommitment {
  id: string;
  commitment_number: string;
  commitment_type: string;
  title: string;
  status: string;
  vendor_id: string;
  original_amount: string;
  approved_change_orders: string;
  current_committed_amount: string;
  invoiced_amount: string;
  paid_amount: string;
  retained_amount: string;
  remaining_commitment: string;
  currency: string;
  updated_at: string;
}

export interface ProjectVendorBill {
  id: string;
  bill_number: string;
  vendor_invoice_number: string;
  vendor_id: string;
  commitment_id: string | null;
  status: string;
  invoice_date: string;
  due_date: string | null;
  subtotal: string;
  retainage_amount: string;
  approved_amount: string;
  paid_amount: string;
  balance_due: string;
  currency: string;
  updated_at: string;
}

export interface ProjectPayment {
  id: string;
  payment_number: string;
  vendor_id: string;
  payment_date: string;
  status: string;
  payment_method: string;
  gross_amount: string;
  reference_number: string | null;
  currency: string;
  updated_at: string;
}

export interface RetainageSummary {
  total_retained: MetricValue;
  total_released: MetricValue;
  outstanding_retainage: MetricValue;
}

export interface CostSummary {
  source: string;
  totals: Record<string, MetricValue>;
  warnings: string[];
  data_completeness: Record<string, string>;
}

export async function fetchCostSummary(projectId: string): Promise<CostSummary> {
  return apiFetch<CostSummary>(`/projects/${projectId}/cost-summary`);
}

export async function fetchProjectCommitments(
  projectId: string,
): Promise<{ items: ProjectCommitment[]; total: number }> {
  return apiFetch(`/projects/${projectId}/commitments`);
}

export async function fetchProjectVendorBills(
  projectId: string,
): Promise<{ items: ProjectVendorBill[]; total: number }> {
  return apiFetch(`/projects/${projectId}/vendor-bills`);
}

export async function fetchProjectPayments(
  projectId: string,
): Promise<{ items: ProjectPayment[]; total: number }> {
  return apiFetch(`/projects/${projectId}/payments`);
}

export async function fetchRetainageSummary(projectId: string): Promise<RetainageSummary> {
  return apiFetch<RetainageSummary>(`/projects/${projectId}/retainage`);
}

export async function createProjectVendor(
  projectId: string,
  input: { vendor_id: string; role?: string },
): Promise<unknown> {
  return apiFetch(`/projects/${projectId}/vendors`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function createVendor(input: {
  name: string;
  vendor_code?: string;
  vendor_type?: string;
}): Promise<{ id: string; name: string; vendor_code: string }> {
  return apiFetch('/vendors', {
    method: 'POST',
    body: JSON.stringify({
      vendor_type: 'other',
      status: 'active',
      default_currency: 'USD',
      ...input,
    }),
  });
}

export async function createCommitment(
  projectId: string,
  input: {
    vendor_id: string;
    commitment_type: string;
    title: string;
    lines: Array<{ budget_line_id: string; description: string; original_amount: string | number }>;
  },
): Promise<ProjectCommitment> {
  return apiFetch(`/projects/${projectId}/commitments`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function transitionCommitment(
  projectId: string,
  commitmentId: string,
  action: 'submit' | 'approve' | 'reject' | 'execute' | 'activate' | 'complete' | 'close' | 'cancel',
): Promise<ProjectCommitment> {
  return apiFetch(`/projects/${projectId}/commitments/${commitmentId}/${action}`, {
    method: 'POST',
  });
}

export async function transitionVendorBill(
  projectId: string,
  billId: string,
  action: 'submit' | 'approve' | 'reject' | 'post' | 'void',
): Promise<ProjectVendorBill> {
  return apiFetch(`/projects/${projectId}/vendor-bills/${billId}/${action}`, {
    method: 'POST',
  });
}

// --- Google Drive mapping / sync (Creative Studio) ---

export type DriveSyncStatusValue = 'IDLE' | 'RUNNING' | 'SUCCESS' | 'FAILED' | string;

export type ProjectDriveMapping = {
  id: string;
  project_id: string;
  drive_folder_id: string;
  drive_sync_enabled: boolean;
  last_drive_sync_at: string | null;
  last_successful_sync_at: string | null;
  last_sync_status: DriveSyncStatusValue;
  last_sync_error: string | null;
  force_full_sync: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type ProjectDriveMappingUpsert = {
  drive_folder_id: string;
  drive_sync_enabled: boolean;
};

export type ProjectDriveStatus = {
  project_id: string;
  mapped: boolean;
  drive_folder_id?: string | null;
  drive_sync_enabled: boolean;
  last_sync_status: DriveSyncStatusValue;
  last_drive_sync_at: string | null;
  last_successful_sync_at: string | null;
  last_sync_error: string | null;
  force_full_sync: boolean;
  sync_started_at?: string | null;
  has_change_token: boolean;
  background_sync_enabled: boolean;
  background_sync_interval_minutes: number;
};

export type DriveSyncDuplicateItem = {
  drive_file_id: string;
  existing_asset_id: string;
  checksum: string;
  filename: string;
};

export type DriveSyncErrorItem = {
  path: string;
  code: string;
  message: string;
};

export type DriveSyncResult = {
  scanned: number;
  created: number;
  updated: number;
  unchanged: number;
  missing: number;
  skipped: number;
  possible_duplicates: DriveSyncDuplicateItem[];
  errors: DriveSyncErrorItem[];
  dry_run: boolean;
  warnings: string[];
};

export async function fetchProjectDriveMapping(
  projectId: string,
): Promise<ProjectDriveMapping> {
  return apiFetch<ProjectDriveMapping>(`/projects/${projectId}/drive/mapping`);
}

export async function upsertProjectDriveMapping(
  projectId: string,
  input: ProjectDriveMappingUpsert,
): Promise<ProjectDriveMapping> {
  return apiFetch<ProjectDriveMapping>(`/projects/${projectId}/drive/mapping`, {
    method: 'PUT',
    body: JSON.stringify(input),
  });
}

export async function fetchProjectDriveStatus(
  projectId: string,
): Promise<ProjectDriveStatus> {
  return apiFetch<ProjectDriveStatus>(`/projects/${projectId}/drive/status`);
}

export async function syncProjectDrive(
  projectId: string,
  options?: { dryRun?: boolean; forceFull?: boolean },
): Promise<DriveSyncResult> {
  const params = new URLSearchParams();
  if (options?.dryRun) params.set('dry_run', 'true');
  if (options?.forceFull) params.set('force_full', 'true');
  const query = params.toString();
  return apiFetch<DriveSyncResult>(
    `/projects/${projectId}/drive/sync${query ? `?${query}` : ''}`,
    { method: 'POST' },
  );
}
