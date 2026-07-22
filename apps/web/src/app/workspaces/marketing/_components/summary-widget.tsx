'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';

type SummaryWidgetProps = {
  title: string;
  state: 'loading' | 'empty' | 'error' | 'no_data' | 'not_calculated' | 'permission_restricted' | 'ready';
  value?: ReactNode;
  children?: ReactNode;
};

export function SummaryWidget({ title, state, value, children }: SummaryWidgetProps) {
  const t = useTranslations('marketing.common');

  return (
    <div className="marketing-summary-widget">
      <h3 className="marketing-summary-widget__title">{title}</h3>
      {state === 'loading' && <LoadingState label={t('loading')} />}
      {state === 'error' && <ErrorState title={t('error')} message={t('error')} />}
      {state === 'permission_restricted' && (
        <EmptyState title={t('permissionRestricted')} description={t('permissionRestrictedDescription')} />
      )}
      {state === 'empty' && <EmptyState title={t('empty')} description={t('empty')} />}
      {state === 'no_data' && <EmptyState title={t('noData')} description={t('noData')} />}
      {state === 'not_calculated' && <span className="marketing-summary-widget__not-calculated">{t('notCalculated')}</span>}
      {state === 'ready' && (children ?? <span className="marketing-summary-widget__value">{value ?? '—'}</span>)}
    </div>
  );
}

type UnavailableValueProps = {
  label: string;
};

export function UnavailableValue({ label }: UnavailableValueProps) {
  return <span className="marketing-unavailable">{label}</span>;
}
