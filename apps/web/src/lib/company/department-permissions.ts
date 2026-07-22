import type { CurrentUser } from '@/lib/api/auth';
import { hasPermission } from '@/lib/api/auth';

export type DepartmentPermissionAction =
  | 'read'
  | 'create'
  | 'update'
  | 'delete'
  | 'archive'
  | 'export'
  | 'assign_head'
  | 'assign_employee'
  | 'transfer_employee'
  | 'move'
  | 'merge'
  | 'manage_kpi'
  | 'manage_budget';

export function hasDepartmentPermission(
  user: CurrentUser | null,
  action: DepartmentPermissionAction,
): boolean {
  if (!user) {
    return false;
  }
  return hasPermission(user, 'department', action);
}

export function canReadDepartment(user: CurrentUser | null): boolean {
  return hasDepartmentPermission(user, 'read');
}

export function canCreateDepartment(user: CurrentUser | null): boolean {
  return hasDepartmentPermission(user, 'create');
}

export function canUpdateDepartment(user: CurrentUser | null): boolean {
  return hasDepartmentPermission(user, 'update');
}

export function canDeleteDepartment(user: CurrentUser | null): boolean {
  return hasDepartmentPermission(user, 'delete');
}

export function canExportDepartments(user: CurrentUser | null): boolean {
  return hasDepartmentPermission(user, 'export');
}
