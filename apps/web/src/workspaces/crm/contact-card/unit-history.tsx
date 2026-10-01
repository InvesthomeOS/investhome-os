'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { Fragment } from 'react';

import type { CrmUnitHistoryStep } from '@/workspaces/crm/api/agreements';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';

type Step = Pick<
  CrmUnitHistoryStep,
  'agreement_id' | 'unit_number' | 'is_current' | 'contact_id' | 'project_label'
>;

function stepHref(step: Step, personId: string) {
  return salesDetailUrl(step.contact_id || personId, step.agreement_id);
}

function splitSteps(steps: Step[]) {
  return {
    historical: steps.filter((step) => !step.is_current),
    current: steps.find((step) => step.is_current),
  };
}

function hasProjectChange(steps: Step[]) {
  const labels = [...new Set(steps.map((step) => (step.project_label || '').trim()).filter(Boolean))];
  return labels.length > 1;
}

export function unitChangeText(steps?: Step[] | null): string | null {
  const { historical, current } = splitSteps(steps ?? []);
  if (!historical.length || !current) return null;
  const projectChange = hasProjectChange([current, ...historical]);
  const token = (step: Step) =>
    projectChange && step.project_label ? `${step.project_label} / ${step.unit_number}` : step.unit_number;
  return `${historical.map(token).join(' / ')} → ${token(current)}`;
}

function StepToken({
  step,
  personId,
  viewingAgreementId,
  projectChange,
}: {
  step: Step;
  personId?: string;
  viewingAgreementId?: string;
  projectChange: boolean;
}) {
  return (
    <span className="crm-unit-history__token">
      {projectChange && step.project_label ? (
        <>
          <span>{step.project_label}</span>
          <span> / </span>
        </>
      ) : null}
      {personId ? (
        <UnitHistoryUnit step={step} personId={personId} viewingAgreementId={viewingAgreementId} />
      ) : (
        <span className={step.is_current ? 'is-current' : undefined}>{step.unit_number}</span>
      )}
    </span>
  );
}

function UnitHistoryTrail({
  steps,
  personId,
  viewingAgreementId,
}: {
  steps: Step[];
  personId?: string;
  viewingAgreementId?: string;
}) {
  const { historical, current } = splitSteps(steps);
  if (!historical.length || !current) return null;
  const projectChange = hasProjectChange([current, ...historical]);

  return (
    <span className="crm-unit-history__trail">
      <span className="crm-unit-history__label">
        {projectChange ? 'Proje / Daire Değişikliği:' : 'Daire Değişikliği:'}
      </span>
      <span>
        {historical.map((step, index) => (
          <Fragment key={step.agreement_id}>
            {index > 0 ? ' / ' : null}
            <StepToken
              step={step}
              personId={personId}
              viewingAgreementId={viewingAgreementId}
              projectChange={projectChange}
            />
          </Fragment>
        ))}
      </span>
      <span className="crm-unit-history__arrow" aria-hidden>
        →
      </span>
      <span className="crm-unit-history__current">
        <StepToken
          step={current}
          personId={personId}
          viewingAgreementId={viewingAgreementId}
          projectChange={projectChange}
        />
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
      <p className="crm-unit-history__trail-wrap">
        <UnitHistoryTrail steps={steps} personId={personId} viewingAgreementId={viewingAgreementId} />
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
      <UnitHistoryTrail steps={steps} />
    </span>
  );
}
