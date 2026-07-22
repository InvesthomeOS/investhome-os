'use client';

import { DashboardView } from '@/components/ui-preview/mosaic/DashboardView';
import { MosaicShell } from '@/components/ui-preview/mosaic/MosaicShell';

export default function MosaicDashboardPreviewPage() {
  return (
    <MosaicShell
      title="Dashboard"
      actions={
        <>
          <button type="button" className="mosaic-btn">
            Filters
          </button>
          <button type="button" className="mosaic-btn mosaic-btn--dark">
            Add view
          </button>
        </>
      }
    >
      <DashboardView />
    </MosaicShell>
  );
}
