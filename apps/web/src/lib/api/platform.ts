import { apiFetch } from './client';

export type PlatformModule = {
  id: string;
  code: string;
  name_en: string;
  name_tr: string;
  description_en: string | null;
  description_tr: string | null;
  lifecycle_status: string;
  enabled: boolean;
  env_enabled: boolean;
  kill_switch: boolean;
  effective_enabled: boolean;
  depends_on: string[];
  feature_flag_key: string | null;
  route_prefix: string | null;
  admin_only: boolean;
  pilot_phase: string | null;
  block_reason: string | null;
  sort_order: number;
  key_immutable?: boolean;
  key_locked?: boolean;
  health?: string;
};

export type PlatformFeatureFlag = {
  key: string;
  enabled: boolean;
  source: string;
  rollout_percent: number;
  target_roles: string[];
  target_companies: string[];
  target_users: string[];
  kill_switch: boolean;
  effective_enabled: boolean;
  environment_scope: string;
  notes: string | null;
};

export type PlatformOverview = {
  health: {
    status: string;
    environment: string;
    modules_total: number;
    modules_enabled: number;
    modules_blocked: number;
    api_clients: number;
    webhook_subscriptions: number;
    webhook_dead_letter?: number;
    mga_status: string;
    billing: string;
    kpis: Array<{ key: string; label: string; value: number | string | null; available: boolean }>;
    notification_gateway: Array<{ provider_id: string; channel: string; status: string; message: string }>;
  };
  modules: PlatformModule[];
  architecture_audit?: Array<{ capability: string; status: string; reuse: string; notes: string }>;
  integrations_summary: Record<string, number>;
  roadmap: Record<string, string>;
  recommended_next_pilot: {
    code: string;
    phase: string;
    implemented_in_g15a: boolean;
    reason_en: string;
    reason_tr: string;
  };
};

async function platformFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return apiFetch<T>(`/platform${path}`, init);
}

export const platformApi = {
  overview: () => platformFetch<PlatformOverview>('/overview'),
  health: () => platformFetch<PlatformOverview['health']>('/health'),
  architectureAudit: () =>
    platformFetch<{ items: Array<{ capability: string; status: string; reuse: string; notes: string }> }>(
      '/architecture-audit',
    ),
  modules: () => platformFetch<{ items: PlatformModule[] }>('/modules'),
  dependencies: () =>
    platformFetch<{
      modules: PlatformModule[];
      edges: Array<{ from: string; to: string }>;
      has_cycle: boolean;
      cycle: string[];
      visualization: Array<{ id: string; depends_on: string[]; health: string }>;
    }>('/modules/dependencies'),
  moduleHealth: () =>
    platformFetch<{ items: Array<Record<string, unknown>>; summary: Record<string, number> }>(
      '/modules/health',
    ),
  depsPreview: (code: string, depends_on: string[]) =>
    platformFetch<{ ok: boolean; error?: string }>(`/modules/${code}/deps-preview`, {
      method: 'POST',
      body: JSON.stringify({ depends_on }),
    }),
  updateModule: (
    code: string,
    body: {
      enabled?: boolean;
      env_enabled?: boolean;
      kill_switch?: boolean;
      depends_on?: string[];
      rename_code?: string;
    },
  ) =>
    platformFetch<PlatformModule>(`/modules/${code}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  featureFlags: () => platformFetch<{ items: PlatformFeatureFlag[] }>('/feature-flags'),
  updateFeatureFlag: (
    key: string,
    body: {
      enabled: boolean;
      kill_switch?: boolean;
      rollout_percent?: number;
      target_roles?: string[];
      notes?: string | null;
      environment_scope?: string;
    },
  ) =>
    platformFetch<PlatformFeatureFlag>(`/feature-flags/${key}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  killSwitches: () => platformFetch<{ modules: PlatformModule[]; flags: PlatformFeatureFlag[] }>('/kill-switches'),
  environment: () => platformFetch<Record<string, unknown>>('/environment'),
  entitlements: () =>
    platformFetch<{ items: Array<Record<string, unknown>>; billing: string }>('/entitlements'),
  checkEntitlement: (body: {
    capability: string;
    role_codes?: string[];
    external_type?: string | null;
  }) =>
    platformFetch<{ capability: string; allowed: boolean; reason: string; matched: string | null }>(
      '/entitlements/check',
      { method: 'POST', body: JSON.stringify(body) },
    ),
  externalUsers: () => platformFetch<{ items: Array<Record<string, unknown>> }>('/external-users'),
  apiScopes: () =>
    platformFetch<{ items: Array<Record<string, unknown>>; forbidden: string[]; note: string }>(
      '/api-scopes',
    ),
  apiClients: () => platformFetch<{ items: Array<Record<string, unknown>> }>('/api-clients'),
  createApiClient: (name: string, scopes: string[]) =>
    platformFetch<Record<string, unknown>>('/api-clients', {
      method: 'POST',
      body: JSON.stringify({ name, scopes }),
    }),
  rotateApiClient: (id: string) =>
    platformFetch<Record<string, unknown>>(`/api-clients/${id}/rotate`, { method: 'POST' }),
  revokeApiClient: (id: string) =>
    platformFetch<Record<string, unknown>>(`/api-clients/${id}/revoke`, { method: 'POST' }),
  checkApiScope: (api_key: string, required_scope: string) =>
    platformFetch<{ allowed: boolean; reason: string }>(
      '/api-clients/check-scope',
      { method: 'POST', body: JSON.stringify({ api_key, required_scope }) },
    ),
  webhooks: () => platformFetch<{ items: Array<Record<string, unknown>> }>('/webhooks'),
  deliveries: () => platformFetch<{ items: Array<Record<string, unknown>> }>('/webhooks/deliveries'),
  createWebhook: (name: string, target_url: string, event_types: string[]) =>
    platformFetch<Record<string, unknown>>('/webhooks', {
      method: 'POST',
      body: JSON.stringify({ name, target_url, event_types }),
    }),
  enqueueWebhook: (id: string, event_type: string, payload: Record<string, unknown>, signing_secret?: string) =>
    platformFetch<Record<string, unknown>>(`/webhooks/${id}/enqueue`, {
      method: 'POST',
      body: JSON.stringify({ event_type, payload, signing_secret }),
    }),
  verifySignature: (secret: string, payload: Record<string, unknown>, signature_header: string) =>
    platformFetch<{ valid: boolean }>('/webhooks/verify-signature', {
      method: 'POST',
      body: JSON.stringify({ secret, payload, signature_header }),
    }),
  deadLetterDelivery: (id: string) =>
    platformFetch<Record<string, unknown>>(`/webhooks/deliveries/${id}/dead-letter`, { method: 'POST' }),
  retryDelivery: (id: string) =>
    platformFetch<Record<string, unknown>>(`/webhooks/deliveries/${id}/retry`, { method: 'POST' }),
  integrations: () => platformFetch<{ items: Array<Record<string, unknown>> }>('/integrations'),
  externalAudit: () => platformFetch<{ items: Array<Record<string, unknown>> }>('/audit/external-access'),
  recordExternalAudit: (body: Record<string, unknown>) =>
    platformFetch<Record<string, unknown>>('/audit/external-access', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};
