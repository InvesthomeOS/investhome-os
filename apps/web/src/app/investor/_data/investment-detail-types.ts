import type { PortfolioInvestment, RiskLevel } from './investment-types';

export const MILESTONE_STATUSES = [
  'completed',
  'in_progress',
  'upcoming',
  'delayed',
  'at_risk',
] as const;

export type MilestoneStatus = (typeof MILESTONE_STATUSES)[number];

export const UPDATE_CATEGORIES = [
  'construction',
  'financial',
  'legal',
  'market',
  'operations',
  'investor_relations',
] as const;

export type UpdateCategory = (typeof UPDATE_CATEGORIES)[number];

export const DOCUMENT_CATEGORIES = [
  'subscription',
  'tax',
  'financial',
  'legal',
  'report',
  'insurance',
] as const;

export type DocumentCategory = (typeof DOCUMENT_CATEGORIES)[number];

export const DISTRIBUTION_TYPES = [
  'cash',
  'return_of_capital',
  'preferred_return',
  'profit_share',
  'final',
] as const;

export type DistributionType = (typeof DISTRIBUTION_TYPES)[number];

export const DISTRIBUTION_STATUSES = ['paid', 'pending', 'scheduled'] as const;

export type DistributionStatus = (typeof DISTRIBUTION_STATUSES)[number];

export const RISK_SEVERITIES = ['low', 'medium', 'high', 'critical'] as const;

export type RiskSeverity = (typeof RISK_SEVERITIES)[number];

export const RISK_STATUSES = ['open', 'monitoring', 'mitigated', 'closed'] as const;

export type RiskStatus = (typeof RISK_STATUSES)[number];

export const CONTACT_ROLES = [
  'investor_relations',
  'project_manager',
  'asset_manager',
  'legal',
  'accounting',
] as const;

export type ContactRole = (typeof CONTACT_ROLES)[number];

export interface ChartDataPoint {
  label: string;
  value: number;
}

export interface InvestorPosition {
  committedCapital: number;
  calledCapital: number;
  uncalledCapital: number;
  capitalAccountBalance: number;
  ownershipUnits: number;
  totalFundUnits: number;
  preferredReturnRate: number;
  profitSplitPercent: number;
  votingRights: boolean;
  capitalCallSchedule: string;
  lastCapitalCallDate?: string;
  nextCapitalCallDate?: string;
}

export interface FinancialMetric {
  key: string;
  label: string;
  value: string;
  tooltip?: string;
}

export interface InvestmentFinancials {
  investmentGrowth: ChartDataPoint[];
  equityGrowth: ChartDataPoint[];
  cashFlowHistory: ChartDataPoint[];
  roiProgression: ChartDataPoint[];
  metrics: FinancialMetric[];
  netAssetValue: number;
  unrealizedGain: number;
  realizedGain: number;
  totalReturn: number;
  cashOnCashReturn: number;
  debtServiceCoverage: number;
  loanToValue: number;
  capRate: number;
}

export interface CapitalStructureItem {
  label: string;
  amount: number;
  percent: number;
  color: string;
}

export interface CapitalStructure {
  totalCapitalization: number;
  items: CapitalStructureItem[];
  seniorDebt: number;
  mezzanineDebt: number;
  preferredEquity: number;
  commonEquity: number;
  investorEquity: number;
}

export interface ProjectProgress {
  overallPercent: number;
  currentPhase: string;
  constructionPercent: number;
  leasingPercent: number;
  salesPercent: number;
  budgetSpent: number;
  totalBudget: number;
  budgetSpentPercent: number;
  timelineStatus: 'on_track' | 'ahead' | 'behind' | 'at_risk';
  estimatedCompletion: string;
  daysRemaining: number;
}

export interface ProjectMilestone {
  id: string;
  title: string;
  description: string;
  targetDate: string;
  completedDate?: string;
  status: MilestoneStatus;
  phase: string;
}

export interface DistributionRecord {
  id: string;
  date: string;
  type: DistributionType;
  amount: number;
  status: DistributionStatus;
  taxYear: number;
  paymentMethod: string;
  reference: string;
  notes?: string;
}

export interface InvestmentDocument {
  id: string;
  title: string;
  category: DocumentCategory;
  date: string;
  fileSize: string;
  format: string;
}

export interface InvestmentUpdate {
  id: string;
  title: string;
  summary: string;
  category: UpdateCategory;
  date: string;
  isRead: boolean;
  author: string;
}

export interface InvestmentRisk {
  id: string;
  title: string;
  description: string;
  severity: RiskSeverity;
  status: RiskStatus;
  category: string;
  mitigationPlan?: string;
  lastReviewed: string;
}

export interface ProjectContact {
  id: string;
  name: string;
  role: ContactRole;
  title: string;
  email: string;
  phone: string;
  availability: string;
}

export interface PropertySummary {
  description: string;
  neighborhood: string;
  submarket: string;
  yearBuilt?: number;
  yearRenovated?: number;
  unitCount: number;
  buildingSizeSqFt: number;
  lotSizeAcres?: number;
  parkingSpaces?: number;
  amenities: string[];
  galleryImages: { url: string; alt: string }[];
  mapCoordinates?: { lat: number; lng: number };
}

export interface InvestmentOverview {
  thesis: string;
  strategy: string;
  businessPlan: string;
  holdPeriod: string;
  assetClass: string;
  propertyType: string;
  acquisitionDate?: string;
  stabilizationDate?: string;
  keyDates: { label: string; date: string }[];
}

export interface InvestmentSummaryPanel {
  nextMilestone: string;
  nextMilestoneDate: string;
  irContactName: string;
  irContactEmail: string;
  overallRiskLevel: RiskLevel;
}

export interface InvestmentDetail {
  investment: PortfolioInvestment;
  overview: InvestmentOverview;
  position: InvestorPosition;
  financials: InvestmentFinancials;
  capitalStructure: CapitalStructure;
  progress: ProjectProgress;
  milestones: ProjectMilestone[];
  distributions: DistributionRecord[];
  documents: InvestmentDocument[];
  updates: InvestmentUpdate[];
  risks: InvestmentRisk[];
  contacts: ProjectContact[];
  property: PropertySummary;
  summaryPanel: InvestmentSummaryPanel;
}

export type InvestmentDetailTab =
  | 'overview'
  | 'financials'
  | 'progress'
  | 'distributions'
  | 'documents'
  | 'updates'
  | 'risks'
  | 'contacts';

export const INVESTMENT_DETAIL_TABS: { id: InvestmentDetailTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'financials', label: 'Financials' },
  { id: 'progress', label: 'Project Progress' },
  { id: 'distributions', label: 'Distributions' },
  { id: 'documents', label: 'Documents' },
  { id: 'updates', label: 'Updates' },
  { id: 'risks', label: 'Risks' },
  { id: 'contacts', label: 'Contacts' },
];
