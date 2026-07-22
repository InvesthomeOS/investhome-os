'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';

import { BarChart } from '@/components/design-system/charts/BarChart';
import { LineChart } from '@/components/design-system/charts/LineChart';
import { Sparkline } from '@/components/design-system/charts/Sparkline';

import { navValueSeries } from '../../_data/investors';
import { formatMoney, formatPct } from '../../_lib/format';
import { getHoldingsFor } from '../../_lib/permissions';
import { usePortalSession } from '../../_state/portal-session';
import { PageHeader } from '../page-header';

export function PortfolioView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const holdings = getHoldingsFor(investorId);
  const committed = holdings.reduce((s, h) => s + h.committed, 0);
  const current = holdings.reduce((s, h) => s + h.currentValue, 0);
  const allocation = holdings.map((h) => ({ label: h.projectName.split(' ')[0]!, value: h.currentValue }));

  return (
    <div className="portal-page" data-testid="portal-portfolio">
      <PageHeader title={t('portfolio.title')} subtitle={t('portfolio.subtitle')} />
      <section className="portal-kpi-grid">
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('portfolio.committed')}</div>
          <div className="portal-kpi__value">{formatMoney(committed, locale)}</div>
        </article>
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('portfolio.current')}</div>
          <div className="portal-kpi__value">{formatMoney(current, locale)}</div>
        </article>
        <article className="portal-kpi">
          <div className="portal-kpi__label">Δ</div>
          <div className="portal-kpi__value">{formatMoney(current - committed, locale)}</div>
        </article>
        <article className="portal-kpi">
          <div className="portal-kpi__label">{t('dashboard.irr')}</div>
          <div className="portal-kpi__value">
            {formatPct(
              holdings.reduce((s, h) => s + h.irr, 0) / Math.max(holdings.length, 1),
              locale,
            )}
          </div>
        </article>
      </section>

      <div className="portal-grid-2">
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('dashboard.valueTrend')}</h2>
          <LineChart
            data={navValueSeries}
            ariaLabel={t('dashboard.valueTrend')}
            locale={locale}
            format="currency"
            currency="TRY"
            height={150}
          />
        </section>
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('portfolio.allocation')}</h2>
          <BarChart
            data={allocation}
            ariaLabel={t('portfolio.allocation')}
            locale={locale}
            format="currency"
            currency="TRY"
            horizontal
          />
        </section>
      </div>

      <section className="portal-panel">
        <table className="portal-table">
          <thead>
            <tr>
              <th>{t('nav.projects')}</th>
              <th>{t('portfolio.committed')}</th>
              <th>{t('portfolio.current')}</th>
              <th>{t('portfolio.ownership')}</th>
              <th>{t('portfolio.roi')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.id} data-testid={`portal-holding-${h.id}`}>
                <td>
                  <Link href={`/portal/projects/${h.projectId}` as Route}>{h.projectName}</Link>
                  <div className="portal-list__meta">{h.location}</div>
                </td>
                <td>{formatMoney(h.committed, locale, h.currency)}</td>
                <td>{formatMoney(h.currentValue, locale, h.currency)}</td>
                <td>{formatPct(h.ownershipPct, locale)}</td>
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
