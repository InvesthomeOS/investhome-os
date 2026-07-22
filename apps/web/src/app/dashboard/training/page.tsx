'use client';

import { AdoptionPageShell } from '@/components/adoption/adoption-page-shell';
import { TrainingWorkspace } from './_components/training-workspace';

export default function TrainingPage() {
  return (
    <AdoptionPageShell>
      <TrainingWorkspace />
    </AdoptionPageShell>
  );
}
