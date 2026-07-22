'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { fetchSecretProviders, type ProviderStatus } from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { ProviderTable, SecSection } from '../../_components/sec-ui';

export function SecretsWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<ProviderStatus[]>([]);

  const load = useCallback(async () => {
    const res = await fetchSecretProviders();
    setItems(res.items);
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
    <main className="dashboard" data-sec-workspace="secrets">
      <PageHeader eyebrow={t('eyebrow')} title={t('secretsTitle')} subtitle={t('secretsSubtitle')} />
      <SecSection title={t('secretProviders')} description={t('secretsNeverShown')}>
        <ProviderTable items={items} emptyLabel={t('emptyProviders')} />
      </SecSection>
    </main>
  );
}
