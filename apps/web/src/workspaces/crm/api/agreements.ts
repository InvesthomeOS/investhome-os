import { apiFetch } from '@/lib/api/client';

export type CrmAgreementStatus = 'active' | 'completed' | 'cancelled' | 'unknown';

export type CrmAgreementSummary = {
  id: string;
  contact_id: string;
  contact_name: string | null;
  project_id: string | null;
  project_group: string;
  project_group_label: string;
  source: string;
  source_external_id: string | null;
  status: CrmAgreementStatus;
  agreement_date: string | null;
  unit_number: string | null;
  investment_amount: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  review_required: boolean;
  created_at: string;
  updated_at: string;
};

export type CrmAgreementListResponse = {
  items: CrmAgreementSummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  request_id: string;
  project_groups: { id: string; label: string }[];
};

export type AgreementListParams = {
  project_group?: string;
  status?: CrmAgreementStatus;
  page?: number;
  page_size?: number;
};

export async function fetchAgreements(
  params: AgreementListParams = {},
): Promise<CrmAgreementListResponse> {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.page_size ?? 25));
  if (params.project_group) search.set('project_group', params.project_group);
  if (params.status) search.set('status', params.status);
  return apiFetch<CrmAgreementListResponse>(`/crm/agreements?${search.toString()}`);
}
