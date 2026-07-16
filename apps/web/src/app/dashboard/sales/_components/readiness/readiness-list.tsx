'use client';

import { StatusChip } from '@investhome/ui';
import { useTranslations } from 'next-intl';

import type { ReadinessCase } from '@/lib/api/sales-readiness';
import { useReadinessLabels } from '@/lib/i18n/sales-readiness-labels';

interface ReadinessListProps {
  items: ReadinessCase[];
  selectedId: string | null;
  onSelect: (item: ReadinessCase) => void;
}

export function ReadinessList({ items, selectedId, onSelect }: ReadinessListProps) {
  const t = useTranslations('salesReadiness');
  const { getStatusLabel } = useReadinessLabels();

  if (items.length === 0) {
    return (
      <div className="sales-readiness-empty">
        <h3>{t('empty.title')}</h3>
        <p>{t('empty.description')}</p>
      </div>
    );
  }

  return (
    <div className="sales-readiness-list" role="table">
      <div className="sales-readiness-list__header" role="row">
        <span role="columnheader">{t('columns.opportunity')}</span>
        <span role="columnheader">{t('columns.party')}</span>
        <span role="columnheader">{t('columns.asset')}</span>
        <span role="columnheader">{t('columns.percentage')}</span>
        <span role="columnheader">{t('columns.status')}</span>
        <span role="columnheader">{t('columns.blocker')}</span>
      </div>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="row"
          className={`sales-readiness-list__row${selectedId === item.id ? ' sales-readiness-list__row--selected' : ''}`}
          onClick={() => onSelect(item)}
        >
          <span role="cell">{item.opportunity_code ?? item.case_code}</span>
          <span role="cell">{item.party_name ?? '—'}</span>
          <span role="cell">{item.inventory_display_id ?? '—'}</span>
          <span role="cell">{item.readiness_percentage}%</span>
          <span role="cell">
            <StatusChip tone={item.status === 'blocked' ? 'warning' : 'default'}>
              {getStatusLabel(item.status)}
            </StatusChip>
          </span>
          <span role="cell">{item.blocker_summary ?? '—'}</span>
        </button>
      ))}
    </div>
  );
}
