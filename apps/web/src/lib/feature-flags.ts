import { apiFetch, unwrapApiEnvelope, type ApiEnvelope } from '@/lib/api/client';

export type FeatureFlags = Record<string, boolean>;

let cachedFlags: FeatureFlags | null = null;

export async function fetchFeatureFlags(): Promise<FeatureFlags> {
  if (cachedFlags) {
    return cachedFlags;
  }
  const response = await apiFetch<ApiEnvelope<{ feature_flags: FeatureFlags }>>('/meta');
  const data = unwrapApiEnvelope(response);
  cachedFlags = data.feature_flags ?? {};
  return cachedFlags;
}

export function isFeatureEnabled(flags: FeatureFlags, key: string): boolean {
  return Boolean(flags[key]);
}

export function clearFeatureFlagCache(): void {
  cachedFlags = null;
}
