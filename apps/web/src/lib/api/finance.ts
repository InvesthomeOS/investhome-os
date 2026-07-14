import { apiFetch } from '@/lib/api/client';

export const ACCOUNT_TYPES = [
  'operating',
  'project',
  'escrow',
  'investor_funds',
  'reserve',
  'debt',
  'personal',
  'other',
] as const;

export type AccountType = (typeof ACCOUNT_TYPES)[number];

export const ACCOUNT_STATUSES = ['active', 'inactive', 'closed'] as const;

export type AccountStatus = (typeof ACCOUNT_STATUSES)[number];

export const TRANSACTION_TYPES = [
  'income',
  'expense',
  'transfer',
  'investment_inflow',
  'investor_distribution',
  'loan_draw',
  'loan_payment',
  'acquisition',
  'construction_cost',
  'operating_cost',
  'sale_proceeds',
  'rental_income',
  'refund',
  'other',
] as const;

export type TransactionType = (typeof TRANSACTION_TYPES)[number];

export const TRANSACTION_STATUSES = [
  'draft',
  'pending',
  'scheduled',
  'completed',
  'overdue',
  'cancelled',
] as const;

export type TransactionStatus = (typeof TRANSACTION_STATUSES)[number];

export const PAYMENT_METHODS = [
  'wire',
  'ach',
  'check',
  'credit_card',
  'cash',
  'internal_transfer',
  'other',
] as const;

export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

export const BUDGET_CATEGORIES = [
  'acquisition',
  'design',
  'architecture',
  'engineering',
  'permitting',
  'legal',
  'financing',
  'construction',
  'marketing',
  'sales',
  'leasing',
  'operations',
  'contingency',
  'taxes',
  'insurance',
  'other',
] as const;

export type BudgetCategory = (typeof BUDGET_CATEGORIES)[number];

export const COMMITMENT_TYPES = [
  'equity',
  'preferred_equity',
  'debt',
  'bridge_loan',
  'construction_loan',
  'mezzanine',
  'sponsor_equity',
  'other',
] as const;

export type CommitmentType = (typeof COMMITMENT_TYPES)[number];

export const COMMITMENT_STATUSES = [
  'proposed',
  'committed',
  'partially_funded',
  'fully_funded',
  'delayed',
  'cancelled',
] as const;

export type CommitmentStatus = (typeof COMMITMENT_STATUSES)[number];

export const OBLIGATION_TYPES = [
  'vendor_payment',
  'loan_payment',
  'investor_distribution',
  'tax',
  'insurance',
  'payroll',
  'utility',
  'professional_fee',
  'acquisition_payment',
  'other',
] as const;

export type ObligationType = (typeof OBLIGATION_TYPES)[number];

export const OBLIGATION_STATUSES = ['upcoming', 'due', 'overdue', 'paid', 'cancelled'] as const;

export type ObligationStatus = (typeof OBLIGATION_STATUSES)[number];

export const OBLIGATION_PRIORITIES = ['low', 'normal', 'high', 'critical'] as const;

export type ObligationPriority = (typeof OBLIGATION_PRIORITIES)[number];

export type CurrencyTotals = Record<string, string>;

export interface FinanceStats {
  total_cash: CurrencyTotals;
  available_cash: CurrencyTotals;
  pending_receivables: CurrencyTotals;
  upcoming_payments: CurrencyTotals;
  overdue_payments: CurrencyTotals;
  total_project_budget: CurrencyTotals;
  total_paid: CurrencyTotals;
  remaining_funding_need: CurrencyTotals;
}

