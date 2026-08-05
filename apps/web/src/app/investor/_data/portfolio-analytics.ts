import { getAllInvestments } from './investments';
import { enrichInvestments } from './investment-analytics-extensions';
import {
  INVESTMENT_STATUS_LABELS,
  INVESTMENT_TYPE_LABELS,
  PROJECT_STAGE_LABELS,
} from './investments';
import type { PortfolioInvestment } from './investment-types';
import type {
  EnrichedPortfolioInvestment,
  PortfolioAllocation,
  PortfolioBenchmark,
  PortfolioCashFlowSummary,
  PortfolioConcentration,
  PortfolioConcentrationAlert,
  PortfolioDateRange,
  PortfolioExitEvent,
  PortfolioExitSchedule,
  PortfolioFilterState,
  PortfolioInsight,
  PortfolioPerformancePoint,
  PortfolioRiskSummary,
  PortfolioSummary,
  PerformanceTableRow,
  ReturnAttributionItem,
  AllocationSlice,
  StageAllocation,
} from './portfolio-types';

const CONCENTRATION_THRESHOLDS = {
  singleInvestment: 30,
  geography: 50,
  assetClass: 60,
  highRisk: 25,
  construction: 40,
} as const;

export function getEnrichedPortfolio(): EnrichedPortfolioInvestment[] {
  return enrichInvestments(getAllInvestments());
}

export function countActivePortfolioFilters(filters: PortfolioFilterState): number {
  let count = 0;
  if (filters.status !== 'all') count += 1;
  if (filters.assetClass !== 'all') count += 1;
  if (filters.type !== 'all') count += 1;
  if (filters.location !== 'all') count += 1;
  if (filters.stage !== 'all') count += 1;
  if (filters.riskLevel !== 'all') count += 1;
  return count;
}

export function filterPortfolioInvestments(
  investments: EnrichedPortfolioInvestment[],
  filters: PortfolioFilterState,
): EnrichedPortfolioInvestment[] {
  return investments.filter((inv) => {
    if (filters.status !== 'all' && inv.status !== filters.status) return false;
    if (filters.assetClass !== 'all' && inv.analytics.assetClass !== filters.assetClass) return false;
    if (filters.type !== 'all' && inv.type !== filters.type) return false;
    if (filters.location !== 'all' && `${inv.city}, ${inv.state}` !== filters.location) return false;
    if (filters.stage !== 'all' && inv.stage !== filters.stage) return false;
    if (filters.riskLevel !== 'all' && inv.riskLevel !== filters.riskLevel) return false;
    return true;
  });
}

export function getPortfolioAssetClasses(investments: EnrichedPortfolioInvestment[]): string[] {
  return Array.from(new Set(investments.map((i) => i.analytics.assetClass))).sort();
}

export function getPortfolioLocations(investments: EnrichedPortfolioInvestment[]): string[] {
  return Array.from(new Set(investments.map((i) => `${i.city}, ${i.state}`))).sort();
}

function resolveDateRangeBounds(
  dateRange: PortfolioDateRange,
  investments: EnrichedPortfolioInvestment[],
): { start: Date; end: Date } {
  const end = dateRange.endDate ? new Date(dateRange.endDate) : new Date();
  let start: Date;

  switch (dateRange.preset) {
    case '3M':
      start = new Date(end.getFullYear(), end.getMonth() - 3, 1);
      break;
    case '6M':
      start = new Date(end.getFullYear(), end.getMonth() - 6, 1);
      break;
    case 'YTD':
      start = new Date(end.getFullYear(), 0, 1);
      break;
    case '1Y':
      start = new Date(end.getFullYear() - 1, end.getMonth(), 1);
      break;
    case '3Y':
      start = new Date(end.getFullYear() - 3, end.getMonth(), 1);
      break;
    case 'custom':
      start = dateRange.startDate ? new Date(dateRange.startDate) : new Date(end.getFullYear() - 1, end.getMonth(), 1);
      break;
    case 'inception':
    default: {
      const earliest = investments.reduce((min, inv) => {
        const d = new Date(inv.investmentDate);
        return d < min ? d : min;
      }, new Date());
      start = earliest;
      break;
    }
  }

  return { start, end };
}

