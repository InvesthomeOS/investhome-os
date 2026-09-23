import type { IhIconName } from '@/components/icons/ih-icons';

export type ContactsViewMode = 'table' | 'cards';

export type ContactRoleKey =
  | 'investor'
  | 'broker'
  | 'developer'
  | 'partner'
  | 'vendor'
  | 'other';

export type ContactStatusKey =
  | 'lead'
  | 'qualified'
  | 'investor'
  | 'negotiating'
  | 'client'
  | 'inactive'
  | 'lost';

export type ContactPriorityKey = 'low' | 'medium' | 'high' | 'urgent';

export type ContactSourceKey =
  | 'referral'
  | 'event'
  | 'website'
  | 'linkedin'
  | 'cold_outreach'
  | 'partner';

export type ContactQuickFilter =
  | 'all'
  | 'investors'
  | 'brokers'
  | 'developers'
  | 'partners'
  | 'vendors'
  | 'archived';

export type ContactSortKey =
  | 'name_asc'
  | 'name_desc'
  | 'activity_desc'
  | 'followup_asc'
  | 'score_desc'
  | 'priority_desc';

export type ContactAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';

export type StatusTone = 'success' | 'warning' | 'info' | 'default' | 'danger';

export type AiScoreBand = 'green' | 'yellow' | 'orange' | 'red';

export type ContactsKpiKey = 'total' | 'activeInvestors' | 'brokers' | 'followUpsToday';

export type ContactRow = {
  id: string;
  fullName: string;
  initials: string;
  avatarTone: ContactAvatarTone;
  company: string;
  role: ContactRoleKey;
  status: ContactStatusKey;
  source: ContactSourceKey;
  lastActivity: string;
  nextFollowUp: string | null;
  owner: string;
  priority: ContactPriorityKey;
  aiScore: number;
  archived: boolean;
  email?: string;
  phone?: string;
};

export type ContactsDsFilters = {
  search: string;
  role: ContactRoleKey | '';
  status: ContactStatusKey | '';
  owner: string;
  sort: ContactSortKey;
  quick: ContactQuickFilter;
};

export const EMPTY_CONTACTS_FILTERS: ContactsDsFilters = {
  search: '',
  role: '',
  status: '',
  owner: '',
  sort: 'activity_desc',
  quick: 'all',
};

export const CONTACTS_KPI_ICONS: Record<ContactsKpiKey, IhIconName> = {
  total: 'users',
  activeInvestors: 'investors',
  brokers: 'crm',
  followUpsToday: 'calendar',
};

export const CONTACT_ROLE_ORDER: ContactRoleKey[] = [
  'investor',
  'broker',
  'developer',
  'partner',
  'vendor',
  'other',
];

export const CONTACT_STATUS_ORDER: ContactStatusKey[] = [
  'lead',
  'qualified',
  'investor',
  'negotiating',
  'client',
  'inactive',
  'lost',
];

export const CONTACT_PRIORITY_ORDER: ContactPriorityKey[] = [
  'low',
  'medium',
  'high',
  'urgent',
];

export const CONTACT_QUICK_FILTERS: ContactQuickFilter[] = [
  'all',
  'investors',
  'brokers',
  'developers',
  'partners',
  'vendors',
  'archived',
];

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase();
}

export function statusTone(status: ContactStatusKey): StatusTone {
  switch (status) {
    case 'client':
    case 'investor':
      return 'success';
    case 'qualified':
    case 'negotiating':
      return 'info';
    case 'lead':
      return 'warning';
    case 'inactive':
      return 'default';
    case 'lost':
      return 'danger';
    default:
      return 'default';
  }
}

export function aiScoreBand(score: number): AiScoreBand {
  if (score >= 75) return 'green';
  if (score >= 55) return 'yellow';
  if (score >= 35) return 'orange';
  return 'red';
}

export function priorityRank(priority: ContactPriorityKey): number {
  switch (priority) {
    case 'urgent':
      return 4;
    case 'high':
      return 3;
    case 'medium':
      return 2;
    case 'low':
    default:
      return 1;
  }
}

function matchesQuick(row: ContactRow, quick: ContactQuickFilter): boolean {
  if (quick === 'all') return !row.archived;
  if (quick === 'archived') return row.archived;
  if (row.archived) return false;
  switch (quick) {
    case 'investors':
      return row.role === 'investor';
    case 'brokers':
      return row.role === 'broker';
    case 'developers':
      return row.role === 'developer';
    case 'partners':
      return row.role === 'partner';
    case 'vendors':
      return row.role === 'vendor';
    default:
      return true;
  }
}

