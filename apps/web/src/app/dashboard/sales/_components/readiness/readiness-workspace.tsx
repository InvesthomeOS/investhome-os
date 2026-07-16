'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import {
  fetchReadinessCases,
  fetchReadinessKpis,
  type ReadinessCase,
  type ReadinessDashboardKpis,
  type ReadinessViewName,
} from '@/lib/api/sales-readiness';
import { useAuth } from '@/lib/auth/auth-context';
import { useReadinessLabels } from '@/lib/i18n/sales-readiness-labels';

import { ReadinessDetailDrawer } from './readiness-detail-drawer';
import { ReadinessHome } from './readiness-home';
import { ReadinessList } from './readiness-list';

export function ReadinessWorkspace() {
  const t = useTranslations('salesReadiness');
  const { user } = useAuth();
  const { viewOptions, getViewLabel } = useReadinessLabels();

  const [kpis, setKpis] = useState<ReadinessDashboardKpis | null>(null);
  const [items, setItems] = useState<ReadinessCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<ReadinessViewName>('overview');
  const [selected, setSelected] = useState<ReadinessCase | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const canView = user ? hasPermission(user, 'sales', 'view_readiness') : false;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [kpiData, listData] = await Promise.all([
        fetchReadinessKpis(),
        fetchReadinessCases({ view: activeView === 'overview' ? undefined : activeView }),
      ]);
      setKpis(kpiData);
      setItems(listData.items);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [activeView, t]);

  useEffect(() => {
    if (canView) void loadData();
  }, [canView, loadData]);

  if (!canView) {
    return <ErrorState title={t('permissionDenied')} message={t('permissionDenied')} />;
  }

  return (
    <div className="sales-readiness-workspace">
      <header className="sales-readiness-workspace__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <Link href={'/dashboard/sales' as Route} className="leads__button leads__button--secondary">
          {t('backToSales')}
        </Link>
      </header>

      <ReadinessHome
        kpis={kpis}
        loading={loading}
        activeView={activeView}
        onSelectView={setActiveView}
      />

      <nav className="sales-readiness-workspace__views" aria-label={t('viewsLabel')}>
        {viewOptions.map((view) => (
          <Button
            key={view}
            variant={activeView === view ? 'primary' : 'secondary'}
            onClick={() => setActiveView(view)}
          >
            {getViewLabel(view)}
          </Button>
        ))}
      </nav>

      {loading && <LoadingState label={t('loading')} />}
      {error && <ErrorState title={error} message={error} onRetry={() => void loadData()} />}
      {!loading && !error && (
        <ReadinessList
          items={items}
          selectedId={selected?.id ?? null}
          onSelect={(item) => {
            setSelected(item);
            setDrawerOpen(true);
          }}
        />
      )}

      <ReadinessDetailDrawer
        caseId={selected?.id ?? null}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onUpdated={(updated) => {
          setSelected(updated);
          void loadData();
        }}
      />
    </div>
  );
}
