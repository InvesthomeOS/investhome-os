import type {
  FinanceStats,
  FinanceTransaction,
  FinancialAccount,
  FundingCommitment,
  PaymentObligation,
  ProjectBudget,
} from '@/lib/api/finance';

export function sumCurrencyTotals(totals: Record<string, string> | undefined): number {
  if (!totals) return 0;
  return Object.values(totals).reduce((s, v) => s + (Number(v) || 0), 0);
}

export function num(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === '') return 0;
  const n = Number(value);
  return Number.isNaN(n) ? 0 : n;
}

export function sparkFromBase(base: number, points = 7): number[] {
  const safe = Math.abs(base) || 1;
  const factors = [0.62, 0.68, 0.74, 0.8, 0.88, 0.94, 1];
  return factors.slice(0, points).map((f) => Math.round(safe * f * 100) / 100);
}

export function primaryCurrency(stats: FinanceStats | null): string {
  if (!stats) return 'USD';
  const keys = Object.keys(stats.total_cash ?? {});
  if (keys.length === 0) return 'USD';
  const sorted = keys.sort((a, b) => num(stats.total_cash[b]) - num(stats.total_cash[a]));
  return sorted[0] ?? 'USD';
}

export type WireDirection = 'in' | 'out';

export interface WireRow {
  id: string;
  direction: WireDirection;
  counterparty: string;
  amount: number;
  currency: string;
  status: string;
  date: string | null;
  reference: string | null;
  projectName: string | null;
  source: 'transaction' | 'obligation';
  isDemo: boolean;
}

const INFLOW_TYPES = new Set([
  'income',
  'investment_inflow',
  'loan_draw',
  'sale_proceeds',
  'rental_income',
  'refund',
]);

const OUTFLOW_TYPES = new Set([
  'expense',
  'investor_distribution',
  'loan_payment',
  'acquisition',
  'construction_cost',
  'operating_cost',
]);

export function deriveIncomingWires(transactions: FinanceTransaction[]): WireRow[] {
  return transactions
    .filter(
      (tx) =>
        tx.payment_method === 'wire' &&
        (INFLOW_TYPES.has(tx.transaction_type) || tx.transaction_type === 'transfer'),
    )
    .map((tx) => ({
      id: tx.id,
      direction: 'in' as const,
      counterparty: tx.counterparty || tx.investor_name || tx.description || '—',
      amount: num(tx.amount),
      currency: tx.currency,
      status: mapIncomingWireStatus(tx.status),
      date: tx.transaction_date,
      reference: tx.reference_number,
      projectName: tx.project_name,
      source: 'transaction' as const,
      isDemo: tx.is_demo,
    }));
}

export function deriveOutgoingWires(
  transactions: FinanceTransaction[],
  obligations: PaymentObligation[],
): WireRow[] {
  const txRows: WireRow[] = transactions
    .filter((tx) => tx.payment_method === 'wire' && OUTFLOW_TYPES.has(tx.transaction_type))
    .map((tx) => ({
      id: tx.id,
      direction: 'out' as const,
      counterparty: tx.counterparty || tx.description || '—',
      amount: num(tx.amount),
      currency: tx.currency,
      status: mapOutgoingWireStatus(tx.status),
      date: tx.due_date || tx.transaction_date,
      reference: tx.reference_number,
      projectName: tx.project_name,
      source: 'transaction' as const,
      isDemo: tx.is_demo,
    }));

  const oblRows: WireRow[] = obligations
    .filter((o) => o.status !== 'cancelled' && o.status !== 'paid')
    .slice(0, 40)
    .map((o) => ({
      id: `obl-${o.id}`,
      direction: 'out' as const,
      counterparty: o.payee || o.description || '—',
      amount: num(o.amount),
      currency: o.currency,
      status: mapObligationToWire(o.status),
      date: o.due_date,
      reference: null,
      projectName: o.project_name,
      source: 'obligation' as const,
      isDemo: o.is_demo,
    }));

  return [...txRows, ...oblRows];
}

function mapIncomingWireStatus(status: string): string {
  if (status === 'completed') return 'completed';
  if (status === 'cancelled') return 'returned';
  return 'pending';
}

function mapOutgoingWireStatus(status: string): string {
  if (status === 'scheduled') return 'scheduled';
  if (status === 'pending') return 'approved';
  if (status === 'completed') return 'released';
  if (status === 'cancelled') return 'cancelled';
  return 'scheduled';
}

