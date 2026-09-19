'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, KpiCard, LoadingState, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { LineChart } from '@/components/design-system/charts';
import { crmActivityEventLabel } from '@/lib/crm/crm-labels';
import { useAiCopilotOptional } from '@/lib/crm/use-ai-copilot-optional';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';

import {
  ACTIVITY_ICONS,
  TASK_KIND_TONE,
  buildDashboardDsData,
  type ActivityItem,
  type LeadItem,
  type MeetingItem,
  type TaskItem,
  type TimelineItem,
} from './crm-dashboard-ds-model';

import './crm-dashboard-ds.css';

function PanelEmpty({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="crm-dash-ds__empty">
      <IhIcon name="empty" size={22} />
      <strong>{title}</strong>
      <p>{hint}</p>
    </div>
  );
}

function TaskRow({ task, kindLabel }: { task: TaskItem; kindLabel: string }) {
  return (
    <Link href={task.href as Route} className="crm-dash-ds__row">
      <span className="crm-dash-ds__check" aria-hidden="true" />
      <div className="crm-dash-ds__row-main">
        <span className="crm-dash-ds__row-title">{task.title}</span>
        <span className="crm-dash-ds__row-meta">{task.related}</span>
      </div>
      <div className="crm-dash-ds__row-side">
        <span className="crm-dash-ds__row-time">{task.dueLabel}</span>
        <StatusChip tone={TASK_KIND_TONE[task.kind]}>{kindLabel}</StatusChip>
      </div>
    </Link>
  );
}

function LeadRow({ lead, newLabel }: { lead: LeadItem; newLabel: string }) {
  return (
    <Link href={lead.href as Route} className="crm-dash-ds__row">
      <span className={`crm-dash-ds__avatar is-${lead.tone}`} aria-hidden="true">
        {lead.initials}
      </span>
      <div className="crm-dash-ds__row-main">
        <span className="crm-dash-ds__row-title">{lead.name}</span>
        <span className="crm-dash-ds__row-meta">{lead.tag}</span>
      </div>
      <div className="crm-dash-ds__row-side">
        {lead.isNew ? <span className="crm-dash-ds__badge">{newLabel}</span> : null}
        <span className="crm-dash-ds__row-time">{lead.dateLabel}</span>
      </div>
    </Link>
  );
}

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <Link href={item.href as Route} className="crm-dash-ds__row">
      <span className="crm-dash-ds__act-icon" aria-hidden="true">
        <IhIcon name={ACTIVITY_ICONS[item.kind]} size={13} />
      </span>
      <div className="crm-dash-ds__row-main">
        <span className="crm-dash-ds__row-title">{item.title}</span>
        <span className="crm-dash-ds__row-meta">{item.meta}</span>
      </div>
      <span className="crm-dash-ds__row-time">{item.timeLabel}</span>
    </Link>
  );
}

function TimelineRow({ item }: { item: TimelineItem }) {
  return (
    <Link href={item.href as Route} className="crm-dash-ds__timeline-item">
      <div className="crm-dash-ds__timeline-rail">
        <span className="crm-dash-ds__timeline-dot" aria-hidden="true">
          <IhIcon name={ACTIVITY_ICONS[item.kind]} size={12} />
        </span>
      </div>
      <div className="crm-dash-ds__row-main">
        <span className="crm-dash-ds__row-title">{item.title}</span>
        <span className="crm-dash-ds__row-meta">{item.meta}</span>
      </div>
      <span className="crm-dash-ds__row-time">{item.timeLabel}</span>
    </Link>
  );
}

function MeetingCard({
  meeting,
  joinLabel,
  openLabel,
}: {
  meeting: MeetingItem;
  joinLabel: string;
  openLabel: string;
}) {
  const router = useRouter();
  return (
    <article className="crm-dash-ds__meeting">
      <div className="crm-dash-ds__meeting-date" aria-hidden="true">
        <strong>{meeting.day}</strong>
        <span>{meeting.month}</span>
      </div>
      <div className="crm-dash-ds__meeting-body">
        <strong>{meeting.title}</strong>
        <span>
          {meeting.contact} · {meeting.project}
        </span>
        <span>
          {meeting.time} · {meeting.location}
        </span>
      </div>
      <div className="crm-dash-ds__meeting-actions">
        {meeting.joinHref ? (
          <Button
            variant="primary"
            size="sm"
            onClick={() => router.push(meeting.joinHref as Route)}
          >
            {joinLabel}
          </Button>
        ) : null}
        <Button
          variant="secondary"
          size="sm"
          onClick={() => router.push(meeting.openHref as Route)}
        >
          {openLabel}
        </Button>
      </div>
    </article>
  );
}

