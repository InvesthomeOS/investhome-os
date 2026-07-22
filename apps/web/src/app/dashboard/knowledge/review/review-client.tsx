'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';

import {
  fetchKnowledgeReview,
  resolveKnowledgeReview,
  syncKnowledgeReview,
  type KnowledgeReviewItem,
} from '@/lib/api/knowledge';
import { useAuth } from '@/lib/auth/auth-context';
import { canReviewKnowledge } from '@/lib/knowledge/knowledge-permissions';
import { KnowledgeHubShell } from '../_components/knowledge-hub-shell';

export default function KnowledgeReviewPage() {
  const t = useTranslations('knowledge');
  const { user } = useAuth();
  const canReview = canReviewKnowledge(user);
  const searchParams = useSearchParams();
  const reason = searchParams.get('reason') || undefined;
  const [items, setItems] = useState<KnowledgeReviewItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await fetchKnowledgeReview({ reason }));
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reason]);

  const handleSync = async () => {
    try {
      await syncKnowledgeReview();
      await load();
    } catch {
      setError(t('review.syncError'));
    }
  };

  const handleResolve = async (id: string, status: 'resolved' | 'dismissed') => {
    try {
      await resolveKnowledgeReview(id, { status });
      await load();
    } catch {
      setError(t('review.resolveError'));
    }
  };

  return (
    <KnowledgeHubShell title={t('nav.review')} subtitle={t('review.subtitle')}>
      {canReview && (
        <div className="knowledge-hub__form-row">
          <button type="button" className="button" onClick={() => void handleSync()}>
            {t('review.sync')}
          </button>
        </div>
      )}
      {loading && <p>{t('loading')}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && items.length === 0 && <p>{t('review.empty')}</p>}
      <ul className="knowledge-hub__list">
        {items.map((item) => (
          <li key={item.id} className="knowledge-hub__list-item">
            <div>
              <Link href={`/dashboard/documents/${item.document_id}` as Route}>
                <strong>{item.document_title || item.document_id}</strong>
              </Link>
              <p>
                {t(`review.reasons.${item.reason}` as 'review.reasons.unlinked')} · {item.priority}
              </p>
              {item.details && <p>{item.details}</p>}
            </div>
            {canReview && (
              <div className="knowledge-hub__actions">
                <button type="button" className="button button--ghost" onClick={() => void handleResolve(item.id, 'resolved')}>
                  {t('review.resolve')}
                </button>
                <button type="button" className="button button--ghost" onClick={() => void handleResolve(item.id, 'dismissed')}>
                  {t('review.dismiss')}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </KnowledgeHubShell>
  );
}
