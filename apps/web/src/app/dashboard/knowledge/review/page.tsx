import { Suspense } from 'react';

import KnowledgeReviewPage from './review-client';

export default function KnowledgeReviewRoute() {
  return (
    <Suspense fallback={<main className="leads-page"><p>Loading…</p></main>}>
      <KnowledgeReviewPage />
    </Suspense>
  );
}
