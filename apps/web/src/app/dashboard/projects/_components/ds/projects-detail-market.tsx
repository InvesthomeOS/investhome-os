'use client';

import { useTranslations } from 'next-intl';
import { KpiCard } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  localizedValue,
  type MarketIntelligence,
  type MarketMetricKey,
} from './projects-detail-media-model';

const ICONS: Record<MarketMetricKey, IhIconName> = {
  medianSale: 'barChart',
  medianRent: 'inbox',
  appreciation: 'trendingUp',
  rentalDemand: 'target',
  inventory: 'projects',
  daysOnMarket: 'clock',
  neighborhoodGrowth: 'sparkles',
};

export function ProjectsDetailMarket({
  market,
  locale,
}: {
  market: MarketIntelligence;
  locale: string;
}) {
  const t = useTranslations('projects.detail.twin');

  return (
    <section className="proj-detail-ds__twin-section" aria-label={t('market.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('market.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('market.subtitle')}</p>
        </div>
      </header>

      <div className="proj-detail-ds__market-grid">
        {market.metrics.map((metric) => (
          <KpiCard
            key={metric.key}
            className="proj-detail-ds__kpi proj-detail-ds__market-kpi"
            label={t(`market.metrics.${metric.key}`)}
            value={localizedValue(metric, locale)}
            hint={t(`market.hints.${metric.key}`)}
            {...(metric.delta ? { delta: metric.delta } : {})}
            {...(metric.deltaTone ? { deltaTone: metric.deltaTone } : {})}
            icon={<IhIcon name={ICONS[metric.key]} size={16} />}
          />
        ))}
      </div>
    </section>
  );
}
