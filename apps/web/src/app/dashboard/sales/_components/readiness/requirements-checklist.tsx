'use client';

import { useTranslations } from 'next-intl';

import type { ReadinessRequirement } from '@/lib/api/sales-readiness';
import { useReadinessLabels } from '@/lib/i18n/sales-readiness-labels';

const GROUP_ORDER = ['reservation', 'deposit', 'party', 'documents', 'contract', 'handoff'];

interface RequirementsChecklistProps {
  requirements: ReadinessRequirement[];
  onVerify?: (req: ReadinessRequirement) => void;
  onWaive?: (req: ReadinessRequirement) => void;
}

export function RequirementsChecklist({ requirements, onVerify, onWaive }: RequirementsChecklistProps) {
  const t = useTranslations('salesReadiness');
  const { getRequirementStatusLabel, getGroupLabel } = useReadinessLabels();

  const grouped = GROUP_ORDER.map((group) => ({
    group,
    items: requirements.filter((r) => (r.template_group ?? 'other') === group),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="readiness-checklist">
      {grouped.map(({ group, items }) => (
        <section key={group} className="readiness-checklist__group">
          <h4>{getGroupLabel(group)}</h4>
          <ul>
            {items.map((req) => (
              <li key={req.id} className={`readiness-checklist__item readiness-checklist__item--${req.status}`}>
                <div className="readiness-checklist__title">
                  <strong>{req.title}</strong>
                  {req.is_mandatory && <span className="readiness-checklist__badge">{t('mandatory')}</span>}
                </div>
                <div className="readiness-checklist__meta">
                  <span aria-label={t('requirementStatus')}>{getRequirementStatusLabel(req.status)}</span>
                  {req.blocked_reason && <span className="readiness-checklist__blocker">{req.blocked_reason}</span>}
                </div>
                <div className="readiness-checklist__actions">
                  {onVerify && req.status !== 'verified' && req.status !== 'waived' && (
                    <button type="button" onClick={() => onVerify(req)}>{t('actions.verify')}</button>
                  )}
                  {onWaive && req.is_mandatory && req.status !== 'waived' && (
                    <button type="button" onClick={() => onWaive(req)}>{t('actions.waive')}</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
