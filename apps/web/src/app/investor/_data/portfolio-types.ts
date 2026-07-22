import type {
  InvestmentStatus,
  InvestmentType,
  PortfolioInvestment,
  ProjectStage,
  RiskLevel,
} from './investment-types';

export const ALLOCATION_CATEGORIES = [
  'core',
  'core_plus',
  'value_add',
  'opportunistic',
  'development',
] as const;

export type AllocationCategory = (typeof ALLOCATION_CATEGORIES)[number];

export const PORTFOLIO_DATE_PRESETS = [
  '3M',
  '6M',
  'YTD',
  '1Y',
  '3Y',
  'inception',
  'custom',
] as const;

export type PortfolioDatePreset = (typeof PORTFOLIO_DATE_PRESETS)[number];

export interface MonthlyValuePoint {
  date: string;
  investedCapital: number;
  portfolioValue: number;
  equity: number;
}

export interface MonthlyCashFlowPoint {
  date: string;
  amount: number;
}

export interface InvestmentAnalyticsExtension {
  currentDebtBalance: number;
  assetClass: string;
  neighborhood: string;
  historicalMonthlyValues: MonthlyValuePoint[];
  historicalCashFlow: MonthlyCashFlowPoint[];
  targetReturn: number;
  currentReturn: number;
  exitProbability: number;
  riskScore: number;
  allocationCategory: AllocationCategory;
}

export interface EnrichedPortfolioInvestment extends PortfolioInvestment {
  analytics: InvestmentAnalyticsExtension;
}

export interface PortfolioDateRange {
  preset: PortfolioDatePreset;
  startDate?: string;
  endDate?: string;
}

export interface PortfolioFilterState {
  status: InvestmentStatus | 'all';
  assetClass: string | 'all';
  type: InvestmentType | 'all';
  location: string | 'all';
  stage: ProjectStage | 'all';
  riskLevel: RiskLevel | 'all';
}

export interface PortfolioSummary {
  totalInvested: number;
  currentValue: number;
  equity: number;
  outstandingDebt: number;
  annualNetCashFlow: number;
  portfolioRoi: number;
  portfolioIrr: number;
  equityMultiple: number;
  currency: string;
  investmentCount: number;
  trends: {
    totalInvested: number;
    currentValue: number;
    equity: number;
    annualNetCashFlow: number;
    portfolioRoi: number;
    portfolioIrr: number;
    equityMultiple: number;
  };
}

export interface AllocationSlice {
  key: string;
  label: string;
  amount: number;
  value: number;
  count: number;
  percent: number;
}

export interface AssetAllocation {
  byAssetClass: AllocationSlice[];
  byType: AllocationSlice[];
  byStage: AllocationSlice[];
  byStatus: AllocationSlice[];
}

export interface GeographicAllocation {
  byCity: AllocationSlice[];
  byState: AllocationSlice[];
}

export interface StageAllocation {
  stage: ProjectStage;
  label: string;
  investedCapital: number;
  currentValue: number;
  equity: number;
  count: number;
  avgRoi: number;
  avgRiskScore: number;
}

export interface PortfolioAllocation {
  asset: AssetAllocation;
  geographic: GeographicAllocation;
  stage: StageAllocation[];
}

export interface PortfolioPerformancePoint {
  date: string;
  label: string;
  investedCapital: number;
  portfolioValue: number;
  equity: number;
  cumulativeRoi: number;
  irr: number;
  equityMultiple: number;
  cashFlow: number;
  projectedRoi: number;
  actualRoi: number;
  benchmarkValue?: number;
}

export interface PortfolioRiskSummary {
  distribution: { range: string; count: number; percent: number }[];
  byInvestment: {
    id: string;
    projectName: string;
    riskLevel: RiskLevel;
    riskScore: number;
    exposure: number;
    exposurePercent: number;
  }[];
  byStage: { stage: ProjectStage; label: string; avgRiskScore: number; count: number }[];
  portfolioRiskScore: number;
  highRiskExposurePercent: number;
}

export interface PortfolioBenchmark {
  id: string;
  label: string;
  description: string;
  value: number;
  unit: 'percent' | 'multiple' | 'currency';
  isMock: true;
}

export interface PortfolioExitEvent {
  id: string;
  investmentId: string;
  slug: string;
  projectName: string;
  eventType: 'exit' | 'distribution' | 'milestone' | 'refinance';
  date: string;
  probability: number;
  projectedProceeds: number;
  status: 'scheduled' | 'projected' | 'completed';
}

export interface PortfolioExitSchedule {
  events: PortfolioExitEvent[];
}

export type ConcentrationSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface PortfolioConcentrationAlert {
  id: string;
  category: 'investment' | 'geography' | 'asset_class' | 'risk' | 'construction';
  severity: ConcentrationSeverity;
  title: string;
  description: string;
  exposure: number;
  exposurePercent: number;
  threshold: number;
  suggestedAction: string;
}

export interface PortfolioConcentration {
  alerts: PortfolioConcentrationAlert[];
  topInvestmentPercent: number;
  topGeographyPercent: number;
  topAssetClassPercent: number;
}

export interface PortfolioCashFlowMonth {
  date: string;
  label: string;
  actual: number;
  projected: number;
}

export interface PortfolioCashFlowByInvestment {
  id: string;
  projectName: string;
  annualCashFlow: number;
  monthlyAverage: number;
}

export interface PortfolioCashFlowSummary {
  trend: PortfolioCashFlowMonth[];
  byInvestment: PortfolioCashFlowByInvestment[];
  nextTwelveMonths: PortfolioCashFlowMonth[];
  totalAnnual: number;
  totalProjectedNext12: number;
}

export interface ReturnAttributionItem {
  id: string;
  label: string;
  contribution: number;
  percentOfTotal: number;
}

export interface PortfolioInsight {
  id: string;
  type:
    | 'top_performer'
    | 'bottom_performer'
    | 'concentration'
    | 'highest_risk'
    | 'cash_flow'
    | 'closest_exit'
    | 'most_improved'
    | 'target_missed';
  title: string;
  description: string;
  investmentId?: string;
  metric?: string;
}

export interface PerformanceTableRow {
  id: string;
  slug: string;
  projectName: string;
  type: InvestmentType;
  status: InvestmentStatus;
  stage: ProjectStage;
  city: string;
  state: string;
  assetClass: string;
  investedAmount: number;
  currentValue: number;
  equity: number;
  debt: number;
  roi: number;
  irr: number;
  equityMultiple: number;
  annualCashFlow: number;
  targetReturn: number;
  riskLevel: RiskLevel;
  riskScore: number;
  exitDate?: string;
  exitProbability: number;
}
