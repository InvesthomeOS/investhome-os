import { apiFetch } from './client';

export type BranchType =
  | 'head_office'
  | 'regional_office'
  | 'corporate_office'
  | 'sales_office'
  | 'construction_office'
  | 'project_office'
  | 'warehouse'
  | 'service_center'
  | 'temporary_office'
  | 'remote_office'
  | 'other';

export type BranchStatus =
  | 'planning'
  | 'opening_soon'
  | 'active'
  | 'inactive'
  | 'temporarily_closed'
  | 'closed'
  | 'archived';

export type BranchWorkingHours = {
  id: string;
  branch_id: string;
  business_days: Record<string, boolean> | null;
  open_time: string | null;
  close_time: string | null;
  holidays: unknown[] | null;
  special_hours: unknown[] | null;
};

export type BranchAsset = {
  id: string;
  branch_id: string;
  asset_type: string;
  name: string;
  status: string;
  notes: string | null;
};

export type BranchDocument = {
  id: string;
  branch_id: string;
  document_type: string;
  title: string;
  document_id: string | null;
  reference_number: string | null;
  expiry_date: string | null;
};

export type BranchSummary = {
  id: string;
  branch_code: string;
  branch_name: string;
  company_id: string;
  company_name: string | null;
  branch_type: BranchType;
  country: string;
  state: string | null;
  city: string;
  status: BranchStatus;
  manager_user_id: string | null;
  manager_name: string | null;
  employee_count: number;
  department_count: number;
  opening_date: string | null;
  created_at: string;
  updated_at: string;
};

export type BranchDetail = BranchSummary & {
  district: string | null;
  postal_code: string | null;
  full_address: string;
  latitude: number | null;
  longitude: number | null;
  google_maps_link: string | null;
  timezone: string | null;
  main_phone: string | null;
  mobile_phone: string | null;
  email: string | null;
  website: string | null;
  emergency_contact: string | null;
  notes: string | null;
  archived_at: string | null;
  working_hours: BranchWorkingHours | null;
  assets: BranchAsset[];
  documents: BranchDocument[];
  warnings: string[];
};

export type BranchListResponse = {
  items: BranchSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type BranchInput = {
  branch_code: string;
  branch_name: string;
  company_id: string;
  branch_type: BranchType;
  country: string;
  state?: string | null;
  city: string;
  district?: string | null;
  postal_code?: string | null;
  full_address: string;
  latitude?: number | null;
  longitude?: number | null;
  google_maps_link?: string | null;
  timezone?: string | null;
  main_phone?: string | null;
  mobile_phone?: string | null;
  email?: string | null;
  website?: string | null;
  emergency_contact?: string | null;
  manager_user_id?: string | null;
  status?: BranchStatus;
  opening_date?: string | null;
  department_count?: number;
  notes?: string | null;
};

export type BranchListParams = {
  search?: string;
  company_id?: string;
  country?: string;
  state?: string;
  city?: string;
  branch_type?: string;
  status?: string;
  manager_user_id?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
};

function buildQuery(params: BranchListParams): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value));
    }
  });
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export async function fetchBranches(params: BranchListParams = {}): Promise<BranchListResponse> {
  return apiFetch<BranchListResponse>(`/branches${buildQuery(params)}`);
}

export async function fetchBranch(branchId: string): Promise<BranchDetail> {
  return apiFetch<BranchDetail>(`/branches/${branchId}`);
}

export async function createBranch(payload: BranchInput): Promise<{ branch: BranchDetail; warnings: string[] }> {
  return apiFetch(`/branches`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateBranch(
  branchId: string,
  payload: Partial<BranchInput>,
): Promise<{ branch: BranchDetail; warnings: string[] }> {
  return apiFetch(`/branches/${branchId}`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function deleteBranch(branchId: string): Promise<void> {
  await apiFetch(`/branches/${branchId}`, { method: 'DELETE' });
}

export async function archiveBranch(branchId: string): Promise<BranchDetail> {
  return apiFetch(`/branches/${branchId}/archive`, { method: 'POST' });
}

export async function deactivateBranch(branchId: string): Promise<BranchDetail> {
  return apiFetch(`/branches/${branchId}/deactivate`, { method: 'POST' });
}

export async function duplicateBranch(branchId: string): Promise<BranchDetail> {
  return apiFetch(`/branches/${branchId}/duplicate`, { method: 'POST' });
}

export async function assignBranchManager(
  branchId: string,
  managerUserId: string | null,
): Promise<BranchDetail> {
  return apiFetch(`/branches/${branchId}/assign-manager`, {
    method: 'POST',
    body: JSON.stringify({ manager_user_id: managerUserId }),
  });
}

export async function exportBranchesCsv(): Promise<Blob> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/branches/export`, {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Export failed');
  }
  return response.blob();
}

export function getBranchMapsUrl(branch: Pick<BranchDetail, 'google_maps_link' | 'latitude' | 'longitude'>): string | null {
  if (branch.google_maps_link) {
    return branch.google_maps_link;
  }
  if (branch.latitude != null && branch.longitude != null) {
    return `https://www.google.com/maps?q=${branch.latitude},${branch.longitude}`;
  }
  return null;
}
