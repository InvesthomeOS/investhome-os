import { apiFetch } from './client';

export type SecurityKpi = {
  key: string;
  label: string;
  value: number | string | null;
  available: boolean;
  note: string | null;
};

export type SecurityDashboard = {
  kpis: SecurityKpi[];
  alerts: Array<{ severity: string; title: string; detail: string }>;
  generated_at: string;
};

export type AuthSessionItem = {
  id: string;
  user_id: string;
  user_email: string | null;
  user_name: string | null;
  ip_address: string | null;
  user_agent: string | null;
  device_label: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  revoked_at: string | null;
  is_current: boolean;
};

export type ProviderStatus = {
  provider_id: string;
  category: string;
  label: string;
  status: string;
  configured: boolean;
  message: string | null;
  env_keys: string[];
};

export type ApiKeyItem = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  status: string;
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
};

export type FeatureFlagItem = {
  key: string;
  enabled: boolean;
  source: string;
  rollout_percent: number;
  target_roles: string[];
  notes: string | null;
  env_default: boolean | null;
};

export type SystemHealth = {
  components: Array<{
    id: string;
    label: string;
    status: string;
    detail: string | null;
    link: string | null;
  }>;
  overall: string;
};

export type SecurityIncident = {
  id: string;
  title: string;
  severity: string;
  status: string;
  category: string;
  summary: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
};

export async function fetchSecurityDashboard(): Promise<SecurityDashboard> {
  return apiFetch('/security/dashboard');
}

export async function fetchSessions(params?: {
  userId?: string;
  includeRevoked?: boolean;
}): Promise<{ items: AuthSessionItem[]; total: number }> {
  const q = new URLSearchParams();
  if (params?.userId) q.set('user_id', params.userId);
  if (params?.includeRevoked) q.set('include_revoked', 'true');
  const suffix = q.toString() ? `?${q}` : '';
  return apiFetch(`/security/sessions${suffix}`);
}

export async function terminateSession(sessionId: string): Promise<void> {
  await apiFetch(`/security/sessions/${sessionId}/terminate`, { method: 'POST' });
}

export async function terminateAllSessions(userId?: string): Promise<{ sessions_revoked: number }> {
  const q = userId ? `?user_id=${userId}` : '';
  return apiFetch(`/security/sessions/terminate-all${q}`, { method: 'POST' });
}

export async function fetchSsoProviders(): Promise<{ items: ProviderStatus[] }> {
  return apiFetch('/security/sso');
}

export async function fetchMfaPolicy(): Promise<{
  enforcement: string;
  methods: ProviderStatus[];
  recovery_codes_available: boolean;
  adoption: SecurityKpi;
}> {
  return apiFetch('/security/mfa');
}

export async function fetchSecretProviders(): Promise<{ items: ProviderStatus[] }> {
  return apiFetch('/security/secrets');
}

export async function fetchApiKeys(): Promise<{ items: ApiKeyItem[]; total: number }> {
  return apiFetch('/security/api-keys');
}

export async function createApiKey(payload: {
  name: string;
  scopes?: string[];
  expires_at?: string | null;
}): Promise<{ key: ApiKeyItem; secret: string }> {
  return apiFetch('/security/api-keys', { method: 'POST', body: JSON.stringify(payload) });
}

export async function rotateApiKey(keyId: string): Promise<{ key: ApiKeyItem; secret: string }> {
  return apiFetch(`/security/api-keys/${keyId}/rotate`, { method: 'POST' });
}

export async function revokeApiKey(keyId: string): Promise<ApiKeyItem> {
  return apiFetch(`/security/api-keys/${keyId}/revoke`, { method: 'POST' });
}

export async function fetchFeatureFlags(): Promise<{ items: FeatureFlagItem[] }> {
  return apiFetch('/security/feature-flags');
}

export async function updateFeatureFlag(
  key: string,
  payload: { enabled: boolean; rollout_percent?: number; target_roles?: string[]; notes?: string },
): Promise<FeatureFlagItem> {
  return apiFetch(`/security/feature-flags/${key}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function fetchCompliance(): Promise<Record<string, unknown>> {
  return apiFetch('/security/compliance');
}

export async function fetchDataGovernance(): Promise<Record<string, unknown>> {
  return apiFetch('/security/data-governance');
}

export async function fetchBackupStatus(): Promise<{
  status: string;
  last_backup_at: string | null;
  health: string;
  provider: string;
  message: string;
  env_keys: string[];
}> {
  return apiFetch('/security/backup');
}

export async function fetchSystemConfig(): Promise<{
  currencies: string[];
  languages: string[];
  timezones: string[];
  feature_flags: FeatureFlagItem[];
  brand_settings_path: string;
  organization_path: string;
}> {
  return apiFetch('/security/system-config');
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  return apiFetch('/security/health');
}

export async function fetchIncidents(): Promise<{ items: SecurityIncident[]; total: number }> {
  return apiFetch('/security/incidents');
}

export async function createIncident(payload: {
  title: string;
  severity?: string;
  category?: string;
  summary?: string;
}): Promise<SecurityIncident> {
  return apiFetch('/security/incidents', { method: 'POST', body: JSON.stringify(payload) });
}

export async function exportAudit(payload?: {
  from_date?: string;
  to_date?: string;
  actions?: string[];
}): Promise<{ exported_at: string; total: number; items: unknown[]; note: string }> {
  return apiFetch('/security/audit/export', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export async function fetchAuditCategories(): Promise<{
  categories: Array<{ id: string; actions: string[] }>;
}> {
  return apiFetch('/security/audit/categories');
}

export async function forceLogoutUser(userId: string): Promise<{ sessions_revoked: number }> {
  return apiFetch(`/users/${userId}/force-logout`, { method: 'POST' });
}

export async function resetUserPassword(userId: string): Promise<{ message: string }> {
  return apiFetch(`/users/${userId}/reset-password`, { method: 'POST' });
}

export async function suspendUser(userId: string): Promise<{ message: string }> {
  return apiFetch(`/users/${userId}/suspend`, { method: 'POST' });
}

export async function fetchTemporaryGrants(): Promise<{
  items: Array<{
    id: string;
    user_id: string;
    resource: string;
    action: string;
    reason: string | null;
    expires_at: string;
    revoked_at: string | null;
  }>;
  total: number;
}> {
  return apiFetch('/security/temporary-grants');
}
