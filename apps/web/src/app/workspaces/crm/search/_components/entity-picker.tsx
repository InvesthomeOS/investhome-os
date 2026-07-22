'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { Route } from 'next';
import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { LoadingState } from '@investhome/ui';

import { useEntityPicker } from '@/workspaces/crm/hooks/use-crm-search';
import type { CrmSearchResultItem } from '@/workspaces/crm/types/search';
import { CRM_SEARCH_DEBOUNCE_MS } from '@/workspaces/crm/types/search';

export type EntityPickerProps = {
  entityTypes?: string[];
  selectedIds?: string[];
  onSelect: (item: CrmSearchResultItem) => void;
  onRemove?: (id: string) => void;
  multiple?: boolean;
  placeholder?: string;
  createNewHref?: Route;
  excludeIds?: string[];
};

export function EntityPicker({
  entityTypes = ['crm_contact', 'crm_company'],
  selectedIds = [],
  onSelect,
  onRemove,
  multiple = true,
  placeholder,
  createNewHref,
  excludeIds,
}: EntityPickerProps) {
  const t = useTranslations('crm.search.entityPicker');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), CRM_SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  const params = useMemo(
    () => ({
      query: debouncedQuery,
      entity_types: entityTypes,
      page: 1,
      page_size: 20,
      exclude_ids: excludeIds,
    }),
    [debouncedQuery, entityTypes, excludeIds],
  );

  const pickerQuery = useEntityPicker(params, debouncedQuery.length >= 1 || debouncedQuery === '');

  useEffect(() => {
    setActiveIndex(0);
  }, [pickerQuery.data?.items]);

  const items = pickerQuery.data?.items ?? [];

  return (
    <div className="crm-entity-picker">
      <div className="crm-entity-picker__input-row">
        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder ?? t('placeholder')}
          aria-label={placeholder ?? t('placeholder')}
          onKeyDown={(e) => {
            if (items.length === 0) return;
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setActiveIndex((i) => (i + 1) % items.length);
            }
            if (e.key === 'ArrowUp') {
              e.preventDefault();
              setActiveIndex((i) => (i - 1 + items.length) % items.length);
            }
            if (e.key === 'Enter') {
              e.preventDefault();
              const item = items[activeIndex];
              if (item) onSelect(item);
            }
          }}
        />
        {createNewHref && (
          <Link href={createNewHref} className="crm-entity-picker__create">
            {t('createNew')}
          </Link>
        )}
      </div>

      {selectedIds.length > 0 && (
        <ul className="crm-entity-picker__selected">
          {selectedIds.map((id) => (
            <li key={id}>
              <span>{id.slice(0, 8)}…</span>
              {onRemove && (
                <button type="button" onClick={() => onRemove(id)} aria-label={t('remove')}>
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {pickerQuery.isLoading && <LoadingState label={t('loading')} />}

      <ul className="crm-entity-picker__results" role="listbox">
        {items.map((item, index) => (
          <li key={item.entity_id}>
            <button
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              className={`crm-entity-picker__option${index === activeIndex ? ' crm-entity-picker__option--active' : ''}${selectedIds.includes(item.entity_id) ? ' crm-entity-picker__option--selected' : ''}`}
              onClick={() => onSelect(item)}
              disabled={!multiple && selectedIds.includes(item.entity_id)}
            >
              <strong>{item.title}</strong>
              {item.subtitle && <span>{item.subtitle}</span>}
              <span className="crm-entity-picker__type">{t(`types.${item.entity_type}` as 'types.crm_contact')}</span>
            </button>
          </li>
        ))}
      </ul>

      {pickerQuery.data?.has_more && <p className="crm-entity-picker__more">{t('loadMore')}</p>}
    </div>
  );
}
