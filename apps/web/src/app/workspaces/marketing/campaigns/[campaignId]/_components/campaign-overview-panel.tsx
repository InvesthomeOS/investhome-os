'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import { campaignQueries } from '@/workspaces/marketing/hooks/use-campaigns';

function MetricBlock({
  label,
  value,
  unavailable,
}: {
  label: string;
  value: string;
  unavailable?: boolean;
}) {
  return (
    <article className="marketing-campaign-overview__metric">
      <p className="marketing-campaign-overview__metric-label">{label}</p>
      <p
        className={
          unavailable
            ? 'marketing-campaign-overview__metric-value marketing-campaign-overview__metric-value--unavailable'
            : 'marketing-campaign-overview__metric-value'
        }
      >
        {value}
      </p>
    </article>
  );
}

function displayAmount(value: unknown, currency?: unknown, emptyLabel?: string): string {
  if (value === null || value === undefined || value === '') {
    return emptyLabel ?? '—';
  }
  const amount = String(value);
  return currency ? `${amount} ${String(currency)}` : amount;
}

export function CampaignOverviewPanel({ campaignId }: { campaignId: string }) {
  const t = useTranslations('marketing.campaigns.detail.panels.overview');
  const tDetail = useTranslations('marketing.campaigns.detail.overview');
  const overviewQuery = useQuery(campaignQueries.overview(campaignId));
  const detailQuery = useQuery(campaignQueries.detail(campaignId));

  if (overviewQuery.isLoading || detailQuery.isLoading) {
    return <LoadingState label={t('loading')} />;
  }

  if (overviewQuery.isError || !overviewQuery.data || !detailQuery.data) {
    return <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />;
  }

  const overview = overviewQuery.data;
  const campaign = detailQuery.data;
  const budget = overview.budget_summary ?? {};
  const leads = overview.leads_summary ?? {};
  const conversions = overview.conversions_summary ?? {};
  const spend = overview.spend_summary ?? {};
  const spendUnavailable = spend.state !== 'ready';
  const conversionsUnavailable = conversions.state === 'not_connected';

  return (
    <div className="marketing-campaign-overview">
      <section className="marketing-campaign-overview__grid" aria-label={tDetail('title')}>
        <MetricBlock
          label={tDetail('budget')}
          value={displayAmount(budget.planned, budget.currency, tDetail('notSet'))}
        />
        <MetricBlock
          label={tDetail('spend')}
          value={
            spendUnavailable
              ? tDetail('noData')
              : displayAmount(spend.amount ?? budget.spent, budget.currency, tDetail('noData'))
          }
          unavailable={spendUnavailable}
        />
        <MetricBlock
          label={t('remaining')}
          value={displayAmount(overview.remaining_budget ?? budget.remaining, budget.currency, tDetail('notSet'))}
        />
        <MetricBlock
          label={tDetail('leads')}
          value={leads.count != null ? String(leads.count) : tDetail('noData')}
        />
        <MetricBlock
          label={tDetail('conversions')}
          value={conversionsUnavailable ? tDetail('notConnected') : String(conversions.count ?? tDetail('noData'))}
          unavailable={conversionsUnavailable}
        />
      </section>

      <section className="marketing-campaign-overview__section">
        <h3>{t('timeline')}</h3>
        <dl className="marketing-campaign-overview__dl">
          <div>
            <dt>{t('startDate')}</dt>
            <dd>{overview.start_date ? new Date(overview.start_date).toLocaleDateString() : tDetail('notSet')}</dd>
          </div>
          <div>
            <dt>{t('endDate')}</dt>
            <dd>{overview.end_date ? new Date(overview.end_date).toLocaleDateString() : tDetail('notSet')}</dd>
          </div>
          <div>
            <dt>{t('primaryChannel')}</dt>
            <dd>{overview.primary_channel ?? campaign.primary_channel ?? tDetail('notSet')}</dd>
          </div>
        </dl>
      </section>

      <section className="marketing-campaign-overview__section">
        <h3>{t('connectedProject')}</h3>
        {campaign.target_project_id || overview.target_project_id ? (
          <Link
            href={`/dashboard/projects/${campaign.target_project_id ?? overview.target_project_id}/overview` as Route}
            className="marketing-campaign-overview__link"
          >
            {String(campaign.target_project_id ?? overview.target_project_id)}
          </Link>
        ) : (
          <p className="marketing-campaign-overview__empty">{t('noProject')}</p>
        )}
        {(campaign.project_ids?.length ?? 0) > 0 ? (
          <ul className="marketing-campaign-overview__list">
            {campaign.project_ids?.map((projectId) => (
              <li key={projectId}>
                <Link href={`/dashboard/projects/${projectId}/overview` as Route}>{projectId}</Link>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="marketing-campaign-overview__section">
        <h3>{t('connectedLeads')}</h3>
        <p>
          {leads.count != null && Number(leads.count) > 0
            ? t('leadsCount', { count: Number(leads.count) })
            : t('noLeads')}
        </p>
        {(campaign.lead_source_id || overview.lead_source_id) && (
          <p className="marketing-campaign-overview__meta">
            {t('leadSource')}: {String(campaign.lead_source_id ?? overview.lead_source_id)}
          </p>
        )}
      </section>

      <section className="marketing-campaign-overview__section">
        <h3>{t('notes')}</h3>
        <p className="marketing-campaign-overview__notes">
          {overview.notes || campaign.notes || t('noNotes')}
        </p>
      </section>

      <section className="marketing-campaign-overview__section">
        <h3>{t('readiness')}</h3>
        <StatusChip tone={overview.readiness.overall_state === 'ready' ? 'success' : 'warning'}>
          {overview.readiness.overall_state}
        </StatusChip>
        {overview.readiness.blockers.length > 0 ? (
          <ul className="marketing-campaign-overview__list">
            {overview.readiness.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  );
}
