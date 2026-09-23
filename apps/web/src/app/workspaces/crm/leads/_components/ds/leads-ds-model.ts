import type { IhIconName } from '@/components/icons/ih-icons';
import {
  LEAD_SOURCES,
  LEAD_STATUSES,
  type Lead,
  type LeadSource,
  type LeadStatus,
} from '@/lib/api/leads';

export type LeadAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';
export type StatusTone = 'success' | 'warning' | 'info' | 'default' | 'danger';
export type ScoreBand = 'green' | 'yellow' | 'orange' | 'red';

export type LeadQuickFilter =
  | 'all'
  | 'new'
  | 'active'
  | 'hot'
  | 'qualified'
  | 'follow_up'
  | 'converted'
  | 'archived';

export type LeadSortKey =
  | 'activity_desc'
  | 'name_asc'
  | 'name_desc'
  | 'score_desc'
  | 'created_desc'
  | 'budget_desc';

export type LeadScoreFilter = '' | 'high' | 'medium' | 'low';

export type LeadsKpiKey =
  | 'total'
  | 'active'
  | 'hot'
  | 'potentialValue'
  | 'converted';

export type LeadsDsFilters = {
  search: string;
  status: LeadStatus | '';
  source: string;
  owner: string;
  score: LeadScoreFilter;
  sort: LeadSortKey;
  quick: LeadQuickFilter;
};

export const EMPTY_LEADS_FILTERS: LeadsDsFilters = {
  search: '',
  status: '',
  source: '',
  owner: '',
  score: '',
  sort: 'activity_desc',
  quick: 'all',
};

export const LEADS_KPI_ICONS: Record<LeadsKpiKey, IhIconName> = {
  total: 'users',
  active: 'activity',
  hot: 'target',
  potentialValue: 'barChart',
  converted: 'check',
};

export const LEAD_QUICK_FILTERS: LeadQuickFilter[] = [
  'all',
  'new',
  'active',
  'hot',
  'qualified',
  'follow_up',
  'converted',
  'archived',
];

export const LEAD_STATUS_ORDER: LeadStatus[] = [...LEAD_STATUSES];
export const LEAD_SOURCE_ORDER: LeadSource[] = [...LEAD_SOURCES];

/** Active pipeline statuses (non-terminal, non-new). */
export const ACTIVE_LEAD_STATUSES: ReadonlySet<LeadStatus> = new Set([
  'Contacted',
  'Qualified',
  'Meeting Scheduled',
  'Proposal Sent',
  'Negotiation',
]);

/** Follow-up waiting: contacted or meeting scheduled. */
export const FOLLOW_UP_STATUSES: ReadonlySet<LeadStatus> = new Set([
  'Contacted',
  'Meeting Scheduled',
]);

export const HOT_SCORE_THRESHOLD = 70;

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase();
}

export function avatarTone(seed: string): LeadAvatarTone {
  const tones: LeadAvatarTone[] = ['navy', 'cyan', 'green', 'amber', 'violet', 'rose'];
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash + seed.charCodeAt(i) * (i + 1)) % tones.length;
  }
  return tones[hash] ?? 'navy';
}

export function leadStatusTone(status: LeadStatus | string): StatusTone {
  switch (status) {
    case 'Won':
      return 'success';
    case 'Qualified':
    case 'Negotiation':
      return 'info';
    case 'New':
    case 'Meeting Scheduled':
      return 'warning';
    case 'Lost':
      return 'danger';
    case 'Contacted':
    case 'Proposal Sent':
    default:
      return 'default';
  }
}

export function scoreBand(score: number | null): ScoreBand {
  if (score == null) return 'red';
  if (score >= 75) return 'green';
  if (score >= 55) return 'yellow';
  if (score >= 35) return 'orange';
  return 'red';
}

export function isArchived(lead: Lead): boolean {
  return Boolean(lead.archived_at);
}

export function isHot(lead: Lead): boolean {
  return (lead.cached_lead_score ?? 0) >= HOT_SCORE_THRESHOLD;
}

export function isActiveLead(lead: Lead): boolean {
  return !isArchived(lead) && ACTIVE_LEAD_STATUSES.has(lead.status);
}

export function isConverted(lead: Lead): boolean {
  return lead.status === 'Won';
}

function matchesQuick(lead: Lead, quick: LeadQuickFilter): boolean {
  if (quick === 'all') return !isArchived(lead);
  if (quick === 'archived') return isArchived(lead);
  if (isArchived(lead)) return false;

  switch (quick) {
    case 'new':
      return lead.status === 'New';
    case 'active':
      return isActiveLead(lead);
    case 'hot':
      return isHot(lead);
    case 'qualified':
      return lead.status === 'Qualified';
    case 'follow_up':
      return FOLLOW_UP_STATUSES.has(lead.status);
    case 'converted':
      return isConverted(lead);
    default:
      return true;
  }
}

