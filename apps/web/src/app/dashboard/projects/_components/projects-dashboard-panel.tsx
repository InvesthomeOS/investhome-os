'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  fetchProjectsDashboard,
  formatMetricCurrency,
  formatNumber,
  formatShortDate,
  toDashboardFilters,
  type AlertSeverity,
  type ProjectAlertItem,
  type ProjectDashboardResponse,
  type ProjectFilters,
  type ProjectMilestoneItem,
  type ProjectActivityItem,
  type ProjectRiskLevel,
} from '@/lib/api/projects';
import { useProjectLabels } from '@/lib/i18n/project-labels';

interface ProjectsDashboardPanelProps {
  filters: ProjectFilters;
  locale: string;
  canViewFinancials: boolean;
  onOpenProject: (projectId: string) => void;
  onRefresh?: () => void;
  /** Bump this value to force a refetch without changing filters (e.g. a manual refresh click). */
  refreshToken?: number;
}

const SEVERITY_BADGE: Record<AlertSeverity, string> = {
  info: 'ih-badge--info',
  low: 'ih-badge--info',
  medium: 'ih-badge--warning',
  high: 'ih-badge--danger',
  critical: 'ih-badge--danger',
};

const RISK_BADGE: Record<ProjectRiskLevel, string> = {
  low: 'ih-badge--success',
  medium: 'ih-badge--warning',
  high: 'ih-badge--danger',
  critical: 'ih-badge--danger',
};

function KpiCard({
  label,
  value,
  note,
}: {
  label: string;
  value: React.ReactNode;
  note?: string;
}) {
  return (
    <article className="investors__stat-card projects-dashboard__kpi">
      <p>{label}</p>
      <strong>{value}</strong>
      {note && <span className="projects-dashboard__kpi-note">{note}</span>}
    </article>
  );
}

function MiniProgressBar({ value }: { value: number | null }) {
  const pct = value === null ? 0 : Math.min(100, Math.max(0, value));
  return (
    <div className="projects-dashboard__mini-bar">
      <div className="projects-dashboard__mini-bar-track">
        <div className="projects-dashboard__mini-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function DistributionBars({
  data,
  getLabel,
}: {
  data: Record<string, number>;
  getLabel: (key: string) => string;
}) {
  const entries = useMemo(
    () =>
      Object.entries(data)
        .filter(([, count]) => count > 0)
        .sort((a, b) => b[1] - a[1]),
    [data],
  );
  const max = entries.length ? Math.max(...entries.map(([, count]) => count)) : 0;

  if (entries.length === 0) return null;

  return (
    <div className="projects-dashboard__bars">
      {entries.map(([key, count]) => (
        <div key={key} className="projects-dashboard__bar-row">
          <span className="projects-dashboard__bar-label">{getLabel(key)}</span>
          <div className="projects-dashboard__bar-track">
            <div
              className="projects-dashboard__bar-fill"
              style={{ width: max > 0 ? `${(count / max) * 100}%` : '0%' }}
            />
          </div>
          <span className="projects-dashboard__bar-value">{count}</span>
        </div>
      ))}
    </div>
  );
}

