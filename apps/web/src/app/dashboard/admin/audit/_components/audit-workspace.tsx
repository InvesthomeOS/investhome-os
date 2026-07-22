'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Button, PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { exportAudit, fetchAuditCategories } from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { SecSection } from '../../_components/sec-ui';
import { useAdminToast } from '../../_components/use-admin-toast';

export function AuditCenterWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { notifySuccess, notifyError } = useAdminToast();
  const [categories, setCategories] = useState<Array<{ id: string; actions: string[] }>>([]);
  const [exportTotal, setExportTotal] = useState<number | null>(null);
  const [exportNote, setExportNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetchAuditCategories();
      setCategories(res.categories);
    } catch (err) {
      notifyError(err, t('loadError'));
    }
  }, [notifyError, t]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (!hasPermission(user, 'activity', 'view')) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [authLoading, load, router, user]);

  return (
    <main className="dashboard" data-sec-workspace="audit">
      <PageHeader
        eyebrow={t('eyebrow')}
        title={t('auditTitle')}
        subtitle={t('auditSubtitle')}
        actions={
          <Link href="/dashboard/activity" className="button button--ghost">
            {t('openActivity')}
          </Link>
        }
      />
      <SecSection title={t('auditCategories')} description={t('auditCategoriesHint')}>
        <div className="sec-card-grid">
          {categories.map((cat) => (
            <article key={cat.id} className="sec-card">
              <h3>{cat.id}</h3>
              <p>{cat.actions.join(', ')}</p>
            </article>
          ))}
        </div>
      </SecSection>
      <SecSection
        title={t('auditExport')}
        description={t('auditExportHint')}
        actions={
          <Button
            type="button"
            onClick={async () => {
              try {
                const res = await exportAudit({});
                setExportTotal(res.total);
                setExportNote(res.note);
                notifySuccess(t('auditExported', { count: res.total }));
              } catch (err) {
                notifyError(err, t('saveFailed'));
              }
            }}
          >
            {t('exportAudit')}
          </Button>
        }
      >
        {exportTotal !== null ? (
          <p>
            {t('auditExported', { count: exportTotal })}
            {exportNote ? ` — ${exportNote}` : ''}
          </p>
        ) : (
          <p className="sec-empty">{t('auditExportReady')}</p>
        )}
      </SecSection>
    </main>
  );
}
