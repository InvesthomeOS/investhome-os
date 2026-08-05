'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Dialog, ProgressBar, StatusChip } from '@investhome/ui';

import { formatShortDate } from '@/lib/api/projects';
import { IhIcon } from '@/components/icons/ih-icons';

import {
  localizedCaption,
  type ConstructionGalleryMilestone,
  type InspectionStatus,
} from './projects-detail-media-model';

function inspectionTone(status: InspectionStatus) {
  switch (status) {
    case 'passed':
      return 'success' as const;
    case 'failed':
      return 'danger' as const;
    case 'scheduled':
      return 'info' as const;
    default:
      return 'warning' as const;
  }
}

export function ProjectsDetailConstructionGallery({
  milestones,
  locale,
}: {
  milestones: ConstructionGalleryMilestone[];
  locale: string;
}) {
  const t = useTranslations('projects.detail.twin');
  const [active, setActive] = useState<{
    milestone: ConstructionGalleryMilestone;
    mediaIndex: number;
  } | null>(null);

  return (
    <section className="proj-detail-ds__twin-section" aria-label={t('constructionGallery.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('constructionGallery.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('constructionGallery.subtitle')}</p>
        </div>
        <StatusChip tone="info">
          {t('constructionGallery.milestones', { count: milestones.length })}
        </StatusChip>
      </header>

      <div className="proj-detail-ds__cg-list">
        {milestones.map((m) => (
          <article key={m.id} className="proj-detail-ds__cg-card">
            <div className="proj-detail-ds__cg-top">
              <div>
                <em className="proj-detail-ds__cg-label">{t('constructionGallery.phase')}</em>
                <h4>{t(`constructionGallery.phases.${m.phase}`)}</h4>
                <p className="proj-detail-ds__panel-sub">{formatShortDate(m.date, locale)}</p>
              </div>
              <StatusChip tone={inspectionTone(m.inspectionStatus)}>
                {t(`constructionGallery.inspection.${m.inspectionStatus}`)}
              </StatusChip>
            </div>
            <div className="proj-detail-ds__cg-facts">
              <div className="proj-detail-ds__cg-fact">
                <em>{t('constructionGallery.progress')}</em>
                <strong>{m.progressPct}%</strong>
              </div>
              <div className="proj-detail-ds__cg-fact">
                <em>{t('constructionGallery.inspectionLabel')}</em>
                <strong>{t(`constructionGallery.inspection.${m.inspectionStatus}`)}</strong>
              </div>
              <div className="proj-detail-ds__cg-fact">
                <em>{t('constructionGallery.contractor')}</em>
                <strong>{m.contractor}</strong>
              </div>
            </div>
            <div className="proj-detail-ds__cg-progress">
              <ProgressBar value={m.progressPct} />
            </div>
            <div className="proj-detail-ds__cg-media">
              {m.media.map((media, idx) => (
                <button
                  key={media.id}
                  type="button"
                  className="proj-detail-ds__cg-thumb"
                  onClick={() => setActive({ milestone: m, mediaIndex: idx })}
                >
                  <div
                    className={`proj-detail-ds__media-frame is-${media.scene} accent-${media.accent}`}
                    aria-hidden="true"
                  >
                    <i />
                    <i />
                  </div>
                  <span>
                    {media.type === 'video' ? (
                      <IhIcon name="activity" size={12} />
                    ) : (
                      <IhIcon name="projects" size={12} />
                    )}
                    {localizedCaption(media, locale)}
                  </span>
                </button>
              ))}
            </div>
          </article>
        ))}
      </div>

      <Dialog
        open={Boolean(active)}
        onClose={() => setActive(null)}
        title={
          active
            ? t(`constructionGallery.phases.${active.milestone.phase}`)
            : t('constructionGallery.title')
        }
      >
        {active ? (
          <div className="proj-detail-ds__lightbox">
            {(() => {
              const media = active.milestone.media[active.mediaIndex]!;
              return (
                <>
                  <div
                    className={`proj-detail-ds__media-frame is-lightbox is-${media.scene} accent-${media.accent}`}
                    aria-hidden="true"
                  >
                    <i />
                    <i />
                    <i />
                  </div>
                  <div className="proj-detail-ds__lightbox-meta">
                    <p>{localizedCaption(media, locale)}</p>
                    <p>
                      {t('constructionGallery.progress')}: {active.milestone.progressPct}%
                    </p>
                    <p>
                      {t('constructionGallery.contractor')}: {active.milestone.contractor}
                    </p>
                    <StatusChip tone={inspectionTone(active.milestone.inspectionStatus)}>
                      {t(`constructionGallery.inspection.${active.milestone.inspectionStatus}`)}
                    </StatusChip>
                  </div>
                </>
              );
            })()}
          </div>
        ) : null}
      </Dialog>
    </section>
  );
}
