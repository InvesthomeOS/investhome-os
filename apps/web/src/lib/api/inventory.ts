import { apiFetch } from '@/lib/api/client';

export const INVENTORY_ASSET_TYPES = [
  'residential_unit',
  'commercial_unit',
  'parking_space',
  'storage_unit',
  'land_parcel',
  'office_unit',
  'retail_unit',
] as const;

export type InventoryAssetType = (typeof INVENTORY_ASSET_TYPES)[number];

export const USAGE_TYPES = [
  'residential',
  'commercial',
  'retail',
  'office',
  'parking',
  'storage',
  'industrial',
  'mixed',
] as const;

export type UsageType = (typeof USAGE_TYPES)[number];

export const AVAILABILITY_STATUSES = [
  'not_released',
  'available',
  'unavailable',
  'hold',
] as const;

export type AvailabilityStatus = (typeof AVAILABILITY_STATUSES)[number];

export const RESERVATION_STATUSES = [
  'none',
  'soft_hold',
  'confirmed',
  'expired',
  'cancelled',
] as const;

export type ReservationStatus = (typeof RESERVATION_STATUSES)[number];

export const SALES_STATUSES = [
  'not_for_sale',
  'available_for_sale',
  'under_contract',
  'sold',
] as const;

export type SalesStatus = (typeof SALES_STATUSES)[number];

export const CONSTRUCTION_STATUSES = [
  'planned',
  'foundation',
  'structure',
  'envelope',
  'interior',
  'finishing',
  'inspection',
  'ready',
  'delivered',
  'on_hold',
] as const;

export type ConstructionStatus = (typeof CONSTRUCTION_STATUSES)[number];

export const CLOSING_STATUSES = [
  'not_started',
  'in_progress',
  'title_clear',
  'funding_pending',
  'scheduled',
  'closed',
  'fallen_through',
] as const;

export type ClosingStatus = (typeof CLOSING_STATUSES)[number];

export const LEASING_STATUSES = [
  'not_applicable',
  'vacant',
  'listed',
  'application',
  'leased',
  'notice_given',
  'off_market',
] as const;

export type LeasingStatus = (typeof LEASING_STATUSES)[number];

export const STATUS_CATEGORIES = [
  'availability',
  'reservation',
  'sales',
  'construction',
  'closing',
  'leasing',
] as const;

export type StatusCategory = (typeof STATUS_CATEGORIES)[number];

export const BUILDING_TYPES = [
  'apartment',
  'condominium',
  'mixed_use',
  'office',
  'retail',
  'townhouse',
  'single_family',
  'parking_structure',
  'storage',
  'other',
] as const;

export type BuildingType = (typeof BUILDING_TYPES)[number];

export const STRUCTURE_STATUSES = ['active', 'inactive', 'planned', 'under_construction'] as const;

export type StructureStatus = (typeof STRUCTURE_STATUSES)[number];