export function filterContacts(rows: ContactRow[], filters: ContactsDsFilters): ContactRow[] {
  const q = filters.search.trim().toLowerCase();
  let next = rows.filter((row) => {
    if (!matchesQuick(row, filters.quick)) return false;
    if (filters.role && row.role !== filters.role) return false;
    if (filters.status && row.status !== filters.status) return false;
    if (filters.owner && row.owner !== filters.owner) return false;
    if (!q) return true;
    const hay = [row.fullName, row.company, row.owner, row.email, row.phone]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(q);
  });

  next = [...next].sort((a, b) => {
    switch (filters.sort) {
      case 'name_asc':
        return a.fullName.localeCompare(b.fullName);
      case 'name_desc':
        return b.fullName.localeCompare(a.fullName);
      case 'followup_asc': {
        const aDate = a.nextFollowUp ?? '9999-99-99';
        const bDate = b.nextFollowUp ?? '9999-99-99';
        return aDate.localeCompare(bDate);
      }
      case 'score_desc':
        return b.aiScore - a.aiScore;
      case 'priority_desc':
        return priorityRank(b.priority) - priorityRank(a.priority);
      case 'activity_desc':
      default:
        return b.lastActivity.localeCompare(a.lastActivity);
    }
  });

  return next;
}

export type ContactsKpi = {
  key: ContactsKpiKey;
  value: string;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
};

export function deriveContactsKpis(rows: ContactRow[]): ContactsKpi[] {
  const active = rows.filter((r) => !r.archived);
  const today = '2026-07-27';
  const followUpsToday = active.filter((r) => r.nextFollowUp === today).length;

  return [
    {
      key: 'total',
      value: String(active.length),
      delta: '+18',
      deltaTone: 'up',
    },
    {
      key: 'activeInvestors',
      value: String(active.filter((r) => r.role === 'investor').length),
      delta: '+6',
      deltaTone: 'up',
    },
    {
      key: 'brokers',
      value: String(active.filter((r) => r.role === 'broker').length),
      delta: '+3',
      deltaTone: 'up',
    },
    {
      key: 'followUpsToday',
      value: String(followUpsToday),
      delta: '+2',
      deltaTone: 'neutral',
    },
  ];
}

