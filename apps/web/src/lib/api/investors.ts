import { apiFetch } from '@/lib/api/client';
import { formatBudget, formatDate } from '@/lib/api/leads';

export const INVESTOR_TYPES = [
  'individual',
  'company',
  'family_office',
  'fund',
  'institutional',
  'broker',
  'referral_partner',
] as const;

export type InvestorType = (typeof INVESTOR_TYPES)[number];

export const INVESTOR_STATUSES = [
  'prospect',
  'contacted',
  'qualified',
  'active',
  'invested',
  'follow_up',
  'dormant',
  'rejected',
] as const;

export type InvestorStatus = (typeof INVESTOR_STATUSES)[number];

export const INVESTMENT_MODELS = [
  'development_equity',
  'rental_income',
  'fix_and_flip',
  'debt_investment',
  'bulk_purchase',
  'joint_venture',
  'other',
] as const;

export type InvestmentModel = (typeof INVESTMENT_MODELS)[number];

export const ACCREDITATION_STATUSES = [
  'unknown',
  'self_certified',
  'verified',
  'not_accredited',
] as const;

export type AccreditationStatus = (typeof ACCREDITATION_STATUSES)[number];

export const RISK_PROFILES = ['conservative', 'balanced', 'growth', 'aggressive'] as const;

export type RiskProfile = (typeof RISK_PROFILES)[number];

export interface Investor {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  country: string | null;
  city: string | null;
  investor_type: InvestorType;
  accreditation_status: AccreditationStatus;
  preferred_investment_model: InvestmentModel | null;
  investment_capacity: string | null;
  minimum_ticket: string | null;
  maximum_ticket: string | null;
  preferred_markets: string | null;
  preferred_projects: string | null;
  risk_profile: RiskProfile | null;
  status: InvestorStatus;
  assigned_to: string | null;
  source: string | null;
  notes: string | null;
  last_contact_date: string | null;
  next_follow_up_date: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvestorListResponse {
  items: Investor[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface InvestorStats {
  total: number;
  active: number;
  invested: number;
  total_investment_capacity: string;
}

export interface InvestorInput {
  full_name: string;
  email?: string | null;
  phone?: string | null;
  country?: string | null;
  city?: string | null;
  investor_type?: InvestorType;
  accreditation_status?: AccreditationStatus;
  preferred_investment_model?: InvestmentModel | null;
  investment_capacity?: number | null;
  minimum_ticket?: number | null;
  maximum_ticket?: number | null;
  preferred_markets?: string | null;
  preferred_projects?: string | null;
  risk_profile?: RiskProfile | null;
  status?: InvestorStatus;
  assigned_to?: string | null;
  source?: string | null;
  notes?: string | null;
  last_contact_date?: string | null;
  next_follow_up_date?: string | null;
}

export interface InvestorFilters {
  search?: string;
  status?: InvestorStatus | '';
  investor_type?: InvestorType | '';
  country?: string;
  preferred_investment_model?: InvestmentModel | '';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

function buildQuery(filters: InvestorFilters = {}): string {
  const params = new URLSearchParams();

  if (filters.search?.trim()) {
    params.set('search', filters.search.trim());
  }
  if (filters.status) {
    params.set('status', filters.status);
  }
  if (filters.investor_type) {
    params.set('investor_type', filters.investor_type);
  }
  if (filters.country?.trim()) {
    params.set('country', filters.country.trim());
  }
  if (filters.preferred_investment_model) {
    params.set('preferred_investment_model', filters.preferred_investment_model);
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

export async function fetchInvestors(filters: InvestorFilters = {}): Promise<InvestorListResponse> {
  return apiFetch<InvestorListResponse>(`/investors${buildQuery(filters)}`);
}

export async function fetchInvestorStats(): Promise<InvestorStats> {
  return apiFetch<InvestorStats>('/investors/stats');
}

export async function fetchInvestor(id: string): Promise<Investor> {
  return apiFetch<Investor>(`/investors/${id}`);
}

export async function createInvestor(input: InvestorInput): Promise<Investor> {
  return apiFetch<Investor>('/investors', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateInvestor(
  id: string,
  input: Partial<InvestorInput>,
): Promise<Investor> {
  return apiFetch<Investor>(`/investors/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function archiveInvestor(id: string): Promise<Investor> {
  return apiFetch<Investor>(`/investors/${id}`, {
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
