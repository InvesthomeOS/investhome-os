import { getAllInvestments } from './investments';
import {
  DISTRIBUTION_REFERENCE_DATE,
  getAllDistributions,
  getDistributionById,
} from './distributions';
import type {
  CashFlowPeriod,
  CashFlowProjection,
  CashFlowSummary,
  Distribution,
  DistributionAlert,
  DistributionDateRange,
  DistributionEvent,
  DistributionFilterState,
  DistributionInsight,
  DistributionSchedule,
  DistributionTaxSummary,
  InvestmentCashFlowRow,
  PreferredReturnTracking,
  ReturnOfCapitalTracking,
  SourceBreakdownSlice,
} from './distribution-types';

const COMPLETED_STATUSES = new Set<Distribution['status']>(['completed']);
const PENDING_STATUSES = new Set<Distribution['status']>([
  'scheduled',
  'declared',
  'approved',
  'processing',
  'delayed',
]);

function parseDate(dateStr: string): Date {
  return new Date(`${dateStr}T12:00:00`);
}

function isInDateRange(dateStr: string, start: Date, end: Date): boolean {
  const d = parseDate(dateStr);
  return d >= start && d <= end;
}

function resolveDateRangeBounds(
  dateRange: DistributionDateRange,
  distributions: Distribution[],
): { start: Date; end: Date } {
  const end = dateRange.endDate
    ? parseDate(dateRange.endDate)
    : parseDate(DISTRIBUTION_REFERENCE_DATE);
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
      start = new Date(end.getFullYear() - 1, end.getMonth(), end.getDate());
      break;
    case '3Y':
      start = new Date(end.getFullYear() - 3, end.getMonth(), end.getDate());
      break;
    case 'all':
    default: {
      if (distributions.length === 0) {
        start = new Date(end.getFullYear() - 5, 0, 1);
      } else {
        const earliest = distributions.reduce((min, d) => {
          const dt = parseDate(d.paymentDate);
          return dt < min ? dt : min;
        }, parseDate(distributions[0]!.paymentDate));
        start = earliest;
      }
      break;
    }
  }

  if (dateRange.startDate) {
    start = parseDate(dateRange.startDate);
  }

  return { start, end };
}

