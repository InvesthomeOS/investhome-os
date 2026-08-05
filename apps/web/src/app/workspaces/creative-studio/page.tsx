'use client';

import { CreativeStudioDsWorkspace } from './_components/ds/creative-studio-ds-workspace';

/**
 * Creative Studio — AI Production Center (TOOLS).
 */
export default function CreativeStudioPage() {
  return (
    <main className="dashboard" data-testid="creative-studio-page">
      <CreativeStudioDsWorkspace />
    </main>
  );
}
