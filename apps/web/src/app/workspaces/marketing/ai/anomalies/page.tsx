'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState } from '@investhome/ui';

import { canViewMarketingAI } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';

import { AIPageShell, AIConfidenceBadge, AIEmptyState } from '../_components/ai-shell';

export default function MarketingAIAnomaliesPage() {
  const t = useTranslations('marketing.ai.anomalies');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const canView = canViewMarketingAI(user);

  const anomaliesQuery = useQuery({
    ...marketingQueries.aiAnomalies(),
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
      {anomaliesQuery.isLoading ? (
        <p>{tCommon('loading')}</p>
      ) : anomaliesQuery.isError ? (
        <ErrorState
          title={t('loadFailed')}
          message={anomaliesQuery.error?.message}
          action={
            <Button type="button" onClick={() => void anomaliesQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      ) : anomaliesQuery.data?.items.length === 0 ? (
        <AIEmptyState title={t('noAnomalies')} description={t('noAnomaliesHint')} />
      ) : (
        <ul className="mkt-ai-anomalies">
          {anomaliesQuery.data?.items.map((anomaly) => (
            <li key={anomaly.id} className={`mkt-ai-anomalies__item mkt-ai-anomalies__item--${anomaly.severity}`}>
              <div className="mkt-ai-anomalies__header">
                <span>{anomaly.anomaly_type}</span>
                <AIConfidenceBadge confidence={anomaly.confidence} />
              </div>
              <h3>{anomaly.title}</h3>
              <p>{anomaly.description}</p>
            </li>
          ))}
        </ul>
      )}
    </AIPageShell>
  );
}
