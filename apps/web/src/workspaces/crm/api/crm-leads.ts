import { apiFetch, ApiError, getApiBaseUrl } from '@/lib/api/client';

export type CrmLeadStage =
  | 'yeni'
  | 'contacted'
  | 'following'
  | 'qualified'
  | 'converted'
  | 'unqualified';

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
  created_at: string;
  updated_at: string;
  existing_person_id?: string | null;
  existing_person_name?: string | null;
  activity?: CrmLeadActivityItem[];
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
  const response = await fetch(`${getApiBaseUrl()}/crm/leads${confirm ? '?confirm=true' : ''}`, {
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

export async function moveCrmLeadStage(id: string, stage: CrmLeadStage): Promise<CrmLeadItem> {
  return apiFetch<CrmLeadItem>(`/crm/leads/${id}/stage`, {
    method: 'POST',
    body: JSON.stringify({ stage }),
  });
}

export async function convertCrmLead(
  id: string,
  confirmExistingPersonId?: string,
): Promise<CrmLeadConvertResponse> {
  const response = await fetch(`${getApiBaseUrl()}/crm/leads/${id}/convert`, {
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
