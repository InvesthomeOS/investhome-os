'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { fetchChannelCalendar } from '@/workspaces/marketing/api/channel';
import { contentQueries } from '@/workspaces/marketing/hooks/use-content';

export default function MarketingCalendarPage() {
  const t = useTranslations('marketing.calendar');
  const contentCalendarQuery = useQuery(contentQueries.calendar());
  const channelCalendarQuery = useQuery({
    queryKey: ['marketing', 'channelCampaigns', 'calendar'],
    queryFn: () => fetchChannelCalendar(),
  });

  const contentItems = contentCalendarQuery.data?.items ?? [];
  const channelItems = channelCalendarQuery.data?.items ?? [];
  const items = [...contentItems.map((item) => ({ ...item, source: 'content' as const })), ...channelItems.map((item) => ({ ...item, source: 'channel' as const }))].sort(
    (a, b) => new Date(a.scheduled_at ?? 0).getTime() - new Date(b.scheduled_at ?? 0).getTime(),
  );

  const isLoading = contentCalendarQuery.isLoading || channelCalendarQuery.isLoading;
  const isError = contentCalendarQuery.isError || channelCalendarQuery.isError;

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      {isLoading ? (
        <LoadingState label={t('loading')} />
      ) : isError ? (
        <ErrorState title={t('loadFailed')} message={t('loadFailed')} />
      ) : items.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <ul className="marketing-calendar__list">
          {items.map((item) => (
            <li key={`${item.source}-${item.id}`} className="marketing-calendar__item">
              <strong>{item.title}</strong>
              <span>{'channel' in item && item.channel ? item.channel : item.status}</span>
              <span>{item.scheduled_at ? new Date(item.scheduled_at).toLocaleString() : t('notScheduled')}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
