import { apiFetch } from '@/lib/api/client';

export const ASSIGNMENT_TYPES = ['parking_for', 'storage_for'] as const;
export type AssignmentType = (typeof ASSIGNMENT_TYPES)[number];

export const ASSIGNMENT_REQUEST_TYPES = ['assign', 'reassign', 'unassign'] as const;
export type AssignmentRequestType = (typeof ASSIGNMENT_REQUEST_TYPES)[number];

export const ASSIGNMENT_REQUEST_STATUSES = [
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

export type AssignmentRequestStatus = (typeof ASSIGNMENT_REQUEST_STATUSES)[number];

export interface AssignmentRecord {
  id: string;
  child_asset_id: string;
  child_display_id: string | null;
  parent_asset_id: string;
  parent_display_id: string | null;
  assignment_type: AssignmentType;
  status: string;
  effective_from: string;
  effective_to: string | null;
  assignment_price: string | null;
  currency: string;
  supporting_document_id: string | null;
  related_transaction_id: string | null;
  notes: string | null;
  created_by_user_id: string | null;
  approved_by_user_id: string | null;
  assignment_request_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssignmentRequest {
  id: string;
  child_asset_id: string;
  child_display_id: string | null;
  parent_asset_id: string | null;
  parent_display_id: string | null;
  project_name: string | null;
  request_type: AssignmentRequestType;
  assignment_type: AssignmentType;
  effective_date: string;
  reason: string;
  assignment_price: string | null;
  currency: string;
  supporting_document_id: string | null;
  related_transaction_id: string | null;
  requested_by_user_id: string;
  assigned_approver_user_id: string | null;
  status: AssignmentRequestStatus;
  reviewed_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  decision_notes: string | null;
  actions: string[];
  created_at: string;
  updated_at: string;
}

export interface AssignmentSummary {
  assigned_to_display_id: string | null;
  assigned_to_asset_id: string | null;
  assignment_status: string;
  assignment_type: string | null;
  parking_count: number;
  storage_count: number;
  has_scheduled: boolean;
  has_pending: boolean;
}

export interface AssetAssignmentDetail {
  child_asset_id: string;
  current: AssignmentRecord | null;
  history: AssignmentRecord[];
  pending_requests: AssignmentRequest[];
  scheduled_requests: AssignmentRequest[];
  parent_accessories: AssignmentRecord[];
}

export interface AssignmentRequestInput {
  child_asset_id: string;
  parent_asset_id?: string | null;
  request_type?: AssignmentRequestType;
  effective_date: string;
  reason: string;
  assignment_price?: string | null;
  currency?: string;
  supporting_document_id?: string | null;
  related_transaction_id?: string | null;
  assigned_approver_user_id?: string | null;
  submit?: boolean;
}

export function fetchAssetAssignmentDetail(assetId: string): Promise<AssetAssignmentDetail> {
  return apiFetch(`/inventory/assignments/by-asset/${assetId}/detail`);
}

export function fetchAssignmentSummary(assetId: string): Promise<AssignmentSummary> {
  return apiFetch(`/inventory/assignments/summary/by-asset/${assetId}`);
}

export function fetchPendingAssignmentApprovals(): Promise<AssignmentRequest[]> {
  return apiFetch('/inventory/assignment-requests/pending-approvals');
}

export function createAssignmentRequest(input: AssignmentRequestInput): Promise<AssignmentRequest> {
  return apiFetch('/inventory/assignment-requests', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function approveAssignmentRequest(requestId: string, comments?: string): Promise<AssignmentRequest> {
  return apiFetch(`/inventory/assignment-requests/${requestId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ comments: comments ?? null }),
  });
}

export function rejectAssignmentRequest(requestId: string, decisionNotes: string): Promise<AssignmentRequest> {
  return apiFetch(`/inventory/assignment-requests/${requestId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ decision_notes: decisionNotes }),
  });
}

export function requestAssignmentRevision(requestId: string, decisionNotes: string): Promise<AssignmentRequest> {
  return apiFetch(`/inventory/assignment-requests/${requestId}/request-revision`, {
    method: 'POST',
    body: JSON.stringify({ decision_notes: decisionNotes }),
  });
}

export function formatAssignmentMoney(
  value: string | null | undefined,
  currency: string,
  locale: string,
): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = Number.parseFloat(value);
  if (Number.isNaN(num)) return '—';
  return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(num);
}
