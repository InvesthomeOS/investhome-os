'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { canCreateCrm, canManageCrmTasks } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  useCrmQuickSearch,
  useCrmRecentSearches,
  useRecordRecentSearch,
} from '@/workspaces/crm/hooks/use-crm-search';
import { useCrmSearchStore } from '@/workspaces/crm/stores/crm-search-store';
import { CRM_SEARCH_DEBOUNCE_MS, CRM_SEARCH_MIN_QUERY_LENGTH } from '@/workspaces/crm/types/search';
import type { CrmSearchResultItem } from '@/workspaces/crm/types/search';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';

function HighlightText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const index = lowerText.indexOf(lowerQuery);
  if (index < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, index)}
      <mark className="crm-search-highlight">{text.slice(index, index + query.length)}</mark>
      {text.slice(index + query.length)}
    </>
  );
}

function entityIcon(entityType: string) {
  const icons: Record<string, string> = {
    crm_contact: 'C',
    crm_company: 'B',
    crm_relationship: 'R',
    crm_activity: 'A',
    crm_communication: 'M',
    sales_opportunity: 'O',
    investor: 'I',
    project: 'P',
    inventory_asset: 'H',
    document: 'D',
  };
  return icons[entityType] ?? '?';
}

export function CrmSearchPalette() {
  const t = useTranslations('crm.search');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { openContact } = useContactCard();
  const { authLoading, user, canRead: canSearch } = useCrmAccess();
  const { paletteOpen, closePalette, query, setQuery, activeItemIndex, setActiveItemIndex } = useCrmSearchStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const recordRecent = useRecordRecentSearch();

  const canSearchEnabled = !authLoading && canSearch;
  const canCreate = canCreateCrm(user);
  const canTasks = canManageCrmTasks(user);

  useEffect(() => {
    if (!paletteOpen) return;
    setQuery('');
    setDebouncedQuery('');
    setActiveItemIndex(0);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [paletteOpen, setQuery, setActiveItemIndex]);

  useEffect(() => {
    if (!paletteOpen) return;
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), CRM_SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [paletteOpen, query]);

  const searchQuery = useCrmQuickSearch(
    debouncedQuery,
    canSearchEnabled && paletteOpen && debouncedQuery.length >= CRM_SEARCH_MIN_QUERY_LENGTH,
  );
  const recentQuery = useCrmRecentSearches();

  const groups = useMemo(() => searchQuery.data?.groups ?? [], [searchQuery.data?.groups]);
  const flatItems = useMemo(
    () => groups.flatMap((g) => g.items.map((item) => ({ group: g, item }))),
    [groups],
  );

  const quickActions = useMemo(() => {
    const actions: Array<{ id: string; label: string; href: Route; show: boolean }> = [];
    if (canCreate) {
      actions.push({ id: 'create-contact', label: t('actions.createContact'), href: '/workspaces/crm/contacts/new' as Route, show: true });
      actions.push({ id: 'create-company', label: t('actions.createCompany'), href: '/workspaces/crm/companies/new' as Route, show: true });
    }
    if (canTasks) {
      actions.push({ id: 'create-task', label: t('actions.createTask'), href: '/workspaces/crm/tasks' as Route, show: true });
    }
    return actions.filter((a) => a.show);
  }, [canCreate, canTasks, t]);

  const navigateTo = useCallback(
    (item: CrmSearchResultItem) => {
      void recordRecent.mutateAsync({ query: debouncedQuery, result_count: searchQuery.data?.total ?? 0 });
      closePalette();
      if (item.entity_type === 'crm_contact') {
        openContact(item.entity_id || item.id);
        return;
      }
      router.push(item.url as Route);
    },
    [closePalette, debouncedQuery, openContact, recordRecent, router, searchQuery.data?.total],
  );

  useEffect(() => {
    if (!paletteOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

      if (event.key === 'Escape') {
        event.preventDefault();
        closePalette();
        return;
      }

      if (event.key === '/' && !isInput && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        inputRef.current?.focus();
        return;
      }

      if (flatItems.length === 0) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActiveItemIndex((activeItemIndex + 1) % flatItems.length);
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveItemIndex((activeItemIndex - 1 + flatItems.length) % flatItems.length);
      }
      if (event.key === 'Enter') {
        event.preventDefault();
        const current = flatItems[activeItemIndex];
        if (current) navigateTo(current.item);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [paletteOpen, flatItems, activeItemIndex, closePalette, navigateTo, setActiveItemIndex]);

  if (!paletteOpen || !canSearchEnabled) return null;

  let runningIndex = -1;

  return (
    <div className="crm-search-overlay" role="presentation" onClick={closePalette}>
      <div
        className="crm-search-palette"
        role="dialog"
        aria-modal="true"
        aria-label={t('paletteTitle')}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="crm-search-palette__header">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.5" />
            <path d="M20 20 16.5 16.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('placeholder')}
            aria-label={t('placeholder')}
            className="crm-search-palette__input"
          />
          <button type="button" className="crm-search-palette__close" onClick={closePalette}>
            {tCommon('close')}
          </button>
        </header>

        <div className="crm-search-palette__body">
          {searchQuery.isLoading && <p className="crm-search-palette__state">{tCommon('loading')}</p>}
          {searchQuery.isError && <p className="crm-search-palette__state crm-search-palette__state--error">{t('errors.failed')}</p>}

          {!debouncedQuery && recentQuery.data && recentQuery.data.length > 0 && (
            <section className="crm-search-group">
              <h3>{t('recentSearches')}</h3>
              <ul>
                {recentQuery.data.slice(0, 5).map((recent) => (
                  <li key={recent.id}>
                    <button
                      type="button"
                      className="crm-search-result"
                      onClick={() => {
                        setQuery(recent.query);
                        setDebouncedQuery(recent.query);
                      }}
                    >
                      <span className="crm-search-result__icon">↺</span>
                      <span className="crm-search-result__content">
                        <strong>{recent.query}</strong>
                        <span className="crm-search-result__subtitle">{t('resultCount', { count: recent.result_count })}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {!debouncedQuery && (
            <section className="crm-search-group">
              <h3>{t('quickActions')}</h3>
              <ul>
                {quickActions.map((action) => (
                  <li key={action.id}>
                    <Link href={action.href} className="crm-search-result" onClick={closePalette}>
                      <span className="crm-search-result__icon">+</span>
                      <span className="crm-search-result__content">
                        <strong>{action.label}</strong>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {debouncedQuery && !searchQuery.isLoading && flatItems.length === 0 && (
            <div className="crm-search-zero">
              <p>{t('empty')}</p>
              <p className="crm-search-zero__hint">{t('zeroHint')}</p>
            </div>
          )}

          {groups.map((group) => (
            <section key={group.entity_type} className="crm-search-group">
              <h3>{t(`entities.${group.entity_type}` as 'entities.crm_contact')}</h3>
              <ul>
                {group.items.map((item) => {
                  runningIndex += 1;
                  const isActive = runningIndex === activeItemIndex;
                  const preview = item.highlighted_fields[0]?.snippet || item.preview || item.subtitle || '';
                  return (
                    <li key={item.entity_id}>
                      <Link
                        href={item.url as Route}
                        className={`crm-search-result${isActive ? ' crm-search-result--active' : ''}`}
                        onMouseEnter={() => setActiveItemIndex(runningIndex)}
                        onClick={(e) => {
                          e.preventDefault();
                          navigateTo(item);
                        }}
                      >
                        <span className={`crm-search-result__icon crm-search-result__icon--${item.entity_type}`}>
                          {entityIcon(item.entity_type)}
                        </span>
                        <span className="crm-search-result__content">
                          <strong>
                            <HighlightText text={item.title} query={debouncedQuery} />
                          </strong>
                          {item.subtitle && (
                            <span className="crm-search-result__subtitle">
                              <HighlightText text={item.subtitle} query={debouncedQuery} />
                            </span>
                          )}
                          {preview && (
                            <span className="crm-search-result__preview">
                              <HighlightText text={preview} query={debouncedQuery} />
                            </span>
                          )}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>

        <footer className="crm-search-palette__footer">
          <span>{t('keyboard.navigate')}</span>
          <span>{t('keyboard.open')}</span>
          <span>{t('keyboard.close')}</span>
        </footer>
      </div>
    </div>
  );
}

export function useCrmSearchShortcuts() {
  const { authLoading, canRead: canSearch } = useCrmAccess();
  const { openPalette, togglePalette } = useCrmSearchStore();

  useEffect(() => {
    if (authLoading || !canSearch) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;
      const isMac = navigator.platform.toLowerCase().includes('mac');
      const modifier = isMac ? event.metaKey : event.ctrlKey;

      if (modifier && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        togglePalette();
        return;
      }

      if (event.key === '/' && !isInput && !modifier) {
        event.preventDefault();
        openPalette();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [authLoading, canSearch, openPalette, togglePalette]);
}
