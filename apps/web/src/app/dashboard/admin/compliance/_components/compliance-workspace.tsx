'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { fetchCompliance, fetchDataGovernance } from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { SecSection, StatusBadge } from '../../_components/sec-ui';

type DictList = Array<Record<string, unknown>>;

export function ComplianceWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [compliance, setCompliance] = useState<Record<string, unknown> | null>(null);
  const [governance, setGovernance] = useState<Record<string, unknown> | null>(null);

  const load = useCallback(async () => {
    const [c, g] = await Promise.all([fetchCompliance(), fetchDataGovernance()]);
    setCompliance(c);
    setGovernance(g);
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (!hasPermission(user, 'security', 'view') && !hasPermission(user, 'compliance', 'view')) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [authLoading, load, router, user]);

  const list = (key: string, source: Record<string, unknown> | null): DictList =>
    Array.isArray(source?.[key]) ? (source[key] as DictList) : [];

  return (
    <main className="dashboard" data-sec-workspace="compliance">
      <PageHeader eyebrow={t('eyebrow')} title={t('complianceTitle')} subtitle={t('complianceSubtitle')} />
      <SecSection title={t('policiesTitle')}>
        <div className="sec-card-grid">
          {list('policies', compliance).map((p) => (
            <article key={String(p.id)} className="sec-card">
              <h3>{String(p.title ?? p.id)}</h3>
              <StatusBadge status={String(p.status ?? 'draft')} />
            </article>
          ))}
        </div>
      </SecSection>
      <SecSection
        title={t('retentionTitle')}
        description={t('retentionSubtitle')}
        actions={
          <Link href={String(compliance?.knowledge_retention_link ?? '/dashboard/documents')}>
            {t('openKnowledge')}
          </Link>
        }
      >
        {list('retention', compliance).length === 0 ? (
          <p className="sec-empty">{t('retentionEmpty')}</p>
        ) : (
          <ul className="sec-plain-list">
            {list('retention', compliance).map((r) => (
              <li key={String(r.id)}>
                {String(r.name)} — <StatusBadge status={String(r.status ?? 'foundation')} />
              </li>
            ))}
          </ul>
        )}
      </SecSection>
      <SecSection title={t('legalHoldTitle')}>
        {list('legal_holds', compliance).length === 0 ? (
          <p className="sec-empty">{t('legalHoldEmpty')}</p>
        ) : (
          <ul className="sec-plain-list">
            {list('legal_holds', compliance).map((h) => (
              <li key={String(h.id)}>
                {String(h.document_id)} — <StatusBadge status={String(h.status)} />
              </li>
            ))}
          </ul>
        )}
      </SecSection>
      <SecSection title={t('governanceTitle')} description={t('governanceSubtitle')}>
        <div className="sec-card-grid">
          {list('classifications', governance).map((c) => (
            <article key={String(c.level)} className="sec-card">
              <h3>{String(c.level)}</h3>
              <p>{String(c.description)}</p>
            </article>
          ))}
        </div>
        <h3 className="sec-subhead">{t('sensitiveFields')}</h3>
        <ul className="sec-plain-list">
          {list('sensitive_fields', governance).map((f) => (
            <li key={String(f.field)}>
              <code>{String(f.field)}</code> — {String(f.masking)}
            </li>
          ))}
        </ul>
      </SecSection>
      {Array.isArray(compliance?.notes) ? (
        <p className="sec-note">{(compliance.notes as string[]).join(' ')}</p>
      ) : null}
    </main>
  );
}
