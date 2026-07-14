import { apiFetch } from '@/lib/api/client';
import { formatBudget, formatDate } from '@/lib/api/leads';

export const PROJECT_TYPES = [
  'residential',
  'mixed_use',
  'commercial',
  'land',
  'multifamily',
  'condominium',
  'single_family',
  'townhome',
] as const;

export type ProjectType = (typeof PROJECT_TYPES)[number];

export const DEVELOPMENT_TYPES = [
  'ground_up',
  'renovation',
  'conversion',
  'value_add',
  'fix_and_flip',
  'rental',
  'land_development',
] as const;

export type DevelopmentType = (typeof DEVELOPMENT_TYPES)[number];

export const PROJECT_STATUSES = [
  'pipeline',
  'due_diligence',
  'acquisition',
  'pre_development',
  'permitting',
  'construction',
  'leasing',
  'sales',
  'stabilization',
  'completed',
  'on_hold',
  'cancelled',
] as const;

export type ProjectStatus = (typeof PROJECT_STATUSES)[number];

export interface Project {
  id: string;
  project_code: string;
  project_name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  project_type: ProjectType;
  development_type: DevelopmentType;
  project_status: ProjectStatus;
  ownership_entity: string | null;
  total_units: number | null;
  residential_units: number | null;
  commercial_units: number | null;
  gross_square_feet: number | null;
  acquisition_price: string | null;
  total_development_cost: string | null;
  current_project_value: string | null;
  projected_sale_value: string | null;
  equity_required: string | null;
  equity_raised: string | null;
  debt_amount: string | null;
  loan_to_cost: string | null;
  projected_revenue: string | null;
  projected_profit: string | null;
  projected_roi: string | null;
  projected_irr: string | null;
  start_date: string | null;
  target_completion_date: string | null;
  actual_completion_date: string | null;
  assigned_project_manager: string | null;
  description: string | null;
  notes: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ProjectStats {
  total: number;
  active: number;
  units_under_development: number;
  total_development_cost: string;
  current_portfolio_value: string;
  equity_raised: string;
}

export interface ProjectInput {
  project_code: string;
  project_name: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  project_type?: ProjectType;
  development_type?: DevelopmentType;
  project_status?: ProjectStatus;
  ownership_entity?: string | null;
  total_units?: number | null;
  residential_units?: number | null;
  commercial_units?: number | null;
  gross_square_feet?: number | null;
  acquisition_price?: number | null;
  total_development_cost?: number | null;
  current_project_value?: number | null;
  projected_sale_value?: number | null;
  equity_required?: number | null;
  equity_raised?: number | null;
  debt_amount?: number | null;
  loan_to_cost?: number | null;
  projected_revenue?: number | null;
  projected_profit?: number | null;
  projected_roi?: number | null;
  projected_irr?: number | null;
  start_date?: string | null;
  target_completion_date?: string | null;
  actual_completion_date?: string | null;
  assigned_project_manager?: string | null;
  description?: string | null;
  notes?: string | null;
}

export interface ProjectFilters {
  search?: string;
  status?: ProjectStatus | '';
  project_type?: ProjectType | '';
  development_type?: DevelopmentType | '';
  city?: string;
  assigned_project_manager?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

function buildQuery(filters: ProjectFilters = {}): string {
  const params = new URLSearchParams();

  if (filters.search?.trim()) {
    params.set('search', filters.search.trim());
  }
  if (filters.status) {
    params.set('status', filters.status);
  }
  if (filters.project_type) {
    params.set('project_type', filters.project_type);
  }
  if (filters.development_type) {
    params.set('development_type', filters.development_type);
  }
  if (filters.city?.trim()) {
    params.set('city', filters.city.trim());
  }
  if (filters.assigned_project_manager?.trim()) {
    params.set('assigned_project_manager', filters.assigned_project_manager.trim());
  }
  if (filters.sort_by) {
    params.set('sort_by', filters.sort_by);
  }
  if (filters.sort_order) {
    params.set('sort_order', filters.sort_order);
  }
  if (filters.page) {
    params.set('page', String(filters.page));
  }
  if (filters.page_size) {
    params.set('page_size', String(filters.page_size));
  }

  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchProjects(filters: ProjectFilters = {}): Promise<ProjectListResponse> {
  return apiFetch<ProjectListResponse>(`/projects${buildQuery(filters)}`);
}

export async function fetchProjectStats(): Promise<ProjectStats> {
  return apiFetch<ProjectStats>('/projects/stats');
}

export async function fetchProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`);
}

export async function createProject(input: ProjectInput): Promise<Project> {
  return apiFetch<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateProject(
  id: string,
  input: Partial<ProjectInput>,
): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function archiveProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`, {
    method: 'DELETE',
  });
}

export { formatBudget as formatCurrency, formatDate };

export function formatShortDate(value: string | null, locale = 'tr'): string {
  if (!value) {
    return '—';
  }

  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-GB';
  return new Intl.DateTimeFormat(intlLocale, { dateStyle: 'medium' }).format(new Date(value));
}

export function formatPercent(value: string | null, locale = 'tr'): string {
  if (!value) {
    return '—';
  }

  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return value;
  }

  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';

  return new Intl.NumberFormat(intlLocale, {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(amount / 100);
}

export function formatLocation(project: Project): string {
  const parts = [project.city, project.state].filter(Boolean);
  if (parts.length === 0) {
    return '—';
  }
  return parts.join(', ');
}

export function formatNumber(value: number | null | undefined, locale = 'tr'): string {
  if (value === null || value === undefined) {
    return '—';
  }

  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return new Intl.NumberFormat(intlLocale).format(value);
}
