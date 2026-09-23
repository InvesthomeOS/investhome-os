'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { Fragment } from 'react';

import type { CrmUnitHistoryStep } from '@/workspaces/crm/api/agreements';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';

type Step = Pick<CrmUnitHistoryStep, 'agreement_id' | 'unit_number' | 'is_current' | 'contact_id'>;

function stepHref(step: Step, personId: string) {
  return salesDetailUrl(step.contact_id || personId, step.agreement_id);
}

function splitSteps(steps: Step[]) {
  return {
    historical: steps.filter((step) => !step.is_current),
    current: steps.find((step) => step.is_current),
  };
}

function UnitHistoryTrail({
  steps,
  personId,
  viewingAgreementId,
  labeled,
}: {
  steps: Step[];
  personId?: string;
  viewingAgreementId?: string;
  labeled: boolean;
}) {
  const { historical, current } = splitSteps(steps);
  if (!historical.length || !current) return null;
  const previousLabel = historical.length === 1 ? 'Önceki Daire' : 'Önceki Daireler';

  return (
    <span className="crm-unit-history__trail">
      <span>
        {labeled ? `${previousLabel}: ` : null}
        {historical.map((step, index) => (
          <Fragment key={step.agreement_id}>
            {index > 0 ? ', ' : null}
            {personId ? (
              <UnitHistoryUnit step={step} personId={personId} viewingAgreementId={viewingAgreementId} />
            ) : (
              <span>{step.unit_number}</span>
            )}
          </Fragment>
        ))}
      </span>
      <span className="crm-unit-history__arrow" aria-hidden>
        →
      </span>
      <span className="crm-unit-history__current">
        {labeled ? 'Güncel Daire: ' : null}
        {personId ? (
          <UnitHistoryUnit step={current} personId={personId} viewingAgreementId={viewingAgreementId} />
        ) : (
          <span className="is-current">{current.unit_number}</span>
        )}
      </span>
    </span>
  );
}

export function UnitHistorySection({
  steps,
  personId,
  viewingAgreementId,
}: {
  steps?: Step[] | null;
  personId: string;
  viewingAgreementId?: string;
}) {
  if (!steps || steps.length < 2) return null;

  return (
    <section className="crm-unit-history" data-testid="unit-history">
      <h2>DAİRE GEÇMİŞİ</h2>
      <p className="crm-unit-history__trail-wrap">
        <UnitHistoryTrail steps={steps} personId={personId} viewingAgreementId={viewingAgreementId} labeled />
      </p>
    </section>
  );
}

function UnitHistoryUnit({
  step,
  personId,
  viewingAgreementId,
}: {
  step: Step;
  personId: string;
  viewingAgreementId?: string;
}) {
  const isViewing = step.agreement_id === viewingAgreementId;
  const className = step.is_current ? 'crm-unit-history__unit is-current' : 'crm-unit-history__unit';
  if (step.is_current && isViewing) {
    return <strong className={className}>{step.unit_number}</strong>;
  }
  if (isViewing) {
    return <span className={className}>{step.unit_number}</span>;
  }
  return (
    <Link className={className} href={stepHref(step, personId) as Route}>
      {step.unit_number}
    </Link>
  );
}

export function UnitHistoryInline({ steps }: { steps?: Step[] | null }) {
  if (!steps || steps.length < 2) return null;
  return (
    <span className="crm-purchase-list__unit-history">
      <UnitHistoryTrail steps={steps} labeled={false} />
    </span>
  );
}
