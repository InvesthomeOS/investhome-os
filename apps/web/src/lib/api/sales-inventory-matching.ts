import { apiFetch } from '@/lib/api/client';

export type MatchRelationshipType =
  | 'matched'
  | 'shortlisted'
  | 'favorite'
  | 'proposed'
  | 'selected'
  | 'rejected'
  | 'soft_hold'
  | 'reserved';

export type MatchStatus = 'active' | 'inactive' | 'rejected' | 'converted' | 'archived';

export type MatchRejectionReason =
  | 'budget'
  | 'size'
  | 'layout'
  | 'location'
  | 'floor'
  | 'exposure'
  | 'delivery_timing'
  | 'availability'
  | 'financing'
  | 'client_preference'
  | 'other';

export type ShortlistStatus = 'draft' | 'active' | 'shared' | 'superseded' | 'archived';

export interface InventoryPreference {
  id: string;
  lead_id: string | null;
  opportunity_id: string | null;
  budget_min: string | null;
  budget_max: string | null;
  currency: string;
  bedrooms_min: number | null;
  bedrooms_max: number | null;
  bathrooms_min: number | null;
  bathrooms_max: number | null;
  area_min: string | null;
  area_max: string | null;
  floor_min: number | null;
  floor_max: number | null;
  delivery_date_before: string | null;
  notes: string | null;
  preferred_project_ids: string[];
  preferred_asset_types: string[];
  preferred_usage_types: string[];
  preferred_building_ids: string[];
}

export interface InventorySearchResultItem {
  asset_id: string;
  display_id: string | null;
  system_code: string | null;
  project_id: string;
  asset_type: string;
  usage_type: string;
  availability_status: string;
  reservation_status: string;
  sales_status: string;
  bedrooms: number | null;
  bathrooms: number | null;
  interior_area_sqft: string | null;
  list_price: string | null;
  currency: string;
  is_stale: boolean;
  existing_match_id: string | null;
  relationship_type: MatchRelationshipType | null;
}

export interface InventoryMatch {
  id: string;
  lead_id: string | null;
  opportunity_id: string | null;
  inventory_asset_id: string;
  relationship_type: MatchRelationshipType;
  status: MatchStatus;
  match_source: string;
  match_score: number | null;
  match_reason: string | null;
  rejection_reason: MatchRejectionReason | null;
  is_primary: boolean;
  is_stale: boolean;
  stale_fields: string[];
  asset_display_id: string | null;
  list_price: string | null;
}

export interface ShortlistItem {
  id: string;
  shortlist_id: string;
  inventory_asset_id: string;
  sort_order: number;
  notes: string | null;
  is_favorite: boolean;
  is_stale: boolean;
  stale_fields: string[];
  asset_display_id: string | null;
  list_price: string | null;
  availability_status: string | null;
}

export interface SalesShortlist {
  id: string;
  lead_id: string | null;
  opportunity_id: string | null;
  title: string;
  description: string | null;
  status: ShortlistStatus;
  items: ShortlistItem[];
}

export interface CompareAssetItem {
  asset_id: string;
  display_id: string | null;
  system_code: string | null;
  asset_type: string;
  usage_type: string;
  bedrooms: number | null;
  bathrooms: number | null;
  interior_area_sqft: string | null;
  availability_status: string;
  reservation_status: string;
  sales_status: string;
  list_price: string | null;
  currency: string;
  project_name: string | null;
  building_code: string | null;
  floor_label: string | null;
}

export async function fetchInventoryPreferences(params: {
  leadId?: string;
  opportunityId?: string;
}): Promise<InventoryPreference | null> {
  const query = new URLSearchParams();
  if (params.leadId) query.set('lead_id', params.leadId);
  if (params.opportunityId) query.set('opportunity_id', params.opportunityId);
  try {
    return await apiFetch<InventoryPreference>(`/sales/inventory-preferences?${query}`);
  } catch {
    return null;
  }
}

