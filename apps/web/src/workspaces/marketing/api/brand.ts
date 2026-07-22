import { apiFetch } from '@/lib/api/client';

export type BrandProfileSummary = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export async function fetchBrandOverview() {
  return apiFetch<{ profiles: BrandProfileSummary[]; default_profile_id: string | null; profile_count: number }>(
    '/marketing/brand',
  );
}

export async function fetchBrandProfile(profileId: string) {
  return apiFetch<BrandProfileSummary & Record<string, unknown>>(`/marketing/brand/profiles/${profileId}`);
}

export async function fetchBrandGuidelines(profileId: string) {
  return apiFetch<{
    guidelines_json: Record<string, unknown> | null;
    colors_json: Record<string, unknown> | null;
    typography_json: Record<string, unknown> | null;
    voice_json: Record<string, unknown> | null;
  }>(`/marketing/brand/profiles/${profileId}/guidelines`);
}

export async function fetchBrandTerminology(profileId: string) {
  return apiFetch<{ items: unknown[] }>(`/marketing/brand/profiles/${profileId}/terminology`);
}

export async function fetchApprovedClaims(profileId: string) {
  return apiFetch<{ items: unknown[] }>(`/marketing/brand/profiles/${profileId}/claims/approved`);
}

export async function fetchProhibitedClaims(profileId: string) {
  return apiFetch<{ items: unknown[] }>(`/marketing/brand/profiles/${profileId}/claims/prohibited`);
}

export async function runBrandComplianceCheck(payload: {
  brand_profile_id?: string;
  body_text: string;
  content_id?: string;
}) {
  return apiFetch<{ result: { status: string; violations_json: unknown[] | null } }>(
    '/marketing/brand/compliance-check',
    { method: 'POST', body: JSON.stringify(payload) },
  );
}
