'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Dialog, StatusChip } from '@investhome/ui';

import { formatShortDate } from '@/lib/api/projects';

import {
  localizedTitle,
  type GalleryCategory,
  type ProjectGalleryItem,
} from './projects-detail-media-model';

const CATEGORIES: GalleryCategory[] = [
  'cover',
  'exterior',
  'interior',
  'drone',
  'street',
  'marketing',
  'construction',
];

export function ProjectsDetailGallery({
  items,
  locale,
}: {
  items: ProjectGalleryItem[];
  locale: string;
}) {
  const t = useTranslations('projects.detail.twin');
  const [filter, setFilter] = useState<GalleryCategory | 'all'>('all');
  const [active, setActive] = useState<ProjectGalleryItem | null>(null);

  const filtered = filter === 'all' ? items : items.filter((i) => i.category === filter);
  const counts = CATEGORIES.reduce(
    (acc, cat) => {
      acc[cat] = items.filter((i) => i.category === cat).length;
      return acc;
    },
    {} as Record<GalleryCategory, number>,
  );

  return (
    <section className="proj-detail-ds__twin-section" aria-label={t('gallery.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('gallery.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('gallery.subtitle')}</p>
        </div>
        <StatusChip tone="info">
          {t('gallery.count', { count: items.length })}
        </StatusChip>
      </header>

      <div className="proj-detail-ds__gallery-filters" role="tablist" aria-label={t('gallery.filters')}>
        <button
          type="button"
          className={`proj-detail-ds__gallery-filter${filter === 'all' ? ' is-active' : ''}`}
          onClick={() => setFilter('all')}
        >
          {t('gallery.all')} · {items.length}
        </button>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`proj-detail-ds__gallery-filter${filter === cat ? ' is-active' : ''}`}
            onClick={() => setFilter(cat)}
          >
            {t(`gallery.categories.${cat}`)} · {counts[cat]}
          </button>
        ))}
      </div>

      <div className="proj-detail-ds__gallery-grid">
        {filtered.map((item) => (
          <button
            key={item.id}
            type="button"
            className="proj-detail-ds__gallery-card"
            onClick={() => setActive(item)}
          >
            <div
              className={`proj-detail-ds__media-frame is-${item.scene} accent-${item.accent}`}
              aria-hidden="true"
            >
              <i />
              <i />
              <i />
            </div>
            <div className="proj-detail-ds__gallery-meta">
              <strong>{localizedTitle(item, locale)}</strong>
              <span>
                {t(`gallery.categories.${item.category}`)} ·{' '}
                {formatShortDate(item.uploadedAt, locale)}
              </span>
              <em>
                {item.photographer} · {item.source}
              </em>
            </div>
          </button>
        ))}
      </div>

      <Dialog
        open={Boolean(active)}
        onClose={() => setActive(null)}
        title={active ? localizedTitle(active, locale) : t('gallery.title')}
      >
        {active ? (
          <div className="proj-detail-ds__lightbox">
            <div
              className={`proj-detail-ds__media-frame is-lightbox is-${active.scene} accent-${active.accent}`}
              aria-hidden="true"
            >
              <i />
              <i />
              <i />
            </div>
            <div className="proj-detail-ds__lightbox-meta">
              <StatusChip tone="info">{t(`gallery.categories.${active.category}`)}</StatusChip>
              <p>
                {t('gallery.uploaded')}: {formatShortDate(active.uploadedAt, locale)}
              </p>
              <p>
                {t('gallery.photographer')}: {active.photographer}
              </p>
              <p>
                {t('gallery.source')}: {active.source}
              </p>
            </div>
          </div>
        ) : null}
      </Dialog>
    </section>
  );
}
