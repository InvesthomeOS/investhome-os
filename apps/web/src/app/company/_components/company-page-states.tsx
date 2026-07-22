'use client';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';
import { useTranslations } from 'next-intl';

type CompanyPageStatesProps = {
  isLoading?: boolean;
  isError?: boolean;
  isEmpty?: boolean;
  loadingLabel?: string;
  errorTitle?: string;
  errorMessage?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  children: React.ReactNode;
};

export function CompanyPageStates({
  isLoading = false,
  isError = false,
  isEmpty = false,
  loadingLabel,
  errorTitle,
  errorMessage,
  emptyTitle,
  emptyDescription,
  children,
}: CompanyPageStatesProps) {
  const t = useTranslations('company');

  if (isLoading) {
    return <LoadingState label={loadingLabel ?? t('loading')} />;
  }

  if (isError) {
    return <ErrorState title={errorTitle ?? t('loadFailed')} message={errorMessage ?? t('loadFailed')} />;
  }

  if (isEmpty) {
    return <EmptyState title={emptyTitle ?? t('stubs.comingSoon')} description={emptyDescription} />;
  }

  return <>{children}</>;
}
