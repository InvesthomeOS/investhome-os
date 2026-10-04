import { apiFetch, clearCsrfToken } from './client';

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
  mfa_enabled?: boolean;
  mfa_method?: string | null;
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

export async function login(
  email: string,
  password: string,
): Promise<CurrentUser | MfaChallengeRequired | MfaEnrollmentRequired> {
  return apiFetch<CurrentUser | MfaChallengeRequired | MfaEnrollmentRequired>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export type MfaChallengeRequired = {
  mfa_required: true;
  mfa_challenge_token: string;
  mfa_method?: string;
  expires_in?: number;
};

export type MfaEnrollmentRequired = {
  mfa_enrollment_required: true;
  mfa_enrollment_challenge_token: string;
  expires_in?: number;
};

export type MfaEnrollStart = {
  otpauth_uri: string;
  issuer: string;
  account_label: string;
  pending: boolean;
};

export type MfaEnrollConfirm = {
  mfa_enabled: boolean;
  mfa_method: string;
  recovery_codes: string[];
};

export async function startMfaEnrollment(): Promise<MfaEnrollStart> {
  return apiFetch<MfaEnrollStart>('/auth/mfa/enroll', { method: 'POST' });
}

export async function confirmMfaEnrollment(code: string): Promise<MfaEnrollConfirm> {
  return apiFetch<MfaEnrollConfirm>('/auth/mfa/enroll/confirm', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

export type MfaRequiredEnrollConfirm = MfaEnrollConfirm & {
  user: CurrentUser;
};

export async function startRequiredMfaEnrollment(challengeToken: string): Promise<MfaEnrollStart> {
  return apiFetch<MfaEnrollStart>('/auth/mfa/enroll/required', {
    method: 'POST',
    body: JSON.stringify({ challenge_token: challengeToken }),
  });
}

export async function confirmRequiredMfaEnrollment(
  challengeToken: string,
  code: string,
): Promise<MfaRequiredEnrollConfirm> {
  return apiFetch<MfaRequiredEnrollConfirm>('/auth/mfa/enroll/required/confirm', {
    method: 'POST',
    body: JSON.stringify({ challenge_token: challengeToken, code }),
  });
}

export async function verifyMfaLogin(challengeToken: string, code: string): Promise<CurrentUser> {
  return apiFetch<CurrentUser>('/auth/mfa/verify', {
    method: 'POST',
    body: JSON.stringify({ challenge_token: challengeToken, code }),
  });
}

export async function logout(): Promise<void> {
  try {
    await apiFetch('/auth/logout', { method: 'POST' });
  } finally {
    clearCsrfToken();
  }
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

export async function fetchUsers(params?: {
  search?: string;
  status?: string;
  include_archived?: boolean;
}): Promise<{ items: UserRecord[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.search) query.set('search', params.search);
  if (params?.status) query.set('status', params.status);
  if (params?.include_archived) query.set('include_archived', 'true');
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch(`/users${suffix}`);
}

export async function fetchUser(userId: string): Promise<UserRecord> {
  return apiFetch(`/users/${userId}`);
}

export async function createUser(payload: Record<string, unknown>): Promise<InviteDelivery> {
  return apiFetch('/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export type InviteDelivery = {
  user: UserRecord;
  delivery_status: 'not_connected' | 'not_sent' | 'failed' | 'sent';
  channel?: string;
};

export type InvitePreview = {
  email: string;
  full_name: string;
  expires_at: string;
};

export function splitPersonName(fullName: string): { firstName: string; lastName: string } {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  return { firstName: parts[0] ?? '', lastName: parts.slice(1).join(' ') };
}

export function combinePersonName(firstName: string, lastName: string): string {
  return [firstName.trim(), lastName.trim()].filter(Boolean).join(' ');
}

export async function fetchInvitePreview(token: string): Promise<InvitePreview> {
  return apiFetch(`/auth/invite/${encodeURIComponent(token)}`);
}

export async function acceptInvite(
  token: string,
  password: string,
  fullName?: string,
): Promise<void> {
  const payload: Record<string, string> = { password };
  if (fullName && fullName.trim()) {
    payload.full_name = fullName.trim();
  }
  await apiFetch(`/auth/invite/${encodeURIComponent(token)}/accept`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function resendUserInvite(userId: string): Promise<InviteDelivery> {
  return apiFetch(`/users/${userId}/invite/resend`, { method: 'POST' });
}

export async function activateUser(userId: string): Promise<UserRecord> {
  return apiFetch(`/users/${userId}/activate`, { method: 'POST' });
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

export function canManageSecurity(user: CurrentUser | null): boolean {
  return hasPermission(user, 'security', 'manage');
}
