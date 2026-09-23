import type { IhIconName } from '@/components/icons/ih-icons';

export type ReportsKpiKey =
  | 'totalRevenue'
  | 'newOpportunities'
  | 'wonDeals'
  | 'activeCustomers'
  | 'meetings';

export type ReportsFunnelStageKey =
  | 'new'
  | 'review'
  | 'proposal'
  | 'negotiation'
  | 'won';

export type ReportsSourceKey =
  | 'referral'
  | 'event'
  | 'website'
  | 'email'
  | 'social'
  | 'other';

export type ReportsQuickReportKey =
  | 'salesPerformance'
  | 'pipeline'
  | 'customerAnalysis'
  | 'activityAnalysis'
  | 'wonOpportunities';

export type ReportsPerformanceMetricKey =
  | 'totalRevenue'
  | 'newOpportunities'
  | 'wonDeals'
  | 'avgDealSize'
  | 'winRate';

export type ReportsGoalKey =
  | 'revenue'
  | 'newOpportunities'
  | 'wonDeals'
  | 'meetings'
  | 'activeCustomers';

export type ReportsAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';

export type ReportsKpi = {
  key: ReportsKpiKey;
  value: string;
  delta: string;
  deltaTone: 'up' | 'down' | 'neutral';
  sparkValues: number[];
  sparkColor: string;
};

export type ReportsTrendPoint = {
  label: string;
  current: number;
  previous: number;
};

export type ReportsFunnelStage = {
  key: ReportsFunnelStageKey;
  valueLabel: string;
  count: number;
  widthPct: number;
};

export type ReportsPerformanceMetric = {
  key: ReportsPerformanceMetricKey;
  value: string;
  delta: string;
  deltaTone: 'up' | 'down' | 'neutral';
};

export type ReportsTeamMember = {
  id: string;
  name: string;
  initials: string;
  tone: ReportsAvatarTone;
  revenue: string;
  opportunities: number;
  won: number;
  sparkValues: number[];
  trendTone: 'up' | 'down' | 'neutral';
};

export type ReportsMonthlyPoint = {
  label: string;
  current: number;
  previous: number;
};

export type ReportsGoal = {
  key: ReportsGoalKey;
  target: string;
  actual: string;
  pct: number;
  tone: 'success' | 'warning' | 'danger';
};

export type ReportsSourceSlice = {
  key: ReportsSourceKey;
  pct: number;
};

export type ReportsQuickReport = {
  key: ReportsQuickReportKey;
  icon: IhIconName;
};

export type ReportsAiInsight = {
  id: string;
  textKey: string;
};

export type ReportsWorkspacePreview = {
  filters: {
    dateRange: string;
    comparison: string;
    teams: string[];
    users: string[];
    sources: string[];
  };
  kpis: ReportsKpi[];
  revenueTrend: ReportsTrendPoint[];
  funnel: ReportsFunnelStage[];
  performanceSummary: ReportsPerformanceMetric[];
  team: ReportsTeamMember[];
  monthlyComparison: ReportsMonthlyPoint[];
  goals: ReportsGoal[];
  sources: ReportsSourceSlice[];
  quickReports: ReportsQuickReport[];
  aiInsights: ReportsAiInsight[];
};

export const REPORTS_KPI_ICONS: Record<ReportsKpiKey, IhIconName> = {
  totalRevenue: 'trendingUp',
  newOpportunities: 'target',
  wonDeals: 'check',
  activeCustomers: 'users',
  meetings: 'meeting',
};

export const REPORTS_SOURCE_COLORS: Record<ReportsSourceKey, string> = {
  referral: '#075b75',
  event: '#58aebb',
  website: '#2f6fed',
  email: '#7b5ea7',
  social: '#c77938',
  other: '#9aa7af',
};

export const REPORTS_FUNNEL_COLORS: Record<ReportsFunnelStageKey, string> = {
  new: '#0b6b86',
  review: '#1a7f97',
  proposal: '#2f93a8',
  negotiation: '#4aa7b8',
  won: '#6bb8c6',
};

export const REPORTS_KPI_ICON_TONES: Record<ReportsKpiKey, string> = {
  totalRevenue: 'green',
  newOpportunities: 'violet',
  wonDeals: 'blue',
  activeCustomers: 'amber',
  meetings: 'rose',
};
