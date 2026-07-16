import { apiFetch } from '@/lib/api/client';

export const QUALIFICATION_STATUSES = [
  'new',
  'in_review',
  'qualified',
  'requires_more_information',
  'unqualified',
] as const;

export type QualificationStatus = (typeof QUALIFICATION_STATUSES)[number];

export const INVESTMENT_OBJECTIVES = [
  'rental_income',
  'capital_appreciation',
  'personal_use',
  'diversification',
  'citizenship',
  'development',
  'other',
] as const;

export type InvestmentObjective = (typeof INVESTMENT_OBJECTIVES)[number];

export const CASH_OR_FINANCING = ['cash', 'mortgage', 'mixed', 'unknown'] as const;
export type CashOrFinancing = (typeof CASH_OR_FINANCING)[number];

export const PURCHASE_TIMELINES = ['immediate', '3_months', '6_months', '12_plus', 'unknown'] as const;
export type PurchaseTimeline = (typeof PURCHASE_TIMELINES)[number];

export const RISK_TOLERANCES = ['low', 'medium', 'high'] as const;
export type RiskTolerance = (typeof RISK_TOLERANCES)[number];

export const LEAD_INTEREST_TYPES = ['matched', 'shortlisted', 'favorite', 'rejected'] as const;
export type LeadInterestType = (typeof LEAD_INTEREST_TYPES)[number];

export const FOLLOW_UP_TYPES = ['call', 'email', 'meeting', 'whatsapp', 'site_visit', 'other'] as const;
export type FollowUpType = (typeof FOLLOW_UP_TYPES)[number];

export interface LeadQualification {
  id: string;
  lead_id: string;
  investment_objective: InvestmentObjective | null;
  investment_capacity: string | null;
  budget_min: string | null;
  budget_max: string | null;
  preferred_currency: string;
  cash_or_financing: CashOrFinancing | null;
  expected_purchase_timeline: PurchaseTimeline | null;
  preferred_markets: string[] | null;
  preferred_projects: string[] | null;
  preferred_property_types: string[] | null;
  bedrooms_min: number | null;
  bedrooms_max: number | null;
  bathrooms_min: number | null;
  bathrooms_max: number | null;
  area_min: string | null;
  area_max: string | null;
  target_rental_yield: string | null;
  expected_roi: string | null;
  risk_tolerance: RiskTolerance | null;
  decision_makers: string | null;
  accredited_investor: boolean | null;
  required_documents: string[] | null;
  current_concerns: string | null;
  sales_notes: string | null;
  qualification_status: QualificationStatus;
  qualified_at: string | null;
  qualified_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadScoreComponent {
  component_key: string;
  score: number;
  weight: string;
}

export interface LeadScore {
  id: string;
  lead_id: string;
  total_score: number;
  computed_at: string;
  computed_by_id: string | null;
  is_manual_override: boolean;
  components: LeadScoreComponent[];
}

export interface LeadInventoryInterest {
  id: string;
  lead_id: string;
  inventory_asset_id: string;
  interest_type: LeadInterestType;
  match_reason: string | null;
  rejection_reason: string | null;
  opportunity_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadFollowUp {
  id: string;
  lead_id: string;
  follow_up_type: FollowUpType;
  due_at: string;
  completed_at: string | null;
  assigned_user_id: string | null;
  notes: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface LeadTimelineEntry {
  source: string;
  event_type: string;
  actor_user_id: string | null;
  notes: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface LeadDetailSummary {
  lead_id: string;
  opportunity_count: number;
  reservation_count: number;
  inventory_interest_count: number;
  follow_up_count: number;
  pending_follow_up_count: number;
  lead_score: number | null;
  qualification_status: QualificationStatus | null;
}

export interface LeadQualificationExecutiveSummary {
  qualified_count: number;
  unqualified_count: number;
  awaiting_review_count: number;
  avg_lead_score: number;
  without_follow_up_count: number;
  ready_for_opportunity_count: number;
}

export type LeadQualificationInput = Partial<
  Omit<LeadQualification, 'id' | 'lead_id' | 'qualified_at' | 'qualified_by_id' | 'created_at' | 'updated_at'>
>;

export async function fetchLeadQualification(leadId: string): Promise<LeadQualification> {
  return apiFetch<LeadQualification>(`/leads/${leadId}/qualification`);
}

export async function updateLeadQualification(
  leadId: string,
  input: LeadQualificationInput,
): Promise<LeadQualification> {
  return apiFetch<LeadQualification>(`/leads/${leadId}/qualification`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function changeQualificationStatus(
  leadId: string,
  status: QualificationStatus,
  notes?: string,
): Promise<LeadQualification> {
  return apiFetch<LeadQualification>(`/leads/${leadId}/qualification/status`, {
    method: 'POST',
    body: JSON.stringify({ status, notes }),
  });
}

export async function fetchLeadScore(leadId: string): Promise<LeadScore | null> {
  return apiFetch<LeadScore | null>(`/leads/${leadId}/score`);
}

export async function recalculateLeadScore(
  leadId: string,
  manualOverride?: number,
): Promise<LeadScore> {
  return apiFetch<LeadScore>(`/leads/${leadId}/score/recalculate`, {
    method: 'POST',
    body: JSON.stringify({ manual_override: manualOverride ?? null }),
  });
}

export async function fetchLeadTimeline(leadId: string): Promise<LeadTimelineEntry[]> {
  const response = await apiFetch<{ items: LeadTimelineEntry[] }>(`/leads/${leadId}/timeline`);
  return response.items;
}

export async function fetchLeadInventoryInterests(leadId: string): Promise<LeadInventoryInterest[]> {
  return apiFetch<LeadInventoryInterest[]>(`/leads/${leadId}/inventory-interests`);
}

export async function createLeadInventoryInterest(
  leadId: string,
  input: {
    inventory_asset_id: string;
    interest_type: LeadInterestType;
    match_reason?: string;
    opportunity_id?: string;
  },
): Promise<LeadInventoryInterest> {
  return apiFetch<LeadInventoryInterest>(`/leads/${leadId}/inventory-interests`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function deleteLeadInventoryInterest(leadId: string, interestId: string): Promise<void> {
  await apiFetch<void>(`/leads/${leadId}/inventory-interests/${interestId}`, { method: 'DELETE' });
}

export async function fetchLeadFollowUps(leadId: string): Promise<LeadFollowUp[]> {
  return apiFetch<LeadFollowUp[]>(`/leads/${leadId}/follow-ups`);
}

export async function createLeadFollowUp(
  leadId: string,
  input: { follow_up_type: FollowUpType; due_at: string; notes?: string; assigned_user_id?: string },
): Promise<LeadFollowUp> {
  return apiFetch<LeadFollowUp>(`/leads/${leadId}/follow-ups`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function completeLeadFollowUp(leadId: string, followUpId: string): Promise<LeadFollowUp> {
  return apiFetch<LeadFollowUp>(`/leads/${leadId}/follow-ups/${followUpId}/complete`, {
    method: 'PATCH',
  });
}

export async function fetchLeadDetailSummary(leadId: string): Promise<LeadDetailSummary> {
  return apiFetch<LeadDetailSummary>(`/leads/${leadId}/summary`);
}

export async function fetchLeadQualificationExecutiveSummary(): Promise<LeadQualificationExecutiveSummary> {
  return apiFetch<LeadQualificationExecutiveSummary>('/leads/executive/qualification-summary');
}
