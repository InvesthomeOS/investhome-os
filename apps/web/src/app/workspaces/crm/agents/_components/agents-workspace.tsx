'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { fetchActivities } from '@/workspaces/crm/api/activities';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { ContactListParams } from '@/workspaces/crm/api/contacts';
import type { CrmActivitySummary } from '@/workspaces/crm/types/activities';
import type { CrmContactSummary } from '@/workspaces/crm/types';

import { AgentsActivities } from './agents-activities';
import { AgentsCalendar } from './agents-calendar';
import { AgentsKanban } from './agents-kanban';
import { AgentsList } from './agents-list';
import { buildActivityIndex } from './agents-stage';

import '../../contacts/_components/ds/contacts-ds.css';
import '@/workspaces/crm/contact-card/contact-card.css';
import '../../agreements/_components/agreements-workspace.css';

const VIEW_TABS = [
  { id: 'kanban', labelKey: 'views.kanban' },
  { id: 'list', labelKey: 'views.list' },
  { id: 'activities', labelKey: 'views.activities' },
  { id: 'calendar', labelKey: 'views.calendar' },
] as const;

type ViewId = (typeof VIEW_TABS)[number]['id'];

const LIST_PARAMS: ContactListParams = {
  contact_types: ['broker', 'realtor'],
  page: 1,
  page_size: 100,
  sort_by: 'display_name',
  sort_dir: 'asc',
};

async function fetchAgentActivities(ids: string[]): Promise<CrmActivitySummary[]> {
  if (!ids.length) return [];
  const pages = await Promise.allSettled(
    ids.map((id) =>
      fetchActivities({
        entity_type: 'contact',
        entity_id: id,
        page: 1,
        page_size: 50,
        sort_by: 'created_at',
        sort_dir: 'desc',
      }),
    ),
  );
  return pages.flatMap((page) => (page.status === 'fulfilled' ? page.value.items : []));
}

export function AgentsWorkspace() {
  const t = useTranslations('crm.agents');
  const { openContact } = useContactCard();
  const [view, setView] = useState<ViewId>('kanban');

  const query = useQuery(contactQueries.list(LIST_PARAMS));
  const items = query.data?.items ?? [];
  const agentIds = useMemo(() => items.map((item) => item.id), [items]);

  const activityQuery = useQuery({
    queryKey: ['crm', 'agents', 'activities', agentIds],
    queryFn: () => fetchAgentActivities(agentIds),
    enabled: agentIds.length > 0,
  });

  const activity = useMemo(
    () => buildActivityIndex(agentIds, activityQuery.data ?? []),
    [agentIds, activityQuery.data],
  );

  const openAgent = (agent: CrmContactSummary | string) => {
    openContact(typeof agent === 'string' ? agent : agent.id);
  };

  return (
    <div className="ctc-ds crm-agents-workspace" data-testid="crm-agents-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-agreements-views" role="tablist" aria-label={t('viewsLabel')}>
          {VIEW_TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              className={view === item.id ? 'is-active' : undefined}
              data-testid={`agents-view-${item.id}`}
              onClick={() => setView(item.id)}
            >
              {t(item.labelKey)}
            </button>
          ))}
        </div>
      </header>

      <section className="ctc-ds__toolbar crm-agreements-toolbar">
        <p className="crm-agreements-count" data-testid="agents-count">
          {query.data ? t('count', { count: query.data.total }) : t('loading')}
        </p>
      </section>

      {query.isLoading ? <p>{t('loading')}</p> : null}
      {query.isError ? <p>{t('loadError')}</p> : null}

      {!query.isLoading && !query.isError && items.length === 0 ? (
        <div className="ctc-ds__empty" data-testid="crm-agents-empty">
          <strong>{t('emptyTitle')}</strong>
          <p>{t('emptyDescription')}</p>
        </div>
      ) : null}

      {!query.isLoading && !query.isError && items.length > 0 && view === 'kanban' ? (
        <AgentsKanban items={items} activity={activity} onOpen={openAgent} />
      ) : null}
      {!query.isLoading && !query.isError && items.length > 0 && view === 'list' ? (
        <AgentsList items={items} activity={activity} onOpen={openAgent} />
      ) : null}
      {!query.isLoading && !query.isError && view === 'activities' ? (
        activityQuery.isLoading ? (
          <p>{t('loading')}</p>
        ) : (
          <AgentsActivities items={items} activities={activity.items} onOpen={openAgent} />
        )
      ) : null}
      {!query.isLoading && !query.isError && view === 'calendar' ? (
        activityQuery.isLoading ? (
          <p>{t('loading')}</p>
        ) : (
          <AgentsCalendar items={items} activities={activity.items} onOpen={openAgent} />
        )
      ) : null}
    </div>
  );
}
