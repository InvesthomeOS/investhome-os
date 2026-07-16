'use client';

import { KpiCard } from '@investhome/ui';
import { useTranslations } from 'next-intl';

import type { ReadinessDashboardKpis, ReadinessViewName } from '@/lib/api/sales-readiness';

interface ReadinessHomeProps {
  kpis: ReadinessDashboardKpis | null;
  loading: boolean;
  activeView: ReadinessViewName | null;
  onSelectView: (view: ReadinessViewName) => void;
}

const KPI_CONFIG: Array<{ key: keyof ReadinessDashboardKpis; view: ReadinessViewName; labelKey: string }> = [
  { key: 'active_cases', view: 'overview', labelKey: 'kpis.activeCases' },
  { key: 'blocked', view: 'blocked', labelKey: 'kpis.blocked' },
  { key: 'reservation_approved', view: 'overview', labelKey: 'kpis.reservationApproved' },
  { key: 'deposit_pending', view: 'deposit_pending', labelKey: 'kpis.depositPending' },
  { key: 'deposit_received', view: 'overview', labelKey: 'kpis.depositReceived' },
  { key: 'documents_missing', view: 'documents_missing', labelKey: 'kpis.documentsMissing' },
  { key: 'contract_preparation', view: 'in_progress', labelKey: 'kpis.contractPreparation' },
  { key: 'signature_pending', view: 'signature_pending', labelKey: 'kpis.signaturePending' },
  { key: 'ready_for_handoff', view: 'ready_for_handoff', labelKey: 'kpis.readyForHandoff' },
  { key: 'handed_off_this_month', view: 'handed_off', labelKey: 'kpis.handedOffThisMonth' },
];

export function ReadinessHome({ kpis, loading, activeView, onSelectView }: ReadinessHomeProps) {
  const t = useTranslations('salesReadiness');

  return (
    <div className="sales-work-kpis">
      {KPI_CONFIG.map(({ key, view, labelKey }) => (
        <button
          key={key}
          type="button"
          className={`sales-work-kpis__card${activeView === view ? ' sales-work-kpis__card--active' : ''}`}
          onClick={() => onSelectView(view)}
        >
          <KpiCard label={t(labelKey as never)} value={loading ? '—' : String(kpis?.[key] ?? 0)} />
        </button>
      ))}
    </div>
  );
}
