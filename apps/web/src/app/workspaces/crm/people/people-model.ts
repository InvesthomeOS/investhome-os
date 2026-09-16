import type { IhIconName } from '@/components/icons/ih-icons';

export type PeopleAiActionKey =
  | 'newPerson'
  | 'aiAnalysis'
  | 'similar'
  | 'missingInfo';

export type PeopleKpiKey =
  | 'total'
  | 'active'
  | 'decisionMakers'
  | 'newThisMonth'
  | 'meetingPending';

export type PeopleRoleKey =
  | 'ceo'
  | 'decisionMaker'
  | 'broker'
  | 'partner'
  | 'architect'
  | 'lawyer'
  | 'finance'
  | 'operations'
  | 'investor'
  | 'influencer';

export type PeopleDepartmentKey =
  | 'executive'
  | 'investment'
  | 'sales'
  | 'legal'
  | 'design'
  | 'operations'
  | 'finance'
  | 'brokerage';

export type PeopleCountryKey = 'us' | 'ae' | 'uk' | 'tr' | 'de' | 'sg';

export type PeopleRelationKey =
  | 'veryStrong'
  | 'strong'
  | 'medium'
  | 'attention'
  | 'weak';

export type PeopleSourceKey =
  | 'referral'
  | 'event'
  | 'website'
  | 'email'
  | 'ads'
  | 'other';

export type PeopleAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';

export type PeopleRow = {
  id: string;
  name: string;
  titleKey: string;
  title?: string;
  initials: string;
  avatarTone: PeopleAvatarTone;
  company: string;
  companyInitials: string;
  companyTone: PeopleAvatarTone;
  role: PeopleRoleKey;
  department: PeopleDepartmentKey;
  country: PeopleCountryKey;
  hasEmail: boolean;
  hasPhone: boolean;
  hasLinkedIn: boolean;
  hasWhatsApp: boolean;
  lastActivityKey: string;
  lastActivityLabel?: string;
  lastActivityDate: string;
  relationScore: number;
  relation: PeopleRelationKey;
  aiNoteKey: string;
  aiNote?: string;
  owner: string;
  tags: string[];
};

export type PeopleKpi = {
  key: PeopleKpiKey;
  value: number;
  hintKey: string;
  delta: string;
  deltaTone: 'up' | 'down' | 'neutral';
};

export type PeopleRecentItem = {
  id: string;
  name: string;
  company: string;
  initials: string;
  avatarTone: PeopleAvatarTone;
  addedAtKey: string;
};

export type PeopleMeetingItem = {
  id: string;
  name: string;
  company: string;
  whenKey: string;
};

export type PeopleSourceSlice = {
  key: PeopleSourceKey;
  pct: number;
};

export type PeopleActiveItem = {
  id: string;
  name: string;
  initials: string;
  avatarTone: PeopleAvatarTone;
  activityCount?: number;
  lastContactKey?: string;
  lastContactLabel?: string;
};

export type PeopleWorkspacePreview = {
  totalPeople: number;
  totalPages: number;
  kpis: PeopleKpi[];
  people: PeopleRow[];
  recentPeople: PeopleRecentItem[];
  upcomingMeetings: PeopleMeetingItem[];
  sourceDistribution: PeopleSourceSlice[];
  activePeople: PeopleActiveItem[];
  owners: string[];
  tags: string[];
  companies: string[];
  countries: PeopleCountryKey[];
};

export const PEOPLE_ROLE_ORDER: PeopleRoleKey[] = [
  'ceo',
  'decisionMaker',
  'broker',
  'partner',
  'architect',
  'lawyer',
  'finance',
  'operations',
  'investor',
  'influencer',
];

export const PEOPLE_DEPARTMENT_ORDER: PeopleDepartmentKey[] = [
  'executive',
  'investment',
  'sales',
  'legal',
  'design',
  'operations',
  'finance',
  'brokerage',
];

export const PEOPLE_KPI_ICONS: Record<PeopleKpiKey, IhIconName> = {
  total: 'users',
  active: 'activity',
  decisionMakers: 'executive',
  newThisMonth: 'plus',
  meetingPending: 'calendar',
};

export const PEOPLE_AI_ACTIONS: ReadonlyArray<{
  key: PeopleAiActionKey;
  icon: IhIconName;
  featured?: boolean;
}> = [
  { key: 'newPerson', icon: 'plus', featured: true },
  { key: 'aiAnalysis', icon: 'sparkles' },
  { key: 'similar', icon: 'search' },
  { key: 'missingInfo', icon: 'alert' },
];

export const PEOPLE_COUNTRY_FLAG: Record<PeopleCountryKey, string> = {
  us: '🇺🇸',
  ae: '🇦🇪',
  uk: '🇬🇧',
  tr: '🇹🇷',
  de: '🇩🇪',
  sg: '🇸🇬',
};

export const PEOPLE_RELATION_SCORE_COLOR: Record<PeopleRelationKey, string> = {
  veryStrong: '#2f8a5b',
  strong: '#3d9a6a',
  medium: '#d4a017',
  attention: '#c77938',
  weak: '#c45c5c',
};

export const PEOPLE_SOURCE_COLOR: Record<PeopleSourceKey, string> = {
  referral: '#2f6fed',
  event: '#2f8a5b',
  website: '#58aebb',
  email: '#7b5ea7',
  ads: '#c77938',
  other: '#9aa7af',
};