export function filterDistributions(
  distributions: Distribution[],
  filters: DistributionFilterState,
): Distribution[] {
  return distributions.filter((d) => {
    if (filters.investmentId !== 'all' && d.investmentId !== filters.investmentId) return false;
    if (filters.type !== 'all' && d.distributionType !== filters.type) return false;
    if (filters.status !== 'all' && d.status !== filters.status) return false;
    if (filters.taxYear !== 'all' && d.taxYear !== filters.taxYear) return false;
    if (filters.dateFrom && parseDate(d.paymentDate) < parseDate(filters.dateFrom)) return false;
    if (filters.dateTo && parseDate(d.paymentDate) > parseDate(filters.dateTo)) return false;
    if (filters.search.trim()) {
      const q = filters.search.toLowerCase();
      const haystack = [
        d.investmentName,
        d.entityName,
        d.periodLabel,
        d.reference,
        d.distributionType,
      ]
        .join(' ')
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
}

export function computeDistributionSummary(
  distributions: Distribution[],
  filters: DistributionFilterState,
  dateRange: DistributionDateRange,
): CashFlowSummary {
  const filtered = filterDistributions(distributions, filters);
  const { start, end } = resolveDateRangeBounds(dateRange, filtered);
  const refYear = parseDate(DISTRIBUTION_REFERENCE_DATE).getFullYear();
  const currency = filtered[0]?.currency ?? 'USD';

  const completed = filtered.filter((d) => COMPLETED_STATUSES.has(d.status));
  const pending = filtered.filter((d) => PENDING_STATUSES.has(d.status));

  const lifetimeGross = completed.reduce((s, d) => s + d.breakdown.grossAmount, 0);
  const lifetimeNet = completed.reduce((s, d) => s + d.breakdown.netAmount, 0);

  const currentYearCompleted = completed.filter((d) => d.taxYear === refYear);
  const currentYearGross = currentYearCompleted.reduce((s, d) => s + d.breakdown.grossAmount, 0);
  const currentYearNet = currentYearCompleted.reduce((s, d) => s + d.breakdown.netAmount, 0);

  const preferredReturnTotal = completed.reduce(
    (s, d) => s + d.breakdown.preferredReturnAmount,
    0,
  );
  const capitalReturned = completed.reduce(
    (s, d) => s + d.breakdown.returnOfCapitalAmount,
    0,
  );
  const pendingAmount = pending.reduce((s, d) => s + d.breakdown.netAmount, 0);

  const rangeCompleted = completed.filter((d) => isInDateRange(d.paymentDate, start, end));
  const yearsInRange = Math.max(
    1,
    (end.getTime() - start.getTime()) / (365.25 * 24 * 60 * 60 * 1000),
  );
  const rangeNet = rangeCompleted.reduce((s, d) => s + d.breakdown.netAmount, 0);
  const totalInvested = getAllInvestments().reduce((s, i) => s + i.investedAmount, 0);
  const avgAnnualYield = totalInvested > 0 ? (rangeNet / yearsInRange / totalInvested) * 100 : 0;

  return {
    lifetimeGross,
    lifetimeNet,
    currentYearGross,
    currentYearNet,
    preferredReturnTotal,
    capitalReturned,
    pendingAmount,
    avgAnnualYield,
    currency,
  };
}

export function computeCashFlowSeries(
  distributions: Distribution[],
  filters: DistributionFilterState,
  dateRange: DistributionDateRange,
  granularity: 'monthly' | 'quarterly',
): CashFlowPeriod[] {
  const filtered = filterDistributions(distributions, filters);
  const { start, end } = resolveDateRangeBounds(dateRange, filtered);
  const completed = filtered.filter(
    (d) => COMPLETED_STATUSES.has(d.status) && isInDateRange(d.paymentDate, start, end),
  );

  const buckets = new Map<string, CashFlowPeriod>();

  for (const d of completed) {
    const dt = parseDate(d.paymentDate);
    let key: string;
    let label: string;

    if (granularity === 'monthly') {
      key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`;
      label = dt.toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' });
    } else {
      const q = Math.floor(dt.getMonth() / 3) + 1;
      key = `${dt.getFullYear()}-Q${q}`;
      label = `Q${q} ${dt.getFullYear()}`;
    }

    const existing = buckets.get(key) ?? {
      label,
      date: d.paymentDate,
      gross: 0,
      net: 0,
      preferredReturn: 0,
      returnOfCapital: 0,
      refinance: 0,
      sale: 0,
      fees: 0,
      withholding: 0,
    };

    existing.gross += d.breakdown.grossAmount;
    existing.net += d.breakdown.netAmount;
    existing.preferredReturn += d.breakdown.preferredReturnAmount;
    existing.returnOfCapital += d.breakdown.returnOfCapitalAmount;
    existing.refinance += d.breakdown.refinanceAmount;
    existing.sale += d.breakdown.saleAmount;
    existing.fees += d.breakdown.fees;
    existing.withholding += d.breakdown.withholding;

    buckets.set(key, existing);
  }

  return Array.from(buckets.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, period]) => period);
}

export function computeSourceBreakdown(
  distributions: Distribution[],
  filters: DistributionFilterState,
  dateRange: DistributionDateRange,
): SourceBreakdownSlice[] {
  const filtered = filterDistributions(distributions, filters);
  const { start, end } = resolveDateRangeBounds(dateRange, filtered);
  const completed = filtered.filter(
    (d) => COMPLETED_STATUSES.has(d.status) && isInDateRange(d.paymentDate, start, end),
  );

  const totals = {
    preferred_return: 0,
    return_of_capital: 0,
    profit_share: 0,
    refinance_proceeds: 0,
    sale_proceeds: 0,
  };

  for (const d of completed) {
    totals.preferred_return += d.breakdown.preferredReturnAmount;
    totals.return_of_capital += d.breakdown.returnOfCapitalAmount;
    totals.profit_share += d.breakdown.profitShareAmount;
    totals.refinance_proceeds += d.breakdown.refinanceAmount;
    totals.sale_proceeds += d.breakdown.saleAmount;
  }

  return [
    { label: 'Preferred Return', value: totals.preferred_return, type: 'preferred_return' as const },
    { label: 'Return of Capital', value: totals.return_of_capital, type: 'return_of_capital' as const },
    { label: 'Profit Share', value: totals.profit_share, type: 'profit_share' as const },
    { label: 'Refinance Proceeds', value: totals.refinance_proceeds, type: 'refinance_proceeds' as const },
    { label: 'Sale Proceeds', value: totals.sale_proceeds, type: 'sale_proceeds' as const },
  ].filter((s) => s.value > 0);
}

export function computeProjections(
  distributions: Distribution[],
): CashFlowProjection[] {
  const ref = parseDate(DISTRIBUTION_REFERENCE_DATE);
  const scheduled = distributions.filter((d) => d.status === 'scheduled' || d.status === 'approved');

  const next30 = addDays(ref, 30);
  const next90 = addDays(ref, 90);

  const projections: CashFlowProjection[] = [];

  const sumInWindow = (start: Date, end: Date, probability: CashFlowProjection['probability']) => {
    const inWindow = scheduled.filter((d) => {
      const pd = parseDate(d.paymentDate);
      return pd >= start && pd <= end;
    });
    if (inWindow.length === 0) return;
    projections.push({
      period: `${start.toISOString().slice(0, 10)}_${end.toISOString().slice(0, 10)}`,
      label: formatWindowLabel(start, end),
      projectedGross: inWindow.reduce((s, d) => s + d.breakdown.grossAmount, 0),
      projectedNet: inWindow.reduce((s, d) => s + d.breakdown.netAmount, 0),
      probability,
      investmentCount: new Set(inWindow.map((d) => d.investmentId)).size,
    });
  };

  sumInWindow(ref, next30, 'high');
  sumInWindow(ref, next90, 'high');

  const monthlyAvg =
    distributions
      .filter((d) => COMPLETED_STATUSES.has(d.status) && d.taxYear === ref.getFullYear())
      .reduce((s, d) => s + d.breakdown.netAmount, 0) / 6;

  for (let m = 1; m <= 12; m++) {
    const monthStart = new Date(ref.getFullYear(), ref.getMonth() + m, 1);
    const monthEnd = new Date(ref.getFullYear(), ref.getMonth() + m + 1, 0);
    const scheduledInMonth = scheduled.filter((d) => {
      const pd = parseDate(d.paymentDate);
      return pd >= monthStart && pd <= monthEnd;
    });
    const net =
      scheduledInMonth.length > 0
        ? scheduledInMonth.reduce((s, d) => s + d.breakdown.netAmount, 0)
        : monthlyAvg * 0.85;
    projections.push({
      period: `month-${m}`,
      label: monthStart.toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' }),
      projectedGross: net * 1.12,
      projectedNet: net,
      probability: scheduledInMonth.length > 0 ? 'high' : 'medium',
      investmentCount: scheduledInMonth.length > 0
        ? new Set(scheduledInMonth.map((d) => d.investmentId)).size
        : 3,
    });
  }

  for (let y = 2; y <= 5; y++) {
    const year = ref.getFullYear() + y;
    const annualEstimate = monthlyAvg * 12 * (1 + y * 0.03);
    projections.push({
      period: `year-${year}`,
      label: `${year} (Est.)`,
      projectedGross: annualEstimate * 1.12,
      projectedNet: annualEstimate,
      probability: y <= 2 ? 'medium' : 'low',
      investmentCount: getAllInvestments().filter((i) => i.status !== 'exited').length,
    });
  }

  return projections;
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function formatWindowLabel(start: Date, end: Date): string {
  const fmt = (d: Date) =>
    d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
  return `${fmt(start)} – ${fmt(end)}`;
}

export function computePreferredReturnByInvestment(
  distributions: Distribution[],
): PreferredReturnTracking[] {
  const investments = getAllInvestments();
  const preferredRates: Record<string, number> = {
    'pi-002': 8.0,
    'pi-003': 7.5,
    'pi-004': 6.0,
    'pi-005': 8.0,
    'pi-009': 5.0,
  };

  return investments
    .filter((inv) => preferredRates[inv.id] !== undefined)
    .map((inv) => {
      const invDists = distributions.filter(
        (d) => d.investmentId === inv.id && COMPLETED_STATUSES.has(d.status),
      );
      const cumulativePaid = invDists.reduce(
        (s, d) => s + d.breakdown.preferredReturnAmount,
        0,
      );
      const yearsHeld =
        (parseDate(DISTRIBUTION_REFERENCE_DATE).getTime() -
          parseDate(inv.investmentDate).getTime()) /
        (365.25 * 24 * 60 * 60 * 1000);
      const rate = preferredRates[inv.id] ?? 0;
      const cumulativePreferred = inv.investedAmount * (rate / 100) * Math.max(yearsHeld, 0);

      return {
        investmentId: inv.id,
        investmentName: inv.projectName,
        investedAmount: inv.investedAmount,
        preferredRate: rate,
        cumulativePreferred,
        cumulativePaid,
        outstandingPreferred: Math.max(cumulativePreferred - cumulativePaid, 0),
        currency: inv.currency,
      };
    });
}

export function computeReturnOfCapital(
  distributions: Distribution[],
): ReturnOfCapitalTracking[] {
  const investments = getAllInvestments();

  return investments
    .map((inv) => {
      const invDists = distributions.filter(
        (d) => d.investmentId === inv.id && COMPLETED_STATUSES.has(d.status),
      );
      const capitalReturned = invDists.reduce(
        (s, d) => s + d.breakdown.returnOfCapitalAmount,
        0,
      );
      const remainingCapital = Math.max(inv.investedAmount - capitalReturned, 0);
      const percentReturned =
        inv.investedAmount > 0 ? (capitalReturned / inv.investedAmount) * 100 : 0;

      return {
        investmentId: inv.id,
        investmentName: inv.projectName,
        investedAmount: inv.investedAmount,
        capitalReturned,
        remainingCapital,
        percentReturned,
        currency: inv.currency,
      };
    })
    .filter((r) => r.capitalReturned > 0 || r.investedAmount > 0);
}

export function computeTaxSummary(distributions: Distribution[]): DistributionTaxSummary[] {
  const years = Array.from(new Set(distributions.map((d) => d.taxYear))).sort((a, b) => b - a);

  return years.map((taxYear) => {
    const yearDists = distributions.filter(
      (d) => d.taxYear === taxYear && COMPLETED_STATUSES.has(d.status),
    );
    return {
      taxYear,
      grossIncome: yearDists.reduce((s, d) => s + d.breakdown.grossAmount, 0),
      returnOfCapital: yearDists.reduce((s, d) => s + d.breakdown.returnOfCapitalAmount, 0),
      preferredReturn: yearDists.reduce((s, d) => s + d.breakdown.preferredReturnAmount, 0),
      profitShare: yearDists.reduce(
        (s, d) => s + d.breakdown.profitShareAmount + d.breakdown.saleAmount,
        0,
      ),
      totalWithholding: yearDists.reduce((s, d) => s + d.breakdown.withholding, 0),
      netReceived: yearDists.reduce((s, d) => s + d.breakdown.netAmount, 0),
      distributionCount: yearDists.length,
    };
  });
}

export function computeAlerts(distributions: Distribution[]): DistributionAlert[] {
  const alerts: DistributionAlert[] = [];

  for (const d of distributions) {
    if (d.status === 'failed') {
      alerts.push({
        id: `alert-failed-${d.id}`,
        severity: 'error',
        title: `Payment failed — ${d.investmentName}`,
        description: d.failureReason ?? 'Payment could not be processed.',
        distributionId: d.id,
        investmentId: d.investmentId,
        actionLabel: 'Update Payment Info',
      });
    }
    if (d.status === 'delayed') {
      alerts.push({
        id: `alert-delayed-${d.id}`,
        severity: 'warning',
        title: `Delayed distribution — ${d.periodLabel}`,
        description: d.delayReason ?? 'Distribution processing is behind schedule.',
        distributionId: d.id,
        investmentId: d.investmentId,
        actionLabel: 'View Details',
      });
    }
  }

  const ref = parseDate(DISTRIBUTION_REFERENCE_DATE);
  const overdue = distributions.filter((d) => {
    if (d.status !== 'processing') return false;
    return parseDate(d.paymentDate) < ref;
  });
  for (const d of overdue) {
    alerts.push({
      id: `alert-overdue-${d.id}`,
      severity: 'warning',
      title: `Processing overdue — ${d.reference}`,
      description: `Payment initiated but not yet completed as of ${DISTRIBUTION_REFERENCE_DATE}.`,
      distributionId: d.id,
      investmentId: d.investmentId,
    });
  }

  if (alerts.length === 0) {
    alerts.push({
      id: 'alert-all-clear',
      severity: 'info',
      title: 'No critical exceptions',
      description: 'All completed distributions reconciled. Scheduled payments on track.',
      distributionId: null,
      investmentId: null,
    });
  }

  return alerts;
}

export function computeInsights(
  distributions: Distribution[],
  summary: CashFlowSummary,
): DistributionInsight[] {
  const insights: DistributionInsight[] = [];
  const refYear = parseDate(DISTRIBUTION_REFERENCE_DATE).getFullYear();
  const lastYear = distributions.filter(
    (d) => d.taxYear === refYear - 1 && COMPLETED_STATUSES.has(d.status),
  );
  const thisYear = distributions.filter(
    (d) => d.taxYear === refYear && COMPLETED_STATUSES.has(d.status),
  );
  const lastYearNet = lastYear.reduce((s, d) => s + d.breakdown.netAmount, 0);
  const thisYearNet = thisYear.reduce((s, d) => s + d.breakdown.netAmount, 0);

  if (lastYearNet > 0) {
    const yoy = ((thisYearNet - lastYearNet) / lastYearNet) * 100;
    insights.push({
      id: 'insight-yoy',
      type: yoy >= 0 ? 'positive' : 'attention',
      title: 'Year-over-year cash flow',
      description: `Net distributions ${yoy >= 0 ? 'increased' : 'decreased'} compared to the same period last year.`,
      metric: `${yoy >= 0 ? '+' : ''}${yoy.toFixed(1)}%`,
    });
  }

  insights.push({
    id: 'insight-yield',
    type: 'neutral',
    title: 'Portfolio distribution yield',
    description: 'Annualized net cash flow relative to total invested capital in the selected range.',
    metric: `${summary.avgAnnualYield.toFixed(1)}%`,
  });

  const topInvestment = computeCashFlowByInvestment(distributions)[0];
  if (topInvestment) {
    insights.push({
      id: 'insight-top',
      type: 'positive',
      title: 'Largest cash flow contributor',
      description: `${topInvestment.investmentName} accounts for the highest cumulative net distributions.`,
      metric: formatCompact(topInvestment.netTotal),
    });
  }

  const pendingCount = distributions.filter((d) => PENDING_STATUSES.has(d.status)).length;
  if (pendingCount > 0) {
    insights.push({
      id: 'insight-pending',
      type: 'attention',
      title: 'Pending distributions',
      description: `${pendingCount} distribution${pendingCount > 1 ? 's' : ''} awaiting completion or scheduled payment.`,
      metric: formatCompact(summary.pendingAmount),
    });
  }

  return insights;
}

function formatCompact(amount: number): string {
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
  return `$${amount.toFixed(0)}`;
}

export function getUpcomingDistributions(
  distributions: Distribution[],
  limit = 4,
): Distribution[] {
  const ref = parseDate(DISTRIBUTION_REFERENCE_DATE);
  return distributions
    .filter(
      (d) =>
        PENDING_STATUSES.has(d.status) && parseDate(d.paymentDate) >= ref,
    )
    .sort((a, b) => parseDate(a.paymentDate).getTime() - parseDate(b.paymentDate).getTime())
    .slice(0, limit);
}

export function getUpcomingTotals(
  distributions: Distribution[],
): { days30: number; days90: number } {
  const ref = parseDate(DISTRIBUTION_REFERENCE_DATE);
  const d30 = addDays(ref, 30);
  const d90 = addDays(ref, 90);
  const upcoming = distributions.filter((d) => PENDING_STATUSES.has(d.status));

  return {
    days30: upcoming
      .filter((d) => {
        const pd = parseDate(d.paymentDate);
        return pd >= ref && pd <= d30;
      })
      .reduce((s, d) => s + d.breakdown.netAmount, 0),
    days90: upcoming
      .filter((d) => {
        const pd = parseDate(d.paymentDate);
        return pd >= ref && pd <= d90;
      })
      .reduce((s, d) => s + d.breakdown.netAmount, 0),
  };
}

export function getDistributionEvents(distributions: Distribution[]): DistributionEvent[] {
  return distributions.map((d) => ({
    id: `evt-${d.id}`,
    date: d.paymentDate,
    title: `${d.periodLabel} — ${d.investmentName}`,
    investmentName: d.investmentName,
    investmentId: d.investmentId,
    amount: d.breakdown.netAmount,
    type: d.distributionType,
    status: d.status,
    distributionId: d.id,
  }));
}

export function getDistributionSchedules(): DistributionSchedule[] {
  const investments = getAllInvestments();
  const distributions = getAllDistributions();
  const ref = parseDate(DISTRIBUTION_REFERENCE_DATE);

  return investments
    .filter((inv) => inv.distribution.nextDistributionDate)
    .map((inv) => {
      const scheduled = distributions.find(
        (d) =>
          d.investmentId === inv.id &&
          d.status === 'scheduled' &&
          d.paymentDate === inv.distribution.nextDistributionDate,
      );
      return {
        investmentId: inv.id,
        investmentName: inv.projectName,
        nextDate: inv.distribution.nextDistributionDate!,
        estimatedNet: scheduled?.breakdown.netAmount ?? inv.performance.annualCashFlow / 4,
        frequency: scheduled?.frequency ?? 'quarterly',
        currency: inv.currency,
      };
    })
    .filter((s) => parseDate(s.nextDate) >= ref)
    .sort((a, b) => parseDate(a.nextDate).getTime() - parseDate(b.nextDate).getTime());
}

export function computeCashFlowByInvestment(
  distributions: Distribution[],
): InvestmentCashFlowRow[] {
  const investments = getAllInvestments();
  const rows: InvestmentCashFlowRow[] = investments.map((inv) => {
    const invDists = distributions.filter((d) => d.investmentId === inv.id);
    const completed = invDists.filter((d) => COMPLETED_STATUSES.has(d.status));
    const lastCompleted = completed.sort(
      (a, b) => parseDate(b.paymentDate).getTime() - parseDate(a.paymentDate).getTime(),
    )[0];

    return {
      investmentId: inv.id,
      investmentName: inv.projectName,
      grossTotal: completed.reduce((s, d) => s + d.breakdown.grossAmount, 0),
      netTotal: completed.reduce((s, d) => s + d.breakdown.netAmount, 0),
      preferredReturn: completed.reduce((s, d) => s + d.breakdown.preferredReturnAmount, 0),
      returnOfCapital: completed.reduce((s, d) => s + d.breakdown.returnOfCapitalAmount, 0),
      distributionCount: completed.length,
      lastPaymentDate: lastCompleted?.paymentDate ?? null,
      currency: inv.currency,
    };
  });

  return rows
    .filter((r) => r.distributionCount > 0)
    .sort((a, b) => b.netTotal - a.netTotal);
}

export function getAvailableTaxYears(distributions: Distribution[]): number[] {
  return Array.from(new Set(distributions.map((d) => d.taxYear))).sort((a, b) => b - a);
}

export { getAllDistributions, getDistributionById };

export function computeNextScheduledAmount(distributions: Distribution[]): {
  date: string;
  amount: number;
  investmentName: string;
  currency: string;
} | null {
  const upcoming = getUpcomingDistributions(distributions, 1);
  if (upcoming.length === 0) return null;
  const next = upcoming[0]!;
  return {
    date: next.paymentDate,
    amount: next.breakdown.netAmount,
    investmentName: next.investmentName,
    currency: next.currency,
  };
}
