import type { Route } from 'next';

import type { CurrentUser } from '@/lib/api/auth';
import { canReadCompany } from '@/lib/company/company-permissions';
import { canReadCrm } from '@/lib/crm/crm-permissions';
import { canReadMarketing } from '@/lib/marketing/marketing-permissions';

export type WorkspaceId = 'crm' | 'marketing' | 'company';

export type WorkspaceDefinition = {
  id: WorkspaceId;
  name: string;
  labelKey: string;
  descriptionKey: string;
  route: Route;
  icon: string;
  order: number;
  enabled: boolean;
  searchKeywords: string[];
  canAccess: (user: CurrentUser | null) => boolean;
};

/** Specialized operational workspaces — single registry for nav and search. */
export const OPERATIONAL_WORKSPACES: readonly WorkspaceDefinition[] = [
  {
    id: 'crm',
    name: 'crm',
    labelKey: 'modules.crm.title',
    descriptionKey: 'modules.crm.description',
    route: '/workspaces/crm/dashboard' as Route,
    icon: 'CRM',
    order: 35,
    enabled: true,
    searchKeywords: ['crm', 'contacts', 'companies', 'relationships', 'ilişki', 'müşteri'],
    canAccess: canReadCrm,
  },
  {
    id: 'marketing',
    name: 'marketing',
    labelKey: 'modules.marketing.title',
    descriptionKey: 'modules.marketing.description',
    route: '/dashboard/marketing' as Route,
    icon: 'MKT',
    order: 36,
    enabled: true,
    searchKeywords: ['marketing', 'campaigns', 'pazarlama', 'kampanya', 'lead', 'content'],
    canAccess: canReadMarketing,
  },
  {
    id: 'company',
    name: 'company',
    labelKey: 'modules.company.title',
    descriptionKey: 'modules.company.description',
    route: '/company' as Route,
    icon: 'CO',
    order: 37,
    enabled: true,
    searchKeywords: ['company', 'organization', 'şirket', 'branches', 'departments'],
    canAccess: canReadCompany,
  },
] as const;

export function getVisibleWorkspaces(user: CurrentUser | null): WorkspaceDefinition[] {
  return OPERATIONAL_WORKSPACES.filter((workspace) => workspace.enabled && workspace.canAccess(user)).sort(
    (a, b) => a.order - b.order,
  );
}

export function isWorkspaceRouteActive(pathname: string, workspace: WorkspaceDefinition): boolean {
  if (workspace.id === 'company') {
    return pathname === '/company' || pathname.startsWith('/company/');
  }
  if (workspace.id === 'crm' && pathname.startsWith('/ui-preview/crm')) {
    return true;
  }
  // Marketing canonical OS entry is /dashboard/marketing (legacy /workspaces/marketing still active-matched).
  if (workspace.id === 'marketing') {
    return (
      pathname === '/dashboard/marketing' ||
      pathname.startsWith('/dashboard/marketing/') ||
      pathname === '/workspaces/marketing' ||
      pathname.startsWith('/workspaces/marketing/')
    );
  }
  const base = `/workspaces/${workspace.id}`;
  return pathname === base || pathname.startsWith(`${base}/`);
}

export function findWorkspaceByPathname(pathname: string): WorkspaceDefinition | undefined {
  return OPERATIONAL_WORKSPACES.find((workspace) => isWorkspaceRouteActive(pathname, workspace));
}
