import type { IhIconName } from '@/components/icons/ih-icons';

export type CompanyAiActionKey =
  | 'newCompany'
  | 'aiAnalysis'
  | 'similar'
  | 'missingInfo';

export type CompanyKpiKey =
  | 'total'
  | 'activePartners'
  | 'investors'
  | 'newThisMonth'
  | 'openCollaborations';

export type CompanyCategoryKey =
  | 'investor'
  | 'developer'
  | 'architecture'
  | 'legal'
  | 'title'
  | 'broker'
  | 'bank'
  | 'partner';

export type CompanyStatusKey = 'active' | 'prospect' | 'inactive' | 'archived';

export type CompanyRelationKey =
  | 'strategicPartner'
  | 'vendor'
  | 'client'
  | 'investor'
  | 'advisor';

export type CompanyHealthKey = 'excellent' | 'good' | 'medium' | 'attention' | 'risk';

export type CompanyCountryKey = 'us' | 'ae' | 'uk' | 'tr' | 'de' | 'sg';

export type CompanyRow = {
  id: string;
  name: string;
  subtitleKey: string;
  subtitle?: string;
  initials: string;
  logoTone: 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';
  category: CompanyCategoryKey;
  country: CompanyCountryKey;
  contactName: string;
  contactRoleKey: string;
  contactDetail?: string;
  contactInitials: string;
  openProjects: number;
  lastActivityKey: string;
  lastActivityLabel?: string;
  lastActivityDate: string;
  healthScore: number;
  health: CompanyHealthKey;
  aiSummaryKey: string;
  aiSummary?: string;
  status: CompanyStatusKey;
  relation: CompanyRelationKey;
  owner: string;
  tags: string[];
};

export type CompanyKpi = {
  key: CompanyKpiKey;
  value: number;
  hintKey: string;
  delta: string;
  deltaTone: 'up' | 'down' | 'neutral';
};

export type CompanyRecentItem = {
  id: string;
  name: string;
  initials: string;
  logoTone: CompanyRow['logoTone'];
  addedAtKey: string;
};

export type CompanyMeetingItem = {
  id: string;
  company: string;
  typeKey: string;
  whenKey: string;
};

export type CompanyRecommendation = {
  id: string;
  bodyKey: string;
};

export type CompanyCategorySlice = {
  key: CompanyCategoryKey | 'other';
  pct: number;
};

export type CompanyActivePartner = {
  id: string;
  name: string;
  initials: string;
  logoTone: CompanyRow['logoTone'];
  activityCount: number;
  lastContactKey: string;
};

export type CompanyWorkspacePreview = {
  totalCompanies: number;
  totalPages: number;
  kpis: CompanyKpi[];
  companies: CompanyRow[];
  recentCompanies: CompanyRecentItem[];
  upcomingMeetings: CompanyMeetingItem[];
  recommendations: CompanyRecommendation[];
  categoryDistribution: CompanyCategorySlice[];
  activePartners: CompanyActivePartner[];
  owners: string[];
  tags: string[];
  countries: CompanyCountryKey[];
};

export const COMPANY_CATEGORY_ORDER: CompanyCategoryKey[] = [
  'investor',
  'developer',
  'architecture',
  'legal',
  'title',
  'broker',
  'bank',
  'partner',
];

export const COMPANY_STATUS_ORDER: CompanyStatusKey[] = [
  'active',
  'prospect',
  'inactive',
  'archived',
];

export const COMPANY_RELATION_ORDER: CompanyRelationKey[] = [
  'strategicPartner',
  'vendor',
  'client',
  'investor',
  'advisor',
];

export const COMPANY_KPI_ICONS: Record<CompanyKpiKey, IhIconName> = {
  total: 'investors',
  activePartners: 'users',
  investors: 'trendingUp',
  newThisMonth: 'plus',
  openCollaborations: 'activity',
};

export const COMPANY_AI_ACTIONS: ReadonlyArray<{
  key: CompanyAiActionKey;
  icon: IhIconName;
  featured?: boolean;
}> = [
  { key: 'newCompany', icon: 'plus', featured: true },
  { key: 'aiAnalysis', icon: 'sparkles' },
  { key: 'similar', icon: 'search' },
  { key: 'missingInfo', icon: 'alert' },
];

export const COMPANY_COUNTRY_FLAG: Record<CompanyCountryKey, string> = {
  us: '🇺🇸',
  ae: '🇦🇪',
  uk: '🇬🇧',
  tr: '🇹🇷',
  de: '🇩🇪',
  sg: '🇸🇬',
};

export const COMPANY_HEALTH_SCORE_COLOR: Record<CompanyHealthKey, string> = {
  excellent: '#2f8a5b',
  good: '#3d9a6a',
  medium: '#d4a017',
  attention: '#c77938',
  risk: '#c45c5c',
};
