'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  fetchAutomationIntegrations,
  type AutomationIntegrationItem,
} from '@/lib/api/automation-center';

import { AutomationShell } from './automation-shell';

export function IntegrationsPanelWorkspace() {
  const t = useTranslations('automation');
  const tCommon = useTranslations('common');
  const [items, setItems] = useState<AutomationIntegrationItem[]>([]);
  const [state, setState] = useState<'loading' | 'error' | 'success'>('loading');

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    void fetchAutomationIntegrations()
      .then((response) => {
        if (!cancelled) {
          setItems(response.items);
          setState('success');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setState('error');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AutomationShell title={t('integrations.title')} subtitle={t('integrations.subtitle')}>
      <div className="automation-center__banner" role="note">
        {t('integrations.envNote')}
      </div>

      {state === 'loading' ? <LoadingState label={tCommon('loading')} /> : null}
      {state === 'error' ? <ErrorState title={t('loadError')} message={t('loadErrorHint')} /> : null}
      {state === 'success' && items.length === 0 ? (
        <EmptyState title={t('empty.integrations')} description={t('empty.integrationsHint')} />
      ) : null}

      {state === 'success' && items.length > 0 ? (
        <div className="automation-center__integration-grid">
          {items.map((item) => (
            <article key={item.id} className="automation-center__integration" data-integration={item.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', alignItems: 'center' }}>
                <h3>{item.name}</h3>
                <StatusChip
                  tone={
                    item.status === 'connected'
                      ? 'success'
                      : item.status === 'configured'
                        ? 'warning'
                        : 'default'
                  }
                >
                  {t.has(`integrationStatus.${item.status}`)
                    ? t(`integrationStatus.${item.status}`)
                    : item.status}
                </StatusChip>
              </div>
              <p>{item.notes}</p>
              {item.feature_flag ? (
                <p>
                  {t('integrations.featureFlag')}: {item.feature_flag}
                </p>
              ) : null}
              {item.env_keys.length > 0 ? (
                <p>
                  {t('integrations.envKeys')}: {item.env_keys.join(', ')}
                </p>
              ) : null}
              {item.href ? (
                <p>
                  <Link href={item.href as Route} className="automation-center__panel-link">
                    {t('integrations.openRelated')}
                  </Link>
                </p>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}
    </AutomationShell>
  );
}
