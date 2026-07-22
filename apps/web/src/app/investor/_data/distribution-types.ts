export const DISTRIBUTION_TYPES = [
  'preferred_return',
  'return_of_capital',
  'profit_share',
  'refinance_proceeds',
  'sale_proceeds',
  'mixed',
] as const;

export type DistributionType = (typeof DISTRIBUTION_TYPES)[number];

export const DISTRIBUTION_STATUSES = [
  'scheduled',
  'declared',
  'approved',
  'processing',
  'completed',
  'delayed',
  'failed',
  'cancelled',
] as const;

export type DistributionStatus = (typeof DISTRIBUTION_STATUSES)[number];

export const DISTRIBUTION_FREQUENCIES = [
  'monthly',
  'quarterly',
  'semi_annual',
  'annual',
  'one_time',
] as const;

export type DistributionFrequency = (typeof DISTRIBUTION_FREQUENCIES)[number];

export const PAYMENT_METHODS = ['ach', 'wire', 'check'] as const;

export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

export const PAYMENT_STATUSES = [
  'pending',
  'initiated',
  'completed',
  'failed',
] as const;

export type PaymentStatus = (typeof PAYMENT_STATUSES)[number];

export interface DistributionBreakdown {
  grossAmount: number;
  preferredReturnAmount: number;
  returnOfCapitalAmount: number;
  profitShareAmount: number;
  refinanceAmount: number;
  saleAmount: number;
  fees: number;
  withholding: number;
  netAmount: number;
}

export interface PaymentTimelineStep {
  stage: 'declared' | 'record_date' | 'approved' | 'initiated' | 'completed';
  label: string;
  date: string | null;
  completed: boolean;
}

export interface Distribution {
  id: string;
  investmentId: string;
  investmentName: string;
  entityName: string;
  periodLabel: string;
  taxYear: number;
  distributionType: DistributionType;
  frequency: DistributionFrequency;
  declaredDate: string;
  recordDate: string;
  paymentDate: string;
  breakdown: DistributionBreakdown;
  currency: string;
  status: DistributionStatus;
  paymentMethod: PaymentMethod;
  paymentStatus: PaymentStatus;
  reference: string;
  statementId: string | null;
  notes: string | null;
  delayReason: string | null;
  failureReason: string | null;
  paymentTimeline: PaymentTimelineStep[];
}

export interface DistributionStatement {
  id: string;
  distributionId: string;
  investmentId: string;
  investmentName: string;
  entityName: string;
  statementDate: string;
  periodLabel: string;
  taxYear: number;
  distributionType: DistributionType;
  grossAmount: number;
  netAmount: number;
  currency: string;
  status: 'available' | 'pending' | 'archived';
  fileName: string;
  pageCount: number;
}

export interface CashFlowPeriod {
  label: string;
  date: string;
  gross: number;
  net: number;
  preferredReturn: number;
  returnOfCapital: number;
  refinance: number;
  sale: number;
  fees: number;
  withholding: number;
}

export interface CashFlowSummary {
  lifetimeGross: number;
  lifetimeNet: number;
  currentYearGross: number;
  currentYearNet: number;
  preferredReturnTotal: number;
  capitalReturned: number;
  pendingAmount: number;
  avgAnnualYield: number;
  currency: string;
}

export interface CashFlowProjection {
  period: string;
  label: string;
  projectedGross: number;
  projectedNet: number;
  probability: 'high' | 'medium' | 'low';
  investmentCount: number;
}

export interface DistributionTaxSummary {
  taxYear: number;
  grossIncome: number;
  returnOfCapital: number;
  preferredReturn: number;
  profitShare: number;
  totalWithholding: number;
  netReceived: number;
  distributionCount: number;
}

export interface DistributionSchedule {
  investmentId: string;
  investmentName: string;
  nextDate: string;
  estimatedNet: number;
  frequency: DistributionFrequency;
  currency: string;
}

export interface DistributionEvent {
  id: string;
  date: string;
  title: string;
  investmentName: string;
  investmentId: string;
  amount: number;
  type: DistributionType;
  status: DistributionStatus;
  distributionId: string;
}

export interface DistributionAlert {
  id: string;
  severity: 'info' | 'warning' | 'error';
  title: string;
  description: string;
  distributionId: string | null;
  investmentId: string | null;
  actionLabel?: string;
}

export interface DistributionInsight {
  id: string;
  type: 'positive' | 'neutral' | 'attention';
  title: string;
  description: string;
  metric?: string;
}

export interface PreferredReturnTracking {
  investmentId: string;
  investmentName: string;
  investedAmount: number;
  preferredRate: number;
  cumulativePreferred: number;
  cumulativePaid: number;
  outstandingPreferred: number;
  currency: string;
}

export interface ReturnOfCapitalTracking {
  investmentId: string;
  investmentName: string;
  investedAmount: number;
  capitalReturned: number;
  remainingCapital: number;
  percentReturned: number;
  currency: string;
}

export interface InvestmentCashFlowRow {
  investmentId: string;
  investmentName: string;
  grossTotal: number;
  netTotal: number;
  preferredReturn: number;
  returnOfCapital: number;
  distributionCount: number;
  lastPaymentDate: string | null;
  currency: string;
}

export interface DistributionFilterState {
  search: string;
  investmentId: string | 'all';
  type: DistributionType | 'all';
  status: DistributionStatus | 'all';
  taxYear: number | 'all';
  dateFrom: string;
  dateTo: string;
}

export type CashFlowGranularity = 'monthly' | 'quarterly';

export interface DistributionDateRange {
  preset: '3M' | '6M' | 'YTD' | '1Y' | '3Y' | 'all';
  startDate?: string;
  endDate?: string;
}

export interface SourceBreakdownSlice {
  label: string;
  value: number;
  type: DistributionType | 'fees' | 'withholding';
}
