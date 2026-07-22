'use client';

import { useLocale, useTranslations } from 'next-intl';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import {
  formatMoney,
  formatShortDate,
  type FinancialAccount,
  type FinanceTransaction,
} from '@/lib/api/finance';
import { useFinanceLabels } from '@/lib/i18n/finance-labels';

type DrawerTarget =
  | { kind: 'account'; account: FinancialAccount }
  | { kind: 'transaction'; transaction: FinanceTransaction };

interface OpsDrawerProps {
  target: DrawerTarget | null;
  onClose: () => void;
  onEditTransaction?: (transaction: FinanceTransaction) => void;
  canUpdate?: boolean;
}

export function OpsDrawer({ target, onClose, onEditTransaction, canUpdate }: OpsDrawerProps) {
  const t = useTranslations('finance');
  const tG5 = useTranslations('finance.g5');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const {
    getAccountTypeLabel,
    getAccountStatusLabel,
    getTransactionTypeLabel,
    getTransactionStatusLabel,
    getPaymentMethodLabel,
  } = useFinanceLabels();

  if (!target) return null;

  const title =
    target.kind === 'account'
      ? target.account.account_name
      : target.transaction.description ||
        getTransactionTypeLabel(target.transaction.transaction_type);

  return (
    <div className="fin-g5-drawer" role="presentation" onClick={onClose} data-testid="fin-g5-drawer">
      <aside
        className="fin-g5-drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="fin-g5-drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="fin-g5-drawer__header">
          <div>
            <p className="fin-g5__eyebrow">
              {target.kind === 'account' ? tG5('drawerAccount') : t('detailEyebrow')}
            </p>
            <h2 id="fin-g5-drawer-title">{title}</h2>
          </div>
          <button type="button" className="fin-g5__btn fin-g5__btn--ghost" onClick={onClose}>
            {tCommon('close')}
          </button>
        </header>

        {target.kind === 'transaction' && canUpdate && onEditTransaction ? (
          <div className="fin-g5-drawer__actions">
            <button
              type="button"
              className="fin-g5__btn fin-g5__btn--primary"
              onClick={() => onEditTransaction(target.transaction)}
            >
              {t('editTransaction')}
            </button>
          </div>
        ) : null}

        <div className="fin-g5-drawer__body">
          {target.kind === 'account' ? (
            <dl className="fin-g5-drawer__grid">
              <div>
                <dt>{t('accountsTable.institution')}</dt>
                <dd>{target.account.institution_name || tCommon('noValue')}</dd>
              </div>
              <div>
                <dt>{t('accountTypeLabel')}</dt>
                <dd>{getAccountTypeLabel(target.account.account_type)}</dd>
              </div>
              <div>
                <dt>{tG5('colCompany')}</dt>
                <dd>{target.account.ownership_entity || tCommon('noValue')}</dd>
              </div>
              <div>
                <dt>{t('currencyLabel')}</dt>
                <dd>{target.account.currency}</dd>
              </div>
              <div>
                <dt>{t('accountsTable.currentBalance')}</dt>
                <dd>{formatMoney(target.account.current_balance, target.account.currency, locale)}</dd>
              </div>
              <div>
                <dt>{t('accountsTable.availableBalance')}</dt>
                <dd>{formatMoney(target.account.available_balance, target.account.currency, locale)}</dd>
              </div>
              <div>
                <dt>{t('statusLabel')}</dt>
                <dd>{getAccountStatusLabel(target.account.status)}</dd>
              </div>
              <div>
                <dt>{tG5('colLastActivity')}</dt>
                <dd>{formatShortDate(target.account.updated_at, locale)}</dd>
              </div>
            </dl>
          ) : (
            <dl className="fin-g5-drawer__grid">
              <div>
                <dt>{t('detail.transactionDate')}</dt>
                <dd>{formatShortDate(target.transaction.transaction_date, locale)}</dd>
              </div>
              <div>
                <dt>{t('detail.transactionType')}</dt>
                <dd>{getTransactionTypeLabel(target.transaction.transaction_type)}</dd>
              </div>
              <div>
                <dt>{t('detail.amount')}</dt>
                <dd>{formatMoney(target.transaction.amount, target.transaction.currency, locale)}</dd>
              </div>
              <div>
                <dt>{t('detail.status')}</dt>
                <dd>{getTransactionStatusLabel(target.transaction.status)}</dd>
              </div>
              <div>
                <dt>{t('detail.account')}</dt>
                <dd>{target.transaction.account_name || tCommon('noValue')}</dd>
              </div>
              <div>
                <dt>{t('detail.paymentMethod')}</dt>
                <dd>
                  {target.transaction.payment_method
                    ? getPaymentMethodLabel(target.transaction.payment_method)
                    : tCommon('noValue')}
                </dd>
              </div>
              <div>
                <dt>{t('detail.counterparty')}</dt>
                <dd>{target.transaction.counterparty || tCommon('noValue')}</dd>
              </div>
              <div>
                <dt>{t('detail.referenceNumber')}</dt>
                <dd>{target.transaction.reference_number || tCommon('noValue')}</dd>
              </div>
            </dl>
          )}

          {target.kind === 'transaction' ? (
            <div style={{ marginTop: '1rem' }}>
              <EntityDocumentsPanel
                entityType="transaction"
                entityId={target.transaction.id}
                transactionId={target.transaction.id}
              />
            </div>
          ) : null}
          <div style={{ marginTop: '1rem' }}>
            <EntityActivityTimeline
              entityType={target.kind === 'account' ? 'financial_account' : 'transaction'}
              entityId={target.kind === 'account' ? target.account.id : target.transaction.id}
            />
          </div>
        </div>
      </aside>
    </div>
  );
}
