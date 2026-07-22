'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { canViewMarketingAI } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';

import {
  AIPageShell,
  PredictionSkeleton,
  AIConfidenceBadge,
  AIEmptyState,
} from '../_components/ai-shell';

export default function MarketingAIPredictionsPage() {
  const t = useTranslations('marketing.ai.predictions');
  const tCommon = useTranslations('common');
  const { user, loading: authLoading } = useAuth();
  const canView = canViewMarketingAI(user);

  const predictionsQuery = useQuery({
    ...marketingQueries.aiPredictions(),
    enabled: !authLoading && canView,
  });

  if (authLoading) {
    return (
      <AIPageShell title={t('title')} subtitle={t('subtitle')}>
        <LoadingState label={tCommon('loading')} />
      </AIPageShell>
    );
  }

  if (!canView) {
    return (
      <AIPageShell title={t('title')} subtitle={t('subtitle')}>
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </AIPageShell>
    );
  }

  return (
    <AIPageShell title={t('title')} subtitle={t('subtitle')}>
      <p className="mkt-ai-panel__note">{t('frameworkNote')}</p>
      {predictionsQuery.isLoading ? (
        <PredictionSkeleton />
      ) : predictionsQuery.isError ? (
        <ErrorState
          title={t('loadFailed')}
          message={predictionsQuery.error?.message}
          action={
            <Button type="button" onClick={() => void predictionsQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      ) : predictionsQuery.data?.frameworks.length === 0 ? (
        <AIEmptyState title={t('noPredictions')} description={t('noPredictionsHint')} />
      ) : (
        <div className="mkt-ai-predictions">
          {predictionsQuery.data?.frameworks.map((fw) => (
            <section key={fw.framework} className="mkt-ai-panel">
              <div className="mkt-ai-panel__header">
                <h2>{fw.label}</h2>
                {!fw.model_connected ? <span className="mkt-ai-tag">{t('modelNotConnected')}</span> : null}
              </div>
              <p className="mkt-ai-panel__desc">{fw.description}</p>
              <ul className="mkt-ai-prediction-slots">
                {fw.items.map((item) => (
                  <li key={item.prediction_key} className="mkt-ai-prediction-slots__item">
                    <span>{item.label}</span>
                    <span className="mkt-ai-prediction-slots__value">
                      {item.value ?? t('unknown')}
                    </span>
                    <AIConfidenceBadge confidence={item.confidence} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </AIPageShell>
  );
}
