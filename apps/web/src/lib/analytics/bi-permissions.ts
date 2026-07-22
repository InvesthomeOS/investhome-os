import { hasPermission, type CurrentUser } from '@/lib/api/auth';

export function canViewAnalytics(user: CurrentUser | null): boolean {
  if (!user) return false;
  return (
    hasPermission(user, 'analytics', 'view') ||
    hasPermission(user, 'executive', 'view') ||
    hasPermission(user, 'reports', 'view')
  );
}

export function canExportAnalytics(user: CurrentUser | null): boolean {
  if (!user) return false;
  return (
    hasPermission(user, 'analytics', 'export') ||
    hasPermission(user, 'executive', 'export') ||
    hasPermission(user, 'reports', 'export')
  );
}

export function canManageAnalytics(user: CurrentUser | null): boolean {
  if (!user) return false;
  return hasPermission(user, 'analytics', 'manage');
}
