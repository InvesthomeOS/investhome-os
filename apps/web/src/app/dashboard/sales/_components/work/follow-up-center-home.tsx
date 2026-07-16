'use client';

import { KpiCard } from '@investhome/ui';
import { useTranslations } from 'next-intl';

import type { WorkDashboardKpis } from '@/lib/api/work-items';

interface FollowUpCenterHomeProps {
  kpis: WorkDashboardKpis | null;
  loading: boolean;
  activeView: string | null;
  onSelectView: (view: string) => void;
}

const KPI_VIEWS: Array<{ key: keyof WorkDashboardKpis; view: string; labelKey: string }> = [
  { key: 'today_count', view: 'today', labelKey: 'kpis.today' },
  { key: 'overdue_count', view: 'overdue', labelKey: 'kpis.overdue' },
  { key: 'meetings_today_count', view: 'meetings', labelKey: 'kpis.meetingsToday' },
  { key: 'blocked_count', view: 'blocked', labelKey: 'kpis.blocked' },
  { key: 'waiting_count', view: 'waiting', labelKey: 'kpis.waiting' },
  { key: 'my_work_count', view: 'my_work', labelKey: 'kpis.myWork' },
  { key: 'no_next_action_count', view: 'overdue', labelKey: 'kpis.noNextAction' },
];

export function FollowUpCenterHome({ kpis, loading, activeView, onSelectView }: FollowUpCenterHomeProps) {
  const t = useTranslations('work');

  return (
    <div className="sales-work-kpis">
      {KPI_VIEWS.map(({ key, view, labelKey }) => (
        <button
          key={key}
          type="button"
          className={`sales-work-kpis__card${activeView === view ? ' sales-work-kpis__card--active' : ''}`}
          onClick={() => onSelectView(view)}
        >
          <KpiCard
            label={t(labelKey as never)}
            value={loading ? '—' : String(kpis?.[key] ?? 0)}
          />
        </button>
      ))}
    </div>
  );
}
