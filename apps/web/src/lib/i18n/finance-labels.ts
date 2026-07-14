import { useTranslations } from 'next-intl';

import {
  ACCOUNT_STATUSES,
  ACCOUNT_TYPES,
  BUDGET_CATEGORIES,
  COMMITMENT_STATUSES,
  COMMITMENT_TYPES,
  OBLIGATION_PRIORITIES,
  OBLIGATION_STATUSES,
  OBLIGATION_TYPES,
  PAYMENT_METHODS,
  TRANSACTION_STATUSES,
  TRANSACTION_TYPES,
  type AccountStatus,
  type AccountType,
  type BudgetCategory,
  type CommitmentStatus,
  type CommitmentType,
  type ObligationPriority,
  type ObligationStatus,
  type ObligationType,
  type PaymentMethod,
  type TransactionStatus,
  type TransactionType,
} from '@/lib/api/finance';

export function useFinanceLabels() {
  const tAccountType = useTranslations('finance.accountTypes');
  const tAccountStatus = useTranslations('finance.accountStatuses');
  const tTransactionType = useTranslations('finance.transactionTypes');
  const tTransactionStatus = useTranslations('finance.transactionStatuses');
  const tPaymentMethod = useTranslations('finance.paymentMethods');
  const tBudgetCategory = useTranslations('finance.budgetCategories');
  const tCommitmentType = useTranslations('finance.commitmentTypes');
  const tCommitmentStatus = useTranslations('finance.commitmentStatuses');
  const tObligationType = useTranslations('finance.obligationTypes');
  const tObligationStatus = useTranslations('finance.obligationStatuses');
  const tObligationPriority = useTranslations('finance.obligationPriorities');

  const getAccountTypeLabel = (value: AccountType | string): string =>
    tAccountType(value as AccountType);
  const getAccountStatusLabel = (value: AccountStatus | string): string =>
    tAccountStatus(value as AccountStatus);
  const getTransactionTypeLabel = (value: TransactionType | string): string =>
    tTransactionType(value as TransactionType);
  const getTransactionStatusLabel = (value: TransactionStatus | string): string =>
    tTransactionStatus(value as TransactionStatus);
  const getPaymentMethodLabel = (value: PaymentMethod | string | null | undefined): string => {
    if (!value) return '—';
    return tPaymentMethod(value as PaymentMethod);
  };
  const getBudgetCategoryLabel = (value: BudgetCategory | string): string =>
    tBudgetCategory(value as BudgetCategory);
  const getCommitmentTypeLabel = (value: CommitmentType | string): string =>
    tCommitmentType(value as CommitmentType);
  const getCommitmentStatusLabel = (value: CommitmentStatus | string): string =>
    tCommitmentStatus(value as CommitmentStatus);
  const getObligationTypeLabel = (value: ObligationType | string): string =>
    tObligationType(value as ObligationType);
  const getObligationStatusLabel = (value: ObligationStatus | string): string =>
    tObligationStatus(value as ObligationStatus);
  const getObligationPriorityLabel = (value: ObligationPriority | string): string =>
    tObligationPriority(value as ObligationPriority);

  const accountTypeOptions = ACCOUNT_TYPES.map((value) => ({
    value,
    label: tAccountType(value),
  }));
  const accountStatusOptions = ACCOUNT_STATUSES.map((value) => ({
    value,
    label: tAccountStatus(value),
  }));
  const transactionTypeOptions = TRANSACTION_TYPES.map((value) => ({
    value,
    label: tTransactionType(value),
  }));
  const transactionStatusOptions = TRANSACTION_STATUSES.map((value) => ({
    value,
    label: tTransactionStatus(value),
  }));
  const paymentMethodOptions = PAYMENT_METHODS.map((value) => ({
    value,
    label: tPaymentMethod(value),
  }));
  const budgetCategoryOptions = BUDGET_CATEGORIES.map((value) => ({
    value,
    label: tBudgetCategory(value),
  }));
  const commitmentTypeOptions = COMMITMENT_TYPES.map((value) => ({
    value,
    label: tCommitmentType(value),
  }));
  const commitmentStatusOptions = COMMITMENT_STATUSES.map((value) => ({
    value,
    label: tCommitmentStatus(value),
  }));
  const obligationTypeOptions = OBLIGATION_TYPES.map((value) => ({
    value,
    label: tObligationType(value),
  }));
  const obligationStatusOptions = OBLIGATION_STATUSES.map((value) => ({
    value,
    label: tObligationStatus(value),
  }));
  const obligationPriorityOptions = OBLIGATION_PRIORITIES.map((value) => ({
    value,
    label: tObligationPriority(value),
  }));

  return {
    getAccountTypeLabel,
    getAccountStatusLabel,
    getTransactionTypeLabel,
    getTransactionStatusLabel,
    getPaymentMethodLabel,
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
    paymentMethodOptions,
    budgetCategoryOptions,
    commitmentTypeOptions,
    commitmentStatusOptions,
    obligationTypeOptions,
    obligationStatusOptions,
    obligationPriorityOptions,
  };
}
