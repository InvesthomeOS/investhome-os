'use client';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';
import { useTranslations } from 'next-intl';
import type { ReactNode } from 'react';

type AdminPageStatesProps = {
  loading: boolean;
  error: string | null;
  empty: boolean;
  onRetry: () => void;
  emptyTitle: string;
  emptyDescription?: string;
  children: ReactNode;
};

export function AdminPageStates({
  loading,
  error,
  empty,
  onRetry,
  emptyTitle,
  emptyDescription,
  children,
}: AdminPageStatesProps) {
  const tCommon = useTranslations('common');

  if (loading) {
    return <LoadingState label={tCommon('loading')} variant="skeleton" lines={5} />;
  }

  if (error) {
    return (
      <ErrorState
        message={error}
        action={
          <Button type="button" variant="secondary" onClick={onRetry}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  if (empty) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return <>{children}</>;
}
