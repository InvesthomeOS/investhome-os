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
  hemen_kira?: boolean;
  responsible_name?: string | null;
  next_activity_title?: string | null;
  next_activity_at?: string | null;
  payment_status?: string | null;
  payment_method?: string | null;
  share_ratio?: string | null;
  company_details?: string | null;
  payment_dates?: string | null;
  floor?: string | null;
  deposit_amount?: string | null;
  customer_journey?: string | null;
  potential_status?: string | null;
  begin_date?: string | null;
  close_date?: string | null;
  joint_owners?: boolean;
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
  checksum?: string | null;
  hidden_from_view?: boolean;
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
  is_historical_unit_change?: boolean;
};

export type CrmUnitHistoryStep = {
  agreement_id: string;
  unit_number: string;
  is_current: boolean;
  is_historical_unit_change?: boolean;
  contact_id?: string | null;
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
  person_documents?: CrmPurchaseDocument[];
  person_document_count?: number;
  responsible_name?: string | null;
  comments?: string | null;
  agreement_date?: string | null;
  related_purchases?: CrmRelatedPurchase[];
  primary_contact_name?: string | null;
  llc_name?: string | null;
  payment_fields?: CrmLabeledValue[];
  llc_fields?: CrmLabeledValue[];
  extra_fields?: CrmLabeledValue[];
  hemen_kira?: boolean;
  unit_history?: CrmUnitHistoryStep[];
};

export type CrmAgreementActivityItem = {
  id: string;
  agreement_id: string | null;
  contact_id: string | null;
  contact_name: string | null;
  project_group: string | null;
  project_label: string | null;
  activity_type: string;
  title: string;
  summary: string | null;
  actor_name: string | null;
  responsible_name: string | null;
  created_at: string;
  start_date: string | null;
  due_date: string | null;
};

export type CrmAgreementActivityListResponse = {
  items: CrmAgreementActivityItem[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  request_id: string;
};

export type CrmAgreementCalendarItem = {
  id: string;
  title: string;
  date: string;
  kind: string;
  agreement_id: string | null;
  contact_name: string | null;
  project_label: string | null;
  activity_type: string | null;
};

export type CrmAgreementCalendarResponse = {
  items: CrmAgreementCalendarItem[];
  start: string;
  end: string;
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
  contact_id?: string;
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
  if (params.contact_id) search.set('contact_id', params.contact_id);
  return apiFetch<CrmAgreementListResponse>(`/crm/agreements?${search.toString()}`);
}

export async function fetchPurchaseCard(
  agreementId: string,
  viewerContactId?: string | null,
  options: { includeHidden?: boolean } = {},
): Promise<CrmPurchaseCard> {
  const search = new URLSearchParams();
  if (viewerContactId) search.set('viewer_contact_id', viewerContactId);
  if (options.includeHidden) search.set('include_hidden', 'true');
  const query = search.toString();
  return apiFetch<CrmPurchaseCard>(`/crm/agreements/${agreementId}${query ? `?${query}` : ''}`);
}

export async function patchAgreement(
  agreementId: string,
  payload: { hemen_kira: boolean },
): Promise<CrmPurchaseCard> {
  return apiFetch<CrmPurchaseCard>(`/crm/agreements/${agreementId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function fetchAgreementActivities(params: {
  project_group?: string;
  contact_id?: string;
  activity_type?: string;
  responsible?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}): Promise<CrmAgreementActivityListResponse> {
  const search = new URLSearchParams();
  search.set('page', String(params.page ?? 1));
  search.set('page_size', String(params.page_size ?? 50));
  if (params.project_group) search.set('project_group', params.project_group);
  if (params.contact_id) search.set('contact_id', params.contact_id);
  if (params.activity_type) search.set('activity_type', params.activity_type);
  if (params.responsible) search.set('responsible', params.responsible);
  if (params.date_from) search.set('date_from', params.date_from);
  if (params.date_to) search.set('date_to', params.date_to);
  return apiFetch<CrmAgreementActivityListResponse>(`/crm/agreements/activities?${search.toString()}`);
}

export async function fetchAgreementCalendar(params: {
  start: string;
  end: string;
  project_group?: string;
  contact_id?: string;
}): Promise<CrmAgreementCalendarResponse> {
  const search = new URLSearchParams();
  search.set('start', params.start);
  search.set('end', params.end);
  if (params.project_group) search.set('project_group', params.project_group);
  if (params.contact_id) search.set('contact_id', params.contact_id);
  return apiFetch<CrmAgreementCalendarResponse>(`/crm/agreements/calendar?${search.toString()}`);
}
