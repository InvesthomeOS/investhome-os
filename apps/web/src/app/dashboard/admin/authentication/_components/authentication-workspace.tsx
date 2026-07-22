'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { fetchMfaPolicy, fetchSsoProviders, type ProviderStatus, type SecurityKpi } from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { KpiGrid, ProviderTable, SecSection } from '../../_components/sec-ui';

export function AuthenticationWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [sso, setSso] = useState<ProviderStatus[]>([]);
  const [mfaMethods, setMfaMethods] = useState<ProviderStatus[]>([]);
  const [enforcement, setEnforcement] = useState('optional');
  const [adoption, setAdoption] = useState<SecurityKpi | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ssoRes, mfaRes] = await Promise.all([fetchSsoProviders(), fetchMfaPolicy()]);
      setSso(ssoRes.items);
      setMfaMethods(mfaRes.methods);
      setEnforcement(mfaRes.enforcement);
      setAdoption(mfaRes.adoption);
    } catch {
      setSso([]);
      setMfaMethods([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (!hasPermission(user, 'security', 'view')) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [authLoading, load, router, user]);

  return (
    <main className="dashboard" data-sec-workspace="authentication">
      <PageHeader eyebrow={t('eyebrow')} title={t('authTitle')} subtitle={t('authSubtitle')} />
      {loading ? <p>{t('loading')}</p> : null}
      {adoption ? <KpiGrid items={[adoption]} /> : null}
      <SecSection title={t('mfaTitle')} description={t('mfaSubtitle', { enforcement })}>
        <ProviderTable items={mfaMethods} emptyLabel={t('emptyProviders')} />
        <p className="sec-note">{t('mfaHonestNote')}</p>
      </SecSection>
      <SecSection title={t('ssoTitle')} description={t('ssoSubtitle')}>
        <ProviderTable items={sso} emptyLabel={t('emptyProviders')} />
        <p className="sec-note">{t('ssoHonestNote')}</p>
      </SecSection>
    </main>
  );
}
