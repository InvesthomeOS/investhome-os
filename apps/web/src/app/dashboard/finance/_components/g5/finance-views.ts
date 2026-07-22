export const FINANCE_VIEWS = [
  'executive',
  'cash',
  'accounts',
  'wires_in',
  'wires_out',
  'investor_payments',
  'vendor_payments',
  'ar',
  'ap',
  'treasury',
  'forecast',
  'budget',
  'approvals',
  'documents',
  'audit',
] as const;

export type FinanceViewId = (typeof FINANCE_VIEWS)[number];

export function parseView(raw: string | null): FinanceViewId {
  if (raw && (FINANCE_VIEWS as readonly string[]).includes(raw)) {
    return raw as FinanceViewId;
  }
  return 'executive';
}

export type DataKind = 'live' | 'partial' | 'demo' | 'blocked';

export const VIEW_DATA_KIND: Record<FinanceViewId, DataKind> = {
  executive: 'live',
  cash: 'live',
  accounts: 'live',
  wires_in: 'partial',
  wires_out: 'partial',
  investor_payments: 'partial',
  vendor_payments: 'partial',
  ar: 'partial',
  ap: 'partial',
  treasury: 'partial',
  forecast: 'partial',
  budget: 'live',
  approvals: 'partial',
  documents: 'live',
  audit: 'partial',
};
