'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button, Dialog, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import type { FloorPlanItem } from './projects-detail-media-model';

export function ProjectsDetailFloorPlans({
  plans,
}: {
  plans: FloorPlanItem[];
  locale: string;
}) {
  const t = useTranslations('projects.detail.twin');
  const [active, setActive] = useState<FloorPlanItem | null>(null);

  return (
    <section className="proj-detail-ds__twin-section" aria-label={t('floorPlans.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('floorPlans.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('floorPlans.subtitle')}</p>
        </div>
        <StatusChip tone="info">{t('floorPlans.count', { count: plans.length })}</StatusChip>
      </header>

      <div className="proj-detail-ds__fp-grid">
        {plans.map((plan) => (
          <article key={plan.id} className="proj-detail-ds__fp-card">
            <button
              type="button"
              className="proj-detail-ds__fp-preview"
              onClick={() => setActive(plan)}
              aria-label={t('floorPlans.open', { type: t(`floorPlans.types.${plan.type}`) })}
            >
              <div
                className={`proj-detail-ds__media-frame is-plan is-${plan.scene} accent-${plan.accent}`}
                aria-hidden="true"
              >
                <span className="proj-detail-ds__plan-lines" />
              </div>
            </button>
            <div className="proj-detail-ds__fp-body">
              <strong>{t(`floorPlans.types.${plan.type}`)}</strong>
              <span>
                {t('floorPlans.area', { area: plan.areaSqm })} ·{' '}
                {t('floorPlans.units', { count: plan.unitCount })}
              </span>
              <div className="proj-detail-ds__fp-actions">
                <Button variant="secondary" size="sm" type="button" onClick={() => setActive(plan)}>
                  <IhIcon name="search" size={12} />
                  {t('floorPlans.preview')}
                </Button>
                <a className="proj-detail-ds__fp-pdf" href={plan.pdfUrl}>
                  <IhIcon name="inbox" size={12} />
                  {t('floorPlans.pdf')}
                </a>
              </div>
            </div>
          </article>
        ))}
      </div>

      <Dialog
        open={Boolean(active)}
        onClose={() => setActive(null)}
        title={active ? t(`floorPlans.types.${active.type}`) : t('floorPlans.title')}
        footer={
          active ? (
            <a className="proj-detail-ds__fp-pdf is-primary" href={active.pdfUrl}>
              {t('floorPlans.downloadPdf')}
            </a>
          ) : null
        }
      >
        {active ? (
          <div className="proj-detail-ds__lightbox">
            <div
              className={`proj-detail-ds__media-frame is-lightbox is-plan is-${active.scene} accent-${active.accent}`}
              aria-hidden="true"
            >
              <span className="proj-detail-ds__plan-lines" />
            </div>
            <div className="proj-detail-ds__lightbox-meta">
              <p>{t('floorPlans.area', { area: active.areaSqm })}</p>
              <p>{t('floorPlans.units', { count: active.unitCount })}</p>
            </div>
          </div>
        ) : null}
      </Dialog>
    </section>
  );
}
