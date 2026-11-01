'use client';

import { useTranslations } from 'next-intl';
import Link from 'next/link';
import type { Route } from 'next';

import { EmptyState } from '../empty-state';

export function DistributionNotFound() {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <div className="investor-page inv-distributions">
      <EmptyState
        icon="$"
        title={tChrome('k7ff09ebb98')}
        description="The distribution you're looking for doesn't exist or may have been removed."
      >
        <Link href={'/investor/distributions' as Route} className="inv-empty-state__action">
          Back to Distributions
        </Link>
      </EmptyState>
    </div>
  );
}
