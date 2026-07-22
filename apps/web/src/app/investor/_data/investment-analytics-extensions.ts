import type { PortfolioInvestment } from './investment-types';
import type {
  AllocationCategory,
  EnrichedPortfolioInvestment,
  InvestmentAnalyticsExtension,
  MonthlyCashFlowPoint,
  MonthlyValuePoint,
} from './portfolio-types';

interface ExtensionSeed {
  currentDebtBalance: number;
  assetClass: string;
  neighborhood: string;
  targetReturn: number;
  exitProbability: number;
  riskScore: number;
  allocationCategory: AllocationCategory;
}

const EXTENSION_SEEDS: Record<string, ExtensionSeed> = {
  'pi-001': {
    currentDebtBalance: 420_000,
    assetClass: 'Multifamily',
    neighborhood: 'Downtown / Penn Quarter',
    targetReturn: 22.4,
    exitProbability: 0.72,
    riskScore: 58,
    allocationCategory: 'development',
  },
  'pi-002': {
    currentDebtBalance: 85_000,
    assetClass: 'Multifamily',
    neighborhood: 'U Street Corridor',
    targetReturn: 21.0,
    exitProbability: 0.88,
    riskScore: 32,
    allocationCategory: 'core_plus',
  },
  'pi-003': {
    currentDebtBalance: 112_500,
    assetClass: 'Mixed-Use',
    neighborhood: 'H Street NE',
    targetReturn: 18.2,
    exitProbability: 0.81,
    riskScore: 48,
    allocationCategory: 'value_add',
  },
  'pi-004': {
    currentDebtBalance: 310_000,
    assetClass: 'Commercial',
    neighborhood: 'Van Ness / Forest Hills',
    targetReturn: 26.5,
    exitProbability: 0.91,
    riskScore: 28,
    allocationCategory: 'core',
  },
  'pi-005': {
    currentDebtBalance: 48_000,
    assetClass: 'Residential',
    neighborhood: 'Morris Park',
    targetReturn: 30.0,
    exitProbability: 0.95,
    riskScore: 25,
    allocationCategory: 'core_plus',
  },
  'pi-006': {
    currentDebtBalance: 225_000,
    assetClass: 'Condominium',
    neighborhood: 'H Street NE',
    targetReturn: 19.6,
    exitProbability: 0.65,
    riskScore: 62,
    allocationCategory: 'development',
  },
  'pi-007': {
    currentDebtBalance: 0,
    assetClass: 'Residential',
    neighborhood: 'Riverside',
    targetReturn: 42.0,
    exitProbability: 1.0,
    riskScore: 78,
    allocationCategory: 'opportunistic',
  },
  'pi-008': {
    currentDebtBalance: 175_000,
    assetClass: 'Multifamily',
    neighborhood: 'Capitol Heights',
    targetReturn: 17.8,
    exitProbability: 0.58,
    riskScore: 55,
    allocationCategory: 'value_add',
  },
  'pi-009': {
    currentDebtBalance: 195_000,
    assetClass: 'Residential',
    neighborhood: 'Georgetown',
    targetReturn: 16.4,
    exitProbability: 0.76,
    riskScore: 52,
    allocationCategory: 'value_add',
  },
};

function hashSeed(id: string): number {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash << 5) - hash + id.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function generateHistoricalMonthlyValues(
  investment: PortfolioInvestment,
  seed: ExtensionSeed,
): MonthlyValuePoint[] {
  const start = new Date(investment.investmentDate);
  const end = new Date();
  const points: MonthlyValuePoint[] = [];
  const months =
    (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
  const totalMonths = Math.max(months, 6);
  const noise = (hashSeed(investment.id) % 100) / 1000;

  for (let i = 0; i <= totalMonths; i += 1) {
    const date = new Date(start.getFullYear(), start.getMonth() + i, 1);
    if (date > end) break;

    const progress = i / totalMonths;
    const growthCurve = progress ** (0.85 + noise);
    const investedCapital = investment.investedAmount;
    const portfolioValue =
      investedCapital +
      (investment.currentValue - investedCapital) * growthCurve +
      Math.sin(i * 0.4 + hashSeed(investment.id)) * investedCapital * 0.008;
    const debtRatio = seed.currentDebtBalance / Math.max(investment.currentValue, 1);
    const debt = portfolioValue * debtRatio;
    const equity = portfolioValue - debt;

    points.push({
      date: date.toISOString().slice(0, 10),
      investedCapital,
      portfolioValue: Math.round(portfolioValue),
      equity: Math.round(equity),
    });
  }

  return points;
}

function generateHistoricalCashFlow(
  investment: PortfolioInvestment,
): MonthlyCashFlowPoint[] {
  const annual = investment.performance.annualCashFlow;
  if (annual <= 0) return [];

  const start = new Date(investment.investmentDate);
  const end = new Date();
  const points: MonthlyCashFlowPoint[] = [];
  const monthlyBase = annual / 12;
  const rampMonths = investment.stage === 'stabilized' ? 3 : 12;

  let monthIndex = 0;
  for (
    let date = new Date(start.getFullYear(), start.getMonth(), 1);
    date <= end;
    date = new Date(date.getFullYear(), date.getMonth() + 1, 1)
  ) {
    const ramp = Math.min(1, monthIndex / rampMonths);
    const seasonal = 1 + Math.sin(monthIndex * 0.5 + hashSeed(investment.id) * 0.01) * 0.08;
    const amount = Math.round(monthlyBase * ramp * seasonal);

    if (amount > 0) {
      points.push({
        date: date.toISOString().slice(0, 10),
        amount,
      });
    }
    monthIndex += 1;
  }

  return points;
}

function buildExtension(investment: PortfolioInvestment): InvestmentAnalyticsExtension {
  const seed = EXTENSION_SEEDS[investment.id] ?? {
    currentDebtBalance: investment.currentValue * 0.15,
    assetClass: 'Real Estate',
    neighborhood: investment.city,
    targetReturn: investment.performance.projectedRoi,
    exitProbability: 0.7,
    riskScore: investment.riskLevel === 'high' ? 75 : investment.riskLevel === 'moderate' ? 50 : 30,
    allocationCategory: 'value_add' as AllocationCategory,
  };

  const currentReturn = investment.performance.roi;

  return {
    ...seed,
    currentReturn,
    historicalMonthlyValues: generateHistoricalMonthlyValues(investment, seed),
    historicalCashFlow: generateHistoricalCashFlow(investment),
  };
}

export function enrichInvestment(investment: PortfolioInvestment): EnrichedPortfolioInvestment {
  return {
    ...investment,
    analytics: buildExtension(investment),
  };
}

export function enrichInvestments(investments: PortfolioInvestment[]): EnrichedPortfolioInvestment[] {
  return investments.map(enrichInvestment);
}

export function getAnalyticsExtension(id: string): InvestmentAnalyticsExtension | undefined {
  const seed = EXTENSION_SEEDS[id];
  if (!seed) return undefined;
  return seed as unknown as InvestmentAnalyticsExtension;
}
