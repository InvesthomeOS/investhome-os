'use client';

import { OsShell } from '@/components/shell/os-shell';
import { CrmSidebar } from '@/app/workspaces/crm/_components/crm-sidebar';

import '../crm/crm-theme.css';
import './admin.css';

export default function AdminWorkspaceLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <OsShell withQueryProvider shellClassName="crm-shell" workspaceChrome={<CrmSidebar />}>
      {children}
    </OsShell>
  );
}
