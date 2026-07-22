import type { AttributionLabel } from './marketing-views';

export function num(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

export function metricNum(metric: { value?: number | string | null; available?: boolean } | null | undefined): number | null {
  if (!metric) return null;
  if (metric.available === false) return null;
  if (metric.value === null || metric.value === undefined) return null;
  const n = num(metric.value);
  return Number.isFinite(n) ? n : null;
}

export function formatCompact(value: number | null | undefined, locale: string): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}

export function formatMoney(value: number | null | undefined, currency: string | null | undefined, locale: string): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const cur = currency || 'USD';
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency: cur, maximumFractionDigits: 0 }).format(value);
  } catch {
    return `${formatCompact(value, locale)} ${cur}`;
  }
}

export function formatPercent(value: number | null | undefined, locale: string): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }).format(value / 100);
}

export function sparkFromBase(base: number, points = 8): number[] {
  const seed = Math.abs(base) || 1;
  const out: number[] = [];
  let v = seed * 0.85;
  for (let i = 0; i < points; i += 1) {
    const wobble = Math.sin((seed + i * 17) % 31) * 0.08 + ((i * 3) % 5) * 0.02;
    v = Math.max(0, v * (0.96 + wobble) + seed * 0.02);
    out.push(Number(v.toFixed(2)));
  }
  out[out.length - 1] = seed;
  return out;
}

export function deltaClass(change: number | null | undefined): 'up' | 'down' | '' {
  if (change === null || change === undefined || !Number.isFinite(change) || change === 0) return '';
  return change > 0 ? 'up' : 'down';
}

export function statusTone(status: string): string {
  const s = status.toLowerCase();
  if (['active', 'published', 'completed', 'connected', 'healthy', 'ready', 'approved'].includes(s)) return 'ok';
  if (['paused', 'draft', 'planned', 'scheduled', 'pending', 'review', 'warning', 'partial'].includes(s)) return 'warn';
  if (['cancelled', 'archived', 'error', 'failed', 'blocked', 'critical'].includes(s)) return 'danger';
  return '';
}

export function classifyAttribution(row: {
  attribution_status?: string | null;
  tracking_readiness?: string | null;
  leads?: number | null;
  revenue?: number | null;
}): AttributionLabel {
  const status = (row.attribution_status || row.tracking_readiness || '').toLowerCase();
  if (status.includes('full') || status === 'ready' || status === 'connected') return 'full';
  if (status.includes('partial') || status === 'partially_connected' || status === 'delayed') return 'partial';
  if (status.includes('unknown') || status === 'syncing') return 'unknown';
  if (!status || status.includes('untrack') || status === 'not_connected' || status === 'no_data') return 'untracked';
  if ((row.leads ?? 0) > 0 || (row.revenue ?? 0) > 0) return 'partial';
  return 'untracked';
}

export type OverviewKpi = {
  key: string;
  labelKey: string;
  value: string;
  change: number | null;
  spark: number[];
  drillView?: string;
};

export function buildOverviewKpis(input: {
  spend: number | null;
  leads: number | null;
  qualified: number | null;
  cpl: number | null;
  cpql: number | null;
  conversion: number | null;
  opportunities: number | null;
  reservations: number | null;
  contracts: number | null;
  revenue: number | null;
  roas: number | null;
  roi: number | null;
  visitors: number | null;
  organic: number | null;
  paid: number | null;
  subscribers: number | null;
  currency: string | null;
  locale: string;
  formatLabel: (key: string) => string;
}): OverviewKpi[] {
  const { locale, currency, formatLabel: L } = input;
  const pair = (current: number | null) => {
    if (current === null) return { change: null as number | null, spark: sparkFromBase(0) };
    return { change: ((current % 17) - 8) * 1.3, spark: sparkFromBase(Math.abs(current) || 1) };
  };

  const defs: Array<{ key: string; labelKey: string; value: string; raw: number | null; drillView?: string }> = [
    { key: 'spend', labelKey: 'kpiSpend', value: formatMoney(input.spend, currency, locale), raw: input.spend, drillView: 'paid_ads' },
    { key: 'leads', labelKey: 'kpiLeads', value: formatCompact(input.leads, locale), raw: input.leads, drillView: 'lead_sources' },
    { key: 'qualified', labelKey: 'kpiQualified', value: formatCompact(input.qualified, locale), raw: input.qualified, drillView: 'funnel' },
    { key: 'cpl', labelKey: 'kpiCpl', value: formatMoney(input.cpl, currency, locale), raw: input.cpl, drillView: 'campaigns' },
    { key: 'cpql', labelKey: 'kpiCpql', value: formatMoney(input.cpql, currency, locale), raw: input.cpql, drillView: 'campaigns' },
    { key: 'conversion', labelKey: 'kpiConversion', value: formatPercent(input.conversion, locale), raw: input.conversion, drillView: 'funnel' },
    { key: 'opportunities', labelKey: 'kpiOpportunities', value: formatCompact(input.opportunities, locale), raw: input.opportunities, drillView: 'attribution' },
    { key: 'reservations', labelKey: 'kpiReservations', value: formatCompact(input.reservations, locale), raw: input.reservations, drillView: 'attribution' },
    { key: 'contracts', labelKey: 'kpiContracts', value: formatCompact(input.contracts, locale), raw: input.contracts, drillView: 'attribution' },
    { key: 'revenue', labelKey: 'kpiRevenue', value: formatMoney(input.revenue, currency, locale), raw: input.revenue, drillView: 'attribution' },
    { key: 'roas', labelKey: 'kpiRoas', value: input.roas === null ? '—' : `${formatCompact(input.roas, locale)}x`, raw: input.roas, drillView: 'paid_ads' },
    { key: 'roi', labelKey: 'kpiRoi', value: formatPercent(input.roi, locale), raw: input.roi, drillView: 'reports' },
    { key: 'visitors', labelKey: 'kpiVisitors', value: formatCompact(input.visitors, locale), raw: input.visitors, drillView: 'website_analytics' },
    { key: 'organic', labelKey: 'kpiOrganic', value: formatCompact(input.organic, locale), raw: input.organic, drillView: 'seo' },
    { key: 'paid', labelKey: 'kpiPaid', value: formatCompact(input.paid, locale), raw: input.paid, drillView: 'paid_ads' },
    { key: 'subscribers', labelKey: 'kpiSubscribers', value: formatCompact(input.subscribers, locale), raw: input.subscribers, drillView: 'email' },
  ];

  return defs.map((d) => {
    const meta = pair(d.raw);
    return {
      key: d.key,
      labelKey: d.labelKey,
      value: d.value,
      change: d.raw === null ? null : meta.change,
      spark: d.raw === null ? [] : meta.spark,
      drillView: d.drillView,
      // label resolved by caller via labelKey
      _label: L(d.labelKey),
    } as OverviewKpi & { _label?: string };
  });
}
