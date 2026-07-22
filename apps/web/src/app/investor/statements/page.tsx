'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useState } from 'react';

import { StatementsList } from '../_components/distributions/statements-list';
import { LoadingSkeleton } from '../_components/loading-skeleton';

export default function StatementsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 400);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = window.setTimeout(() => setToastMessage(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  const showToast = useCallback((message: string) => setToastMessage(message), []);

  if (isLoading) {
    return (
      <div className="investor-page inv-distributions">
        <LoadingSkeleton variant="title" />
        <LoadingSkeleton variant="card" count={3} />
      </div>
    );
  }

  return (
    <div className="investor-page inv-distributions">
      <header className="inv-distributions__page-header">
        <div>
          <Link href={'/investor/distributions' as Route} className="inv-distributions__back-link">
            ← Back to Distributions
          </Link>
          <h1 className="investor-page__title">Distribution Statements</h1>
          <p className="investor-page__subtitle">
            Search and download distribution statements linked to your payments. Mock UI — preview and
            download are placeholders.
          </p>
        </div>
      </header>

      <StatementsList
        onPreview={(id) => showToast(`Preview for statement ${id} coming soon.`)}
        onDownload={(id) => showToast(`Download for statement ${id} coming soon.`)}
      />

      {toastMessage ? (
        <div className="inv-investments__toast" role="status">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
