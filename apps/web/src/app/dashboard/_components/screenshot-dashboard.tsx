'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import { useScreenshotDashboardInteractions } from './screenshot-dashboard-interactions';
import { useScreenshotDashboardPreferences } from './screenshot-dashboard-preferences';

type Kpi = {
  labelKey: string;
  value: string;
  change: string;
  direction: 'up' | 'down';
  icon: IhIconName;
};

const KPI_DATA: readonly Kpi[] = [
  { labelKey: 'newLeads', value: '12', change: '20%', direction: 'up', icon: 'investors' },
  { labelKey: 'followUps', value: '8', change: '14%', direction: 'up', icon: 'inbox' },
  { labelKey: 'tasks', value: '5', change: '17%', direction: 'down', icon: 'check' },
  { labelKey: 'meetings', value: '3', change: '25%', direction: 'up', icon: 'calendar' },
];

const FUNNEL_DATA = [
  { labelKey: 'newLeads', count: 120, percent: 100 },
  { labelKey: 'contacted', count: 84, percent: 70 },
  { labelKey: 'qualified', count: 48, percent: 40 },
  { labelKey: 'proposal', count: 26, percent: 22 },
  { labelKey: 'closedWon', count: 15, percent: 12 },
] as const;

const SALES_DATA = [
  ['jan', 37],
  ['feb', 46],
  ['mar', 55],
  ['apr', 68],
  ['may', 79],
  ['jun', 57],
  ['jul', 51],
  ['aug', 44],
  ['sep', 50],
  ['oct', 57],
  ['nov', 69],
  ['dec', 74],
] as const;

const PROJECT_DATA = [
  { name: 'Marina Heights', location: 'Dubai Marina', progress: 65, scene: 'marina' },
  { name: 'Greenview Residences', location: 'Dubai Hills Estate', progress: 40, scene: 'green' },
  { name: 'Sunset Boulevard', location: 'Jumeirah Village Circle', progress: 25, scene: 'sunset' },
] as const;

const AI_ACTIONS: ReadonlyArray<{
  key: 'priorities' | 'portfolio' | 'podcast' | 'risks' | 'task';
  icon: IhIconName;
}> = [
  { key: 'priorities', icon: 'sparkles' },
  { key: 'portfolio', icon: 'projects' },
  { key: 'podcast', icon: 'activity' },
  { key: 'risks', icon: 'admin' },
  { key: 'task', icon: 'check' },
];

function ArrowLink({ href, children }: { href: Route; children: React.ReactNode }) {
  return (
    <Link href={href} className="screenshot-dashboard__link">
      {children}
      <IhIcon name="arrowRight" size={11} />
    </Link>
  );
}

function BuildingThumbnail({ scene }: { scene: string }) {
  return (
    <span className={`screenshot-dashboard__project-image is-${scene}`} aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
      <i />
    </span>
  );
}

