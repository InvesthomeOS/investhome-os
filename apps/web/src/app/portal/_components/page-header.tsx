'use client';

import { useTranslations } from 'next-intl';

import type { DataClass } from '../_data/types';
import { DataBadge } from './data-badge';

export function PageHeader({
  title,
  subtitle,
  classification = 'DEMO',
}: {
  title: string;
  subtitle: string;
  classification?: DataClass;
}) {
  const t = useTranslations('portalG9');
  return (
    <header className="portal-page__head">
      <div>
        <h1 className="portal-page__title">{title}</h1>
        <p className="portal-page__subtitle">{subtitle}</p>
      </div>
      <DataBadge kind={classification} />
      <p className="portal-gap" style={{ flexBasis: '100%', margin: 0 }}>
        {t('gapBanner')}
      </p>
    </header>
  );
}