function weightedAverage(
  items: { value: number; weight: number }[],
): number {
  const totalWeight = items.reduce((s, i) => s + i.weight, 0);
  if (totalWeight === 0) return 0;
  return items.reduce((s, i) => s + i.value * i.weight, 0) / totalWeight;
}

function computeTrend(current: number, previous: number): number {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
}

export function computePortfolioSummary(
  investments: EnrichedPortfolioInvestment[],
  _filters: PortfolioFilterState,
  dateRange: PortfolioDateRange,
): PortfolioSummary {
  const currency = investments[0]?.currency ?? 'USD';
  if (investments.length === 0) {
    return {
      totalInvested: 0,
      currentValue: 0,
      equity: 0,
      outstandingDebt: 0,
      annualNetCashFlow: 0,
      portfolioRoi: 0,
      portfolioIrr: 0,
      equityMultiple: 0,
      currency,
      investmentCount: 0,
      trends: {
        totalInvested: 0,
        currentValue: 0,
        equity: 0,
        annualNetCashFlow: 0,
        portfolioRoi: 0,
        portfolioIrr: 0,
        equityMultiple: 0,
      },
    };
  }

  const totalInvested = investments.reduce((s, i) => s + i.investedAmount, 0);
  const currentValue = investments.reduce((s, i) => s + i.currentValue, 0);
  const outstandingDebt = investments.reduce((s, i) => s + i.analytics.currentDebtBalance, 0);
  const equity = currentValue - outstandingDebt;
  const annualNetCashFlow = investments.reduce((s, i) => s + i.performance.annualCashFlow, 0);
  const portfolioRoi = totalInvested > 0 ? ((currentValue - totalInvested) / totalInvested) * 100 : 0;
  const portfolioIrr = weightedAverage(
    investments.map((i) => ({ value: i.performance.irr, weight: i.investedAmount })),
  );
  const equityMultiple = totalInvested > 0 ? currentValue / totalInvested : 0;

  const { start } = resolveDateRangeBounds(dateRange, investments);
  const priorPoints = computePerformanceSeries(investments, dateRange).points;
  const startLabel = start.toISOString().slice(0, 7);
  const priorPoint = priorPoints.find((p) => p.date.startsWith(startLabel)) ?? priorPoints[0];

  const priorInvested = priorPoint?.investedCapital ?? totalInvested;
  const priorValue = priorPoint?.portfolioValue ?? currentValue;
  const priorEquity = priorPoint?.equity ?? equity;
  const priorCashFlow = priorPoint?.cashFlow ?? annualNetCashFlow;
  const priorRoi = priorPoint?.cumulativeRoi ?? portfolioRoi;
  const priorIrr = priorPoint?.irr ?? portfolioIrr;
  const priorMultiple = priorPoint?.equityMultiple ?? equityMultiple;

  return {
    totalInvested,
    currentValue,
    equity,
    outstandingDebt,
    annualNetCashFlow,
    portfolioRoi,
    portfolioIrr,
    equityMultiple,
    currency,
    investmentCount: investments.length,
    trends: {
      totalInvested: computeTrend(totalInvested, priorInvested),
      currentValue: computeTrend(currentValue, priorValue),
      equity: computeTrend(equity, priorEquity),
      annualNetCashFlow: computeTrend(annualNetCashFlow, priorCashFlow),
      portfolioRoi: portfolioRoi - priorRoi,
      portfolioIrr: portfolioIrr - priorIrr,
      equityMultiple: computeTrend(equityMultiple, priorMultiple),
    },
  };
}

function buildAllocationSlices(
  investments: EnrichedPortfolioInvestment[],
  keyFn: (inv: EnrichedPortfolioInvestment) => string,
  labelFn: (key: string) => string,
): AllocationSlice[] {
  const map = new Map<string, { amount: number; value: number; count: number }>();
  for (const inv of investments) {
    const key = keyFn(inv);
    const existing = map.get(key) ?? { amount: 0, value: 0, count: 0 };
    map.set(key, {
      amount: existing.amount + inv.investedAmount,
      value: existing.value + inv.currentValue,
      count: existing.count + 1,
    });
  }
  const totalValue = investments.reduce((s, i) => s + i.currentValue, 0);
  return Array.from(map.entries())
    .map(([key, data]) => ({
      key,
      label: labelFn(key),
      amount: data.amount,
      value: data.value,
      count: data.count,
      percent: totalValue > 0 ? (data.value / totalValue) * 100 : 0,
    }))
    .sort((a, b) => b.value - a.value);
}

