import { apiFetch } from '@/lib/api/client';

export type CrmMatchKind = 'strong' | 'possible';
export type CrmMatchStatus = 'pending' | 'in_review' | 'same_person' | 'different';
export type CrmMatchAction = 'same_person' | 'different' | 'in_review';

export type CrmMatchEvidence = {
  reason: string;
  value?: string | null;
};

export type CrmMatchPurchase = {
  id: string;
  project?: string | null;
  unit?: string | null;
  source_id?: string | null;
  historical: boolean;
};

export type CrmMatchPerson = {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  secondary_emails: string[];
  source: string | null;
  source_ids: string[];
  notes: string | null;
  review_required: boolean;
  href: string;
  purchases: CrmMatchPurchase[];
};

export type CrmMatchItem = {
  id: string;
  person_a_id: string;
  person_a_name: string;
  person_b_id: string;
  person_b_name: string;
  reasons: string[];
  match_kind: CrmMatchKind;
  shared_phone: string | null;
  shared_email: string | null;
  source: string | null;
  status: CrmMatchStatus;
  protected: boolean;
  protected_reason: string | null;
  merge_queued: boolean;
  review_notes: string | null;
  created_at?: string | null;
};

export type CrmMatchDetail = CrmMatchItem & {
  person_a: CrmMatchPerson;
  person_b: CrmMatchPerson;
  evidence: CrmMatchEvidence[];
  conflicts: string[];
  linked_purchases: CrmMatchPurchase[];
  merge_blocked: boolean;
  merge_message: string;
};

export type CrmMatchKpis = {
  pending: number;
  strong: number;
  possible: number;
  rejected: number;
  same_person: number;
};

export type CrmMatchListResponse = {
  items: CrmMatchItem[];
  total: number;
  kpis: CrmMatchKpis;
  sources: string[];
  reasons: string[];
};

export type CrmMatchListParams = {
  search?: string;
  match_type?: string;
  status?: string;
  source?: string;
};

function buildParams(values: Record<string, string | undefined>): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (!value) continue;
    params.set(key, value);
  }
  return params;
}

export async function fetchCrmMatches(params: CrmMatchListParams = {}): Promise<CrmMatchListResponse> {
  const query = buildParams({
    search: params.search,
    match_type: params.match_type,
    status: params.status,
    source: params.source,
  });
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<CrmMatchListResponse>(`/crm/matches${suffix}`);
}

export async function fetchCrmMatch(id: string): Promise<CrmMatchDetail> {
  return apiFetch<CrmMatchDetail>(`/crm/matches/${id}`);
}

export async function decideCrmMatch(
  id: string,
  action: CrmMatchAction,
  notes?: string,
): Promise<CrmMatchDetail> {
  return apiFetch<CrmMatchDetail>(`/crm/matches/${id}/decision`, {
    method: 'POST',
    body: JSON.stringify({ action, notes: notes || null }),
  });
}
