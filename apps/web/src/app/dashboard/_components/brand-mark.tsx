'use client';

import { BrandLogo } from '@/components/brand/brand-logo';

/** @deprecated Prefer BrandLogo — kept for any residual imports. */
export function BrandMark({ className }: { className?: string }) {
  return <BrandLogo layout="mark" className={className ?? 'dashboard-shell__brand-logo'} />;
}