export function computeAllocations(investments: EnrichedPortfolioInvestment[]): PortfolioAllocation {
  const byAssetClass = buildAllocationSlices(
    investments,
    (i) => i.analytics.assetClass,
    (k) => k,
  );
  const byType = buildAllocationSlices(
    investments,
    (i) => i.type,
    (k) => INVESTMENT_TYPE_LABELS[k as PortfolioInvestment['type']] ?? k,
  );
  const byStage = buildAllocationSlices(
    investments,
    (i) => i.stage,
    (k) => PROJECT_STAGE_LABELS[k as PortfolioInvestment['stage']] ?? k,
  );
  const byStatus = buildAllocationSlices(
    investments,
    (i) => i.status,
    (k) => INVESTMENT_STATUS_LABELS[k as PortfolioInvestment['status']] ?? k,
  );

  const byCity = buildAllocationSlices(
    investments,
    (i) => i.city,
    (k) => k,
  );
  const byState = buildAllocationSlices(
    investments,
    (i) => i.state,
    (k) => k,
  );

  const stageMap = new Map<string, StageAllocation>();
  for (const inv of investments) {
    const existing = stageMap.get(inv.stage) ?? {
      stage: inv.stage,
      label: PROJECT_STAGE_LABELS[inv.stage],
      investedCapital: 0,
      currentValue: 0,
      equity: 0,
      count: 0,
      avgRoi: 0,
      avgRiskScore: 0,
    };
    existing.investedCapital += inv.investedAmount;
    existing.currentValue += inv.currentValue;
    existing.equity += inv.currentValue - inv.analytics.currentDebtBalance;
    existing.count += 1;
    existing.avgRoi += inv.performance.roi;
    existing.avgRiskScore += inv.analytics.riskScore;
    stageMap.set(inv.stage, existing);
  }

  const stage: StageAllocation[] = Array.from(stageMap.values()).map((s) => ({
    ...s,
    avgRoi: s.count > 0 ? s.avgRoi / s.count : 0,
    avgRiskScore: s.count > 0 ? s.avgRiskScore / s.count : 0,
  }));

  return {
    asset: { byAssetClass, byType, byStage, byStatus },
    geographic: { byCity, byState },
    stage,
  };
}

export function computeConcentration(investments: EnrichedPortfolioInvestment[]): PortfolioConcentration {
  const alerts = computeConcentrationAlerts(investments);
  const totalValue = investments.reduce((s, i) => s + i.currentValue, 0);

  if (investments.length === 0) {
    return {
      alerts,
      topInvestmentPercent: 0,
      topGeographyPercent: 0,
      topAssetClassPercent: 0,
    };
  }

  const topInvestment = investments.reduce((max, i) =>
    i.currentValue > max.currentValue ? i : max,
  );
  const topInvestmentPercent =
    totalValue > 0 && topInvestment ? (topInvestment.currentValue / totalValue) * 100 : 0;

  const geoMap = new Map<string, number>();
  const classMap = new Map<string, number>();
  for (const inv of investments) {
    const loc = `${inv.city}, ${inv.state}`;
    geoMap.set(loc, (geoMap.get(loc) ?? 0) + inv.currentValue);
    classMap.set(inv.analytics.assetClass, (classMap.get(inv.analytics.assetClass) ?? 0) + inv.currentValue);
  }
  const topGeographyPercent =
    totalValue > 0 && geoMap.size > 0
      ? (Math.max(...geoMap.values()) / totalValue) * 100
      : 0;
  const topAssetClassPercent =
    totalValue > 0 && classMap.size > 0
      ? (Math.max(...classMap.values()) / totalValue) * 100
      : 0;

  return { alerts, topInvestmentPercent, topGeographyPercent, topAssetClassPercent };
}

