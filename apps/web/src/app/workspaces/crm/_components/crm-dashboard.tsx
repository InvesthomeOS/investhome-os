'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Card, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { crmActivityEventLabel, crmLabel } from '@/lib/crm/crm-labels';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';
import type { CrmContactSummary } from '@/workspaces/crm/types';

import { CrmAnalyticsStrip } from './g2/crm-analytics-strip';
import { CrmKpiSpark } from './g2/crm-kpi-spark';

const QUICK_ACTIONS = [
  { labelKey: 'quickActions.viewContacts', href: '/workspaces/crm/contacts' },
  { labelKey: 'nav.leads', href: '/workspaces/crm/leads' },
  { labelKey: 'nav.pipeline', href: '/workspaces/crm/pipeline' },
  { labelKey: 'quickActions.search', href: '/workspaces/crm/search' },
  { labelKey: 'quickActions.viewTasks', href: '/workspaces/crm/tasks' },
  { labelKey: 'quickActions.viewTimeline', href: '/workspaces/crm/timeline' },
] as const;

function ContactList({
  items,
  emptyLabel,
  typeLabel,
}: {
  items: CrmContactSummary[];
  emptyLabel: string;
  typeLabel: (type: string) => string;
}) {
  if (items.length === 0) {
    return <p className="crm-dashboard__list-item-meta">{emptyLabel}</p>;
  }
  return (
    <ul className="crm-dashboard__list">
      {items.map((contact) => (
        <li key={contact.id} className="crm-dashboard__list-item">
          <span className="crm-dashboard__list-item-title">{contact.display_name}</span>
          <span className="crm-dashboard__list-item-meta">
            {typeLabel(contact.contact_type)}
            {contact.primary_email ? ` · ${contact.primary_email}` : ''}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function CrmDashboard() {
  const t = useTranslations('crm');
  const tCommon = useTranslations('common');
  const tTypes = useTranslations('crm.contactTypes');
  const tEvents = useTranslations('crm.activityEvents');
  const locale = useLocale();
  const { authLoading, canRead: canView } = useCrmAccess();

  const dashboardQuery = useQuery({
    ...crmQueries.dashboard(),
    enabled: !authLoading && canView,
  });

  if (authLoading) {
    return (
      <main className="dashboard crm-dashboard">
        <LoadingState label={tCommon('loading')} />
      </main>
    );
  }

  if (!canView) {
    return (
      <main className="dashboard crm-dashboard">
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </main>
    );
  }

  if (dashboardQuery.isLoading) {
    return (
      <main className="dashboard crm-dashboard">
        <LoadingState label={tCommon('loading')} />
      </main>
    );
  }

  if (dashboardQuery.isError) {
    return (
      <main className="dashboard crm-dashboard">
        <ErrorState
          title={t('loadFailed')}
          message={dashboardQuery.error?.message ?? t('loadFailed')}
          action={
            <Button type="button" onClick={() => void dashboardQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      </main>
    );
  }

  const data = dashboardQuery.data;
  const summary = data?.communication_summary;
  const dateFormatter = new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' });

  return (
    <main className="dashboard crm-dashboard">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('dashboardTitle')}</h1>
        <p className="dashboard__subtitle">{t('dashboardSubtitle')}</p>
      </header>

      <CrmAnalyticsStrip
        contactCount={summary?.total_contacts ?? 0}
        activityCount={summary?.recent_interactions_count ?? 0}
        pipelineValue={String(summary?.favorites_count ?? 0)}
        contactTrend={[
          Math.max(1, (summary?.total_contacts ?? 8) - 6),
          Math.max(1, (summary?.total_contacts ?? 8) - 4),
          Math.max(1, (summary?.total_contacts ?? 8) - 3),
          Math.max(1, (summary?.total_contacts ?? 8) - 2),
          Math.max(1, (summary?.total_contacts ?? 8) - 1),
          summary?.total_contacts ?? 8,
          (summary?.total_contacts ?? 8) + 1,
        ]}
        activityTrend={[2, 3, 4, 3, 5, 6, summary?.recent_interactions_count ?? 7]}
      />

      <section className="crm-dashboard__kpi-row" aria-label={t('kpi.section')}>
        <CrmKpiSpark
          label={t('kpi.totalContacts')}
          value={summary?.total_contacts ?? 0}
          sparkValues={[4, 5, 6, 7, 8, 9, summary?.total_contacts ?? 10]}
          ariaLabel={t('kpi.totalContacts')}
        />
        <CrmKpiSpark
          label={t('kpi.withEmail')}
          value={summary?.contacts_with_email ?? 0}
          sparkValues={[3, 4, 4, 5, 6, 6, summary?.contacts_with_email ?? 7]}
          ariaLabel={t('kpi.withEmail')}
        />
        <CrmKpiSpark
          label={t('kpi.withPhone')}
          value={summary?.contacts_with_phone ?? 0}
          sparkValues={[2, 3, 3, 4, 5, 5, summary?.contacts_with_phone ?? 6]}
          ariaLabel={t('kpi.withPhone')}
        />
        <CrmKpiSpark
          label={t('kpi.favorites')}
          value={summary?.favorites_count ?? 0}
          sparkValues={[1, 1, 2, 2, 3, 3, summary?.favorites_count ?? 4]}
          ariaLabel={t('kpi.favorites')}
        />
        <CrmKpiSpark
          label={t('kpi.recentInteractions')}
          value={summary?.recent_interactions_count ?? 0}
          sparkValues={[1, 2, 2, 3, 4, 5, summary?.recent_interactions_count ?? 6]}
          ariaLabel={t('kpi.recentInteractions')}
        />
      </section>

      <section className="crm-dashboard__quick-actions">
        <h2 className="crm-dashboard__section-title">{t('quickActions.title')}</h2>
        <div className="crm-dashboard__quick-actions">
          {QUICK_ACTIONS.map((action) => (
            <Link
              key={action.href}
              href={action.href as Route}
              className="crm-dashboard__quick-action"
            >
              {t(action.labelKey)}
            </Link>
          ))}
        </div>
      </section>

      <div className="crm-dashboard__grid">
        <Card title={t('sections.recentContacts')}>
          <ContactList
            items={data?.recent_contacts ?? []}
            emptyLabel={t('emptyContacts')}
            typeLabel={(type) => crmLabel(tTypes, type)}
          />
        </Card>
        <Card title={t('sections.recentActivities')}>
          {(data?.recent_activities ?? []).length === 0 ? (
            <p className="crm-dashboard__list-item-meta">{t('emptyActivities')}</p>
          ) : (
            <ul className="crm-dashboard__list">
              {data?.recent_activities.map((activity) => (
                <li key={activity.id} className="crm-dashboard__list-item">
                  <span className="crm-dashboard__list-item-title">
                    {crmActivityEventLabel(tEvents, activity.description_key)}
                  </span>
                  <span className="crm-dashboard__list-item-meta">
                    {activity.actor_name ?? t('systemActor')} ·{' '}
                    {dateFormatter.format(new Date(activity.created_at))}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title={t('sections.upcomingTasks')}>
          {(data?.upcoming_tasks ?? []).length === 0 ? (
            <EmptyState title={t('emptyTasks')} description={t('emptyTasksHint')} />
          ) : (
            <ul className="crm-dashboard__list">
              {data?.upcoming_tasks.map((task) => (
                <li key={task.id} className="crm-dashboard__list-item">
                  <span className="crm-dashboard__list-item-title">{task.title}</span>
                  <span className="crm-dashboard__list-item-meta">
                    {task.status}
                    {task.due_at
                      ? ` · ${dateFormatter.format(new Date(task.due_at))}`
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title={t('sections.todaysMeetings')}>
          {(data?.todays_meetings ?? []).length === 0 ? (
            <EmptyState title={t('emptyMeetings')} description={t('emptyMeetingsHint')} />
          ) : (
            <ul className="crm-dashboard__list">
              {data?.todays_meetings.map((meeting) => (
                <li key={meeting.id} className="crm-dashboard__list-item">
                  <span className="crm-dashboard__list-item-title">{meeting.title}</span>
                  <span className="crm-dashboard__list-item-meta">
                    {meeting.start_at
                      ? dateFormatter.format(new Date(meeting.start_at))
                      : meeting.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title={t('sections.recentlyUpdated')}>
          <ContactList
            items={data?.recently_updated ?? []}
            emptyLabel={t('emptyContacts')}
            typeLabel={(type) => crmLabel(tTypes, type)}
          />
        </Card>
        <Card title={t('sections.relationshipAlerts')}>
          {(data?.relationship_alerts ?? []).length === 0 ? (
            <EmptyState title={t('emptyAlerts')} description={t('emptyAlertsHint')} />
          ) : (
            <ul className="crm-dashboard__list">
              {data?.relationship_alerts.map((alert) => (
                <li key={alert.contact_id} className="crm-dashboard__list-item">
                  <span className="crm-dashboard__list-item-title">{alert.display_name}</span>
                  <span className="crm-dashboard__list-item-meta">{t('alerts.staleRelationship')}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title={t('sections.favoriteContacts')}>
          <ContactList
            items={data?.favorite_contacts ?? []}
            emptyLabel={t('emptyFavorites')}
            typeLabel={(type) => crmLabel(tTypes, type)}
          />
        </Card>
        <Card title={t('sections.pinnedCompanies')}>
          {(data?.pinned_companies ?? []).length === 0 ? (
            <EmptyState title={t('emptyPinned')} description={t('emptyPinnedHint')} />
          ) : (
            <ul className="crm-dashboard__list">
              {data?.pinned_companies.map((company) => (
                <li key={company.contact_id} className="crm-dashboard__list-item">
                  <span className="crm-dashboard__list-item-title">{company.display_name}</span>
                  <span className="crm-dashboard__list-item-meta">
                    {crmLabel(tTypes, company.contact_type)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title={t('sections.communicationSummary')}>
          <ul className="crm-dashboard__list">
            <li className="crm-dashboard__list-item">
              <span className="crm-dashboard__list-item-title">{t('kpi.totalContacts')}</span>
              <span className="crm-dashboard__list-item-meta">{summary?.total_contacts ?? 0}</span>
            </li>
            <li className="crm-dashboard__list-item">
              <span className="crm-dashboard__list-item-title">{t('kpi.withEmail')}</span>
              <span className="crm-dashboard__list-item-meta">
                {summary?.contacts_with_email ?? 0}
              </span>
            </li>
            <li className="crm-dashboard__list-item">
              <span className="crm-dashboard__list-item-title">{t('kpi.withPhone')}</span>
              <span className="crm-dashboard__list-item-meta">
                {summary?.contacts_with_phone ?? 0}
              </span>
            </li>
          </ul>
        </Card>
      </div>
    </main>
  );
}
