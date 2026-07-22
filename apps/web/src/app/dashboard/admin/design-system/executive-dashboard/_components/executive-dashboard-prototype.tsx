'use client';

import {
  DateRangeControl,
  IconButton,
  MetricCard,
  StatusBadge,
  WidgetMenu,
  WidgetShell,
  RightRailCard,
} from '@investhome/ui';
import type { Route } from 'next';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { useMemo, useState } from 'react';

import {
  AreaChart,
  BarChart,
  DonutChart,
  FunnelChart,
  ProgressChart,
  Sparkline,
  TimelineChart,
} from '@/components/design-system/charts';
import {
  AppPage,
  ContentContainer,
  DashboardGrid,
  PageHeader,
  PageSection,
  RightRail,
  WidgetColumn,
} from '@/components/design-system/layout';
import { IhIcon } from '@/components/icons/ih-icons';

import {
  PROTOTYPE_DEMO_BANNER,
  demoAiItems,
  demoAlerts,
  demoApprovals,
  demoCashTrend,
  demoComms,
  demoDeadlines,
  demoFinancePulse,
  demoFunnel,
  demoInvestorMix,
  demoInvestorPulse,
  demoKpis,
  demoMarketingBars,
  demoMarketingMetrics,
  demoProjects,
  demoQuickActions,
} from './prototype-demo-data';

type DemoState = 'ready' | 'loading' | 'empty' | 'error';

/** Final D1C mobile priority order — documented in executive-dashboard-visual-direction.md */
const MOBILE_ORDER: Record<string, number> = {
  'exec.alerts': 1,
  'exec.kpi_cash': 2,
  'exec.kpi_pipeline': 3,
  'exec.kpi_investors': 4,
  'exec.kpi_open_deals': 5,
  'exec.kpi_projects': 6,
  'exec.ai_decision': 7,
  'exec.cash_trend': 8,
  'exec.tasks_approvals': 9,
  'exec.calendar_deadlines': 10,
  'exec.sales_funnel': 11,
  'exec.investor_pulse': 12,
  'exec.projects_progress': 13,
  'exec.marketing_pulse': 14,
  'exec.communications': 15,
  'exec.quick_actions': 16,
};

const REGISTRY_MAP = [
  'navigation-page-header-ds',
  'primitive-date-range',
  'primitive-icon-button',
  'overlay-widget-menu',
  'data-metric-card',
  'data-widget-shell',
  'chart-area',
  'chart-funnel',
  'chart-donut',
  'chart-progress',
  'chart-sparkline',
  'chart-timeline',
  'chart-bar',
  'data-right-rail-card',
  'layout-dashboard-grid',
  'primitive-status-badge',
] as const;

/**
 * Design-system D1C visual refinement prototype. Demo data only — not production executive.
 */
