'use client';

import { LeadsView } from '@/components/ui-preview/mosaic/LeadsView';
import { MosaicShell } from '@/components/ui-preview/mosaic/MosaicShell';

export default function MosaicLeadsPreviewPage() {
  return (
    <MosaicShell
      title="Leads"
      actions={
        <button type="button" className="mosaic-btn mosaic-btn--primary">
          New lead
        </button>
      }
    >
      <LeadsView />
    </MosaicShell>
  );
}
