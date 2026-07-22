'use client';

import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState } from '@investhome/ui';

import { audienceQueries } from '@/workspaces/marketing/hooks/use-audiences';

export default function AudienceMembersPage() {
  const params = useParams<{ audienceId: string }>();
  const t = useTranslations('marketing.audiences');
  const tCommon = useTranslations('marketing.common');
  const membersQuery = useQuery(audienceQueries.members(params.audienceId));

  if (membersQuery.isLoading) return <LoadingState label={tCommon('loading')} />;

  const items = membersQuery.data?.items ?? [];
  if (items.length === 0) return <EmptyState title={t('members.empty')} />;

  return (
    <section className="marketing-detail-panel">
      <table className="admin-table">
        <thead>
          <tr>
            <th>{t('members.contact')}</th>
            <th>{t('members.included')}</th>
            <th>{t('members.reason')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((m) => (
            <tr key={m.id}>
              <td>{m.contact_id ?? m.company_id}</td>
              <td>{m.is_included ? t('members.yes') : t('members.no')}</td>
              <td>
                {m.is_included
                  ? String(m.inclusion_source ?? '')
                  : String(
                      (m.explainability_json as { reason?: string } | null)?.reason ??
                        m.exclusion_reason ??
                        t('members.unknown'),
                    )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