function matchesScore(lead: Lead, score: LeadScoreFilter): boolean {
  if (!score) return true;
  const value = lead.cached_lead_score;
  if (value == null) return score === 'low';
  if (score === 'high') return value >= HOT_SCORE_THRESHOLD;
  if (score === 'medium') return value >= 40 && value < HOT_SCORE_THRESHOLD;
  return value < 40;
}

export function filterLeads(rows: Lead[], filters: LeadsDsFilters): Lead[] {
  const q = filters.search.trim().toLowerCase();
  let next = rows.filter((lead) => {
    if (!matchesQuick(lead, filters.quick)) return false;
    if (filters.status && lead.status !== filters.status) return false;
    if (filters.source && (lead.source ?? '') !== filters.source) return false;
    if (filters.owner && (lead.assigned_to ?? '') !== filters.owner) return false;
    if (!matchesScore(lead, filters.score)) return false;
    if (!q) return true;
    const hay = [
      lead.full_name,
      lead.company,
      lead.email,
      lead.phone,
      lead.assigned_to,
      lead.country,
      lead.source,
      lead.preferred_market,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(q);
  });

  next = [...next].sort((a, b) => {
    switch (filters.sort) {
      case 'name_asc':
        return a.full_name.localeCompare(b.full_name);
      case 'name_desc':
        return b.full_name.localeCompare(a.full_name);
      case 'score_desc':
        return (b.cached_lead_score ?? -1) - (a.cached_lead_score ?? -1);
      case 'created_desc':
        return b.created_at.localeCompare(a.created_at);
      case 'budget_desc':
        return (Number(b.estimated_budget) || 0) - (Number(a.estimated_budget) || 0);
      case 'activity_desc':
      default:
        return b.updated_at.localeCompare(a.updated_at);
    }
  });

  return next;
}

export type LeadsKpi = {
  key: LeadsKpiKey;
  value: string;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
};

export function deriveLeadsKpis(
  rows: Lead[],
  formatMoney: (value: number) => string,
): LeadsKpi[] {
  const live = rows.filter((r) => !isArchived(r));
  const active = live.filter((r) => isActiveLead(r));
  const hot = live.filter((r) => isHot(r));
  const converted = live.filter((r) => isConverted(r));
  const potential = live.reduce((sum, r) => sum + (Number(r.estimated_budget) || 0), 0);

  return [
    {
      key: 'total',
      value: String(live.length),
      delta: '+8%',
      deltaTone: 'up',
    },
    {
      key: 'active',
      value: String(active.length),
      delta: '+5%',
      deltaTone: 'up',
    },
    {
      key: 'hot',
      value: String(hot.length),
      delta: '+3%',
      deltaTone: 'up',
    },
    {
      key: 'potentialValue',
      value: formatMoney(potential),
      delta: '+6%',
      deltaTone: 'up',
    },
    {
      key: 'converted',
      value: String(converted.length),
      delta: '+2%',
      deltaTone: 'neutral',
    },
  ];
}

export function formatDisplayDate(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-GB';
  try {
    return new Intl.DateTimeFormat(intlLocale, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatRelativeActivity(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-GB';
  try {
    const date = new Date(value);
    const now = new Date();
    const sameDay =
      date.getFullYear() === now.getFullYear() &&
      date.getMonth() === now.getMonth() &&
      date.getDate() === now.getDate();
    if (sameDay) {
      return new Intl.DateTimeFormat(intlLocale, {
        hour: '2-digit',
        minute: '2-digit',
      }).format(date);
    }
    return new Intl.DateTimeFormat(intlLocale, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  } catch {
    return value;
  }
}

/** Demo fallback used only when API is empty or unreachable (same contract as legacy G2). */
export const DEMO_LEADS: Lead[] = [
  {
    id: 'demo-lead-1',
    full_name: 'Ayşe Demir',
    email: 'ayse@example.com',
    phone: '+90 532 000 0001',
    country: 'TR',
    source: 'Website',
    status: 'Qualified',
    assigned_to: 'Sales A',
    assigned_manager_id: null,
    company: 'Demir Holding',
    preferred_market: 'Istanbul',
    cached_lead_score: 82,
    estimated_budget: '450000',
    interested_project: 'Marina Residences',
    notes: 'Demo kayıt — API yoksa gösterilir.',
    is_demo: true,
    archived_at: null,
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-07-18T14:00:00Z',
  },
  {
    id: 'demo-lead-2',
    full_name: 'James Carter',
    email: 'james@example.com',
    phone: null,
    country: 'GB',
    source: 'Referral',
    status: 'Meeting Scheduled',
    assigned_to: 'Sales B',
    assigned_manager_id: null,
    company: 'Carter Capital',
    preferred_market: 'London',
    cached_lead_score: 74,
    estimated_budget: '1200000',
    interested_project: 'Skyline Tower',
    notes: null,
    is_demo: true,
    archived_at: null,
    created_at: '2026-06-12T09:00:00Z',
    updated_at: '2026-07-19T11:00:00Z',
  },
  {
    id: 'demo-lead-3',
    full_name: 'Fatima Al-Hassan',
    email: 'fatima@example.com',
    phone: '+971 50 000 0003',
    country: 'AE',
    source: 'Exhibition',
    status: 'New',
    assigned_to: 'Sales A',
    assigned_manager_id: null,
    company: 'Gulf Property Group',
    preferred_market: 'Dubai',
    cached_lead_score: 61,
    estimated_budget: '890000',
    interested_project: null,
    notes: null,
    is_demo: true,
    archived_at: null,
    created_at: '2026-07-01T08:00:00Z',
    updated_at: '2026-07-15T16:00:00Z',
  },
  {
    id: 'demo-lead-4',
    full_name: 'Robert Hayes',
    email: 'robert@hayesinvest.com',
    phone: '+1 415 555 0144',
    country: 'US',
    source: 'LinkedIn',
    status: 'Negotiation',
    assigned_to: 'Sales A',
    assigned_manager_id: null,
    company: 'Hayes Invest',
    preferred_market: 'Istanbul',
    cached_lead_score: 91,
    estimated_budget: '2100000',
    interested_project: 'Bosphorus Residences',
    notes: 'Yüksek ilgi — sunum sonrası teklif bekleniyor.',
    is_demo: true,
    archived_at: null,
    created_at: '2026-05-20T09:00:00Z',
    updated_at: '2026-07-26T10:30:00Z',
  },
  {
    id: 'demo-lead-5',
    full_name: 'Elena Rossi',
    email: 'elena@rossicapital.it',
    phone: '+39 02 555 0199',
    country: 'IT',
    source: 'Partner',
    status: 'Contacted',
    assigned_to: 'Sales B',
    assigned_manager_id: null,
    company: 'Rossi Capital',
    preferred_market: 'Antalya',
    cached_lead_score: 48,
    estimated_budget: '320000',
    interested_project: null,
    notes: null,
    is_demo: true,
    archived_at: null,
    created_at: '2026-07-10T12:00:00Z',
    updated_at: '2026-07-20T09:15:00Z',
  },
  {
    id: 'demo-lead-6',
    full_name: 'Omar Khalid',
    email: 'omar@khalidgroup.sa',
    phone: '+966 50 555 0112',
    country: 'SA',
    source: 'Website',
    status: 'Won',
    assigned_to: 'Sales A',
    assigned_manager_id: null,
    company: 'Khalid Group',
    preferred_market: 'Dubai',
    cached_lead_score: 88,
    estimated_budget: '1750000',
    interested_project: 'Palm Villas',
    notes: 'Dönüşüm tamamlandı.',
    is_demo: true,
    archived_at: null,
    created_at: '2026-04-02T08:00:00Z',
    updated_at: '2026-07-12T16:40:00Z',
  },
  {
    id: 'demo-lead-7',
    full_name: 'Nora Bergman',
    email: 'nora@bergman.se',
    phone: null,
    country: 'SE',
    source: 'Cold Outreach',
    status: 'Lost',
    assigned_to: 'Sales B',
    assigned_manager_id: null,
    company: 'Bergman Family Office',
    preferred_market: 'London',
    cached_lead_score: 22,
    estimated_budget: '500000',
    interested_project: null,
    notes: 'Bütçe uyumsuzluğu.',
    is_demo: true,
    archived_at: null,
    created_at: '2026-03-15T11:00:00Z',
    updated_at: '2026-06-01T10:00:00Z',
  },
  {
    id: 'demo-lead-8',
    full_name: 'Can Yılmaz',
    email: 'can@yilmazholding.com',
    phone: '+90 533 000 0088',
    country: 'TR',
    source: 'Referral',
    status: 'Proposal Sent',
    assigned_to: 'Sales A',
    assigned_manager_id: null,
    company: 'Yılmaz Holding',
    preferred_market: 'Istanbul',
    cached_lead_score: 69,
    estimated_budget: '980000',
    interested_project: 'City Port',
    notes: null,
    is_demo: true,
    archived_at: null,
    created_at: '2026-06-28T14:00:00Z',
    updated_at: '2026-07-24T13:20:00Z',
  },
];
