'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState } from '@investhome/ui';

import { campaignQueries } from '@/workspaces/marketing/hooks/use-campaigns';

function formatMoney(value: string | null | undefined, currency: string | null | undefined, empty: string) {
  if (value == null || value === '') return empty;
  return currency ? `${value} ${currency}` : value;
}

export function CampaignBudgetPanel({ campaignId }: { campaignId: string }) {
  const t = useTranslations('marketing.campaigns.detail.panels.budget');
  const tBudget = useTranslations('marketing.campaigns.detail.budget');
  const detailQuery = useQuery(campaignQueries.detail(campaignId));
  const budgetQuery = useQuery(campaignQueries.budget(campaignId));

  if (detailQuery.isLoading || budgetQuery.isLoading) {
    return <LoadingState label={t('loading')} />;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />;
  }

  const campaign = detailQuery.data;
  const allocations = budgetQuery.data ?? [];
  const planned = campaign.budget_amount;
  const spent = campaign.spent_amount;
  const remaining = campaign.remaining_budget;
  const currency = campaign.budget_currency;

  return (
    <div className="marketing-campaign-budget">
      <section className="marketing-campaign-budget__summary" aria-label={tBudget('title')}>
        <article>
          <p>{tBudget('planned')}</p>
          <strong>{formatMoney(planned, currency, t('notSet'))}</strong>
        </article>
        <article>
          <p>{tBudget('spent')}</p>
          <strong>
            {spent == null ? t('noData') : formatMoney(spent, currency, t('noData'))}
          </strong>
        </article>
        <article>
          <p>{t('remaining')}</p>
          <strong>{formatMoney(remaining, currency, t('notSet'))}</strong>
        </article>
      </section>

      {allocations.length === 0 ? (
        <EmptyState title={tBudget('noAllocations')} description={t('emptyDescription')} />
      ) : (
        <table className="marketing-campaign-budget__table">
          <thead>
            <tr>
              <th>{tBudget('allocation')}</th>
              <th>{tBudget('planned')}</th>
              <th>{tBudget('spent')}</th>
            </tr>
          </thead>
          <tbody>
            {allocations.map((row) => (
              <tr key={row.id}>
                <td>{row.name}</td>
                <td>{formatMoney(row.planned_amount, row.currency, t('notSet'))}</td>
                <td>{formatMoney(row.spent_amount, row.currency, t('noData'))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