export function computeConcentrationAlerts(
  investments: EnrichedPortfolioInvestment[],
): PortfolioConcentrationAlert[] {
  const alerts: PortfolioConcentrationAlert[] = [];
  const totalValue = investments.reduce((s, i) => s + i.currentValue, 0);
  if (totalValue === 0) return alerts;

  for (const inv of investments) {
    const pct = (inv.currentValue / totalValue) * 100;
    if (pct > CONCENTRATION_THRESHOLDS.singleInvestment) {
      alerts.push({
        id: `conc-inv-${inv.id}`,
        category: 'investment',
        severity: pct > 40 ? 'critical' : 'high',
        title: `High concentration in ${inv.projectName}`,
        description: `${inv.projectName} represents ${pct.toFixed(1)}% of portfolio value, exceeding the ${CONCENTRATION_THRESHOLDS.singleInvestment}% threshold.`,
        exposure: inv.currentValue,
        exposurePercent: pct,
        threshold: CONCENTRATION_THRESHOLDS.singleInvestment,
        suggestedAction: 'Consider rebalancing through new commitments in other markets or asset classes.',
      });
    }
  }

  const geoMap = new Map<string, { value: number; label: string }>();
  for (const inv of investments) {
    const key = `${inv.city}, ${inv.state}`;
    const existing = geoMap.get(key) ?? { value: 0, label: key };
    geoMap.set(key, { value: existing.value + inv.currentValue, label: key });
  }
  for (const [, data] of geoMap) {
    const pct = (data.value / totalValue) * 100;
    if (pct > CONCENTRATION_THRESHOLDS.geography) {
      alerts.push({
        id: `conc-geo-${data.label}`,
        category: 'geography',
        severity: pct > 65 ? 'critical' : 'high',
        title: `Geographic concentration in ${data.label}`,
        description: `${data.label} accounts for ${pct.toFixed(1)}% of portfolio value.`,
        exposure: data.value,
        exposurePercent: pct,
        threshold: CONCENTRATION_THRESHOLDS.geography,
        suggestedAction: 'Diversify into additional metropolitan areas to reduce regional exposure.',
      });
    }
  }

  const classMap = new Map<string, number>();
  for (const inv of investments) {
    classMap.set(
      inv.analytics.assetClass,
      (classMap.get(inv.analytics.assetClass) ?? 0) + inv.currentValue,
    );
  }
  for (const [assetClass, value] of classMap) {
    const pct = (value / totalValue) * 100;
    if (pct > CONCENTRATION_THRESHOLDS.assetClass) {
      alerts.push({
        id: `conc-class-${assetClass}`,
        category: 'asset_class',
        severity: pct > 75 ? 'critical' : 'medium',
        title: `${assetClass} overweight`,
        description: `${assetClass} represents ${pct.toFixed(1)}% of portfolio value.`,
        exposure: value,
        exposurePercent: pct,
        threshold: CONCENTRATION_THRESHOLDS.assetClass,
        suggestedAction: 'Evaluate complementary asset classes such as commercial or opportunistic strategies.',
      });
    }
  }

  const highRiskValue = investments
    .filter((i) => i.riskLevel === 'high')
    .reduce((s, i) => s + i.currentValue, 0);
  const highRiskPct = (highRiskValue / totalValue) * 100;
  if (highRiskPct > CONCENTRATION_THRESHOLDS.highRisk) {
    alerts.push({
      id: 'conc-risk-high',
      category: 'risk',
      severity: 'high',
      title: 'Elevated high-risk exposure',
      description: `High-risk investments comprise ${highRiskPct.toFixed(1)}% of portfolio value.`,
      exposure: highRiskValue,
      exposurePercent: highRiskPct,
      threshold: CONCENTRATION_THRESHOLDS.highRisk,
      suggestedAction: 'Review risk-adjusted return targets and consider core or core-plus allocations.',
    });
  }

  const constructionValue = investments
    .filter((i) => i.stage === 'construction' || i.stage === 'pre_construction')
    .reduce((s, i) => s + i.currentValue, 0);
  const constructionPct = (constructionValue / totalValue) * 100;
  if (constructionPct > CONCENTRATION_THRESHOLDS.construction) {
    alerts.push({
      id: 'conc-construction',
      category: 'construction',
      severity: 'medium',
      title: 'Construction stage concentration',
      description: `${constructionPct.toFixed(1)}% of portfolio value is in pre-construction or construction.`,
      exposure: constructionValue,
      exposurePercent: constructionPct,
      threshold: CONCENTRATION_THRESHOLDS.construction,
      suggestedAction: 'Monitor capital calls and timeline risk across development projects.',
    });
  }

  return alerts.sort((a, b) => b.exposurePercent - a.exposurePercent);
}

