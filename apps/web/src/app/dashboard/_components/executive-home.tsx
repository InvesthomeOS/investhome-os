'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button, EmptyState, ErrorState, KpiCard, LoadingState, Panel, ProgressIndicator } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { metadataForI18n } from '@/lib/api/activity';
import {
  fetchExecutiveActivity,
  fetchExecutiveAiInsights,
  fetchExecutiveAttention,
  fetchExecutiveInvestorOverview,
  fetchExecutiveLeadsPipeline,
  fetchExecutiveProjectPortfolio,
  fetchExecutiveSummary,
  formatCurrencyTotals,
  formatShortDate,
  moduleHref,
  resolvePeriodDates,
  type ActivityItem,
  type AiInsightItem,
  type AttentionItem,
  type LeadsPipelineSummary,
  type ProjectHealthRow,
  type SummaryCard,
} from '@/lib/api/executive';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useCompanyBranding } from '@/lib/company/company-context';
import { useActivityLabels } from '@/lib/i18n/activity-labels';
import { useNotificationLabels } from '@/lib/i18n/notification-labels';
import { canReadMarketing } from '@/lib/marketing/marketing-permissions';
import { metadataForNotification } from '@/lib/api/notifications';
import { useNotifications } from '@/lib/notifications/notification-context';
import { GlobalSearchEntry } from '../executive/_components/command-center/global-search-entry';

type LoadState = 'idle' | 'loading' | 'error' | 'success';

function stripExecutivePrefix(key: string): string {
  return key.startsWith('executive.') ? key.slice('executive.'.length) : key;
}

function fundingProgress(project: ProjectHealthRow): number | null {
  const required = Number(project.equity_required);
  const raised = Number(project.equity_raised);
  if (!Number.isFinite(required) || required <= 0 || !Number.isFinite(raised)) return null;
  return Math.max(0, Math.min(100, (raised / required) * 100));
}

