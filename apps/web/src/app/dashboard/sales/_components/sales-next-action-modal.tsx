'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  OPPORTUNITY_NEXT_ACTIONS,
  type OpportunityNextAction,
  type SalesOpportunity,
} from '@/lib/api/sales';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

interface SalesNextActionModalProps {
  opportunity: SalesOpportunity | null;
  submitting: boolean;
  onClose: () => void;
  onSubmit: (nextAction: OpportunityNextAction, nextActionDate: string) => void;
}

export function SalesNextActionModal({
  opportunity,
  submitting,
  onClose,
  onSubmit,
}: SalesNextActionModalProps) {
  const t = useTranslations('sales');
  const tCommon = useTranslations('common');
  const { getNextActionLabel } = useSalesLabels();
  const [nextAction, setNextAction] = useState<OpportunityNextAction>(
    opportunity?.next_action ?? 'call',
  );
  const [nextActionDate, setNextActionDate] = useState(opportunity?.next_action_date ?? '');

  if (!opportunity) return null;

  return (
    <div className="leads-modal" role="presentation" onClick={onClose}>
      <form
        className="leads-modal__panel"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(nextAction, nextActionDate);
        }}
      >
        <header className="leads-modal__header">
          <h2>{t('nextAction.title')}</h2>
          <p className="sales__modal-subtitle">{opportunity.opportunity_code}</p>
        </header>
        <div className="leads-form">
          <label className="leads__field">
            <span>{t('nextAction.action')}</span>
            <select
              value={nextAction}
              onChange={(e) => setNextAction(e.target.value as OpportunityNextAction)}
              required
            >
              {OPPORTUNITY_NEXT_ACTIONS.map((action) => (
                <option key={action} value={action}>
                  {getNextActionLabel(action)}
                </option>
              ))}
            </select>
          </label>
          <label className="leads__field">
            <span>{t('nextAction.date')}</span>
            <input
              type="date"
              value={nextActionDate}
              onChange={(e) => setNextActionDate(e.target.value)}
              required
            />
          </label>
        </div>
        <footer className="leads-modal__footer">
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('cancel')}
          </button>
          <button type="submit" className="leads__button leads__button--primary" disabled={submitting}>
            {t('nextAction.save')}
          </button>
        </footer>
      </form>
    </div>
  );
}
