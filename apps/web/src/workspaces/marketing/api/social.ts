import { apiFetch } from '@/lib/api/client';

import type { ChannelDashboardBase, ReadinessResult } from './channel';

export type SocialPostSummary = {
  id: string;
  title: string | null;
  status: string;
  approval_status: string;
  readiness_state: string;
  scheduled_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SocialDashboard = ChannelDashboardBase & {
  total_posts: number;
  scheduled_posts: number;
  connected_accounts: number;
};

export const socialQueryKeys = {
  all: ['marketing', 'social'] as const,
  dashboard: () => ['marketing', 'social', 'dashboard'] as const,
  list: (page = 1) => ['marketing', 'social', 'list', page] as const,
  detail: (id: string) => ['marketing', 'social', 'detail', id] as const,
  accounts: () => ['marketing', 'social', 'accounts'] as const,
  inbox: () => ['marketing', 'social', 'inbox'] as const,
};

export async function fetchSocialDashboard() {
  return apiFetch<SocialDashboard>('/marketing/social/dashboard');
}

export async function fetchSocialPosts(page = 1) {
  return apiFetch<{ items: SocialPostSummary[]; total: number; pages: number }>(
    `/marketing/social/posts?page=${page}`,
  );
}

export async function createSocialPost(payload: Record<string, unknown>) {
  return apiFetch<SocialPostSummary>('/marketing/social/posts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchSocialPostReadiness(postId: string) {
  return apiFetch<ReadinessResult>(`/marketing/social/posts/${postId}/readiness`, { method: 'POST' });
}

export const socialQueries = {
  dashboard: () => ({ queryKey: socialQueryKeys.dashboard(), queryFn: () => fetchSocialDashboard() }),
  list: (page = 1) => ({ queryKey: socialQueryKeys.list(page), queryFn: () => fetchSocialPosts(page) }),
};
