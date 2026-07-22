import { hasPermission, type CurrentUser } from '@/lib/api/auth';

export function canViewAutomation(user: CurrentUser | null): boolean {
  if (!user) return false;
  return (
    hasPermission(user, 'automation', 'view') ||
    hasPermission(user, 'automation', 'manage') ||
    hasPermission(user, 'marketing', 'manage_automations')
  );
}

export function canManageAutomation(user: CurrentUser | null): boolean {
  if (!user) return false;
  return (
    hasPermission(user, 'automation', 'manage') ||
    hasPermission(user, 'marketing', 'manage_automations')
  );
}
