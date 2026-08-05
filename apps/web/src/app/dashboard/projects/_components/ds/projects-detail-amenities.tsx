'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { StatusChip } from '@investhome/ui';

import {
  localizedName,
  type AmenityCategory,
  type AmenityItem,
} from './projects-detail-media-model';

const CATEGORIES: AmenityCategory[] = [
  'schools',
  'universities',
  'metro',
  'bus',
  'hospitals',
  'clinics',
  'shopping',
  'restaurants',
  'coffee',
  'parks',
  'fitness',
  'banks',
  'pharmacies',
  'entertainment',
  'government',
];

export function ProjectsDetailAmenities({
  amenities,
  locale,
}: {
  amenities: AmenityItem[];
  locale: string;
}) {
  const t = useTranslations('projects.detail.twin');
  const [filter, setFilter] = useState<AmenityCategory | 'all'>('all');

  const visibleItems = useMemo(() => {
    const filtered =
      filter === 'all' ? amenities : amenities.filter((item) => item.category === filter);
    return [...filtered].sort(
      (a, b) =>
        CATEGORIES.indexOf(a.category) - CATEGORIES.indexOf(b.category) ||
        a.distanceKm - b.distanceKm,
    );
  }, [amenities, filter]);

  const categoryCounts = useMemo(() => {
    const counts = {} as Record<AmenityCategory, number>;
    for (const cat of CATEGORIES) counts[cat] = 0;
    for (const item of amenities) counts[item.category] += 1;
    return counts;
  }, [amenities]);

  return (
    <section className="proj-detail-ds__twin-section" aria-label={t('amenities.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('amenities.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('amenities.subtitle')}</p>
        </div>
        <StatusChip tone="info">{t('amenities.count', { count: amenities.length })}</StatusChip>
      </header>

      <div className="proj-detail-ds__gallery-filters" role="tablist" aria-label={t('amenities.filters')}>
        <button
          type="button"
          className={`proj-detail-ds__gallery-filter${filter === 'all' ? ' is-active' : ''}`}
          onClick={() => setFilter('all')}
        >
          {t('amenities.all')}
        </button>
        {CATEGORIES.filter((cat) => categoryCounts[cat] > 0).map((cat) => (
          <button
            key={cat}
            type="button"
            className={`proj-detail-ds__gallery-filter${filter === cat ? ' is-active' : ''}`}
            onClick={() => setFilter(cat)}
          >
            {t(`amenities.categories.${cat}`)}
          </button>
        ))}
      </div>

      <div className="proj-detail-ds__amenity-grid">
        {visibleItems.map((item) => (
          <article key={item.id} className="proj-detail-ds__amenity-card">
            <div className="proj-detail-ds__amenity-card-top">
              <StatusChip tone="default">{t(`amenities.categories.${item.category}`)}</StatusChip>
              {item.rating != null ? (
                <StatusChip tone="success">
                  {t('amenities.rating', { rating: item.rating.toFixed(1) })}
                </StatusChip>
              ) : null}
            </div>
            <strong>{localizedName(item, locale)}</strong>
            <div className="proj-detail-ds__amenity-meta">
              <span>{t('amenities.distance', { km: item.distanceKm.toFixed(1) })}</span>
              <span>{t('amenities.walk', { min: item.walkMin })}</span>
              <span>{t('amenities.drive', { min: item.driveMin })}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
