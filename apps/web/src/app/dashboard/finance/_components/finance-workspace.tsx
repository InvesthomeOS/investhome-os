'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

import {
  archiveTransaction,
  createTransaction,
  updateTransaction,
  fetchAccounts,
  fetchFinanceStats,
  fetchFundingCommitments,
  fetchPaymentObligations,
  fetchProjectBudgets,
  fetchTransaction,
  fetchTransactions,
  formatCurrencyTotals,
  formatMoney,
  formatShortDate,
  type AccountFilters,
  type BudgetFilters,
  type FinanceStats,
  type FinanceTransaction,
  type FinanceTransactionInput,
  type FinancialAccount,
  type FundingCommitment,
  type FundingFilters,
  type ObligationFilters,
  type PaymentObligation,
  type ProjectBudget,
  type TransactionFilters,
} from '@/lib/api/finance';
import { fetchInvestors } from '@/lib/api/investors';
import { fetchProjects } from '@/lib/api/projects';
import { useFinanceLabels } from '@/lib/i18n/finance-labels';

import { TransactionDetailDrawer } from './transaction-detail-drawer';
import { TransactionFormModal } from './transaction-form-modal';

type FinanceTab = 'overview' | 'accounts' | 'transactions' | 'budgets' | 'funding' | 'payments';
type TransactionFormMode = 'create' | 'edit' | null;

const PAGE_SIZE = 20;

