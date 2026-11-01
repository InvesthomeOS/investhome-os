'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import { EmptyState } from '../empty-state';

export function InvestmentNotFound() {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <div className="investor-page inv-detail-not-found">
      <Link href={'/investor/investments' as Route} className="inv-investments__back-link">
        ← Back to My Investments
      </Link>
      <EmptyState
        icon="◇"
        title={tChrome('k7f1dee05ad')}
        description="The investment you are looking for does not exist or may have been removed from your portfolio."
        actionLabel="Go to Dashboard"
        onAction={() => {
          window.location.href = '/investor';
        }}
      />
      <div className="inv-detail-not-found__actions">
        <Link href={'/investor/investments' as Route} className="inv-empty-state__action inv-detail-not-found__secondary">
          View All Investments
        </Link>
      </div>
    </div>
  );
}