export function ProjectsDashboardPanel({
  filters,
  locale,
  canViewFinancials,
  onOpenProject,
  onRefresh,
  refreshToken,
}: ProjectsDashboardPanelProps) {
  const t = useTranslations('projects');
  const tCommon = useTranslations('common');
  const { getStatusLabel } = useProjectLabels();

  const [data, setData] = useState<ProjectDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const dashboardFilters = useMemo(() => toDashboardFilters(filters), [filters]);
  const filtersKey = useMemo(() => JSON.stringify(dashboardFilters), [dashboardFilters]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchProjectsDashboard(dashboardFilters);
      setData(response);
    } catch {
      setError(t('dashboardLoadError'));
      setData(null);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey, t]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey, refreshToken]);

  const handleRetry = () => {
    void load();
    onRefresh?.();
  };

  const showFinancials = canViewFinancials && Boolean(data?.financials);
  const financials = showFinancials ? data?.financials ?? null : null;

  const constructionRows = data?.construction.projects.slice(0, 8) ?? [];
  const salesFunnel = data
    ? [
        { key: 'available', label: t('charts.salesAvailable'), metric: data.sales.available_units },
        { key: 'reserved', label: t('charts.salesReserved'), metric: data.sales.reserved_units },
        {
          key: 'under_contract',
          label: t('charts.salesUnderContract'),
          metric: data.sales.under_contract_units,
        },
        { key: 'sold', label: t('charts.salesSold'), metric: data.sales.sold_units },
      ]
    : [];
  const salesMax = Math.max(
    1,
    ...salesFunnel.map((item) => (item.metric.available ? Number(item.metric.value ?? 0) : 0)),
  );

  const notAvailable = t('notAvailable');

  if (loading && !data) {
    return (
      <section className="dashboard__panel projects-dashboard">
        <div className="projects-dashboard__skeleton-grid">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="projects-dashboard__skeleton" />
          ))}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="dashboard__panel projects-dashboard">
        <div className="leads__state leads__state--error">
          <p>{error}</p>
          <button type="button" className="leads__button leads__button--secondary" onClick={handleRetry}>
            {tCommon('retry')}
          </button>
        </div>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="dashboard__panel projects-dashboard">
        <p className="dashboard__placeholder">{t('emptyDashboard')}</p>
      </section>
    );
  }

  const { portfolio } = data;
  const warnings = data.meta.partial_data_warnings;

  return (
    <section className="dashboard__panel projects-dashboard">
      <div className="projects-dashboard__header">
        <div>
          <h2 className="projects-dashboard__title">{t('title')}</h2>
          <p className="projects-dashboard__updated">
            {t('lastUpdated', { date: formatShortDate(data.meta.generated_at, locale) })}
          </p>
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="projects-dashboard__warnings" role="status">
          <strong>{t('warnings')}</strong>
          <ul>
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="projects-dashboard__kpis">
        <KpiCard label={t('kpi.activeProjects')} value={formatNumber(portfolio.active_projects, locale)} />
        {showFinancials && (
          <KpiCard
            label={t('kpi.expectedRevenue')}
            value={formatMetricCurrency(financials?.expected_revenue, locale, notAvailable)}
          />
        )}
        {showFinancials && (
          <KpiCard
            label={t('kpi.forecastCost')}
            value={formatMetricCurrency(financials?.forecast_cost, locale, notAvailable)}
          />
        )}
        {showFinancials && (
          <KpiCard
            label={t('kpi.expectedProfit')}
            value={formatMetricCurrency(financials?.expected_profit, locale, notAvailable)}
          />
        )}
        {showFinancials && (
          <KpiCard
            label={t('kpi.fundingGap')}
            value={formatMetricCurrency(financials?.funding_gap, locale, notAvailable)}
          />
        )}
        {showFinancials && (
          <KpiCard
            label={t('kpi.cashPosition')}
            value={formatMetricCurrency(financials?.cash_position, locale, notAvailable)}
          />
        )}
        {showFinancials && (
          <KpiCard
            label={t('kpi.need30')}
            value={formatMetricCurrency(financials?.need_30_days, locale, notAvailable)}
          />
        )}
        <KpiCard label={t('kpi.projectsAtRisk')} value={formatNumber(portfolio.projects_at_risk, locale)} />
      </div>
      {!canViewFinancials && (
        <p className="projects-dashboard__restricted-note">{t('restricted')}</p>
      )}

      <div className="projects-dashboard__charts">
        <article className="projects-dashboard__chart-card">
          <h3>{t('charts.statusDistribution')}</h3>
          <DistributionBars data={portfolio.status_distribution} getLabel={getStatusLabel} />
        </article>

        <article className="projects-dashboard__chart-card">
          <h3>{t('charts.constructionProgress')}</h3>
          {constructionRows.length === 0 ? (
            <p className="dashboard__placeholder">{t('emptyDashboard')}</p>
          ) : (
            <ul className="projects-dashboard__construction-list">
              {constructionRows.map((row) => (
                <li key={row.project_id}>
                  <button
                    type="button"
                    className="projects-dashboard__construction-row"
                    onClick={() => onOpenProject(row.project_id)}
                  >
                    <span className="projects-dashboard__construction-name">{row.project_name}</span>
                    <MiniProgressBar
                      value={row.completion_percentage === null ? null : Number(row.completion_percentage)}
                    />
                    <span className={`ih-badge ${RISK_BADGE[row.risk]}`}>{t(`risk.${row.risk}`)}</span>
                    {row.is_delayed && (
                      <span className="ih-badge ih-badge--danger">{t('charts.delayed')}</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="projects-dashboard__chart-card">
          <h3>{t('charts.salesFunnel')}</h3>
          {salesFunnel.every((item) => !item.metric.available) ? (
            <p className="dashboard__placeholder">{notAvailable}</p>
          ) : (
            <div className="projects-dashboard__funnel">
              {salesFunnel.map((item) => {
                const value = item.metric.available ? Number(item.metric.value ?? 0) : null;
                return (
                  <div key={item.key} className="projects-dashboard__funnel-row">
                    <span className="projects-dashboard__funnel-label">{item.label}</span>
                    <div className="projects-dashboard__funnel-track">
                      <div
                        className="projects-dashboard__funnel-fill"
                        style={{ width: value === null ? '0%' : `${(value / salesMax) * 100}%` }}
                      />
                    </div>
                    <span className="projects-dashboard__funnel-value">
                      {value === null ? notAvailable : formatNumber(value, locale)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </article>
      </div>

      {showFinancials ? (
        <div className="projects-dashboard__panels">
          <PanelShell title={t('executivePanels.attention')}>
            {(financials?.projects_requiring_attention?.length ?? 0) === 0 ? (
              <p className="dashboard__placeholder">{t('executivePanels.emptyAttention')}</p>
            ) : (
              <ul className="projects-dashboard__alert-list">
                {(financials?.projects_requiring_attention ?? []).map((item) => {
                  const projectId = String(item.project_id ?? '');
                  return (
                    <li key={projectId}>
                      <button type="button" onClick={() => onOpenProject(projectId)}>
                        <strong>{String(item.project_name ?? '')}</strong>
                        <span>{String(item.reason ?? item.health ?? '')}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </PanelShell>
          <PanelShell title={t('executivePanels.upcomingCash')}>
            {(financials?.upcoming_large_cash_events?.length ?? 0) === 0 ? (
              <p className="dashboard__placeholder">{t('executivePanels.emptyUpcomingCash')}</p>
            ) : (
              <ul className="projects-dashboard__alert-list">
                {(financials?.upcoming_large_cash_events ?? []).map((item, index) => {
                  const projectId = String(item.project_id ?? '');
                  return (
                    <li key={`${projectId}-${index}`}>
                      <button type="button" onClick={() => onOpenProject(projectId)}>
                        <strong>
                          {String(item.project_name ?? '')} · {String(item.label ?? '')}
                        </strong>
                        <span>
                          {formatMetricCurrency(
                            {
                              value: item.amount as string | number | null,
                              available: item.amount != null,
                              reason: null,
                            },
                            locale,
                            notAvailable,
                          )}{' '}
                          · {String(item.direction ?? '')}
                          {item.expected_date
                            ? ` · ${formatShortDate(String(item.expected_date), locale)}`
                            : ''}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </PanelShell>
        </div>
      ) : null}

      <div className="projects-dashboard__panels">
        <AlertsPanel alerts={data.alerts} onOpenProject={onOpenProject} />
        <MilestonesPanel milestones={data.milestones} locale={locale} onOpenProject={onOpenProject} />
        <ActivityPanel activity={data.activity} locale={locale} onOpenProject={onOpenProject} />
      </div>
    </section>
  );
}

function PanelShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <article className="projects-dashboard__panel-card">
      <h3>{title}</h3>
      {children}
    </article>
  );
}

function AlertsPanel({
  alerts,
  onOpenProject,
}: {
  alerts: ProjectAlertItem[];
  onOpenProject: (projectId: string) => void;
}) {
  const t = useTranslations('projects');

  return (
    <PanelShell title={t('panels.alerts')}>
      {alerts.length === 0 ? (
        <p className="dashboard__placeholder">{t('emptyDashboard')}</p>
      ) : (
        <ul className="projects-dashboard__list">
          {alerts.map((alert) => (
            <li key={alert.id} className="projects-dashboard__list-item">
              <button
                type="button"
                className="projects-dashboard__list-button"
                onClick={() => onOpenProject(alert.project_id)}
              >
                <div className="projects-dashboard__list-header">
                  <span className={`ih-badge ${SEVERITY_BADGE[alert.severity]}`}>
                    {t(`severity.${alert.severity}`)}
                  </span>
                  <span className="projects-dashboard__list-title">{alert.title}</span>
                </div>
                <p className="projects-dashboard__list-message">{alert.message}</p>
                <p className="projects-dashboard__list-meta">{alert.project_name}</p>
                {alert.recommended_action && (
                  <p className="projects-dashboard__list-action">{alert.recommended_action}</p>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </PanelShell>
  );
}

function MilestonesPanel({
  milestones,
  locale,
  onOpenProject,
}: {
  milestones: ProjectMilestoneItem[];
  locale: string;
  onOpenProject: (projectId: string) => void;
}) {
  const t = useTranslations('projects');

  return (
    <PanelShell title={t('panels.milestones')}>
      {milestones.length === 0 ? (
        <p className="dashboard__placeholder">{t('emptyDashboard')}</p>
      ) : (
        <ul className="projects-dashboard__list">
          {milestones.map((milestone) => (
            <li key={milestone.id} className="projects-dashboard__list-item">
              <button
                type="button"
                className="projects-dashboard__list-button"
                onClick={() => onOpenProject(milestone.project_id)}
              >
                <div className="projects-dashboard__list-header">
                  {milestone.is_overdue && (
                    <span className="ih-badge ih-badge--danger">{t('charts.overdue')}</span>
                  )}
                  <span className="projects-dashboard__list-title">{milestone.title}</span>
                </div>
                <p className="projects-dashboard__list-meta">{milestone.project_name}</p>
                <p className="projects-dashboard__list-meta">
                  {formatShortDate(milestone.date, locale)} ·{' '}
                  {t('charts.daysRemaining', { count: milestone.days_remaining })}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </PanelShell>
  );
}

function ActivityPanel({
  activity,
  locale,
  onOpenProject,
}: {
  activity: ProjectActivityItem[];
  locale: string;
  onOpenProject: (projectId: string) => void;
}) {
  const t = useTranslations('projects');

  return (
    <PanelShell title={t('panels.activity')}>
      {activity.length === 0 ? (
        <p className="dashboard__placeholder">{t('emptyDashboard')}</p>
      ) : (
        <ul className="projects-dashboard__list">
          {activity.map((item) => (
            <li key={item.id} className="projects-dashboard__list-item">
              <button
                type="button"
                className="projects-dashboard__list-button"
                disabled={!item.project_id}
                onClick={() => item.project_id && onOpenProject(item.project_id)}
              >
                <div className="projects-dashboard__list-header">
                  <span className="projects-dashboard__list-title">{item.title}</span>
                </div>
                <p className="projects-dashboard__list-meta">
                  {item.project_name ?? t('table.project')}
                  {item.actor ? ` · ${item.actor}` : ''}
                </p>
                <p className="projects-dashboard__list-meta">{formatShortDate(item.created_at, locale)}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </PanelShell>
  );
}
