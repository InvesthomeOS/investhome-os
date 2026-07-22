'use client';

import { useEffect, useState } from 'react';

import {
  fetchFundingCommitments,
  fetchPaymentObligations,
  formatMoney,
  type FundingCommitment,
  type PaymentObligation,
} from '@/lib/api/finance';
import {
  fetchReservations,
  formatCountdown,
  type InventoryReservation,
} from '@/lib/api/inventory';
import type { Investor } from '@/lib/api/investors';
import { formatCurrency, formatShortDate } from '@/lib/api/investors';
import {
  fetchOpportunities,
  formatMoney as formatOppMoney,
  type SalesOpportunity,
} from '@/lib/api/sales';
import { fetchEntityActivity, type ActivityLogEntry } from '@/lib/api/activity';

import { toLifecycleStage, type InvestorLifecycleStage } from './lifecycle';

type DataMode = 'live' | 'partial' | 'demo' | 'blocked';

function DataTag({ mode, label }: { mode: DataMode; label: string }) {
  return <span className={`inv-g3__data-tag inv-g3__data-tag--${mode}`}>{label}</span>;
}

interface PanelCommon {
  locale: string;
  investors: Investor[];
  labels: Record<string, string>;
  stageLabel: (s: InvestorLifecycleStage) => string;
}

