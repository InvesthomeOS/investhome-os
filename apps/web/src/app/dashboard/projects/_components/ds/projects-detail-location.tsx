'use client';

import { useTranslations } from 'next-intl';
import { StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import type {
  LocationIntelligence,
  WalkScoreItem,
  WalkScoreKind,
} from './projects-detail-media-model';

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
}: {
  location: LocationIntelligence;
  walkScores: WalkScoreItem[];
  locale: string;
}) {
  const t = useTranslations('projects.detail.twin');
  const neighborhood = locale === 'tr' ? location.neighborhoodTr : location.neighborhoodEn;
  const address = locale === 'tr' ? location.addressTr : location.addressEn;
  const overview = locale === 'tr' ? location.overviewTr : location.overviewEn;

  return (
    <section className="proj-detail-ds__twin-section" aria-label={t('location.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('location.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('location.subtitle')}</p>
        </div>
        <StatusChip tone="info">{neighborhood}</StatusChip>
      </header>

      <div className="proj-detail-ds__location-grid">
        <div className="proj-detail-ds__map" role="img" aria-label={t('location.mapAria')}>
          <div className="proj-detail-ds__map-grid" aria-hidden="true" />
          <div className="proj-detail-ds__map-rings" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div className="proj-detail-ds__map-pin" aria-hidden="true">
            <IhIcon name="projects" size={14} />
          </div>
          <div className="proj-detail-ds__map-coords">
            {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
          </div>
        </div>

        <div className="proj-detail-ds__location-side">
          <article className="proj-detail-ds__panel proj-detail-ds__location-card">
            <h4>{t('location.neighborhood')}</h4>
            <p className="proj-detail-ds__panel-sub">{overview}</p>
            <div className="proj-detail-ds__kv">
              <div className="proj-detail-ds__kv-row">
                <span>{t('location.address')}</span>
                <strong>{address}</strong>
              </div>
              <div className="proj-detail-ds__kv-row">
                <span>{t('location.coordinates')}</span>
                <strong>
                  {location.lat.toFixed(5)}, {location.lng.toFixed(5)}
                </strong>
              </div>
            </div>
          </article>

          <article className="proj-detail-ds__panel proj-detail-ds__location-card">
            <h4>{t('location.radii')}</h4>
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
            <ul className="proj-detail-ds__list">
              {location.nearbyPlaces.map((place) => (
                <li key={place.id}>
                  <strong>{locale === 'tr' ? place.nameTr : place.nameEn}</strong>
                  <span>
                    {locale === 'tr' ? place.kindTr : place.kindEn} ·{' '}
                    {t('amenities.distance', { km: place.distanceKm.toFixed(1) })}
                  </span>
                </li>
              ))}
            </ul>
          </article>
        </div>
      </div>

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
