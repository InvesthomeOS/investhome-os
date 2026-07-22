import type { CurrentUser } from '@/lib/api/auth';
import { hasPermission } from '@/lib/api/auth';

export type CompanyPermissionAction = 'read' | 'create' | 'update' | 'delete' | 'archive' | 'export';

const ACTION_ALIASES: Record<CompanyPermissionAction, string[]> = {
  read: ['read', 'view'],
  create: ['create'],
  update: ['update'],
  delete: ['delete'],
  archive: ['archive'],
  export: ['export'],
};

export function hasCompanyPermission(
  user: CurrentUser | null,
  action: CompanyPermissionAction,
): boolean {
  if (!user) {
    return false;
  }
  return ACTION_ALIASES[action].some((candidate) => hasPermission(user, 'company', candidate));
}

export function canReadCompany(user: CurrentUser | null): boolean {
  return hasCompanyPermission(user, 'read');
}

export function canCreateCompany(user: CurrentUser | null): boolean {
  return hasCompanyPermission(user, 'create');
}

export function canUpdateCompany(user: CurrentUser | null): boolean {
  return hasCompanyPermission(user, 'update');
}

export function canDeleteCompany(user: CurrentUser | null): boolean {
  return hasCompanyPermission(user, 'delete');
}

export function canArchiveCompany(user: CurrentUser | null): boolean {
  return hasCompanyPermission(user, 'archive');
}

export function canExportCompanies(user: CurrentUser | null): boolean {
  return hasCompanyPermission(user, 'export');
}
