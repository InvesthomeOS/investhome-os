'use client';

import { AdoptionPageShell } from '@/components/adoption/adoption-page-shell';
import { OperationsWorkspace } from './_components/operations-workspace';

export default function OperationsPage() {
  return (
    <AdoptionPageShell adminOnly>
      <OperationsWorkspace />
    </AdoptionPageShell>
  );
}
