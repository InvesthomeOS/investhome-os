'use client';

import { AdoptionPageShell } from '@/components/adoption/adoption-page-shell';
import { HelpWorkspace } from './_components/help-workspace';

export default function HelpPage() {
  return (
    <AdoptionPageShell>
      <HelpWorkspace />
    </AdoptionPageShell>
  );
}
