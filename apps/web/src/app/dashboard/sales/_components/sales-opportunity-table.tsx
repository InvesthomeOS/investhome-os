'use client';

import { useLocale, useTranslations } from 'next-intl';

import { LoadingState, Pagination, StatusChip, Table } from '@investhome/ui';

import {
  formatMoney,
  formatShortDate,
  type SalesOpportunity,
} from '@/lib/api/sales';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

interface SalesOpportunityTableProps {
  opportunities: SalesOpportunity[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  density: 'comfortable' | 'compact';
  partyNames: Record<string, string>;
  userNames: Record<string, string>;
  projectNames: Record<string, string>;
  primaryProjectByOpp: Record<string, string>;
  sortBy: string;
  sortDir: 'asc' | 'desc';
  onSort: (column: string) => void;
  onPageChange: (page: number) => void;
  onDensityChange: (density: 'comfortable' | 'compact') => void;
  onOpen: (opportunity: SalesOpportunity) => void;
}

export function SalesOpportunityTable({
  opportunities,
  total,
  page,
  pageSize,
  loading,
  density,
  partyNames,
  userNames,
  projectNames,
  primaryProjectByOpp,
  sortBy,
  sortDir,
  onSort,
  onPageChange,
  onDensityChange,
  onOpen,
}: SalesOpportunityTableProps) {
  const t = useTranslations('sales');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getStageLabel, getNextActionLabel, getPriorityLabel } = useSalesLabels();

  const sortIndicator = (column: string) => {
    if (sortBy !== column) return '';
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  };

  if (loading && opportunities.length === 0) {
    return <LoadingState label={tCommon('loading')} />;
  }

  return (
    <>
      <div className="sales__table-toolbar">
        <span className="inventory__result-count">{t('resultCount', { count: total })}</span>
        <button
          type="button"
          className="leads__button leads__button--ghost"
          onClick={() => onDensityChange(density === 'comfortable' ? 'compact' : 'comfortable')}
        >
          {density === 'comfortable' ? t('table.compact') : t('table.comfortable')}
        </button>
      </div>
      <div className="leads__table-wrap">
        <Table className={`leads__table${density === 'compact' ? ' leads__table--compact' : ''}`}>
          <thead>
            <tr>
              <th>
                <button type="button" className="sales__sort-button" onClick={() => onSort('opportunity_code')}>
                  {t('table.code')}{sortIndicator('opportunity_code')}
                </button>
              </th>
              <th>{t('table.party')}</th>
              <th>
                <button type="button" className="sales__sort-button" onClick={() => onSort('stage')}>
                  {t('table.stage')}{sortIndicator('stage')}
                </button>
              </th>
              <th>{t('table.value')}</th>
              <th>{t('table.probability')}</th>
              <th>{t('table.assignee')}</th>
              <th>{t('table.nextAction')}</th>
              <th>{t('table.project')}</th>
              <th>{t('table.priority')}</th>
              <th>
                <button type="button" className="sales__sort-button" onClick={() => onSort('expected_close_date')}>
                  {t('table.expectedClose')}{sortIndicator('expected_close_date')}
                </button>
              </th>
              <th>
                <button type="button" className="sales__sort-button" onClick={() => onSort('updated_at')}>
                  {t('table.updated')}{sortIndicator('updated_at')}
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {opportunities.length === 0 ? (
              <tr>
                <td colSpan={11}>{t('empty')}</td>
              </tr>
            ) : (
              opportunities.map((opportunity) => (
                <tr
                  key={opportunity.id}
                  className="sales__row"
                  onClick={() => onOpen(opportunity)}
                >
                  <td>{opportunity.display_id ?? opportunity.opportunity_code}</td>
                  <td>{partyNames[opportunity.party_id] ?? t('unknownParty')}</td>
                  <td>
                    <StatusChip tone="default">{getStageLabel(opportunity.stage)}</StatusChip>
                  </td>
                  <td>
                    {opportunity.expected_revenue
                      ? formatMoney(opportunity.expected_revenue, opportunity.currency, locale)
                      : tCommon('noValue')}
                  </td>
                  <td>{opportunity.probability}%</td>
                  <td>
                    {opportunity.assigned_sales_user_id
                      ? userNames[opportunity.assigned_sales_user_id] ?? tCommon('noValue')
                      : tCommon('noValue')}
                  </td>
                  <td>
                    {opportunity.next_action
                      ? `${getNextActionLabel(opportunity.next_action)}${
                          opportunity.next_action_date
                            ? ` (${formatShortDate(opportunity.next_action_date, locale)})`
                            : ''
                        }`
                      : tCommon('noValue')}
                  </td>
                  <td>
                    {primaryProjectByOpp[opportunity.id]
                      ? projectNames[primaryProjectByOpp[opportunity.id]!] ?? tCommon('noValue')
                      : tCommon('noValue')}
                  </td>
                  <td>{getPriorityLabel(opportunity.priority)}</td>
                  <td>{formatShortDate(opportunity.expected_close_date, locale)}</td>
                  <td>{formatShortDate(opportunity.updated_at, locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </Table>
      </div>
      {total > pageSize && (
        <Pagination
          page={page}
          pageSize={pageSize}
          total={total}
          previousLabel={t('prevPage')}
          nextLabel={t('nextPage')}
          onPrevious={() => onPageChange(Math.max(1, page - 1))}
          onNext={() => onPageChange(page + 1)}
          summary={t('pagination', {
            page,
            pages: Math.max(1, Math.ceil(total / pageSize)),
            total,
          })}
        />
      )}
    </>
  );
}
