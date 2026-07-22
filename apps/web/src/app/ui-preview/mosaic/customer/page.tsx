'use client';

import { CustomerView } from '@/components/ui-preview/mosaic/CustomerView';
import { MosaicShell } from '@/components/ui-preview/mosaic/MosaicShell';

export default function MosaicCustomerPreviewPage() {
  return (
    <MosaicShell title="Customer">
      <CustomerView />
    </MosaicShell>
  );
}
