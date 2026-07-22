import { hasPermission, type CurrentUser } from '@/lib/api/auth';

export function canViewProjects(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'view');
}

export function canCreateProjects(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'create');
}

export function canUpdateProjects(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'update');
}

export function canArchiveProjects(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'archive');
}

export function canRestoreProjects(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'restore');
}

export function canManageProjectStatus(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'manage_status');
}

export function canViewProjectFinancials(user: CurrentUser | null): boolean {
  return (
    hasPermission(user, 'projects', 'view_financial') ||
    hasPermission(user, 'projects', 'edit_financial')
  );
}

export function canEditProjectFinancials(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'edit_financial');
}

export function canViewProjectTeam(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'view_team');
}

export function canManageProjectTeam(user: CurrentUser | null): boolean {
  return hasPermission(user, 'projects', 'manage_team');
}
