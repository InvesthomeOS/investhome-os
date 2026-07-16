import { apiFetch } from '@/lib/api/client';

export const PROPOSAL_STATUSES = [
  'draft',
  'internal_review',
  'revision_requested',
  'approved',
  'sent',
  'viewed',
  'accepted',
  'rejected',
  'expired',
  'superseded',
  'archived',
] as const;

export type ProposalStatus = (typeof PROPOSAL_STATUSES)[number];

export interface SalesProposal {
  id: string;
  opportunity_id: string;
  lead_id: string | null;
  party_id: string | null;
  title: string;
  proposal_number: string;
  status: ProposalStatus;
  currency: string;
  valid_until: string | null;
  primary_project_id: string | null;
  current_version_id: string | null;
  created_by_user_id: string | null;
  assigned_sales_user_id: string | null;
  approved_by_user_id: string | null;
  approved_at: string | null;
  sent_at: string | null;
  viewed_at: string | null;
  accepted_at: string | null;
  rejected_at: string | null;
  expired_at: string | null;
  superseded_by_proposal_id: string | null;
  notes: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SalesProposalItem {
  id: string;
  proposal_version_id: string;
  inventory_asset_id: string;
  sort_order: number;
  item_title: string | null;
  approved_price_id: string;
  displayed_amount: string;
  currency: string;
  promotional_terms: string | null;
  payment_terms: string | null;
  estimated_rent: string | null;
  selected_documents: string[] | null;
  selected_media: string[] | null;
  notes: string | null;
}

export interface SalesProposalVersion {
  id: string;
  proposal_id: string;
  version_number: number;
  source_shortlist_id: string | null;
  content_snapshot: Record<string, unknown> | null;
  pricing_snapshot: Record<string, unknown> | null;
  terms_snapshot: Record<string, unknown> | null;
  branding_snapshot: Record<string, unknown> | null;
  generated_document_id: string | null;
  is_approved: boolean;
  approved_at: string | null;
  created_by_user_id: string | null;
  created_at: string;
}

export interface SalesProposalRecipient {
  id: string;
  proposal_id: string;
  party_id: string | null;
  recipient_type: string;
  is_primary: boolean;
  email_snapshot: string | null;
  language: string;
  created_at: string;
}

export interface SalesProposalDetail extends SalesProposal {
  current_version: SalesProposalVersion | null;
  items: SalesProposalItem[];
  recipients: SalesProposalRecipient[];
  stale_check: { has_stale: boolean; items: { item_id: string; stale_fields: string[] }[] } | null;
}

export interface SalesProposalListResponse {
  items: SalesProposal[];
  total: number;
  offset: number;
  limit: number;
}

export interface SalesProposalCreateInput {
  opportunity_id: string;
  title: string;
  lead_id?: string | null;
  party_id?: string | null;
  currency?: string;
  valid_until?: string | null;
  primary_project_id?: string | null;
  assigned_sales_user_id?: string | null;
  notes?: string | null;
  recipient_email?: string | null;
  language?: string;
}

export async function fetchProposals(params: Record<string, string | number | boolean | undefined> = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value));
  });
  const qs = search.toString();
  return apiFetch<SalesProposalListResponse>(`/sales/proposals${qs ? `?${qs}` : ''}`);
}

export async function fetchProposal(id: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}`);
}

export async function createProposal(input: SalesProposalCreateInput) {
  return apiFetch<SalesProposalDetail>('/sales/proposals', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateProposal(id: string, input: Partial<SalesProposalCreateInput & { content_snapshot?: Record<string, unknown>; terms_snapshot?: Record<string, unknown> }>) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function submitProposal(id: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}/submit`, { method: 'POST' });
}

export async function reviewProposal(id: string, decision: 'approved' | 'rejected' | 'revision_requested', comments?: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}/review`, {
    method: 'POST',
    body: JSON.stringify({ decision, comments }),
  });
}

export async function markProposalSent(id: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}/mark-sent`, { method: 'POST' });
}

export async function markProposalViewed(id: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}/mark-viewed`, { method: 'POST' });
}

export async function markProposalAccepted(id: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}/mark-accepted`, { method: 'POST' });
}

export async function markProposalRejected(id: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}/mark-rejected`, { method: 'POST' });
}

export async function createProposalVersion(id: string) {
  return apiFetch<SalesProposalVersion>(`/sales/proposals/${id}/versions`, { method: 'POST' });
}

export async function importShortlistToProposal(id: string, shortlistId: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}/import-shortlist`, {
    method: 'POST',
    body: JSON.stringify({ shortlist_id: shortlistId }),
  });
}

export async function refreshProposalPricing(id: string) {
  return apiFetch<SalesProposalDetail>(`/sales/proposals/${id}/refresh-pricing`, { method: 'POST' });
}

export async function fetchProposalPreview(id: string) {
  return apiFetch<{ html: string; proposal_number: string; version_number: number }>(`/sales/proposals/${id}/preview`);
}

export function getProposalDownloadUrl(id: string) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  return `${base}/sales/proposals/${id}/download`;
}

export async function archiveProposal(id: string) {
  return apiFetch<SalesProposal>(`/sales/proposals/${id}`, { method: 'DELETE' });
}

export async function fetchProposalActivities(id: string) {
  return apiFetch<{ id: string; activity_type: string; created_at: string; metadata_json: Record<string, unknown> | null }[]>(
    `/sales/proposals/${id}/activities`,
  );
}

export async function fetchProposalVersions(id: string) {
  return apiFetch<SalesProposalVersion[]>(`/sales/proposals/${id}/versions`);
}

export async function fetchProposalApprovals(id: string) {
  return apiFetch<{ id: string; decision: string; comments: string | null; created_at: string }[]>(
    `/sales/proposals/${id}/approvals`,
  );
}
