'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { fetchAutomationWorkflow, type AutomationWorkflowDetail } from '@/lib/api/automation-center';
import { canManageAutomation } from '@/lib/automation/automation-permissions';
import { useAuth } from '@/lib/auth/auth-context';

import { AutomationShell } from './automation-shell';
import { formatDateTime, formatDuration, formatSuccessRate } from './format';

export function WorkflowDetailWorkspace({ workflowId }: { workflowId: string }) {
  const t = useTranslations('automation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const canManage = canManageAutomation(user);
  const [detail, setDetail] = useState<AutomationWorkflowDetail | null>(null);
  const [state, setState] = useState<'loading' | 'error' | 'success'>('loading');

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    void fetchAutomationWorkflow(workflowId)
      .then((response) => {
        if (!cancelled) {
          setDetail(response);
          setState('success');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDetail(null);
          setState('error');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  return (
    <AutomationShell
      title={detail?.name || t('detail.title')}
      subtitle={detail?.description || t('detail.subtitle')}
      actions={
        detail?.manage_href ? (
          <Link href={detail.manage_href as Route} className="leads__button leads__button--secondary">
            {t('detail.openSource')}
          </Link>
        ) : undefined
      }
    >
      {state === 'loading' ? <LoadingState label={tCommon('loading')} /> : null}
      {state === 'error' ? <ErrorState title={t('detail.notFound')} message={t('loadErrorHint')} /> : null}

      {state === 'success' && detail ? (
        <>
          {!detail.execution_engine_available ? (
            <div className="automation-center__banner automation-center__banner--warn" role="status">
              {detail.execution_engine_message || t('engineUnavailable')}
            </div>
          ) : null}

          <section className="automation-center__kpis">
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('columns.status')}</p>
              <p className="automation-center__kpi-value" style={{ fontSize: '1.05rem' }}>
                <StatusChip tone={detail.status === 'active' || detail.status === 'scheduled' ? 'success' : 'default'}>
                  {t.has(`workflowStatus.${detail.status}`) ? t(`workflowStatus.${detail.status}`) : detail.status}
                </StatusChip>
              </p>
            </div>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('columns.trigger')}</p>
              <p className="automation-center__kpi-value" style={{ fontSize: '1rem' }}>
                {detail.trigger_label || detail.trigger || '—'}
              </p>
            </div>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('columns.lastRun')}</p>
              <p className="automation-center__kpi-value" style={{ fontSize: '1rem' }}>
                {formatDateTime(detail.last_run_at, locale)}
              </p>
            </div>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('columns.successRate')}</p>
              <p className="automation-center__kpi-value" style={{ fontSize: '1rem' }}>
                {formatSuccessRate(detail.success_rate, detail.success_rate_available, t('unavailable'))}
              </p>
            </div>
          </section>

          {canManage && (detail.can_pause || detail.can_resume || detail.can_retry) ? (
            <div className="automation-center__banner" role="note">
              {t('detail.manageHint')}
              {detail.manage_href ? (
                <>
                  {' '}
                  <Link href={detail.manage_href as Route}>{t('detail.openSource')}</Link>
                </>
              ) : null}
            </div>
          ) : null}

          <div className="automation-center__grid">
            <section className="automation-center__panel">
              <h2 className="automation-center__panel-title">{t('detail.steps')}</h2>
              {detail.steps.length === 0 ? (
                <p className="automation-center__empty">{t('detail.noSteps')}</p>
              ) : (
                <div className="automation-center__steps">
                  {detail.steps.map((step, index) => (
                    <div key={step.id} className="automation-center__step">
                      <strong>
                        {index + 1}. {step.label}
                      </strong>
                      <span>{step.type}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="automation-center__panel">
              <h2 className="automation-center__panel-title">{t('detail.dependencies')}</h2>
              {detail.dependencies.length === 0 ? (
                <p className="automation-center__empty">{t('detail.noDependencies')}</p>
              ) : (
                <ul style={{ margin: '0.75rem 0 0 1.1rem' }}>
                  {detail.dependencies.map((dep) => (
                    <li key={dep}>{dep}</li>
                  ))}
                </ul>
              )}
              <h2 className="automation-center__panel-title" style={{ marginTop: '1.25rem' }}>
                {t('detail.triggerConfig')}
              </h2>
              <pre style={{ marginTop: '0.5rem', fontSize: '0.78rem', overflow: 'auto' }}>
                {JSON.stringify(detail.trigger_config ?? {}, null, 2)}
              </pre>
            </section>

            <section className="automation-center__panel automation-center__panel--full">
              <h2 className="automation-center__panel-title">{t('detail.history')}</h2>
              {detail.history.length === 0 ? (
                <p className="automation-center__empty">{t('empty.executions')}</p>
              ) : (
                <div className="automation-center__table-wrap">
                  <table className="automation-center__table">
                    <thead>
                      <tr>
                        <th>{t('columns.status')}</th>
                        <th>{t('columns.duration')}</th>
                        <th>{t('columns.retries')}</th>
                        <th>{t('columns.time')}</th>
                        <th>{t('columns.message')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.history.map((row) => (
                        <tr key={row.id}>
                          <td>{row.status}</td>
                          <td>{formatDuration(row.duration_ms)}</td>
                          <td>{row.retry_count}</td>
                          <td>{formatDateTime(row.created_at, locale)}</td>
                          <td>{row.error_message || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="automation-center__panel automation-center__panel--full">
              <h2 className="automation-center__panel-title">{t('detail.logs')}</h2>
              {detail.logs.length === 0 ? (
                <p className="automation-center__empty">{t('empty.logs')}</p>
              ) : (
                <ul style={{ listStyle: 'none', display: 'grid', gap: '0.55rem', marginTop: '0.75rem' }}>
                  {detail.logs.map((log) => (
                    <li key={log.id} className="automation-center__step">
                      <strong>
                        {log.level} · {formatDateTime(log.created_at, locale)}
                      </strong>
                      <span>{log.message}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      ) : null}
    </AutomationShell>
  );
}
