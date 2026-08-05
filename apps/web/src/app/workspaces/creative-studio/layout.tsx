'use client';

import { OsShell } from '@/components/shell/os-shell';

import './creative-studio-shell.css';
import './creative-studio-shared.css';

/**
 * Creative Studio — standalone TOOLS module (not Marketing).
 * Uses global OS shell only; shellClassName remaps cool freeze tokens
 * (same pattern as CRM) so Marketing beige/brown brand bleed cannot tint this route.
 * New builders: wrap left/center/right with CreativeStudioFocusWorkspace from
 * ./_components/focus-workspace and put CreativeStudioFocusModeSwitcher in the toolbar.
 */

export default function CreativeStudioLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <OsShell withQueryProvider shellClassName="creative-studio-shell">
      {children}
    </OsShell>
  );
}