export function computeRiskSummary(investments: EnrichedPortfolioInvestment[]): PortfolioRiskSummary {
  const totalValue = investments.reduce((s, i) => s + i.currentValue, 0);
  const ranges = [
    { range: '0–25 (Low)', min: 0, max: 25 },
    { range: '26–50 (Moderate)', min: 26, max: 50 },
    { range: '51–75 (Elevated)', min: 51, max: 75 },
    { range: '76–100 (High)', min: 76, max: 100 },
  ];

  const distribution = ranges.map((r) => {
    const count = investments.filter(
      (i) => i.analytics.riskScore >= r.min && i.analytics.riskScore <= r.max,
    ).length;
    return {
      range: r.range,
      count,
      percent: investments.length > 0 ? (count / investments.length) * 100 : 0,
    };
  });

  const byInvestment = investments
    .map((inv) => ({
      id: inv.id,
      projectName: inv.projectName,
      riskLevel: inv.riskLevel,
      riskScore: inv.analytics.riskScore,
      exposure: inv.currentValue,
      exposurePercent: totalValue > 0 ? (inv.currentValue / totalValue) * 100 : 0,
    }))
    .sort((a, b) => b.riskScore - a.riskScore);

  const stageMap = new Map<string, { total: number; count: number }>();
  for (const inv of investments) {
    const existing = stageMap.get(inv.stage) ?? { total: 0, count: 0 };
    stageMap.set(inv.stage, {
      total: existing.total + inv.analytics.riskScore,
      count: existing.count + 1,
    });
  }

  const byStage = Array.from(stageMap.entries()).map(([stage, data]) => ({
    stage: stage as PortfolioInvestment['stage'],
    label: PROJECT_STAGE_LABELS[stage as PortfolioInvestment['stage']],
    avgRiskScore: data.count > 0 ? data.total / data.count : 0,
    count: data.count,
  }));

  const portfolioRiskScore = weightedAverage(
    investments.map((i) => ({ value: i.analytics.riskScore, weight: i.currentValue })),
  );
  const highRiskExposurePercent =
    totalValue > 0
      ? (investments.filter((i) => i.riskLevel === 'high').reduce((s, i) => s + i.currentValue, 0) /
          totalValue) *
        100
      : 0;

  return {
    distribution,
    byInvestment,
    byStage,
    portfolioRiskScore,
    highRiskExposurePercent,
  };
}

export function computePerformanceSeries(
  investments: EnrichedPortfolioInvestment[],
  dateRange: PortfolioDateRange,
): { points: PortfolioPerformancePoint[]; hasHistoricalFallback: boolean } {
  if (investments.length === 0) {
    return { points: [], hasHistoricalFallback: false };
  }

  const { start, end } = resolveDateRangeBounds(dateRange, investments);
  const dateMap = new Map<string, PortfolioPerformancePoint>();

  let hasHistoricalFallback = false;

  for (const inv of investments) {
    const history = inv.analytics.historicalMonthlyValues;
    if (history.length === 0) hasHistoricalFallback = true;

    for (const point of history) {
      const d = new Date(point.date);
      if (d < start || d > end) continue;
      const monthKey = point.date.slice(0, 7);
      const existing = dateMap.get(monthKey) ?? {
        date: `${monthKey}-01`,
        label: new Date(`${monthKey}-01T12:00:00.000Z`).toLocaleDateString('en-US', {
          month: 'short',
          year: '2-digit',
          timeZone: 'UTC',
        }),
        investedCapital: 0,
        portfolioValue: 0,
        equity: 0,
        cumulativeRoi: 0,
        irr: 0,
        equityMultiple: 0,
        cashFlow: 0,
        projectedRoi: 0,
        actualRoi: 0,
      };
      existing.investedCapital += point.investedCapital;
      existing.portfolioValue += point.portfolioValue;
      existing.equity += point.equity;
      dateMap.set(monthKey, existing);
    }
  }

  const sortedPoints = Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
  const pointCount = sortedPoints.length;

  const points = sortedPoints.map((p, index) => {
    const cumulativeRoi =
      p.investedCapital > 0 ? ((p.portfolioValue - p.investedCapital) / p.investedCapital) * 100 : 0;
    const equityMultiple = p.investedCapital > 0 ? p.portfolioValue / p.investedCapital : 0;
    const filtered = investments.filter((inv) => {
      const invStart = new Date(inv.investmentDate);
      return invStart <= new Date(p.date);
    });
    const irr = weightedAverage(
      filtered.map((i) => ({ value: i.performance.irr, weight: i.investedAmount })),
    );
    const projectedRoi = weightedAverage(
      filtered.map((i) => ({ value: i.performance.projectedRoi, weight: i.investedAmount })),
    );
    const actualRoi = weightedAverage(
      filtered.map((i) => ({ value: i.performance.roi, weight: i.investedAmount })),
    );
    const cashFlow = filtered.reduce((s, i) => s + i.performance.annualCashFlow / 12, 0);
    const benchmarkValue =
      p.investedCapital * (1 + 0.085 * ((index + 1) / Math.max(pointCount, 12)));

    return {
      ...p,
      cumulativeRoi,
      equityMultiple,
      irr,
      projectedRoi,
      actualRoi,
      cashFlow,
      benchmarkValue,
    };
  });

  return { points, hasHistoricalFallback };
}

