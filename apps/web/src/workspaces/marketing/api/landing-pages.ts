import { apiFetch } from '@/lib/api/client';

export type LandingPageSummary = {
  id: string;
  name: string;
  slug: string;
  status: string;
  campaign_id: string | null;
  form_id: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export async function fetchLandingPages(page = 1, pageSize = 25) {
  return apiFetch<{ items: LandingPageSummary[]; total: number; pages: number }>(
    `/marketing/landing-pages?page=${page}&page_size=${pageSize}`,
  );
}
