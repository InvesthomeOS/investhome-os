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
  purchase_card_enabled?: boolean;
  owners_label?: string | null;
  bitrix_deal_id?: string | null;
  amount_label?: string | null;
  stage_label?: string | null;
  participants?: Array<{
    contact_id: string;
    display_name: string;
    role: string;
    ownership_pct: string | null;
    is_primary: boolean;
    source: string | null;
  }>;
};

export type CrmPurchaseDocument = {
  id: string;
  title: string;
  original_file_name: string | null;
  bitrix_file_id: string | null;
  bitrix_entity_type: string | null;
  bitrix_entity_id: string | null;
  document_type?: string | null;
  mime_type?: string | null;
  source?: string | null;
  created_at?: string | null;
};

export type CrmPurchaseOwner = {
  contact_id: string;
  display_name: string;
  role: string;
  ownership_pct: string | null;
  is_primary: boolean;
  source: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  company?: string | null;
  position?: string | null;
  responsible?: string | null;
};

export type CrmRelatedPurchase = {
  agreement_id: string;
  project_label: string;
  unit_number: string | null;
  amount_label: string | null;
  owners_label: string | null;
  is_current: boolean;
};

export type CrmLabeledValue = {
  label: string;
  value: string;
};

export type CrmPurchaseCard = {
  agreement_id: string;
  bitrix_deal_id: string | null;
  project_group: string;
  project_label: string;
  unit_number: string | null;
  amount: string | null;
  currency: string | null;
  amount_label: string | null;
  stage: string | null;
  begin_date: string | null;
  close_date: string | null;
  status: CrmAgreementStatus;
  primary_contact_id: string;
  owners_label: string | null;
  participants: CrmPurchaseOwner[];
  payment: Record<string, unknown>;
  history: Array<{
    id: string;
    source: string;
    activity_type: string;
    title: string;
    summary: string | null;
    status: string | null;
    actor_name: string | null;
    created_at: string;
    is_system_event: boolean;
    imported_historical_comment?: boolean;
    metadata?: Record<string, unknown> | null;
  }>;
  history_count: number;
  documents: CrmPurchaseDocument[];
  document_count: number;
  responsible_name?: string | null;
  comments?: string | null;
  agreement_date?: string | null;
  related_purchases?: CrmRelatedPurchase[];
  primary_contact_name?: string | null;
  llc_name?: string | null;
  payment_fields?: CrmLabeledValue[];
  llc_fields?: CrmLabeledValue[];
  extra_fields?: CrmLabeledValue[];
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

export async function fetchPurchaseCard(
  agreementId: string,
  viewerContactId?: string | null,
): Promise<CrmPurchaseCard> {
  const search = viewerContactId ? `?viewer_contact_id=${viewerContactId}` : '';
  return apiFetch<CrmPurchaseCard>(`/crm/agreements/${agreementId}${search}`);
}
