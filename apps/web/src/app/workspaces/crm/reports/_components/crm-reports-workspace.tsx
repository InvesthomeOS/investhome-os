'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  REPORTS_KPI_ICONS,
  REPORTS_KPI_ICON_TONES,
  type ReportsAvatarTone,
  type ReportsWorkspacePreview,
} from '../reports-model';
import {
  MonthlyComparisonChart,
  OpportunityFunnel,
  ReportSparkline,
  RevenueTrendChart,
  SourceDonut,
} from './reports-charts';

function TeamAvatar({
  initials,
  tone,
}: {
  initials: string;
  tone: ReportsAvatarTone;
}) {
  return (
    <span className={`crm-reports__avatar is-${tone}`} aria-hidden="true">
      {initials}
    </span>
  );
}

export function CrmReportsWorkspace({
  preview,
  onOpenAi,
}: {
  preview: ReportsWorkspacePreview;
  onOpenAi?: (prompt?: string) => void;
}) {
  const t = useTranslations('crm.reports');
  const [dateRange, setDateRange] = useState(preview.filters.dateRange);
  const [comparison, setComparison] = useState('previousPeriod');
  const [team, setTeam] = useState('all');
  const [user, setUser] = useState('all');
  const [source, setSource] = useState('all');
  const [granularity, setGranularity] = useState('daily');
  const [funnelMode, setFunnelMode] = useState('value');

  const clearFilters = () => {
    setDateRange('rangeWeek');
    setComparison('previousPeriod');
    setTeam('all');
    setUser('all');
    setSource('all');
  };

  const sourceLabels = Object.fromEntries(
    preview.sources.map((s) => [s.key, t(`sources.${s.key}`)]),
  );
  const funnelLabels = Object.fromEntries(
    preview.funnel.map((s) => [s.key, t(`funnel.stages.${s.key}`)]),
  );

  return (
    <div className="crm-reports" data-testid="crm-reports-workspace">
      <header className="crm-reports__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-reports__header-actions">
          <Button variant="primary" size="sm">
            <IhIcon name="plus" size={14} />
            {t('actions.createReport')}
          </Button>
          <Button variant="secondary" size="sm">
            <IhIcon name="documents" size={14} />
            {t('actions.reportLibrary')}
          </Button>
        </div>
      </header>

      <section className="crm-reports__filters" aria-label={t('filters.aria')}>
        <Select
          label={t('filters.dateRange')}
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
        >
          <option value="rangeWeek">{t('filters.datePresets.rangeWeek')}</option>
          <option value="last7">{t('filters.datePresets.last7')}</option>
          <option value="last30">{t('filters.datePresets.last30')}</option>
          <option value="thisQuarter">{t('filters.datePresets.thisQuarter')}</option>
        </Select>
        <Select
          label={t('filters.comparison')}
          value={comparison}
          onChange={(e) => setComparison(e.target.value)}
        >
          <option value="previousPeriod">{t('filters.comparisonOptions.previousPeriod')}</option>
          <option value="previousYear">{t('filters.comparisonOptions.previousYear')}</option>
          <option value="none">{t('filters.comparisonOptions.none')}</option>
        </Select>
        <Select
          label={t('filters.team')}
          value={team}
          onChange={(e) => setTeam(e.target.value)}
        >
          {preview.filters.teams.map((key) => (
            <option key={key} value={key}>
              {t(`filters.teamOptions.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.user')}
          value={user}
          onChange={(e) => setUser(e.target.value)}
        >
          {preview.filters.users.map((key) => (
            <option key={key} value={key}>
              {t(`filters.userOptions.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.source')}
          value={source}
          onChange={(e) => setSource(e.target.value)}
        >
          {preview.filters.sources.map((key) => (
            <option key={key} value={key}>
              {key === 'all' ? t('filters.any') : t(`sources.${key}`)}
            </option>
          ))}
        </Select>
        <button type="button" className="crm-reports__clear" onClick={clearFilters}>
          <IhIcon name="refresh" size={13} />
          {t('filters.clear')}
        </button>
      </section>

      <section className="crm-reports__kpi-row" aria-label={t('kpis.aria')}>
        {preview.kpis.map((kpi) => (
          <article
            key={kpi.key}
            className={`crm-reports__kpi is-${REPORTS_KPI_ICON_TONES[kpi.key]}`}
          >
            <div className="crm-reports__kpi-top">
              <p className="crm-reports__kpi-label">{t(`kpis.${kpi.key}`)}</p>
              <span className="crm-reports__kpi-icon" aria-hidden="true">
                <IhIcon name={REPORTS_KPI_ICONS[kpi.key]} size={16} />
              </span>
            </div>
            <strong className="crm-reports__kpi-value">{kpi.value}</strong>
            <span className={`crm-reports__kpi-delta is-${kpi.deltaTone}`}>{kpi.delta}</span>
            <ReportSparkline
              values={kpi.sparkValues}
              color={kpi.sparkColor}
              ariaLabel={t('kpis.sparkAria', { name: t(`kpis.${kpi.key}`) })}
            />
          </article>
        ))}
      </section>

      <div className="crm-reports__layout">
        <div className="crm-reports__main">
          <section className="crm-reports__grid crm-reports__grid--primary" aria-label={t('sections.analytics')}>
            <article className="crm-reports__card crm-reports__card--wide">
              <header className="crm-reports__card-head">
                <h2>{t('charts.revenueTrend')}</h2>
                <Select
                  aria-label={t('charts.granularity')}
                  value={granularity}
                  onChange={(e) => setGranularity(e.target.value)}
                  className="crm-reports__compact-select"
                >
                  <option value="daily">{t('charts.daily')}</option>
                  <option value="weekly">{t('charts.weekly')}</option>
                </Select>
              </header>
              <RevenueTrendChart
                data={preview.revenueTrend}
                ariaLabel={t('charts.revenueTrendAria')}
                currentLabel={t('charts.thisPeriod')}
                previousLabel={t('charts.previousPeriod')}
              />
            </article>

            <article className="crm-reports__card">
              <header className="crm-reports__card-head">
                <h2>{t('charts.funnel')}</h2>
                <Select
                  aria-label={t('charts.funnelMode')}
                  value={funnelMode}
                  onChange={(e) => setFunnelMode(e.target.value)}
                  className="crm-reports__compact-select"
                >
                  <option value="value">{t('charts.valueBased')}</option>
                  <option value="count">{t('charts.countBased')}</option>
                </Select>
              </header>
              <OpportunityFunnel
                stages={preview.funnel}
                stageLabels={funnelLabels}
                ariaLabel={t('charts.funnelAria')}
              />
            </article>

            <article className="crm-reports__card">
              <header className="crm-reports__card-head">
                <h2>{t('charts.performanceSummary')}</h2>
              </header>
              <ul className="crm-reports__summary" aria-label={t('charts.performanceSummaryAria')}>
                {preview.performanceSummary.map((metric) => (
                  <li key={metric.key}>
                    <span>{t(`performance.${metric.key}`)}</span>
                    <strong>{metric.value}</strong>
                    <em className={`is-${metric.deltaTone}`}>{metric.delta}</em>
                  </li>
                ))}
              </ul>
            </article>
          </section>

          <section className="crm-reports__grid crm-reports__grid--secondary" aria-label={t('sections.operations')}>
            <article className="crm-reports__card">
              <header className="crm-reports__card-head">
                <h2>{t('team.title')}</h2>
              </header>
              <div className="crm-reports__table-wrap">
                <table className="crm-reports__table" aria-label={t('team.aria')}>
                  <thead>
                    <tr>
                      <th>{t('team.columns.user')}</th>
                      <th>{t('team.columns.revenue')}</th>
                      <th>{t('team.columns.opportunities')}</th>
                      <th>{t('team.columns.won')}</th>
                      <th>{t('team.columns.trend')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.team.map((member) => (
                      <tr key={member.id}>
                        <td>
                          <div className="crm-reports__user-cell">
                            <TeamAvatar initials={member.initials} tone={member.tone} />
                            <span>{member.name}</span>
                          </div>
                        </td>
                        <td>{member.revenue}</td>
                        <td>{member.opportunities}</td>
                        <td>{member.won}</td>
                        <td>
                          <ReportSparkline
                            values={member.sparkValues}
                            color={member.trendTone === 'up' ? '#2f8a5b' : '#9aa7af'}
                            ariaLabel={t('team.trendAria', { name: member.name })}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button type="button" className="crm-reports__view-all">
                {t('actions.viewAll')}
                <IhIcon name="chevronRight" size={12} />
              </button>
            </article>

            <article className="crm-reports__card">
              <header className="crm-reports__card-head">
                <h2>{t('charts.monthlyComparison')}</h2>
              </header>
              <MonthlyComparisonChart
                data={preview.monthlyComparison.map((point) => ({
                  ...point,
                  label: t(`charts.months.${point.label}`),
                }))}
                ariaLabel={t('charts.monthlyComparisonAria')}
                currentLabel={t('charts.thisPeriod')}
                previousLabel={t('charts.previousPeriod')}
              />
            </article>

            <article className="crm-reports__card">
              <header className="crm-reports__card-head">
                <h2>{t('goals.title')}</h2>
              </header>
              <ul className="crm-reports__goals" aria-label={t('goals.aria')}>
                {preview.goals.map((goal) => (
                  <li key={goal.key}>
                    <div className="crm-reports__goal-head">
                      <span>{t(`goals.items.${goal.key}`)}</span>
                      <strong>{goal.pct}%</strong>
                    </div>
                    <div
                      className={`crm-reports__goal-track is-${goal.tone}`}
                      role="progressbar"
                      aria-label={t('goals.progressAria', {
                        name: t(`goals.items.${goal.key}`),
                        pct: goal.pct,
                      })}
                      aria-valuenow={goal.pct}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    >
                      <span style={{ width: `${Math.min(goal.pct, 100)}%` }} />
                    </div>
                    <div className="crm-reports__goal-meta">
                      <small>
                        {t('goals.target')}: {goal.target}
                      </small>
                      <small>
                        {t('goals.actual')}: {goal.actual}
                      </small>
                    </div>
                  </li>
                ))}
              </ul>
              <button type="button" className="crm-reports__view-all">
                {t('actions.viewAll')}
                <IhIcon name="chevronRight" size={12} />
              </button>
            </article>
          </section>
        </div>

        <aside className="crm-reports__rail" aria-label={t('rail.aria')}>
          <section className="crm-reports__rail-card">
            <h3>{t('rail.topSources')}</h3>
            <SourceDonut
              slices={preview.sources}
              labels={sourceLabels}
              ariaLabel={t('rail.topSourcesAria')}
            />
          </section>

          <section className="crm-reports__rail-card">
            <h3>{t('rail.quickReports')}</h3>
            <ul className="crm-reports__quick">
              {preview.quickReports.map((report) => (
                <li key={report.key}>
                  <button type="button" className="crm-reports__quick-link">
                    <span className="crm-reports__quick-icon" aria-hidden="true">
                      <IhIcon name={report.icon} size={14} />
                    </span>
                    <span>{t(`quickReports.${report.key}`)}</span>
                    <IhIcon name="chevronRight" size={12} />
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-reports__rail-card crm-reports__rail-card--ai">
            <h3>{t('rail.aiInsights')}</h3>
            <ul className="crm-reports__ai-list">
              {preview.aiInsights.map((insight) => (
                <li key={insight.id}>{t(`aiInsights.${insight.textKey}`)}</li>
              ))}
            </ul>
            <Button
              variant="secondary"
              size="sm"
              className="crm-reports__ai-cta"
              onClick={() => onOpenAi?.(t('rail.aiPrompt'))}
            >
              <IhIcon name="sparkles" size={14} />
              {t('rail.openAi')}
            </Button>
          </section>
        </aside>
      </div>
    </div>
  );
}
