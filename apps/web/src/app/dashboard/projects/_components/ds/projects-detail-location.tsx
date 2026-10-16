'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import {
  LOCATION_MAP_CATEGORIES,
  nearbyPlacesForCategory,
} from '@/lib/projects/project-location-map';

import type {
  LocationIntelligence,
  NearbyPlace,
  WalkScoreItem,
  WalkScoreKind,
} from './projects-detail-media-model';
import { ProjectsDetailLocationMap } from './projects-detail-location-map';

function scoreTone(score: number) {
  if (score >= 90) return 'success' as const;
  if (score >= 70) return 'info' as const;
  if (score >= 50) return 'warning' as const;
  return 'default' as const;
}

function iconFor(kind: WalkScoreKind) {
  switch (kind) {
    case 'walk':
      return 'home' as const;
    case 'transit':
      return 'activity' as const;
    case 'bike':
      return 'trendingUp' as const;
  }
}

export function ProjectsDetailLocation({
  location,
  walkScores,
  locale,
  onRefresh,
  refreshState,
  refreshError,
}: {
  location: LocationIntelligence;
  walkScores: WalkScoreItem[];
  locale: string;
  onRefresh: () => void;
  refreshState?: string | null;
  refreshError?: string | null;
}) {
  const t = useTranslations('projects.detail.twin');
  const tEmpty = useTranslations('projects.detail.empty');
  const neighborhood = locale === 'tr' ? location.neighborhoodTr : location.neighborhoodEn;
  const address = locale === 'tr' ? location.addressTr : location.addressEn;
  const hasCoordinates = location.lat != null && location.lng != null;
  const [category, setCategory] = useState('all');
  const visiblePlaces = useMemo(
    () => nearbyPlacesForCategory(location.nearbyPlaces, category) as NearbyPlace[],
    [category, location.nearbyPlaces],
  );
  const refreshLabel =
    refreshState === 'working' ||
    refreshState === 'queued' ||
    refreshState === 'already_queued' ||
    refreshState === 'disabled' ||
    refreshState === 'error'
      ? t(`location.refreshState.${refreshState}`)
      : null;
  const refreshBusy =
    refreshState === 'working' || refreshState === 'queued' || refreshState === 'already_queued';

  return (
    <section className="proj-detail-ds__twin-section" aria-label={t('location.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('location.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('location.subtitle')}</p>
        </div>
        <div className="proj-detail-ds__twin-head-actions">
          {neighborhood ? <StatusChip tone="info">{neighborhood}</StatusChip> : null}
          {location.canRefresh ? (
            <button
              type="button"
              data-testid="project-location-refresh"
              className="proj-detail-ds__gallery-filter proj-detail-ds__location-refresh"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onRefresh();
              }}
              disabled={refreshBusy}
            >
              {t('location.refresh')}
            </button>
          ) : null}
        </div>
      </header>
      {refreshLabel ? (
        <p className="proj-detail-ds__panel-sub" role="status">
          {refreshLabel}
        </p>
      ) : null}
      {refreshError ? (
        <p className="proj-detail-ds__banner" role="alert">
          {refreshError}
        </p>
      ) : null}
      {location.refreshedAt ? (
        <p className="proj-detail-ds__panel-sub">
          {t('location.refreshedAt', { time: location.refreshedAt.slice(0, 16).replace('T', ' ') })}
        </p>
      ) : null}
      {!hasCoordinates ? <p className="proj-detail-ds__banner">{tEmpty('location')}</p> : null}

      <div className="proj-detail-ds__location-grid">
        {hasCoordinates ? (
          <div className="proj-detail-ds__map-column">
            <div className="proj-detail-ds__gallery-filters" role="tablist" aria-label={t('location.mapFilters')}>
              <button
                type="button"
                className={`proj-detail-ds__gallery-filter${category === 'all' ? ' is-active' : ''}`}
                data-testid="project-location-map-filter"
                data-category="all"
                aria-pressed={category === 'all'}
                onClick={() => setCategory('all')}
              >
                {t('location.categories.all')}
              </button>
              {LOCATION_MAP_CATEGORIES.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`proj-detail-ds__gallery-filter${category === item ? ' is-active' : ''}`}
                  data-testid="project-location-map-filter"
                  data-category={item}
                  aria-pressed={category === item}
                  onClick={() => setCategory(item)}
                >
                  {t(`location.categories.${item}`)}
                </button>
              ))}
            </div>
            <ProjectsDetailLocationMap location={location} locale={locale} category={category} />
          </div>
        ) : null}

        <div className="proj-detail-ds__location-side">
          <article className="proj-detail-ds__panel proj-detail-ds__location-card">
            <h4>{t('location.neighborhood')}</h4>
            <p className="proj-detail-ds__panel-sub">{neighborhood || tEmpty('neighborhood')}</p>
            {location.aiSummary ? (
              <p className="proj-detail-ds__panel-sub">
                <strong>{t('location.aiAnalysis')}</strong> {location.aiSummary}
              </p>
            ) : null}
            <div className="proj-detail-ds__kv">
              {address ? (
              <div className="proj-detail-ds__kv-row">
                <span>{t('location.address')}</span>
                <strong>{address}</strong>
              </div>
              ) : null}
              {hasCoordinates ? (
              <div className="proj-detail-ds__kv-row">
                <span>{t('location.coordinates')}</span>
                <strong>
                  {location.lat?.toFixed(5)}, {location.lng?.toFixed(5)}
                </strong>
              </div>
              ) : null}
            </div>
          </article>

          <article className="proj-detail-ds__panel proj-detail-ds__location-card">
            <h4>{t('location.radii')}</h4>
            {location.radii.length === 0 && !hasCoordinates ? (
              <p className="proj-detail-ds__panel-sub">{tEmpty('location')}</p>
            ) : null}
            <div className="proj-detail-ds__radius-row">
              {location.radii.map((r) => (
                <div key={r.id} className="proj-detail-ds__radius-chip">
                  <IhIcon name={r.mode === 'walk' ? 'home' : 'activity'} size={12} />
                  <span>
                    {t(`location.radius.${r.mode}`, { minutes: r.minutes })}
                  </span>
                </div>
              ))}
            </div>
          </article>

          <article className="proj-detail-ds__panel proj-detail-ds__location-card">
            <h4>{t('location.nearby')}</h4>
            {visiblePlaces.length === 0 ? (
              <p className="proj-detail-ds__panel-sub">{tEmpty('nearby')}</p>
            ) : null}
            <ul className="proj-detail-ds__list">
              {visiblePlaces.map((place) => (
                <li key={place.id}>
                  <strong>{locale === 'tr' ? place.nameTr : place.nameEn}</strong>
                  <span>
                    {t(`location.categories.${place.kindEn}`)} ·{' '}
                    {t('amenities.distance', { km: place.distanceKm.toFixed(1) })}
                  </span>
                  {place.address ? <span>{place.address}</span> : null}
                </li>
              ))}
            </ul>
          </article>
        </div>
      </div>

      {walkScores.length === 0 ? <p className="proj-detail-ds__banner">{tEmpty('scores')}</p> : null}
      <div className="proj-detail-ds__walk-grid" aria-label={t('walkScore.aria')}>
        {walkScores.map((item) => (
          <article key={item.kind} className="proj-detail-ds__walk-card">
            <div className="proj-detail-ds__walk-top">
              <span className="proj-detail-ds__walk-icon" aria-hidden="true">
                <IhIcon name={iconFor(item.kind)} size={16} />
              </span>
              <div>
                <em>{t(`walkScore.kinds.${item.kind}`)}</em>
                <strong className="proj-detail-ds__walk-score">{item.score}</strong>
              </div>
              <StatusChip tone={scoreTone(item.score)}>
                {t(`walkScore.badges.${item.badge}`)}
              </StatusChip>
            </div>
            <p className="proj-detail-ds__panel-sub">
              {locale === 'tr' ? item.descriptionTr : item.descriptionEn}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
