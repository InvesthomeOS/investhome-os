import { apiFetch } from '@/lib/api/client';

export type FormSummary = {
  id: string;
  name: string;
  slug: string;
  status: string;
  campaign_id: string | null;
  source_id: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export async function fetchForms(page = 1, pageSize = 25) {
  return apiFetch<{ items: FormSummary[]; total: number; pages: number }>(
    `/marketing/forms?page=${page}&page_size=${pageSize}`,
  );
}
