'use client';

import { useLocale, useTranslations } from 'next-intl';

import { formatBudget, formatDate, type Lead } from '@/lib/api/leads';
import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { useLeadLabels } from '@/lib/i18n/lead-labels';

interface LeadDetailDrawerProps {
  lead: Lead | null;
  archiving: boolean;
  onClose: () => void;
  onEdit: (lead: Lead) => void;
  onArchive: (lead: Lead) => void;
}

export function LeadDetailDrawer({
  lead,
  archiving,
  onClose,
  onEdit,
  onArchive,
}: LeadDetailDrawerProps) {
  const t = useTranslations('leads');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getStatusLabel, getSourceLabel } = useLeadLabels();

  if (!lead) {
    return null;
  }

  return (
    <div className="leads-drawer" role="presentation" onClick={onClose}>
      <aside
        className="leads-drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lead-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-drawer__header">
          <div>
            <p className="dashboard__eyebrow">{t('detailEyebrow')}</p>
            <h2 id="lead-detail-title">{lead.full_name}</h2>
            {lead.is_demo && (
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
            <dd>{lead.email ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.phone')}</dt>
            <dd>{lead.phone ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.country')}</dt>
            <dd>{lead.country ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.source')}</dt>
            <dd>{getSourceLabel(lead.source)}</dd>
          </div>
          <div>
            <dt>{t('detail.status')}</dt>
            <dd>{getStatusLabel(lead.status)}</dd>
          </div>
          <div>
            <dt>{t('detail.assignedTo')}</dt>
            <dd>{lead.assigned_to ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.budget')}</dt>
            <dd>{formatBudget(lead.estimated_budget, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.project')}</dt>
            <dd>{lead.interested_project ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.created')}</dt>
            <dd>{formatDate(lead.created_at, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.updated')}</dt>
            <dd>{formatDate(lead.updated_at, locale)}</dd>
          </div>
        </dl>

        <div className="leads-drawer__notes">
          <h3>{t('detail.notes')}</h3>
          <p>{lead.notes?.trim() ? lead.notes : t('noNotes')}</p>
        </div>

        <EntityActivityTimeline entityType="lead" entityId={lead.id} />

        <footer className="leads-drawer__footer">
          <button
            type="button"
            className="leads__button leads__button--secondary"
            onClick={() => onEdit(lead)}
          >
            {tCommon('edit')}
          </button>
          <button
            type="button"
            className="leads__button leads__button--danger"
            disabled={archiving}
            onClick={() => onArchive(lead)}
          >
            {archiving ? t('archiving') : t('archiveLead')}
          </button>
        </footer>
      </aside>
    </div>
  );
}