const EMPTY_ACCOUNT_FILTERS: AccountFilters = {
  search: '',
  account_type: '',
  status: '',
  currency: '',
  sort_by: 'updated_at',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

const EMPTY_TRANSACTION_FILTERS: TransactionFilters = {
  search: '',
  date_from: '',
  date_to: '',
  project_id: '',
  investor_id: '',
  account_id: '',
  transaction_type: '',
  status: '',
  currency: '',
  sort_by: 'transaction_date',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

const EMPTY_BUDGET_FILTERS: BudgetFilters = {
  project_id: '',
  category: '',
  sort_by: 'updated_at',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

const EMPTY_FUNDING_FILTERS: FundingFilters = {
  project_id: '',
  investor_id: '',
  status: '',
  sort_by: 'updated_at',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

const EMPTY_OBLIGATION_FILTERS: ObligationFilters = {
  project_id: '',
  status: '',
  priority: '',
  due_date_from: '',
  due_date_to: '',
  sort_by: 'due_date',
  sort_order: 'asc',
  page: 1,
  page_size: 100,
};

function PaginationBar({
  page,
  pages,
  total,
  onPageChange,
}: {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  const t = useTranslations('finance');

  if (pages <= 1) {
    return null;
  }

  return (
    <div className="investors__pagination">
      <span>{t('pagination', { page, pages, total })}</span>
      <div className="investors__pagination-actions">
        <button
          type="button"
          className="leads__button leads__button--ghost"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          {t('prevPage')}
        </button>
        <button
          type="button"
          className="leads__button leads__button--ghost"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          {t('nextPage')}
        </button>
      </div>
    </div>
  );
}

export function FinanceWorkspace() {
  const t = useTranslations('finance');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const {
    getAccountTypeLabel,
    getAccountStatusLabel,
    getTransactionTypeLabel,
    getTransactionStatusLabel,
    getBudgetCategoryLabel,
    getCommitmentTypeLabel,
    getCommitmentStatusLabel,
    getObligationTypeLabel,
    getObligationStatusLabel,
    getObligationPriorityLabel,
    accountTypeOptions,
    accountStatusOptions,
    transactionTypeOptions,
    transactionStatusOptions,
    budgetCategoryOptions,
    commitmentStatusOptions,
    obligationStatusOptions,
    obligationPriorityOptions,
  } = useFinanceLabels();

  const [activeTab, setActiveTab] = useState<FinanceTab>('overview');
  const [stats, setStats] = useState<FinanceStats | null>(null);

  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [accountTotal, setAccountTotal] = useState(0);
  const [accountPages, setAccountPages] = useState(0);
  const [accountFilters, setAccountFilters] = useState<AccountFilters>(EMPTY_ACCOUNT_FILTERS);
  const [appliedAccountFilters, setAppliedAccountFilters] =
    useState<AccountFilters>(EMPTY_ACCOUNT_FILTERS);

  const [transactions, setTransactions] = useState<FinanceTransaction[]>([]);
  const [transactionTotal, setTransactionTotal] = useState(0);
  const [transactionPages, setTransactionPages] = useState(0);
  const [transactionFilters, setTransactionFilters] =
    useState<TransactionFilters>(EMPTY_TRANSACTION_FILTERS);
  const [appliedTransactionFilters, setAppliedTransactionFilters] =
    useState<TransactionFilters>(EMPTY_TRANSACTION_FILTERS);

  const [budgets, setBudgets] = useState<ProjectBudget[]>([]);
  const [budgetTotal, setBudgetTotal] = useState(0);
  const [budgetPages, setBudgetPages] = useState(0);
  const [budgetFilters, setBudgetFilters] = useState<BudgetFilters>(EMPTY_BUDGET_FILTERS);
  const [appliedBudgetFilters, setAppliedBudgetFilters] =
    useState<BudgetFilters>(EMPTY_BUDGET_FILTERS);

  const [commitments, setCommitments] = useState<FundingCommitment[]>([]);
  const [fundingTotal, setFundingTotal] = useState(0);
  const [fundingPages, setFundingPages] = useState(0);
  const [fundingFilters, setFundingFilters] = useState<FundingFilters>(EMPTY_FUNDING_FILTERS);
  const [appliedFundingFilters, setAppliedFundingFilters] =
    useState<FundingFilters>(EMPTY_FUNDING_FILTERS);

  const [obligations, setObligations] = useState<PaymentObligation[]>([]);
  const [obligationFilters, setObligationFilters] =
    useState<ObligationFilters>(EMPTY_OBLIGATION_FILTERS);
  const [appliedObligationFilters, setAppliedObligationFilters] =
    useState<ObligationFilters>(EMPTY_OBLIGATION_FILTERS);

  const [allAccounts, setAllAccounts] = useState<FinancialAccount[]>([]);
  const [projectOptions, setProjectOptions] = useState<{ id: string; label: string }[]>([]);
  const [investorOptions, setInvestorOptions] = useState<{ id: string; label: string }[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<FinanceTransaction | null>(null);
  const [transactionFormMode, setTransactionFormMode] = useState<TransactionFormMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const response = await fetchFinanceStats();
      setStats(response);
    } catch {
      setStats(null);
    }
  }, []);

  const loadReferenceData = useCallback(async () => {
    try {
      const [accountsResponse, projectsResponse, investorsResponse] = await Promise.all([
        fetchAccounts({ page: 1, page_size: 100, sort_by: 'account_name', sort_order: 'asc' }),
        fetchProjects({ page: 1, page_size: 100, sort_by: 'project_name', sort_order: 'asc' }),
        fetchInvestors({ page: 1, page_size: 100, sort_by: 'full_name', sort_order: 'asc' }),
      ]);
      setAllAccounts(accountsResponse.items);
      setProjectOptions(
        projectsResponse.items.map((project) => ({
          id: project.id,
          label: project.project_name,
        })),
      );
      setInvestorOptions(
        investorsResponse.items.map((investor) => ({
          id: investor.id,
          label: investor.full_name,
        })),
      );
    } catch {
      setAllAccounts([]);
      setProjectOptions([]);
      setInvestorOptions([]);
    }
  }, []);

  const loadAccounts = useCallback(
    async (nextFilters: AccountFilters) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchAccounts(nextFilters);
        setAccounts(response.items);
        setAccountTotal(response.total);
        setAccountPages(response.pages);
      } catch {
        setError(t('loadError'));
        setAccounts([]);
        setAccountTotal(0);
        setAccountPages(0);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  const loadTransactions = useCallback(
    async (nextFilters: TransactionFilters) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchTransactions(nextFilters);
        setTransactions(response.items);
        setTransactionTotal(response.total);
        setTransactionPages(response.pages);
      } catch {
        setError(t('loadError'));
        setTransactions([]);
        setTransactionTotal(0);
        setTransactionPages(0);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  const loadBudgets = useCallback(
    async (nextFilters: BudgetFilters) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchProjectBudgets(nextFilters);
        setBudgets(response.items);
        setBudgetTotal(response.total);
        setBudgetPages(response.pages);
      } catch {
        setError(t('loadError'));
        setBudgets([]);
        setBudgetTotal(0);
        setBudgetPages(0);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  const loadFunding = useCallback(
    async (nextFilters: FundingFilters) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchFundingCommitments(nextFilters);
        setCommitments(response.items);
        setFundingTotal(response.total);
        setFundingPages(response.pages);
      } catch {
        setError(t('loadError'));
        setCommitments([]);
        setFundingTotal(0);
        setFundingPages(0);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  const loadObligations = useCallback(
    async (nextFilters: ObligationFilters) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchPaymentObligations(nextFilters);
        setObligations(response.items);
      } catch {
        setError(t('loadError'));
        setObligations([]);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  useEffect(() => {
    void loadStats();
    void loadReferenceData();
  }, [loadReferenceData, loadStats]);

  const pathname = usePathname();
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    const recordId = params.get('id');
    const validTabs: FinanceTab[] = [
      'overview',
      'accounts',
      'transactions',
      'budgets',
      'funding',
      'payments',
    ];
    if (tab && validTabs.includes(tab as FinanceTab)) {
      setActiveTab(tab as FinanceTab);
    }
    if (recordId && tab === 'transactions') {
      void fetchTransaction(recordId).then(setSelectedTransaction).catch(() => undefined);
    }
  }, [pathname]);

  useEffect(() => {
    if (activeTab === 'overview') {
      setLoading(false);
      setError(null);
      void loadTransactions({ ...EMPTY_TRANSACTION_FILTERS, page: 1, page_size: 10 });
      return;
    }
    if (activeTab === 'accounts') {
      void loadAccounts(appliedAccountFilters);
      return;
    }
    if (activeTab === 'transactions') {
      void loadTransactions(appliedTransactionFilters);
      return;
    }
    if (activeTab === 'budgets') {
      void loadBudgets(appliedBudgetFilters);
      return;
    }
    if (activeTab === 'funding') {
      void loadFunding(appliedFundingFilters);
      return;
    }
    if (activeTab === 'payments') {
      void loadObligations(appliedObligationFilters);
    }
  }, [
    activeTab,
    appliedAccountFilters,
    appliedBudgetFilters,
    appliedFundingFilters,
    appliedObligationFilters,
    appliedTransactionFilters,
    loadAccounts,
    loadBudgets,
    loadFunding,
    loadObligations,
    loadTransactions,
  ]);

  const demoCount = useMemo(() => {
    if (activeTab === 'accounts') return accounts.filter((item) => item.is_demo).length;
    if (activeTab === 'transactions') return transactions.filter((item) => item.is_demo).length;
    if (activeTab === 'budgets') return budgets.filter((item) => item.is_demo).length;
    if (activeTab === 'funding') return commitments.filter((item) => item.is_demo).length;
    if (activeTab === 'payments') return obligations.filter((item) => item.is_demo).length;
    return 0;
  }, [accounts, activeTab, budgets, commitments, obligations, transactions]);

  const criticalObligations = useMemo(
    () =>
      obligations.filter(
        (item) =>
          item.priority === 'critical' && item.status !== 'paid' && item.status !== 'cancelled',
      ),
    [obligations],
  );

  const overdueObligations = useMemo(
    () => obligations.filter((item) => item.status === 'overdue'),
    [obligations],
  );

  const upcomingObligations = useMemo(
    () => obligations.filter((item) => item.status === 'upcoming' || item.status === 'due'),
    [obligations],
  );

  const paidObligations = useMemo(
    () => obligations.filter((item) => item.status === 'paid'),
    [obligations],
  );

  const handleSubmitTransaction = async (input: FinanceTransactionInput) => {
    setSubmitting(true);
    setActionError(null);
    try {
      if (transactionFormMode === 'create') {
        await createTransaction(input);
      } else if (transactionFormMode === 'edit' && selectedTransaction) {
        await updateTransaction(selectedTransaction.id, input);
      }
      setTransactionFormMode(null);
      await Promise.all([
        loadStats(),
        loadTransactions(appliedTransactionFilters),
        activeTab === 'overview'
          ? loadTransactions({ ...EMPTY_TRANSACTION_FILTERS, page: 1, page_size: 10 })
          : Promise.resolve(),
      ]);
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchiveTransaction = async (transaction: FinanceTransaction) => {
    setSubmitting(true);
    setActionError(null);
    try {
      await archiveTransaction(transaction.id);
      setSelectedTransaction(null);
      await Promise.all([loadStats(), loadTransactions(appliedTransactionFilters)]);
    } catch {
      setActionError(t('archiveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const tabs: { id: FinanceTab; label: string }[] = [
    { id: 'overview', label: t('tabs.overview') },
    { id: 'accounts', label: t('tabs.accounts') },
    { id: 'transactions', label: t('tabs.transactions') },
    { id: 'budgets', label: t('tabs.budgets') },
    { id: 'funding', label: t('tabs.funding') },
    { id: 'payments', label: t('tabs.payments') },
  ];

  const renderObligationTable = (items: PaymentObligation[], emptyKey: string) => {
    if (items.length === 0) {
      return <p className="leads__state">{t(emptyKey)}</p>;
    }

    return (
      <div className="leads__table-wrap">
        <table className="leads__table">
          <thead>
            <tr>
              <th>{t('paymentsTable.dueDate')}</th>
              <th>{t('paymentsTable.payee')}</th>
              <th>{t('paymentsTable.description')}</th>
              <th>{t('paymentsTable.project')}</th>
              <th>{t('paymentsTable.type')}</th>
              <th>{t('paymentsTable.amount')}</th>
              <th>{t('paymentsTable.priority')}</th>
              <th>{t('paymentsTable.status')}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="leads__row">
                <td>{formatShortDate(item.due_date, locale)}</td>
                <td>{item.payee ?? tCommon('noValue')}</td>
                <td>{item.description ?? tCommon('noValue')}</td>
                <td>{item.project_name ?? tCommon('noValue')}</td>
                <td>{getObligationTypeLabel(item.obligation_type)}</td>
                <td>{formatMoney(item.amount, item.currency, locale)}</td>
                <td>{getObligationPriorityLabel(item.priority)}</td>
                <td>{getObligationStatusLabel(item.status)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <main className="dashboard leads investors finance">
      <header className="dashboard__header leads__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="leads__subtitle">{t('subtitle')}</p>
      </header>

      {stats && (
        <section className="finance__stats">
          <article className="investors__stat-card">
            <p>{t('stats.totalCash')}</p>
            <strong>{formatCurrencyTotals(stats.total_cash, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.availableCash')}</p>
            <strong>{formatCurrencyTotals(stats.available_cash, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.pendingReceivables')}</p>
            <strong>{formatCurrencyTotals(stats.pending_receivables, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.upcomingPayments')}</p>
            <strong>{formatCurrencyTotals(stats.upcoming_payments, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.overduePayments')}</p>
            <strong>{formatCurrencyTotals(stats.overdue_payments, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.totalProjectBudget')}</p>
            <strong>{formatCurrencyTotals(stats.total_project_budget, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.totalPaid')}</p>
            <strong>{formatCurrencyTotals(stats.total_paid, locale)}</strong>
          </article>
          <article className="investors__stat-card">
            <p>{t('stats.remainingFundingNeed')}</p>
            <strong>{formatCurrencyTotals(stats.remaining_funding_need, locale)}</strong>
          </article>
        </section>
      )}

      {demoCount > 0 && (
        <div className="leads__demo-banner" role="status">
          {t('demoBanner', { count: demoCount })}
        </div>
      )}

      <nav className="finance__tabs" aria-label={t('tabsLabel')}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`finance__tab${activeTab === tab.id ? ' finance__tab--active' : ''}`}
            aria-current={activeTab === tab.id ? 'page' : undefined}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Overview tab */}
      {activeTab === 'overview' && (
        <section className="dashboard__panel leads__panel">
          <h2 className="leads-form__section-title">{t('overview.recentTransactions')}</h2>
          {loading && <p className="leads__state">{t('loading')}</p>}
          {error && <p className="leads__state leads__state--error">{error}</p>}
          {!loading && !error && transactions.length === 0 && (
            <p className="leads__state">{t('emptyState')}</p>
          )}
          {!loading && !error && transactions.length > 0 && (
            <div className="leads__table-wrap">
              <table className="leads__table">
                <thead>
                  <tr>
                    <th>{t('table.date')}</th>
                    <th>{t('table.type')}</th>
                    <th>{t('table.description')}</th>
                    <th>{t('table.project')}</th>
                    <th>{t('table.amount')}</th>
                    <th>{t('table.status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((item) => (
                    <tr
                      key={item.id}
                      className="leads__row"
                      tabIndex={0}
                      onClick={() => setSelectedTransaction(item)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          setSelectedTransaction(item);
                        }
                      }}
                    >
                      <td>{formatShortDate(item.transaction_date, locale)}</td>
                      <td>{getTransactionTypeLabel(item.transaction_type)}</td>
                      <td>{item.description ?? tCommon('noValue')}</td>
                      <td>{item.project_name ?? tCommon('noValue')}</td>
                      <td>{formatMoney(item.amount, item.currency, locale)}</td>
                      <td>{getTransactionStatusLabel(item.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Accounts tab */}
      {activeTab === 'accounts' && (
        <section className="dashboard__panel leads__panel">
          <div className="leads__toolbar">
            <div className="leads__filters">
              <label className="leads__field">
                <span>{t('searchLabel')}</span>
                <input
                  type="search"
                  value={accountFilters.search ?? ''}
                  placeholder={t('accountsSearchPlaceholder')}
                  onChange={(event) =>
                    setAccountFilters((current) => ({ ...current, search: event.target.value }))
                  }
                />
              </label>
              <label className="leads__field">
                <span>{t('accountTypeLabel')}</span>
                <select
                  value={accountFilters.account_type ?? ''}
                  onChange={(event) =>
                    setAccountFilters((current) => ({
                      ...current,
                      account_type: event.target.value as AccountFilters['account_type'],
                    }))
                  }
                >
                  <option value="">{t('allAccountTypes')}</option>
                  {accountTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('statusLabel')}</span>
                <select
                  value={accountFilters.status ?? ''}
                  onChange={(event) =>
                    setAccountFilters((current) => ({
                      ...current,
                      status: event.target.value as AccountFilters['status'],
                    }))
                  }
                >
                  <option value="">{t('allStatuses')}</option>
                  {accountStatusOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('currencyLabel')}</span>
                <input
                  value={accountFilters.currency ?? ''}
                  placeholder={t('currencyPlaceholder')}
                  onChange={(event) =>
                    setAccountFilters((current) => ({ ...current, currency: event.target.value }))
                  }
                />
              </label>
              <div className="leads__filter-actions">
                <button
                  type="button"
                  className="leads__button leads__button--secondary"
                  onClick={() => setAppliedAccountFilters({ ...accountFilters, page: 1 })}
                >
                  {tCommon('apply')}
                </button>
                <button
                  type="button"
                  className="leads__button leads__button--ghost"
                  onClick={() => {
                    setAccountFilters(EMPTY_ACCOUNT_FILTERS);
                    setAppliedAccountFilters(EMPTY_ACCOUNT_FILTERS);
                  }}
                >
                  {tCommon('reset')}
                </button>
              </div>
            </div>
          </div>

          {loading && <p className="leads__state">{t('loading')}</p>}
          {error && <p className="leads__state leads__state--error">{error}</p>}
          {!loading && !error && accounts.length === 0 && (
            <p className="leads__state">{t('emptyState')}</p>
          )}
          {!loading && !error && accounts.length > 0 && (
            <>
              <div className="leads__table-wrap">
                <table className="leads__table">
                  <thead>
                    <tr>
                      <th>{t('accountsTable.name')}</th>
                      <th>{t('accountsTable.type')}</th>
                      <th>{t('accountsTable.institution')}</th>
                      <th>{t('accountsTable.currency')}</th>
                      <th>{t('accountsTable.currentBalance')}</th>
                      <th>{t('accountsTable.availableBalance')}</th>
                      <th>{t('accountsTable.status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((item) => (
                      <tr key={item.id} className="leads__row">
                        <td className="leads__name">
                          {item.account_name}
                          {item.is_demo && (
                            <span className="leads__demo-tag">{tCommon('demoData')}</span>
                          )}
                        </td>
                        <td>{getAccountTypeLabel(item.account_type)}</td>
                        <td>{item.institution_name ?? tCommon('noValue')}</td>
                        <td>{item.currency}</td>
                        <td>{formatMoney(item.current_balance, item.currency, locale)}</td>
                        <td>{formatMoney(item.available_balance, item.currency, locale)}</td>
                        <td>{getAccountStatusLabel(item.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <PaginationBar
                page={appliedAccountFilters.page ?? 1}
                pages={accountPages}
                total={accountTotal}
                onPageChange={(page) =>
                  setAppliedAccountFilters((current) => ({ ...current, page }))
                }
              />
            </>
          )}
        </section>
      )}

      {/* Transactions tab */}
      {activeTab === 'transactions' && (
        <section className="dashboard__panel leads__panel">
          <div className="leads__toolbar">
            <div className="leads__filters">
              <label className="leads__field">
                <span>{t('dateFromLabel')}</span>
                <input
                  type="date"
                  value={transactionFilters.date_from ?? ''}
                  onChange={(event) =>
                    setTransactionFilters((current) => ({
                      ...current,
                      date_from: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="leads__field">
                <span>{t('dateToLabel')}</span>
                <input
                  type="date"
                  value={transactionFilters.date_to ?? ''}
                  onChange={(event) =>
                    setTransactionFilters((current) => ({
                      ...current,
                      date_to: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="leads__field">
                <span>{t('projectLabel')}</span>
                <select
                  value={transactionFilters.project_id ?? ''}
                  onChange={(event) =>
                    setTransactionFilters((current) => ({
                      ...current,
                      project_id: event.target.value,
                    }))
                  }
                >
                  <option value="">{t('allProjects')}</option>
                  {projectOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('investorLabel')}</span>
                <select
                  value={transactionFilters.investor_id ?? ''}
                  onChange={(event) =>
                    setTransactionFilters((current) => ({
                      ...current,
                      investor_id: event.target.value,
                    }))
                  }
                >
                  <option value="">{t('allInvestors')}</option>
                  {investorOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('accountLabel')}</span>
                <select
                  value={transactionFilters.account_id ?? ''}
                  onChange={(event) =>
                    setTransactionFilters((current) => ({
                      ...current,
                      account_id: event.target.value,
                    }))
                  }
                >
                  <option value="">{t('allAccounts')}</option>
                  {allAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.account_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('transactionTypeLabel')}</span>
                <select
                  value={transactionFilters.transaction_type ?? ''}
                  onChange={(event) =>
                    setTransactionFilters((current) => ({
                      ...current,
                      transaction_type: event.target.value as TransactionFilters['transaction_type'],
                    }))
                  }
                >
                  <option value="">{t('allTransactionTypes')}</option>
                  {transactionTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('statusLabel')}</span>
                <select
                  value={transactionFilters.status ?? ''}
                  onChange={(event) =>
                    setTransactionFilters((current) => ({
                      ...current,
                      status: event.target.value as TransactionFilters['status'],
                    }))
                  }
                >
                  <option value="">{t('allStatuses')}</option>
                  {transactionStatusOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('currencyLabel')}</span>
                <input
                  value={transactionFilters.currency ?? ''}
                  placeholder={t('currencyPlaceholder')}
                  onChange={(event) =>
                    setTransactionFilters((current) => ({
                      ...current,
                      currency: event.target.value,
                    }))
                  }
                />
              </label>
              <div className="leads__filter-actions">
                <button
                  type="button"
                  className="leads__button leads__button--secondary"
                  onClick={() => setAppliedTransactionFilters({ ...transactionFilters, page: 1 })}
                >
                  {tCommon('apply')}
                </button>
                <button
                  type="button"
                  className="leads__button leads__button--ghost"
                  onClick={() => {
                    setTransactionFilters(EMPTY_TRANSACTION_FILTERS);
                    setAppliedTransactionFilters(EMPTY_TRANSACTION_FILTERS);
                  }}
                >
                  {tCommon('reset')}
                </button>
                <button
                  type="button"
                  className="leads__button leads__button--primary"
                  onClick={() => {
                    setActionError(null);
                    setTransactionFormMode('create');
                  }}
                >
                  {t('addTransaction')}
                </button>
              </div>
            </div>
          </div>

          {loading && <p className="leads__state">{t('loading')}</p>}
          {error && <p className="leads__state leads__state--error">{error}</p>}
          {!loading && !error && transactions.length === 0 && (
            <p className="leads__state">{t('emptyState')}</p>
          )}
          {!loading && !error && transactions.length > 0 && (
            <>
              <div className="leads__table-wrap">
                <table className="leads__table">
                  <thead>
                    <tr>
                      <th>{t('table.date')}</th>
                      <th>{t('table.type')}</th>
                      <th>{t('table.category')}</th>
                      <th>{t('table.description')}</th>
                      <th>{t('table.project')}</th>
                      <th>{t('table.investor')}</th>
                      <th>{t('table.account')}</th>
                      <th>{t('table.amount')}</th>
                      <th>{t('table.status')}</th>
                      <th>{t('table.dueDate')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((item) => (
                      <tr
                        key={item.id}
                        className="leads__row"
                        tabIndex={0}
                        onClick={() => setSelectedTransaction(item)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            setSelectedTransaction(item);
                          }
                        }}
                      >
                        <td>{formatShortDate(item.transaction_date, locale)}</td>
                        <td>{getTransactionTypeLabel(item.transaction_type)}</td>
                        <td>{item.category ?? tCommon('noValue')}</td>
                        <td>{item.description ?? tCommon('noValue')}</td>
                        <td>{item.project_name ?? tCommon('noValue')}</td>
                        <td>{item.investor_name ?? tCommon('noValue')}</td>
                        <td>{item.account_name ?? tCommon('noValue')}</td>
                        <td>{formatMoney(item.amount, item.currency, locale)}</td>
                        <td>{getTransactionStatusLabel(item.status)}</td>
                        <td>{formatShortDate(item.due_date, locale)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <PaginationBar
                page={appliedTransactionFilters.page ?? 1}
                pages={transactionPages}
                total={transactionTotal}
                onPageChange={(page) =>
                  setAppliedTransactionFilters((current) => ({ ...current, page }))
                }
              />
            </>
          )}
        </section>
      )}

      {/* Budgets tab */}
      {activeTab === 'budgets' && (
        <section className="dashboard__panel leads__panel">
          <div className="leads__toolbar">
            <div className="leads__filters">
              <label className="leads__field">
                <span>{t('projectLabel')}</span>
                <select
                  value={budgetFilters.project_id ?? ''}
                  onChange={(event) =>
                    setBudgetFilters((current) => ({
                      ...current,
                      project_id: event.target.value,
                    }))
                  }
                >
                  <option value="">{t('allProjects')}</option>
                  {projectOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('categoryLabel')}</span>
                <select
                  value={budgetFilters.category ?? ''}
                  onChange={(event) =>
                    setBudgetFilters((current) => ({
                      ...current,
                      category: event.target.value as BudgetFilters['category'],
                    }))
                  }
                >
                  <option value="">{t('allCategories')}</option>
                  {budgetCategoryOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="leads__filter-actions">
                <button
                  type="button"
                  className="leads__button leads__button--secondary"
                  onClick={() => setAppliedBudgetFilters({ ...budgetFilters, page: 1 })}
                >
                  {tCommon('apply')}
                </button>
                <button
                  type="button"
                  className="leads__button leads__button--ghost"
                  onClick={() => {
                    setBudgetFilters(EMPTY_BUDGET_FILTERS);
                    setAppliedBudgetFilters(EMPTY_BUDGET_FILTERS);
                  }}
                >
                  {tCommon('reset')}
                </button>
              </div>
            </div>
          </div>

          {loading && <p className="leads__state">{t('loading')}</p>}
          {error && <p className="leads__state leads__state--error">{error}</p>}
          {!loading && !error && budgets.length === 0 && (
            <p className="leads__state">{t('emptyState')}</p>
          )}
          {!loading && !error && budgets.length > 0 && (
            <>
              <div className="leads__table-wrap">
                <table className="leads__table">
                  <thead>
                    <tr>
                      <th>{t('budgetsTable.project')}</th>
                      <th>{t('budgetsTable.name')}</th>
                      <th>{t('budgetsTable.category')}</th>
                      <th>{t('budgetsTable.original')}</th>
                      <th>{t('budgetsTable.revised')}</th>
                      <th>{t('budgetsTable.committed')}</th>
                      <th>{t('budgetsTable.paid')}</th>
                      <th>{t('budgetsTable.forecast')}</th>
                      <th>{t('budgetsTable.remaining')}</th>
                      <th>{t('budgetsTable.variance')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {budgets.map((item) => (
                      <tr key={item.id} className="leads__row">
                        <td>{item.project_name ?? tCommon('noValue')}</td>
                        <td>{item.budget_name}</td>
                        <td>{getBudgetCategoryLabel(item.category)}</td>
                        <td>{formatMoney(item.original_budget, item.currency, locale)}</td>
                        <td>{formatMoney(item.revised_budget, item.currency, locale)}</td>
                        <td>{formatMoney(item.committed_amount, item.currency, locale)}</td>
                        <td>{formatMoney(item.paid_amount, item.currency, locale)}</td>
                        <td>{formatMoney(item.forecast_amount, item.currency, locale)}</td>
                        <td>{formatMoney(item.remaining, item.currency, locale)}</td>
                        <td>{formatMoney(item.variance, item.currency, locale)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <PaginationBar
                page={appliedBudgetFilters.page ?? 1}
                pages={budgetPages}
                total={budgetTotal}
                onPageChange={(page) =>
                  setAppliedBudgetFilters((current) => ({ ...current, page }))
                }
              />
            </>
          )}
        </section>
      )}

      {/* Funding tab */}
      {activeTab === 'funding' && (
        <section className="dashboard__panel leads__panel">
          <div className="leads__toolbar">
            <div className="leads__filters">
              <label className="leads__field">
                <span>{t('projectLabel')}</span>
                <select
                  value={fundingFilters.project_id ?? ''}
                  onChange={(event) =>
                    setFundingFilters((current) => ({
                      ...current,
                      project_id: event.target.value,
                    }))
                  }
                >
                  <option value="">{t('allProjects')}</option>
                  {projectOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('investorLabel')}</span>
                <select
                  value={fundingFilters.investor_id ?? ''}
                  onChange={(event) =>
                    setFundingFilters((current) => ({
                      ...current,
                      investor_id: event.target.value,
                    }))
                  }
                >
                  <option value="">{t('allInvestors')}</option>
                  {investorOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('statusLabel')}</span>
                <select
                  value={fundingFilters.status ?? ''}
                  onChange={(event) =>
                    setFundingFilters((current) => ({
                      ...current,
                      status: event.target.value as FundingFilters['status'],
                    }))
                  }
                >
                  <option value="">{t('allStatuses')}</option>
                  {commitmentStatusOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="leads__filter-actions">
                <button
                  type="button"
                  className="leads__button leads__button--secondary"
                  onClick={() => setAppliedFundingFilters({ ...fundingFilters, page: 1 })}
                >
                  {tCommon('apply')}
                </button>
                <button
                  type="button"
                  className="leads__button leads__button--ghost"
                  onClick={() => {
                    setFundingFilters(EMPTY_FUNDING_FILTERS);
                    setAppliedFundingFilters(EMPTY_FUNDING_FILTERS);
                  }}
                >
                  {tCommon('reset')}
                </button>
              </div>
            </div>
          </div>

          {loading && <p className="leads__state">{t('loading')}</p>}
          {error && <p className="leads__state leads__state--error">{error}</p>}
          {!loading && !error && commitments.length === 0 && (
            <p className="leads__state">{t('emptyState')}</p>
          )}
          {!loading && !error && commitments.length > 0 && (
            <>
              <div className="leads__table-wrap">
                <table className="leads__table">
                  <thead>
                    <tr>
                      <th>{t('fundingTable.investor')}</th>
                      <th>{t('fundingTable.project')}</th>
                      <th>{t('fundingTable.type')}</th>
                      <th>{t('fundingTable.committed')}</th>
                      <th>{t('fundingTable.funded')}</th>
                      <th>{t('fundingTable.remaining')}</th>
                      <th>{t('fundingTable.targetDate')}</th>
                      <th>{t('fundingTable.status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commitments.map((item) => (
                      <tr key={item.id} className="leads__row">
                        <td>{item.investor_name ?? tCommon('noValue')}</td>
                        <td>{item.project_name ?? tCommon('noValue')}</td>
                        <td>{getCommitmentTypeLabel(item.commitment_type)}</td>
                        <td>{formatMoney(item.committed_amount, item.currency, locale)}</td>
                        <td>{formatMoney(item.funded_amount, item.currency, locale)}</td>
                        <td>{formatMoney(item.remaining_amount, item.currency, locale)}</td>
                        <td>{formatShortDate(item.target_funding_date, locale)}</td>
                        <td>{getCommitmentStatusLabel(item.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <PaginationBar
                page={appliedFundingFilters.page ?? 1}
                pages={fundingPages}
                total={fundingTotal}
                onPageChange={(page) =>
                  setAppliedFundingFilters((current) => ({ ...current, page }))
                }
              />
            </>
          )}
        </section>
      )}

      {/* Payments tab */}
      {activeTab === 'payments' && (
        <section className="dashboard__panel leads__panel">
          <div className="leads__toolbar">
            <div className="leads__filters">
              <label className="leads__field">
                <span>{t('projectLabel')}</span>
                <select
                  value={obligationFilters.project_id ?? ''}
                  onChange={(event) =>
                    setObligationFilters((current) => ({
                      ...current,
                      project_id: event.target.value,
                    }))
                  }
                >
                  <option value="">{t('allProjects')}</option>
                  {projectOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('statusLabel')}</span>
                <select
                  value={obligationFilters.status ?? ''}
                  onChange={(event) =>
                    setObligationFilters((current) => ({
                      ...current,
                      status: event.target.value as ObligationFilters['status'],
                    }))
                  }
                >
                  <option value="">{t('allStatuses')}</option>
                  {obligationStatusOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('priorityLabel')}</span>
                <select
                  value={obligationFilters.priority ?? ''}
                  onChange={(event) =>
                    setObligationFilters((current) => ({
                      ...current,
                      priority: event.target.value as ObligationFilters['priority'],
                    }))
                  }
                >
                  <option value="">{t('allPriorities')}</option>
                  {obligationPriorityOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('dateFromLabel')}</span>
                <input
                  type="date"
                  value={obligationFilters.due_date_from ?? ''}
                  onChange={(event) =>
                    setObligationFilters((current) => ({
                      ...current,
                      due_date_from: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="leads__field">
                <span>{t('dateToLabel')}</span>
                <input
                  type="date"
                  value={obligationFilters.due_date_to ?? ''}
                  onChange={(event) =>
                    setObligationFilters((current) => ({
                      ...current,
                      due_date_to: event.target.value,
                    }))
                  }
                />
              </label>
              <div className="leads__filter-actions">
                <button
                  type="button"
                  className="leads__button leads__button--secondary"
                  onClick={() => setAppliedObligationFilters({ ...obligationFilters, page: 1 })}
                >
                  {tCommon('apply')}
                </button>
                <button
                  type="button"
                  className="leads__button leads__button--ghost"
                  onClick={() => {
                    setObligationFilters(EMPTY_OBLIGATION_FILTERS);
                    setAppliedObligationFilters(EMPTY_OBLIGATION_FILTERS);
                  }}
                >
                  {tCommon('reset')}
                </button>
              </div>
            </div>
          </div>

          {loading && <p className="leads__state">{t('loading')}</p>}
          {error && <p className="leads__state leads__state--error">{error}</p>}

          {!loading && !error && (
            <>
              <section className="leads-drawer__section">
                <h3>{t('paymentsSections.critical')}</h3>
                {renderObligationTable(criticalObligations, 'paymentsEmpty.critical')}
              </section>
              <section className="leads-drawer__section">
                <h3>{t('paymentsSections.overdue')}</h3>
                {renderObligationTable(overdueObligations, 'paymentsEmpty.overdue')}
              </section>
              <section className="leads-drawer__section">
                <h3>{t('paymentsSections.upcoming')}</h3>
                {renderObligationTable(upcomingObligations, 'paymentsEmpty.upcoming')}
              </section>
              <section className="leads-drawer__section">
                <h3>{t('paymentsSections.paid')}</h3>
                {renderObligationTable(paidObligations, 'paymentsEmpty.paid')}
              </section>
            </>
          )}
        </section>
      )}

      {actionError && <p className="leads__error">{actionError}</p>}

      <TransactionFormModal
        mode={transactionFormMode}
        transaction={selectedTransaction}
        accounts={allAccounts}
        projectOptions={projectOptions}
        investorOptions={investorOptions}
        submitting={submitting}
        error={actionError}
        onClose={() => setTransactionFormMode(null)}
        onSubmit={handleSubmitTransaction}
      />

      <TransactionDetailDrawer
        transaction={selectedTransaction}
        archiving={submitting}
        onClose={() => setSelectedTransaction(null)}
        onEdit={(transaction) => {
          setSelectedTransaction(transaction);
          setTransactionFormMode('edit');
        }}
        onArchive={handleArchiveTransaction}
      />
    </main>
  );
}
