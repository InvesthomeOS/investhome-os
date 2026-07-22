'use client';

import { useLocale, useTranslations } from 'next-intl';

import { BarChart } from '@/components/design-system/charts/BarChart';

import { devicesA, paymentBarSeries, reportPresets } from '../../_data/investors';
import { formatDate, formatDateTime, formatMoney, formatPct } from '../../_lib/format';
import {
  getContractsFor,
  getMeetingsFor,
  getNotificationsFor,
  getPaymentsFor,
  getRentalFor,
  getReservationsFor,
  getTasksFor,
  getInvestorProfile,
} from '../../_lib/permissions';
import { usePortalSession } from '../../_state/portal-session';
import { PageHeader } from '../page-header';

export function ReservationsView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const rows = getReservationsFor(investorId);
  return (
    <div className="portal-page" data-testid="portal-reservations">
      <PageHeader title={t('reservations.title')} subtitle={t('reservations.subtitle')} />
      <section className="portal-panel">
        <table className="portal-table">
          <thead>
            <tr>
              <th>{t('nav.projects')}</th>
              <th>{t('reservations.unit')}</th>
              <th>{t('reservations.expires')}</th>
              <th>{t('payments.amount')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.projectName}</td>
                <td>{r.unit}</td>
                <td>{formatDate(r.expiresAt, locale)}</td>
                <td>{formatMoney(r.amount, locale, r.currency)}</td>
                <td>
                  <span className={`portal-status portal-status--${r.status}`}>{r.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export function ContractsView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const rows = getContractsFor(investorId);
  return (
    <div className="portal-page" data-testid="portal-contracts">
      <PageHeader title={t('contracts.title')} subtitle={t('contracts.subtitle')} />
      <section className="portal-panel">
        <table className="portal-table">
          <thead>
            <tr>
              <th />
              <th>{t('nav.projects')}</th>
              <th>{t('contracts.signed')}</th>
              <th>{t('contracts.value')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td>
                  <strong>{c.title}</strong>
                </td>
                <td>{c.projectName}</td>
                <td>{c.signedAt ? formatDate(c.signedAt, locale) : '—'}</td>
                <td>{formatMoney(c.value, locale, c.currency)}</td>
                <td>
                  <span className={`portal-status portal-status--${c.status}`}>{c.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export function PaymentsView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const rows = getPaymentsFor(investorId);
  return (
    <div className="portal-page" data-testid="portal-payments">
      <PageHeader title={t('payments.title')} subtitle={t('payments.subtitle')} />
      <div className="portal-grid-2">
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('payments.mix')}</h2>
          <BarChart
            data={paymentBarSeries}
            ariaLabel={t('payments.mix')}
            locale={locale}
            format="currency"
            currency="TRY"
            horizontal
          />
        </section>
        <section className="portal-panel">
          <div className="portal-kpi-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <article className="portal-kpi">
              <div className="portal-kpi__label">{t('dashboard.cashDue')}</div>
              <div className="portal-kpi__value">
                {formatMoney(
                  rows.filter((p) => p.status === 'due').reduce((s, p) => s + p.amount, 0),
                  locale,
                )}
              </div>
            </article>
            <article className="portal-kpi">
              <div className="portal-kpi__label">Paid</div>
              <div className="portal-kpi__value">
                {formatMoney(
                  rows.filter((p) => p.status === 'paid').reduce((s, p) => s + p.amount, 0),
                  locale,
                )}
              </div>
            </article>
          </div>
        </section>
      </div>
      <section className="portal-panel">
        <table className="portal-table">
          <thead>
            <tr>
              <th />
              <th>{t('nav.projects')}</th>
              <th>{t('payments.due')}</th>
              <th>{t('payments.amount')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id} data-testid={`portal-payment-${p.id}`}>
                <td>
                  <strong>{p.label}</strong>
                </td>
                <td>{p.projectName}</td>
                <td>{formatDate(p.dueDate, locale)}</td>
                <td>{formatMoney(p.amount, locale, p.currency)}</td>
                <td>
                  <span className={`portal-status portal-status--${p.status}`}>{p.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export function RentalIncomeView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const rows = getRentalFor(investorId);
  return (
    <div className="portal-page" data-testid="portal-rental">
      <PageHeader title={t('rental.title')} subtitle={t('rental.subtitle')} />
      <section className="portal-panel">
        <table className="portal-table">
          <thead>
            <tr>
              <th>{t('nav.projects')}</th>
              <th>Period</th>
              <th>{t('rental.gross')}</th>
              <th>{t('rental.net')}</th>
              <th>{t('rental.occupancy')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.projectName}</td>
                <td>{r.period}</td>
                <td>{formatMoney(r.gross, locale, r.currency)}</td>
                <td>{formatMoney(r.net, locale, r.currency)}</td>
                <td>{formatPct(r.occupancy, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export function ReportsView() {
  const t = useTranslations('portalG9');
  return (
    <div className="portal-page" data-testid="portal-reports">
      <PageHeader title={t('reports.title')} subtitle={t('reports.subtitle')} />
      <div className="portal-grid-2">
        {reportPresets.map((r) => (
          <article key={r.id} className="portal-panel" data-testid={`portal-report-${r.id}`}>
            <h2 className="portal-panel__title">{t(r.titleKey)}</h2>
            <p className="portal-panel__desc">{t(r.descriptionKey)}</p>
            <div className="portal-actions">
              <span className="portal-status">{r.frequency}</span>
              <button type="button" className="portal-btn portal-btn--primary">
                {t('reports.generate')}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export function TasksView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const rows = getTasksFor(investorId);
  return (
    <div className="portal-page" data-testid="portal-tasks">
      <PageHeader title={t('tasks.title')} subtitle={t('tasks.subtitle')} />
      <section className="portal-panel">
        <table className="portal-table">
          <thead>
            <tr>
              <th />
              <th>{t('tasks.due')}</th>
              <th>{t('tasks.priority')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((task) => (
              <tr key={task.id}>
                <td>
                  <strong>{task.title}</strong>
                </td>
                <td>{formatDate(task.dueDate, locale)}</td>
                <td>{task.priority}</td>
                <td>
                  <span className={`portal-status portal-status--${task.status}`}>{task.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export function MeetingsView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const rows = getMeetingsFor(investorId);
  return (
    <div className="portal-page" data-testid="portal-meetings">
      <PageHeader title={t('meetings.title')} subtitle={t('meetings.subtitle')} />
      <div className="portal-list">
        {rows.map((m) => (
          <div key={m.id} className="portal-list__item">
            <div>
              <strong>{m.title}</strong>
              <div className="portal-list__meta">
                {formatDateTime(m.at, locale)} · {t('meetings.with')}: {m.withWhom}
              </div>
              <div className="portal-list__meta">
                {t('meetings.where')}: {m.location}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function NotificationsView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const rows = getNotificationsFor(investorId);
  const types = Array.from(new Set(rows.map((n) => n.type)));
  return (
    <div className="portal-page" data-testid="portal-notifications">
      <PageHeader title={t('notifications.title')} subtitle={t('notifications.subtitle')} />
      <div className="portal-actions" style={{ marginBottom: '0.5rem' }}>
        <span className="portal-list__meta">{t('notifications.types')}:</span>
        {types.map((type) => (
          <span key={type} className="portal-status">
            {type}
          </span>
        ))}
      </div>
      <div className="portal-list">
        {rows.map((n) => (
          <div key={n.id} className="portal-list__item" data-testid={`portal-ntf-${n.id}`}>
            <div>
              <strong className={n.read ? undefined : 'unread'}>{n.title}</strong>
              <div className="portal-list__meta">
                {n.body} · {formatDateTime(n.at, locale)}
              </div>
            </div>
            <span className="portal-status">{n.type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SupportView() {
  const t = useTranslations('portalG9');
  return (
    <div className="portal-page" data-testid="portal-support">
      <PageHeader title={t('support.title')} subtitle={t('support.subtitle')} />
      <div className="portal-grid-2">
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('support.contact')}</h2>
          <p className="portal-panel__desc">IR · ir@investhome.demo · +90 212 000 00 00</p>
          <button type="button" className="portal-btn portal-btn--primary">
            {t('support.contact')}
          </button>
        </section>
        <section className="portal-panel">
          <h2 className="portal-panel__title">FAQ</h2>
          <div className="portal-list">
            <div className="portal-list__item">
              <div>
                <strong>{t('support.faq1')}</strong>
                <div className="portal-list__meta">{t('support.faq1a')}</div>
              </div>
            </div>
            <div className="portal-list__item">
              <div>
                <strong>{t('support.faq2')}</strong>
                <div className="portal-list__meta">{t('support.faq2a')}</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export function AccountView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId, logout } = usePortalSession();
  if (!investorId) return null;
  const profile = getInvestorProfile(investorId);
  if (!profile) return null;

  return (
    <div className="portal-page" data-testid="portal-account">
      <PageHeader title={t('account.title')} subtitle={t('account.subtitle')} />
      <div className="portal-account-grid">
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('account.profile')}</h2>
          <div className="portal-toggle-row">
            <span>Name</span>
            <strong>{profile.fullName}</strong>
          </div>
          <div className="portal-toggle-row">
            <span>Email</span>
            <strong>{profile.email}</strong>
          </div>
          <div className="portal-toggle-row">
            <span>Phone</span>
            <strong>{profile.phone}</strong>
          </div>
          <div className="portal-toggle-row">
            <span>City</span>
            <strong>
              {profile.city}, {profile.country}
            </strong>
          </div>
        </section>
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('account.security')}</h2>
          <div className="portal-toggle-row">
            <span>{t('account.twofa')}</span>
            <span className={`portal-status ${profile.twoFactorEnabled ? 'portal-status--active' : ''}`}>
              {profile.twoFactorEnabled ? 'ON' : 'OFF'}
            </span>
          </div>
          <div className="portal-toggle-row">
            <span>{t('account.language')}</span>
            <strong>{locale.toUpperCase()}</strong>
          </div>
          <button type="button" className="portal-btn" onClick={() => void logout()}>
            {t('account.logout')}
          </button>
        </section>
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('account.devices')}</h2>
          <div className="portal-list">
            {devicesA.map((d) => (
              <div key={d.id} className="portal-list__item">
                <div>
                  <strong>{d.device}</strong>
                  <div className="portal-list__meta">
                    {d.location} · {formatDateTime(d.lastActive, locale)}
                  </div>
                </div>
                {d.current ? <span className="portal-status portal-status--active">current</span> : null}
              </div>
            ))}
          </div>
        </section>
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('account.notifPrefs')}</h2>
          <div className="portal-toggle-row">
            <span>{t('account.emailNotif')}</span>
            <span className="portal-status portal-status--active">ON</span>
          </div>
          <div className="portal-toggle-row">
            <span>{t('account.pushNotif')}</span>
            <span className="portal-status portal-status--active">ON</span>
          </div>
          <div className="portal-toggle-row">
            <span>{t('account.smsNotif')}</span>
            <span className="portal-status">OFF</span>
          </div>
        </section>
      </div>
    </div>
  );
}
