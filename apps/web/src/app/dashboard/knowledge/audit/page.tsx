'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchActivities, type ActivityLogEntry } from '@/lib/api/activity';
import { KnowledgeHubShell } from '../_components/knowledge-hub-shell';

export default function KnowledgeAuditPage() {
  const t = useTranslations('knowledge');
  const [items, setItems] = useState<ActivityLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await fetchActivities({
          search: '',
          entity_type: 'document',
          action: '',
          source: '',
          date_from: '',
          date_to: '',
          sort_order: 'desc',
          page: 1,
          page_size: 50,
        });
        if (!cancelled) setItems(res.items ?? []);
      } catch {
        if (!cancelled) setError(t('loadError'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  return (
    <KnowledgeHubShell title={t('nav.audit')} subtitle={t('audit.subtitle')}>
      <p className="knowledge-hub__note">{t('audit.note')}</p>
      {loading && <p>{t('loading')}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && items.length === 0 && <p>{t('audit.empty')}</p>}
      <ul className="knowledge-hub__list">
        {items.map((item) => (
          <li key={item.id} className="knowledge-hub__list-item">
            <div>
              <strong>{item.action}</strong>
              <p>
                {item.entity_label || item.entity_id} · {item.created_at}
              </p>
            </div>
            {item.entity_id && (
              <Link href={`/dashboard/documents/${item.entity_id}` as Route}>{t('audit.open')}</Link>
            )}
          </li>
        ))}
      </ul>
      <Link href={'/dashboard/activity' as Route} className="button button--ghost">
        {t('audit.fullActivity')}
      </Link>
    </KnowledgeHubShell>
  );
}