export function CrmDashboardDsWorkspace() {
  const t = useTranslations('crm.dashboard.ds');
  const tCommon = useTranslations('common');
  const tCrm = useTranslations('crm');
  const tEvents = useTranslations('crm.activityEvents');
  const locale = useLocale();
  const router = useRouter();
  const copilot = useAiCopilotOptional();
  const { authLoading, canRead: canView } = useCrmAccess();

  const dashboardQuery = useQuery({
    ...crmQueries.dashboard(),
    enabled: !authLoading && canView,
  });
  const reportsQuery = useQuery({
    ...crmQueries.reports(),
    enabled: !authLoading && canView,
  });

  const data = useMemo(
    () =>
      buildDashboardDsData(
        dashboardQuery.data,
        locale,
        (key) => crmActivityEventLabel(tEvents, key),
        reportsQuery.data,
      ),
    [dashboardQuery.data, reportsQuery.data, locale, tEvents],
  );

  if (authLoading || dashboardQuery.isLoading || (canView && reportsQuery.isLoading)) {
    return (
      <div className="crm-dash-ds" data-testid="crm-dashboard-ds-workspace">
        <LoadingState label={tCommon('loading')} />
      </div>
    );
  }

  if (!canView) {
    return (
      <div className="crm-dash-ds" data-testid="crm-dashboard-ds-workspace">
        <ErrorState title={tCrm('accessDenied')} message={tCrm('accessDeniedHint')} />
      </div>
    );
  }

  if (dashboardQuery.isError) {
    return (
      <div className="crm-dash-ds" data-testid="crm-dashboard-ds-workspace">
        <ErrorState title={tCrm('loadFailed')} message={tCrm('accessDeniedHint')} />
      </div>
    );
  }

  return (
    <div className="crm-dash-ds" data-testid="crm-dashboard-ds-workspace">
      <header className="crm-dash-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-dash-ds__header-actions">
          {copilot ? (
            <Button variant="secondary" size="sm" onClick={() => copilot.openCopilot()}>
              <IhIcon name="sparkles" size={13} />
              {t('actions.copilot')}
            </Button>
          ) : null}
          <Button
            variant="primary"
            size="sm"
            onClick={() => router.push('/workspaces/crm/leads' as Route)}
            data-testid="crm-dashboard-ds-new-lead"
          >
            <IhIcon name="plus" size={13} />
            {t('actions.newLead')}
          </Button>
        </div>
      </header>

      <section className="crm-dash-ds__section" aria-label={t('priorities.aria')}>
        <div className="crm-dash-ds__section-head">
          <h2>{t('priorities.title')}</h2>
        </div>
        <div className="crm-dash-ds__priorities">
          {data.priorities.map((p) => (
            <Link
              key={p.key}
              href={p.href as Route}
              className="crm-dash-ds__priority"
              data-testid={`crm-dash-priority-${p.key}`}
            >
              <span className="crm-dash-ds__priority-icon" aria-hidden="true">
                <IhIcon name={p.icon} size={14} />
              </span>
              <div className="crm-dash-ds__priority-body">
                <span className="crm-dash-ds__priority-value">{p.value}</span>
                <span className="crm-dash-ds__priority-label">{t(`priorities.${p.key}.label`)}</span>
                <span className="crm-dash-ds__priority-desc">{t(`priorities.${p.key}.desc`)}</span>
              </div>
              <span className="crm-dash-ds__priority-action">
                {t(`priorities.${p.key}.action`)} →
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="crm-dash-ds__section" aria-label={t('kpis.aria')}>
        <div className="crm-dash-ds__section-head">
          <h2>{t('kpis.title')}</h2>
        </div>
        <div className="crm-dash-ds__kpi-row">
          {data.kpis.map((kpi) => (
            <KpiCard
              key={kpi.key}
              className="crm-dash-ds__kpi"
              label={t(`kpis.${kpi.key}`)}
              value={kpi.value}
              hint={t(`kpis.hints.${kpi.key}`)}
              delta={kpi.delta ? `${kpi.delta} ${t('kpis.vsLastMonth')}` : undefined}
              {...(kpi.deltaTone ? { deltaTone: kpi.deltaTone } : {})}
              icon={<IhIcon name={kpi.icon} size={18} />}
            />
          ))}
        </div>
      </section>

      <section className="crm-dash-ds__section" aria-label={t('ops.aria')}>
        <div className="crm-dash-ds__section-head">
          <h2>{t('ops.title')}</h2>
        </div>
        <div className="crm-dash-ds__ops">
          <div className="crm-dash-ds__panel">
            <div className="crm-dash-ds__panel-head">
              <h3>{t('ops.tasks')}</h3>
              <Link href={'/workspaces/crm/tasks' as Route} className="crm-dash-ds__view-all">
                {t('viewAll')}
                <IhIcon name="arrowRight" size={11} />
              </Link>
            </div>
            <div className="crm-dash-ds__panel-body">
              {data.tasks.length === 0 ? (
                <PanelEmpty title={t('empty.tasks')} hint={t('empty.tasksHint')} />
              ) : (
                data.tasks.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    kindLabel={t(`taskKinds.${task.kind}`)}
                  />
                ))
              )}
            </div>
          </div>

          <div className="crm-dash-ds__panel">
            <div className="crm-dash-ds__panel-head">
              <h3>{t('ops.leads')}</h3>
              <Link href={'/workspaces/crm/leads' as Route} className="crm-dash-ds__view-all">
                {t('viewAll')}
                <IhIcon name="arrowRight" size={11} />
              </Link>
            </div>
            <div className="crm-dash-ds__panel-body">
              {data.leads.length === 0 ? (
                <PanelEmpty title={t('empty.leads')} hint={t('empty.leadsHint')} />
              ) : (
                data.leads.map((lead) => (
                  <LeadRow key={lead.id} lead={lead} newLabel={t('ops.newBadge')} />
                ))
              )}
            </div>
          </div>

          <div className="crm-dash-ds__panel">
            <div className="crm-dash-ds__panel-head">
              <h3>{t('ops.activities')}</h3>
              <Link href={'/workspaces/crm/activities' as Route} className="crm-dash-ds__view-all">
                {t('viewAll')}
                <IhIcon name="arrowRight" size={11} />
              </Link>
            </div>
            <div className="crm-dash-ds__panel-body">
              {data.activities.length === 0 ? (
                <PanelEmpty title={t('empty.activities')} hint={t('empty.activitiesHint')} />
              ) : (
                data.activities.map((item) => <ActivityRow key={item.id} item={item} />)
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="crm-dash-ds__section" aria-label={t('insights.aria')}>
        <div className="crm-dash-ds__insights-row">
          <div className="crm-dash-ds__insights">
            <div className="crm-dash-ds__panel-head">
              <h3>{t('insights.title')}</h3>
            </div>
            {data.insights.length === 0 ? (
              <PanelEmpty title={t('empty.insights')} hint={t('empty.insightsHint')} />
            ) : (
              <div className="crm-dash-ds__insight-list">
                {data.insights.map((insight) => (
                  <Link
                    key={insight.id}
                    href={insight.href as Route}
                    className={`crm-dash-ds__insight is-${insight.tone}`}
                  >
                    <span className="crm-dash-ds__insight-dot" aria-hidden="true" />
                    <div className="crm-dash-ds__insight-text">
                      <strong>{t(`insights.items.${insight.titleKey}`)}</strong>
                      <span>{t(`insights.items.${insight.bodyKey}`)}</span>
                    </div>
                    <span className="crm-dash-ds__insight-go" aria-hidden="true">
                      <IhIcon name="arrowRight" size={11} />
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="crm-dash-ds__chart-panel">
            <div className="crm-dash-ds__panel-head">
              <h3>{t('pipeline.title')}</h3>
              <span className="crm-dash-ds__row-time">{t('pipeline.period')}</span>
            </div>
            <div className="crm-dash-ds__chart-body">
              {data.pipelineTrend.length === 0 ? (
                <PanelEmpty title={t('empty.pipeline')} hint={t('empty.pipelineHint')} />
              ) : (
                <LineChart
                  data={data.pipelineTrend}
                  ariaLabel={t('pipeline.aria')}
                  locale={locale}
                  height={112}
                  format="number"
                />
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="crm-dash-ds__section" aria-label={t('timeline.aria')}>
        <div className="crm-dash-ds__timeline">
          <div className="crm-dash-ds__panel-head">
            <h3>{t('timeline.title')}</h3>
            <Link href={'/workspaces/crm/timeline' as Route} className="crm-dash-ds__view-all">
              {t('viewAll')}
              <IhIcon name="arrowRight" size={11} />
            </Link>
          </div>
          <div className="crm-dash-ds__timeline-list">
            {data.timeline.length === 0 ? (
              <PanelEmpty title={t('empty.timeline')} hint={t('empty.timelineHint')} />
            ) : (
              data.timeline.map((item) => <TimelineRow key={item.id} item={item} />)
            )}
          </div>
        </div>
      </section>

      <section className="crm-dash-ds__section" aria-label={t('meetings.aria')}>
        <div className="crm-dash-ds__section-head">
          <h2>{t('meetings.title')}</h2>
          <Link href={'/workspaces/crm/calendar' as Route} className="crm-dash-ds__view-all">
            {t('viewAll')}
            <IhIcon name="arrowRight" size={11} />
          </Link>
        </div>
        {data.meetings.length === 0 ? (
          <PanelEmpty title={t('empty.meetings')} hint={t('empty.meetingsHint')} />
        ) : (
          <div className="crm-dash-ds__meetings">
            {data.meetings.map((meeting) => (
              <MeetingCard
                key={meeting.id}
                meeting={meeting}
                joinLabel={t('meetings.join')}
                openLabel={t('meetings.open')}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
