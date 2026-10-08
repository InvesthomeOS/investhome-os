import { apiFetch, ApiError, getApiBaseUrl, staffFetch } from '@/lib/api/client';

export const CRM_LEAD_STAGES = [
  'yeni',
  'contacted',
  'following',
  'proposal',
  'qualified',
  'negotiation',
  'long_term',
  'unqualified',
  'converted',
] as const;

export type CrmLeadStage = (typeof CRM_LEAD_STAGES)[number];

export const CRM_LEAD_STAGE_LABELS: Record<CrmLeadStage, { tr: string; en: string }> = {
  yeni: { tr: 'Yeni Müşteri Adayı', en: 'New Lead' },
  contacted: { tr: 'Ulaşılamadı', en: 'Unreachable' },
  following: { tr: 'Proje Ortaklığı', en: 'Project Partnership' },
  proposal: { tr: 'Ön Bilgi / Teklif Aşaması', en: 'Info / Proposal' },
  qualified: { tr: 'Potansiyel', en: 'Potential' },
  negotiation: { tr: 'Satış Koridoru', en: 'Sales Corridor' },
  long_term: { tr: 'Uzun Dönem Yatırımcı', en: 'Long-term Investor' },
  unqualified: { tr: 'Junk Lead', en: 'Junk Lead' },
  converted: { tr: 'Satış Kapama', en: 'Sales Closing' },
};

export function crmLeadStageLabel(stage: CrmLeadStage, locale: 'tr' | 'en'): string {
  return CRM_LEAD_STAGE_LABELS[stage][locale];
}

export function crmLeadDisplayName(item: {
  full_name: string;
  contact_name?: string | null;
  converted_contact_name?: string | null;
  existing_person_name?: string | null;
}): string {
  const canonical =
    item.contact_name?.trim() ||
    item.converted_contact_name?.trim() ||
    item.existing_person_name?.trim();
  return canonical || item.full_name;
}

export const CRM_LEAD_JUNK_REASONS = [
  { code: 'unreachable', tr: 'Ulaşılamıyor', en: 'Unreachable' },
  { code: 'insufficient_budget', tr: 'Bütçe Yetersiz', en: 'Insufficient Budget' },
  { code: 'not_interested', tr: 'Yatırım Yapmayı Düşünmüyor', en: 'Not Interested in Investing' },
  { code: 'no_suitable_project', tr: 'Uygun Proje Bulunamadı', en: 'No Suitable Project' },
  { code: 'timing', tr: 'Zamanlama Uygun Değil', en: 'Timing Not Suitable' },
  { code: 'invested_elsewhere', tr: 'Başka Yerden Satın Aldı / Yatırım Yaptı', en: 'Purchased / Invested Elsewhere' },
  { code: 'invalid_contact', tr: 'Yanlış / Geçersiz İletişim Bilgisi', en: 'Invalid Contact Information' },
  { code: 'duplicate', tr: 'Mükerrer Kayıt', en: 'Duplicate Record' },
  { code: 'spam', tr: 'Spam / Sahte Lead', en: 'Spam / Fake Lead' },
  { code: 'other', tr: 'Diğer', en: 'Other' },
] as const;

export type CrmLeadJunkReason = (typeof CRM_LEAD_JUNK_REASONS)[number]['code'];

export function crmLeadJunkReasonLabel(code: string | null | undefined, locale: 'tr' | 'en'): string {
  const found = CRM_LEAD_JUNK_REASONS.find((item) => item.code === code);
  return found ? found[locale] : code || '—';
}

export function formatCrmInvestmentBudget(
  amount: string | null | undefined,
  currency: string | null | undefined,
  locale: 'tr' | 'en' = 'tr',
): string {
  void locale;
  if (amount == null || String(amount).trim() === '') return '—';
  const code = (currency || 'USD').trim().toUpperCase() || 'USD';
  const whole = String(amount).split('.')[0] ?? '';
  const digits = whole.replace(/[^\d-]/g, '');
  if (!digits) return '—';
  const formatted = new Intl.NumberFormat('en-US').format(BigInt(digits));
  if (code === 'USD') return `$${formatted}`;
  return `${formatted} ${code}`;
}

export function emptyCrmLeadStageBuckets<T>(): Record<CrmLeadStage, T[]> {
  const buckets = {} as Record<CrmLeadStage, T[]>;
  for (const stage of CRM_LEAD_STAGES) {
    buckets[stage] = [];
  }
  return buckets;
}

export type CrmLeadMatch = {
  kind: 'lead' | 'person';
  id: string;
  name: string;
  phone?: string | null;
  email?: string | null;
  reason: string;
  href?: string | null;
};

export type CrmLeadOwnerOption = {
  id: string;
  name: string;
};

export type CrmLeadActivityItem = {
  id: string;
  action: string;
  description: string;
  actor_name?: string | null;
  created_at: string;
  metadata?: Record<string, unknown> | null;
};

export type CrmLeadTaskItem = {
  id: string;
  title: string;
  due_date: string | null;
  timezone?: string | null;
  status: string;
  task_status?: string | null;
  contact_id?: string | null;
};

