'use client';

import { AdoptionPageShell } from '@/components/adoption/adoption-page-shell';
import { TrainingBuilderWorkspace } from './_components/training-builder';

export default function TrainingBuilderPage() {
  return (
    <AdoptionPageShell adminOnly>
      <TrainingBuilderWorkspace />
    </AdoptionPageShell>
  );
}