/** High-quality presentation fixtures for CRM Contacts DS review. */
export function makeContactsFixture(): ContactRow[] {
  return [
    {
      id: 'c-james',
      fullName: 'James Temple',
      initials: 'JT',
      avatarTone: 'navy',
      company: 'The Temple Group',
      role: 'investor',
      status: 'investor',
      source: 'referral',
      lastActivity: '2026-07-22',
      nextFollowUp: '2026-07-27',
      owner: 'Emin Bilgin',
      priority: 'urgent',
      aiScore: 94,
      archived: false,
      email: 'james@temple.group',
      phone: '+1 415 555 0142',
    },
    {
      id: 'c-sara',
      fullName: 'Sara Al-Hassan',
      initials: 'SA',
      avatarTone: 'cyan',
      company: 'Marina Heights LLC',
      role: 'investor',
      status: 'negotiating',
      source: 'event',
      lastActivity: '2026-07-21',
      nextFollowUp: '2026-07-28',
      owner: 'Ayşe Demir',
      priority: 'high',
      aiScore: 86,
      archived: false,
      email: 'sara@marinaheights.ae',
      phone: '+971 50 555 0198',
    },
    {
      id: 'c-oliver',
      fullName: 'Oliver Grant',
      initials: 'OG',
      avatarTone: 'amber',
      company: 'Grant Capital Partners',
      role: 'broker',
      status: 'qualified',
      source: 'linkedin',
      lastActivity: '2026-07-20',
      nextFollowUp: '2026-07-27',
      owner: 'Can Özkan',
      priority: 'high',
      aiScore: 78,
      archived: false,
      email: 'oliver@grantcapital.co.uk',
      phone: '+44 20 7946 0958',
    },
    {
      id: 'c-mia',
      fullName: 'Mia Chen',
      initials: 'MC',
      avatarTone: 'rose',
      company: 'Bayview Developers',
      role: 'developer',
      status: 'client',
      source: 'partner',
      lastActivity: '2026-07-19',
      nextFollowUp: '2026-07-30',
      owner: 'Mehmet Kaya',
      priority: 'medium',
      aiScore: 72,
      archived: false,
      email: 'mia@bayview.dev',
      phone: '+1 628 555 0114',
    },
    {
      id: 'c-elena',
      fullName: 'Elena Brooks',
      initials: 'EB',
      avatarTone: 'violet',
      company: 'Horizon Realty Group',
      role: 'broker',
      status: 'lead',
      source: 'website',
      lastActivity: '2026-07-18',
      nextFollowUp: '2026-07-29',
      owner: 'Ayşe Demir',
      priority: 'medium',
      aiScore: 61,
      archived: false,
      email: 'elena@horizonrealty.com',
      phone: '+1 310 555 0177',
    },
    {
      id: 'c-ahmed',
      fullName: 'Ahmed Rahman',
      initials: 'AR',
      avatarTone: 'green',
      company: 'Gulf Partnership Advisors',
      role: 'partner',
      status: 'qualified',
      source: 'referral',
      lastActivity: '2026-07-17',
      nextFollowUp: '2026-08-02',
      owner: 'Emin Bilgin',
      priority: 'high',
      aiScore: 81,
      archived: false,
      email: 'ahmed@gulfpa.ae',
      phone: '+971 55 555 0231',
    },
    {
      id: 'c-lisa',
      fullName: 'Lisa Nakamura',
      initials: 'LN',
      avatarTone: 'cyan',
      company: 'Pacific Title Services',
      role: 'vendor',
      status: 'client',
      source: 'partner',
      lastActivity: '2026-07-16',
      nextFollowUp: null,
      owner: 'Can Özkan',
      priority: 'low',
      aiScore: 58,
      archived: false,
      email: 'lisa@pacifictitle.com',
      phone: '+1 415 555 0290',
    },
    {
      id: 'c-daniel',
      fullName: 'Daniel Kovacs',
      initials: 'DK',
      avatarTone: 'navy',
      company: 'Central Park Investors',
      role: 'investor',
      status: 'lead',
      source: 'cold_outreach',
      lastActivity: '2026-07-15',
      nextFollowUp: '2026-07-31',
      owner: 'Mehmet Kaya',
      priority: 'medium',
      aiScore: 49,
      archived: false,
      email: 'daniel@cpinvestors.com',
      phone: '+1 212 555 0344',
    },
    {
      id: 'c-fatima',
      fullName: 'Fatima Yılmaz',
      initials: 'FY',
      avatarTone: 'amber',
      company: 'Ankara Development Co.',
      role: 'developer',
      status: 'negotiating',
      source: 'event',
      lastActivity: '2026-07-14',
      nextFollowUp: '2026-07-27',
      owner: 'Ayşe Demir',
      priority: 'urgent',
      aiScore: 88,
      archived: false,
      email: 'fatima@ankara-dev.com.tr',
      phone: '+90 532 555 0188',
    },
    {
      id: 'c-robert',
      fullName: 'Robert Hale',
      initials: 'RH',
      avatarTone: 'violet',
      company: 'Hale & Partners Law',
      role: 'partner',
      status: 'inactive',
      source: 'referral',
      lastActivity: '2026-06-02',
      nextFollowUp: null,
      owner: 'Emin Bilgin',
      priority: 'low',
      aiScore: 34,
      archived: false,
      email: 'robert@halepartners.com',
      phone: '+1 617 555 0412',
    },
    {
      id: 'c-sophia',
      fullName: 'Sophia Martins',
      initials: 'SM',
      avatarTone: 'rose',
      company: 'Atlantic Brokerage',
      role: 'broker',
      status: 'lost',
      source: 'website',
      lastActivity: '2026-05-11',
      nextFollowUp: null,
      owner: 'Can Özkan',
      priority: 'low',
      aiScore: 22,
      archived: false,
      email: 'sophia@atlanticbrokerage.com',
      phone: '+1 305 555 0520',
    },
    {
      id: 'c-kenji',
      fullName: 'Kenji Watanabe',
      initials: 'KW',
      avatarTone: 'green',
      company: 'Tokyo Asset Bridge',
      role: 'investor',
      status: 'investor',
      source: 'linkedin',
      lastActivity: '2026-07-12',
      nextFollowUp: '2026-08-05',
      owner: 'Mehmet Kaya',
      priority: 'high',
      aiScore: 91,
      archived: false,
      email: 'kenji@tokyoasset.jp',
      phone: '+81 3 5555 0670',
    },
    {
      id: 'c-archived-1',
      fullName: 'Marcus Webb',
      initials: 'MW',
      avatarTone: 'navy',
      company: 'Webb Holdings',
      role: 'investor',
      status: 'inactive',
      source: 'referral',
      lastActivity: '2025-11-04',
      nextFollowUp: null,
      owner: 'Emin Bilgin',
      priority: 'low',
      aiScore: 18,
      archived: true,
      email: 'marcus@webbholdings.com',
    },
    {
      id: 'c-priya',
      fullName: 'Priya Sharma',
      initials: 'PS',
      avatarTone: 'cyan',
      company: 'Lotus Vendor Solutions',
      role: 'vendor',
      status: 'qualified',
      source: 'partner',
      lastActivity: '2026-07-10',
      nextFollowUp: '2026-08-01',
      owner: 'Ayşe Demir',
      priority: 'medium',
      aiScore: 66,
      archived: false,
      email: 'priya@lotusvendor.com',
      phone: '+971 54 555 0781',
    },
  ];
}

export function formatDisplayDate(iso: string | null, locale: string): string {
  if (!iso) return '—';
  const date = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-US', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}
