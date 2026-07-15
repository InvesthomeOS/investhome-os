import { Suspense } from 'react';

import { SettingsWorkspace } from './_components/settings-workspace';

export default function SettingsPage() {
  return (
    <Suspense fallback={<main className="dashboard" />}>
      <SettingsWorkspace />
    </Suspense>
  );
}
