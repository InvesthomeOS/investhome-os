'use client';

import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

import { Breadcrumbs } from './breadcrumbs';

function resolveWorkspaceTitle(
  pathname: string,
  t: ReturnType<typeof useTranslations<'navigation'>>,
  tHome: ReturnType<typeof useTranslations<'home'>>,
): string {
  if (pathname === '/dashboard') return tHome('workspaceTitle');
  if (pathname.startsWith('/dashboard/executive')) return t('modules.executive.title');
  if (pathname.startsWith('/dashboard/sales') || pathname.startsWith('/dashboard/leads')) {
    return t('modules.sales.title');
  }
  if (pathname.startsWith('/dashboard/investors')) return t('modules.investors.title');
  if (pathname.startsWith('/dashboard/projects')) return t('modules.projects.title');
  if (pathname.startsWith('/dashboard/inventory')) return t('modules.inventory.title');
  if (pathname.startsWith('/dashboard/marketing')) return t('modules.marketing.title');
  if (pathname.startsWith('/dashboard/finance')) return t('modules.finance.title');
  if (pathname.startsWith('/dashboard/documents')) return t('documents');
  if (pathname.startsWith('/dashboard/knowledge')) return t('documents');
  if (pathname.startsWith('/dashboard/design')) return t('designStudio');
  if (pathname.startsWith('/dashboard/activity')) return t('activity');
  if (pathname.startsWith('/dashboard/settings')) return t('settings');
  if (pathname.startsWith('/dashboard/admin')) return t('adminSection');
  if (pathname.startsWith('/workspaces/crm') || pathname.startsWith('/ui-preview/crm')) {
    return t('modules.crm.title');
  }
  if (pathname.startsWith('/workspaces/marketing')) return t('modules.marketing.title');
  if (pathname.startsWith('/company')) return t('modules.company.title');
  if (pathname.startsWith('/dashboard/analytics')) return t('businessIntelligence');
  if (pathname.startsWith('/dashboard/ai')) return t('aiWorkspace');
  if (pathname.startsWith('/dashboard/automation')) return t('automation');
  return tHome('workspaceTitle');
}

export function WorkspaceTitle() {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const tHome = useTranslations('home');
  const title = resolveWorkspaceTitle(pathname, t, tHome);
  const showCrumbs = pathname.split('/').filter(Boolean).length > 1;

  return (
    <div className="app-header__left">
      <p className="app-header__workspace">{title}</p>
      {showCrumbs ? <Breadcrumbs /> : null}
    </div>
  );
}