export interface FinancialAccount {
  id: string;
  account_name: string;
  account_type: AccountType;
  institution_name: string | null;
  ownership_entity: string | null;
  currency: string;
  current_balance: string | null;
  available_balance: string | null;
  account_reference: string | null;
  status: AccountStatus;
  notes: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialAccountListResponse {
  items: FinancialAccount[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface FinancialAccountInput {
  account_name: string;
  account_type?: AccountType;
  institution_name?: string | null;
  ownership_entity?: string | null;
  currency?: string;
  current_balance?: number | null;
  available_balance?: number | null;
  account_reference?: string | null;
  status?: AccountStatus;
  notes?: string | null;
}

export interface AccountFilters {
  search?: string;
  account_type?: AccountType | '';
  status?: AccountStatus | '';
  currency?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface FinanceTransaction {
  id: string;
  transaction_date: string;
  transaction_type: TransactionType;
  category: string | null;
  amount: string;
  currency: string;
  description: string | null;
  account_id: string;
  project_id: string | null;
  investor_id: string | null;
  counterparty: string | null;
  reference_number: string | null;
  payment_method: PaymentMethod | null;
  status: TransactionStatus;
  due_date: string | null;
  paid_date: string | null;
  notes: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  project_name: string | null;
  investor_name: string | null;
  account_name: string | null;
}

export interface FinanceTransactionListResponse {
  items: FinanceTransaction[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface FinanceTransactionInput {
  transaction_date: string;
  transaction_type: TransactionType;
  category?: string | null;
  amount: number;
  currency?: string;
  description?: string | null;
  account_id: string;
  project_id?: string | null;
  investor_id?: string | null;
  counterparty?: string | null;
  reference_number?: string | null;
  payment_method?: PaymentMethod | null;
  status?: TransactionStatus;
  due_date?: string | null;
  paid_date?: string | null;
  notes?: string | null;
}

export interface TransactionFilters {
  search?: string;
  date_from?: string;
  date_to?: string;
  project_id?: string;
  investor_id?: string;
  account_id?: string;
  transaction_type?: TransactionType | '';
  status?: TransactionStatus | '';
  currency?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface ProjectBudget {
  id: string;
  project_id: string;
  budget_name: string;
  category: BudgetCategory;
  original_budget: string | null;
  revised_budget: string | null;
  committed_amount: string | null;
  paid_amount: string | null;
  forecast_amount: string | null;
  currency: string;
  notes: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  project_name: string | null;
  remaining: string | null;
  variance: string | null;
}

export interface ProjectBudgetListResponse {
  items: ProjectBudget[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface BudgetFilters {
  project_id?: string;
  category?: BudgetCategory | '';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface FundingCommitment {
  id: string;
  project_id: string;
  investor_id: string;
  commitment_type: CommitmentType;
  committed_amount: string;
  funded_amount: string | null;
  remaining_amount: string | null;
  currency: string;
  commitment_date: string | null;
  target_funding_date: string | null;
  actual_funding_date: string | null;
  status: CommitmentStatus;
  notes: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  project_name: string | null;
  investor_name: string | null;
}

export interface FundingCommitmentListResponse {
  items: FundingCommitment[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface FundingFilters {
  project_id?: string;
  investor_id?: string;
  status?: CommitmentStatus | '';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface PaymentObligation {
  id: string;
  project_id: string | null;
  investor_id: string | null;
  obligation_type: ObligationType;
  payee: string | null;
  description: string | null;
  amount: string;
  currency: string;
  due_date: string | null;
  paid_date: string | null;
  status: ObligationStatus;
  priority: ObligationPriority;
  notes: string | null;
  is_demo: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  project_name: string | null;
  investor_name: string | null;
}

export interface PaymentObligationListResponse {
  items: PaymentObligation[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ObligationFilters {
  project_id?: string;
  status?: ObligationStatus | '';
  priority?: ObligationPriority | '';
  due_date_from?: string;
  due_date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

function buildAccountQuery(filters: AccountFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set('search', filters.search.trim());
  if (filters.account_type) params.set('account_type', filters.account_type);
  if (filters.status) params.set('status', filters.status);
  if (filters.currency?.trim()) params.set('currency', filters.currency.trim());
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  const query = params.toString();
  return query ? `?${query}` : '';
}

function buildTransactionQuery(filters: TransactionFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set('search', filters.search.trim());
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  if (filters.project_id) params.set('project_id', filters.project_id);
  if (filters.investor_id) params.set('investor_id', filters.investor_id);
  if (filters.account_id) params.set('account_id', filters.account_id);
  if (filters.transaction_type) params.set('transaction_type', filters.transaction_type);
  if (filters.status) params.set('status', filters.status);
  if (filters.currency?.trim()) params.set('currency', filters.currency.trim());
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  const query = params.toString();
  return query ? `?${query}` : '';
}

function buildBudgetQuery(filters: BudgetFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.project_id) params.set('project_id', filters.project_id);
  if (filters.category) params.set('category', filters.category);
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  const query = params.toString();
  return query ? `?${query}` : '';
}

function buildFundingQuery(filters: FundingFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.project_id) params.set('project_id', filters.project_id);
  if (filters.investor_id) params.set('investor_id', filters.investor_id);
  if (filters.status) params.set('status', filters.status);
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  const query = params.toString();
  return query ? `?${query}` : '';
}

function buildObligationQuery(filters: ObligationFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.project_id) params.set('project_id', filters.project_id);
  if (filters.status) params.set('status', filters.status);
  if (filters.priority) params.set('priority', filters.priority);
  if (filters.due_date_from) params.set('due_date_from', filters.due_date_from);
  if (filters.due_date_to) params.set('due_date_to', filters.due_date_to);
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchFinanceStats(): Promise<FinanceStats> {
  return apiFetch<FinanceStats>('/finance/stats');
}

export async function fetchAccounts(
  filters: AccountFilters = {},
): Promise<FinancialAccountListResponse> {
  return apiFetch<FinancialAccountListResponse>(`/finance/accounts${buildAccountQuery(filters)}`);
}

export async function fetchAccount(id: string): Promise<FinancialAccount> {
  return apiFetch<FinancialAccount>(`/finance/accounts/${id}`);
}

export async function createAccount(input: FinancialAccountInput): Promise<FinancialAccount> {
  return apiFetch<FinancialAccount>('/finance/accounts', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateAccount(
  id: string,
  input: Partial<FinancialAccountInput>,
): Promise<FinancialAccount> {
  return apiFetch<FinancialAccount>(`/finance/accounts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function archiveAccount(id: string): Promise<FinancialAccount> {
  return apiFetch<FinancialAccount>(`/finance/accounts/${id}`, { method: 'DELETE' });
}

export async function fetchTransactions(
  filters: TransactionFilters = {},
): Promise<FinanceTransactionListResponse> {
  return apiFetch<FinanceTransactionListResponse>(
    `/finance/transactions${buildTransactionQuery(filters)}`,
  );
}

export async function fetchTransaction(id: string): Promise<FinanceTransaction> {
  return apiFetch<FinanceTransaction>(`/finance/transactions/${id}`);
}

export async function createTransaction(
  input: FinanceTransactionInput,
): Promise<FinanceTransaction> {
  return apiFetch<FinanceTransaction>('/finance/transactions', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateTransaction(
  id: string,
  input: Partial<FinanceTransactionInput>,
): Promise<FinanceTransaction> {
  return apiFetch<FinanceTransaction>(`/finance/transactions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function archiveTransaction(id: string): Promise<FinanceTransaction> {
  return apiFetch<FinanceTransaction>(`/finance/transactions/${id}`, { method: 'DELETE' });
}

export async function fetchProjectBudgets(
  filters: BudgetFilters = {},
): Promise<ProjectBudgetListResponse> {
  return apiFetch<ProjectBudgetListResponse>(
    `/finance/project-budgets${buildBudgetQuery(filters)}`,
  );
}

export async function fetchFundingCommitments(
  filters: FundingFilters = {},
): Promise<FundingCommitmentListResponse> {
  return apiFetch<FundingCommitmentListResponse>(
    `/finance/funding-commitments${buildFundingQuery(filters)}`,
  );
}

export async function fetchPaymentObligations(
  filters: ObligationFilters = {},
): Promise<PaymentObligationListResponse> {
  return apiFetch<PaymentObligationListResponse>(
    `/finance/payment-obligations${buildObligationQuery(filters)}`,
  );
}

export function formatMoney(
  amount: string | number | null | undefined,
  currency = 'USD',
  locale = 'tr',
): string {
  if (amount === null || amount === undefined || amount === '') {
    return '—';
  }

  const num = Number(amount);
  if (Number.isNaN(num)) {
    return String(amount);
  }

  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';

  return new Intl.NumberFormat(intlLocale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatCurrencyTotals(totals: CurrencyTotals, locale = 'tr'): string {
  const entries = Object.entries(totals).filter(([, value]) => {
    const num = Number(value);
    return !Number.isNaN(num) && num !== 0;
  });

  if (entries.length === 0) {
    return '—';
  }

  return entries
    .map(([currency, amount]) => formatMoney(amount, currency, locale))
    .join(' · ');
}

export function formatShortDate(value: string | null, locale = 'tr'): string {
  if (!value) {
    return '—';
  }

  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-GB';
  return new Intl.DateTimeFormat(intlLocale, { dateStyle: 'medium' }).format(new Date(value));
}
