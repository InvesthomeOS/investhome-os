'use client';

import { useLocale, useTranslations } from 'next-intl';

import {
  formatMoney,
  formatShortDate,
  type FinanceTransaction,
} from '@/lib/api/finance';
import { useFinanceLabels } from '@/lib/i18n/finance-labels';

interface TransactionDetailDrawerProps {
  transaction: FinanceTransaction | null;
  archiving: boolean;
  onClose: () => void;
  onEdit: (transaction: FinanceTransaction) => void;
  onArchive: (transaction: FinanceTransaction) => void;
}

export function TransactionDetailDrawer({
  transaction,
  archiving,
  onClose,
  onEdit,
  onArchive,
}: TransactionDetailDrawerProps) {
  const t = useTranslations('finance');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const {
    getTransactionTypeLabel,
    getTransactionStatusLabel,
    getPaymentMethodLabel,
  } = useFinanceLabels();

  if (!transaction) {
    return null;
  }

  return (
    <div className="leads-drawer" role="presentation" onClick={onClose}>
      <aside
        className="leads-drawer__panel leads-drawer__panel--wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="transaction-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-drawer__header">
          <div>
            <p className="dashboard__eyebrow">{t('detailEyebrow')}</p>
            <h2 id="transaction-detail-title">
              {transaction.description ?? getTransactionTypeLabel(transaction.transaction_type)}
            </h2>
            {transaction.is_demo && (
              <span className="leads__demo-tag">{tCommon('demoData')}</span>
            )}
          </div>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('close')}
          </button>
        </header>

        <dl className="leads-drawer__grid">
          <div>
            <dt>{t('detail.transactionDate')}</dt>
            <dd>{formatShortDate(transaction.transaction_date, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.transactionType')}</dt>
            <dd>{getTransactionTypeLabel(transaction.transaction_type)}</dd>
          </div>
          <div>
            <dt>{t('detail.category')}</dt>
            <dd>{transaction.category ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.amount')}</dt>
            <dd>{formatMoney(transaction.amount, transaction.currency, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.status')}</dt>
            <dd>{getTransactionStatusLabel(transaction.status)}</dd>
          </div>
          <div>
            <dt>{t('detail.account')}</dt>
            <dd>{transaction.account_name ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.project')}</dt>
            <dd>{transaction.project_name ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.investor')}</dt>
            <dd>{transaction.investor_name ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.counterparty')}</dt>
            <dd>{transaction.counterparty ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.referenceNumber')}</dt>
            <dd>{transaction.reference_number ?? tCommon('noValue')}</dd>
          </div>
          <div>
            <dt>{t('detail.paymentMethod')}</dt>
            <dd>{getPaymentMethodLabel(transaction.payment_method)}</dd>
          </div>
          <div>
            <dt>{t('detail.dueDate')}</dt>
            <dd>{formatShortDate(transaction.due_date, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.paidDate')}</dt>
            <dd>{formatShortDate(transaction.paid_date, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.created')}</dt>
            <dd>{formatShortDate(transaction.created_at, locale)}</dd>
          </div>
          <div>
            <dt>{t('detail.updated')}</dt>
            <dd>{formatShortDate(transaction.updated_at, locale)}</dd>
          </div>
        </dl>

        {transaction.notes && (
          <section className="leads-drawer__notes">
            <h3>{t('detail.notes')}</h3>
            <p>{transaction.notes}</p>
          </section>
        )}

        <footer className="leads-drawer__footer">
          <button
            type="button"
            className="leads__button leads__button--secondary"
            onClick={() => onEdit(transaction)}
          >
            {t('editTransaction')}
          </button>
          <button
            type="button"
            className="leads__button leads__button--danger"
            disabled={archiving}
            onClick={() => onArchive(transaction)}
          >
            {archiving ? t('archiving') : t('archiveTransaction')}
          </button>
        </footer>
      </aside>
    </div>
  );
}
