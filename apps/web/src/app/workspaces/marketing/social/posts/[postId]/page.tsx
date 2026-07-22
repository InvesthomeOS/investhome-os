'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { LoadingState, StatusChip } from '@investhome/ui';

import { apiFetch } from '@/lib/api/client';

export default function SocialPostDetailPage() {
  const params = useParams<{ postId: string }>();
  const t = useTranslations('marketing.channels.social');
  const tCommon = useTranslations('marketing.common');

  const query = useQuery({
    queryKey: ['marketing', 'social', 'detail', params.postId],
    queryFn: () => apiFetch<{ id: string; title: string | null; status: string; readiness_state: string; body_text: string | null }>(
      `/marketing/social/posts/${params.postId}`,
    ),
  });

  if (query.isLoading) return <LoadingState label={tCommon('loading')} />;
  const post = query.data;

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{post?.title ?? t('columns.name')}</h1>
        <StatusChip>{post?.status}</StatusChip>
        <StatusChip tone={post?.readiness_state === 'blocked' ? 'danger' : 'default'}>{post?.readiness_state}</StatusChip>
      </header>
      <p>{post?.body_text}</p>
    </main>
  );
}