export async function saveInventoryPreferences(body: Partial<InventoryPreference> & {
  lead_id?: string;
  opportunity_id?: string;
}): Promise<InventoryPreference> {
  return apiFetch<InventoryPreference>('/sales/inventory-preferences', {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

export async function searchInventoryForMatching(body: Record<string, unknown>): Promise<{
  items: InventorySearchResultItem[];
  total: number;
}> {
  return apiFetch('/sales/inventory-matching/search', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function fetchInventoryMatches(params: {
  leadId?: string;
  opportunityId?: string;
  relationshipType?: MatchRelationshipType;
  excludeRejected?: boolean;
}): Promise<InventoryMatch[]> {
  const query = new URLSearchParams();
  if (params.leadId) query.set('lead_id', params.leadId);
  if (params.opportunityId) query.set('opportunity_id', params.opportunityId);
  if (params.relationshipType) query.set('relationship_type', params.relationshipType);
  if (params.excludeRejected) query.set('exclude_rejected', 'true');
  const res = await apiFetch<{ items: InventoryMatch[] }>(`/sales/inventory-matches?${query}`);
  return res.items;
}

export async function createInventoryMatch(body: {
  lead_id?: string;
  opportunity_id?: string;
  inventory_asset_id: string;
  relationship_type?: MatchRelationshipType;
  match_reason?: string;
}): Promise<InventoryMatch> {
  return apiFetch('/sales/inventory-matches', { method: 'POST', body: JSON.stringify(body) });
}

export async function rejectInventoryMatch(
  matchId: string,
  body: { rejection_reason: MatchRejectionReason; notes?: string },
): Promise<InventoryMatch> {
  return apiFetch(`/sales/inventory-matches/${matchId}/reject`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function setPrimaryInventoryMatch(matchId: string): Promise<InventoryMatch> {
  return apiFetch(`/sales/inventory-matches/${matchId}/set-primary`, { method: 'POST' });
}

export async function favoriteInventoryMatch(matchId: string): Promise<InventoryMatch> {
  return apiFetch(`/sales/inventory-matches/${matchId}/favorite`, { method: 'POST' });
}

export async function fetchShortlists(params: {
  leadId?: string;
  opportunityId?: string;
}): Promise<SalesShortlist[]> {
  const query = new URLSearchParams();
  if (params.leadId) query.set('lead_id', params.leadId);
  if (params.opportunityId) query.set('opportunity_id', params.opportunityId);
  const res = await apiFetch<{ items: SalesShortlist[] }>(`/sales/shortlists?${query}`);
  return res.items;
}

export async function createShortlist(body: {
  lead_id?: string;
  opportunity_id?: string;
  title: string;
  description?: string;
}): Promise<SalesShortlist> {
  return apiFetch('/sales/shortlists', { method: 'POST', body: JSON.stringify(body) });
}

export async function addShortlistItem(
  shortlistId: string,
  body: { inventory_asset_id: string; notes?: string; is_favorite?: boolean },
): Promise<ShortlistItem> {
  return apiFetch(`/sales/shortlists/${shortlistId}/items`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function reorderShortlistItems(
  shortlistId: string,
  itemIds: string[],
): Promise<SalesShortlist> {
  return apiFetch(`/sales/shortlists/${shortlistId}/items/reorder`, {
    method: 'PATCH',
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

export async function compareInventoryAssets(assetIds: string[]): Promise<CompareAssetItem[]> {
  const res = await apiFetch<{ items: CompareAssetItem[] }>('/sales/inventory-matching/compare', {
    method: 'POST',
    body: JSON.stringify({ asset_ids: assetIds }),
  });
  return res.items;
}

export async function createSoftHoldFromSales(body: {
  inventory_asset_id: string;
  lead_id?: string;
  opportunity_id?: string;
  notes?: string;
}): Promise<Record<string, unknown>> {
  return apiFetch('/sales/inventory-matching/soft-hold', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function staleCheckInventory(
  assetIds: string[],
  snapshots: Record<string, Record<string, unknown>>,
): Promise<Array<{ asset_id: string; is_stale: boolean; stale_fields: string[] }>> {
  const res = await apiFetch<{ items: Array<{ asset_id: string; is_stale: boolean; stale_fields: string[] }> }>(
    '/sales/inventory-matching/stale-check',
    { method: 'POST', body: JSON.stringify({ asset_ids: assetIds, snapshots }) },
  );
  return res.items;
}
