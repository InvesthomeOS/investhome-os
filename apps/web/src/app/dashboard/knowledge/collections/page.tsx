'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  createKnowledgeCollection,
  fetchKnowledgeCollections,
  type KnowledgeCollection,
} from '@/lib/api/knowledge';
import { useAuth } from '@/lib/auth/auth-context';
import { canManageKnowledge } from '@/lib/knowledge/knowledge-permissions';

import { KnowledgeHubShell } from '../_components/knowledge-hub-shell';

export default function KnowledgeCollectionsPage() {
  const t = useTranslations('knowledge');
  const { user } = useAuth();
  const canManage = canManageKnowledge(user);
  const [items, setItems] = useState<KnowledgeCollection[]>([]);
  const [name, setName] = useState('');
  const [type, setType] = useState<'manual' | 'smart'>('manual');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await fetchKnowledgeCollections());
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
      await createKnowledgeCollection({
        name: name.trim(),
        collection_type: type,
        smart_rules: type === 'smart' ? { folder: 'general' } : undefined,
      });
      setName('');
      await load();
    } catch {
      setError(t('collections.createError'));
    }
  };

  return (
    <KnowledgeHubShell title={t('nav.collections')} subtitle={t('collections.subtitle')}>
      {canManage && (
        <div className="knowledge-hub__form-row">
          <label>
            <span className="sr-only">{t('collections.name')}</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('collections.name')}
              aria-label={t('collections.name')}
            />
          </label>
          <select value={type} onChange={(e) => setType(e.target.value as 'manual' | 'smart')} aria-label={t('collections.type')}>
            <option value="manual">{t('collections.manual')}</option>
            <option value="smart">{t('collections.smart')}</option>
          </select>
          <button type="button" className="button" onClick={() => void handleCreate()}>
            {t('collections.create')}
          </button>
        </div>
      )}
      {loading && <p>{t('loading')}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && items.length === 0 && <p>{t('collections.empty')}</p>}
      <ul className="knowledge-hub__list">
        {items.map((item) => (
          <li key={item.id} className="knowledge-hub__list-item">
            <div>
              <strong>{item.name}</strong>
              <p>{item.description || t(`collections.${item.collection_type}` as 'collections.manual')}</p>
            </div>
            <span>{t('collections.docCount', { count: item.document_count })}</span>
          </li>
        ))}
      </ul>
    </KnowledgeHubShell>
  );
}
