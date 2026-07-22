'use client';

import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { ContextualAiActions } from '@/components/ai/contextual-ai-actions';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { fetchExecutiveApprovals, type ApprovalItem } from '@/lib/api/executive';
import {
  createTransaction,
  fetchAccounts,
  fetchFinanceStats,
  fetchFundingCommitments,
  fetchPaymentObligations,
  fetchProjectBudgets,
  fetchTransaction,
  fetchTransactions,
  formatCurrencyTotals,
  updateTransaction,
  type FinanceStats,
  type FinanceTransaction,
  type FinanceTransactionInput,
  type FinancialAccount,
  type FundingCommitment,
  type PaymentObligation,
  type ProjectBudget,
} from '@/lib/api/finance';
import { fetchInvestors } from '@/lib/api/investors';
import { fetchProjects } from '@/lib/api/projects';

import { TransactionFormModal } from '../transaction-form-modal';
import {
  ApPanel,
  ApprovalsPanel,
  ArPanel,
  AuditPanel,
  BankAccountsPanel,
  BudgetPanel,
  CashPositionPanel,
  DocumentsPanel,
  ExecutiveDashboard,
  ForecastPanel,
  IncomingWiresPanel,
  InvestorPaymentsPanel,
  OutgoingWiresPanel,
  TreasuryPanel,
  VendorPaymentsPanel,
} from './domain-panels';
import { FINANCE_VIEWS, parseView, VIEW_DATA_KIND, type FinanceViewId } from './finance-views';
import { OpsDrawer } from './ops-drawer';

import './finance-g5.css';

type FormMode = 'create' | 'edit' | null;

function buildG5Labels(t: (key: string) => string): Record<string, string> {
  const keys = [
    'liveTag',
    'partialTag',
    'demoTag',
    'blockedTag',
    'empty',
    'loading',
    'allStatuses',
    'allKinds',
    'executiveNote',
    'sparkNote',
    'kpiCash',
    'kpiAvailable',
    'kpiRestricted',
    'kpiReceivables',
    'kpiPayables',
    'kpiInvestorFunds',
    'kpiConstruction',
    'kpiBurn',
    'kpiRunway',
    'kpiCollections',
    'kpiExpectedPayments',
    'kpiNet',
    'months',
    'inflowShort',
    'outflowShort',
    'budgetShort',
    'chartCashTrend',
    'chartCashFlow',
    'chartForecast',
    'insightsTitle',
    'insightsSubtitle',
    'insightsEmpty',
    'insight.cashShortage.title',
    'insight.cashShortage.body',
    'insight.upcomingPayments.title',
    'insight.upcomingPayments.body',
    'insight.delayedInvestor.title',
    'insight.delayedInvestor.body',
    'insight.budgetOverrun.title',
    'insight.budgetOverrun.body',
    'insight.fundingGap.title',
    'insight.fundingGap.body',
    'insight.forecastAnomaly.title',
    'insight.forecastAnomaly.body',
    'cashTitle',
    'cashSubtitle',
    'accountsTitle',
    'accountsSubtitle',
    'wiresInTitle',
    'wiresInSubtitle',
    'wiresOutTitle',
    'wiresOutSubtitle',
    'wiresGap',
    'wireStatus.pending',
    'wireStatus.completed',
    'wireStatus.returned',
    'wireStatus.scheduled',
    'wireStatus.approved',
    'wireStatus.released',
    'wireStatus.cancelled',
    'investorPayTitle',
    'investorPaySubtitle',
    'investorKind.reservation',
    'investorKind.deposit',
    'investorKind.progress',
    'investorKind.final',
    'investorKind.refund',
    'investorKind.late',
    'investorKind.outstanding',
    'vendorPayTitle',
    'vendorPaySubtitle',
    'approvalState.required',
    'approvalState.cleared',
    'arTitle',
    'arSubtitle',
    'apTitle',
    'apSubtitle',
    'openItems',
    'treasuryTitle',
    'treasurySubtitle',
    'treasuryMix',
    'treasuryGap',
    'liquidity',
    'expectedLiq',
    'debt',
    'creditLines',
    'obligations',
    'forecastTitle',
    'forecastSubtitle',
    'expectedRevenue',
    'expectedExpenses',
    'projectFunding',
    'investorCollections',
    'budgetTitle',
    'budgetSubtitle',
    'approvalsTitle',
    'approvalsSubtitle',
    'executiveApprovals',
    'pendingTransactions',
    'emptyApprovals',
    'documentsTitle',
    'documentsSubtitle',
    'documentsError',
    'auditTitle',
    'auditSubtitle',
    'auditGap',
    'colBank',
    'colCurrency',
    'colBalance',
    'colAvailable',
    'colPending',
    'colReserved',
    'colLastSync',
    'colTrend',
    'colInstitution',
    'colAccount',
    'colCompany',
    'colStatus',
    'colLastActivity',
    'colCounterparty',
    'colAmount',
    'colDate',
    'colReference',
    'colProject',
    'colInvestor',
    'colKind',
    'colVendor',
    'colInvoice',
    'colDueDate',
    'colApproval',
    'colPayment',
    'colRetention',
    'colOutstanding',
    'colPayee',
    'colType',
    'colPriority',
    'colName',
    'colCategory',
    'colOriginal',
    'colRevised',
    'colCommitted',
    'colPaid',
    'colForecast',
    'colVariance',
    'colAge',
    'colSubmitted',
    'colRelated',
    'colAction',
    'colEntity',
    'colActor',
  ];
  const out: Record<string, string> = {};
  for (const key of keys) {
    try {
      out[key] = t(key);
    } catch {
      out[key] = key;
    }
  }
  return out;
}

