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
  const tEmpty = useTranslations('projects.detail.empty');
  const [active, setActive] = useState<FloorPlanItem | null>(null);

  return (
    <section className="proj-detail-ds__twin-section" aria-label={t('floorPlans.aria')}>
      <header className="proj-detail-ds__twin-head">
        <div>
          <h3>{t('floorPlans.title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('floorPlans.subtitle')}</p>
        </div>
        {plans.length > 0 ? (
          <StatusChip tone="info">{t('floorPlans.count', { count: plans.length })}</StatusChip>
        ) : null}
      </header>
      {plans.length === 0 ? <p className="proj-detail-ds__banner">{tEmpty('floorPlans')}</p> : null}

      <div className="proj-detail-ds__fp-grid">
        {plans.map((plan) => (
          <article key={plan.id} className="proj-detail-ds__fp-card">
            <button
              type="button"
              className="proj-detail-ds__fp-preview"
              onClick={() => setActive(plan)}
              aria-label={t('floorPlans.open', { type: plan.label })}
            >
              <div
                className="proj-detail-ds__media-frame is-plan"
                aria-hidden="true"
              >
                {plan.imageUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={plan.imageUrl} alt="" />
                ) : (
                  <span className="proj-detail-ds__plan-lines" />
                )}
              </div>
            </button>
            <div className="proj-detail-ds__fp-body">
              <strong>{plan.label}</strong>
              {plan.areaSqm != null && plan.unitCount != null ? (
                <span>
                  {t('floorPlans.area', { area: plan.areaSqm })} ·{' '}
                  {t('floorPlans.units', { count: plan.unitCount })}
                </span>
              ) : null}
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
        title={active ? active.label : t('floorPlans.title')}
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
              className="proj-detail-ds__media-frame is-lightbox is-plan"
              aria-hidden="true"
            >
              {active.imageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={active.imageUrl} alt="" />
              ) : (
                <span className="proj-detail-ds__plan-lines" />
              )}
            </div>
            <div className="proj-detail-ds__lightbox-meta">
              {active.areaSqm != null ? <p>{t('floorPlans.area', { area: active.areaSqm })}</p> : null}
              {active.unitCount != null ? <p>{t('floorPlans.units', { count: active.unitCount })}</p> : null}
              <p>{active.label}</p>
            </div>
          </div>
        ) : null}
      </Dialog>
    </section>
  );
}
