import { apiFetch } from '@/lib/api/client';

export const PRICE_TYPES = [
  'original',
  'launch',
  'list',
  'promotional',
  'reservation',
  'contracted',
  'closing',
  'appraised',
  'estimated_rent',
] as const;

export type PriceType = (typeof PRICE_TYPES)[number];

export const PRICE_STATUSES = [
  'draft',
  'pending',
  'active',
  'expired',
  'superseded',
  'rejected',
  'archived',
] as const;

export type PriceStatus = (typeof PRICE_STATUSES)[number];

export const PRICE_REQUEST_STATUSES = [
  'draft',
  'submitted',
  'under_review',
  'approved',
  'rejected',
  'withdrawn',
  'expired',
  'applied',
] as const;

export type PriceRequestStatus = (typeof PRICE_REQUEST_STATUSES)[number];

export interface InventoryAssetPrice {
  id: string;
  inventory_asset_id: string;
  price_type: PriceType;
  amount: string;
  currency: string;
  effective_from: string;
  effective_to: string | null;
  status: PriceStatus;
  reason: string | null;
  source: string;
  approved_request_id: string | null;
  created_by_user_id: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface PriceChangeRequest {
  id: string;
  inventory_asset_id: string;
  price_type: PriceType;
  current_price_id: string | null;
  current_amount: string | null;
  proposed_amount: string;
  currency: string;
  change_amount: string;
  change_percentage: string | null;
  effective_from: string;
  effective_to: string | null;
  reason: string;
  supporting_document_id: string | null;
  requested_by_user_id: string;
  assigned_approver_user_id: string | null;
  status: PriceRequestStatus;
  reviewed_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  decision_notes: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  asset_display_id?: string | null;
  asset_system_code?: string | null;
  project_id?: string | null;
  project_name?: string | null;
  is_high_impact?: boolean | null;
  valid_actions?: string[];
}

export interface PriceApprovalRecord {
  id: string;
  price_change_request_id: string;
  reviewer_user_id: string;
  decision: 'approved' | 'rejected' | 'revision_requested';
  comments: string | null;
  created_at: string;
}

export interface AssetPricingSummary {
  list_price: string | null;
  promotional_price: string | null;
  contracted_price: string | null;
  currency: string;
  pending_price_requests: number;
}

export interface AssetPricingDetail {
  current_prices: InventoryAssetPrice[];
  pending_requests: PriceChangeRequest[];
  history: { price: InventoryAssetPrice; previous_amount?: string | null; change_amount?: string | null; change_percentage?: string | null; approved_request_id?: string | null }[];
  approval_history: PriceApprovalRecord[];
}

export interface InitialPriceInput {
  inventory_asset_id: string;
  price_type: PriceType;
  amount: number;
  currency: string;
  effective_from: string;
  effective_to?: string | null;
  reason?: string | null;
}

export interface PriceChangeInput {
  inventory_asset_id: string;
  price_type: PriceType;
  proposed_amount: number;
  currency: string;
  effective_from: string;
  effective_to?: string | null;
  reason: string;
  supporting_document_id?: string | null;
  assigned_approver_user_id?: string | null;
  submit?: boolean;
}

export interface PriceRequestFilters {
  project_id?: string;
  inventory_asset_id?: string;
  price_type?: PriceType | '';
  status?: PriceRequestStatus | '';
  page?: number;
  page_size?: number;
}

export interface PaginatedPriceRequests {
  items: PriceChangeRequest[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '' || value === false) continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : '';
}

export function formatMoney(
  amount: string | number | null | undefined,
  currency: string,
  locale: string,
): string {
  if (amount === null || amount === undefined || amount === '') return '—';
  const value = typeof amount === 'string' ? Number(amount) : amount;
  if (Number.isNaN(value)) return '—';
  return new Intl.NumberFormat(locale, { style: 'currency', currency, maximumFractionDigits: 0 }).format(value);
}

export function computeChangePreview(
  current: number | null,
  proposed: number,
): { changeAmount: number; changePercent: number | null } {
  const base = current ?? 0;
  const changeAmount = proposed - base;
  const changePercent = base !== 0 ? (changeAmount / base) * 100 : null;
  return { changeAmount, changePercent };
}

export async function fetchAssetPricingSummary(assetId: string): Promise<AssetPricingSummary> {
  return apiFetch<AssetPricingSummary>(`/inventory/prices/by-asset/${assetId}/summary`);
}

export async function fetchAssetPricingDetail(assetId: string): Promise<AssetPricingDetail> {
  return apiFetch<AssetPricingDetail>(`/inventory/prices/by-asset/${assetId}/detail`);
}

export async function fetchCurrentPrices(assetId: string): Promise<InventoryAssetPrice[]> {
  return apiFetch<InventoryAssetPrice[]>(`/inventory/prices/by-asset/${assetId}/current`);
}

export async function createInitialPrice(input: InitialPriceInput): Promise<InventoryAssetPrice> {
  return apiFetch<InventoryAssetPrice>('/inventory/prices/initial', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function createPriceChangeRequest(input: PriceChangeInput): Promise<PriceChangeRequest> {
  return apiFetch<PriceChangeRequest>('/inventory/price-requests', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function submitPriceRequest(id: string): Promise<PriceChangeRequest> {
  return apiFetch<PriceChangeRequest>(`/inventory/price-requests/${id}/submit`, { method: 'POST', body: '{}' });
}

export async function approvePriceRequest(id: string, comments?: string | null): Promise<PriceChangeRequest> {
  return apiFetch<PriceChangeRequest>(`/inventory/price-requests/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ comments: comments ?? null }),
  });
}

export async function rejectPriceRequest(id: string, decisionNotes: string): Promise<PriceChangeRequest> {
  return apiFetch<PriceChangeRequest>(`/inventory/price-requests/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ decision_notes: decisionNotes }),
  });
}

export async function requestPriceRevision(id: string, decisionNotes: string): Promise<PriceChangeRequest> {
  return apiFetch<PriceChangeRequest>(`/inventory/price-requests/${id}/request-revision`, {
    method: 'POST',
    body: JSON.stringify({ decision_notes: decisionNotes }),
  });
}

export async function withdrawPriceRequest(id: string): Promise<PriceChangeRequest> {
  return apiFetch<PriceChangeRequest>(`/inventory/price-requests/${id}/withdraw`, { method: 'POST', body: '{}' });
}

export async function fetchPendingPriceRequests(
  filters: PriceRequestFilters = {},
): Promise<PaginatedPriceRequests> {
  return apiFetch<PaginatedPriceRequests>(
    `/inventory/price-requests/pending${buildQuery({
      project_id: filters.project_id,
      page: filters.page,
      page_size: filters.page_size,
    })}`,
  );
}

export async function fetchPriceRequests(filters: PriceRequestFilters = {}): Promise<PaginatedPriceRequests> {
  return apiFetch<PaginatedPriceRequests>(
    `/inventory/price-requests${buildQuery({
      project_id: filters.project_id,
      inventory_asset_id: filters.inventory_asset_id,
      price_type: filters.price_type,
      status: filters.status,
      page: filters.page,
      page_size: filters.page_size,
    })}`,
  );
}

export async function fetchPriceRequest(id: string): Promise<PriceChangeRequest> {
  return apiFetch<PriceChangeRequest>(`/inventory/price-requests/${id}`);
}
