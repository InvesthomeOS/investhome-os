'use client';

import { AdoptionPageShell } from '@/components/adoption/adoption-page-shell';
import { AdoptionDashboard } from './_components/adoption-dashboard';

export default function AdminAdoptionPage() {
  return (
    <AdoptionPageShell adminOnly>
      <AdoptionDashboard />
    </AdoptionPageShell>
  );
}
