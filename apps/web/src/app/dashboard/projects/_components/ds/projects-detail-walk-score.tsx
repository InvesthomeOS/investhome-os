'use client';

import { useTranslations } from 'next-intl';
import { StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import type { WalkScoreItem, WalkScoreKind } from './projects-detail-media-model';

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

export function ProjectsDetailWalkScore({
  scores,
  locale,
}: {
  scores: WalkScoreItem[];
  locale: string;
}) {
  const t = useTranslations('projects.detail.twin');

  return (
    <section className="proj-detail-ds__twin-section proj-detail-ds__twin-section--compact" aria-label={t('walkScore.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('walkScore.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('walkScore.subtitle')}</p>
        </div>
      </header>

      <div className="proj-detail-ds__walk-grid">
        {scores.map((item) => (
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
