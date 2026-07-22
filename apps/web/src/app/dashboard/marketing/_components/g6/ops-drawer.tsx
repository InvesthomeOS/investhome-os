'use client';

import { useEffect, useState } from 'react';

import type { MarketingCampaignDetail, MarketingCampaignSummary } from '@/workspaces/marketing/types';
import { fetchCampaign } from '@/workspaces/marketing/api/marketing';
import { fetchCampaignLeadBreakdown, fetchCampaignPerformanceDetail } from '@/workspaces/marketing/api/performance';

import { formatMoney, num, statusTone } from './derive';
import { DRAWER_SECTIONS, type DrawerSectionId } from './marketing-views';

function lab(labels: Record<string, string>, key: string): string {
  return labels[key] ?? key;
}

export function OpsDrawer({
  campaign,
  labels,
  locale,
  onClose,
  onDuplicate,
}: {
  campaign: MarketingCampaignSummary;
  labels: Record<string, string>;
  locale: string;
  onClose: () => void;
  onDuplicate?: () => void;
}) {
  const [section, setSection] = useState<DrawerSectionId>('overview');
  const [detail, setDetail] = useState<MarketingCampaignDetail | null>(null);
  const [perf, setPerf] = useState<Record<string, unknown> | null>(null);
  const [leads, setLeads] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [d, p, l] = await Promise.all([
          fetchCampaign(campaign.id),
          fetchCampaignPerformanceDetail(campaign.id).catch(() => null),
          fetchCampaignLeadBreakdown(campaign.id, { page_size: 25 }).catch(() => null),
        ]);
        if (cancelled) return;
        setDetail(d);
        setPerf(p as Record<string, unknown> | null);
        setLeads((l?.items as Array<Record<string, unknown>>) ?? []);
      } catch {
        if (!cancelled) {
          setDetail(null);
          setPerf(null);
          setLeads([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [campaign.id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const c = detail ?? campaign;

  return (
    <div className="mkt-g6-drawer" data-testid="mkt-g6-drawer" role="dialog" aria-modal="true" aria-label={c.name}>
      <div className="mkt-g6-drawer__panel">
        <header className="mkt-g6-drawer__header">
          <div>
            <p className="mkt-g6__eyebrow">{lab(labels, 'campaignDrawer')}</p>
            <h2>{c.name}</h2>
            <p className="mkt-g6__subtitle">
              <span className={`mkt-g6__status mkt-g6__status--${statusTone(c.status)}`}>{c.status}</span>
              {' · '}
              {c.campaign_type}
            </p>
          </div>
          <button type="button" className="mkt-g6__btn" onClick={onClose} data-testid="mkt-g6-drawer-close">
            {lab(labels, 'close')}
          </button>
        </header>

        <div className="mkt-g6-drawer__actions">
          {onDuplicate ? (
            <button type="button" className="mkt-g6__btn" onClick={onDuplicate}>
              {lab(labels, 'duplicate')}
            </button>
          ) : null}
          <a className="mkt-g6__btn" href={`/workspaces/marketing/campaigns/${campaign.id}`}>
            {lab(labels, 'openFull')}
          </a>
        </div>

        <nav className="mkt-g6-drawer__tabs" aria-label={lab(labels, 'drawerSections')}>
          {DRAWER_SECTIONS.map((s) => (
            <button
              key={s}
              type="button"
              className={`mkt-g6-drawer__tab${section === s ? ' is-active' : ''}`}
              data-testid={`mkt-g6-drawer-tab-${s}`}
              onClick={() => setSection(s)}
            >
              {lab(labels, `drawer.${s}`)}
            </button>
          ))}
        </nav>

        <div className="mkt-g6-drawer__body">
          {loading ? (
            <div className="mkt-g6__empty">{lab(labels, 'loading')}</div>
          ) : section === 'overview' ? (
            <dl className="mkt-g6-drawer__grid">
              <div>
                <dt>{lab(labels, 'colChannel')}</dt>
                <dd>{c.primary_channel ?? '—'}</dd>
              </div>
              <div>
                <dt>{lab(labels, 'colBudget')}</dt>
                <dd>{formatMoney(num(c.budget_amount), c.budget_currency, locale)}</dd>
              </div>
              <div>
                <dt>{lab(labels, 'colSpend')}</dt>
                <dd>{formatMoney(num(c.spent_amount), c.budget_currency, locale)}</dd>
              </div>
              <div>
                <dt>{lab(labels, 'colLeads')}</dt>
                <dd>{c.actual_leads ?? '—'}</dd>
              </div>
              <div>
                <dt>{lab(labels, 'colDates')}</dt>
                <dd>
                  {c.start_date ?? '—'} → {c.end_date ?? '—'}
                </dd>
              </div>
              <div>
                <dt>{lab(labels, 'colCode')}</dt>
                <dd className="mkt-g6__mono">{c.code ?? '—'}</dd>
              </div>
              {'description' in c && typeof (c as { description?: unknown }).description === 'string' && (c as { description: string }).description ? (
                <div style={{ gridColumn: '1 / -1' }}>
                  <dt>{lab(labels, 'notes')}</dt>
                  <dd>{(c as { description: string }).description}</dd>
                </div>
              ) : null}
            </dl>
          ) : section === 'performance' ? (
            <dl className="mkt-g6-drawer__grid">
              {perf ? (
                Object.entries(perf)
                  .filter(([, v]) => v && typeof v === 'object' && 'value' in (v as object))
                  .slice(0, 12)
                  .map(([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>{String((v as { value?: unknown }).value ?? '—')}</dd>
                    </div>
                  ))
              ) : (
                <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
              )}
            </dl>
          ) : section === 'leads' ? (
            <div className="mkt-g6__list-wrap">
              <table className="mkt-g6__table" style={{ minWidth: 0 }}>
                <thead>
                  <tr>
                    <th>{lab(labels, 'colName')}</th>
                    <th>{lab(labels, 'colStatus')}</th>
                    <th>{lab(labels, 'colAttr')}</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.length === 0 ? (
                    <tr>
                      <td colSpan={3}>
                        <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                      </td>
                    </tr>
                  ) : (
                    leads.map((lead) => (
                      <tr key={String(lead.lead_id)}>
                        <td>{String(lead.full_name ?? '—')}</td>
                        <td>{String(lead.status ?? '—')}</td>
                        <td>{String(lead.attribution_status ?? '—')}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          ) : section === 'audience' || section === 'channels' || section === 'content' || section === 'ads' ? (
            <div>
              <p className="mkt-g6__subtitle">{lab(labels, `drawerHint.${section}`)}</p>
              <dl className="mkt-g6-drawer__grid">
                <div>
                  <dt>{lab(labels, 'colAudience')}</dt>
                  <dd>{'audience_ids' in c && Array.isArray(c.audience_ids) ? c.audience_ids.length : 0}</dd>
                </div>
                <div>
                  <dt>{lab(labels, 'colChannels')}</dt>
                  <dd>{'channel_ids' in c && Array.isArray(c.channel_ids) ? c.channel_ids.length : 0}</dd>
                </div>
              </dl>
            </div>
          ) : section === 'budget' ? (
            <dl className="mkt-g6-drawer__grid">
              <div>
                <dt>{lab(labels, 'colBudget')}</dt>
                <dd>{formatMoney(num(c.budget_amount), c.budget_currency, locale)}</dd>
              </div>
              <div>
                <dt>{lab(labels, 'colSpend')}</dt>
                <dd>{formatMoney(num(c.spent_amount), c.budget_currency, locale)}</dd>
              </div>
              <div>
                <dt>{lab(labels, 'remaining')}</dt>
                <dd>
                  {'remaining_budget' in c
                    ? formatMoney(num(c.remaining_budget), c.budget_currency, locale)
                    : '—'}
                </dd>
              </div>
            </dl>
          ) : section === 'opportunities' || section === 'documents' || section === 'ai' || section === 'activity' || section === 'audit' ? (
            <div className="mkt-g6__empty">{lab(labels, `drawerHint.${section}`)}</div>
          ) : (
            <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
          )}
        </div>
      </div>
    </div>
  );
}
