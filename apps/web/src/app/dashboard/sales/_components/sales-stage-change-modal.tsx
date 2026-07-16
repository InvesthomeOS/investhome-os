'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  ALLOWED_STAGE_TRANSITIONS,
  OPPORTUNITY_LOSS_REASONS,
  type OpportunityLossReason,
  type OpportunityStage,
  type SalesOpportunity,
} from '@/lib/api/sales';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

interface SalesStageChangeModalProps {
  opportunity: SalesOpportunity | null;
  targetStage: OpportunityStage | null;
  submitting: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    stage: OpportunityStage;
    notes?: string;
    loss_reason?: OpportunityLossReason;
    loss_notes?: string;
    dormant_review_date?: string;
    cancelled_reason?: string;
  }) => void;
}

export function SalesStageChangeModal({
  opportunity,
  targetStage: initialTargetStage,
  submitting,
  onClose,
  onSubmit,
}: SalesStageChangeModalProps) {
  const t = useTranslations('sales');
  const tCommon = useTranslations('common');
  const { getStageLabel, getLossReasonLabel } = useSalesLabels();
  const allowedTargets = opportunity
    ? ALLOWED_STAGE_TRANSITIONS[opportunity.stage] ?? []
    : [];
  const [targetStage, setTargetStage] = useState<OpportunityStage>(
    initialTargetStage ?? allowedTargets[0] ?? 'qualified',
  );
  const [notes, setNotes] = useState('');
  const [lossReason, setLossReason] = useState<OpportunityLossReason>('budget');
  const [lossNotes, setLossNotes] = useState('');
  const [dormantReviewDate, setDormantReviewDate] = useState('');
  const [cancelledReason, setCancelledReason] = useState('');

  if (!opportunity) return null;

  const selectableStages = initialTargetStage
    ? [initialTargetStage]
    : [...allowedTargets];

  if (selectableStages.length === 0) {
    return (
      <div className="leads-modal" role="presentation" onClick={onClose}>
        <div className="leads-modal__panel" role="dialog" onClick={(e) => e.stopPropagation()}>
          <p className="leads__state">{t('errors.invalidStageTransition')}</p>
          <button type="button" className="leads__button leads__button--secondary" onClick={onClose}>
            {tCommon('close')}
          </button>
        </div>
      </div>
    );
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    onSubmit({
      stage: targetStage,
      notes: notes.trim() || undefined,
      loss_reason: targetStage === 'lost' ? lossReason : undefined,
      loss_notes: targetStage === 'lost' ? lossNotes.trim() || undefined : undefined,
      dormant_review_date:
        targetStage === 'dormant' && dormantReviewDate ? dormantReviewDate : undefined,
      cancelled_reason:
        targetStage === 'cancelled' && cancelledReason.trim() ? cancelledReason.trim() : undefined,
    });
  };

  return (
    <div className="leads-modal" role="presentation" onClick={onClose}>
      <form
        className="leads-modal__panel"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <header className="leads-modal__header">
          <h2>{t('stageChange.title')}</h2>
          <p className="sales__modal-subtitle">
            {opportunity.opportunity_code} → {getStageLabel(targetStage)}
          </p>
        </header>
        <div className="leads-form">
          {!initialTargetStage && (
            <label className="leads__field">
              <span>{t('stageChange.targetStage')}</span>
              <select
                value={targetStage}
                onChange={(e) => setTargetStage(e.target.value as OpportunityStage)}
                required
              >
                {selectableStages.map((stage) => (
                  <option key={stage} value={stage}>
                    {getStageLabel(stage)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="leads__field">
            <span>{t('stageChange.notes')}</span>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
          </label>
          {targetStage === 'lost' && (
            <>
              <label className="leads__field">
                <span>{t('stageChange.lossReason')}</span>
                <select
                  value={lossReason}
                  onChange={(e) => setLossReason(e.target.value as OpportunityLossReason)}
                  required
                >
                  {OPPORTUNITY_LOSS_REASONS.map((reason) => (
                    <option key={reason} value={reason}>
                      {getLossReasonLabel(reason)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('stageChange.lossNotes')}</span>
                <textarea value={lossNotes} onChange={(e) => setLossNotes(e.target.value)} rows={2} />
              </label>
            </>
          )}
          {targetStage === 'dormant' && (
            <label className="leads__field">
              <span>{t('stageChange.dormantReviewDate')}</span>
              <input
                type="date"
                value={dormantReviewDate}
                onChange={(e) => setDormantReviewDate(e.target.value)}
              />
            </label>
          )}
          {targetStage === 'cancelled' && (
            <label className="leads__field">
              <span>{t('stageChange.cancelledReason')}</span>
              <input
                type="text"
                value={cancelledReason}
                onChange={(e) => setCancelledReason(e.target.value)}
                required
              />
            </label>
          )}
        </div>
        <footer className="leads-modal__footer">
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('cancel')}
          </button>
          <button type="submit" className="leads__button leads__button--primary" disabled={submitting}>
            {t('stageChange.confirm')}
          </button>
        </footer>
      </form>
    </div>
  );
}