export function OpportunitiesPanel({ locale, investors, labels }: PanelCommon) {
  const [items, setItems] = useState<SalesOpportunity[]>([]);
  const [mode, setMode] = useState<DataMode>('live');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchOpportunities({ limit: 100, offset: 0 });
        const investorIds = new Set(investors.map((i) => i.id));
        const filtered = res.items.filter(
          (o) => o.party_type === 'investor' || investorIds.has(o.party_id),
        );
        if (cancelled) return;
        if (filtered.length === 0 && res.items.length === 0) {
          setMode('demo');
          setItems([]);
        } else if (filtered.length === 0) {
          setMode('partial');
          setItems(res.items.slice(0, 20));
        } else {
          setMode('live');
          setItems(filtered);
        }
      } catch {
        if (!cancelled) {
          setError(labels.loadError ?? 'Error');
          setMode('blocked');
          setItems([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [investors, labels.loadError]);

  return (
    <section className="inv-g3__panel" data-testid="inv-g3-opportunities">
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <h3>{labels.opportunitiesTitle}</h3>
        <DataTag mode={mode} label={labels[`data_${mode}`] ?? mode} />
      </div>
      <p>{labels.opportunitiesHint}</p>
      {error ? <p className="inv-g3__banner">{error}</p> : null}
      {items.length === 0 ? (
        <div className="inv-g3__empty">{labels.emptyOpportunities}</div>
      ) : (
        <div className="inv-g3__list-wrap">
          <table className="inv-g3__table">
            <thead>
              <tr>
                <th>{labels.colOpportunity}</th>
                <th>{labels.colStage}</th>
                <th>{labels.colValue}</th>
                <th>{labels.colProbability}</th>
                <th>{labels.colClose}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((o) => (
                <tr key={o.id}>
                  <td>
                    <strong>{o.notes?.trim() || o.display_id || o.opportunity_code}</strong>
                  </td>
                  <td>{o.stage}</td>
                  <td>{formatOppMoney(o.expected_revenue, o.currency || 'TRY', locale)}</td>
                  <td>%{o.probability}</td>
                  <td>
                    {o.expected_close_date
                      ? formatShortDate(o.expected_close_date, locale)
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function ReservationsPanel({ locale, labels }: PanelCommon) {
  const [items, setItems] = useState<InventoryReservation[]>([]);
  const [mode, setMode] = useState<DataMode>('live');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchReservations({ page_size: 50, active_only: true });
        if (cancelled) return;
        setItems(res.items);
        setMode(res.items.length ? 'live' : 'partial');
      } catch {
        if (!cancelled) {
          setError(labels.loadError ?? 'Error');
          setMode('blocked');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [labels.loadError]);

  return (
    <section className="inv-g3__panel" data-testid="inv-g3-reservations">
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <h3>{labels.reservationsTitle}</h3>
        <DataTag mode={mode} label={labels[`data_${mode}`] ?? mode} />
      </div>
      <p>{labels.reservationsHint}</p>
      {error ? <p className="inv-g3__banner">{error}</p> : null}
      {items.length === 0 ? (
        <div className="inv-g3__empty">{labels.emptyReservations}</div>
      ) : (
        <div className="inv-g3__list-wrap">
          <table className="inv-g3__table">
            <thead>
              <tr>
                <th>{labels.colReservation}</th>
                <th>{labels.colStatus}</th>
                <th>{labels.colInvestor}</th>
                <th>{labels.colExpires}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{r.asset_display_id || r.id.slice(0, 8)}</strong>
                  </td>
                  <td>{r.status}</td>
                  <td>{r.party_name || r.investor_id || '—'}</td>
                  <td>
                    {r.expires_at
                      ? formatShortDate(r.expires_at.slice(0, 10), locale)
                      : formatCountdown(r.seconds_until_expiry)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function ContractsPanel({ labels, investors, stageLabel }: PanelCommon) {
  const contractLike = investors.filter((i) =>
    ['contract', 'payment_pending', 'wire_received', 'closing'].includes(toLifecycleStage(i.status)),
  );

  return (
    <section className="inv-g3__panel" data-testid="inv-g3-contracts">
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <h3>{labels.contractsTitle}</h3>
        <DataTag mode="partial" label={labels.data_partial ?? 'partial'} />
      </div>
      <p>{labels.contractsHint}</p>
      {contractLike.length === 0 ? (
        <div className="inv-g3__empty">{labels.emptyContracts}</div>
      ) : (
        <div className="inv-g3__list-wrap">
          <table className="inv-g3__table">
            <thead>
              <tr>
                <th>{labels.colInvestor}</th>
                <th>{labels.colStage}</th>
                <th>{labels.colValue}</th>
              </tr>
            </thead>
            <tbody>
              {contractLike.map((i) => (
                <tr key={i.id}>
                  <td>
                    <strong>{i.full_name}</strong>
                  </td>
                  <td>{stageLabel(toLifecycleStage(i.status))}</td>
                  <td>{i.investment_capacity ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

const PAYMENT_STATUS_MAP: Record<string, string> = {
  upcoming: 'Scheduled',
  due: 'Pending',
  overdue: 'Overdue',
  paid: 'Received',
  cancelled: 'Cancelled',
  proposed: 'Scheduled',
  committed: 'Pending',
  partially_funded: 'Partial',
  fully_funded: 'Received',
  delayed: 'Overdue',
};

export function PaymentsPanel({ locale, labels }: PanelCommon) {
  const [commitments, setCommitments] = useState<FundingCommitment[]>([]);
  const [obligations, setObligations] = useState<PaymentObligation[]>([]);
  const [mode, setMode] = useState<DataMode>('live');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [c, o] = await Promise.all([
          fetchFundingCommitments({ page_size: 50 }),
          fetchPaymentObligations({ page_size: 50 }),
        ]);
        if (cancelled) return;
        setCommitments(c.items);
        setObligations(o.items);
        setMode(c.items.length || o.items.length ? 'live' : 'partial');
      } catch {
        if (!cancelled) {
          setError(labels.loadError ?? 'Error');
          setMode('blocked');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [labels.loadError]);

  return (
    <section className="inv-g3__panel" data-testid="inv-g3-payments">
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <h3>{labels.paymentsTitle}</h3>
        <DataTag mode={mode} label={labels[`data_${mode}`] ?? mode} />
      </div>
      <p>{labels.paymentsHint}</p>
      {error ? <p className="inv-g3__banner">{error}</p> : null}

      <h3 style={{ marginTop: '0.75rem' }}>{labels.commitments}</h3>
      {commitments.length === 0 ? (
        <div className="inv-g3__empty">{labels.emptyPayments}</div>
      ) : (
        <div className="inv-g3__list-wrap">
          <table className="inv-g3__table">
            <thead>
              <tr>
                <th>{labels.colInvestor}</th>
                <th>{labels.colProject}</th>
                <th>{labels.colValue}</th>
                <th>{labels.colStatus}</th>
              </tr>
            </thead>
            <tbody>
              {commitments.map((c) => (
                <tr key={c.id}>
                  <td>{c.investor_name || c.investor_id.slice(0, 8)}</td>
                  <td>{c.project_name || c.project_id.slice(0, 8)}</td>
                  <td>{formatMoney(c.committed_amount, c.currency, locale)}</td>
                  <td>{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 style={{ marginTop: '0.75rem' }}>{labels.obligations}</h3>
      {obligations.length === 0 ? (
        <div className="inv-g3__empty">{labels.emptyPayments}</div>
      ) : (
        <div className="inv-g3__list-wrap">
          <table className="inv-g3__table">
            <thead>
              <tr>
                <th>{labels.colInvestor}</th>
                <th>{labels.colValue}</th>
                <th>{labels.colStatus}</th>
                <th>{labels.colDue}</th>
              </tr>
            </thead>
            <tbody>
              {obligations.map((o) => (
                <tr key={o.id}>
                  <td>{o.investor_name || o.payee || '—'}</td>
                  <td>{formatMoney(o.amount, o.currency, locale)}</td>
                  <td>{PAYMENT_STATUS_MAP[o.status] ?? o.status}</td>
                  <td>{o.due_date ? formatShortDate(o.due_date, locale) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function ClosingsPanel({ investors, labels, stageLabel, locale }: PanelCommon) {
  const closings = investors.filter((i) =>
    ['closing', 'wire_received', 'construction', 'portfolio'].includes(toLifecycleStage(i.status)),
  );

  return (
    <section className="inv-g3__panel" data-testid="inv-g3-closings">
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <h3>{labels.closingsTitle}</h3>
        <DataTag mode="partial" label={labels.data_partial ?? 'partial'} />
      </div>
      <p>{labels.closingsHint}</p>
      {closings.length === 0 ? (
        <div className="inv-g3__empty">{labels.emptyClosings}</div>
      ) : (
        <div className="inv-g3__list-wrap">
          <table className="inv-g3__table">
            <thead>
              <tr>
                <th>{labels.colInvestor}</th>
                <th>{labels.colStage}</th>
                <th>{labels.colValue}</th>
                <th>{labels.colClose}</th>
              </tr>
            </thead>
            <tbody>
              {closings.map((i) => (
                <tr key={i.id}>
                  <td>
                    <strong>{i.full_name}</strong>
                  </td>
                  <td>{stageLabel(toLifecycleStage(i.status))}</td>
                  <td>{formatCurrency(i.investment_capacity, locale)}</td>
                  <td>{formatShortDate(i.next_follow_up_date, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function PortfolioPanel({ investors, labels, locale }: PanelCommon) {
  const portfolio = investors.filter((i) => {
    const s = toLifecycleStage(i.status);
    return s === 'portfolio' || s === 'rental' || i.status === 'invested';
  });

  return (
    <section className="inv-g3__panel" data-testid="inv-g3-portfolio">
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <h3>{labels.portfolioTitle}</h3>
        <DataTag mode="demo" label={labels.data_demo ?? 'demo'} />
      </div>
      <p>{labels.portfolioHint}</p>
      <p className="inv-g3__banner inv-g3__banner--gap">{labels.portfolioGap ?? ''}</p>
      {portfolio.length === 0 ? (
        <div className="inv-g3__empty">{labels.emptyPortfolio}</div>
      ) : (
        <div className="inv-g3__list-wrap">
          <table className="inv-g3__table">
            <thead>
              <tr>
                <th>{labels.colInvestor}</th>
                <th>{labels.colCapacity}</th>
                <th>{labels.colProjects}</th>
                <th>{labels.colNav}</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.map((i) => (
                <tr key={i.id}>
                  <td>
                    <strong>{i.full_name}</strong>
                  </td>
                  <td>{formatCurrency(i.investment_capacity, locale)}</td>
                  <td>{i.preferred_projects ?? '—'}</td>
                  <td>
                    <em>{labels.demoOnly}</em>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function ActivityPanel({ investors, labels, locale }: PanelCommon) {
  const [items, setItems] = useState<ActivityLogEntry[]>([]);
  const [mode, setMode] = useState<DataMode>('live');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const sample = investors.slice(0, 8);
        const batches = await Promise.all(
          sample.map((inv) =>
            fetchEntityActivity('investor', inv.id, 5).catch(() => ({
              items: [] as ActivityLogEntry[],
            })),
          ),
        );
        if (cancelled) return;
        const merged = batches.flatMap((b) => b.items).slice(0, 40);
        setItems(merged);
        setMode(merged.length ? 'live' : 'partial');
      } catch {
        if (!cancelled) setMode('blocked');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [investors]);

  return (
    <section className="inv-g3__panel" data-testid="inv-g3-activity">
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <h3>{labels.activityTitle}</h3>
        <DataTag mode={mode} label={labels[`data_${mode}`] ?? mode} />
      </div>
      <p>{labels.activityHint}</p>
      {items.length === 0 ? (
        <div className="inv-g3__empty">{labels.emptyActivity}</div>
      ) : (
        <ul className="inv-g3-drawer__history">
          {items.map((a) => (
            <li key={a.id}>
              <strong>{a.description_key || a.action || a.id}</strong>
              <div>
                {a.entity_label || a.entity_id} · {formatShortDate(a.created_at.slice(0, 10), locale)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
