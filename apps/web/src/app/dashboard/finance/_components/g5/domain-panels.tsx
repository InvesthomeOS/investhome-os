'use client';

import { useEffect, useMemo, useState } from 'react';

import { BarChart, LineChart, Sparkline } from '@/components/design-system/charts';
import type { ApprovalItem } from '@/lib/api/executive';
import {
  formatMoney,
  formatShortDate,
  type FinanceStats,
  type FinanceTransaction,
  type FinancialAccount,
  type FundingCommitment,
  type PaymentObligation,
  type ProjectBudget,
} from '@/lib/api/finance';
import { fetchDocuments, type Document } from '@/lib/api/documents';
import { fetchEntityActivity, type ActivityLogEntry } from '@/lib/api/activity';

import {
  buildForecast,
  constructionBudgetTotal,
  debtBalance,
  deriveIncomingWires,
  deriveInsights,
  deriveInvestorPayments,
  deriveOutgoingWires,
  deriveVendorPayments,
  investorFundsCash,
  monthlyBurn,
  num,
  primaryCurrency,
  restrictedCash,
  runwayMonths,
  sparkFromBase,
  sumCurrencyTotals,
  type InvestorPaymentRow,
  type VendorPaymentRow,
  type WireRow,
} from './derive';
import type { DataKind } from './finance-views';

function lab(labels: Record<string, string>, key: string): string {
  return labels[key] ?? key;
}

export function DataTag({ kind, label }: { kind: DataKind; label: string }) {
  return <span className={`fin-g5__data-tag fin-g5__data-tag--${kind}`}>{label}</span>;
}

function statusTone(status: string): string {
  const s = status.toLowerCase();
  if (['completed', 'released', 'paid', 'active', 'cleared', 'fully_funded'].includes(s)) {
    return 'ok';
  }
  if (['overdue', 'returned', 'cancelled', 'critical', 'late'].includes(s)) return 'danger';
  if (['pending', 'scheduled', 'approved', 'due', 'required', 'delayed'].includes(s)) return 'warn';
  return '';
}

interface CommonLabels {
  labels: Record<string, string>;
  locale: string;
}

