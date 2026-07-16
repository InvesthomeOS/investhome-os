import { apiFetch } from './client';

export type ReadinessCaseStatus =
  | 'not_started'
  | 'in_progress'
  | 'blocked'
  | 'ready_for_contract'
  | 'contract_preparation'
  | 'signature_pending'
  | 'contract_signed'
  | 'ready_for_closing_handoff'
  | 'handed_off'
  | 'cancelled'
  | 'archived';

export type ReadinessRequirementStatus =
  | 'missing'
  | 'pending'
  | 'received'
  | 'under_review'
  | 'verified'
  | 'rejected'
  | 'waived'
  | 'expired'
  | 'not_applicable';

export type ReadinessViewName =
  | 'overview'
  | 'in_progress'
  | 'blocked'
  | 'deposit_pending'
  | 'documents_missing'
  | 'signature_pending'
  | 'ready_for_handoff'
  | 'handed_off'
  | 'archived';

export interface ReadinessRequirement {
  id: string;
  readiness_case_id: string;
  requirement_type: string;
  template_group: string | null;
  title: string;
  description: string | null;
  status: ReadinessRequirementStatus;
  is_mandatory: boolean;
  source_entity_type: string | null;
  source_entity_id: string | null;
  due_at: string | null;
  verified_at: string | null;
  blocked_reason: string | null;
  notes: string | null;
}

export interface DepositSummary {
  reservation_id: string | null;
  deposit_amount: string | null;
  received_amount: string | null;
  remaining_amount: string | null;
  currency: string | null;
  due_at: string | null;
  is_overdue: boolean;
  finance_transaction_id: string | null;
  status: string;
}

export interface ReadinessCase {
  id: string;
  case_code: string;
  opportunity_id: string;
  lead_id: string | null;
  party_id: string | null;
  inventory_asset_id: string | null;
  reservation_id: string | null;
  proposal_id: string | null;
  status: ReadinessCaseStatus;
  readiness_percentage: number;
  target_contract_date: string | null;
  target_closing_handoff_date: string | null;
  assigned_sales_user_id: string | null;
  assigned_legal_user_id: string | null;
  assigned_finance_user_id: string | null;
  blocker_summary: string | null;
  notes: string | null;
  handoff_requested_at: string | null;
  handoff_approved_at: string | null;
  handoff_return_reason: string | null;
  signature_status: string | null;
  signed_document_id: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  requirements?: ReadinessRequirement[];
  deposit_summary?: DepositSummary | null;
  opportunity_code?: string | null;
  party_name?: string | null;
  inventory_display_id?: string | null;
  missing_mandatory_count?: number;
}

export interface ReadinessDashboardKpis {
  active_cases: number;
  blocked: number;
  reservation_approved: number;
  deposit_pending: number;
  deposit_received: number;
  documents_missing: number;
  contract_preparation: number;
  signature_pending: number;
  ready_for_handoff: number;
  handed_off_this_month: number;
}

export interface ReadinessStatusHistoryEntry {
  id: string;
  previous_status: string | null;
  new_status: string;
  reason: string | null;
  changed_by_user_id: string | null;
  effective_at: string;
}

export async function fetchReadinessKpis(): Promise<ReadinessDashboardKpis> {
  return apiFetch<ReadinessDashboardKpis>('/sales/readiness/dashboard/kpis');
}

export async function fetchReadinessCases(params: {
  view?: ReadinessViewName;
  opportunity_id?: string;
  search?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<{ items: ReadinessCase[]; total: number }> {
  const query = new URLSearchParams();
  if (params.view) query.set('view', params.view);
  if (params.opportunity_id) query.set('opportunity_id', params.opportunity_id);
  if (params.search) query.set('search', params.search);
  if (params.limit) query.set('limit', String(params.limit));
  if (params.offset) query.set('offset', String(params.offset));
  const suffix = query.toString() ? `?${query}` : '';
  return apiFetch(`/sales/readiness/cases${suffix}`);
}

export async function fetchReadinessCase(id: string): Promise<ReadinessCase> {
  return apiFetch<ReadinessCase>(`/sales/readiness/cases/${id}`);
}

export async function createReadinessCase(
  opportunityId: string,
  payload: Record<string, unknown> = {},
): Promise<ReadinessCase> {
  return apiFetch<ReadinessCase>(`/sales/readiness/opportunities/${opportunityId}/cases`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function recalculateReadinessCase(id: string): Promise<ReadinessCase> {
  return apiFetch<ReadinessCase>(`/sales/readiness/cases/${id}/recalculate`, { method: 'POST' });
}

export async function fetchOpportunityReadiness(opportunityId: string): Promise<ReadinessCase | null> {
  return apiFetch<ReadinessCase | null>(`/sales/readiness/opportunities/${opportunityId}/summary`);
}

export async function verifyRequirement(id: string, notes?: string): Promise<ReadinessRequirement> {
  return apiFetch<ReadinessRequirement>(`/sales/readiness/requirements/${id}/verify`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

export async function waiveRequirement(id: string, reason: string): Promise<ReadinessRequirement> {
  return apiFetch<ReadinessRequirement>(`/sales/readiness/requirements/${id}/waive`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function requestHandoff(id: string, notes?: string): Promise<ReadinessCase> {
  return apiFetch<ReadinessCase>(`/sales/readiness/cases/${id}/handoff/request`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

export async function approveHandoff(id: string, notes?: string): Promise<ReadinessCase> {
  return apiFetch<ReadinessCase>(`/sales/readiness/cases/${id}/handoff/approve`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

export async function returnHandoff(id: string, reason: string): Promise<ReadinessCase> {
  return apiFetch<ReadinessCase>(`/sales/readiness/cases/${id}/handoff/return`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function fetchReadinessStatusHistory(caseId: string): Promise<ReadinessStatusHistoryEntry[]> {
  return apiFetch<ReadinessStatusHistoryEntry[]>(`/sales/readiness/cases/${caseId}/status-history`);
}

export async function markSignaturePending(id: string): Promise<ReadinessCase> {
  return apiFetch<ReadinessCase>(`/sales/readiness/cases/${id}/signature-pending`, { method: 'POST' });
}

export async function markContractSigned(id: string, signedDocumentId?: string): Promise<ReadinessCase> {
  return apiFetch<ReadinessCase>(`/sales/readiness/cases/${id}/contract-signed`, {
    method: 'POST',
    body: JSON.stringify({ signed_document_id: signedDocumentId }),
  });
}

export async function createReadinessFollowUp(
  caseId: string,
  payload: { follow_up_type?: string; title?: string; notes?: string },
): Promise<unknown> {
  return apiFetch(`/sales/readiness/cases/${caseId}/follow-ups`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
