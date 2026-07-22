'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState } from '@investhome/ui';

import { canViewMarketingAI } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';

import { AIPageShell, AIConfidenceBadge, AIEmptyState } from '../_components/ai-shell';

export default function MarketingAIRecommendationsPage() {
  const t = useTranslations('marketing.ai.recommendations');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const canView = canViewMarketingAI(user);

  const recsQuery = useQuery({
    ...marketingQueries.aiRecommendations(),
    enabled: canView,
  });

  if (!canView) {
    return (
      <AIPageShell title={t('title')} subtitle={t('subtitle')}>
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </AIPageShell>
    );
  }

  return (
    <AIPageShell title={t('title')} subtitle={t('subtitle')}>
      <p className="mkt-ai-panel__note">{t('evidenceNote')}</p>
      {recsQuery.isLoading ? (
        <p>{tCommon('loading')}</p>
      ) : recsQuery.isError ? (
        <ErrorState
          title={t('loadFailed')}
          message={recsQuery.error?.message}
          action={
            <Button type="button" onClick={() => void recsQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      ) : recsQuery.data?.items.length === 0 ? (
        <AIEmptyState title={t('noRecommendations')} description={t('noRecommendationsHint')} />
      ) : (
        <ul className="mkt-ai-recommendations">
          {recsQuery.data?.items.map((rec) => (
            <li key={rec.id} className="mkt-ai-recommendations__item">
              <div className="mkt-ai-recommendations__header">
                <span className="mkt-ai-recommendations__type">{rec.recommendation_type}</span>
                <AIConfidenceBadge confidence={rec.confidence} />
              </div>
              <h3>{rec.title}</h3>
              <p>{rec.rationale}</p>
              {rec.requires_evidence && !rec.evidence_refs?.length ? (
                <p className="mkt-ai-recommendations__warning">{t('missingEvidence')}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </AIPageShell>
  );
}
