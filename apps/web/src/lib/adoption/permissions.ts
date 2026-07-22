import { hasPermission, type CurrentUser } from '@/lib/api/auth';

import type { AdoptionRoleId, HelpArticle } from './types';

/** Map demo / system role codes to G13 learning-path roles. */
const ROLE_CODE_MAP: Record<string, AdoptionRoleId> = {
  super_admin: 'admin',
  executive: 'ceo',
  sales: 'sales_rep',
  investor_relations: 'investor_relations',
  finance: 'finance',
  construction: 'construction_ops',
  marketing: 'marketing',
  operations: 'operations',
  partner: 'operations',
  assistant: 'executive_assistant',
  read_only: 'executive_assistant',
};

export function resolveAdoptionRoles(user: CurrentUser | null): AdoptionRoleId[] {
  if (!user) return [];
  const mapped = user.roles
    .map((r) => ROLE_CODE_MAP[r.code])
    .filter((v): v is AdoptionRoleId => Boolean(v));
  if (mapped.length === 0) return ['operations'];
  return Array.from(new Set(mapped));
}

export function primaryAdoptionRole(user: CurrentUser | null): AdoptionRoleId {
  const roles = resolveAdoptionRoles(user);
  if (roles.includes('admin')) return 'admin';
  if (roles.includes('ceo')) return 'ceo';
  if (roles.includes('cfo')) return 'cfo';
  return roles[0] ?? 'operations';
}

export function canViewAdoptionSurfaces(user: CurrentUser | null): boolean {
  return Boolean(user);
}

export function canManageTraining(user: CurrentUser | null): boolean {
  if (!user) return false;
  return (
    hasPermission(user, 'users', 'view') ||
    hasPermission(user, 'roles', 'view') ||
    hasPermission(user, 'knowledge', 'manage') ||
    hasPermission(user, 'security', 'view') ||
    hasPermission(user, '*', '*')
  );
}

export function canViewAdoptionDashboard(user: CurrentUser | null): boolean {
  return canManageTraining(user);
}

export function canViewAdminOnlyHelp(user: CurrentUser | null): boolean {
  return canManageTraining(user);
}

export function filterHelpForUser(
  articles: HelpArticle[],
  user: CurrentUser | null,
  roleIds: AdoptionRoleId[],
): HelpArticle[] {
  const allowAdmin = canViewAdminOnlyHelp(user);
  return articles.filter((a) => {
    if (a.status !== 'published' && a.status !== 'outdated') return false;
    if (a.adminOnly && !allowAdmin) return false;
    if (a.roles.includes('*' as never)) return true;
    return a.roles.some((r) => roleIds.includes(r as AdoptionRoleId));
  });
}