export interface Building {
  id: string;
  project_id: string;
  name: string;
  code: string;
  building_type: BuildingType;
  address: string | null;
  total_floors: number | null;
  status: StructureStatus;
  description: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface Floor {
  id: string;
  building_id: string;
  floor_number: number;
  display_name: string | null;
  level_code: string | null;
  sort_order: number;
  status: StructureStatus;
  description: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface InventoryAsset {
  id: string;
  project_id: string;
  building_id: string | null;
  floor_id: string | null;
  display_id: string;
  system_code: string;
  legal_identifier: string | null;
  asset_type: InventoryAssetType;
  usage_type: UsageType;
  unit_subtype: string | null;
  bedrooms: string | null;
  bathrooms: string | null;
  interior_area_sqft: string | null;
  exterior_area_sqft: string | null;
  total_area_sqft: string | null;
  orientation: string | null;
  view_type: string | null;
  availability_status: AvailabilityStatus;
  reservation_status: ReservationStatus;
  sales_status: SalesStatus;
  construction_status: ConstructionStatus;
  closing_status: ClosingStatus;
  leasing_status: LeasingStatus;
  currency: string;
  release_date: string | null;
  delivery_date: string | null;
  description: string | null;
  notes: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface InventoryAssetStatusHistory {
  id: string;
  inventory_asset_id: string;
  status_category: StatusCategory;
  previous_status: string | null;
  new_status: string;
  reason: string | null;
  changed_by_user_id: string | null;
  effective_at: string;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type BuildingListResponse = PaginatedResponse<Building>;
export type FloorListResponse = PaginatedResponse<Floor>;
export type InventoryAssetListResponse = PaginatedResponse<InventoryAsset>;

export interface BuildingFilters {
  project_id?: string;
  building_type?: BuildingType | '';
  status?: StructureStatus | '';
  search?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface FloorFilters {
  building_id?: string;
  project_id?: string;
  status?: StructureStatus | '';
  search?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface InventoryAssetFilters {
  project_id?: string;
  building_id?: string;
  floor_id?: string;
  asset_type?: InventoryAssetType | '';
  usage_type?: UsageType | '';
  availability_status?: AvailabilityStatus | '';
  reservation_status?: ReservationStatus | '';
  sales_status?: SalesStatus | '';
  construction_status?: ConstructionStatus | '';
  closing_status?: ClosingStatus | '';
  leasing_status?: LeasingStatus | '';
  search?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface InventoryAssetInput {
  project_id: string;
  building_id?: string | null;
  floor_id?: string | null;
  display_id: string;
  legal_identifier?: string | null;
  asset_type: InventoryAssetType;
  usage_type: UsageType;
  unit_subtype?: string | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  interior_area_sqft?: number | null;
  exterior_area_sqft?: number | null;
  total_area_sqft?: number | null;
  orientation?: string | null;
  view_type?: string | null;
  currency?: string;
  release_date?: string | null;
  delivery_date?: string | null;
  description?: string | null;
  notes?: string | null;
}

export interface StatusUpdateInput {
  status_category: StatusCategory;
  new_status: string;
  reason?: string | null;
  effective_at?: string | null;
}

export interface InventoryKpis {
  total: number;
  available: number;
  soft_hold: number;
  reserved: number;
  under_contract: number;
  sold: number;
  closed: number;
  leased: number;
}

const SQFT_TO_SQM = 0.092903;

export type AreaDisplayUnit = 'sqft' | 'sqm';

export function getAreaDisplayUnit(): AreaDisplayUnit {
  if (typeof window === 'undefined') return 'sqft';
  const stored = window.localStorage.getItem('investhome.areaUnit');
  if (stored === 'sqm' || stored === 'sqft') return stored;
  return 'sqft';
}

export function formatArea(
  sqft: string | number | null | undefined,
  locale: string,
  unit: AreaDisplayUnit = getAreaDisplayUnit(),
): string {
  if (sqft === null || sqft === undefined || sqft === '') return '—';
  const value = typeof sqft === 'string' ? Number(sqft) : sqft;
  if (Number.isNaN(value)) return '—';
  const displayValue = unit === 'sqm' ? value * SQFT_TO_SQM : value;
  const formatted = new Intl.NumberFormat(locale, {
    maximumFractionDigits: unit === 'sqm' ? 1 : 0,
  }).format(displayValue);
  return unit === 'sqm' ? `${formatted} m²` : `${formatted} ft²`;
}

export function formatShortDate(value: string | null, locale: string): string {
  if (!value) return '—';
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

export function formatDateTime(value: string | null, locale: string): string {
  if (!value) return '—';
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function isParkingAsset(assetType: InventoryAssetType): boolean {
  return assetType === 'parking_space';
}

export function isStorageAsset(assetType: InventoryAssetType): boolean {
  return assetType === 'storage_unit';
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

function assetFilterQuery(filters: InventoryAssetFilters = {}): string {
  return buildQuery({
    project_id: filters.project_id,
    building_id: filters.building_id,
    floor_id: filters.floor_id,
    asset_type: filters.asset_type,
    usage_type: filters.usage_type,
    availability_status: filters.availability_status,
    reservation_status: filters.reservation_status,
    sales_status: filters.sales_status,
    construction_status: filters.construction_status,
    closing_status: filters.closing_status,
    leasing_status: filters.leasing_status,
    search: filters.search?.trim(),
    include_archived: filters.include_archived,
    sort_by: filters.sort_by,
    sort_order: filters.sort_order,
    page: filters.page,
    page_size: filters.page_size,
  });
}

export async function fetchBuildings(filters: BuildingFilters = {}): Promise<BuildingListResponse> {
  return apiFetch<BuildingListResponse>(
    `/inventory/buildings${buildQuery({
      project_id: filters.project_id,
      building_type: filters.building_type,
      status: filters.status,
      search: filters.search?.trim(),
      include_archived: filters.include_archived,
      sort_by: filters.sort_by,
      sort_order: filters.sort_order,
      page: filters.page,
      page_size: filters.page_size,
    })}`,
  );
}

export async function fetchBuilding(id: string): Promise<Building> {
  return apiFetch<Building>(`/inventory/buildings/${id}`);
}

export async function fetchFloors(filters: FloorFilters = {}): Promise<FloorListResponse> {
  return apiFetch<FloorListResponse>(
    `/inventory/floors${buildQuery({
      building_id: filters.building_id,
      project_id: filters.project_id,
      status: filters.status,
      search: filters.search?.trim(),
      include_archived: filters.include_archived,
      sort_by: filters.sort_by,
      sort_order: filters.sort_order,
      page: filters.page,
      page_size: filters.page_size,
    })}`,
  );
}

export async function fetchFloor(id: string): Promise<Floor> {
  return apiFetch<Floor>(`/inventory/floors/${id}`);
}

export async function fetchInventoryAssets(
  filters: InventoryAssetFilters = {},
): Promise<InventoryAssetListResponse> {
  return apiFetch<InventoryAssetListResponse>(`/inventory/assets${assetFilterQuery(filters)}`);
}

export async function fetchInventoryAsset(id: string): Promise<InventoryAsset> {
  return apiFetch<InventoryAsset>(`/inventory/assets/${id}`);
}

export async function createInventoryAsset(input: InventoryAssetInput): Promise<InventoryAsset> {
  return apiFetch<InventoryAsset>('/inventory/assets', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateInventoryAsset(
  id: string,
  input: Partial<InventoryAssetInput>,
): Promise<InventoryAsset> {
  return apiFetch<InventoryAsset>(`/inventory/assets/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function archiveInventoryAsset(id: string): Promise<InventoryAsset> {
  return apiFetch<InventoryAsset>(`/inventory/assets/${id}/archive`, { method: 'POST' });
}

export async function restoreInventoryAsset(id: string): Promise<InventoryAsset> {
  return apiFetch<InventoryAsset>(`/inventory/assets/${id}/restore`, { method: 'POST' });
}

export async function updateInventoryAssetStatus(
  id: string,
  input: StatusUpdateInput,
): Promise<InventoryAssetStatusHistory> {
  return apiFetch<InventoryAssetStatusHistory>(`/inventory/assets/${id}/status`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function fetchInventoryAssetStatusHistory(
  id: string,
  statusCategory?: StatusCategory,
): Promise<InventoryAssetStatusHistory[]> {
  const query = statusCategory ? `?status_category=${statusCategory}` : '';
  return apiFetch<InventoryAssetStatusHistory[]>(`/inventory/assets/${id}/status-history${query}`);
}

export async function fetchInventoryKpis(
  scope: Pick<InventoryAssetFilters, 'project_id' | 'building_id' | 'floor_id'> = {},
): Promise<InventoryKpis> {
  const base: InventoryAssetFilters = { ...scope, page: 1, page_size: 1 };

  const [
    total,
    available,
    softHold,
    reserved,
    underContract,
    sold,
    closed,
    leased,
  ] = await Promise.all([
    fetchInventoryAssets(base),
    fetchInventoryAssets({ ...base, availability_status: 'available' }),
    fetchInventoryAssets({ ...base, reservation_status: 'soft_hold' }),
    fetchInventoryAssets({ ...base, reservation_status: 'confirmed' }),
    fetchInventoryAssets({ ...base, sales_status: 'under_contract' }),
    fetchInventoryAssets({ ...base, sales_status: 'sold' }),
    fetchInventoryAssets({ ...base, closing_status: 'closed' }),
    fetchInventoryAssets({ ...base, leasing_status: 'leased' }),
  ]);

  return {
    total: total.total,
    available: available.total,
    soft_hold: softHold.total,
    reserved: reserved.total,
    under_contract: underContract.total,
    sold: sold.total,
    closed: closed.total,
    leased: leased.total,
  };
}

export const RESERVATION_RECORD_STATUSES = [
  'active',
  'requested',
  'approved',
  'deposit_pending',
  'deposit_received',
  'converted',
  'expired',
  'cancelled',
  'rejected',
  'released',
] as const;

export type ReservationRecordStatus = (typeof RESERVATION_RECORD_STATUSES)[number];

export interface InventoryReservation {
  id: string;
  inventory_asset_id: string;
  reservation_type: 'soft_hold' | 'reservation';
  status: ReservationRecordStatus;
  source: string;
  investor_id: string | null;
  lead_id: string | null;
  reserved_by_user_id: string | null;
  approved_by_user_id: string | null;
  expires_at: string | null;
  deposit_due_at: string | null;
  deposit_amount: string | null;
  deposit_currency: string | null;
  finance_transaction_id: string | null;
  extension_count: number;
  notes: string | null;
  cancellation_reason: string | null;
  requested_at: string | null;
  approved_at: string | null;
  deposit_received_at: string | null;
  converted_at: string | null;
  expired_at: string | null;
  cancelled_at: string | null;
  released_at: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  asset_display_id?: string | null;
  asset_system_code?: string | null;
  party_name?: string | null;
  seconds_until_expiry?: number | null;
  valid_actions?: string[];
}

export interface InventoryReservationEvent {
  id: string;
  reservation_id: string;
  event_type: string;
  from_status: string | null;
  to_status: string;
  actor_user_id: string | null;
  notes: string | null;
  created_at: string;
}

export interface SoftHoldInput {
  inventory_asset_id: string;
  investor_id?: string | null;
  lead_id?: string | null;
  expires_at?: string | null;
  deposit_amount?: number | null;
  deposit_currency?: string | null;
  notes?: string | null;
}

export interface ReservationFilters {
  project_id?: string;
  inventory_asset_id?: string;
  investor_id?: string;
  lead_id?: string;
  status?: ReservationRecordStatus | '';
  active_only?: boolean;
  expiring_within_hours?: number;
  search?: string;
  page?: number;
  page_size?: number;
}

export type ReservationListResponse = PaginatedResponse<InventoryReservation>;

export interface ReservationHistoryEntry {
  reservation: InventoryReservation;
  events: InventoryReservationEvent[];
}

export function formatCountdown(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  if (seconds <= 0) return 'Expired';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h`;
  }
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export async function fetchReservations(
  filters: ReservationFilters = {},
): Promise<ReservationListResponse> {
  return apiFetch<ReservationListResponse>(
    `/inventory/reservations${buildQuery({
      project_id: filters.project_id,
      inventory_asset_id: filters.inventory_asset_id,
      investor_id: filters.investor_id,
      lead_id: filters.lead_id,
      status: filters.status,
      active_only: filters.active_only,
      expiring_within_hours: filters.expiring_within_hours,
      search: filters.search?.trim(),
      page: filters.page,
      page_size: filters.page_size,
    })}`,
  );
}

export async function fetchReservation(id: string): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>(`/inventory/reservations/${id}`);
}

export async function fetchReservationHistoryByAsset(
  assetId: string,
): Promise<ReservationHistoryEntry[]> {
  return apiFetch<ReservationHistoryEntry[]>(`/inventory/reservations/by-asset/${assetId}/history`);
}

export async function createSoftHold(input: SoftHoldInput): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>('/inventory/reservations/soft-hold', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function releaseSoftHold(
  id: string,
  reason?: string | null,
): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>(`/inventory/reservations/${id}/release`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export async function requestReservation(
  id: string,
  input: { notes?: string | null; deposit_amount?: number | null; deposit_due_at?: string | null } = {},
): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>(`/inventory/reservations/${id}/request`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function approveReservation(
  id: string,
  notes?: string | null,
): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>(`/inventory/reservations/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ notes: notes ?? null }),
  });
}

export async function rejectReservation(id: string, reason: string): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>(`/inventory/reservations/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function cancelReservation(
  id: string,
  reason?: string | null,
): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>(`/inventory/reservations/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export async function markDepositReceived(
  id: string,
  input: { finance_transaction_id?: string | null; reference_number?: string | null } = {},
): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>(`/inventory/reservations/${id}/deposit-received`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function convertReservation(
  id: string,
  notes?: string | null,
): Promise<InventoryReservation> {
  return apiFetch<InventoryReservation>(`/inventory/reservations/${id}/convert`, {
    method: 'POST',
    body: JSON.stringify({ notes: notes ?? null }),
  });
}