export function ScreenshotDashboard() {
  const t = useTranslations('screenshotDashboard');
  const locale = useLocale();
  const { openAi } = useScreenshotDashboardInteractions();
  const { density, formatUsdCurrency } = useScreenshotDashboardPreferences();
  const dateLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  const dateValue = new Date(2025, 4, 26);
  const dashboardDate = new Intl.DateTimeFormat(dateLocale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(dateValue);
  const dashboardWeekday = new Intl.DateTimeFormat(dateLocale, { weekday: 'long' }).format(
    dateValue,
  );

  return (
    <main
      className="screenshot-dashboard"
      data-testid="screenshot-dashboard"
      data-dashboard-version="screenshot-dashboard-v1-final"
      data-density={density}
      data-currency="USD"
    >
      <section className="screenshot-dashboard__intro">
        <div className="screenshot-dashboard__greeting">
          <h1>{t('intro.greeting')}</h1>
          <p>{t('intro.subtitle')}</p>
        </div>
        <nav className="screenshot-dashboard__intro-ai" aria-label={t('ai.title')}>
          {AI_ACTIONS.map((action, index) => (
            <button
              key={action.key}
              type="button"
              className={index === 0 ? 'is-featured' : undefined}
              onClick={() => openAi(t(`ai.actions.${action.key}`))}
            >
              <IhIcon name={action.icon} size={14} />
              <span>{t(`ai.actions.${action.key}`)}</span>
            </button>
          ))}
          <button
            type="button"
            className="screenshot-dashboard__intro-ai-primary"
            onClick={() => openAi()}
          >
            <IhIcon name="sparkles" size={13} />
            {t('ai.title')}
          </button>
        </nav>
        <button
          type="button"
          className="screenshot-dashboard__date"
          aria-label={`${dashboardDate}, ${dashboardWeekday}`}
        >
          <IhIcon name="calendar" size={14} />
          <span className="screenshot-dashboard__date-copy">
            <strong>{dashboardDate}</strong>
            <small>{dashboardWeekday}</small>
          </span>
          <IhIcon name="chevronDown" size={11} />
        </button>
      </section>

      <section className="screenshot-dashboard__kpi-grid" aria-label={t('kpis.ariaLabel')}>
        {KPI_DATA.map((item) => (
          <article className="screenshot-dashboard__kpi" key={item.labelKey}>
            <span className="screenshot-dashboard__kpi-icon">
              <IhIcon name={item.icon} size={20} />
            </span>
            <div className="screenshot-dashboard__kpi-copy">
              <span>{t(`kpis.${item.labelKey}`)}</span>
              <strong>{item.value}</strong>
              <small className={`is-${item.direction}`}>
                {item.direction === 'up' ? '▲' : '▼'} {item.change}
                <em> {t('kpis.yesterday')}</em>
              </small>
            </div>
          </article>
        ))}
      </section>

      <section className="screenshot-dashboard__row screenshot-dashboard__row--middle">
        <article className="screenshot-dashboard__card screenshot-dashboard__funnel">
          <h2>{t('funnel.title')}</h2>
          <div className="screenshot-dashboard__funnel-list">
            {FUNNEL_DATA.map((stage) => (
              <div className="screenshot-dashboard__funnel-stage" key={stage.labelKey}>
                <span>{t(`funnel.${stage.labelKey}`)}</span>
                <strong>{stage.count}</strong>
                <span className="screenshot-dashboard__funnel-track" aria-hidden="true">
                  <span style={{ width: `${stage.percent}%` }} />
                </span>
                <small>{stage.percent}%</small>
              </div>
            ))}
          </div>
          <ArrowLink href={'/dashboard/sales' as Route}>{t('funnel.viewAll')}</ArrowLink>
        </article>

        <article className="screenshot-dashboard__card screenshot-dashboard__availability">
          <h2>{t('availability.title')}</h2>
          <div className="screenshot-dashboard__availability-body">
            <div
              className="screenshot-dashboard__donut"
              role="img"
              aria-label={t('availability.ariaLabel')}
            >
              <div>
                <strong>320</strong>
                <small>{t('availability.total')}</small>
              </div>
            </div>
            <ul className="screenshot-dashboard__availability-legend">
              <li>
                <i className="is-available" />
                <span>
                  {t('availability.available')}
                  <strong>160 (50%)</strong>
                </span>
              </li>
              <li>
                <i className="is-reserved" />
                <span>
                  {t('availability.reserved')}
                  <strong>96 (30%)</strong>
                </span>
              </li>
              <li>
                <i className="is-sold" />
                <span>
                  {t('availability.sold')}
                  <strong>64 (20%)</strong>
                </span>
              </li>
            </ul>
          </div>
          <ArrowLink href={'/dashboard/inventory' as Route}>
            {t('availability.viewInventory')}
          </ArrowLink>
        </article>
      </section>

      <section className="screenshot-dashboard__row screenshot-dashboard__row--bottom">
        <article className="screenshot-dashboard__card screenshot-dashboard__sales-chart">
          <header className="screenshot-dashboard__card-header">
            <h2>{t('sales.title')}</h2>
            <button type="button">
              {t('sales.thisYear')} <IhIcon name="chevronDown" size={10} />
            </button>
          </header>
          <div className="screenshot-dashboard__chart-area">
            <div className="screenshot-dashboard__chart-axis" aria-hidden="true">
              {/* Fixed demo labels — avoid Node/browser compact Intl hydration mismatches */}
              <span>$2.0M</span>
              <span>$1.5M</span>
              <span>$1.0M</span>
              <span>$0.5M</span>
              <span>$0</span>
            </div>
            <div className="screenshot-dashboard__bars">
              {SALES_DATA.map(([monthKey, height]) => (
                <div className="screenshot-dashboard__bar-column" key={monthKey}>
                  <span style={{ height: `${height}%` }} />
                  <small>{t(`sales.months.${monthKey}`)}</small>
                </div>
              ))}
            </div>
          </div>
          <div className="screenshot-dashboard__chart-key">
            <i /> {t('sales.legend')} (USD)
          </div>
        </article>

        <article className="screenshot-dashboard__card screenshot-dashboard__projects">
          <header className="screenshot-dashboard__card-header">
            <h2>{t('projects.title')}</h2>
            <ArrowLink href={'/dashboard/projects' as Route}>{t('projects.viewAll')}</ArrowLink>
          </header>
          <div className="screenshot-dashboard__project-list">
            {PROJECT_DATA.map((project) => (
              <article className="screenshot-dashboard__project-row" key={project.name}>
                <BuildingThumbnail scene={project.scene} />
                <div className="screenshot-dashboard__project-copy">
                  <strong>{project.name}</strong>
                  <small>{project.location}</small>
                </div>
                <span className="screenshot-dashboard__project-progress" aria-hidden="true">
                  <span style={{ width: `${project.progress}%` }} />
                </span>
                <strong className="screenshot-dashboard__project-value">{project.progress}%</strong>
              </article>
            ))}
          </div>
          <ArrowLink href={'/dashboard/projects' as Route}>{t('projects.viewAll')}</ArrowLink>
        </article>
      </section>

      <section className="screenshot-dashboard__widget-row" aria-label={t('widgets.ariaLabel')}>
        <article className="screenshot-dashboard__card screenshot-dashboard__compact-widget">
          <header>
            <span className="screenshot-dashboard__widget-icon">
              <IhIcon name="calendar" size={15} />
            </span>
            <h2>{t('widgets.daily.title')}</h2>
          </header>
          <dl>
            <div>
              <dt>{t('widgets.daily.meetings')}</dt>
              <dd>3</dd>
            </div>
            <div>
              <dt>{t('widgets.daily.followUps')}</dt>
              <dd>8</dd>
            </div>
            <div>
              <dt>{t('widgets.daily.overdueTasks')}</dt>
              <dd className="is-warning">2</dd>
            </div>
          </dl>
        </article>

        <article className="screenshot-dashboard__card screenshot-dashboard__compact-widget">
          <header>
            <span className="screenshot-dashboard__widget-icon">
              <IhIcon name="finance" size={15} />
            </span>
            <h2>{t('widgets.finance.title')}</h2>
          </header>
          <dl>
            <div>
              <dt>{t('widgets.finance.cash')}</dt>
              <dd suppressHydrationWarning>{formatUsdCurrency(2_400_000)}</dd>
            </div>
            <div>
              <dt>{t('widgets.finance.payments')}</dt>
              <dd suppressHydrationWarning>{formatUsdCurrency(680_000)}</dd>
            </div>
            <div>
              <dt>{t('widgets.finance.collections')}</dt>
              <dd suppressHydrationWarning>{formatUsdCurrency(1_200_000)}</dd>
            </div>
          </dl>
        </article>

        <article className="screenshot-dashboard__card screenshot-dashboard__compact-widget screenshot-dashboard__alerts">
          <header>
            <span className="screenshot-dashboard__widget-icon is-alert">
              <IhIcon name="alert" size={15} />
            </span>
            <h2>{t('widgets.alerts.title')}</h2>
          </header>
          <ul>
            <li>
              <i />
              {t('widgets.alerts.fundingGap')}
            </li>
            <li>
              <i />
              {t('widgets.alerts.delayedStage')}
            </li>
            <li>
              <i />
              {t('widgets.alerts.missingDocument')}
            </li>
            <li>
              <i />
              {t('widgets.alerts.expiringReservation')}
            </li>
          </ul>
        </article>
      </section>
    </main>
  );
}
