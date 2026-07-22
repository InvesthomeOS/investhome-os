'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';

import { LineChart } from '@/components/design-system/charts/LineChart';
import { Sparkline } from '@/components/design-system/charts/Sparkline';

import { navValueSeries } from '../../_data/investors';
import {
  getHoldingsFor,
  getMessagesFor,
  getNotificationsFor,
  getPaymentsFor,
  getTasksFor,
} from '../../_lib/permissions';
import { formatMoney, formatPct } from '../../_lib/format';
import { usePortalSession } from '../../_state/portal-session';
import { PageHeader } from '../page-header';

export function DashboardView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;

  const holdings = getHoldingsFor(investorId);
  const payments = getPaymentsFor(investorId);
  const messages = getMessagesFor(investorId);
  const tasks = getTasksFor(investorId);
  const notifications = getNotificationsFor(investorId);

  const invested = holdings.reduce((s, h) => s + h.invested, 0);
  const current = holdings.reduce((s, h) => s + h.currentValue, 0);
  const irr =
    holdings.length > 0
      ? holdings.reduce((s, h) => s + h.irr, 0) / holdings.length
      : 0;
  const due = payments.filter((p) => p.status === 'due' || p.status === 'overdue');
  const dueAmt = due.reduce((s, p) => s + p.amount, 0);

  return (
    <div className="portal-page" data-testid="portal-dashboard">
      <PageHeader title={t('dashboard.title')} subtitle={t('dashboard.subtitle')} />

      <section className="portal-kpi-grid" aria-label={t('dashboard.title')}>
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('dashboard.navValue')}</div>
          <div className="portal-kpi__value">{formatMoney(current, locale)}</div>
          <div className="portal-kpi__spark">
            <Sparkline
              values={navValueSeries.map((p) => p.value)}
              ariaLabel={t('dashboard.valueTrend')}
              locale={locale}
              format="currency"
            />
          </div>
        </article>
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('dashboard.invested')}</div>
          <div className="portal-kpi__value">{formatMoney(invested, locale)}</div>
        </article>
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('dashboard.irr')}</div>
          <div className="portal-kpi__value">{formatPct(irr, locale)}</div>
        </article>
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('dashboard.cashDue')}</div>
          <div className="portal-kpi__value">{formatMoney(dueAmt, locale)}</div>
          <div className="portal-kpi__meta">{due.length} · {t('nav.payments')}</div>
        </article>
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('dashboard.unread')}</div>
          <div className="portal-kpi__value">{messages.filter((m) => !m.read).length}</div>
        </article>
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('dashboard.tasksOpen')}</div>
          <div className="portal-kpi__value">{tasks.filter((x) => x.status === 'open').length}</div>
        </article>
      </section>

      <div className="portal-grid-2">
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('dashboard.valueTrend')}</h2>
          <p className="portal-panel__desc">NAV · 7 ay</p>
          <LineChart
            data={navValueSeries}
            ariaLabel={t('dashboard.valueTrend')}
            locale={locale}
            format="currency"
            currency="TRY"
            height={140}
          />
        </section>
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('dashboard.activity')}</h2>
          <p className="portal-panel__desc">{t('nav.notifications')}</p>
          <div className="portal-list">
            {notifications.slice(0, 5).map((n) => (
              <div key={n.id} className="portal-list__item">
                <div>
                  <strong>{n.title}</strong>
                  <div className="portal-list__meta">{n.body}</div>
                </div>
                <span className="portal-status">{n.type}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="portal-panel">
        <h2 className="portal-panel__title">{t('dashboard.holdings')}</h2>
        <table className="portal-table">
          <thead>
            <tr>
              <th>{t('nav.projects')}</th>
              <th>{t('portfolio.current')}</th>
              <th>{t('portfolio.roi')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.id}>
                <td>
                  <Link href={`/portal/projects/${h.projectId}` as Route}>{h.projectName}</Link>
                  <div className="portal-list__meta">{h.location}</div>
                </td>
                <td>{formatMoney(h.currentValue, locale, h.currency)}</td>
                <td>{formatPct(h.roi, locale)}</td>
                <td>
                  <Sparkline values={h.sparkline} ariaLabel={h.projectName} locale={locale} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
