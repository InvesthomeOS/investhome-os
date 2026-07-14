'use client';

import { useLocale, useTranslations } from 'next-intl';

import {
  formatCurrency,
  formatDate,
  formatShortDate,
  type Investor,
} from '@/lib/api/investors';
import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { useInvestorLabels } from '@/lib/i18n/investor-labels';

interface InvestorDetailDrawerProps {
  investor: Investor | null;
  archiving: boolean;
  onClose: () => void;
  onEdit: (investor: Investor) => void;
  onArchive: (investor: Investor) => void;
}

export function InvestorDetailDrawer({
  investor,
  archiving,
  onClose,
  onEdit,
  onArchive,
}: InvestorDetailDrawerProps) {
  const t = useTranslations('investors');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const {
    getTypeLabel,
    getStatusLabel,
    getModelLabel,
    getAccreditationLabel,
    getRiskLabel,
  } = useInvestorLabels();

  if (!investor) {
    return null;
  }

  return (
    <div className="leads-drawer" role="presentation" onClick={onClose}>
      <aside
        className="leads-drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="investor-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-drawer__header">
          <div>
            <p className="dashboard__eyebrow">{t('detailEyebrow')}</p>
            <h2 id="investor-detail-title">{investor.full_name}</h2>
            {investor.is_demo && (
              <span className="leads__demo-tag">{tCommon('demoData')}</span>
            )}
          </div>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('close')}
          </button>
        </header>

        <dl className="leads-drawer__grid">
          <div>
            <dt>{t('detail.email')}</dt>
            <dd>{investor.email ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.phone')}</dt>
            <dd>{investor.phone ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.country')}</dt>
            <dd>{investor.country ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.city')}</dt>
            <dd>{investor.city ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.type')}</dt>
            <dd>{getTypeLabel(investor.investor_type)}</dd>
          </div>
          <div>
            <dt>{t('detail.accreditation')}</dt>
            <dd>{getAccreditationLabel(investor.accreditation_status)}</dd>
          </div>
          <div>
            <dt>{t('detail.model')}</dt>
            <dd>{getModelLabel(investor.preferred_investment_model)}</dd>
          </div>
          <div>
            <dt>{t('detail.capacity')}</dt>
            <dd>{formatCurrency(investor.investment_capacity, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.minimumTicket')}</dt>
            <dd>{formatCurrency(investor.minimum_ticket, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.maximumTicket')}</dt>
            <dd>{formatCurrency(investor.maximum_ticket, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.markets')}</dt>
            <dd>{investor.preferred_markets ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.projects')}</dt>
            <dd>{investor.preferred_projects ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.riskProfile')}</dt>
            <dd>{getRiskLabel(investor.risk_profile)}</dd>
          </div>
          <div>
            <dt>{t('detail.status')}</dt>
            <dd>{getStatusLabel(investor.status)}</dd>
          </div>
          <div>
            <dt>{t('detail.assignedTo')}</dt>
            <dd>{investor.assigned_to ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.source')}</dt>
            <dd>{investor.source ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.lastContact')}</dt>
            <dd>{formatShortDate(investor.last_contact_date, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.nextFollowUp')}</dt>
            <dd>{formatShortDate(investor.next_follow_up_date, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.created')}</dt>
            <dd>{formatDate(investor.created_at, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.updated')}</dt>
            <dd>{formatDate(investor.updated_at, locale)}</dd>
          </div>
        </dl>

        <div className="leads-drawer__notes">
          <h3>{t('detail.notes')}</h3>
          <p>{investor.notes?.trim() ? investor.notes : t('noNotes')}</p>
        </div>

        <EntityActivityTimeline entityType="investor" entityId={investor.id} />

        <footer className="leads-drawer__footer">
          <button
            type="button"
            className="leads__button leads__button--secondary"
            onClick={() => onEdit(investor)}
          >
            {tCommon('edit')}
          </button>
          <button
            type="button"
            className="leads__button leads__button--danger"
            disabled={archiving}
            onClick={() => onArchive(investor)}
          >
            {archiving ? t('archiving') : t('archiveInvestor')}
          </button>
        </footer>
      </aside>
    </div>
  );
}
