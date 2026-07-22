'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { knowledgeAiSearch, type KnowledgeAiSearchResponse } from '@/lib/api/knowledge';
import { KnowledgeHubShell } from '../_components/knowledge-hub-shell';
import { KnowledgeProviderBadge } from '../_components/knowledge-provider-badge';

export default function KnowledgeAiSearchPage() {
  const t = useTranslations('knowledge');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<KnowledgeAiSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await knowledgeAiSearch(query.trim()));
    } catch {
      setError(t('aiSearch.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <KnowledgeHubShell title={t('nav.aiSearch')} subtitle={t('aiSearch.subtitle')}>
      <p className="knowledge-hub__note">{t('aiSearch.originalNote')}</p>
      <div className="knowledge-hub__form-row">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('aiSearch.placeholder')}
          aria-label={t('aiSearch.placeholder')}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void handleSearch();
          }}
        />
        <button type="button" className="button" onClick={() => void handleSearch()} disabled={loading}>
          {loading ? t('loading') : t('aiSearch.search')}
        </button>
      </div>
      {error && <p role="alert">{error}</p>}
      {result && (
        <>
          <KnowledgeProviderBadge label={t('providers.vector')} status={result.provider} />
          {result.note && <p className="knowledge-hub__note">{result.note}</p>}
          {result.hits.length === 0 ? (
            <p>{t('aiSearch.empty')}</p>
          ) : (
            <ul className="knowledge-hub__list">
              {result.hits.map((hit) => (
                <li key={`${hit.document_id}-${hit.citation ?? hit.source}`} className="knowledge-hub__list-item">
                  <div>
                    <Link href={`/dashboard/documents/${hit.document_id}` as Route}>
                      <strong>{hit.title}</strong>
                    </Link>
                    <p>{hit.snippet}</p>
                    {hit.citation && (
                      <p className="knowledge-hub__citation">
                        {t('aiSearch.citation')}: {hit.citation}
                        {hit.page != null ? ` (${t('aiSearch.page')} ${hit.page})` : ''}
                      </p>
                    )}
                    {hit.ai_summary && (
                      <p className="knowledge-hub__summary">
                        {t('aiSearch.summary')}: {hit.ai_summary.slice(0, 200)}
                        {hit.ai_summary.length > 200 ? '…' : ''}
                      </p>
                    )}
                  </div>
                  <span>{hit.source}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </KnowledgeHubShell>
  );
}
