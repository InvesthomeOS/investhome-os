'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { canExportCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  useClearRecentSearches,
  useCrmGlobalSearch,
  useCrmQuickSearch,
  useCrmRecentSearches,
  useExportSearchResults,
  useRecordRecentSearch,
  useRemoveRecentSearch,
  crmSearchQueries,
} from '@/workspaces/crm/hooks/use-crm-search';
import { useQuery } from '@tanstack/react-query';
import { useCrmSearchStore } from '@/workspaces/crm/stores/crm-search-store';
import { CRM_SEARCH_ENTITY_TYPES } from '@/workspaces/crm/types/search';
import type { CrmSearchEntityType, CrmSearchResultItem } from '@/workspaces/crm/types/search';

function SanitizedHighlight({ html }: { html: string }) {
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function SearchResultRow({ item, viewMode }: { item: CrmSearchResultItem; viewMode: string }) {
  const t = useTranslations('crm.search');
  return (
    <Link href={item.url as Route} className={`crm-search-page__result crm-search-page__result--${viewMode}`}>
      <span className={`crm-search-page__result-icon crm-search-page__result-icon--${item.entity_type}`}>
        {item.icon?.[0]?.toUpperCase() ?? item.entity_type[0]?.toUpperCase()}
      </span>
      <span className="crm-search-page__result-body">
        <strong>{item.title}</strong>
        {item.subtitle && <span className="crm-search-page__result-sub">{item.subtitle}</span>}
        {item.preview && <span className="crm-search-page__result-preview">{item.preview}</span>}
        {item.highlighted_fields[0]?.highlighted_html && (
          <span className="crm-search-page__result-highlight">
            <SanitizedHighlight html={item.highlighted_fields[0].highlighted_html} />
          </span>
        )}
        <span className="crm-search-page__result-meta">
          {t(`entities.${item.entity_type}` as 'entities.crm_contact')}
          {item.entity_status && ` · ${item.entity_status}`}
        </span>
      </span>
      <span className="crm-search-page__result-score">{Math.round(item.score)}</span>
    </Link>
  );
}

export function SearchWorkspace() {
  const t = useTranslations('crm.search');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { authLoading, user, canRead } = useCrmAccess();
  const {
    activeEntityTab,
    setActiveEntityTab,
    viewMode,
    setViewMode,
    filterSidebarOpen,
    setFilterSidebarOpen,
    selectedResultIds,
    toggleResultSelection,
    clearSelection,
  } = useCrmSearchStore();

  const initialQuery = searchParams.get('q') ?? '';
  const [query, setQuery] = useState(initialQuery);
  const [appliedQuery, setAppliedQuery] = useState(initialQuery);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [exactMatch, setExactMatch] = useState(false);
  const [page, setPage] = useState(1);

  const recordRecent = useRecordRecentSearch();
  const exportMutation = useExportSearchResults();
  const recentQuery = useCrmRecentSearches();
  const clearRecent = useClearRecentSearches();
  const removeRecent = useRemoveRecentSearch();
  const quickQuery = useCrmQuickSearch(query, query.trim().length >= 2 && !appliedQuery.trim());
  const suggestionsQuery = useQuery({
    ...crmSearchQueries.suggestions(query.trim().length >= 2 ? query : 'marina'),
    enabled: !authLoading && canRead && !appliedQuery.trim(),
  });

  const SUGGESTED_FALLBACK = [
    { label: 'Marina Heights', query: 'Marina Heights' },
    { label: 'Ahmet Yılmaz', query: 'Ahmet Yılmaz' },
    { label: 'VIP', query: 'tag:VIP' },
    { label: 'Open opportunities', query: 'status:open' },
  ];

  const entityTypes = useMemo(
    () => (activeEntityTab === 'all' ? undefined : [activeEntityTab]),
    [activeEntityTab],
  );

  const searchParams_ = useMemo(
    () => ({
      query: appliedQuery,
      entity_types: entityTypes,
      page,
      page_size: 25,
      include_archived: includeArchived,
      exact_match: exactMatch,
      fuzzy_match: !exactMatch,
    }),
    [appliedQuery, entityTypes, page, includeArchived, exactMatch],
  );

  const searchQuery = useCrmGlobalSearch(
    searchParams_,
    !authLoading && canRead && Boolean(appliedQuery.trim()),
  );

  const runSearch = useCallback(() => {
    setAppliedQuery(query.trim());
    setPage(1);
    const params = new URLSearchParams();
    if (query.trim()) params.set('q', query.trim());
    router.replace(`/workspaces/crm/search?${params.toString()}` as Route);
  }, [query, router]);

  useEffect(() => {
    if (searchQuery.data && appliedQuery.trim()) {
      void recordRecent.mutateAsync({
        query: appliedQuery,
        result_count: searchQuery.data.total,
        entity_types: entityTypes,
      });
    }
  }, [appliedQuery, entityTypes, recordRecent, searchQuery.data]);

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canRead) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  }

  const handleExport = async () => {
    const result = await exportMutation.mutateAsync({
      format: 'csv',
      query: appliedQuery,
      result_ids: selectedResultIds.length ? selectedResultIds : undefined,
    });
    if (result.content) {
      const blob = new Blob([result.content], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'crm-search-export.csv';
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="crm-search-page">
      <header className="crm-search-page__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-search-page__header-actions">
          <Link href={'/workspaces/crm/search/advanced' as Route} className="crm-search-page__link">
            {t('advanced')}
          </Link>
          <Link href={'/workspaces/crm/search/saved' as Route} className="crm-search-page__link">
            {t('savedSearches')}
          </Link>
        </div>
      </header>

      <form
        className="crm-search-page__bar"
        onSubmit={(e) => {
          e.preventDefault();
          runSearch();
        }}
      >
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('placeholder')}
          aria-label={t('placeholder')}
          className="crm-search-page__input"
        />
        <Button type="submit">{t('search')}</Button>
      </form>

      <div className="crm-search-page__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeEntityTab === 'all'}
          className={activeEntityTab === 'all' ? 'crm-search-page__tab--active' : ''}
          onClick={() => setActiveEntityTab('all')}
        >
          {t('tabs.all')}
        </button>
        {CRM_SEARCH_ENTITY_TYPES.map((type) => (
          <button
            key={type}
            type="button"
            role="tab"
            aria-selected={activeEntityTab === type}
            className={activeEntityTab === type ? 'crm-search-page__tab--active' : ''}
            onClick={() => setActiveEntityTab(type as CrmSearchEntityType)}
          >
            {t(`entities.${type}` as 'entities.crm_contact')}
          </button>
        ))}
      </div>

      <div className="crm-search-page__layout">
        {filterSidebarOpen && (
          <aside className="crm-search-page__filters">
            <h2>{t('filters.title')}</h2>
            <label className="crm-search-page__filter">
              <input type="checkbox" checked={exactMatch} onChange={(e) => setExactMatch(e.target.checked)} />
              {t('filters.exactMatch')}
            </label>
            <label className="crm-search-page__filter">
              <input type="checkbox" checked={includeArchived} onChange={(e) => setIncludeArchived(e.target.checked)} />
              {t('filters.includeArchived')}
            </label>
            {searchQuery.data?.active_filters && searchQuery.data.active_filters.length > 0 && (
              <div className="crm-search-page__chips">
                {searchQuery.data.active_filters.map((chip) => (
                  <span key={chip} className="crm-search-page__chip">
                    {chip}
                  </span>
                ))}
              </div>
            )}
          </aside>
        )}

        <main className="crm-search-page__results">
          <div className="crm-search-page__toolbar">
            <button type="button" onClick={() => setFilterSidebarOpen(!filterSidebarOpen)}>
              {filterSidebarOpen ? t('filters.hide') : t('filters.show')}
            </button>
            <span>
              {searchQuery.data ? t('resultCount', { count: searchQuery.data.total }) : ''}
              {searchQuery.data?.took_ms ? ` · ${searchQuery.data.took_ms}ms` : ''}
            </span>
            <select value={viewMode} onChange={(e) => setViewMode(e.target.value as typeof viewMode)} aria-label={t('viewMode')}>
              <option value="list">{t('views.list')}</option>
              <option value="compact">{t('views.compact')}</option>
              <option value="table">{t('views.table')}</option>
              <option value="card">{t('views.card')}</option>
            </select>
            {canExportCrm(user) && (
              <Button type="button" variant="secondary" onClick={() => void handleExport()} disabled={exportMutation.isPending}>
                {t('export')}
              </Button>
            )}
          </div>

          {searchQuery.data?.explanation && searchQuery.data.total === 0 && (
            <div className="crm-search-page__explanation">{searchQuery.data.explanation}</div>
          )}

          {searchQuery.isLoading && <LoadingState label={tCommon('loading')} />}
          {searchQuery.isError && (
            <ErrorState
              title={t('errors.failed')}
              message={t('errors.failed')}
              action={
                <Button type="button" onClick={() => void searchQuery.refetch()}>
                  {tCommon('retry')}
                </Button>
              }
            />
          )}

          {!appliedQuery.trim() && (
            <div className="crm-search-home" data-testid="crm-search-home">
              <section className="crm-search-home__section" aria-label={t('recentSearches')}>
                <div className="crm-search-home__section-head">
                  <h2>{t('recentSearches')}</h2>
                  {recentQuery.data && recentQuery.data.length > 0 ? (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => void clearRecent.mutateAsync()}
                    >
                      {t('clearRecent')}
                    </Button>
                  ) : null}
                </div>
                {recentQuery.isLoading ? <LoadingState label={tCommon('loading')} /> : null}
                {recentQuery.isError ? (
                  <ErrorState title={t('errors.failed')} message={t('errors.failed')} />
                ) : null}
                {!recentQuery.isLoading && (!recentQuery.data || recentQuery.data.length === 0) ? (
                  <EmptyState title={t('recentEmptyTitle')} description={t('recentEmpty')} />
                ) : (
                  <ul className="crm-search-home__list">
                    {(recentQuery.data ?? []).slice(0, 8).map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          className="crm-search-home__chip"
                          onClick={() => {
                            setQuery(item.query);
                            setAppliedQuery(item.query);
                            router.replace(`/workspaces/crm/search?q=${encodeURIComponent(item.query)}` as Route);
                          }}
                        >
                          {item.query}
                        </button>
                        <button
                          type="button"
                          className="crm-search-home__remove"
                          aria-label={t('removeRecent')}
                          onClick={() => void removeRecent.mutateAsync(item.id)}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="crm-search-home__section" aria-label={t('suggestedResults')}>
                <h2>{t('suggestedResults')}</h2>
                <ul className="crm-search-home__list">
                  {(suggestionsQuery.data?.suggestions?.length
                    ? suggestionsQuery.data.suggestions.slice(0, 6).map((s) => ({
                        label: s.text,
                        query: s.text,
                      }))
                    : SUGGESTED_FALLBACK
                  ).map((item) => (
                    <li key={item.query}>
                      <button
                        type="button"
                        className="crm-search-home__chip"
                        onClick={() => {
                          setQuery(item.query);
                          setAppliedQuery(item.query);
                          router.replace(
                            `/workspaces/crm/search?q=${encodeURIComponent(item.query)}` as Route,
                          );
                        }}
                      >
                        {item.label}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>

              {query.trim().length >= 2 ? (
                <section className="crm-search-home__section" aria-label={t('quickResults')}>
                  <h2>{t('quickResults')}</h2>
                  {quickQuery.isLoading ? <LoadingState label={tCommon('loading')} /> : null}
                  {quickQuery.isError ? (
                    <ErrorState title={t('errors.failed')} message={t('errors.failed')} />
                  ) : null}
                  {!quickQuery.isLoading && (!quickQuery.data?.items || quickQuery.data.items.length === 0) ? (
                    <EmptyState title={t('empty')} description={t('zeroHint')} />
                  ) : (
                    <div className="crm-search-page__list crm-search-page__list--compact">
                      {(quickQuery.data?.items ?? []).slice(0, 6).map((item) => (
                        <SearchResultRow key={item.id} item={item} viewMode="compact" />
                      ))}
                    </div>
                  )}
                </section>
              ) : (
                <EmptyState title={t('hintTitle')} description={t('hint')} />
              )}
            </div>
          )}

          {appliedQuery.trim() && !searchQuery.isLoading && searchQuery.data?.total === 0 && (
            <div className="crm-search-zero">
              <EmptyState title={t('empty')} description={t('zeroHint')} />
              {searchQuery.data.did_you_mean && (
                <p>{t('didYouMean', { suggestion: searchQuery.data.did_you_mean })}</p>
              )}
            </div>
          )}

          {searchQuery.data && searchQuery.data.items.length > 0 && (
            <div className={`crm-search-page__list crm-search-page__list--${viewMode}`}>
              {searchQuery.data.items.map((item) => (
                <div key={item.id} className="crm-search-page__list-item">
                  <input
                    type="checkbox"
                    checked={selectedResultIds.includes(item.id)}
                    onChange={() => toggleResultSelection(item.id)}
                    aria-label={t('selectResult')}
                  />
                  <SearchResultRow item={item} viewMode={viewMode} />
                </div>
              ))}
            </div>
          )}

          {searchQuery.data?.has_more && (
            <Button type="button" variant="secondary" onClick={() => setPage((p) => p + 1)}>
              {t('loadMore')}
            </Button>
          )}

          {selectedResultIds.length > 0 && (
            <div className="crm-search-page__selection-bar">
              <span>{t('selectedCount', { count: selectedResultIds.length })}</span>
              <Button type="button" variant="secondary" onClick={clearSelection}>
                {t('clearSelection')}
              </Button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
