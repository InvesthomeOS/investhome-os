'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  createKnowledgeRetention,
  fetchKnowledgeOverview,
  fetchKnowledgeRetention,
  type KnowledgeMetricValue,
  type KnowledgeRetentionPolicy,
} from '@/lib/api/knowledge';
import { useAuth } from '@/lib/auth/auth-context';
import { canManageKnowledge } from '@/lib/knowledge/knowledge-permissions';
import { KnowledgeHubShell } from '../_components/knowledge-hub-shell';

export default function KnowledgeRetentionPage() {
  const t = useTranslations('knowledge');
  const { user } = useAuth();
  const canManage = canManageKnowledge(user);
  const [policies, setPolicies] = useState<KnowledgeRetentionPolicy[]>([]);
  const [expiring, setExpiring] = useState<KnowledgeMetricValue | null>(null);
  const [name, setName] = useState('');
  const [days, setDays] = useState('365');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [pols, overview] = await Promise.all([
        fetchKnowledgeRetention(),
        fetchKnowledgeOverview().catch(() => null),
      ]);
      setPolicies(pols);
      setExpiring(overview?.expiring_soon ?? null);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      await createKnowledgeRetention({
        name: name.trim(),
        retention_days: Number(days) || 365,
        action_on_expiry: 'notify',
      });
      setName('');
      await load();
    } catch {
      setError(t('retention.createError'));
    }
  };

  return (
    <KnowledgeHubShell title={t('nav.retention')} subtitle={t('retention.subtitle')}>
      <section className="documents-overview" aria-label={t('retention.monitoring')}>
        <Link href={'/dashboard/knowledge/review?reason=expiring' as Route} className="documents-overview__card">
          <span className="documents-overview__label">{t('widgets.expiring')}</span>
          <strong className="documents-overview__value">
            {expiring?.available && expiring.value != null ? expiring.value : '—'}
          </strong>
        </Link>
        <p className="knowledge-hub__note">{t('retention.alertNote')}</p>
      </section>

      {canManage && (
        <div className="knowledge-hub__form-row">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('retention.policyName')}
            aria-label={t('retention.policyName')}
          />
          <input
            type="number"
            min={1}
            value={days}
            onChange={(e) => setDays(e.target.value)}
            aria-label={t('retention.days')}
          />
          <button type="button" className="button" onClick={() => void handleCreate()}>
            {t('retention.create')}
          </button>
        </div>
      )}

      {loading && <p>{t('loading')}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && policies.length === 0 && <p>{t('retention.empty')}</p>}
      <ul className="knowledge-hub__list">
        {policies.map((p) => (
          <li key={p.id} className="knowledge-hub__list-item">
            <div>
              <strong>{p.name}</strong>
              <p>
                {p.retention_days ? t('retention.daysValue', { days: p.retention_days }) : t('retention.noDays')} ·{' '}
                {p.action_on_expiry}
              </p>
            </div>
            <span>{p.is_active ? t('retention.active') : t('retention.inactive')}</span>
          </li>
        ))}
      </ul>
      <p className="knowledge-hub__note">{t('retention.legalHoldNote')}</p>
    </KnowledgeHubShell>
  );
}
