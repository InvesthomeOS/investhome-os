'use client';

import { OsShell } from '@/components/shell/os-shell';
import { ContactCardProvider } from '@/workspaces/crm/contact-card/contact-card-context';

import { CrmSidebar } from './_components/crm-sidebar';
import { CrmWorkspaceExtras } from './_components/crm-workspace-extras';

import './crm-theme.css';

export default function CrmLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <OsShell withQueryProvider shellClassName="crm-shell" workspaceChrome={<CrmSidebar />}>
      <ContactCardProvider>
        <CrmWorkspaceExtras />
        {children}
      </ContactCardProvider>
    </OsShell>
  );
}
