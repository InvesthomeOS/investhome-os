import { apiFetch, getApiBaseUrl, staffFetch } from './client';

export type CompanyEntityType =
  | 'corporation'
  | 'llc'
  | 'lp'
  | 'llp'
  | 'holding'
  | 'trust'
  | 'branch'
  | 'subsidiary'
  | 'joint_venture'
  | 'foundation'
  | 'non_profit'
  | 'other';

export type CompanyStatus =
  | 'draft'
  | 'pending_review'
  | 'active'
  | 'inactive'
  | 'suspended'
  | 'closed'
  | 'archived';

export type CompanyAddress = {
  id: string;
  address_type: string;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
};

export type CompanyContact = {
  id: string;
  role: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  is_signatory: boolean;
  created_at: string;
  updated_at: string;
};

export type CompanyBankAccount = {
  id: string;
  bank_name: string;
  account_name: string | null;
  account_number: string | null;
  iban: string | null;
  routing_number: string | null;
  currency: string;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
};

export type CompanyDocument = {
  id: string;
  document_id: string | null;
  title: string;
  reference_code: string | null;
  notes: string | null;
  created_at: string;
};

export type CompanyRelationship = {
  id: string;
  related_company_id: string;
  related_company_name: string | null;
  relationship_type: string;
  notes: string | null;
  created_at: string;
};

export type CompanyListItem = {
  id: string;
  logo_document_id: string | null;
  company_name: string;
  legal_name: string | null;
  entity_type: CompanyEntityType;
  registration_number: string | null;
  tax_id: string | null;
  country: string | null;
  state: string | null;
  city: string | null;
  status: CompanyStatus;
  industry: string | null;
  owner_user_id: string | null;
  owner_name: string | null;
  employee_count: number;
  branch_count: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type CompanyRecord = CompanyListItem & {
  notes: string | null;
  addresses: CompanyAddress[];
  contacts: CompanyContact[];
  bank_accounts: CompanyBankAccount[];
  documents: CompanyDocument[];
  relationships: CompanyRelationship[];
};

export type CompanyListResponse = {
  items: CompanyListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type CompanyListParams = {
  search?: string;
  status?: CompanyStatus;
  country?: string;
  entity_type?: CompanyEntityType;
  owner_user_id?: string;
  industry?: string;
  created_from?: string;
  created_to?: string;
  include_archived?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
};

export type CompanyCreatePayload = {
  company_name: string;
  legal_name?: string | null;
  entity_type?: CompanyEntityType;
  registration_number?: string | null;
  tax_id?: string | null;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  status?: CompanyStatus;
  industry?: string | null;
  owner_user_id?: string | null;
  logo_document_id?: string | null;
  notes?: string | null;
};

export type CompanyUpdatePayload = Partial<CompanyCreatePayload>;

export type CompanyImportResult = {
  imported: number;
  skipped: number;
  errors: string[];
};

function buildQuery(params: CompanyListParams): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value));
    }
  });
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export async function fetchCompanies(params: CompanyListParams = {}): Promise<CompanyListResponse> {
  return apiFetch<CompanyListResponse>(`/companies${buildQuery(params)}`);
}

export async function fetchCompany(companyId: string): Promise<CompanyRecord> {
  return apiFetch<CompanyRecord>(`/companies/${companyId}`);
}

export async function createCompany(payload: CompanyCreatePayload): Promise<CompanyRecord> {
  return apiFetch<CompanyRecord>('/companies', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateCompany(companyId: string, payload: CompanyUpdatePayload): Promise<CompanyRecord> {
  return apiFetch<CompanyRecord>(`/companies/${companyId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteCompany(companyId: string): Promise<void> {
  await apiFetch<void>(`/companies/${companyId}`, { method: 'DELETE' });
}

export async function archiveCompany(companyId: string): Promise<CompanyRecord> {
  return apiFetch<CompanyRecord>(`/companies/${companyId}/archive`, { method: 'PATCH' });
}

export async function deactivateCompany(companyId: string): Promise<CompanyRecord> {
  return apiFetch<CompanyRecord>(`/companies/${companyId}/deactivate`, { method: 'PATCH' });
}

export async function duplicateCompany(companyId: string): Promise<CompanyRecord> {
  const response = await apiFetch<{ company: CompanyRecord }>(`/companies/${companyId}/duplicate`, {
    method: 'POST',
  });
  return response.company;
}

export async function transferCompanyOwnership(
  companyId: string,
  ownerUserId: string,
): Promise<CompanyRecord> {
  return apiFetch<CompanyRecord>(`/companies/${companyId}/transfer-ownership`, {
    method: 'PATCH',
    body: JSON.stringify({ owner_user_id: ownerUserId }),
  });
}

export async function exportCompanies(includeArchived = false): Promise<string> {
  const params = includeArchived ? '?include_archived=true' : '';
  const response = await staffFetch(`${getApiBaseUrl()}/companies/export${params}`, {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Export failed');
  }
  return response.text();
}

export async function importCompanies(file: File): Promise<CompanyImportResult> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await staffFetch(`${getApiBaseUrl()}/companies/import`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Import failed');
  }
  return response.json() as Promise<CompanyImportResult>;
}
