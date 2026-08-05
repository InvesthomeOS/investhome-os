'use client';

import { useTranslations } from 'next-intl';
import { StatusChip } from '@investhome/ui';

import { formatShortDate } from '@/lib/api/projects';
import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import type { MediaStats } from './projects-detail-media-model';

const STAT_KEYS = [
  'photos',
  'videos',
  'drone',
  'renderings',
  'floorPlans',
  'documents',
] as const;

type StatKey = (typeof STAT_KEYS)[number];

const ICONS: Record<StatKey, IhIconName> = {
  photos: 'projects',
  videos: 'activity',
  drone: 'trendingUp',
  renderings: 'sparkles',
  floorPlans: 'documents',
  documents: 'inbox',
};

export function ProjectsDetailMediaStats({
  stats,
  locale,
}: {
  stats: MediaStats;
  locale: string;
}) {
  const t = useTranslations('projects.detail.twin');

  return (
    <section className="proj-detail-ds__twin-section proj-detail-ds__twin-section--compact" aria-label={t('mediaStats.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('mediaStats.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('mediaStats.subtitle')}</p>
        </div>
        <StatusChip tone="info">
          {t('mediaStats.updated', { date: formatShortDate(stats.lastUpdated, locale) })}
        </StatusChip>
      </header>

      <div className="proj-detail-ds__media-stats">
        {STAT_KEYS.map((key) => (
          <div key={key} className="proj-detail-ds__media-stat">
            <span className="proj-detail-ds__media-stat-icon" aria-hidden="true">
              <IhIcon name={ICONS[key]} size={14} />
            </span>
            <div>
              <em>{t(`mediaStats.keys.${key}`)}</em>
              <strong>{stats[key]}</strong>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
