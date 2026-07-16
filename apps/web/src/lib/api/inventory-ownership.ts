import { apiFetch } from '@/lib/api/client';

export const OWNERSHIP_TYPES = [
  'legal_owner',
  'beneficial_owner',
  'economic_owner',
  'joint_owner',
  'trustee',
  'nominee',
  'manager',
  'other',
] as const;

export type OwnershipType = (typeof OWNERSHIP_TYPES)[number];

export const TRANSFER_TYPES = [
  'initial_ownership',
  'full_transfer',
  'partial_transfer',
  'percentage_change',
  'owner_addition',
  'owner_removal',
  'ownership_type_change',
  'correction',
  'other',
] as const;

export type TransferType = (typeof TRANSFER_TYPES)[number];

export const TRANSFER_PARTY_ROLES = [
  'outgoing_owner',
  'incoming_owner',
  'continuing_owner',
] as const;

export type TransferPartyRole = (typeof TRANSFER_PARTY_ROLES)[number];

export const TRANSFER_REQUEST_STATUSES = [
  'draft',
  'submitted',
  'under_review',
  'approved',
  'rejected',
  'revision_requested',
  'withdrawn',
  'applied',
  'stale',
] as const;

export type TransferRequestStatus = (typeof TRANSFER_REQUEST_STATUSES)[number];

export interface OwnershipRecord {
  id: string;
  inventory_asset_id: string;
  party_id: string;
  party_name: string | null;
  party_type: string | null;
  ownership_type: OwnershipType;
  ownership_percentage: string;
  effective_from: string;
  effective_to: string | null;
  status: string;
  acquisition_method: string;
  transfer_reason: string | null;
  related_document_id: string | null;
  related_transaction_id: string | null;
  source: string;
  notes: string | null;
  created_by_user_id: string | null;
  approved_by_user_id: string | null;
  ownership_transfer_request_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransferParty {
  id: string;
  party_id: string;
  party_name: string | null;
  party_type: string | null;
  ownership_type: OwnershipType;
  previous_percentage: string | null;
  proposed_percentage: string;
  role: TransferPartyRole;
  notes: string | null;
  created_at: string;
}

export interface OwnershipTransferRequest {
  id: string;
  inventory_asset_id: string;
  asset_display_id: string | null;
  project_name: string | null;
  transfer_type: TransferType;
  effective_date: string;
  reason: string;
  supporting_document_id: string | null;
  related_transaction_id: string | null;
  requested_by_user_id: string;
  assigned_approver_user_id: string | null;
  status: TransferRequestStatus;
  reviewed_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  decision_notes: string | null;
  parties: TransferParty[];
  actions: string[];
  proposed_legal_total: string | null;
  current_legal_total: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssetOwnershipDetail {
  asset_id: string;
  current_legal: OwnershipRecord[];
  current_beneficial: OwnershipRecord[];
  current_economic: OwnershipRecord[];
  current_other: OwnershipRecord[];
  pending_requests: OwnershipTransferRequest[];
  scheduled_transfers: OwnershipTransferRequest[];
  history: OwnershipRecord[];
  legal_total: string;
}

export interface OwnershipSummary {
  primary_legal_owner: string | null;
  owner_count: number;
  ownership_status: string;
}

export interface TransferPartyInput {
  party_id: string;
  ownership_type: OwnershipType;
  previous_percentage?: string | null;
  proposed_percentage: string;
  role: TransferPartyRole;
  notes?: string | null;
}

export interface TransferRequestInput {
  inventory_asset_id: string;
  transfer_type: TransferType;
  effective_date: string;
  reason: string;
  parties: TransferPartyInput[];
  supporting_document_id?: string | null;
  related_transaction_id?: string | null;
  assigned_approver_user_id?: string | null;
  submit?: boolean;
}

export function fetchAssetOwnershipDetail(assetId: string): Promise<AssetOwnershipDetail> {
  return apiFetch(`/inventory/ownership/by-asset/${assetId}/detail`);
}

export function fetchOwnershipSummary(assetId: string): Promise<OwnershipSummary> {
  return apiFetch(`/inventory/ownership/summary/by-asset/${assetId}`);
}

export function fetchPendingOwnershipApprovals(): Promise<OwnershipTransferRequest[]> {
  return apiFetch('/inventory/ownership-transfers/pending-approvals');
}

export function createOwnershipTransfer(input: TransferRequestInput): Promise<OwnershipTransferRequest> {
  return apiFetch('/inventory/ownership-transfers', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function submitOwnershipTransfer(requestId: string): Promise<OwnershipTransferRequest> {
  return apiFetch(`/inventory/ownership-transfers/${requestId}/submit`, { method: 'POST' });
}

export function approveOwnershipTransfer(
  requestId: string,
  comments?: string,
): Promise<OwnershipTransferRequest> {
  return apiFetch(`/inventory/ownership-transfers/${requestId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ comments: comments ?? null }),
  });
}

export function rejectOwnershipTransfer(
  requestId: string,
  decisionNotes: string,
): Promise<OwnershipTransferRequest> {
  return apiFetch(`/inventory/ownership-transfers/${requestId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ decision_notes: decisionNotes }),
  });
}

export function requestOwnershipRevision(
  requestId: string,
  decisionNotes: string,
): Promise<OwnershipTransferRequest> {
  return apiFetch(`/inventory/ownership-transfers/${requestId}/request-revision`, {
    method: 'POST',
    body: JSON.stringify({ decision_notes: decisionNotes }),
  });
}

export function formatPercentage(value: string | number | null | undefined, locale: string): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'string' ? Number.parseFloat(value) : value;
  if (Number.isNaN(num)) return '—';
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(num) + '%';
}