export function computeCashFlow(investments: EnrichedPortfolioInvestment[]): PortfolioCashFlowSummary {
  const monthMap = new Map<string, { actual: number; projected: number }>();
  const now = new Date();

  for (const inv of investments) {
    for (const cf of inv.analytics.historicalCashFlow) {
      const monthKey = cf.date.slice(0, 7);
      const existing = monthMap.get(monthKey) ?? { actual: 0, projected: 0 };
      existing.actual += cf.amount;
      monthMap.set(monthKey, existing);
    }
  }

  for (let i = 0; i < 12; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const monthKey = d.toISOString().slice(0, 7);
    const projected = investments.reduce((s, inv) => s + inv.performance.annualCashFlow / 12, 0);
    const existing = monthMap.get(monthKey) ?? { actual: 0, projected: 0 };
    existing.projected = projected;
    monthMap.set(monthKey, existing);
  }

  const trend = Array.from(monthMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-24)
    .map(([monthKey, data]) => ({
      date: `${monthKey}-01`,
      label: new Date(`${monthKey}-01T12:00:00.000Z`).toLocaleDateString('en-US', {
        month: 'short',
        year: '2-digit',
        timeZone: 'UTC',
      }),
      actual: data.actual,
      projected: data.projected,
    }));

  const byInvestment = investments
    .map((inv) => ({
      id: inv.id,
      projectName: inv.projectName,
      annualCashFlow: inv.performance.annualCashFlow,
      monthlyAverage: inv.performance.annualCashFlow / 12,
    }))
    .sort((a, b) => b.annualCashFlow - a.annualCashFlow);

  const nextTwelveMonths: PortfolioCashFlowSummary['nextTwelveMonths'] = [];
  for (let i = 0; i < 12; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const monthKey = d.toISOString().slice(0, 7);
    const projected = investments.reduce((s, inv) => s + inv.performance.annualCashFlow / 12, 0);
    nextTwelveMonths.push({
      date: `${monthKey}-01`,
      label: d.toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' }),
      actual: 0,
      projected,
    });
  }

  return {
    trend,
    byInvestment,
    nextTwelveMonths,
    totalAnnual: investments.reduce((s, i) => s + i.performance.annualCashFlow, 0),
    totalProjectedNext12: nextTwelveMonths.reduce((s, m) => s + m.projected, 0),
  };
}

export function computeBenchmarks(): PortfolioBenchmark[] {
  return [
    {
      id: 'target-roi',
      label: 'Target Portfolio ROI',
      description: 'Blended target return across active commitments (mock benchmark)',
      value: 18.5,
      unit: 'percent',
      isMock: true,
    },
    {
      id: 'target-irr',
      label: 'Target Portfolio IRR',
      description: 'Institutional real estate fund benchmark (mock)',
      value: 14.2,
      unit: 'percent',
      isMock: true,
    },
    {
      id: 'target-em',
      label: 'Target Equity Multiple',
      description: 'Hold-period equity multiple target (mock)',
      value: 1.65,
      unit: 'multiple',
      isMock: true,
    },
    {
      id: 'cash-yield',
      label: 'Cash Yield Benchmark',
      description: 'Stabilized multifamily cash yield (mock)',
      value: 5.8,
      unit: 'percent',
      isMock: true,
    },
    {
      id: 're-benchmark',
      label: 'NCREIF Property Index',
      description: 'Annualized total return — real estate benchmark (mock)',
      value: 8.5,
      unit: 'percent',
      isMock: true,
    },
    {
      id: 'inflation',
      label: 'CPI Inflation Rate',
      description: 'Trailing 12-month inflation reference (mock)',
      value: 3.2,
      unit: 'percent',
      isMock: true,
    },
  ];
}

