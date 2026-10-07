'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import {
  FUTURE_SEARCH_ENTITY_TYPES,
  SEARCH_DEBOUNCE_MS,
  SEARCH_ENTITY_TYPES,
  fetchGlobalSearch,
  searchResultHref,
  type SearchFilters,
  type SearchGroup,
  type SearchResultItem,
} from '@/lib/api/search';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useNotifications } from '@/lib/notifications/notification-context';
import { useGlobalSearch } from '@/lib/search/global-search-context';
import { fetchCrmQuickSearch } from '@/workspaces/crm/api/search';
import type { CrmSearchResultItem } from '@/workspaces/crm/types/search';

function HighlightText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const index = lowerText.indexOf(lowerQuery);
  if (index < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, index)}
      <mark className="global-search-highlight">{text.slice(index, index + query.length)}</mark>
      {text.slice(index + query.length)}
    </>
  );
}

function entityIcon(entityType: string) {
  switch (entityType) {
    case 'lead':
      return 'L';
    case 'investor':
      return 'I';
    case 'project':
      return 'P';
    case 'financial_transaction':
      return 'T';
    case 'financial_account':
      return 'A';
    case 'funding_commitment':
      return 'F';
    case 'payment_obligation':
      return 'O';
    case 'user':
      return 'U';
    case 'role':
      return 'R';
    case 'company':
      return 'C';
    case 'office':
      return 'O';
    case 'department':
      return 'D';
    case 'team':
      return 'T';
    case 'notification':
      return 'N';
    case 'activity':
      return '•';
    case 'inventory_asset':
      return 'V';
    case 'building':
      return 'B';
    case 'floor':
      return 'F';
    case 'sales_opportunity':
      return 'S';
    default:
      return '?';
  }
}

function labelKeyToPath(labelKey: string) {
  return labelKey.startsWith('search.') ? labelKey.slice('search.'.length) : labelKey;
}

function isPhoneQuery(value: string) {
  return value.replace(/\D/g, '').length >= 10;
}

