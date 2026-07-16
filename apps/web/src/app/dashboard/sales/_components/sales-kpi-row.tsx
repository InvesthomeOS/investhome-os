'use client';

import { KpiCard } from '@investhome/ui';

import type { SalesHomeKpis, SalesKpiKey } from '@/lib/api/sales';
import { formatCurrencyTotals } from '@/lib/api/sales';

interface SalesKpiRowProps {
  kpis: SalesHomeKpis | null;
  loading: boolean;
  activeKpi: SalesKpiKey | null;
  labels: Record<SalesKpiKey, string>;
  locale: string;
  onKpiClick: (key: SalesKpiKey) => void;
}

const KPI_ORDER: SalesKpiKey[] = [
  'new_leads',
  'qualified_leads',
  'active_opportunities',
  'pipeline_value',
  'weighted_pipeline',
  'meetings_scheduled',
  'proposals_pending',
  'active_soft_holds',
  'reservations_pending',
  'deposits_pending',
  'under_contract',
  'won_this_month',
  'lost_this_month',
];

function kpiValue(key: SalesKpiKey, kpis: SalesHomeKpis | null, locale: string): string {
  if (!kpis) return '…';
  switch (key) {
    case 'pipeline_value':
      return formatCurrencyTotals(kpis.pipeline_value_by_currency, locale);
    case 'weighted_pipeline':
      return formatCurrencyTotals(kpis.weighted_pipeline_by_currency, locale);
    default:
      return String(kpis[key]);
  }
}

export function SalesKpiRow({
  kpis,
  loading,
  activeKpi,
  labels,
  locale,
  onKpiClick,
}: SalesKpiRowProps) {
  return (
    <section className="sales__stats" aria-label="Sales KPIs">
      {KPI_ORDER.map((key) => (
        <button
          key={key}
          type="button"
          className={`sales__kpi-button${activeKpi === key ? ' sales__kpi-button--active' : ''}`}
          onClick={() => onKpiClick(key)}
          disabled={loading}
        >
          <KpiCard
            label={labels[key]}
            value={loading ? '…' : kpiValue(key, kpis, locale)}
            className="sales__kpi-card"
          />
        </button>
      ))}
    </section>
  );
}
