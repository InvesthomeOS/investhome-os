'use client';

import type { ReactNode } from 'react';

import { DocumentsStateProvider } from '../_state/documents-state';
import { MessagingStateProvider } from '../_state/messaging-state';
import { InvestorHeader } from './investor-header';
import { InvestorSidebar } from './investor-sidebar';
import { useInvestorSidebarCollapsed } from './use-investor-sidebar-collapsed';

export function InvestorShell({ children }: { children: ReactNode }) {
  const [collapsed, toggleCollapsed] = useInvestorSidebarCollapsed();

  return (
    <DocumentsStateProvider>
      <MessagingStateProvider>
        <div className="dashboard-shell investor-shell">
          <InvestorSidebar collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />
          <div className="dashboard-shell__main investor-main">
            <InvestorHeader />
            <main className="dashboard-shell__content investor-content">{children}</main>
          </div>
        </div>
      </MessagingStateProvider>
    </DocumentsStateProvider>
  );
}
