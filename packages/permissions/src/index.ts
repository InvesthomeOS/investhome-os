import type { ModuleName } from '@investhome/shared';

export type PermissionAction = 'read' | 'write' | 'admin' | 'execute';

export interface Permission {
  module: ModuleName;
  resource: string;
  action: PermissionAction;
}

export interface RoleDefinition {
  id: string;
  name: string;
  permissions: Permission[];
}

export function permissionKey(permission: Permission): string {
  return `${permission.module}:${permission.resource}:${permission.action}`;
}
