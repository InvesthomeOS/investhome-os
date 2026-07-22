'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { fetchSecurityDashboard, type SecurityDashboard } from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { KpiGrid, SecSection } from '../../_components/sec-ui';

export function SecurityDashboardWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState<SecurityDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchSecurityDashboard());
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (!hasPermission(user, 'security', 'view') && !hasPermission(user, 'users', 'view')) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [authLoading, load, router, user]);

  return (
    <main className="dashboard" data-sec-workspace="security">
      <PageHeader eyebrow={t('eyebrow')} title={t('dashboardTitle')} subtitle={t('dashboardSubtitle')} />
      {loading ? <p>{t('loading')}</p> : null}
      {error ? <p className="sec-error">{error}</p> : null}
      {data ? (
        <>
          <KpiGrid items={data.kpis} />
          <SecSection title={t('alertsTitle')} description={t('alertsSubtitle')}>
            {data.alerts.length === 0 ? (
              <p className="sec-empty">{t('noAlerts')}</p>
            ) : (
              <ul className="sec-alert-list">
                {data.alerts.map((alert) => (
                  <li key={alert.title} className={`sec-alert sec-alert--${alert.severity}`}>
                    <strong>{alert.title}</strong>
                    <span>{alert.detail}</span>
                  </li>
                ))}
              </ul>
            )}
          </SecSection>
          <p className="sec-meta">
            {t('generatedAt')}: {new Date(data.generated_at).toLocaleString()}
          </p>
        </>
      ) : null}
    </main>
  );
}
