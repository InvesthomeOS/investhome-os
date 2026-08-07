'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { BrandLogo } from '@/components/brand/brand-logo';
import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import { useSidebarCollapsed } from './use-sidebar-collapsed';

const MENU_ITEMS: ReadonlyArray<{ labelKey: string; href: Route; icon: IhIconName }> = [
  { labelKey: 'dashboard', href: '/dashboard' as Route, icon: 'home' },
  { labelKey: 'crm', href: '/workspaces/crm' as Route, icon: 'crm' },
  { labelKey: 'sales', href: '/dashboard/sales' as Route, icon: 'sales' },
  { labelKey: 'investors', href: '/dashboard/investors' as Route, icon: 'investors' },
  { labelKey: 'inventory', href: '/dashboard/inventory' as Route, icon: 'inventory' },
  { labelKey: 'projects', href: '/dashboard/projects' as Route, icon: 'projects' },
  { labelKey: 'finance', href: '/dashboard/finance' as Route, icon: 'finance' },
  { labelKey: 'marketing', href: '/dashboard/marketing' as Route, icon: 'marketing' },
  { labelKey: 'contentStudio', href: '/workspaces/marketing/brand' as Route, icon: 'documents' },
  { labelKey: 'calendar', href: '/workspaces/marketing/calendar' as Route, icon: 'calendar' },
  { labelKey: 'tasks', href: '/workspaces/crm/tasks' as Route, icon: 'check' },
];

/**
 * @deprecated OS product shell uses StandardSidebarNav via SidebarNav.
 * Retained only for CRM Production Freeze / ui-preview chrome parity.
 */
export function ScreenshotDashboardSidebar({
  activeItem = 'dashboard',
  previewMode = false,
}: {
  activeItem?: 'dashboard' | 'crm';
  previewMode?: boolean;
}) {
  const [collapsed, toggleCollapsed] = useSidebarCollapsed();
  const t = useTranslations('screenshotDashboard.sidebar');

  return (
    <aside
      className={`screenshot-sidebar dashboard-shell__sidebar${
        collapsed ? ' dashboard-shell__sidebar--collapsed' : ''
      }`}
    >
      <Link href={'/dashboard' as Route} className="screenshot-sidebar__brand" aria-label="Investhome OS">
        <BrandLogo
          tone="color"
          layout={collapsed ? 'mark' : 'full'}
          className={collapsed ? 'screenshot-sidebar__logo is-collapsed' : 'screenshot-sidebar__logo'}
          priority
          alt="Investhome"
        />
      </Link>

      <nav className="screenshot-sidebar__menu" aria-label={t('ariaLabel')}>
        {MENU_ITEMS.map((item) => {
          const label = t(item.labelKey);
          const isActive = item.labelKey === activeItem;
          return (
            <Link
              key={item.labelKey}
              href={item.href}
              className={`screenshot-sidebar__item${isActive ? ' is-active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
              title={collapsed ? label : undefined}
              onClick={previewMode ? (event) => event.preventDefault() : undefined}
            >
              <IhIcon name={item.icon} size={15} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="screenshot-sidebar__footer">
        {!collapsed ? (
          <div className="screenshot-sidebar__scene" aria-hidden="true">
            <span className="screenshot-sidebar__tree is-left" />
            <span className="screenshot-sidebar__building">
              <i /><i /><i /><i /><i /><i />
            </span>
            <span className="screenshot-sidebar__tree is-right" />
          </div>
        ) : null}
        <button
          type="button"
          className="screenshot-sidebar__toggle"
          onClick={toggleCollapsed}
          aria-expanded={!collapsed}
          aria-label={collapsed ? t('expand') : t('collapse')}
        >
          <IhIcon name={collapsed ? 'chevronRight' : 'chevronLeft'} size={13} />
          {!collapsed ? <span>{t('collapseShort')}</span> : null}
        </button>
      </div>
    </aside>
  );
}
