'use client';

import { AdoptionPageShell } from '@/components/adoption/adoption-page-shell';
import { OnboardingWorkspace } from './_components/onboarding-workspace';

export default function OnboardingPage() {
  return (
    <AdoptionPageShell>
      <OnboardingWorkspace />
    </AdoptionPageShell>
  );
}
