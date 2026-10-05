'use client';

import { useLocale, useTranslations } from 'next-intl';

import { LoadingState, StatusChip, Table } from '@investhome/ui';

import { formatDate, type Lead } from '@/lib/api/leads';
import { useLeadLabels } from '@/lib/i18n/lead-labels';
import { canConvertLeadToOpportunity } from '@/lib/sales/lead-visibility';

interface SalesLeadTableProps {
  leads: Lead[];
  loading: boolean;
  userNames: Record<string, string>;
  canConvert: boolean;
  onOpen: (lead: Lead) => void;
  onConvert: (lead: Lead) => void;
}

export function SalesLeadTable({
  leads,
  loading,
  userNames,
  canConvert,
  onOpen,
  onConvert,
}: SalesLeadTableProps) {
  const t = useTranslations('sales');
  const tLeads = useTranslations('leads');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getStatusLabel, getSourceLabel } = useLeadLabels();

  if (loading && leads.length === 0) {
    return <LoadingState label={tCommon('loading')} />;
  }

  return (
    <>
      <div className="sales__table-toolbar">
        <span className="inventory__result-count">{t('leadsView.resultCount', { count: leads.length })}</span>
      </div>
      <div className="leads__table-wrap">
        <Table className="leads__table">
          <thead>
            <tr>
              <th>{tLeads('table.name')}</th>
              <th>{tLeads('detail.email')}</th>
              <th>{tLeads('detail.phone')}</th>
              <th>{tLeads('table.source')}</th>
              <th>{tLeads('table.project')}</th>
              <th>{tLeads('table.status')}</th>
              <th>{tLeads('table.assignedTo')}</th>
              <th>{tLeads('table.created')}</th>
              {canConvert ? <th>{t('leadsView.actions')}</th> : null}
            </tr>
          </thead>
          <tbody>
            {leads.length === 0 ? (
              <tr>
                <td colSpan={canConvert ? 9 : 8}>{t('leadsView.empty')}</td>
              </tr>
            ) : (
              leads.map((lead) => (
                <tr
                  key={lead.id}
                  className="sales__row leads__row--link"
                  onClick={() => onOpen(lead)}
                >
                  <td>
                    <span className="leads__name">{lead.full_name}</span>
                  </td>
                  <td>{lead.email ?? tCommon('noValue')}</td>
                  <td>{lead.phone ?? tCommon('noValue')}</td>
                  <td>{getSourceLabel(lead.source)}</td>
                  <td>{lead.interested_project ?? tCommon('noValue')}</td>
                  <td>
                    <StatusChip tone="default">{getStatusLabel(lead.status)}</StatusChip>
                  </td>
                  <td>
                    {lead.assigned_to
                      ?? (lead.assigned_manager_id ? userNames[lead.assigned_manager_id] : null)
                      ?? tCommon('noValue')}
                  </td>
                  <td>{formatDate(lead.created_at, locale)}</td>
                  {canConvert ? (
                    <td>
                      {canConvertLeadToOpportunity(lead.status) ? (
                        <button
                          type="button"
                          className="leads__button leads__button--secondary"
                          onClick={(event) => {
                            event.stopPropagation();
                            onConvert(lead);
                          }}
                        >
                          {t('leadsView.convert')}
                        </button>
                      ) : (
                        tCommon('noValue')
                      )}
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </Table>
      </div>
    </>
  );
}
