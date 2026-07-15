import { apiFetch } from '@/lib/api/client';

export type CompanyProfile = {
  id: string;
  company_name: string;
  legal_name: string | null;
  short_name: string | null;
  company_code: string;
  slogan: string | null;
  description: string | null;
  website: string | null;
  primary_email: string | null;
  primary_phone: string | null;
  tax_id: string | null;
  registration_number: string | null;
  country: string | null;
  state_or_region: string | null;
  city: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  postal_code: string | null;
  default_language: string;
  default_timezone: string;
  default_currency: string;
  default_measurement_system: string;
  default_area_unit: string;
  default_date_format: string;
  default_number_format: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type BrandProfile = {
  id: string;
  company_id: string;
  brand_name: string;
  brand_code: string;
  legal_display_name: string | null;
  slogan: string | null;
  brand_description: string | null;
  logo_primary_document_id: string | null;
  logo_secondary_document_id: string | null;
  logo_monochrome_document_id: string | null;
  favicon_document_id: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  accent_color: string | null;
  background_color: string | null;
  surface_color: string | null;
  text_primary_color: string | null;
  text_secondary_color: string | null;
  success_color: string | null;
  warning_color: string | null;
  error_color: string | null;
  font_heading: string | null;
  font_body: string | null;
  font_monospace: string | null;
  border_radius_style: string | null;
  standard_disclaimer_tr: string | null;
  standard_disclaimer_en: string | null;
  email_footer_tr: string | null;
  email_footer_en: string | null;
  social_links: Record<string, string> | null;
  contact_information: Record<string, string> | null;
  is_default: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type Office = {
  id: string;
  company_id: string;
  office_name: string;
  office_code: string;
  office_type: string;
  country: string | null;
  state_or_region: string | null;
  city: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  postal_code: string | null;
  phone: string | null;
  email: string | null;
  timezone: string | null;
  default_currency: string | null;
  is_primary: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type BrandAsset = {
  id: string;
  brand_profile_id: string;
  document_id: string;
  asset_type: string;
  title: string | null;
  language: string | null;
  usage_notes: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type PreferenceItem = {
  preference_key: string;
  category: string;
  value: unknown;
  is_secret: boolean;
  is_configured: boolean;
};

export type SystemPreferences = {
  items: PreferenceItem[];
  categories: Record<string, PreferenceItem[]>;
};

export type SupportedOptions = {
  currencies: string[];
  languages: string[];
  measurement_systems: string[];
  area_units: string[];
  length_units: string[];
  office_types: string[];
  brand_asset_types: string[];
};

export type ProviderStatus = {
  provider_id: string;
  category: string;
  status: string;
  configured: boolean;
  message_key: string;
  requires_secret: boolean;
};

export type Department = {
  id: string;
  company_id: string;
  name: string;
  code: string;
  description: string | null;
  manager_user_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Team = {
  id: string;
  department_id: string;
  name: string;
  code: string;
  description: string | null;
  manager_user_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type CompanyContext = {
  company_name: string;
  short_name: string | null;
  slogan: string | null;
  default_language: string;
  default_timezone: string;
  default_currency: string;
  default_measurement_system: string;
  default_area_unit: string;
  brand: BrandProfile | null;
};

export type PublicBrand = {
  company_name: string;
  short_name: string | null;
  slogan: string | null;
  primary_color: string | null;
  accent_color: string | null;
  logo_primary_document_id: string | null;
};

export function fetchPublicBrand() {
  return apiFetch<PublicBrand>('/company/public-brand');
}

export function fetchCompanyContext() {
  return apiFetch<CompanyContext>('/company/context');
}

export function fetchCompanyProfile() {
  return apiFetch<CompanyProfile>('/company/profile');
}

export function updateCompanyProfile(body: Partial<CompanyProfile>) {
  return apiFetch<CompanyProfile>('/company/profile', {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export function fetchOffices(includeArchived = false) {
  return apiFetch<Office[]>(`/offices?include_archived=${includeArchived}`);
}

export function createOffice(body: Record<string, unknown>) {
  return apiFetch<Office>('/offices', { method: 'POST', body: JSON.stringify(body) });
}

export function updateOffice(id: string, body: Record<string, unknown>) {
  return apiFetch<Office>(`/offices/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
}

export function archiveOffice(id: string) {
  return apiFetch<Office>(`/offices/${id}/archive`, { method: 'POST' });
}

export function fetchBrands(includeArchived = false) {
  return apiFetch<BrandProfile[]>(`/brands?include_archived=${includeArchived}`);
}

export function updateBrand(id: string, body: Record<string, unknown>) {
  return apiFetch<BrandProfile>(`/brands/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
}

export function setDefaultBrand(id: string) {
  return apiFetch<BrandProfile>(`/brands/${id}/set-default`, { method: 'POST' });
}

export function fetchBrandAssets(brandId: string) {
  return apiFetch<BrandAsset[]>(`/brands/${brandId}/assets`);
}

export function linkBrandAsset(brandId: string, body: Record<string, unknown>) {
  return apiFetch<BrandAsset>(`/brands/${brandId}/assets`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function fetchPreferences() {
  return apiFetch<SystemPreferences>('/settings/preferences');
}

export function updatePreferences(preferences: Record<string, unknown>) {
  return apiFetch<SystemPreferences>('/settings/preferences', {
    method: 'PATCH',
    body: JSON.stringify({ preferences }),
  });
}

export function fetchSupportedOptions() {
  return apiFetch<SupportedOptions>('/settings/supported-options');
}

export function fetchProviderStatuses() {
  return apiFetch<{ items: ProviderStatus[] }>('/settings/providers');
}

export function fetchDepartments() {
  return apiFetch<Department[]>('/organization/departments');
}

export function createDepartment(body: Record<string, unknown>) {
  return apiFetch<Department>('/organization/departments', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function fetchTeams(departmentId: string) {
  return apiFetch<Team[]>(`/organization/departments/${departmentId}/teams`);
}

export function createTeam(departmentId: string, body: Record<string, unknown>) {
  return apiFetch<Team>(`/organization/departments/${departmentId}/teams`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