export type CrmLeadItem = {
  id: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  source: string | null;
  campaign: string | null;
  ad_id: string | null;
  form_id: string | null;
  project: string | null;
  owner_user_id: string | null;
  owner_name: string | null;
  stage: CrmLeadStage;
  notes: string | null;
  provider: string | null;
  ingest_status: string;
  converted_contact_id: string | null;
  converted_contact_name: string | null;
  contact_id?: string | null;
  contact_name?: string | null;
  investment_budget_amount?: string | null;
  investment_budget_currency?: string | null;
  junk_reason?: string | null;
  junk_reason_detail?: string | null;
  junked_at?: string | null;
  created_at: string;
  updated_at: string;
  existing_person_id?: string | null;
  existing_person_name?: string | null;
  activity?: CrmLeadActivityItem[];
  tasks?: CrmLeadTaskItem[];
};

export type CrmLeadKpis = {
  total: number;
  active: number;
  yeni: number;
  following: number;
  qualified: number;
  converted: number;
  unqualified: number;
  unmatched: number;
  failed: number;
};

export type CrmLeadListResponse = {
  items: CrmLeadItem[];
  total: number;
  kpis: CrmLeadKpis;
  sources: string[];
  projects: string[];
  owners: CrmLeadOwnerOption[];
  stages: CrmLeadStage[];
};

export type CrmLeadWrite = {
  full_name?: string;
  phone?: string;
  email?: string;
  source?: string;
  campaign?: string;
  ad_id?: string;
  form_id?: string;
  project?: string;
  owner_user_id?: string | null;
  notes?: string;
  stage?: CrmLeadStage;
  junk_reason?: string | null;
  junk_reason_detail?: string | null;
  investment_budget_amount?: string | null;
  investment_budget_currency?: string | null;
};

export type CrmLeadConvertResponse = {
  lead: CrmLeadItem;
  contact_id: string;
  contact_name: string;
  reused_existing: boolean;
  href: string;
};

export type CrmLeadListParams = {
  search?: string;
  stage?: string;
  source?: string;
  project?: string;
  owner_id?: string;
  date_from?: string;
  date_to?: string;
  ingest_status?: string;
  junk_reason?: string;
  surface?: 'leads' | 'pipeline';
};

export class CrmLeadConflictError extends Error {
  readonly status = 409;
  readonly code: string;
  readonly matches: CrmLeadMatch[];

  constructor(code: string, message: string, matches: CrmLeadMatch[]) {
    super(message);
    this.name = 'CrmLeadConflictError';
    this.code = code;
    this.matches = matches;
  }
}

function buildParams(values: Record<string, string | undefined>): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (!value) continue;
    params.set(key, value);
  }
  return params;
}

export async function fetchCrmLeads(params: CrmLeadListParams = {}): Promise<CrmLeadListResponse> {
  const query = buildParams({
    search: params.search,
    stage: params.stage,
    source: params.source,
    project: params.project,
    owner_id: params.owner_id,
    date_from: params.date_from,
    date_to: params.date_to,
    ingest_status: params.ingest_status,
    junk_reason: params.junk_reason,
    surface: params.surface,
  });
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<CrmLeadListResponse>(`/crm/leads${suffix}`);
}

export async function fetchCrmLead(id: string): Promise<CrmLeadItem> {
  return apiFetch<CrmLeadItem>(`/crm/leads/${id}`);
}

async function parseConflict(response: Response, fallback: string): Promise<never> {
  const body = (await response.json().catch(() => ({}))) as {
    detail?: string;
    error?: { code?: string; message?: string };
    matches?: CrmLeadMatch[];
  };
  throw new CrmLeadConflictError(
    body.error?.code || 'existing_person',
    body.error?.message || body.detail || fallback,
    body.matches ?? [],
  );
}

export async function createCrmLead(payload: CrmLeadWrite, confirm = false): Promise<CrmLeadItem> {
  const response = await staffFetch(`${getApiBaseUrl()}/crm/leads${confirm ? '?confirm=true' : ''}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    body: JSON.stringify(payload),
  });
  if (response.status === 409) {
    await parseConflict(response, 'Mevcut kayıt bulundu');
  }
  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status);
  }
  return response.json() as Promise<CrmLeadItem>;
}

export async function updateCrmLead(id: string, payload: CrmLeadWrite): Promise<CrmLeadItem> {
  return apiFetch<CrmLeadItem>(`/crm/leads/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function moveCrmLeadStage(
  id: string,
  stage: CrmLeadStage,
  extra?: { junk_reason?: string; junk_reason_detail?: string },
): Promise<CrmLeadItem> {
  return apiFetch<CrmLeadItem>(`/crm/leads/${id}/stage`, {
    method: 'POST',
    body: JSON.stringify({
      stage,
      ...(extra?.junk_reason ? { junk_reason: extra.junk_reason } : {}),
      ...(extra?.junk_reason_detail ? { junk_reason_detail: extra.junk_reason_detail } : {}),
    }),
  });
}

export async function convertCrmLead(
  id: string,
  confirmExistingPersonId?: string,
): Promise<CrmLeadConvertResponse> {
  const response = await staffFetch(`${getApiBaseUrl()}/crm/leads/${id}/convert`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    body: JSON.stringify({
      confirm_existing_person_id: confirmExistingPersonId || null,
    }),
  });
  if (response.status === 409) {
    await parseConflict(response, 'Kişi eşleşmesi belirsiz');
  }
  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status);
  }
  return response.json() as Promise<CrmLeadConvertResponse>;
}
