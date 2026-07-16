import { apiFetch } from '@/lib/api/client';
import { fetchLeads } from '@/lib/api/leads';
import { fetchReservations } from '@/lib/api/inventory';

export const OPPORTUNITY_STAGES = [
  'new',
  'qualified',
  'meeting_scheduled',
  'meeting_completed',
  'inventory_matching',
  'proposal_preparation',
  'proposal_sent',
  'negotiation',
  'soft_hold',
  'reservation',
  'deposit_pending',
  'contract',
  'closing_handoff',
  'won',
  'lost',
  'dormant',
  'cancelled',
] as const;

export type OpportunityStage = (typeof OPPORTUNITY_STAGES)[number];

export const CLOSED_OPPORTUNITY_STAGES: readonly OpportunityStage[] = [
  'won',
  'lost',
  'dormant',
  'cancelled',
];

export const OPPORTUNITY_NEXT_ACTIONS = [
  'call',
  'meeting',
  'email',
  'whatsapp',
  'site_visit',
  'proposal',
  'reservation_follow_up',
  'deposit_follow_up',
  'contract_follow_up',
  'closing_follow_up',
] as const;

export type OpportunityNextAction = (typeof OPPORTUNITY_NEXT_ACTIONS)[number];

export const OPPORTUNITY_LOSS_REASONS = [
  'budget',
  'financing',
  'competitor',
  'no_response',
  'timeline',
  'location',
  'inventory',
  'internal',
  'other',
] as const;

export type OpportunityLossReason = (typeof OPPORTUNITY_LOSS_REASONS)[number];

export const OPPORTUNITY_PARTY_TYPES = ['lead', 'investor'] as const;
export type OpportunityPartyType = (typeof OPPORTUNITY_PARTY_TYPES)[number];

export const OPPORTUNITY_PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const;
export type OpportunityPriority = (typeof OPPORTUNITY_PRIORITIES)[number];

