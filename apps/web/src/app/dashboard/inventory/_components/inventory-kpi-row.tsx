'use client';

import { KpiCard } from '@investhome/ui';

import type { InventoryKpis } from '@/lib/api/inventory';

export type InventoryKpiKey =
  | 'total'
  | 'available'
  | 'soft_hold'
  | 'reserved'
  | 'under_contract'
  | 'sold'
  | 'closed'
  | 'leased';

interface InventoryKpiRowProps {
  kpis: InventoryKpis | null;
  loading: boolean;
  activeKpi: InventoryKpiKey | null;
  labels: Record<InventoryKpiKey, string>;
  onKpiClick: (key: InventoryKpiKey) => void;
}

const KPI_ORDER: InventoryKpiKey[] = [
  'total',
  'available',
  'soft_hold',
  'reserved',
  'under_contract',
  'sold',
  'closed',
  'leased',
];

export function InventoryKpiRow({
  kpis,
  loading,
  activeKpi,
  labels,
  onKpiClick,
}: InventoryKpiRowProps) {
  return (
    <section className="inventory__stats" aria-label="Inventory KPIs">
      {KPI_ORDER.map((key) => (
        <button
          key={key}
          type="button"
          className={`inventory__kpi-button${activeKpi === key ? ' inventory__kpi-button--active' : ''}`}
          onClick={() => onKpiClick(key)}
          disabled={loading}
        >
          <KpiCard
            label={labels[key]}
            value={loading || !kpis ? '…' : kpis[key]}
            className="inventory__kpi-card"
          />
        </button>
      ))}
    </section>
  );
}
