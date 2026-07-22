'use client';

import { useEffect, useState, type ReactNode } from 'react';

import { PortalSessionProvider, usePortalSession } from '../_state/portal-session';
import { PortalHeader } from './portal-header';
import { PortalSidebar } from './portal-sidebar';

function PortalShellInner({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const { loading, investorId } = usePortalSession();

  useEffect(() => {
    try {
      const raw = localStorage.getItem('portal-g9-sidebar-collapsed');
      if (raw === '1') setCollapsed(true);
    } catch {
      /* ignore */
    }
  }, []);

  function toggle() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('portal-g9-sidebar-collapsed', next ? '1' : '0');
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  if (loading) {
    return (
      <div className="portal-shell" data-testid="portal-shell-loading">
        <div className="portal-empty">…</div>
      </div>
    );
  }

  if (!investorId) {
    return null;
  }

  return (
    <div className="dashboard-shell portal-shell" data-testid="portal-shell">
      <PortalSidebar collapsed={collapsed} onToggleCollapsed={toggle} />
      <div className="dashboard-shell__main">
        <PortalHeader />
        <main className="dashboard-shell__content">{children}</main>
      </div>
    </div>
  );
}

export function PortalShell({ children }: { children: ReactNode }) {
  return (
    <PortalSessionProvider>
      <PortalShellInner>{children}</PortalShellInner>
    </PortalSessionProvider>
  );
}
