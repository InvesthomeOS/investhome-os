'use client';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useCrmSearchStore } from '@/workspaces/crm/stores/crm-search-store';

import { CrmSearchPalette, useCrmSearchShortcuts } from '../search/_components/crm-search-palette';

/** CRM-only overlays that previously lived in CrmHeader (search palette + shortcuts). */
export function CrmWorkspaceExtras() {
  const { canRead } = useCrmAccess();
  const { openPalette } = useCrmSearchStore();

  useCrmSearchShortcuts();

  // Keep openPalette referenced so the store action stays wired for shortcuts.
  void openPalette;

  if (!canRead) {
    return null;
  }

  return <CrmSearchPalette />;
}
