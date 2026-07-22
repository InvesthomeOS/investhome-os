'use client';

import { Suspense } from 'react';
import { LoadingState } from '@investhome/ui';

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingState />}>{children}</Suspense>;
}
