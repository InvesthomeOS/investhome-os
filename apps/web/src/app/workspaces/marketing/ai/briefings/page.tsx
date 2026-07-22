'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState } from '@investhome/ui';

import { canViewMarketingAI } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';
import { useAIUiStore } from '@/workspaces/marketing/stores/ai-ui-store';

import { AIPageShell, AIConfidenceBadge, AIEmptyState } from '../_components/ai-shell';

const PERIODS = ['daily', 'weekly', 'monthly', 'quarterly', 'board'] as const;

export default function MarketingAIBriefingsPage() {
  const t = useTranslations('marketing.ai.briefings');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const canView = canViewMarketingAI(user);
  const period = useAIUiStore((s) => s.briefingPeriod);
  const setPeriod = useAIUiStore((s) => s.setBriefingPeriod);

  const briefingQuery = useQuery({
    ...marketingQueries.aiBriefing(period),
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
        {PERIODS.map((p) => (
          <button
            key={p}
            type="button"
            className={period === p ? 'mkt-ai-filter mkt-ai-filter--active' : 'mkt-ai-filter'}
            onClick={() => setPeriod(p)}
          >
            {t(`periods.${p}` as 'periods.daily')}
          </button>
        ))}
      </div>

      {briefingQuery.isLoading ? (
        <p>{tCommon('loading')}</p>
      ) : briefingQuery.isError ? (
        <ErrorState
          title={t('loadFailed')}
          message={briefingQuery.error?.message}
          action={
            <Button type="button" onClick={() => void briefingQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      ) : briefingQuery.data?.briefing.confidence === 'unknown' ? (
        <AIEmptyState title={t('unknown')} description={briefingQuery.data.briefing.summary} />
      ) : (
        <article className="mkt-ai-briefing">
          <div className="mkt-ai-briefing__header">
            <h2>{briefingQuery.data?.briefing.title}</h2>
            <AIConfidenceBadge confidence={briefingQuery.data?.briefing.confidence ?? 'unknown'} />
          </div>
          <p>{briefingQuery.data?.briefing.summary}</p>
          {(briefingQuery.data?.briefing.sections ?? []).map((section) => (
            <section key={String(section.key)} className="mkt-ai-briefing__section">
              <h3>{String(section.title ?? section.key)}</h3>
              <p>{String(section.content ?? '')}</p>
            </section>
          ))}
        </article>
      )}
    </AIPageShell>
  );
}
