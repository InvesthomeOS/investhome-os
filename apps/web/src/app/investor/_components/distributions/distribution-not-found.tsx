import Link from 'next/link';
import type { Route } from 'next';

import { EmptyState } from '../empty-state';

export function DistributionNotFound() {
  return (
    <div className="investor-page inv-distributions">
      <EmptyState
        icon="$"
        title="Distribution not found"
        description="The distribution you're looking for doesn't exist or may have been removed."
      >
        <Link href={'/investor/distributions' as Route} className="inv-empty-state__action">
          Back to Distributions
        </Link>
      </EmptyState>
    </div>
  );
}
