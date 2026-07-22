import type { CurrentUser } from '@/lib/api/auth';
import { hasPermission } from '@/lib/api/auth';

export type BranchPermissionAction =
  | 'read'
  | 'create'
  | 'update'
  | 'delete'
  | 'assign_manager'
  | 'transfer_employee'
  | 'export';

export function hasBranchPermission(
  user: CurrentUser | null,
  action: BranchPermissionAction,
): boolean {
  if (!user) {
    return false;
  }
  return hasPermission(user, 'branch', action);
}

export function canReadBranch(user: CurrentUser | null): boolean {
  return hasBranchPermission(user, 'read');
}

export function canCreateBranch(user: CurrentUser | null): boolean {
  return hasBranchPermission(user, 'create');
}

export function canUpdateBranch(user: CurrentUser | null): boolean {
  return hasBranchPermission(user, 'update');
}

export function canDeleteBranch(user: CurrentUser | null): boolean {
  return hasBranchPermission(user, 'delete');
}

export function canAssignBranchManager(user: CurrentUser | null): boolean {
  return hasBranchPermission(user, 'assign_manager');
}

export function canTransferBranchEmployees(user: CurrentUser | null): boolean {
  return hasBranchPermission(user, 'transfer_employee');
}

export function canExportBranches(user: CurrentUser | null): boolean {
  return hasBranchPermission(user, 'export');
}