function asText(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

export function GlobalSearchPalette() {
  const t = useTranslations('search');
  const tCrm = useTranslations('crm.search');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const { open, closePalette, canSearch } = useGlobalSearch();
  const { canRead: canReadCrm } = useCrmAccess();
  const { openDrawer: openNotifications } = useNotifications();

  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [groups, setGroups] = useState<SearchGroup[]>([]);
  const [crmItems, setCrmItems] = useState<CrmSearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({});

  const phoneLookup = canReadCrm && isPhoneQuery(query.trim());
  const osItems = useMemo(
    () => (phoneLookup ? [] : groups.flatMap((group) => group.items.map((item) => ({ kind: 'os' as const, item })))),
    [groups, phoneLookup],
  );
  const crmFlat = useMemo(
    () => crmItems.map((item) => ({ kind: 'crm' as const, item })),
    [crmItems],
  );
  const flatItems = useMemo(() => [...crmFlat, ...osItems], [crmFlat, osItems]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setGroups([]);
      setCrmItems([]);
      setActiveIndex(0);
      setError(null);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !canSearch) return;
    const trimmed = query.trim();
    if (trimmed.length < 1) {
      setGroups([]);
      setCrmItems([]);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    const timer = window.setTimeout(() => {
      const phone = canReadCrm && isPhoneQuery(trimmed);
      const work = phone
        ? fetchCrmQuickSearch(trimmed).then((response) => {
            setCrmItems(response.items ?? []);
            setGroups([]);
            setActiveIndex(0);
          })
        : fetchGlobalSearch(trimmed, filters).then((response) => {
            setCrmItems([]);
            setGroups(response.groups);
            setActiveIndex(0);
          });
      void work
        .catch(() => {
          setGroups([]);
          setCrmItems([]);
          setError(t('errors.failed'));
        })
        .finally(() => setLoading(false));
    }, SEARCH_DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [open, canSearch, canReadCrm, query, filters, t]);

  const navigateTo = useCallback(
    (item: SearchResultItem) => {
      closePalette();
      if (item.entity_type === 'notification') {
        openNotifications();
        return;
      }
      router.push(searchResultHref(item));
    },
    [closePalette, openNotifications, router],
  );

  const personCardHref = useCallback((item: CrmSearchResultItem): Route | null => {
    if (item.entity_type === 'crm_contact' || item.metadata?.open_person_card === true) {
      const contactId = item.entity_id || item.id;
      return contactId ? (`/workspaces/crm/contacts/${contactId}` as Route) : null;
    }
    return null;
  }, []);

  const navigateCrm = useCallback(
    (item: CrmSearchResultItem) => {
      const href = personCardHref(item) ?? (item.url as Route);
      router.push(href);
      closePalette();
    },
    [closePalette, personCardHref, router],
  );

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closePalette();
        return;
      }
      if (flatItems.length === 0) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActiveIndex((index) => (index + 1) % flatItems.length);
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveIndex((index) => (index - 1 + flatItems.length) % flatItems.length);
      }
      if (event.key === 'Enter') {
        event.preventDefault();
        const current = flatItems[activeIndex];
        if (!current) return;
        if (current.kind === 'crm') navigateCrm(current.item);
        else navigateTo(current.item);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, flatItems, activeIndex, closePalette, navigateTo, navigateCrm]);

  if (!open || !canSearch) return null;

  const toggleEntityType = (entityType: string) => {
    setFilters((current) => {
      const selected = new Set(current.entity_types ?? []);
      if (selected.has(entityType)) {
        selected.delete(entityType);
      } else {
        selected.add(entityType);
      }
      return {
        ...current,
        entity_types: selected.size ? Array.from(selected) : undefined,
      };
    });
  };

  let runningIndex = -1;

  return (
    <div className="global-search-overlay" role="presentation" onClick={closePalette}>
      <div
        className="global-search-palette"
        role="dialog"
        aria-modal="true"
        aria-labelledby="global-search-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="global-search-palette__header">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.5" />
            <path d="M20 20 16.5 16.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('placeholder')}
            aria-label={t('placeholder')}
            className="global-search-palette__input"
          />
          <button
            type="button"
            className="global-search-palette__filters-toggle"
            aria-pressed={showFilters}
            onClick={() => setShowFilters((value) => !value)}
          >
            {t('filters.toggle')}
          </button>
          <button type="button" className="global-search-palette__close" onClick={closePalette}>
            {tCommon('close')}
          </button>
        </header>

        {showFilters && (
          <section className="global-search-filters">
            <p className="global-search-filters__label">{t('filters.entityType')}</p>
            <div className="global-search-filters__chips">
              {SEARCH_ENTITY_TYPES.map((entityType) => {
                const active = filters.entity_types?.includes(entityType) ?? false;
                return (
                  <button
                    key={entityType}
                    type="button"
                    className={`global-search-filters__chip${active ? ' global-search-filters__chip--active' : ''}`}
                    onClick={() => toggleEntityType(entityType)}
                  >
                    {t(`entities.${entityType}` as 'entities.lead')}
                  </button>
                );
              })}
              {FUTURE_SEARCH_ENTITY_TYPES.map((entityType) => (
                <span key={entityType} className="global-search-filters__chip global-search-filters__chip--future">
                  {t(`entities.${entityType}` as 'entities.document')}
                </span>
              ))}
            </div>
            <div className="global-search-filters__grid">
              <label>
                <span>{t('filters.status')}</span>
                <input
                  type="text"
                  value={filters.status ?? ''}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      status: event.target.value || undefined,
                    }))
                  }
                />
              </label>
              <label>
                <span>{t('filters.assignedTo')}</span>
                <input
                  type="text"
                  value={filters.assigned_to ?? ''}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      assigned_to: event.target.value || undefined,
                    }))
                  }
                />
              </label>
              <label>
                <span>{t('filters.dateFrom')}</span>
                <input
                  type="date"
                  value={filters.date_from ?? ''}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      date_from: event.target.value || undefined,
                    }))
                  }
                />
              </label>
              <label>
                <span>{t('filters.dateTo')}</span>
                <input
                  type="date"
                  value={filters.date_to ?? ''}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      date_to: event.target.value || undefined,
                    }))
                  }
                />
              </label>
            </div>
          </section>
        )}

        <div className="global-search-palette__body">
          {loading && (
            <div className="global-search-palette__state global-search-empty" role="status" aria-busy="true">
              <span className="ih-search__spinner" aria-hidden="true" />
              <span>{tCommon('loading')}</span>
            </div>
          )}
          {!loading && error && <p className="global-search-palette__state global-search-palette__state--error">{error}</p>}
          {!loading && !error && query.trim() && flatItems.length === 0 && (
            <p
              className="global-search-palette__state global-search-empty"
              data-testid={phoneLookup ? 'crm-phone-lookup-empty' : undefined}
            >
              {phoneLookup ? tCrm('emptyPhone') : t('empty')}
            </p>
          )}
          {!loading && !error && !query.trim() && (
            <p className="global-search-palette__state global-search-empty">{t('hint')}</p>
          )}

          {!loading && !error && crmItems.length > 0 && (
            <section className="global-search-group">
              <h3>{tCrm('entities.crm_contact')}</h3>
              <ul>
                {crmItems.map((item) => {
                  runningIndex += 1;
                  const itemIndex = runningIndex;
                  const isActive = itemIndex === activeIndex;
                  const displayPhone = asText(item.metadata?.display_phone) || item.subtitle || '';
                  const email = asText(item.metadata?.email);
                  const stage = asText(item.metadata?.lead_stage) || asText(item.metadata?.kanban_stage);
                  const duplicate = item.metadata?.possible_duplicate === true;
                  const href = personCardHref(item) ?? (item.url as Route);
                  return (
                    <li key={`${item.entity_type}-${item.entity_id}`}>
                      <Link
                        href={href}
                        className={`global-search-result${isActive ? ' global-search-result--active' : ''}`}
                        data-testid={item.metadata?.phone_lookup ? 'crm-phone-lookup-result' : undefined}
                        onMouseEnter={() => setActiveIndex(itemIndex)}
                        onClick={(event) => {
                          event.preventDefault();
                          navigateCrm(item);
                        }}
                      >
                        <span className="global-search-result__icon">{entityIcon('company')}</span>
                        <span className="global-search-result__content">
                          <strong>
                            <HighlightText text={item.title} query={query} />
                          </strong>
                          {displayPhone ? (
                            <span className="global-search-result__subtitle">
                              <HighlightText text={displayPhone} query={query} />
                            </span>
                          ) : null}
                          {email ? <span className="global-search-result__preview">{email}</span> : null}
                          {stage ? (
                            <span className="global-search-result__preview">{tCrm('leadStage', { stage })}</span>
                          ) : null}
                          {duplicate ? (
                            <span className="global-search-result__preview" data-testid="crm-phone-lookup-duplicate">
                              {tCrm('possibleDuplicates')}
                            </span>
                          ) : null}
                          <span className="global-search-result__preview">{tCrm('openPersonCard')}</span>
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {!loading &&
            !error &&
            !phoneLookup &&
            groups.map((group) => (
              <section key={group.entity_type} className="global-search-group">
                <h3>{t(labelKeyToPath(group.label_key) as 'entities.lead')}</h3>
                <ul>
                  {group.items.map((item) => {
                    runningIndex += 1;
                    const itemIndex = runningIndex;
                    const isActive = itemIndex === activeIndex;
                    const href = searchResultHref(item);
                    const preview =
                      item.highlights[0]?.snippet || item.preview || item.subtitle || '';
                    return (
                      <li key={item.entity_id}>
                        <Link
                          href={href}
                          className={`global-search-result${isActive ? ' global-search-result--active' : ''}`}
                          onMouseEnter={() => setActiveIndex(itemIndex)}
                          onClick={(event) => {
                            if (item.entity_type === 'notification') {
                              event.preventDefault();
                              navigateTo(item);
                            } else {
                              closePalette();
                            }
                          }}
                        >
                          <span className={`global-search-result__icon global-search-result__icon--${item.entity_type}`}>
                            {entityIcon(item.entity_type)}
                          </span>
                          <span className="global-search-result__content">
                            <strong>
                              <HighlightText text={item.title} query={query} />
                            </strong>
                            {item.subtitle && (
                              <span className="global-search-result__subtitle">
                                <HighlightText text={item.subtitle} query={query} />
                              </span>
                            )}
                            {preview && (
                              <span className="global-search-result__preview">
                                <HighlightText text={preview} query={query} />
                              </span>
                            )}
                            <span className="global-search-result__module">
                              {t(`modules.${item.module.replace('/', '_')}` as 'modules.leads')}
                            </span>
                          </span>
                          {item.created_at && (
                            <time className="global-search-result__time" dateTime={item.created_at}>
                              {new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-US', {
                                dateStyle: 'short',
                              }).format(new Date(item.created_at))}
                            </time>
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
        </div>

        <footer className="global-search-palette__footer">
          <span>{t('keyboard.navigate')}</span>
          <span>{t('keyboard.open')}</span>
          <span>{t('keyboard.close')}</span>
        </footer>
      </div>
    </div>
  );
}