export function computeExitSchedule(investments: EnrichedPortfolioInvestment[]): PortfolioExitSchedule {
  const events: PortfolioExitEvent[] = [];

  for (const inv of investments) {
    if (inv.exitDate) {
      events.push({
        id: `exit-${inv.id}`,
        investmentId: inv.id,
        slug: inv.slug,
        projectName: inv.projectName,
        eventType: inv.status === 'exited' ? 'exit' : 'exit',
        date: inv.exitDate,
        probability: inv.analytics.exitProbability,
        projectedProceeds: inv.currentValue,
        status: inv.status === 'exited' ? 'completed' : 'projected',
      });
    }
    if (inv.distribution.nextDistributionDate) {
      events.push({
        id: `dist-${inv.id}`,
        investmentId: inv.id,
        slug: inv.slug,
        projectName: inv.projectName,
        eventType: 'distribution',
        date: inv.distribution.nextDistributionDate,
        probability: 0.95,
        projectedProceeds: inv.performance.annualCashFlow / 4,
        status: 'scheduled',
      });
    }
  }

  events.sort((a, b) => a.date.localeCompare(b.date));

  return { events: events.slice(0, 12) };
}

export function computeReturnAttribution(
  investments: EnrichedPortfolioInvestment[],
): ReturnAttributionItem[] {
  const totalGain = investments.reduce(
    (s, i) => s + (i.currentValue - i.investedAmount),
    0,
  );
  if (totalGain <= 0) {
    return investments.map((inv) => ({
      id: inv.id,
      label: inv.projectName,
      contribution: inv.currentValue - inv.investedAmount,
      percentOfTotal: 0,
    }));
  }

  return investments
    .map((inv) => {
      const contribution = inv.currentValue - inv.investedAmount;
      return {
        id: inv.id,
        label: inv.projectName,
        contribution,
        percentOfTotal: (contribution / totalGain) * 100,
      };
    })
    .sort((a, b) => b.contribution - a.contribution);
}

export function computePerformanceTableRows(
  investments: EnrichedPortfolioInvestment[],
): PerformanceTableRow[] {
  return investments.map((inv) => ({
    id: inv.id,
    slug: inv.slug,
    projectName: inv.projectName,
    type: inv.type,
    status: inv.status,
    stage: inv.stage,
    city: inv.city,
    state: inv.state,
    assetClass: inv.analytics.assetClass,
    investedAmount: inv.investedAmount,
    currentValue: inv.currentValue,
    equity: inv.currentValue - inv.analytics.currentDebtBalance,
    debt: inv.analytics.currentDebtBalance,
    roi: inv.performance.roi,
    irr: inv.performance.irr,
    equityMultiple: inv.investedAmount > 0 ? inv.currentValue / inv.investedAmount : 0,
    annualCashFlow: inv.performance.annualCashFlow,
    targetReturn: inv.analytics.targetReturn,
    riskLevel: inv.riskLevel,
    riskScore: inv.analytics.riskScore,
    exitDate: inv.exitDate,
    exitProbability: inv.analytics.exitProbability,
  }));
}

