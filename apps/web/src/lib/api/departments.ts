import { apiFetch } from './client';

export type DepartmentStatus =
  | 'draft'
  | 'active'
  | 'inactive'
  | 'restructuring'
  | 'merging'
  | 'archived';

export type DepartmentSummary = {
  id: string;
  department_code: string;
  department_name: string;
  company_id: string;
  company_name: string | null;
  branch_id: string | null;
  branch_name: string | null;
  department_type: string;
  parent_department_id: string | null;
  department_head_user_id: string | null;
  head_name: string | null;
  cost_center: string | null;
  status: DepartmentStatus;
  employee_count: number;
  team_count: number;
  open_positions: number;
  annual_budget: string | null;
  currency: string | null;
  fiscal_year: number | null;
  created_at: string;
  updated_at: string;
};

export type DepartmentListResponse = {
  items: DepartmentSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type DepartmentListParams = {
  search?: string;
  company_id?: string;
  branch_id?: string;
  department_type?: string;
  status?: string;
  parent_department_id?: string;
  head_user_id?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
};

export async function fetchDepartments(params: DepartmentListParams = {}): Promise<DepartmentListResponse> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      searchParams.set(key, String(value));
    }
  });
  const query = searchParams.toString();
  return apiFetch<DepartmentListResponse>(`/departments${query ? `?${query}` : ''}`);
}

export async function exportDepartmentsCsv(params: DepartmentListParams = {}): Promise<Blob> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      searchParams.set(key, String(value));
    }
  });
  const query = searchParams.toString();
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/departments/export${query ? `?${query}` : ''}`,
    { credentials: 'include' },
  );
  if (!response.ok) {
    throw new Error('Export failed');
  }
  return response.blob();
}
