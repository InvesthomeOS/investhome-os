'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState } from '@investhome/ui';

import { canViewMarketingAI } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';
import { useAIUiStore } from '@/workspaces/marketing/stores/ai-ui-store';

import {
  AIPageShell,
  InsightSkeleton,
  AIConfidenceBadge,
  AIEmptyState,
} from '../_components/ai-shell';

const CATEGORIES = [
  'campaign',
  'country',
  'project',
  'channel',
  'creative',
  'landing_page',
  'form',
  'revenue',
  'audience',
  'budget',
  'automation',
] as const;

export default function MarketingAIInsightsPage() {
  const t = useTranslations('marketing.ai.insights');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const canView = canViewMarketingAI(user);
  const categoryFilter = useAIUiStore((s) => s.insightCategoryFilter);
  const setCategoryFilter = useAIUiStore((s) => s.setInsightCategoryFilter);

  const insightsQuery = useQuery({
    ...marketingQueries.aiInsights(categoryFilter ?? undefined),
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
      <div className="mkt-ai-filters">
        <button
          type="button"
          className={categoryFilter === null ? 'mkt-ai-filter mkt-ai-filter--active' : 'mkt-ai-filter'}
          onClick={() => setCategoryFilter(null)}
        >
          {t('allCategories')}
        </button>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            className={categoryFilter === cat ? 'mkt-ai-filter mkt-ai-filter--active' : 'mkt-ai-filter'}
            onClick={() => setCategoryFilter(cat)}
          >
            {t(`categories.${cat}` as 'categories.campaign')}
          </button>
        ))}
      </div>

      {insightsQuery.isLoading ? (
        <InsightSkeleton />
      ) : insightsQuery.isError ? (
        <ErrorState
          title={t('loadFailed')}
          message={insightsQuery.error?.message}
          action={
            <Button type="button" onClick={() => void insightsQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      ) : insightsQuery.data?.items.length === 0 ? (
        <AIEmptyState title={t('noInsights')} description={t('noInsightsHint')} />
      ) : (
        <ul className="mkt-ai-insights">
          {insightsQuery.data?.items.map((insight) => (
            <li key={insight.id} className={`mkt-ai-insights__item mkt-ai-insights__item--${insight.severity}`}>
              <div className="mkt-ai-insights__header">
                <span className="mkt-ai-insights__category">{insight.category}</span>
                <AIConfidenceBadge confidence={insight.confidence} />
              </div>
              <h3>{insight.title}</h3>
              <p>{insight.summary}</p>
            </li>
          ))}
        </ul>
      )}
    </AIPageShell>
  );
}