export function computeInsights(investments: EnrichedPortfolioInvestment[]): PortfolioInsight[] {
  if (investments.length === 0) return [];

  const insights: PortfolioInsight[] = [];
  const totalValue = investments.reduce((s, i) => s + i.currentValue, 0);

  const byRoi = [...investments].sort((a, b) => b.performance.roi - a.performance.roi);
  const top = byRoi[0];
  const bottom = byRoi[byRoi.length - 1];

  if (top) {
    insights.push({
      id: 'top-performer',
      type: 'top_performer',
      title: 'Highest performer',
      description: `${top.projectName} leads the portfolio with ${top.performance.roi.toFixed(1)}% ROI.`,
      investmentId: top.id,
      metric: `${top.performance.roi.toFixed(1)}% ROI`,
    });
  }

  if (bottom && bottom.id !== top?.id) {
    insights.push({
      id: 'bottom-performer',
      type: 'bottom_performer',
      title: 'Lowest performer',
      description: `${bottom.projectName} has the lowest realized ROI at ${bottom.performance.roi.toFixed(1)}%.`,
      investmentId: bottom.id,
      metric: `${bottom.performance.roi.toFixed(1)}% ROI`,
    });
  }

  const largest = [...investments].sort((a, b) => b.currentValue - a.currentValue)[0];
  if (largest && totalValue > 0) {
    const pct = (largest.currentValue / totalValue) * 100;
    insights.push({
      id: 'concentration',
      type: 'concentration',
      title: 'Largest concentration',
      description: `${largest.projectName} represents ${pct.toFixed(1)}% of total portfolio value.`,
      investmentId: largest.id,
      metric: `${pct.toFixed(1)}% of portfolio`,
    });
  }

  const highestRisk = [...investments].sort(
    (a, b) => b.analytics.riskScore - a.analytics.riskScore,
  )[0];
  if (highestRisk) {
    insights.push({
      id: 'highest-risk',
      type: 'highest_risk',
      title: 'Highest risk exposure',
      description: `${highestRisk.projectName} has a risk score of ${highestRisk.analytics.riskScore} (${highestRisk.riskLevel} risk).`,
      investmentId: highestRisk.id,
      metric: `Score ${highestRisk.analytics.riskScore}`,
    });
  }

  const bestCashFlow = [...investments].sort(
    (a, b) => b.performance.annualCashFlow - a.performance.annualCashFlow,
  )[0];
  if (bestCashFlow && bestCashFlow.performance.annualCashFlow > 0) {
    insights.push({
      id: 'cash-flow',
      type: 'cash_flow',
      title: 'Strongest cash flow',
      description: `${bestCashFlow.projectName} generates the highest annual distributions.`,
      investmentId: bestCashFlow.id,
      metric: `$${bestCashFlow.performance.annualCashFlow.toLocaleString()}/yr`,
    });
  }

  const upcomingExits = investments
    .filter((i) => i.exitDate && i.status !== 'exited')
    .sort((a, b) => (a.exitDate ?? '').localeCompare(b.exitDate ?? ''));
  const closestExit = upcomingExits[0];
  if (closestExit?.exitDate) {
    insights.push({
      id: 'closest-exit',
      type: 'closest_exit',
      title: 'Closest projected exit',
      description: `${closestExit.projectName} is projected to exit on ${closestExit.exitDate}.`,
      investmentId: closestExit.id,
      metric: closestExit.exitDate,
    });
  }

  const mostImproved = [...investments].sort((a, b) => {
    const aDelta = a.analytics.currentReturn - (a.analytics.historicalMonthlyValues[0]?.portfolioValue ?? 0) / Math.max(a.investedAmount, 1) * 100;
    const bDelta = b.analytics.currentReturn - (b.analytics.historicalMonthlyValues[0]?.portfolioValue ?? 0) / Math.max(b.investedAmount, 1) * 100;
    return bDelta - aDelta;
  })[0];
  if (mostImproved) {
    insights.push({
      id: 'most-improved',
      type: 'most_improved',
      title: 'Most improved',
      description: `${mostImproved.projectName} shows the strongest value appreciation trajectory.`,
      investmentId: mostImproved.id,
    });
  }

  const missedTarget = investments.filter(
    (i) => i.performance.roi > 0 && i.performance.roi < i.analytics.targetReturn,
  );
  if (missedTarget.length > 0) {
    insights.push({
      id: 'target-missed',
      type: 'target_missed',
      title: 'Below target returns',
      description: `${missedTarget.length} investment${missedTarget.length > 1 ? 's are' : ' is'} tracking below target return.`,
      metric: `${missedTarget.length} investments`,
    });
  }

  return insights;
}

export function formatTrendDelta(value: number, isPercent = false): string {
  const sign = value >= 0 ? '+' : '';
  if (isPercent) return `${sign}${value.toFixed(1)} pp`;
  return `${sign}${value.toFixed(1)}%`;
}