export function FinanceG5Workspace() {
  const t = useTranslations('finance');
  const tG5 = useTranslations('finance.g5');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const authReady = Boolean(user);
  const canView = user ? hasPermission(user, 'finance', 'view') : false;
  const canCreate = user ? hasPermission(user, 'finance', 'create') : false;
  const canUpdate = user ? hasPermission(user, 'finance', 'update') : false;

  const view = parseView(searchParams.get('view'));

  const setView = (next: FinanceViewId) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 'executive') params.delete('view');
    else params.set('view', next);
    const qs = params.toString();
    router.replace((qs ? `${pathname}?${qs}` : pathname) as Route);
  };

  const labels = useMemo(() => buildG5Labels((key) => tG5(key as never)), [tG5]);

  const [stats, setStats] = useState<FinanceStats | null>(null);
  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [transactions, setTransactions] = useState<FinanceTransaction[]>([]);
  const [budgets, setBudgets] = useState<ProjectBudget[]>([]);
  const [commitments, setCommitments] = useState<FundingCommitment[]>([]);
  const [obligations, setObligations] = useState<PaymentObligation[]>([]);
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [approvalsLoading, setApprovalsLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [drawerAccount, setDrawerAccount] = useState<FinancialAccount | null>(null);
  const [drawerTransaction, setDrawerTransaction] = useState<FinanceTransaction | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [editing, setEditing] = useState<FinanceTransaction | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [projectOptions, setProjectOptions] = useState<{ id: string; label: string }[]>([]);
  const [investorOptions, setInvestorOptions] = useState<{ id: string; label: string }[]>([]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, accountsRes, txRes, budgetsRes, fundingRes, oblRes] = await Promise.all([
        fetchFinanceStats(),
        fetchAccounts({ page_size: 100, sort_by: 'updated_at', sort_order: 'desc' }),
        fetchTransactions({ page_size: 100, sort_by: 'transaction_date', sort_order: 'desc' }),
        fetchProjectBudgets({ page_size: 100, sort_by: 'updated_at', sort_order: 'desc' }),
        fetchFundingCommitments({ page_size: 100, sort_by: 'updated_at', sort_order: 'desc' }),
        fetchPaymentObligations({ page_size: 100, sort_by: 'due_date', sort_order: 'asc' }),
      ]);
      setStats(statsRes);
      setAccounts(accountsRes.items);
      setTransactions(txRes.items);
      setBudgets(budgetsRes.items);
      setCommitments(fundingRes.items);
      setObligations(oblRes.items);
      // Options for transaction modal — non-blocking
      void Promise.all([
        fetchProjects({ page_size: 100 }).catch(() => ({ items: [] as { id: string; project_name: string }[] })),
        fetchInvestors({ page_size: 100 }).catch(() => ({ items: [] as { id: string; full_name: string }[] })),
      ]).then(([projectsRes, investorsRes]) => {
        setProjectOptions(
          projectsRes.items.map((p) => ({
            id: p.id,
            label: p.project_name || p.id,
          })),
        );
        setInvestorOptions(
          investorsRes.items.map((inv) => ({
            id: inv.id,
            label: inv.full_name || inv.id,
          })),
        );
      });
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (!authReady) {
      setLoading(true);
      return;
    }
    if (!canView) {
      setLoading(false);
      return;
    }
    void loadAll();
  }, [authReady, canView, loadAll]);

  useEffect(() => {
    if (view !== 'approvals' || !canView) return;
    let cancelled = false;
    (async () => {
      setApprovalsLoading(true);
      try {
        const res = await fetchExecutiveApprovals({});
        if (!cancelled) setApprovals(res.items ?? []);
      } catch {
        if (!cancelled) setApprovals([]);
      } finally {
        if (!cancelled) setApprovalsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [view, canView]);

  const openTransaction = useCallback(
    async (id: string) => {
      const existing = transactions.find((tx) => tx.id === id);
      if (existing) {
        setDrawerTransaction(existing);
        setDrawerAccount(null);
        return;
      }
      try {
        const tx = await fetchTransaction(id);
        setDrawerTransaction(tx);
        setDrawerAccount(null);
      } catch {
        setToast(t('loadError'));
      }
    },
    [transactions, t],
  );

  const demoCount = useMemo(
    () =>
      accounts.filter((a) => a.is_demo).length +
      transactions.filter((tx) => tx.is_demo).length +
      budgets.filter((b) => b.is_demo).length,
    [accounts, transactions, budgets],
  );

  const pendingTx = useMemo(
    () => transactions.filter((tx) => tx.status === 'pending' || tx.status === 'scheduled'),
    [transactions],
  );

  const handleSubmit = async (input: FinanceTransactionInput) => {
    setSubmitting(true);
    setActionError(null);
    try {
      if (formMode === 'create') {
        await createTransaction(input);
        setToast(tG5('created'));
      } else if (formMode === 'edit' && editing) {
        await updateTransaction(editing.id, input);
        setToast(tG5('updated'));
      }
      setFormMode(null);
      setEditing(null);
      await loadAll();
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  if (!authReady) {
    return (
      <main className="fin-g5" data-testid="fin-g5-workspace">
        <div className="fin-g5__empty">{t('loading')}</div>
      </main>
    );
  }

  if (!canView) {
    return (
      <main className="fin-g5" data-testid="fin-g5-workspace">
        <div className="fin-g5__empty">{tG5('accessDenied')}</div>
      </main>
    );
  }

  const drawerTarget = drawerAccount
    ? ({ kind: 'account' as const, account: drawerAccount })
    : drawerTransaction
      ? ({ kind: 'transaction' as const, transaction: drawerTransaction })
      : null;

  return (
    <main className="fin-g5" data-testid="fin-g5-workspace">
      <header className="fin-g5__top">
        <div>
          <p className="fin-g5__eyebrow">{t('eyebrow')}</p>
          <h1 className="fin-g5__title">{tG5('title')}</h1>
          <p className="fin-g5__subtitle">
            {tG5('subtitle', {
              cash: formatCurrencyTotals(stats?.total_cash ?? {}, locale),
              accounts: accounts.length,
            })}
          </p>
        </div>
        <div className="fin-g5__top-actions">
          <ContextualAiActions module="finance" />
          {canCreate ? (
            <button
              type="button"
              className="fin-g5__btn fin-g5__btn--primary"
              data-testid="fin-g5-add-txn"
              onClick={() => {
                setFormMode('create');
                setEditing(null);
                setActionError(null);
              }}
            >
              {t('addTransaction')}
            </button>
          ) : null}
        </div>
      </header>

      <nav className="fin-g5__nav" aria-label={tG5('viewsLabel')}>
        {FINANCE_VIEWS.map((id) => (
          <button
            key={id}
            type="button"
            className={`fin-g5__nav-btn${view === id ? ' is-active' : ''}`}
            onClick={() => setView(id)}
            data-testid={`fin-g5-nav-${id}`}
            data-kind={VIEW_DATA_KIND[id]}
          >
            {tG5(`views.${id}`)}
          </button>
        ))}
      </nav>

      <div className="fin-g5__body">
        {demoCount > 0 ? (
          <div className="fin-g5__banner fin-g5__banner--info">{t('demoBanner', { count: demoCount })}</div>
        ) : null}
        {toast ? (
          <div className="fin-g5__toast">
            <span>{toast}</span>
            <button type="button" className="fin-g5__btn fin-g5__btn--ghost" onClick={() => setToast(null)}>
              {tCommon('close')}
            </button>
          </div>
        ) : null}
        {error ? <div className="fin-g5__banner">{error}</div> : null}
        {loading ? <div className="fin-g5__empty">{t('loading')}</div> : null}

        {!loading && view === 'executive' ? (
          <ExecutiveDashboard
            stats={stats}
            accounts={accounts}
            budgets={budgets}
            commitments={commitments}
            obligations={obligations}
            transactions={transactions}
            locale={locale}
            labels={labels}
          />
        ) : null}
        {!loading && view === 'cash' ? (
          <CashPositionPanel
            accounts={accounts}
            locale={locale}
            labels={labels}
            onOpenAccount={(a) => {
              setDrawerAccount(a);
              setDrawerTransaction(null);
            }}
          />
        ) : null}
        {!loading && view === 'accounts' ? (
          <BankAccountsPanel
            accounts={accounts}
            locale={locale}
            labels={labels}
            onOpenAccount={(a) => {
              setDrawerAccount(a);
              setDrawerTransaction(null);
            }}
          />
        ) : null}
        {!loading && view === 'wires_in' ? (
          <IncomingWiresPanel
            transactions={transactions}
            locale={locale}
            labels={labels}
            onOpenTransaction={openTransaction}
          />
        ) : null}
        {!loading && view === 'wires_out' ? (
          <OutgoingWiresPanel
            transactions={transactions}
            obligations={obligations}
            locale={locale}
            labels={labels}
            onOpenTransaction={openTransaction}
          />
        ) : null}
        {!loading && view === 'investor_payments' ? (
          <InvestorPaymentsPanel
            commitments={commitments}
            transactions={transactions}
            locale={locale}
            labels={labels}
          />
        ) : null}
        {!loading && view === 'vendor_payments' ? (
          <VendorPaymentsPanel obligations={obligations} locale={locale} labels={labels} />
        ) : null}
        {!loading && view === 'ar' ? (
          <ArPanel stats={stats} transactions={transactions} locale={locale} labels={labels} />
        ) : null}
        {!loading && view === 'ap' ? (
          <ApPanel stats={stats} obligations={obligations} locale={locale} labels={labels} />
        ) : null}
        {!loading && view === 'treasury' ? (
          <TreasuryPanel
            stats={stats}
            accounts={accounts}
            obligations={obligations}
            commitments={commitments}
            locale={locale}
            labels={labels}
          />
        ) : null}
        {!loading && view === 'forecast' ? (
          <ForecastPanel
            commitments={commitments}
            obligations={obligations}
            transactions={transactions}
            locale={locale}
            labels={labels}
          />
        ) : null}
        {!loading && view === 'budget' ? (
          <BudgetPanel budgets={budgets} locale={locale} labels={labels} />
        ) : null}
        {!loading && view === 'approvals' ? (
          <ApprovalsPanel
            approvals={approvals}
            pendingTransactions={pendingTx}
            locale={locale}
            labels={labels}
            loading={approvalsLoading}
          />
        ) : null}
        {!loading && view === 'documents' ? <DocumentsPanel locale={locale} labels={labels} /> : null}
        {!loading && view === 'audit' ? (
          <AuditPanel
            transactions={transactions}
            accounts={accounts}
            locale={locale}
            labels={labels}
          />
        ) : null}
      </div>

      <OpsDrawer
        target={drawerTarget}
        onClose={() => {
          setDrawerAccount(null);
          setDrawerTransaction(null);
        }}
        canUpdate={canUpdate}
        onEditTransaction={(tx) => {
          setEditing(tx);
          setFormMode('edit');
          setActionError(null);
        }}
      />

      <TransactionFormModal
        mode={formMode}
        transaction={editing}
        accounts={accounts}
        projectOptions={projectOptions}
        investorOptions={investorOptions}
        submitting={submitting}
        error={actionError}
        onClose={() => {
          setFormMode(null);
          setEditing(null);
          setActionError(null);
        }}
        onSubmit={handleSubmit}
      />
    </main>
  );
}
