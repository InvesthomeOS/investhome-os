'use client';

import dynamic from 'next/dynamic';
import { Suspense } from 'react';
import { LoadingState } from '@investhome/ui';

const ExecutiveWorkspace = dynamic(
  () =>
    import('./_components/executive-workspace').then((m) => m.ExecutiveWorkspace),
  { loading: () => <LoadingState /> },
);

export default function ExecutivePage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <ExecutiveWorkspace />
    </Suspense>
  );
}
