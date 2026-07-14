import { apiFetch } from './client';

export type RoleSummary = {
  id: string;
  name: string;
  code: string;
  description: string | null;
  is_system_role: boolean;
};

export type CurrentUser = {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  job_title: string | null;
  department: string | null;
  status: 'active' | 'inactive' | 'suspended' | 'invited';
  preferred_language: string;
  timezone: string;
  avatar_url: string | null;
  is_demo: boolean;
  last_login_at: string | null;
  roles: RoleSummary[];
  permissions: string[];
};

export type UserRecord = CurrentUser & {
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PermissionRecord = {
  id: string;
  resource: string;
  action: string;
  description: string | null;
  created_at: string;
};

export type RoleDetail = RoleSummary & {
  permissions: PermissionRecord[];
  created_at: string;
  updated_at: string;
};

export async function login(email: string, password: string): Promise<CurrentUser> {
  return apiFetch<CurrentUser>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  await apiFetch('/auth/logout', { method: 'POST' });
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>('/auth/me');
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiFetch('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export async function fetchUsers(): Promise<{ items: UserRecord[]; total: number }> {
  return apiFetch('/users');
}

export async function fetchUser(userId: string): Promise<UserRecord> {
  return apiFetch(`/users/${userId}`);
}

export async function createUser(payload: Record<string, unknown>): Promise<UserRecord> {
  return apiFetch('/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateUser(userId: string, payload: Record<string, unknown>): Promise<UserRecord> {
  return apiFetch(`/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deactivateUser(userId: string): Promise<UserRecord> {
  return apiFetch(`/users/${userId}/deactivate`, { method: 'POST' });
}

export async function assignUserRoles(userId: string, roleIds: string[]): Promise<UserRecord> {
  return apiFetch(`/users/${userId}/roles`, {
    method: 'PUT',
    body: JSON.stringify({ role_ids: roleIds }),
  });
}

export async function fetchRoles(): Promise<{ items: RoleSummary[]; total: number }> {
  return apiFetch('/roles');
}

export async function fetchRole(roleId: string): Promise<RoleDetail> {
  return apiFetch(`/roles/${roleId}`);
}

export async function createRole(payload: Record<string, unknown>): Promise<RoleDetail> {
  return apiFetch('/roles', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateRole(roleId: string, payload: Record<string, unknown>): Promise<RoleDetail> {
  return apiFetch(`/roles/${roleId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function assignRolePermissions(roleId: string, permissionIds: string[]): Promise<RoleDetail> {
  return apiFetch(`/roles/${roleId}/permissions`, {
    method: 'PUT',
    body: JSON.stringify({ permission_ids: permissionIds }),
  });
}

export async function fetchPermissions(): Promise<{ items: PermissionRecord[]; total: number }> {
  return apiFetch('/permissions');
}

export function hasPermission(user: CurrentUser | null, resource: string, action: string): boolean {
  if (!user) {
    return false;
  }
  if (user.permissions.includes('*:*')) {
    return true;
  }
  return user.permissions.includes(`${resource}:${action}`);
}

export function canManageUsers(user: CurrentUser | null): boolean {
  return hasPermission(user, 'users', 'manage');
}

export function canManageRoles(user: CurrentUser | null): boolean {
  return hasPermission(user, 'roles', 'manage');
}

export function canViewUsers(user: CurrentUser | null): boolean {
  return hasPermission(user, 'users', 'view') || canManageUsers(user);
}

export function canViewRoles(user: CurrentUser | null): boolean {
  return hasPermission(user, 'roles', 'view') || canManageRoles(user);
}
