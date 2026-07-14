'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  type FinanceTransaction,
  type FinanceTransactionInput,
  type FinancialAccount,
  type PaymentMethod,
  type TransactionStatus,
  type TransactionType,
} from '@/lib/api/finance';
import { useFinanceLabels } from '@/lib/i18n/finance-labels';

interface TransactionFormModalProps {
  mode: 'create' | 'edit' | null;
  transaction: FinanceTransaction | null;
  accounts: FinancialAccount[];
  projectOptions: { id: string; label: string }[];
  investorOptions: { id: string; label: string }[];
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (input: FinanceTransactionInput) => void;
}

const EMPTY_FORM: FinanceTransactionInput = {
  transaction_date: new Date().toISOString().slice(0, 10),
  transaction_type: 'expense',
  category: '',
  amount: 0,
  currency: 'USD',
  description: '',
  account_id: '',
  project_id: null,
  investor_id: null,
  counterparty: '',
  reference_number: '',
  payment_method: null,
  status: 'pending',
  due_date: null,
  paid_date: null,
  notes: '',
};

export function TransactionFormModal({
  mode,
  transaction,
  accounts,
  projectOptions,
  investorOptions,
  submitting,
  error,
  onClose,
  onSubmit,
}: TransactionFormModalProps) {
  const t = useTranslations('finance');
  const tCommon = useTranslations('common');
  const {
    transactionTypeOptions,
    transactionStatusOptions,
    paymentMethodOptions,
  } = useFinanceLabels();
  const [form, setForm] = useState<FinanceTransactionInput>(EMPTY_FORM);

  useEffect(() => {
    if (mode === 'edit' && transaction) {
      setForm({
        transaction_date: transaction.transaction_date,
        transaction_type: transaction.transaction_type,
        category: transaction.category ?? '',
        amount: Number(transaction.amount),
        currency: transaction.currency,
        description: transaction.description ?? '',
        account_id: transaction.account_id,
        project_id: transaction.project_id,
        investor_id: transaction.investor_id,
        counterparty: transaction.counterparty ?? '',
        reference_number: transaction.reference_number ?? '',
        payment_method: transaction.payment_method,
        status: transaction.status,
        due_date: transaction.due_date,
        paid_date: transaction.paid_date,
        notes: transaction.notes ?? '',
      });
      return;
    }

    if (mode === 'create') {
      setForm({
        ...EMPTY_FORM,
        account_id: accounts[0]?.id ?? '',
      });
    }
  }, [accounts, mode, transaction]);

  if (!mode) {
    return null;
  }

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit({
      ...form,
      category: form.category?.trim() || null,
      description: form.description?.trim() || null,
      counterparty: form.counterparty?.trim() || null,
      reference_number: form.reference_number?.trim() || null,
      project_id: form.project_id || null,
      investor_id: form.investor_id || null,
      payment_method: form.payment_method || null,
      due_date: form.due_date || null,
      paid_date: form.paid_date || null,
      notes: form.notes?.trim() || null,
    });
  };

  return (
    <div className="leads-modal" role="presentation" onClick={onClose}>
      <div
        className="leads-modal__dialog leads-drawer__panel--wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="transaction-form-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-modal__header">
          <h2 id="transaction-form-title">
            {mode === 'create' ? t('addTransaction') : t('editTransaction')}
          </h2>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('close')}
          </button>
        </header>

        <form className="leads-form" onSubmit={handleSubmit}>
          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.transactionDate')}</span>
              <input
                type="date"
                required
                value={form.transaction_date}
                onChange={(event) =>
                  setForm((current) => ({ ...current, transaction_date: event.target.value }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.transactionType')}</span>
              <select
                required
                value={form.transaction_type}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    transaction_type: event.target.value as TransactionType,
                  }))
                }
              >
                {transactionTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.amount')}</span>
              <input
                type="number"
                required
                min="0.01"
                step="0.01"
                value={form.amount || ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, amount: Number(event.target.value) }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.currency')}</span>
              <input
                required
                maxLength={3}
                value={form.currency ?? 'USD'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    currency: event.target.value.toUpperCase(),
                  }))
                }
              />
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.account')}</span>
              <select
                required
                value={form.account_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, account_id: event.target.value }))
                }
              >
                <option value="">{t('form.selectAccount')}</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.account_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="leads__field">
              <span>{t('form.status')}</span>
              <select
                value={form.status ?? 'pending'}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    status: event.target.value as TransactionStatus,
                  }))
                }
              >
                {transactionStatusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.project')}</span>
              <select
                value={form.project_id ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    project_id: event.target.value || null,
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
              <span>{t('form.investor')}</span>
              <select
                value={form.investor_id ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    investor_id: event.target.value || null,
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
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.category')}</span>
              <input
                value={form.category ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, category: event.target.value }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.paymentMethod')}</span>
              <select
                value={form.payment_method ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    payment_method: (event.target.value as PaymentMethod) || null,
                  }))
                }
              >
                <option value="">{tCommon('noValue')}</option>
                {paymentMethodOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="leads__field">
            <span>{t('form.description')}</span>
            <input
              value={form.description ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </label>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.counterparty')}</span>
              <input
                value={form.counterparty ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, counterparty: event.target.value }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.referenceNumber')}</span>
              <input
                value={form.reference_number ?? ''}
                onChange={(event) =>
                  setForm((current) => ({ ...current, reference_number: event.target.value }))
                }
              />
            </label>
          </div>

          <div className="leads-form__grid">
            <label className="leads__field">
              <span>{t('form.dueDate')}</span>
              <input
                type="date"
                value={form.due_date ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    due_date: event.target.value || null,
                  }))
                }
              />
            </label>
            <label className="leads__field">
              <span>{t('form.paidDate')}</span>
              <input
                type="date"
                value={form.paid_date ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    paid_date: event.target.value || null,
                  }))
                }
              />
            </label>
          </div>

          <label className="leads__field">
            <span>{t('form.notes')}</span>
            <textarea
              rows={3}
              value={form.notes ?? ''}
              onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
            />
          </label>

          {error && <p className="leads__error">{error}</p>}

          <footer className="leads-modal__footer">
            <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
              {tCommon('cancel')}
            </button>
            <button type="submit" className="leads__button leads__button--primary" disabled={submitting}>
              {submitting
                ? t('saving')
                : mode === 'create'
                  ? t('createTransaction')
                  : t('saveChanges')}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