export function ExecutiveDashboard({
  stats,
  accounts,
  budgets,
  commitments,
  obligations,
  transactions,
  locale,
  labels,
}: CommonLabels & {
  stats: FinanceStats | null;
  accounts: FinancialAccount[];
  budgets: ProjectBudget[];
  commitments: FundingCommitment[];
  obligations: PaymentObligation[];
  transactions: FinanceTransaction[];
}) {
  const currency = primaryCurrency(stats);
  const cash = sumCurrencyTotals(stats?.total_cash);
  const available = sumCurrencyTotals(stats?.available_cash);
  const restricted = restrictedCash(accounts);
  const receivables = sumCurrencyTotals(stats?.pending_receivables);
  const payables = sumCurrencyTotals(stats?.upcoming_payments) + sumCurrencyTotals(stats?.overdue_payments);
  const invFunds = investorFundsCash(accounts);
  const construction = constructionBudgetTotal(budgets);
  const burn = monthlyBurn(transactions);
  const runway = runwayMonths(available, burn);
  const expectedCollections = receivables;
  const expectedPayments = payables;
  const net = expectedCollections - expectedPayments;

  const kpis = [
    { key: 'cash', label: lab(labels, 'kpiCash'), value: formatMoney(cash, currency, locale), spark: sparkFromBase(cash) },
    { key: 'available', label: lab(labels, 'kpiAvailable'), value: formatMoney(available, currency, locale), spark: sparkFromBase(available) },
    { key: 'restricted', label: lab(labels, 'kpiRestricted'), value: formatMoney(restricted, currency, locale), spark: sparkFromBase(restricted) },
    { key: 'ar', label: lab(labels, 'kpiReceivables'), value: formatMoney(receivables, currency, locale), spark: sparkFromBase(receivables) },
    { key: 'ap', label: lab(labels, 'kpiPayables'), value: formatMoney(payables, currency, locale), spark: sparkFromBase(payables) },
    { key: 'investor', label: lab(labels, 'kpiInvestorFunds'), value: formatMoney(invFunds, currency, locale), spark: sparkFromBase(invFunds) },
    { key: 'budget', label: lab(labels, 'kpiConstruction'), value: formatMoney(construction, currency, locale), spark: sparkFromBase(construction) },
    { key: 'burn', label: lab(labels, 'kpiBurn'), value: formatMoney(burn, currency, locale), spark: sparkFromBase(burn) },
    {
      key: 'runway',
      label: lab(labels, 'kpiRunway'),
      value: runway === null ? '—' : `${runway} ${lab(labels, 'months')}`,
      spark: sparkFromBase(runway ?? 0),
    },
    { key: 'collections', label: lab(labels, 'kpiCollections'), value: formatMoney(expectedCollections, currency, locale), spark: sparkFromBase(expectedCollections) },
    { key: 'payments', label: lab(labels, 'kpiExpectedPayments'), value: formatMoney(expectedPayments, currency, locale), spark: sparkFromBase(expectedPayments) },
    { key: 'net', label: lab(labels, 'kpiNet'), value: formatMoney(net, currency, locale), spark: sparkFromBase(Math.abs(net)) },
  ];

  const cashTrend = sparkFromBase(cash).map((v, i) => ({ label: `T${i + 1}`, value: v }));
  const flowBars = [
    { label: lab(labels, 'inflowShort'), value: Math.max(expectedCollections, available * 0.15, cash * 0.1) },
    { label: lab(labels, 'outflowShort'), value: Math.max(expectedPayments, available * 0.2) },
    { label: lab(labels, 'budgetShort'), value: Math.max(construction / 12, burn || available * 0.08) },
  ];

  const lateInvestor = commitments.filter((c) => c.status === 'delayed').length;
  const overdueObl = obligations.filter((o) => o.status === 'overdue').length;
  const overrun = budgets.filter((b) => num(b.variance) < 0).length;
  const fundingGap = sumCurrencyTotals(stats?.remaining_funding_need);
  const forecast = buildForecast(commitments, obligations, transactions, locale);
  const insights = deriveInsights({
    availableCash: available,
    burn,
    overdueObligations: overdueObl,
    lateInvestor,
    budgetOverrun: overrun,
    fundingGap,
    forecastNet90: forecast.find((f) => f.days === 90)?.net ?? 0,
  });

  return (
    <div data-testid="fin-g5-executive">
      <div className="fin-g5__toolbar">
        <div className="fin-g5__toolbar-left">
          <DataTag kind="live" label={lab(labels, 'liveTag')} />
          <span className="fin-g5__subtitle" style={{ margin: 0 }}>
            {lab(labels, 'executiveNote')}
          </span>
        </div>
      </div>

      <div className="fin-g5__kpis" style={{ marginTop: '0.35rem' }}>
        {kpis.map((kpi) => (
          <article key={kpi.key} className="fin-g5__kpi" data-testid={`fin-g5-kpi-${kpi.key}`}>
            <p>{kpi.label}</p>
            <strong>{kpi.value}</strong>
            <div className="fin-g5__kpi-spark">
              <Sparkline values={kpi.spark} ariaLabel={kpi.label} locale={locale} format="compact" />
            </div>
          </article>
        ))}
      </div>

      <div className="fin-g5__charts" style={{ marginTop: '0.65rem' }}>
        <div className="fin-g5__chart-card">
          <h4>{lab(labels, 'chartCashTrend')}</h4>
          <LineChart data={cashTrend} ariaLabel={lab(labels, 'chartCashTrend')} locale={locale} format="compact" height={140} />
        </div>
        <div className="fin-g5__chart-card">
          <h4>{lab(labels, 'chartCashFlow')}</h4>
          <BarChart data={flowBars} ariaLabel={lab(labels, 'chartCashFlow')} locale={locale} />
        </div>
      </div>

      <div className="fin-g5__panel" style={{ marginTop: '0.65rem' }}>
        <h3>{lab(labels, 'insightsTitle')}</h3>
        <p>{lab(labels, 'insightsSubtitle')}</p>
        {insights.length === 0 ? (
          <div className="fin-g5__empty">{lab(labels, 'insightsEmpty')}</div>
        ) : (
          <div className="fin-g5__insights">
            {insights.map((item) => (
              <div
                key={item.id}
                className={`fin-g5__insight fin-g5__insight--${item.severity === 'critical' ? 'critical' : item.severity === 'warn' ? 'warn' : 'info'}`}
              >
                <strong>{lab(labels, `insight.${item.kind}.title`)}</strong>
                <span>{lab(labels, `insight.${item.kind}.body`)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="fin-g5__banner fin-g5__banner--gap" style={{ marginTop: '0.55rem' }}>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} /> {lab(labels, 'sparkNote')}
      </p>
    </div>
  );
}

export function CashPositionPanel({
  accounts,
  locale,
  labels,
  onOpenAccount,
}: CommonLabels & {
  accounts: FinancialAccount[];
  onOpenAccount: (account: FinancialAccount) => void;
}) {
  const rows = accounts.map((a) => {
    const current = num(a.current_balance);
    const available = num(a.available_balance);
    const pending = Math.max(current - available, 0);
    const reserved =
      a.account_type === 'escrow' || a.account_type === 'reserve' || a.account_type === 'investor_funds'
        ? current * 0.15
        : 0;
    return { account: a, current, available, pending, reserved };
  });

  return (
    <div className="fin-g5__panel" data-testid="fin-g5-cash">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'cashTitle')}</h3>
          <p>{lab(labels, 'cashSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="fin-g5__list-wrap">
        <table className="fin-g5__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colBank')}</th>
              <th>{lab(labels, 'colCurrency')}</th>
              <th>{lab(labels, 'colBalance')}</th>
              <th>{lab(labels, 'colAvailable')}</th>
              <th>{lab(labels, 'colPending')}</th>
              <th>{lab(labels, 'colReserved')}</th>
              <th>{lab(labels, 'colLastSync')}</th>
              <th>{lab(labels, 'colTrend')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={8}>
                  <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              rows.map(({ account, current, available, pending, reserved }) => (
                <tr key={account.id} onClick={() => onOpenAccount(account)} data-testid={`fin-g5-cash-row-${account.id}`}>
                  <td>
                    <strong>{account.institution_name || account.account_name}</strong>
                    <div className="fin-g5__mono">{account.account_name}</div>
                  </td>
                  <td>{account.currency}</td>
                  <td>{formatMoney(current, account.currency, locale)}</td>
                  <td>{formatMoney(available, account.currency, locale)}</td>
                  <td>{formatMoney(pending, account.currency, locale)}</td>
                  <td>{formatMoney(reserved, account.currency, locale)}</td>
                  <td>{formatShortDate(account.updated_at, locale)}</td>
                  <td style={{ width: 90 }}>
                    <Sparkline values={sparkFromBase(current, 6)} ariaLabel={account.account_name} locale={locale} format="compact" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function BankAccountsPanel({
  accounts,
  locale,
  labels,
  onOpenAccount,
}: CommonLabels & {
  accounts: FinancialAccount[];
  onOpenAccount: (account: FinancialAccount) => void;
}) {
  return (
    <div className="fin-g5__panel" data-testid="fin-g5-accounts">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'accountsTitle')}</h3>
          <p>{lab(labels, 'accountsSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="fin-g5__list-wrap">
        <table className="fin-g5__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colInstitution')}</th>
              <th>{lab(labels, 'colAccount')}</th>
              <th>{lab(labels, 'colCompany')}</th>
              <th>{lab(labels, 'colCurrency')}</th>
              <th>{lab(labels, 'colBalance')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colLastActivity')}</th>
            </tr>
          </thead>
          <tbody>
            {accounts.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              accounts.map((a) => (
                <tr key={a.id} onClick={() => onOpenAccount(a)} data-testid={`fin-g5-account-row-${a.id}`}>
                  <td>{a.institution_name || '—'}</td>
                  <td>
                    <strong>{a.account_name}</strong>
                    <div className="fin-g5__mono">{a.account_reference || a.account_type}</div>
                  </td>
                  <td>{a.ownership_entity || '—'}</td>
                  <td>{a.currency}</td>
                  <td>{formatMoney(a.current_balance, a.currency, locale)}</td>
                  <td>
                    <span className={`fin-g5__status fin-g5__status--${statusTone(a.status)}`}>{a.status}</span>
                  </td>
                  <td>{formatShortDate(a.updated_at, locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function WiresTable({
  rows,
  locale,
  labels,
  testId,
  kind,
  onOpen,
}: CommonLabels & {
  rows: WireRow[];
  testId: string;
  kind: 'in' | 'out';
  onOpen?: (id: string) => void;
}) {
  const statuses =
    kind === 'in'
      ? ['pending', 'completed', 'returned']
      : ['scheduled', 'approved', 'released', 'cancelled'];

  const [filter, setFilter] = useState<string>('all');
  const filtered = filter === 'all' ? rows : rows.filter((r) => r.status === filter);

  return (
    <div className="fin-g5__panel" data-testid={testId}>
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, kind === 'in' ? 'wiresInTitle' : 'wiresOutTitle')}</h3>
          <p>{lab(labels, kind === 'in' ? 'wiresInSubtitle' : 'wiresOutSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <div className="fin-g5__seg" role="group" style={{ marginBottom: '0.55rem' }}>
        <button type="button" className={filter === 'all' ? 'is-active' : ''} onClick={() => setFilter('all')}>
          {lab(labels, 'allStatuses')}
        </button>
        {statuses.map((s) => (
          <button key={s} type="button" className={filter === s ? 'is-active' : ''} onClick={() => setFilter(s)}>
            {lab(labels, `wireStatus.${s}`)}
          </button>
        ))}
      </div>
      <p className="fin-g5__banner fin-g5__banner--gap">{lab(labels, 'wiresGap')}</p>
      <div className="fin-g5__list-wrap" style={{ marginTop: '0.45rem' }}>
        <table className="fin-g5__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colCounterparty')}</th>
              <th>{lab(labels, 'colAmount')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colDate')}</th>
              <th>{lab(labels, 'colReference')}</th>
              <th>{lab(labels, 'colProject')}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              filtered.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => onOpen?.(r.id.replace(/^obl-/, ''))}
                  data-testid={`fin-g5-wire-${r.id}`}
                >
                  <td>
                    <strong>{r.counterparty}</strong>
                    {r.isDemo ? <div className="fin-g5__data-tag fin-g5__data-tag--demo">{lab(labels, 'demoTag')}</div> : null}
                  </td>
                  <td>{formatMoney(r.amount, r.currency, locale)}</td>
                  <td>
                    <span className={`fin-g5__status fin-g5__status--${statusTone(r.status)}`}>
                      {lab(labels, `wireStatus.${r.status}`)}
                    </span>
                  </td>
                  <td>{formatShortDate(r.date, locale)}</td>
                  <td className="fin-g5__mono">{r.reference || '—'}</td>
                  <td>{r.projectName || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function IncomingWiresPanel({
  transactions,
  locale,
  labels,
  onOpenTransaction,
}: CommonLabels & {
  transactions: FinanceTransaction[];
  onOpenTransaction: (id: string) => void;
}) {
  const rows = useMemo(() => deriveIncomingWires(transactions), [transactions]);
  return (
    <WiresTable
      rows={rows}
      locale={locale}
      labels={labels}
      testId="fin-g5-wires-in"
      kind="in"
      onOpen={onOpenTransaction}
    />
  );
}

export function OutgoingWiresPanel({
  transactions,
  obligations,
  locale,
  labels,
  onOpenTransaction,
}: CommonLabels & {
  transactions: FinanceTransaction[];
  obligations: PaymentObligation[];
  onOpenTransaction: (id: string) => void;
}) {
  const rows = useMemo(() => deriveOutgoingWires(transactions, obligations), [transactions, obligations]);
  return (
    <WiresTable
      rows={rows}
      locale={locale}
      labels={labels}
      testId="fin-g5-wires-out"
      kind="out"
      onOpen={onOpenTransaction}
    />
  );
}

export function InvestorPaymentsPanel({
  commitments,
  transactions,
  locale,
  labels,
}: CommonLabels & {
  commitments: FundingCommitment[];
  transactions: FinanceTransaction[];
}) {
  const rows = useMemo(
    () => deriveInvestorPayments(commitments, transactions),
    [commitments, transactions],
  );
  const [kind, setKind] = useState<string>('all');
  const kinds = ['reservation', 'deposit', 'progress', 'final', 'refund', 'late', 'outstanding'];
  const filtered = kind === 'all' ? rows : rows.filter((r) => r.kind === kind);

  return (
    <div className="fin-g5__panel" data-testid="fin-g5-investor-payments">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'investorPayTitle')}</h3>
          <p>{lab(labels, 'investorPaySubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <div className="fin-g5__seg" style={{ marginBottom: '0.55rem' }}>
        <button type="button" className={kind === 'all' ? 'is-active' : ''} onClick={() => setKind('all')}>
          {lab(labels, 'allKinds')}
        </button>
        {kinds.map((k) => (
          <button key={k} type="button" className={kind === k ? 'is-active' : ''} onClick={() => setKind(k)}>
            {lab(labels, `investorKind.${k}`)}
          </button>
        ))}
      </div>
      <PaymentInvestorTable rows={filtered} locale={locale} labels={labels} />
    </div>
  );
}

function PaymentInvestorTable({
  rows,
  locale,
  labels,
}: {
  rows: InvestorPaymentRow[];
  locale: string;
  labels: Record<string, string>;
}) {
  return (
    <div className="fin-g5__list-wrap">
      <table className="fin-g5__table">
        <thead>
          <tr>
            <th>{lab(labels, 'colInvestor')}</th>
            <th>{lab(labels, 'colProject')}</th>
            <th>{lab(labels, 'colKind')}</th>
            <th>{lab(labels, 'colAmount')}</th>
            <th>{lab(labels, 'colStatus')}</th>
            <th>{lab(labels, 'colDate')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={6}>
                <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
              </td>
            </tr>
          ) : (
            rows.map((r) => (
              <tr key={r.id}>
                <td>
                  <strong>{r.investorName}</strong>
                </td>
                <td>{r.projectName || '—'}</td>
                <td>{lab(labels, `investorKind.${r.kind}`)}</td>
                <td>{formatMoney(r.amount, r.currency, locale)}</td>
                <td>
                  <span className={`fin-g5__status fin-g5__status--${statusTone(r.status)}`}>{r.status}</span>
                </td>
                <td>{formatShortDate(r.date, locale)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function VendorPaymentsPanel({
  obligations,
  locale,
  labels,
}: CommonLabels & { obligations: PaymentObligation[] }) {
  const rows = useMemo(() => deriveVendorPayments(obligations), [obligations]);
  return (
    <div className="fin-g5__panel" data-testid="fin-g5-vendor-payments">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'vendorPayTitle')}</h3>
          <p>{lab(labels, 'vendorPaySubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <VendorTable rows={rows} locale={locale} labels={labels} />
    </div>
  );
}

function VendorTable({
  rows,
  locale,
  labels,
}: {
  rows: VendorPaymentRow[];
  locale: string;
  labels: Record<string, string>;
}) {
  return (
    <div className="fin-g5__list-wrap">
      <table className="fin-g5__table">
        <thead>
          <tr>
            <th>{lab(labels, 'colVendor')}</th>
            <th>{lab(labels, 'colInvoice')}</th>
            <th>{lab(labels, 'colDueDate')}</th>
            <th>{lab(labels, 'colApproval')}</th>
            <th>{lab(labels, 'colPayment')}</th>
            <th>{lab(labels, 'colRetention')}</th>
            <th>{lab(labels, 'colOutstanding')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={7}>
                <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
              </td>
            </tr>
          ) : (
            rows.map((r) => (
              <tr key={r.id}>
                <td>
                  <strong>{r.payee}</strong>
                  <div style={{ fontSize: '0.68rem', color: 'var(--fin-muted)' }}>{r.projectName || '—'}</div>
                </td>
                <td className="fin-g5__mono">{r.invoice}</td>
                <td>{formatShortDate(r.dueDate, locale)}</td>
                <td>
                  <span className={`fin-g5__status fin-g5__status--${statusTone(r.approval)}`}>
                    {lab(labels, `approvalState.${r.approval}`)}
                  </span>
                </td>
                <td>
                  <span className={`fin-g5__status fin-g5__status--${statusTone(r.paymentStatus)}`}>
                    {r.paymentStatus}
                  </span>
                </td>
                <td>{formatMoney(r.retention, r.currency, locale)}</td>
                <td>{formatMoney(r.outstanding, r.currency, locale)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function ArPanel({
  stats,
  transactions,
  locale,
  labels,
}: CommonLabels & { stats: FinanceStats | null; transactions: FinanceTransaction[] }) {
  const currency = primaryCurrency(stats);
  const pending = transactions.filter(
    (tx) =>
      ['income', 'investment_inflow', 'sale_proceeds', 'rental_income'].includes(tx.transaction_type) &&
      ['pending', 'scheduled', 'overdue'].includes(tx.status),
  );
  return (
    <div className="fin-g5__panel" data-testid="fin-g5-ar">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'arTitle')}</h3>
          <p>{lab(labels, 'arSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <div className="fin-g5__kpis" style={{ marginBottom: '0.65rem' }}>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'kpiReceivables')}</p>
          <strong>{formatMoney(sumCurrencyTotals(stats?.pending_receivables), currency, locale)}</strong>
        </article>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'openItems')}</p>
          <strong>{String(pending.length)}</strong>
        </article>
      </div>
      <TxnMiniTable rows={pending} locale={locale} labels={labels} />
    </div>
  );
}

export function ApPanel({
  stats,
  obligations,
  locale,
  labels,
}: CommonLabels & { stats: FinanceStats | null; obligations: PaymentObligation[] }) {
  const currency = primaryCurrency(stats);
  const open = obligations.filter((o) => o.status !== 'paid' && o.status !== 'cancelled');
  return (
    <div className="fin-g5__panel" data-testid="fin-g5-ap">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'apTitle')}</h3>
          <p>{lab(labels, 'apSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <div className="fin-g5__kpis" style={{ marginBottom: '0.65rem' }}>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'kpiPayables')}</p>
          <strong>
            {formatMoney(
              sumCurrencyTotals(stats?.upcoming_payments) + sumCurrencyTotals(stats?.overdue_payments),
              currency,
              locale,
            )}
          </strong>
        </article>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'openItems')}</p>
          <strong>{String(open.length)}</strong>
        </article>
      </div>
      <div className="fin-g5__list-wrap">
        <table className="fin-g5__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colPayee')}</th>
              <th>{lab(labels, 'colType')}</th>
              <th>{lab(labels, 'colAmount')}</th>
              <th>{lab(labels, 'colDueDate')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colPriority')}</th>
            </tr>
          </thead>
          <tbody>
            {open.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              open.map((o) => (
                <tr key={o.id}>
                  <td>
                    <strong>{o.payee || o.description || '—'}</strong>
                  </td>
                  <td>{o.obligation_type}</td>
                  <td>{formatMoney(o.amount, o.currency, locale)}</td>
                  <td>{formatShortDate(o.due_date, locale)}</td>
                  <td>
                    <span className={`fin-g5__status fin-g5__status--${statusTone(o.status)}`}>{o.status}</span>
                  </td>
                  <td>{o.priority}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TxnMiniTable({
  rows,
  locale,
  labels,
}: {
  rows: FinanceTransaction[];
  locale: string;
  labels: Record<string, string>;
}) {
  return (
    <div className="fin-g5__list-wrap">
      <table className="fin-g5__table">
        <thead>
          <tr>
            <th>{lab(labels, 'colDate')}</th>
            <th>{lab(labels, 'colCounterparty')}</th>
            <th>{lab(labels, 'colAmount')}</th>
            <th>{lab(labels, 'colStatus')}</th>
            <th>{lab(labels, 'colProject')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={5}>
                <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
              </td>
            </tr>
          ) : (
            rows.map((tx) => (
              <tr key={tx.id}>
                <td>{formatShortDate(tx.due_date || tx.transaction_date, locale)}</td>
                <td>{tx.counterparty || tx.investor_name || tx.description || '—'}</td>
                <td>{formatMoney(tx.amount, tx.currency, locale)}</td>
                <td>
                  <span className={`fin-g5__status fin-g5__status--${statusTone(tx.status)}`}>{tx.status}</span>
                </td>
                <td>{tx.project_name || '—'}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function TreasuryPanel({
  stats,
  accounts,
  obligations,
  commitments,
  locale,
  labels,
}: CommonLabels & {
  stats: FinanceStats | null;
  accounts: FinancialAccount[];
  obligations: PaymentObligation[];
  commitments: FundingCommitment[];
}) {
  const currency = primaryCurrency(stats);
  const liquidity = sumCurrencyTotals(stats?.available_cash);
  const expected = commitments.reduce((s, c) => s + num(c.remaining_amount), 0);
  const debt = debtBalance(accounts);
  const credit = accounts
    .filter((a) => a.account_type === 'operating' || a.account_type === 'reserve')
    .reduce((s, a) => s + Math.max(num(a.available_balance) * 0.2, 0), 0);
  const upcoming = obligations
    .filter((o) => o.status === 'upcoming' || o.status === 'due')
    .reduce((s, o) => s + num(o.amount), 0);

  const bars = [
    { label: lab(labels, 'liquidity'), value: Math.max(liquidity, 1) },
    { label: lab(labels, 'expectedLiq'), value: Math.max(expected, 1) },
    { label: lab(labels, 'debt'), value: Math.max(debt, 1) },
    { label: lab(labels, 'creditLines'), value: Math.max(credit, 1) },
    { label: lab(labels, 'obligations'), value: Math.max(upcoming, 1) },
  ];

  return (
    <div className="fin-g5__panel" data-testid="fin-g5-treasury">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'treasuryTitle')}</h3>
          <p>{lab(labels, 'treasurySubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <div className="fin-g5__kpis" style={{ marginBottom: '0.65rem' }}>
        {[
          ['liquidity', liquidity],
          ['expectedLiq', expected],
          ['debt', debt],
          ['creditLines', credit],
          ['obligations', upcoming],
        ].map(([key, value]) => (
          <article key={String(key)} className="fin-g5__kpi">
            <p>{lab(labels, String(key))}</p>
            <strong>{formatMoney(value as number, currency, locale)}</strong>
          </article>
        ))}
      </div>
      <div className="fin-g5__chart-card">
        <h4>{lab(labels, 'treasuryMix')}</h4>
        <BarChart data={bars} ariaLabel={lab(labels, 'treasuryMix')} locale={locale} />
      </div>
      <p className="fin-g5__banner fin-g5__banner--gap" style={{ marginTop: '0.55rem' }}>
        {lab(labels, 'treasuryGap')}
      </p>
    </div>
  );
}

export function ForecastPanel({
  commitments,
  obligations,
  transactions,
  locale,
  labels,
}: CommonLabels & {
  commitments: FundingCommitment[];
  obligations: PaymentObligation[];
  transactions: FinanceTransaction[];
}) {
  const horizons = useMemo(
    () => buildForecast(commitments, obligations, transactions, locale),
    [commitments, obligations, transactions, locale],
  );
  const [days, setDays] = useState(90);
  const active =
    horizons.find((h) => h.days === days) ??
    horizons[2] ?? {
      days: 90,
      label: '90',
      inflow: 0,
      outflow: 0,
      net: 0,
      funding: 0,
      collections: 0,
    };
  const currency = 'USD';
  const line = horizons.map((h) => ({ label: h.label, value: h.net }));

  return (
    <div className="fin-g5__panel" data-testid="fin-g5-forecast">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'forecastTitle')}</h3>
          <p>{lab(labels, 'forecastSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <div className="fin-g5__seg" style={{ marginBottom: '0.55rem' }}>
        {horizons.map((h) => (
          <button
            key={h.days}
            type="button"
            className={days === h.days ? 'is-active' : ''}
            onClick={() => setDays(h.days)}
          >
            {h.label}
          </button>
        ))}
      </div>
      <div className="fin-g5__kpis" style={{ marginBottom: '0.65rem' }}>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'expectedRevenue')}</p>
          <strong>{formatMoney(active.inflow, currency, locale)}</strong>
        </article>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'expectedExpenses')}</p>
          <strong>{formatMoney(active.outflow, currency, locale)}</strong>
        </article>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'projectFunding')}</p>
          <strong>{formatMoney(active.funding, currency, locale)}</strong>
        </article>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'investorCollections')}</p>
          <strong>{formatMoney(active.collections, currency, locale)}</strong>
        </article>
        <article className="fin-g5__kpi">
          <p>{lab(labels, 'kpiNet')}</p>
          <strong>{formatMoney(active.net, currency, locale)}</strong>
        </article>
      </div>
      <div className="fin-g5__chart-card">
        <h4>{lab(labels, 'chartForecast')}</h4>
        <LineChart data={line} ariaLabel={lab(labels, 'chartForecast')} locale={locale} format="compact" height={150} />
      </div>
    </div>
  );
}

export function BudgetPanel({
  budgets,
  locale,
  labels,
}: CommonLabels & { budgets: ProjectBudget[] }) {
  return (
    <div className="fin-g5__panel" data-testid="fin-g5-budget">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'budgetTitle')}</h3>
          <p>{lab(labels, 'budgetSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="fin-g5__list-wrap">
        <table className="fin-g5__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colProject')}</th>
              <th>{lab(labels, 'colName')}</th>
              <th>{lab(labels, 'colCategory')}</th>
              <th>{lab(labels, 'colOriginal')}</th>
              <th>{lab(labels, 'colRevised')}</th>
              <th>{lab(labels, 'colCommitted')}</th>
              <th>{lab(labels, 'colPaid')}</th>
              <th>{lab(labels, 'colForecast')}</th>
              <th>{lab(labels, 'colVariance')}</th>
            </tr>
          </thead>
          <tbody>
            {budgets.length === 0 ? (
              <tr>
                <td colSpan={9}>
                  <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              budgets.map((b) => (
                <tr key={b.id}>
                  <td>{b.project_name || '—'}</td>
                  <td>
                    <strong>{b.budget_name}</strong>
                  </td>
                  <td>{b.category}</td>
                  <td>{formatMoney(b.original_budget, b.currency, locale)}</td>
                  <td>{formatMoney(b.revised_budget, b.currency, locale)}</td>
                  <td>{formatMoney(b.committed_amount, b.currency, locale)}</td>
                  <td>{formatMoney(b.paid_amount, b.currency, locale)}</td>
                  <td>{formatMoney(b.forecast_amount, b.currency, locale)}</td>
                  <td>{formatMoney(b.variance, b.currency, locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ApprovalsPanel({
  approvals,
  pendingTransactions,
  locale,
  labels,
  loading,
}: CommonLabels & {
  approvals: ApprovalItem[];
  pendingTransactions: FinanceTransaction[];
  loading: boolean;
}) {
  return (
    <div className="fin-g5__panel" data-testid="fin-g5-approvals">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'approvalsTitle')}</h3>
          <p>{lab(labels, 'approvalsSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      {loading ? <div className="fin-g5__empty">{lab(labels, 'loading')}</div> : null}
      <h3 style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>{lab(labels, 'executiveApprovals')}</h3>
      <div className="fin-g5__list-wrap" style={{ marginBottom: '0.75rem' }}>
        <table className="fin-g5__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colType')}</th>
              <th>{lab(labels, 'colRelated')}</th>
              <th>{lab(labels, 'colAge')}</th>
              <th>{lab(labels, 'colSubmitted')}</th>
            </tr>
          </thead>
          <tbody>
            {approvals.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div className="fin-g5__empty">{lab(labels, 'emptyApprovals')}</div>
                </td>
              </tr>
            ) : (
              approvals.map((a) => (
                <tr key={`${a.approval_type}-${a.entity_id}`}>
                  <td>{a.approval_type}</td>
                  <td>{a.related_label || a.entity_type}</td>
                  <td>{a.age_days ?? '—'}</td>
                  <td>{formatShortDate(a.submitted_at, locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <h3 style={{ fontSize: '0.8rem' }}>{lab(labels, 'pendingTransactions')}</h3>
      <TxnMiniTable rows={pendingTransactions} locale={locale} labels={labels} />
    </div>
  );
}

export function DocumentsPanel({ locale, labels }: CommonLabels) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const byFolder = await fetchDocuments({ folder: 'finance', page_size: 50, sort_by: 'updated_at', sort_dir: 'desc' });
        let items = byFolder.items;
        if (items.length === 0) {
          const byType = await fetchDocuments({
            page_size: 50,
            sort_by: 'updated_at',
            sort_dir: 'desc',
          });
          items = byType.items.filter((d) =>
            ['invoice', 'receipt', 'bank_statement', 'financial_report', 'loan_document', 'tax_document'].includes(
              d.document_type,
            ) || d.folder === 'finance',
          );
        }
        if (!cancelled) setDocs(items);
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="fin-g5__panel" data-testid="fin-g5-documents">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'documentsTitle')}</h3>
          <p>{lab(labels, 'documentsSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      {loading ? <div className="fin-g5__empty">{lab(labels, 'loading')}</div> : null}
      {error ? <div className="fin-g5__banner">{lab(labels, 'documentsError')}</div> : null}
      <div className="fin-g5__list-wrap">
        <table className="fin-g5__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colName')}</th>
              <th>{lab(labels, 'colType')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colDate')}</th>
            </tr>
          </thead>
          <tbody>
            {!loading && docs.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div className="fin-g5__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              docs.map((d) => (
                <tr key={d.id}>
                  <td>
                    <strong>{d.title}</strong>
                    <div className="fin-g5__mono">{d.original_file_name}</div>
                  </td>
                  <td>{d.document_type}</td>
                  <td>
                    <span className={`fin-g5__status fin-g5__status--${statusTone(d.status)}`}>{d.status}</span>
                  </td>
                  <td>{formatShortDate(d.updated_at || d.created_at, locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <span style={{ display: 'none' }}>{locale}</span>
    </div>
  );
}

export function AuditPanel({
  transactions,
  accounts,
  locale,
  labels,
}: CommonLabels & {
  transactions: FinanceTransaction[];
  accounts: FinancialAccount[];
}) {
  const [entries, setEntries] = useState<ActivityLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const sample = [...transactions.slice(0, 8), ...accounts.slice(0, 4)];
      const results: ActivityLogEntry[] = [];
      for (const item of sample) {
        const isAccount = 'account_name' in item;
        try {
          const res = await fetchEntityActivity(
            isAccount ? 'financial_account' : 'transaction',
            item.id,
            3,
          );
          results.push(...(res.items ?? []));
        } catch {
          /* entity may not support activity */
        }
      }
      if (!cancelled) {
        setEntries(
          results.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))).slice(0, 40),
        );
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [transactions, accounts]);

  const fallback = useMemo(() => {
    return [...transactions]
      .sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)))
      .slice(0, 25)
      .map((tx) => ({
        id: tx.id,
        action: tx.status,
        label: tx.description || tx.transaction_type,
        at: tx.updated_at,
        entity: 'transaction',
      }));
  }, [transactions]);

  return (
    <div className="fin-g5__panel" data-testid="fin-g5-audit">
      <div className="fin-g5__toolbar">
        <div>
          <h3>{lab(labels, 'auditTitle')}</h3>
          <p>{lab(labels, 'auditSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      {loading ? <div className="fin-g5__empty">{lab(labels, 'loading')}</div> : null}
      {entries.length > 0 ? (
        <div className="fin-g5__list-wrap">
          <table className="fin-g5__table">
            <thead>
              <tr>
                <th>{lab(labels, 'colDate')}</th>
                <th>{lab(labels, 'colAction')}</th>
                <th>{lab(labels, 'colEntity')}</th>
                <th>{lab(labels, 'colActor')}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>{formatShortDate(e.created_at, locale)}</td>
                  <td>{e.action || e.event_type || '—'}</td>
                  <td>{e.entity_label || e.entity_type || '—'}</td>
                  <td>{e.actor_name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <>
          <p className="fin-g5__banner fin-g5__banner--gap">{lab(labels, 'auditGap')}</p>
          <div className="fin-g5__list-wrap" style={{ marginTop: '0.45rem' }}>
            <table className="fin-g5__table">
              <thead>
                <tr>
                  <th>{lab(labels, 'colDate')}</th>
                  <th>{lab(labels, 'colAction')}</th>
                  <th>{lab(labels, 'colEntity')}</th>
                </tr>
              </thead>
              <tbody>
                {fallback.map((f) => (
                  <tr key={f.id}>
                    <td>{formatShortDate(f.at, locale)}</td>
                    <td>{f.action}</td>
                    <td>{f.label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
