'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { BrandLogo } from '@/components/brand/brand-logo';
import { IhIcon } from '@/components/icons/ih-icons';

export interface WorkspaceSidebarBrandProps {
  href: Route | string;
  collapsed: boolean;
  ariaLabel: string;
  /** Subtle workspace identity chip — never a lettermark replacement for the logo. */
  workspaceChip?: string;
  onToggleCollapsed: () => void;
  expandLabel: string;
  collapseLabel: string;
}

/**
 * Shared sidebar brand strip — official Investhome logo + collapse control.
 * Used by Dashboard, CRM, Marketing, Company, and Investor shells.
 */
export function WorkspaceSidebarBrand({
  href,
  collapsed,
  ariaLabel,
  workspaceChip,
  onToggleCollapsed,
  expandLabel,
  collapseLabel,
}: WorkspaceSidebarBrandProps) {
  return (
    <div className="dashboard-shell__sidebar-top">
      <div className="dashboard-shell__brand">
        <Link
          href={href as Route}
          className="dashboard-shell__brand-link"
          aria-label={ariaLabel}
          title={collapsed ? ariaLabel : undefined}
        >
          <BrandLogo
            layout={collapsed ? 'mark' : 'full'}
            className={
              collapsed
                ? 'dashboard-shell__brand-logo dashboard-shell__brand-logo--collapsed'
                : 'dashboard-shell__brand-logo'
            }
            priority
          />
          <span className="sr-only">{ariaLabel}</span>
        </Link>
        {!collapsed && workspaceChip ? (
          <span className="dashboard-shell__workspace-chip">{workspaceChip}</span>
        ) : null}
      </div>
      <button
        type="button"
        className="dashboard-shell__collapse"
        onClick={onToggleCollapsed}
        aria-expanded={!collapsed}
        aria-label={collapsed ? expandLabel : collapseLabel}
      >
        <IhIcon name={collapsed ? 'chevronRight' : 'chevronLeft'} size={16} />
      </button>
    </div>
  );
}
