'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState } from '@investhome/ui';

import { audienceQueries } from '@/workspaces/marketing/hooks/use-audiences';
import { segmentQueries } from '@/workspaces/marketing/hooks/use-segments';

export default function AudienceSegmentsPage() {
  const params = useParams<{ audienceId: string }>();
  const t = useTranslations('marketing.audiences.segments');
  const tCommon = useTranslations('marketing.common');
  const detailQuery = useQuery(audienceQueries.detail(params.audienceId));
  const segmentsQuery = useQuery(segmentQueries.list());

  if (detailQuery.isLoading || segmentsQuery.isLoading) return <LoadingState label={tCommon('loading')} />;

  const segmentIds = detailQuery.data?.segment_ids ?? [];
  const linkedSegments = (segmentsQuery.data?.items ?? []).filter((segment) => segmentIds.includes(segment.id));

  if (segmentIds.length === 0) {
    return <EmptyState title={t('empty')} description={t('emptyDescription')} />;
  }

  if (linkedSegments.length === 0) {
    return (
      <section className="marketing-detail-panel">
        <p>{t('unresolved', { count: segmentIds.length })}</p>
        <ul>
          {segmentIds.map((id) => (
            <li key={id}>{id}</li>
          ))}
        </ul>
      </section>
    );
  }

  return (
    <section className="marketing-detail-panel">
      <table className="admin-table">
        <thead>
          <tr>
            <th>{t('name')}</th>
            <th>{t('type')}</th>
            <th>{t('size')}</th>
          </tr>
        </thead>
        <tbody>
          {linkedSegments.map((segment) => (
            <tr key={segment.id}>
              <td>
                <Link href={`/workspaces/marketing/segments/${segment.id}` as Route}>{segment.name}</Link>
              </td>
              <td>{segment.segment_type}</td>
              <td>{segment.calculated_size ?? tCommon('notCalculated')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
