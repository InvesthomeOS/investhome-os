export const INVESTMENT_STATUSES = [
  'active',
  'under_construction',
  'stabilized',
  'exited',
  'upcoming',
] as const;

export type InvestmentStatus = (typeof INVESTMENT_STATUSES)[number];

export const INVESTMENT_TYPES = [
  'development',
  'rental',
  'flip',
  'condominium',
  'multifamily',
  'commercial',
] as const;

export type InvestmentType = (typeof INVESTMENT_TYPES)[number];

export const PROJECT_STAGES = [
  'acquisition',
  'pre_construction',
  'construction',
  'lease_up',
  'stabilized',
  'exit',
] as const;

export type ProjectStage = (typeof PROJECT_STAGES)[number];

export const RISK_LEVELS = ['low', 'moderate', 'high'] as const;

export type RiskLevel = (typeof RISK_LEVELS)[number];

export interface InvestmentPerformance {
  roi: number;
  irr: number;
  annualCashFlow: number;
  projectedRoi: number;
}

export interface InvestmentDistributionSummary {
  nextDistributionDate?: string;
  lastDistributionDate?: string;
  totalDistributed: number;
}

export interface PortfolioInvestment {
  id: string;
  slug: string;
  imageUrl: string;
  projectName: string;
  address: string;
  city: string;
  state: string;
  entityName: string;
  type: InvestmentType;
  status: InvestmentStatus;
  stage: ProjectStage;
  investmentDate: string;
  investedAmount: number;
  currentValue: number;
  ownershipPercent: number;
  performance: InvestmentPerformance;
  distribution: InvestmentDistributionSummary;
  exitDate?: string;
  riskLevel: RiskLevel;
  progressPercent: number;
  currency: string;
}

export type InvestmentSortField =
  | 'projectName'
  | 'investmentDate'
  | 'investedAmount'
  | 'currentValue'
  | 'roi'
  | 'irr'
  | 'status'
  | 'progressPercent'
  | 'city';

export type SortDirection = 'asc' | 'desc';

export type InvestmentViewMode = 'grid' | 'table';

export interface InvestmentFilterState {
  search: string;
  status: InvestmentStatus | 'all';
  type: InvestmentType | 'all';
  location: string;
  stage: ProjectStage | 'all';
  investmentDateFrom: string;
  investmentDateTo: string;
  sortField: InvestmentSortField;
  sortDirection: SortDirection;
  viewMode: InvestmentViewMode;
}

export interface InvestmentSummaryMetrics {
  totalInvestments: number;
  totalInvested: number;
  currentPortfolioValue: number;
  estimatedEquity: number;
  activeInvestments: number;
  completedInvestments: number;
  averageProjectedRoi: number;
  averageIrr: number;
  currency: string;
}
