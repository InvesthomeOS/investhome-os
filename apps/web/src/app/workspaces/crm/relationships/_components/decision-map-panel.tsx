'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { relationshipQueries } from '@/workspaces/crm/hooks/use-relationships';

type Props = { companyId: string };

export function DecisionMapPanel({ companyId }: Props) {
  const t = useTranslations('crm.relationships.decisionMap');

  const mapQuery = useQuery(relationshipQueries.decisionMap(companyId));

  if (mapQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (mapQuery.isError) return <ErrorState title={t('loadFailed')} message={t('loadFailed')} />;

  const roles = mapQuery.data?.roles ?? [];

  if (roles.length === 0) {
    return <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />;
  }

  return (
    <div className="crm-decision-map">
      <h3>{t('title')}</h3>
      <ul>
        {roles.map((role) => (
          <li key={String(role.id)}>
            <strong>{String(role.contact_display_name ?? role.contact_id)}</strong>
            <span>{String(role.role_type)}</span>
            <span>{t('influence', { level: Number(role.influence_level) })}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