function mapObligationToWire(status: string): string {
  if (status === 'overdue' || status === 'due') return 'approved';
  if (status === 'upcoming') return 'scheduled';
  if (status === 'paid') return 'released';
  return 'scheduled';
}

export type InvestorPaymentKind =
  | 'reservation'
  | 'deposit'
  | 'progress'
  | 'final'
  | 'refund'
  | 'late'
  | 'outstanding';

export interface InvestorPaymentRow {
  id: string;
  investorName: string;
  projectName: string | null;
  kind: InvestorPaymentKind;
  amount: number;
  currency: string;
  status: string;
  date: string | null;
  isDemo: boolean;
}

export function deriveInvestorPayments(
  commitments: FundingCommitment[],
  transactions: FinanceTransaction[],
): InvestorPaymentRow[] {
  const fromFunding: InvestorPaymentRow[] = commitments.map((c) => {
    const remaining = num(c.remaining_amount);
    const funded = num(c.funded_amount);
    const committed = num(c.committed_amount);
    let kind: InvestorPaymentKind = 'outstanding';
    if (c.status === 'fully_funded') kind = 'final';
    else if (c.status === 'partially_funded') kind = 'progress';
    else if (c.status === 'delayed') kind = 'late';
    else if (funded === 0 && committed > 0) kind = 'reservation';
    else if (funded > 0 && remaining > 0) kind = 'deposit';
    return {
      id: c.id,
      investorName: c.investor_name || '—',
      projectName: c.project_name,
      kind,
      amount: remaining > 0 ? remaining : funded || committed,
      currency: c.currency,
      status: c.status,
      date: c.target_funding_date || c.commitment_date,
      isDemo: c.is_demo,
    };
  });

  const fromTx: InvestorPaymentRow[] = transactions
    .filter(
      (tx) =>
        tx.investor_id &&
        (tx.transaction_type === 'investment_inflow' ||
          tx.transaction_type === 'investor_distribution' ||
          tx.transaction_type === 'refund'),
    )
    .map((tx) => ({
      id: tx.id,
      investorName: tx.investor_name || tx.counterparty || '—',
      projectName: tx.project_name,
      kind:
        tx.transaction_type === 'refund'
          ? ('refund' as const)
          : tx.status === 'overdue'
            ? ('late' as const)
            : ('progress' as const),
      amount: num(tx.amount),
      currency: tx.currency,
      status: tx.status,
      date: tx.due_date || tx.transaction_date,
      isDemo: tx.is_demo,
    }));

  return [...fromFunding, ...fromTx];
}

export interface VendorPaymentRow {
  id: string;
  payee: string;
  projectName: string | null;
  invoice: string;
  dueDate: string | null;
  approval: string;
  paymentStatus: string;
  retention: number;
  outstanding: number;
  amount: number;
  currency: string;
  isDemo: boolean;
}

export function deriveVendorPayments(obligations: PaymentObligation[]): VendorPaymentRow[] {
  return obligations
    .filter(
      (o) =>
        o.obligation_type === 'vendor_payment' ||
        o.obligation_type === 'professional_fee' ||
        o.obligation_type === 'acquisition_payment' ||
        o.obligation_type === 'other',
    )
    .map((o) => {
      const amount = num(o.amount);
      const retention = Math.round(amount * 0.05 * 100) / 100;
      const outstanding = o.status === 'paid' ? 0 : amount;
      return {
        id: o.id,
        payee: o.payee || o.description || '—',
        projectName: o.project_name,
        invoice: o.description || o.id.slice(0, 8).toUpperCase(),
        dueDate: o.due_date,
        approval: o.priority === 'critical' || o.status === 'overdue' ? 'required' : 'cleared',
        paymentStatus: o.status,
        retention,
        outstanding,
        amount,
        currency: o.currency,
        isDemo: o.is_demo,
      };
    });
}

export function restrictedCash(accounts: FinancialAccount[]): number {
  return accounts
    .filter((a) => a.account_type === 'escrow' || a.account_type === 'investor_funds' || a.account_type === 'reserve')
    .reduce((s, a) => s + num(a.current_balance), 0);
}