export interface SalesOpportunity {
  id: string;
  opportunity_code: string;
  display_id: string | null;
  lead_id: string | null;
  party_id: string;
  party_type: OpportunityPartyType;
  assigned_sales_user_id: string | null;
  stage: OpportunityStage;
  probability: number;
  expected_close_date: string | null;
  expected_revenue: string | null;
  currency: string;
  priority: OpportunityPriority;
  source: string | null;
  current_risks: unknown;
  next_action: OpportunityNextAction | null;
  next_action_date: string | null;
  last_contact_at: string | null;
  notes: string | null;
  loss_reason: OpportunityLossReason | null;
  loss_notes: string | null;
  dormant_review_date: string | null;
  cancelled_reason: string | null;
  reservation_id: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SalesOpportunityListResponse {
  items: SalesOpportunity[];
  total: number;
  offset: number;
  limit: number;
}

export interface SalesOpportunityInput {
  party_id: string;
  party_type: OpportunityPartyType;
  lead_id?: string | null;
  display_id?: string | null;
  assigned_sales_user_id?: string | null;
  stage?: OpportunityStage;
  probability?: number;
  expected_close_date?: string | null;
  expected_revenue?: number | null;
  currency?: string;
  priority?: OpportunityPriority;
  source?: string | null;
  next_action?: OpportunityNextAction | null;
  next_action_date?: string | null;
  notes?: string | null;
  is_demo?: boolean;
}

export interface SalesOpportunityFilters {
  search?: string;
  stage?: OpportunityStage | '';
  assigned_sales_user_id?: string;
  party_id?: string;
  lead_id?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  offset?: number;
  limit?: number;
}

export interface PipelineStageGroup {
  stage: string;
  count: number;
  opportunities: SalesOpportunity[];
}

export interface PipelineSummary {
  stages: Record<string, number>;
  total: number;
  groups?: PipelineStageGroup[] | null;
}

export interface DashboardMetrics {
  open_opportunities: number;
  pipeline_value: string;
  won_count: number;
  lost_count: number;
  no_follow_up: number;
  dormant_count: number;
  expected_closings_30d: number;
}

export interface ExecutiveSalesSummary {
  pipeline_value: string;
  weighted_pipeline_value: string;
  high_risk_count: number;
  no_follow_up_count: number;
  dormant_count: number;
  expected_closings_30d: number;
}

export interface OpportunityTimelineEntry {
  id: string;
  opportunity_id: string;
  event_type: string;
  from_stage: string | null;
  to_stage: string | null;
  from_probability: number | null;
  to_probability: number | null;
  actor_user_id: string | null;
  notes: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface OpportunityInventoryLink {
  id: string;
  opportunity_id: string;
  inventory_asset_id: string;
  match_reason: string | null;
  rejection_reason: string | null;
  is_favorite: boolean;
  shortlisted_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface OpportunityProjectLink {
  id: string;
  opportunity_id: string;
  project_id: string;
  created_at: string;
}

export interface SalesHomeKpis {
  new_leads: number;
  qualified_leads: number;
  active_opportunities: number;
  pipeline_value_by_currency: Record<string, string>;
  weighted_pipeline_by_currency: Record<string, string>;
  meetings_scheduled: number;
  proposals_pending: number;
  active_soft_holds: number;
  reservations_pending: number;
  deposits_pending: number;
  under_contract: number;
  won_this_month: number;
  lost_this_month: number;
  no_follow_up: number;
  dormant_count: number;
  expected_closings_30d: number;
}

export type SalesKpiKey =
  | 'new_leads'
  | 'qualified_leads'
  | 'active_opportunities'
  | 'pipeline_value'
  | 'weighted_pipeline'
  | 'meetings_scheduled'
  | 'proposals_pending'
  | 'active_soft_holds'
  | 'reservations_pending'
  | 'deposits_pending'
  | 'under_contract'
  | 'won_this_month'
  | 'lost_this_month';

export interface StageChangeInput {
  stage: OpportunityStage;
  notes?: string | null;
  loss_reason?: OpportunityLossReason | null;
  loss_notes?: string | null;
  dormant_review_date?: string | null;
  cancelled_reason?: string | null;
}

export interface ProbabilityChangeInput {
  probability: number;
  reason?: string | null;
}

export interface NextActionInput {
  next_action: OpportunityNextAction;
  next_action_date: string;
}

export interface LinkInventoryInput {
  inventory_asset_id: string;
  match_reason?: string | null;
  is_favorite?: boolean;
  notes?: string | null;
}

export interface LinkProjectInput {
  project_id: string;
}

export const PIPELINE_COLUMNS: {
  id: string;
  dropStage: OpportunityStage;
  stages: OpportunityStage[];
}[] = [
  { id: 'qualification', dropStage: 'qualified', stages: ['new', 'qualified'] },
  { id: 'meeting_scheduled', dropStage: 'meeting_scheduled', stages: ['meeting_scheduled'] },
  { id: 'meeting_completed', dropStage: 'meeting_completed', stages: ['meeting_completed'] },
  { id: 'inventory_matching', dropStage: 'inventory_matching', stages: ['inventory_matching'] },
  { id: 'proposal_preparation', dropStage: 'proposal_preparation', stages: ['proposal_preparation'] },
  { id: 'proposal_sent', dropStage: 'proposal_sent', stages: ['proposal_sent'] },
  { id: 'negotiation', dropStage: 'negotiation', stages: ['negotiation'] },
  { id: 'soft_hold', dropStage: 'soft_hold', stages: ['soft_hold'] },
  { id: 'reservation', dropStage: 'reservation', stages: ['reservation'] },
  { id: 'deposit_pending', dropStage: 'deposit_pending', stages: ['deposit_pending'] },
  { id: 'contract', dropStage: 'contract', stages: ['contract'] },
  { id: 'closing_handoff', dropStage: 'closing_handoff', stages: ['closing_handoff'] },
  { id: 'won', dropStage: 'won', stages: ['won'] },
  { id: 'lost', dropStage: 'lost', stages: ['lost'] },
  { id: 'dormant', dropStage: 'dormant', stages: ['dormant'] },
];

export const ALLOWED_STAGE_TRANSITIONS: Record<OpportunityStage, readonly OpportunityStage[]> = {
  new: ['qualified', 'lost', 'dormant', 'cancelled'],
  qualified: ['meeting_scheduled', 'inventory_matching', 'lost', 'dormant', 'cancelled'],
  meeting_scheduled: ['meeting_completed', 'qualified', 'lost', 'dormant', 'cancelled'],
  meeting_completed: ['inventory_matching', 'proposal_preparation', 'lost', 'dormant', 'cancelled'],
  inventory_matching: ['proposal_preparation', 'soft_hold', 'lost', 'dormant', 'cancelled'],
  proposal_preparation: ['proposal_sent', 'lost', 'dormant', 'cancelled'],
  proposal_sent: ['negotiation', 'lost', 'dormant', 'cancelled'],
  negotiation: ['soft_hold', 'reservation', 'lost', 'dormant', 'cancelled'],
  soft_hold: ['reservation', 'inventory_matching', 'lost', 'dormant', 'cancelled'],
  reservation: ['deposit_pending', 'contract', 'lost', 'dormant', 'cancelled'],
  deposit_pending: ['contract', 'lost', 'dormant', 'cancelled'],
  contract: ['closing_handoff', 'won', 'lost', 'dormant', 'cancelled'],
  closing_handoff: ['won', 'lost', 'dormant', 'cancelled'],
  dormant: ['new', 'qualified', 'cancelled'],
  won: [],
  lost: [],
  cancelled: [],
};

function buildQuery(filters: Record<string, string | number | boolean | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === '' || value === false) continue;
    params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchOpportunities(
  filters: SalesOpportunityFilters = {},
): Promise<SalesOpportunityListResponse> {
  return apiFetch<SalesOpportunityListResponse>(
    `/sales/opportunities${buildQuery({
      search: filters.search?.trim(),
      stage: filters.stage || undefined,
      assigned_sales_user_id: filters.assigned_sales_user_id,
      party_id: filters.party_id,
      lead_id: filters.lead_id,
      include_archived: filters.include_archived,
      sort_by: filters.sort_by ?? 'updated_at',
      sort_dir: filters.sort_dir ?? 'desc',
      offset: filters.offset ?? 0,
      limit: filters.limit ?? 50,
    })}`,
  );
}

export async function fetchOpportunity(id: string): Promise<SalesOpportunity> {
  return apiFetch<SalesOpportunity>(`/sales/opportunities/${id}`);
}

export async function createOpportunity(input: SalesOpportunityInput): Promise<SalesOpportunity> {
  return apiFetch<SalesOpportunity>('/sales/opportunities', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateOpportunity(
  id: string,
  input: Partial<SalesOpportunityInput>,
): Promise<SalesOpportunity> {
  return apiFetch<SalesOpportunity>(`/sales/opportunities/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function archiveOpportunity(id: string): Promise<SalesOpportunity> {
  return apiFetch<SalesOpportunity>(`/sales/opportunities/${id}`, { method: 'DELETE' });
}

export async function restoreOpportunity(id: string): Promise<SalesOpportunity> {
  return apiFetch<SalesOpportunity>(`/sales/opportunities/${id}/restore`, { method: 'POST' });
}

export async function changeOpportunityStage(
  id: string,
  input: StageChangeInput,
): Promise<SalesOpportunity> {
  return apiFetch<SalesOpportunity>(`/sales/opportunities/${id}/stage`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function changeOpportunityProbability(
  id: string,
  input: ProbabilityChangeInput,
): Promise<SalesOpportunity> {
  return apiFetch<SalesOpportunity>(`/sales/opportunities/${id}/probability`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateOpportunityNextAction(
  id: string,
  input: NextActionInput,
): Promise<SalesOpportunity> {
  return apiFetch<SalesOpportunity>(`/sales/opportunities/${id}/next-action`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function linkOpportunityInventory(
  id: string,
  input: LinkInventoryInput,
): Promise<OpportunityInventoryLink> {
  return apiFetch<OpportunityInventoryLink>(`/sales/opportunities/${id}/inventory`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function unlinkOpportunityInventory(
  opportunityId: string,
  inventoryAssetId: string,
): Promise<void> {
  await apiFetch<void>(`/sales/opportunities/${opportunityId}/inventory/${inventoryAssetId}`, {
    method: 'DELETE',
  });
}

export async function linkOpportunityProject(
  id: string,
  input: LinkProjectInput,
): Promise<OpportunityProjectLink> {
  return apiFetch<OpportunityProjectLink>(`/sales/opportunities/${id}/projects`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function unlinkOpportunityProject(
  opportunityId: string,
  projectId: string,
): Promise<void> {
  await apiFetch<void>(`/sales/opportunities/${opportunityId}/projects/${projectId}`, {
    method: 'DELETE',
  });
}

export async function fetchOpportunityTimeline(id: string): Promise<OpportunityTimelineEntry[]> {
  return apiFetch<OpportunityTimelineEntry[]>(`/sales/opportunities/${id}/timeline`);
}

export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  return apiFetch<DashboardMetrics>('/sales/opportunities/dashboard/metrics');
}

export async function fetchPipelineSummary(includeDetails = false): Promise<PipelineSummary> {
  return apiFetch<PipelineSummary>(
    `/sales/opportunities/pipeline${buildQuery({ include_details: includeDetails })}`,
  );
}

export async function fetchExecutiveSalesSummary(): Promise<ExecutiveSalesSummary> {
  return apiFetch<ExecutiveSalesSummary>('/sales/opportunities/executive-summary');
}

function isOpenStage(stage: OpportunityStage): boolean {
  return !CLOSED_OPPORTUNITY_STAGES.includes(stage);
}

function aggregatePipelineByCurrency(opportunities: SalesOpportunity[]): {
  pipeline: Record<string, string>;
  weighted: Record<string, string>;
} {
  const pipeline: Record<string, number> = {};
  const weighted: Record<string, number> = {};
  for (const opp of opportunities) {
    if (!isOpenStage(opp.stage) || !opp.expected_revenue) continue;
    const amount = Number(opp.expected_revenue);
    if (Number.isNaN(amount)) continue;
    const currency = opp.currency || 'USD';
    pipeline[currency] = (pipeline[currency] ?? 0) + amount;
    weighted[currency] = (weighted[currency] ?? 0) + (amount * opp.probability) / 100;
  }
  return {
    pipeline: Object.fromEntries(Object.entries(pipeline).map(([c, v]) => [c, String(v)])),
    weighted: Object.fromEntries(Object.entries(weighted).map(([c, v]) => [c, String(v)])),
  };
}

function isInCurrentMonth(isoDate: string): boolean {
  const date = new Date(isoDate);
  const now = new Date();
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
}

export async function fetchSalesHomeKpis(): Promise<SalesHomeKpis> {
  const [
    newLeads,
    qualifiedLeads,
    meetingLeads,
    metrics,
    openOpportunities,
    wonOpportunities,
    lostOpportunities,
    softHolds,
    pendingReservations,
    depositPending,
    contractStage,
    proposalStages,
  ] = await Promise.all([
    fetchLeads({ status: 'New' }),
    fetchLeads({ status: 'Qualified' }),
    fetchLeads({ status: 'Meeting Scheduled' }),
    fetchDashboardMetrics(),
    fetchOpportunities({ limit: 200, sort_by: 'updated_at', sort_dir: 'desc' }),
    fetchOpportunities({ stage: 'won', limit: 200 }),
    fetchOpportunities({ stage: 'lost', limit: 200 }),
    fetchReservations({ reservation_type: 'soft_hold', active_only: true, page_size: 1 }),
    fetchReservations({ status: 'requested', page_size: 1 }),
    fetchReservations({ status: 'deposit_pending', page_size: 1 }),
    fetchOpportunities({ stage: 'contract', limit: 1 }),
    fetchOpportunities({ limit: 200 }),
  ]);

  const openItems = openOpportunities.items.filter((o) => isOpenStage(o.stage));
  const { pipeline, weighted } = aggregatePipelineByCurrency(openItems);

  const proposalsPending = proposalStages.items.filter((o) =>
    ['proposal_preparation', 'proposal_sent'].includes(o.stage),
  ).length;

  const wonThisMonth = wonOpportunities.items.filter((o) => isInCurrentMonth(o.updated_at)).length;
  const lostThisMonth = lostOpportunities.items.filter((o) => isInCurrentMonth(o.updated_at)).length;

  return {
    new_leads: newLeads.total,
    qualified_leads: qualifiedLeads.total,
    active_opportunities: metrics.open_opportunities,
    pipeline_value_by_currency: pipeline,
    weighted_pipeline_by_currency: weighted,
    meetings_scheduled: meetingLeads.total,
    proposals_pending: proposalsPending,
    active_soft_holds: softHolds.total,
    reservations_pending: pendingReservations.total,
    deposits_pending: depositPending.total,
    under_contract: contractStage.total,
    won_this_month: wonThisMonth,
    lost_this_month: lostThisMonth,
    no_follow_up: metrics.no_follow_up,
    dormant_count: metrics.dormant_count,
    expected_closings_30d: metrics.expected_closings_30d,
  };
}

export function formatMoney(value: string | null, currency: string, locale = 'tr'): string {
  if (!value) return '—';
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString(locale)} ${currency}`;
  }
}

export function formatCurrencyTotals(totals: Record<string, string>, locale = 'tr'): string {
  const entries = Object.entries(totals);
  if (entries.length === 0) return '—';
  return entries.map(([currency, value]) => formatMoney(value, currency, locale)).join(' · ');
}

export function formatShortDate(value: string | null, locale = 'tr'): string {
  if (!value) return '—';
  const date = new Date(value.includes('T') ? value : `${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' });
}

export function canTransitionStage(from: OpportunityStage, to: OpportunityStage): boolean {
  return ALLOWED_STAGE_TRANSITIONS[from]?.includes(to) ?? false;
}

export function stageRequiresModal(stage: OpportunityStage): boolean {
  return stage === 'won' || stage === 'lost' || stage === 'dormant' || stage === 'cancelled';
}
