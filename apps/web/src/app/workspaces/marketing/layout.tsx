'use client';

import { OsShell } from '@/components/shell/os-shell';

import { MarketingSidebar } from './_components/marketing-sidebar';

import './marketing-theme.css';

export default function MarketingLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <OsShell withQueryProvider shellClassName="marketing-shell" workspaceChrome={<MarketingSidebar />}>
      {children}
    </OsShell>
  );
}