export function investorFundsCash(accounts: FinancialAccount[]): number {
  return accounts
    .filter((a) => a.account_type === 'investor_funds')
    .reduce((s, a) => s + num(a.current_balance), 0);
}

export function debtBalance(accounts: FinancialAccount[]): number {
  return accounts
    .filter((a) => a.account_type === 'debt')
    .reduce((s, a) => s + Math.abs(num(a.current_balance)), 0);
}

export function constructionBudgetTotal(budgets: ProjectBudget[]): number {
  return budgets.reduce((s, b) => s + num(b.revised_budget ?? b.original_budget), 0);
}

export function monthlyBurn(transactions: FinanceTransaction[]): number {
  const now = new Date();
  const month = now.getMonth();
  const year = now.getFullYear();
  return transactions
    .filter((tx) => {
      if (!OUTFLOW_TYPES.has(tx.transaction_type) || tx.status === 'cancelled') return false;
      const d = new Date(tx.transaction_date);
      return d.getMonth() === month && d.getFullYear() === year;
    })
    .reduce((s, tx) => s + num(tx.amount), 0);
}

export function runwayMonths(availableCash: number, burn: number): number | null {
  if (burn <= 0) return null;
  return Math.round((availableCash / burn) * 10) / 10;
}

export interface ForecastHorizon {
  days: number;
  label: string;
  inflow: number;
  outflow: number;
  net: number;
  funding: number;
  collections: number;
}

export function buildForecast(
  commitments: FundingCommitment[],
  obligations: PaymentObligation[],
  transactions: FinanceTransaction[],
  locale: string,
): ForecastHorizon[] {
  const horizons = [30, 60, 90, 180, 365];
  const now = Date.now();
  const dayMs = 86_400_000;

  return horizons.map((days) => {
    const cutoff = now + days * dayMs;
    const funding = commitments
      .filter((c) => {
        const d = c.target_funding_date ? new Date(c.target_funding_date).getTime() : now;
        return d <= cutoff && c.status !== 'cancelled' && c.status !== 'fully_funded';
      })
      .reduce((s, c) => s + num(c.remaining_amount), 0);

    const collections = transactions
      .filter((tx) => {
        if (!INFLOW_TYPES.has(tx.transaction_type)) return false;
        if (tx.status !== 'pending' && tx.status !== 'scheduled' && tx.status !== 'overdue') return false;
        const d = new Date(tx.due_date || tx.transaction_date).getTime();
        return d <= cutoff;
      })
      .reduce((s, tx) => s + num(tx.amount), 0);

    const outflow = obligations
      .filter((o) => {
        if (o.status === 'paid' || o.status === 'cancelled') return false;
        const d = o.due_date ? new Date(o.due_date).getTime() : now;
        return d <= cutoff;
      })
      .reduce((s, o) => s + num(o.amount), 0);

    const inflow = funding + collections;
    const label =
      locale === 'tr' ? `${days} gün` : `${days}d`;
    return {
      days,
      label,
      inflow,
      outflow,
      net: inflow - outflow,
      funding,
      collections,
    };
  });
}

export interface InsightItem {
  id: string;
  severity: 'info' | 'warn' | 'critical';
  kind: string;
}

export function deriveInsights(input: {
  availableCash: number;
  burn: number;
  overdueObligations: number;
  lateInvestor: number;
  budgetOverrun: number;
  fundingGap: number;
  forecastNet90: number;
}): InsightItem[] {
  const items: InsightItem[] = [];
  if (input.availableCash > 0 && input.burn > 0 && input.availableCash / input.burn < 3) {
    items.push({ id: 'cash-short', severity: 'critical', kind: 'cashShortage' });
  }
  if (input.overdueObligations > 0) {
    items.push({ id: 'large-pay', severity: 'warn', kind: 'upcomingPayments' });
  }
  if (input.lateInvestor > 0) {
    items.push({ id: 'late-inv', severity: 'warn', kind: 'delayedInvestor' });
  }
  if (input.budgetOverrun > 0) {
    items.push({ id: 'budget', severity: 'critical', kind: 'budgetOverrun' });
  }
  if (input.fundingGap > 0) {
    items.push({ id: 'funding', severity: 'warn', kind: 'fundingGap' });
  }
  if (input.forecastNet90 < 0) {
    items.push({ id: 'forecast', severity: 'info', kind: 'forecastAnomaly' });
  }
  return items;
}
