import { apiFetch } from '@/lib/api/client';

export const LEAD_STATUSES = [
  'New',
  'Contacted',
  'Qualified',
  'Meeting Scheduled',
  'Proposal Sent',
  'Negotiation',
  'Won',
  'Lost',
] as const;

export type LeadStatus = (typeof LEAD_STATUSES)[number];

export const LEAD_SOURCES = [
  'Website',
  'Referral',
  'Exhibition',
  'LinkedIn',
  'Partner',
  'Cold Outreach',
] as const;

export type LeadSource = (typeof LEAD_SOURCES)[number];

export interface Lead {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  country: string | null;
  source: string | null;
  status: LeadStatus;
  assigned_to: string | null;
  assigned_manager_id: string | null;
  company: string | null;
  preferred_market: string | null;
  cached_lead_score: number | null;
  estimated_budget: string | null;
  interested_project: string | null;
  notes: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
}

export interface LeadInput {
  full_name: string;
  email?: string | null;
  phone?: string | null;
  country?: string | null;
  source?: string | null;
  status?: LeadStatus;
  assigned_to?: string | null;
  estimated_budget?: number | null;
  interested_project?: string | null;
  notes?: string | null;
}

export interface LeadFilters {
  search?: string;
  status?: LeadStatus | '';
  source?: string;
  qualification_status?: string;
  preferred_market?: string;
  lead_score_min?: number;
  lead_score_max?: number;
}

function buildQuery(filters: LeadFilters = {}): string {
  const params = new URLSearchParams();

  if (filters.search?.trim()) {
    params.set('search', filters.search.trim());
  }
  if (filters.status) {
    params.set('status', filters.status);
  }
  if (filters.source) {
    params.set('source', filters.source);
  }
  if (filters.qualification_status) {
    params.set('qualification_status', filters.qualification_status);
  }
  if (filters.preferred_market) {
    params.set('preferred_market', filters.preferred_market);
  }
  if (filters.lead_score_min != null) {
    params.set('lead_score_min', String(filters.lead_score_min));
  }
  if (filters.lead_score_max != null) {
    params.set('lead_score_max', String(filters.lead_score_max));
  }

  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchLeads(filters: LeadFilters = {}): Promise<LeadListResponse> {
  return apiFetch<LeadListResponse>(`/leads${buildQuery(filters)}`);
}

export async function fetchLead(id: string): Promise<Lead> {
  return apiFetch<Lead>(`/leads/${id}`);
}

export async function createLead(input: LeadInput): Promise<Lead> {
  return apiFetch<Lead>('/leads', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateLead(id: string, input: Partial<LeadInput>): Promise<Lead> {
  return apiFetch<Lead>(`/leads/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function archiveLead(id: string): Promise<Lead> {
  return apiFetch<Lead>(`/leads/${id}`, {
    method: 'DELETE',
  });
}

export function formatBudget(value: string | null, locale = 'tr'): string {
  if (!value) {
    return '—';
  }

  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return value;
  }

  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';

  return new Intl.NumberFormat(intlLocale, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(value: string, locale = 'tr'): string {
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-GB';

  return new Intl.DateTimeFormat(intlLocale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