export function ExecutiveHome() {
  const t = useTranslations('home');
  const tExec = useTranslations('executive');
  const tCommon = useTranslations('common');
  const tNav = useTranslations('navigation');
  const locale = useLocale();
  const { user } = useAuth();
  const { displayName } = useCompanyBranding();
  const { items: notifications, unreadCount, openDrawer, canView: canViewNotifications } =
    useNotifications();
  const { getTitle: getNotificationTitle, getPriorityLabel } = useNotificationLabels();
  const { getDescription: getActivityDescription } = useActivityLabels();

  const canExecutive = user ? hasPermission(user, 'executive', 'view') : false;
  const canSales = user
    ? hasPermission(user, 'sales', 'view') || hasPermission(user, 'leads', 'view')
    : false;
  const canProjects = user ? hasPermission(user, 'projects', 'view') : false;
  const canInvestors = user ? hasPermission(user, 'investors', 'view') : false;
  const canActivity = user ? hasPermission(user, 'activity', 'view') : false;

  const period = useMemo(() => resolvePeriodDates('last30Days'), []);

  const [summaryState, setSummaryState] = useState<LoadState>('idle');
  const [summaryCards, setSummaryCards] = useState<SummaryCard[]>([]);
  const [attentionState, setAttentionState] = useState<LoadState>('idle');
  const [attention, setAttention] = useState<AttentionItem[]>([]);
  const [pipelineState, setPipelineState] = useState<LoadState>('idle');
  const [pipeline, setPipeline] = useState<LeadsPipelineSummary | null>(null);
  const [pipelineStages, setPipelineStages] = useState<{ status: string; count: number }[]>([]);
  const [projectsState, setProjectsState] = useState<LoadState>('idle');
  const [projects, setProjects] = useState<ProjectHealthRow[]>([]);
  const [investorsState, setInvestorsState] = useState<LoadState>('idle');
  const [investorMetrics, setInvestorMetrics] = useState<{
    active: number;
    committed: string;
    followUps: number;
  } | null>(null);
  const [activityState, setActivityState] = useState<LoadState>('idle');
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [aiState, setAiState] = useState<LoadState>('idle');
  const [aiItems, setAiItems] = useState<AiInsightItem[]>([]);

  const load = useCallback(async () => {
    if (canExecutive) {
      setSummaryState('loading');
      setAttentionState('loading');
      setAiState('loading');
      try {
        const summary = await fetchExecutiveSummary(period);
        setSummaryCards(summary.cards.slice(0, 4));
        setSummaryState('success');
      } catch {
        setSummaryState('error');
      }
      try {
        const att = await fetchExecutiveAttention(period);
        setAttention(att.items.slice(0, 5));
        setAttentionState('success');
      } catch {
        setAttentionState('error');
      }
      try {
        const ai = await fetchExecutiveAiInsights(period);
        setAiItems([...ai.priorities, ...ai.risks].slice(0, 3));
        setAiState('success');
      } catch {
        setAiState('error');
      }
    }

    if (canSales) {
      setPipelineState('loading');
      try {
        const pipe = await fetchExecutiveLeadsPipeline(period);
        setPipeline(pipe.summary);
        setPipelineStages(pipe.stages.slice(0, 6));
        setPipelineState('success');
      } catch {
        setPipelineState('error');
      }
    }

    if (canProjects) {
      setProjectsState('loading');
      try {
        const portfolio = await fetchExecutiveProjectPortfolio(period);
        setProjects(portfolio.projects.slice(0, 4));
        setProjectsState('success');
      } catch {
        setProjectsState('error');
      }
    }

    if (canInvestors) {
      setInvestorsState('loading');
      try {
        const inv = await fetchExecutiveInvestorOverview(period);
        const active =
          inv.by_status.find((row) => row.status === 'active')?.count ??
          inv.by_status.reduce((sum, row) => sum + row.count, 0);
        setInvestorMetrics({
          active,
          committed: formatCurrencyTotals(inv.total_committed, locale),
          followUps: inv.upcoming_follow_ups.length,
        });
        setInvestorsState('success');
      } catch {
        setInvestorsState('error');
      }
    }

    if (canActivity || canExecutive) {
      setActivityState('loading');
      try {
        const act = await fetchExecutiveActivity(period);
        setActivities(act.items.slice(0, 6));
        setActivityState('success');
      } catch {
        setActivityState('error');
      }
    }
  }, [
    canActivity,
    canExecutive,
    canInvestors,
    canProjects,
    canSales,
    locale,
    period,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  const greetingName = user?.full_name?.split(' ')[0] ?? displayName;
  const dateLabel = new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date());

  const maxStage = Math.max(1, ...pipelineStages.map((s) => s.count));

  const cardLabel = (key: string) => {
    try {
      return tExec(`companyOverview.${key}` as 'companyOverview.active_projects');
    } catch {
      return key;
    }
  };

  const attentionTitle = (item: AttentionItem) => {
    const key = stripExecutivePrefix(item.title_key);
    try {
      return tExec(`${key}` as 'attention.title');
    } catch {
      return item.related_label ?? key;
    }
  };

  const attentionDescription = (item: AttentionItem) => {
    const key = stripExecutivePrefix(item.description_key);
    try {
      return tExec(key as 'attention.overdue_payment.description', metadataForI18n(item.metadata) as never);
    } catch {
      return item.related_label ?? '';
    }
  };

  const activityLabel = (item: ActivityItem) => {
    try {
      return getActivityDescription(
        item.description_key,
        metadataForI18n(item.metadata),
      );
    } catch {
      return item.entity_label ?? item.event_type;
    }
  };

  const aiLabel = (item: AiInsightItem, field: 'title' | 'description') => {
    const raw = field === 'title' ? item.title_key : item.description_key;
    const key = stripExecutivePrefix(raw);
    try {
      return tExec(key as 'ai.priorities', metadataForI18n(item.metadata) as never);
    } catch {
      return field === 'title' ? key : '';
    }
  };

  const quickActions: { href: Route; label: string; icon: IhIconName; show: boolean }[] = [
    {
      href: '/dashboard/leads' as Route,
      label: t('quickActions.createLead'),
      icon: 'plus',
      show: !!(user && hasPermission(user, 'leads', 'create')),
    },
    {
      href: '/dashboard/investors' as Route,
      label: t('quickActions.createInvestor'),
      icon: 'investors',
      show: !!(user && hasPermission(user, 'investors', 'create')),
    },
    {
      href: '/dashboard/projects' as Route,
      label: t('quickActions.addProject'),
      icon: 'projects',
      show: !!(user && hasPermission(user, 'projects', 'create')),
    },
    {
      href: '/workspaces/marketing/campaigns' as Route,
      label: t('quickActions.sendCampaign'),
      icon: 'marketing',
      show: canReadMarketing(user),
    },
    {
      href: '/dashboard/finance' as Route,
      label: t('quickActions.approveExpense'),
      icon: 'finance',
      show: !!(user && hasPermission(user, 'finance', 'view')),
    },
    {
      href: '/workspaces/marketing/reports' as Route,
      label: t('quickActions.openReports'),
      icon: 'barChart',
      show: canReadMarketing(user),
    },
    {
      href: '/dashboard/executive' as Route,
      label: t('quickActions.openExecutive'),
      icon: 'executive',
      show: canExecutive,
    },
    {
      href: '/dashboard/sales' as Route,
      label: t('quickActions.openSales'),
      icon: 'sales',
      show: canSales,
    },
    {
      href: '/dashboard/projects' as Route,
      label: t('quickActions.openProjects'),
      icon: 'projects',
      show: canProjects,
    },
    {
      href: '/dashboard/investors' as Route,
      label: t('quickActions.openInvestors'),
      icon: 'investors',
      show: canInvestors,
    },
    {
      href: '/dashboard/finance' as Route,
      label: t('quickActions.openFinance'),
      icon: 'finance',
      show: user ? hasPermission(user, 'finance', 'view') : false,
    },
    {
      href: '/dashboard/marketing' as Route,
      label: t('quickActions.openMarketing'),
      icon: 'marketing',
      show: canReadMarketing(user),
    },
  ];

  return (
    <main className="ex-home" data-testid="dashboard-home-v2" data-ds-surface="v2">
      <section className="ex-home__hero">
        <div className="ex-home__hero-copy">
          <p className="ex-home__eyebrow">{dateLabel}</p>
          <h1 className="ex-home__title">{t('greeting', { name: greetingName })}</h1>
          <p className="ex-home__subtitle">{t('subtitle')}</p>
        </div>
        <div className="ex-home__hero-actions">
          {canExecutive && (
            <Link
              href={'/dashboard/executive' as Route}
              className="ex-home__hero-btn ex-home__hero-btn--solid"
            >
              <IhIcon name="executive" size="sm" />
              {t('hero.fullExecutive')}
            </Link>
          )}
          <button
            type="button"
            className="ex-home__hero-btn"
            onClick={() => void load()}
            aria-label={t('hero.refresh')}
          >
            <IhIcon name="refresh" size="sm" />
            {t('hero.refresh')}
          </button>
        </div>
      </section>

      <GlobalSearchEntry
        title={t('sections.search')}
        hint={t('sections.searchHint')}
        cta={tExec('commandCenter.search.cta')}
        unavailable={tExec('commandCenter.search.unavailable')}
      />

      {canExecutive && (
        <section aria-label={t('sections.kpis')}>
          {summaryState === 'error' ? (
            <ErrorState
              compact
              message={t('errors.summary')}
              action={
                <Button variant="secondary" size="sm" onClick={() => void load()}>
                  {tCommon('retry')}
                </Button>
              }
            />
          ) : (
            <div className="ex-home__kpi-grid">
              {(summaryState === 'loading' ? [0, 1, 2, 3] : summaryCards).map((card, index) => {
                if (typeof card === 'number') {
                  return (
                    <KpiCard
                      key={card}
                      label={tCommon('loading')}
                      value="—"
                      loading
                      emphasis={index < 2 ? 'primary' : 'secondary'}
                    />
                  );
                }
                const href = moduleHref(card.link_module, card.link_query);
                const value =
                  card.currency_totals && Object.keys(card.currency_totals).length > 0
                    ? formatCurrencyTotals(card.currency_totals, locale)
                    : (card.value ?? '—');
                let delta = tExec('cards.noComparison');
                let deltaTone: 'up' | 'down' | 'neutral' = 'neutral';
                if (
                  card.comparison?.change_available &&
                  card.comparison.change !== null &&
                  card.comparison.change !== undefined
                ) {
                  const change = Number(card.comparison.change);
                  if (!Number.isNaN(change)) {
                    delta = change > 0 ? `+${change}` : `${change}`;
                    deltaTone = change > 0 ? 'up' : change < 0 ? 'down' : 'neutral';
                  }
                }
                return (
                  <KpiCard
                    key={card.key}
                    label={cardLabel(card.key)}
                    value={value}
                    delta={delta}
                    deltaTone={deltaTone}
                    tone={index === 0 ? 'gold' : 'default'}
                    emphasis={index < 2 ? 'primary' : 'secondary'}
                    href={href}
                    icon={
                      <IhIcon name={index === 0 ? 'trendingUp' : 'barChart'} size="md" />
                    }
                  />
                );
              })}
            </div>
          )}
        </section>
      )}

      <div className="ex-home__grid">
        <div className="ex-home__stack">
          <Panel
            title={t('sections.priorities')}
            description={t('sections.prioritiesHint')}
            actions={
              canExecutive ? (
                <Link href={'/dashboard/executive' as Route} className="ex-home__link">
                  {t('viewAll')} <IhIcon name="arrowRight" size="sm" />
                </Link>
              ) : null
            }
          >
            {!canExecutive ? (
              <EmptyState
                icon={<IhIcon name="target" size="lg" />}
                title={t('empty.prioritiesTitle')}
                description={t('empty.prioritiesBody')}
              />
            ) : attentionState === 'loading' ? (
              <LoadingState label={tCommon('loading')} lines={4} />
            ) : attentionState === 'error' ? (
              <ErrorState
                compact
                message={t('errors.priorities')}
                action={
                  <Button variant="secondary" size="sm" onClick={() => void load()}>
                    {tCommon('retry')}
                  </Button>
                }
              />
            ) : attention.length === 0 ? (
              <EmptyState
                icon={<IhIcon name="check" size="lg" />}
                title={t('empty.noPrioritiesTitle')}
                description={t('empty.noPrioritiesBody')}
                action={
                  <Link href={'/dashboard/executive' as Route} className="ex-home__link">
                    {t('quickActions.openExecutive')}
                  </Link>
                }
              />
            ) : (
              <ul className="ex-home__list">
                {attention.map((item) => (
                  <li key={`${item.entity_type}-${item.entity_id}-${item.title_key}`}>
                    <Link
                      href={moduleHref(item.link_module, item.link_query)}
                      className="ex-home__list-item"
                    >
                      <span
                        className={`ex-home__list-icon${
                          item.severity === 'critical'
                            ? ' ex-home__list-icon--critical'
                            : item.severity === 'warning'
                              ? ' ex-home__list-icon--warning'
                              : ''
                        }`}
                      >
                        <IhIcon name="alert" size="sm" />
                      </span>
                      <div className="ex-home__list-body">
                        <p className="ex-home__list-title">{attentionTitle(item)}</p>
                        <p className="ex-home__list-meta">{attentionDescription(item)}</p>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title={t('sections.myWork')} description={t('sections.myWorkHint')}>
            {!canExecutive ? (
              <EmptyState
                icon={<IhIcon name="check" size="lg" />}
                title={t('empty.unavailableTitle')}
                description={t('empty.unavailableBody')}
              />
            ) : (
              <EmptyState
                icon={<IhIcon name="check" size="lg" />}
                title={t('sections.myWork')}
                description={t('sections.myWorkHint')}
                action={
                  <Link href={'/dashboard/executive' as Route} className="ex-home__link">
                    {t('hero.fullExecutive')} <IhIcon name="arrowRight" size="sm" />
                  </Link>
                }
              />
            )}
          </Panel>

          <Panel title={t('sections.projects')} description={t('sections.projectsHint')}>
            {!canProjects ? (
              <EmptyState
                icon={<IhIcon name="projects" size="lg" />}
                title={t('empty.unavailableTitle')}
                description={t('empty.unavailableBody')}
              />
            ) : projectsState === 'loading' ? (
              <LoadingState label={tCommon('loading')} lines={4} />
            ) : projectsState === 'error' ? (
              <ErrorState
                compact
                message={t('errors.projects')}
                action={
                  <Button variant="secondary" size="sm" onClick={() => void load()}>
                    {tCommon('retry')}
                  </Button>
                }
              />
            ) : projects.length === 0 ? (
              <EmptyState
                icon={<IhIcon name="projects" size="lg" />}
                title={t('empty.projectsTitle')}
                description={t('empty.projectsBody')}
                action={
                  <Link href={'/dashboard/projects' as Route} className="ex-home__link">
                    {t('quickActions.openProjects')}
                  </Link>
                }
              />
            ) : (
              <div className="ex-home__stack">
                {projects.map((project) => {
                  const funded = fundingProgress(project);
                  return (
                    <article key={project.project_id} className="ex-home__project">
                      <div className="ex-home__project-top">
                        <div>
                          <h3 className="ex-home__project-name">
                            <Link
                              href={`/dashboard/projects/${project.project_id}` as Route}
                              className="ex-home__project-link"
                            >
                              {project.project_name}
                            </Link>
                          </h3>
                          <p className="ex-home__list-meta">
                            {tExec(`health.${project.health_status}`)}
                            {project.completion_target
                              ? ` · ${formatShortDate(project.completion_target, locale)}`
                              : ''}
                          </p>
                        </div>
                      </div>
                      {funded !== null ? (
                        <ProgressIndicator
                          value={funded}
                          label={t('sections.fundingProgress')}
                          tone={
                            project.health_status === 'on_track'
                              ? 'success'
                              : project.health_status === 'attention'
                                ? 'warning'
                                : 'danger'
                          }
                        />
                      ) : (
                        <p className="ex-home__list-meta">{t('sections.fundingUnavailable')}</p>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </Panel>
        </div>

        <div className="ex-home__stack">
          <Panel
            title={t('sections.meetings')}
            description={t('sections.meetingsHint')}
            badge={t('placeholderBadge')}
          >
            <EmptyState
              icon={<IhIcon name="meeting" size="lg" />}
              title={t('empty.meetingsTitle')}
              description={t('empty.meetingsBody')}
            />
            <span className="ex-home__placeholder-note">{t('placeholderNote')}</span>
          </Panel>

          <Panel
            title={t('sections.notifications')}
            actions={
              canViewNotifications ? (
                <button type="button" className="ex-home__link" onClick={openDrawer}>
                  {t('openNotifications')} <IhIcon name="arrowRight" size="sm" />
                </button>
              ) : null
            }
          >
            {!canViewNotifications ? (
              <EmptyState
                icon={<IhIcon name="bell" size="lg" />}
                title={t('empty.unavailableTitle')}
                description={t('empty.unavailableBody')}
              />
            ) : notifications.filter((n) => !n.read_at).length === 0 ? (
              <EmptyState
                icon={<IhIcon name="inbox" size="lg" />}
                title={t('empty.notificationsTitle')}
                description={t('empty.notificationsBody', { count: unreadCount })}
              />
            ) : (
              <ul className="ex-home__list">
                {notifications
                  .filter((n) => n.status === 'unread' || !n.read_at)
                  .slice(0, 5)
                  .map((n) => (
                    <li key={n.id}>
                      <button type="button" className="ex-home__list-item" onClick={openDrawer}>
                        <span
                          className={`ex-home__list-icon${
                            n.priority === 'critical'
                              ? ' ex-home__list-icon--critical'
                              : n.priority === 'high'
                                ? ' ex-home__list-icon--warning'
                                : ''
                          }`}
                        >
                          <IhIcon name="bell" size="sm" />
                        </span>
                        <div className="ex-home__list-body">
                          <p className="ex-home__list-title">
                            {getNotificationTitle(n.title_key, metadataForNotification(n.metadata))}
                          </p>
                          <p className="ex-home__list-meta">
                            {n.related_label ?? getPriorityLabel(n.priority)}
                          </p>
                        </div>
                      </button>
                    </li>
                  ))}
              </ul>
            )}
          </Panel>

          <Panel
            className="ex-home__ai"
            title={t('sections.ai')}
            description={t('sections.aiHint')}
            badge={aiState === 'success' ? undefined : t('placeholderBadge')}
          >
            {canExecutive && aiState === 'loading' ? (
              <LoadingState label={tCommon('loading')} lines={3} />
            ) : canExecutive && aiItems.length > 0 ? (
              <ul className="ex-home__list">
                {aiItems.map((item) => (
                  <li key={`${item.kind}-${item.title_key}`}>
                    <Link
                      href={moduleHref(item.link_module, item.link_query)}
                      className="ex-home__list-item"
                    >
                      <span className="ex-home__list-icon">
                        <IhIcon name="sparkles" size="sm" />
                      </span>
                      <div className="ex-home__list-body">
                        <p className="ex-home__list-title">{aiLabel(item, 'title')}</p>
                        <p className="ex-home__list-meta">{aiLabel(item, 'description')}</p>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <>
                <p className="ex-home__ai-text">{t('aiPlaceholder')}</p>
                <span className="ex-home__placeholder-note">{t('placeholderNote')}</span>
              </>
            )}
          </Panel>
        </div>
      </div>

      <div className="ex-home__grid--3 ex-home__grid">
        <Panel title={t('sections.sales')} description={t('sections.salesQuestion')}>
          {!canSales ? (
            <EmptyState
              icon={<IhIcon name="sales" size="lg" />}
              title={t('empty.unavailableTitle')}
              description={t('empty.unavailableBody')}
            />
          ) : pipelineState === 'loading' ? (
            <LoadingState label={tCommon('loading')} lines={4} />
          ) : pipelineState === 'error' || !pipeline ? (
            <ErrorState
              compact
              message={t('errors.sales')}
              action={
                <Button variant="secondary" size="sm" onClick={() => void load()}>
                  {tCommon('retry')}
                </Button>
              }
            />
          ) : (
            <>
              <div className="ex-home__metric-row">
                <div className="ex-home__metric ex-home__metric--primary">
                  <span className="ex-home__metric-label">{tExec('sales.total')}</span>
                  <span className="ex-home__metric-value">{pipeline.total}</span>
                </div>
                <div className="ex-home__metric ex-home__metric--primary">
                  <span className="ex-home__metric-label">{tExec('sales.qualified')}</span>
                  <span className="ex-home__metric-value">{pipeline.qualified}</span>
                </div>
                <div className="ex-home__metric ex-home__metric--quiet">
                  <span className="ex-home__metric-label">{tExec('sales.won')}</span>
                  <span className="ex-home__metric-value">{pipeline.won}</span>
                </div>
                <div className="ex-home__metric ex-home__metric--quiet">
                  <span className="ex-home__metric-label">{tExec('sales.proposals')}</span>
                  <span className="ex-home__metric-value">{pipeline.proposals}</span>
                </div>
              </div>
              {pipelineStages.length > 0 && (
                <div className="ih-chart ex-home__chart-wrap">
                  <div className="ih-chart__bars" role="img" aria-label={t('sections.salesQuestion')}>
                    {pipelineStages.map((stage) => (
                      <div key={stage.status} className="ih-chart__bar-col">
                        <span className="ih-chart__bar-value">{stage.count}</span>
                        <div
                          className="ih-chart__bar"
                          style={{ height: `${Math.max(8, (stage.count / maxStage) * 100)}%` }}
                          title={`${stage.status}: ${stage.count}`}
                        />
                        <span className="ih-chart__bar-label">{stage.status}</span>
                      </div>
                    ))}
                  </div>
                  <div className="ih-chart__legend" aria-hidden="true">
                    <span className="ih-chart__legend-item">
                      <span className="ih-chart__legend-swatch" />
                      {t('chart.pipelineVolume')}
                    </span>
                    <span className="ih-chart__legend-item">
                      <span className="ih-chart__legend-swatch ih-chart__legend-swatch--accent" />
                      {t('chart.stageMix')}
                    </span>
                  </div>
                </div>
              )}
              <div className="ex-home__panel-footer">
                <Link href={'/dashboard/sales' as Route} className="ex-home__link">
                  {tNav('modules.sales.title')} <IhIcon name="arrowRight" size="sm" />
                </Link>
              </div>
            </>
          )}
        </Panel>

        <Panel
          title={t('sections.marketing')}
          description={t('sections.marketingHint')}
          badge={t('placeholderBadge')}
        >
          <EmptyState
            icon={<IhIcon name="marketing" size="lg" />}
            title={t('empty.marketingTitle')}
            description={t('empty.marketingBody')}
            action={
              canReadMarketing(user) ? (
                <Link href={'/dashboard/marketing' as Route} className="ex-home__link">
                  {t('quickActions.openMarketing')}
                </Link>
              ) : undefined
            }
          />
          <span className="ex-home__placeholder-note">{t('placeholderNote')}</span>
        </Panel>

        <Panel title={t('sections.investors')} description={t('sections.investorsQuestion')}>
          {!canInvestors ? (
            <EmptyState
              icon={<IhIcon name="investors" size="lg" />}
              title={t('empty.unavailableTitle')}
              description={t('empty.unavailableBody')}
            />
          ) : investorsState === 'loading' ? (
            <LoadingState label={tCommon('loading')} lines={4} />
          ) : investorsState === 'error' || !investorMetrics ? (
            <ErrorState
              compact
              message={t('errors.investors')}
              action={
                <Button variant="secondary" size="sm" onClick={() => void load()}>
                  {tCommon('retry')}
                </Button>
              }
            />
          ) : (
            <>
              <div className="ex-home__metric-row">
                <div className="ex-home__metric ex-home__metric--primary">
                  <span className="ex-home__metric-label">{tExec('investors.active')}</span>
                  <span className="ex-home__metric-value">{investorMetrics.active}</span>
                </div>
                <div className="ex-home__metric ex-home__metric--quiet">
                  <span className="ex-home__metric-label">{tExec('investors.followUps')}</span>
                  <span className="ex-home__metric-value">{investorMetrics.followUps}</span>
                </div>
              </div>
              <div className="ex-home__metric ex-home__metric--primary ex-home__panel-footer">
                <span className="ex-home__metric-label">{tExec('investors.committed')}</span>
                <span className="ex-home__metric-value">{investorMetrics.committed}</span>
              </div>
              <div className="ex-home__panel-footer">
                <Link href={'/dashboard/investors' as Route} className="ex-home__link">
                  {tExec('investors.viewAll')} <IhIcon name="arrowRight" size="sm" />
                </Link>
              </div>
            </>
          )}
        </Panel>
      </div>

      <div className="ex-home__grid">
        <Panel title={t('sections.activity')} description={t('sections.activityHint')}>
          {activityState === 'loading' ? (
            <LoadingState label={tCommon('loading')} lines={5} />
          ) : activityState === 'error' ? (
            <ErrorState
              compact
              message={t('errors.activity')}
              action={
                <Button variant="secondary" size="sm" onClick={() => void load()}>
                  {tCommon('retry')}
                </Button>
              }
            />
          ) : activities.length === 0 ? (
            <EmptyState
              icon={<IhIcon name="activity" size="lg" />}
              title={t('empty.activityTitle')}
              description={t('empty.activityBody')}
              action={
                canActivity ? (
                  <Link href={'/dashboard/activity' as Route} className="ex-home__link">
                    {tNav('activity')}
                  </Link>
                ) : undefined
              }
            />
          ) : (
            <ul className="ex-home__list">
              {activities.map((item) => (
                <li key={item.id}>
                  <div className="ex-home__list-item">
                    <span className="ex-home__list-icon">
                      <IhIcon name="clock" size="sm" />
                    </span>
                    <div className="ex-home__list-body">
                      <p className="ex-home__list-title">{activityLabel(item)}</p>
                      <p className="ex-home__list-meta">
                        {item.actor ? `${item.actor} · ` : ''}
                        {formatShortDate(item.created_at, locale)}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={t('sections.quickActions')} description={t('sections.quickActionsHint')}>
          <div className="ex-home__actions">
            {quickActions
              .filter((action) => action.show)
              .map((action) => (
                <Link key={`${action.href}-${action.label}`} href={action.href} className="ex-home__action">
                  <span className="ex-home__action-icon">
                    <IhIcon name={action.icon} size="md" />
                  </span>
                  <span className="ex-home__action-label">{action.label}</span>
                </Link>
              ))}
            {quickActions.every((a) => !a.show) && (
              <EmptyState
                icon={<IhIcon name="quickAction" size="lg" />}
                title={t('empty.unavailableTitle')}
                description={t('empty.unavailableBody')}
              />
            )}
          </div>
        </Panel>
      </div>
    </main>
  );
}
