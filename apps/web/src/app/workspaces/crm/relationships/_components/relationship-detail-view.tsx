'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { crmLabel } from '@/lib/crm/crm-labels';
import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  relationshipQueries,
  relationshipQueryKeys,
  relationshipMutations,
} from '@/workspaces/crm/hooks/use-relationships';
import { getScoreBandColor } from '@/workspaces/crm/stores/relationship-graph-ui-store';

import { WarmIntroPanel } from './warm-intro-panel';

type Props = { relationshipId: string };

const TABS = ['overview', 'timeline', 'interactions', 'scores', 'intro'] as const;

export function RelationshipDetailView({ relationshipId }: Props) {
  const t = useTranslations('crm.relationships.detail');
  const tTypes = useTranslations('crm.relationships.types');
  const tCategories = useTranslations('crm.relationships.categories');
  const tStrengths = useTranslations('crm.relationships.strengths');
  const tStatuses = useTranslations('crm.relationships.filters');
  const tCommon = useTranslations('common');
  const { authLoading, user, canRead } = useCrmAccess();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>('overview');

  const detailQuery = useQuery({
    ...relationshipQueries.detail(relationshipId),
    enabled: !authLoading && canRead && Boolean(relationshipId),
  });

  const scoreMutation = useMutation({
    mutationFn: () => relationshipMutations.calculateScores(relationshipId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: relationshipQueryKeys.detail(relationshipId) }),
  });

  if (authLoading) return <LoadingState label={tCommon('loading')} />;
  if (!canRead) return <ErrorState title={t('accessDenied')} message={t('accessDenied')} />;
  if (detailQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={detailQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void detailQuery.refetch()}>
            {t('loadFailed')}
          </Button>
        }
      />
    );
  }

  const rel = detailQuery.data;

  return (
    <div className="crm-relationship-detail">
      <header className="crm-workspace-header">
        <div>
          <Link href="/workspaces/crm/relationships">{t('back')}</Link>
          <h1>
            {rel.source_display_name} → {rel.target_display_name}
          </h1>
          <p>
            {crmLabel(tTypes, rel.relationship_type)}
            {rel.reciprocal_type ? ` / ${crmLabel(tTypes, rel.reciprocal_type)}` : ''}
          </p>
        </div>
        <div className="crm-workspace-actions">
          {canUpdateCrm(user) && (
            <Button onClick={() => scoreMutation.mutate()} disabled={scoreMutation.isPending}>
              {t('recalculateScores')}
            </Button>
          )}
        </div>
      </header>

      <nav className="crm-detail-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? 'active' : ''}
            onClick={() => setActiveTab(tab)}
          >
            {t(`tabs.${tab}`)}
          </button>
        ))}
      </nav>

      {activeTab === 'overview' && (
        <section className="crm-detail-overview">
          <div className="crm-detail-grid">
            <div>
              <h3>{t('source')}</h3>
              <p>{rel.source_display_name}</p>
            </div>
            <div>
              <h3>{t('target')}</h3>
              <p>{rel.target_display_name}</p>
            </div>
            <div>
              <h3>{t('category')}</h3>
              <StatusChip>{crmLabel(tCategories, rel.category)}</StatusChip>
            </div>
            <div>
              <h3>{t('strength')}</h3>
              <StatusChip>{crmLabel(tStrengths, rel.strength)}</StatusChip>
            </div>
            <div>
              <h3>{t('status')}</h3>
              <StatusChip tone={rel.status === 'active' ? 'success' : 'default'}>
                {crmLabel(tStatuses, rel.status)}
              </StatusChip>
            </div>
            {rel.is_confidential && <StatusChip tone="warning">{t('confidential')}</StatusChip>}
            {rel.is_verified && <StatusChip tone="success">{t('verified')}</StatusChip>}
          </div>
          {rel.notes && (
            <div>
              <h3>{t('notes')}</h3>
              <p>{rel.notes}</p>
            </div>
          )}
        </section>
      )}

      {activeTab === 'timeline' && (
        <EmptyState title={t('timelineEmpty')} description={t('timelineHint')} />
      )}

      {activeTab === 'interactions' && (
        <EmptyState title={t('interactionsEmpty')} description={t('interactionsHint')} />
      )}

      {activeTab === 'scores' && (
        <section className="crm-score-breakdown">
          {(['relationship_score', 'engagement_score', 'influence_score', 'trust_score', 'business_value_score', 'risk_score'] as const).map(
            (key) => (
              <div key={key} className="crm-score-item">
                <span>{t(`scores.${key}`)}</span>
                <strong style={{ color: getScoreBandColor(rel[key]) }}>{rel[key]}</strong>
              </div>
            ),
          )}
        </section>
      )}

      {activeTab === 'intro' && (
        <WarmIntroPanel
          sourceEntityType={rel.source_entity_type}
          sourceEntityId={rel.source_entity_id}
          defaultTargetType={rel.target_entity_type}
          defaultTargetId={rel.target_entity_id}
        />
      )}
    </div>
  );
}
