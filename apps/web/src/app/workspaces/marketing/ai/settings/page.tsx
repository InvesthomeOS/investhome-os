'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState } from '@investhome/ui';

import { canManageAISettings, canViewMarketingAI } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';

import { AIPageShell } from '../_components/ai-shell';

export default function MarketingAISettingsPage() {
  const t = useTranslations('marketing.ai.settings');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const canView = canViewMarketingAI(user);
  const canManage = canManageAISettings(user);

  const settingsQuery = useQuery({
    ...marketingQueries.aiSettings(),
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
      {settingsQuery.isLoading ? (
        <p>{tCommon('loading')}</p>
      ) : settingsQuery.isError ? (
        <ErrorState
          title={t('loadFailed')}
          message={settingsQuery.error?.message}
          action={
            <Button type="button" onClick={() => void settingsQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      ) : settingsQuery.data ? (
        <div className="mkt-ai-settings">
          <dl className="mkt-ai-settings__list">
            <div>
              <dt>{t('copilotEnabled')}</dt>
              <dd>{settingsQuery.data.copilot_enabled ? t('yes') : t('no')}</dd>
            </div>
            <div>
              <dt>{t('predictionsEnabled')}</dt>
              <dd>{settingsQuery.data.predictions_enabled ? t('yes') : t('no')}</dd>
            </div>
            <div>
              <dt>{t('anomalyDetection')}</dt>
              <dd>{settingsQuery.data.anomaly_detection_enabled ? t('yes') : t('no')}</dd>
            </div>
            <div>
              <dt>{t('modelPipeline')}</dt>
              <dd>{settingsQuery.data.model_pipeline_connected ? t('connected') : t('notConnected')}</dd>
            </div>
            <div>
              <dt>{t('defaultConfidence')}</dt>
              <dd>{settingsQuery.data.default_confidence}</dd>
            </div>
          </dl>
          {!canManage ? <p className="mkt-ai-settings__readonly">{t('readOnly')}</p> : null}
        </div>
      ) : null}
    </AIPageShell>
  );
}