export function ExecutiveDashboardPrototype() {
  const t = useTranslations('designSystem.executivePrototype');
  const tDs = useTranslations('designSystem');
  const locale = useLocale();
  const [kpiState, setKpiState] = useState<DemoState>('ready');
  const [chartState, setChartState] = useState<DemoState>('ready');
  const [commsAllowed, setCommsAllowed] = useState(true);
  const [range, setRange] = useState({ from: '2026-01-01', to: '2026-07-20' });
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);

  const funnelStages = useMemo(
    () => demoFunnel.map((s) => ({ label: s.label, value: s.value })),
    [],
  );

  const kpiLabels: Record<string, string> = {
    'exec.kpi_cash': t('kpiCash'),
    'exec.kpi_pipeline': t('kpiPipeline'),
    'exec.kpi_investors': t('kpiInvestors'),
    'exec.kpi_open_deals': t('kpiOpenDeals'),
    'exec.kpi_projects': t('kpiProjects'),
  };

  const healthTone = (health: string) => {
    if (health === 'at_risk') return 'danger' as const;
    if (health === 'attention') return 'warning' as const;
    return 'success' as const;
  };

  const healthLabel = (health: string) => {
    if (health === 'at_risk') return t('healthAtRisk');
    if (health === 'attention') return t('healthAttention');
    return t('healthOnTrack');
  };

  const aiKindTone = (kind: string) => {
    if (kind === 'risk') return 'danger' as const;
    if (kind === 'opportunity') return 'success' as const;
    return 'warning' as const;
  };

  const handleRefresh = () => {
    setRefreshedAt(new Date().toISOString());
  };

  return (
    <ContentContainer>
      <AppPage
        data-testid="executive-dashboard-prototype"
        data-prototype-banner={PROTOTYPE_DEMO_BANNER}
        data-sprint="D1C"
        className="ds-exec-proto"
      >
        <PageHeader
          className="ds-exec-proto__header"
          title={t('title')}
          subtitle={t('subtitle')}
          actions={
            <div className="ds-exec-proto__header-actions" data-testid="exec-proto-header-actions">
              <DateRangeControl
                value={range}
                onChange={setRange}
                fromLabel={tDs('from')}
                toLabel={tDs('to')}
              />
              <IconButton label={t('refresh')} variant="ghost" onClick={handleRefresh} data-testid="exec-proto-refresh">
                <IhIcon name="refresh" size="sm" />
              </IconButton>
              <WidgetMenu
                triggerLabel={t('customize')}
                items={[
                  {
                    id: 'layout',
                    label: t('customizeLayout'),
                    onSelect: () => undefined,
                  },
                  {
                    id: 'reset',
                    label: t('customizeReset'),
                    onSelect: () => undefined,
                  },
                ]}
              />
              <StatusBadge tone="warning">{t('demoOnly')}</StatusBadge>
              <Link
                href={'/dashboard/admin/design-system' as Route}
                className="ds-type-caption"
                data-testid="exec-proto-back-link"
              >
                {t('backToShowcase')}
              </Link>
            </div>
          }
        />

        <div className="ds-exec-proto__banner" data-testid="exec-proto-demo-notice" role="note">
          <StatusBadge tone="warning">{t('demoOnly')}</StatusBadge>
          <p className="ds-type-caption">{t('demoNotice')}</p>
          {refreshedAt ? (
            <p className="ds-type-caption" data-testid="exec-proto-refreshed">
              {t('lastRefreshed', { at: refreshedAt })}
            </p>
          ) : null}
        </div>

        <details className="ds-exec-proto__controls" data-testid="exec-proto-state-controls">
          <summary className="ds-type-caption">{t('stateControls')}</summary>
          <div className="ds-showcase__row">
            <button type="button" className="ds-type-caption" onClick={() => setKpiState('ready')}>
              {t('stateReady')}
            </button>
            <button type="button" className="ds-type-caption" onClick={() => setKpiState('loading')}>
              {t('stateLoading')}
            </button>
            <button type="button" className="ds-type-caption" onClick={() => setKpiState('empty')}>
              {t('stateEmpty')}
            </button>
            <button type="button" className="ds-type-caption" onClick={() => setKpiState('error')}>
              {t('stateError')}
            </button>
            <button type="button" className="ds-type-caption" onClick={() => setChartState('ready')}>
              {t('chartsReady')}
            </button>
            <button type="button" className="ds-type-caption" onClick={() => setChartState('empty')}>
              {t('chartsEmpty')}
            </button>
            <button type="button" className="ds-type-caption" onClick={() => setChartState('error')}>
              {t('chartsError')}
            </button>
            <button
              type="button"
              className="ds-type-caption"
              data-testid="exec-proto-comms-permission-toggle"
              onClick={() => setCommsAllowed((v) => !v)}
            >
              {commsAllowed ? t('commsPermissionOn') : t('commsPermissionOff')}
            </button>
          </div>
        </details>

        <ol
          className="ds-exec-proto-mobile-order"
          data-testid="exec-proto-mobile-order"
          aria-label={t('mobileOrderLabel')}
          hidden
        >
          {Object.entries(MOBILE_ORDER)
            .sort((a, b) => a[1] - b[1])
            .map(([id, order]) => (
              <li key={id} data-widget-id={id} data-mobile-order={order}>
                {id}
              </li>
            ))}
        </ol>

        <ul className="ds-exec-proto-registry" data-testid="exec-proto-registry-map" hidden>
          {REGISTRY_MAP.map((id) => (
            <li key={id} data-registry-id={id}>
              {id}
            </li>
          ))}
        </ul>

        {/* L1 — Alerts */}
        <div data-testid="exec-proto-section-alerts">
          <DashboardGrid>
            <WidgetColumn
              span={12}
              data-widget-id="exec.alerts"
              data-mobile-order={MOBILE_ORDER['exec.alerts']}
            >
              <WidgetShell
                title={t('alertsTitle')}
                description={t('alertsDesc')}
                icon={<IhIcon name="alert" size="sm" />}
                status={{ label: t('statusLive'), tone: 'warning' }}
                span={12}
              >
                <ul className="ds-exec-proto-list">
                  {demoAlerts.map((item) => (
                    <li key={item.titleKey} className="ds-exec-proto-list__row">
                      <StatusBadge
                        tone={
                          item.severity === 'critical'
                            ? 'danger'
                            : item.severity === 'warning'
                              ? 'warning'
                              : 'info'
                        }
                      >
                        {item.severity}
                      </StatusBadge>
                      <span>{t(item.titleKey)}</span>
                      <Link href={item.route as Route} className="ds-exec-proto-link">
                        {t('open')}
                      </Link>
                    </li>
                  ))}
                </ul>
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* L2 — KPI strip ≤5 */}
        <div data-testid="exec-proto-section-kpis">
          <DashboardGrid>
            <WidgetColumn span={12}>
              <div className="ds-exec-proto-kpi-strip" data-testid="exec-proto-kpi-strip">
                {demoKpis.map((kpi) => (
                  <div
                    key={kpi.id}
                    data-widget-id={kpi.id}
                    data-mobile-order={MOBILE_ORDER[kpi.id]}
                    className="ds-exec-proto-kpi"
                  >
                    <MetricCard
                      label={kpiLabels[kpi.id] ?? kpi.id}
                      value={kpi.value}
                      trend={kpi.trend}
                      trendLabel={kpi.trendLabel}
                      size="medium"
                      loading={kpiState === 'loading'}
                      empty={kpiState === 'empty'}
                      emptyLabel={t('kpiEmpty')}
                      error={kpiState === 'error'}
                      errorLabel={t('kpiError')}
                      href={kpi.href}
                    />
                    {kpiState === 'ready' ? (
                      <Sparkline
                        values={kpi.sparkline}
                        ariaLabel={kpiLabels[kpi.id] ?? kpi.id}
                        locale={locale}
                        className="ds-exec-proto-kpi__spark"
                      />
                    ) : null}
                  </div>
                ))}
              </div>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* L3/L5 + AI */}
        <div data-testid="exec-proto-section-decision-finance">
          <DashboardGrid>
            <WidgetColumn
              span={8}
              data-widget-id="exec.cash_trend"
              data-mobile-order={MOBILE_ORDER['exec.cash_trend']}
            >
              <WidgetShell
                title={t('cashTrendTitle')}
                description={t('cashTrendDesc')}
                icon={<IhIcon name="finance" size="sm" />}
                span={8}
                state={chartState === 'error' ? 'error' : 'ready'}
                errorMessage={t('chartError')}
                action={
                  <Link href={'/dashboard/finance' as Route} className="ds-type-caption">
                    {t('drillFinance')}
                  </Link>
                }
              >
                <div className="ds-exec-proto-finance-strip" data-testid="exec-proto-finance-strip">
                  <div>
                    <span className="ds-type-caption">{t('financeLiquidity')}</span>
                    <strong className="ds-type-body-small">{demoFinancePulse.liquidity}</strong>
                  </div>
                  <div>
                    <span className="ds-type-caption">{t('financeInflows')}</span>
                    <strong className="ds-type-body-small">{demoFinancePulse.inflows}</strong>
                  </div>
                  <div>
                    <span className="ds-type-caption">{t('financeOutflows')}</span>
                    <strong className="ds-type-body-small">{demoFinancePulse.outflows}</strong>
                  </div>
                  <div>
                    <span className="ds-type-caption">{t('financeCapital')}</span>
                    <strong className="ds-type-body-small">{demoFinancePulse.capital}</strong>
                  </div>
                </div>
                <AreaChart
                  data={chartState === 'empty' ? [] : demoCashTrend}
                  ariaLabel={t('cashTrendTitle')}
                  locale={locale}
                  format="number"
                  height={200}
                  state={chartState === 'error' ? 'error' : undefined}
                  emptyTitle={t('chartEmpty')}
                  className="ds-chart-container--height-large"
                />
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={4}
              data-widget-id="exec.ai_decision"
              data-mobile-order={MOBILE_ORDER['exec.ai_decision']}
              data-testid="exec-proto-ai-widget"
            >
              <WidgetShell
                title={t('aiTitle')}
                description={t('aiDesc')}
                icon={<IhIcon name="sparkles" size="sm" />}
                status={{ label: t('statusAi'), tone: 'ai' }}
                span={4}
                className="ds-exec-proto-ai-shell"
              >
                <ul className="ds-exec-proto-ai-list" data-testid="exec-proto-ai-list">
                  {demoAiItems.map((item) => (
                    <li key={item.titleKey} className="ds-exec-proto-ai-item" data-ai-kind={item.kind}>
                      <div className="ds-exec-proto-ai-item__head">
                        <StatusBadge tone={aiKindTone(item.kind)}>{item.kind}</StatusBadge>
                        <strong className="ds-type-body-small">{t(item.titleKey)}</strong>
                      </div>
                      <p className="ds-type-caption">
                        <span className="ds-exec-proto-meta">{t('aiReason')}: </span>
                        {t(item.reasonKey)}
                      </p>
                      <p className="ds-type-caption">
                        <span className="ds-exec-proto-meta">{t('aiImpact')}: </span>
                        {t(item.impactKey)}
                      </p>
                      <Link href={item.route as Route} className="ds-exec-proto-link">
                        {t(item.actionKey)}
                        <IhIcon name="arrowRight" size="sm" />
                      </Link>
                    </li>
                  ))}
                </ul>
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* L6 — Tasks + Calendar SEPARATE */}
        <div data-testid="exec-proto-section-work">
          <DashboardGrid>
            <WidgetColumn
              span={6}
              data-widget-id="exec.tasks_approvals"
              data-mobile-order={MOBILE_ORDER['exec.tasks_approvals']}
              data-testid="exec-proto-tasks-widget"
            >
              <WidgetShell
                title={t('tasksTitle')}
                description={t('tasksDesc')}
                icon={<IhIcon name="check" size="sm" />}
                span={6}
              >
                <ul className="ds-exec-proto-list">
                  {demoApprovals.map((item) => (
                    <li key={item.titleKey} className="ds-exec-proto-list__row">
                      <span>
                        {t(item.titleKey)} · {item.age}
                      </span>
                      <Link href={item.route as Route} className="ds-exec-proto-link">
                        {t('open')}
                      </Link>
                    </li>
                  ))}
                </ul>
                <p className="ds-type-caption">{t('tasksNote')}</p>
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={6}
              data-widget-id="exec.calendar_deadlines"
              data-mobile-order={MOBILE_ORDER['exec.calendar_deadlines']}
              data-testid="exec-proto-calendar-widget"
            >
              <WidgetShell
                title={t('calendarTitle')}
                description={t('calendarDesc')}
                icon={<IhIcon name="calendar" size="sm" />}
                span={6}
              >
                <TimelineChart
                  events={demoDeadlines.map((d) => ({
                    id: d.id,
                    label: t(d.titleKey),
                    at: d.when,
                  }))}
                  ariaLabel={t('calendarTitle')}
                  locale={locale}
                  emptyTitle={t('chartEmpty')}
                />
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* Sales + Investors related but not merged */}
        <div data-testid="exec-proto-section-pipeline-projects">
          <DashboardGrid>
            <WidgetColumn
              span={6}
              data-widget-id="exec.sales_funnel"
              data-mobile-order={MOBILE_ORDER['exec.sales_funnel']}
              data-testid="exec-proto-sales-widget"
            >
              <WidgetShell
                title={t('salesTitle')}
                description={t('salesDesc')}
                icon={<IhIcon name="sales" size="sm" />}
                span={6}
                action={
                  <Link href={'/dashboard/sales' as Route} className="ds-type-caption">
                    {t('drillSales')}
                  </Link>
                }
              >
                <FunnelChart
                  stages={chartState === 'empty' ? [] : funnelStages}
                  ariaLabel={t('salesTitle')}
                  locale={locale}
                  state={chartState === 'error' ? 'error' : undefined}
                  emptyTitle={t('chartEmpty')}
                />
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={6}
              data-widget-id="exec.investor_pulse"
              data-mobile-order={MOBILE_ORDER['exec.investor_pulse']}
              data-testid="exec-proto-investors-widget"
            >
              <WidgetShell
                title={t('investorsTitle')}
                description={t('investorsDesc')}
                icon={<IhIcon name="investors" size="sm" />}
                span={6}
                action={
                  <Link href={'/dashboard/investors' as Route} className="ds-type-caption">
                    {t('drillInvestors')}
                  </Link>
                }
              >
                <div className="ds-exec-proto-finance-strip ds-exec-proto-finance-strip--3">
                  <div>
                    <span className="ds-type-caption">{t('investorsCommitted')}</span>
                    <strong className="ds-type-body-small">{demoInvestorPulse.committed}</strong>
                  </div>
                  <div>
                    <span className="ds-type-caption">{t('investorsCapacity')}</span>
                    <strong className="ds-type-body-small">{demoInvestorPulse.capacity}</strong>
                  </div>
                  <div>
                    <span className="ds-type-caption">{t('investorsFollowUps')}</span>
                    <strong className="ds-type-body-small">{demoInvestorPulse.followUps}</strong>
                  </div>
                </div>
                <DonutChart
                  data={demoInvestorMix}
                  ariaLabel={t('investorsTitle')}
                  locale={locale}
                />
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* Projects + Marketing */}
        <div data-testid="exec-proto-section-projects-marketing">
          <DashboardGrid>
            <WidgetColumn
              span={6}
              data-widget-id="exec.projects_progress"
              data-mobile-order={MOBILE_ORDER['exec.projects_progress']}
              data-testid="exec-proto-projects-widget"
            >
              <WidgetShell
                title={t('projectsTitle')}
                description={t('projectsDesc')}
                icon={<IhIcon name="projects" size="sm" />}
                span={6}
                action={
                  <Link href={'/dashboard/projects' as Route} className="ds-type-caption">
                    {t('drillProjects')}
                  </Link>
                }
              >
                <ul className="ds-exec-proto-list">
                  {demoProjects.map((p) => (
                    <li key={p.nameKey} className="ds-exec-proto-project">
                      <div className="ds-exec-proto-project__head">
                        <Link href={p.route as Route} className="ds-type-body-small">
                          {t(p.nameKey)}
                        </Link>
                        <StatusBadge tone={healthTone(p.health)}>{healthLabel(p.health)}</StatusBadge>
                      </div>
                      <ProgressChart value={p.progress} ariaLabel={t(p.nameKey)} locale={locale} />
                      <p className="ds-type-caption">
                        <IhIcon name="target" size="sm" /> {t('nextMilestone')}: {t(p.milestoneKey)}
                      </p>
                    </li>
                  ))}
                </ul>
              </WidgetShell>
            </WidgetColumn>
            <WidgetColumn
              span={6}
              data-widget-id="exec.marketing_pulse"
              data-mobile-order={MOBILE_ORDER['exec.marketing_pulse']}
              data-testid="exec-proto-marketing-widget"
            >
              <WidgetShell
                title={t('marketingTitle')}
                description={t('marketingDesc')}
                icon={<IhIcon name="marketing" size="sm" />}
                status={{ label: t('marketingDemo'), tone: 'info' }}
                span={6}
                action={
                  <Link
                    href={'/workspaces/marketing/dashboard' as Route}
                    className="ds-type-caption"
                    data-testid="exec-proto-marketing-cta"
                  >
                    {t('drillMarketing')}
                  </Link>
                }
              >
                <div className="ds-exec-proto-finance-strip ds-exec-proto-finance-strip--3">
                  <div>
                    <span className="ds-type-caption">{t('marketingLeads')}</span>
                    <strong className="ds-type-body-small">{demoMarketingMetrics.leads}</strong>
                  </div>
                  <div>
                    <span className="ds-type-caption">{t('marketingHandoffs')}</span>
                    <strong className="ds-type-body-small">{demoMarketingMetrics.handoffs}</strong>
                  </div>
                  <div>
                    <span className="ds-type-caption">{t('marketingConversion')}</span>
                    <strong className="ds-type-body-small">{demoMarketingMetrics.conversion}</strong>
                  </div>
                </div>
                <BarChart
                  data={demoMarketingBars}
                  ariaLabel={t('marketingTitle')}
                  locale={locale}
                  className="ds-chart-container--height-compact"
                />
                <p className="ds-type-caption">{t('marketingNote')}</p>
              </WidgetShell>
            </WidgetColumn>
          </DashboardGrid>
        </div>

        {/* Communications + right rail */}
        <div data-testid="exec-proto-section-comms">
          <DashboardGrid>
            <WidgetColumn
              span={8}
              data-widget-id="exec.communications"
              data-mobile-order={MOBILE_ORDER['exec.communications']}
              data-testid="exec-proto-comms-widget"
            >
              <WidgetShell
                title={t('commsTitle')}
                description={t('commsDesc')}
                icon={<IhIcon name="inbox" size="sm" />}
                span={8}
                state={commsAllowed ? 'ready' : 'empty'}
                emptyTitle={t('commsPermissionDenied')}
                emptyDescription={t('commsPermissionDeniedDesc')}
              >
                <ul className="ds-exec-proto-list">
                  {demoComms.map((c) => (
                    <li key={c.titleKey} className="ds-exec-proto-list__row">
                      <span>
                        {t(c.titleKey)} ({c.count})
                      </span>
                      <Link href={c.route as Route} className="ds-exec-proto-link">
                        {t('open')}
                      </Link>
                    </li>
                  ))}
                </ul>
              </WidgetShell>
            </WidgetColumn>
            <RightRail data-testid="exec-proto-right-rail">
              <div
                data-widget-id="exec.quick_actions"
                data-mobile-order={MOBILE_ORDER['exec.quick_actions']}
              >
                <RightRailCard title={t('railQuickTitle')}>
                  <ul className="ds-exec-proto-list">
                    {demoQuickActions.map((qa) => (
                      <li key={qa.labelKey}>
                        <Link href={qa.route as Route} className="ds-exec-proto-link">
                          {t(qa.labelKey)}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </RightRailCard>
                <RightRailCard title={t('railFootnoteTitle')}>
                  <p className="ds-type-caption">{t('railFootnoteBody')}</p>
                </RightRailCard>
              </div>
            </RightRail>
          </DashboardGrid>
          <p className="ds-type-caption ds-exec-proto-separation" data-testid="exec-proto-separation-note">
            {t('separationNote')}
          </p>
        </div>

        <PageSection id="exec-proto-responsive-doc" title={t('responsiveDocTitle')}>
          <p className="ds-type-body-small" data-testid="exec-proto-responsive-doc">
            {t('responsiveDocBody')}
          </p>
        </PageSection>
      </AppPage>
    </ContentContainer>
  );
}
