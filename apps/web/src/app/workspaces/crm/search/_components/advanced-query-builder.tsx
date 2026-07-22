'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmSearchQueries, useCrmGlobalSearch } from '@/workspaces/crm/hooks/use-crm-search';
import { useCrmSearchStore } from '@/workspaces/crm/stores/crm-search-store';

type QueryCondition = {
  id: string;
  field: string;
  operator: string;
  value: string;
};

type QueryGroup = {
  id: string;
  logic: 'and' | 'or';
  conditions: QueryCondition[];
};

const OPERATORS = ['contains', 'equals', 'starts_with', 'ends_with', 'gt', 'lt', 'is_empty', 'is_not_empty'];
const FIELDS = ['display_name', 'email', 'phone', 'status', 'tag', 'owner', 'company', 'relationship_type'];

function newCondition(): QueryCondition {
  return { id: crypto.randomUUID(), field: 'display_name', operator: 'contains', value: '' };
}

function newGroup(): QueryGroup {
  return { id: crypto.randomUUID(), logic: 'and', conditions: [newCondition()] };
}

export function AdvancedQueryBuilder() {
  const t = useTranslations('crm.search.advancedQuery');
  const tSearch = useTranslations('crm.search');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { authLoading, canRead } = useCrmAccess();
  const { queryBuilderDraft, setQueryBuilderDraft } = useCrmSearchStore();
  const [groups, setGroups] = useState<QueryGroup[]>(
    (queryBuilderDraft?.groups as QueryGroup[]) ?? [newGroup()],
  );
  const [freeText, setFreeText] = useState((queryBuilderDraft?.freeText as string) ?? '');
  const [parseErrors, setParseErrors] = useState<string[]>([]);

  const parseQuery = useQuery({
    ...crmSearchQueries.parse(freeText),
    enabled: !authLoading && canRead && freeText.includes(':'),
  });

  const searchQuery = useCrmGlobalSearch(
    { query: freeText, page_size: 25 },
    !authLoading && canRead && Boolean(freeText.trim()),
  );

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canRead) {
    return <EmptyState title={tSearch('accessDenied')} description={tSearch('accessDeniedHint')} />;
  }

  const addCondition = (groupId: string) => {
    setGroups((current) =>
      current.map((g) => (g.id === groupId ? { ...g, conditions: [...g.conditions, newCondition()] } : g)),
    );
  };

  const removeCondition = (groupId: string, conditionId: string) => {
    setGroups((current) =>
      current.map((g) =>
        g.id === groupId ? { ...g, conditions: g.conditions.filter((c) => c.id !== conditionId) } : g,
      ),
    );
  };

  const executeSearch = () => {
    setQueryBuilderDraft({ groups, freeText });
    if (parseQuery.data?.errors?.length) {
      setParseErrors(parseQuery.data.errors);
      return;
    }
    setParseErrors([]);
    router.push(`/workspaces/crm/search?q=${encodeURIComponent(freeText)}` as Route);
  };

  return (
    <div className="crm-search-advanced">
      <header className="crm-search-advanced__header">
        <div>
          <Link href={'/workspaces/crm/search' as Route} className="crm-search-page__link">
            ← {tSearch('title')}
          </Link>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-search-advanced__syntax">
        <label>
          <span>{t('freeText')}</span>
          <input
            type="text"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            placeholder={t('syntaxPlaceholder')}
          />
        </label>
        {parseQuery.data?.warnings?.map((w) => (
          <p key={w} className="crm-search-advanced__warning">{w}</p>
        ))}
        {parseErrors.map((e) => (
          <p key={e} className="crm-search-advanced__error">{e}</p>
        ))}
      </section>

      {groups.map((group) => (
        <section key={group.id} className="crm-search-advanced__group">
          <div className="crm-search-advanced__group-header">
            <select
              value={group.logic}
              onChange={(e) =>
                setGroups((current) =>
                  current.map((g) => (g.id === group.id ? { ...g, logic: e.target.value as 'and' | 'or' } : g)),
                )
              }
            >
              <option value="and">{t('logicAnd')}</option>
              <option value="or">{t('logicOr')}</option>
            </select>
            <Button type="button" variant="secondary" onClick={() => addCondition(group.id)}>
              {t('addCondition')}
            </Button>
          </div>
          {group.conditions.map((condition) => (
            <div key={condition.id} className="crm-search-advanced__condition">
              <select
                value={condition.field}
                onChange={(e) =>
                  setGroups((current) =>
                    current.map((g) =>
                      g.id === group.id
                        ? {
                            ...g,
                            conditions: g.conditions.map((c) =>
                              c.id === condition.id ? { ...c, field: e.target.value } : c,
                            ),
                          }
                        : g,
                    ),
                  )
                }
              >
                {FIELDS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
              <select
                value={condition.operator}
                onChange={(e) =>
                  setGroups((current) =>
                    current.map((g) =>
                      g.id === group.id
                        ? {
                            ...g,
                            conditions: g.conditions.map((c) =>
                              c.id === condition.id ? { ...c, operator: e.target.value } : c,
                            ),
                          }
                        : g,
                    ),
                  )
                }
              >
                {OPERATORS.map((op) => (
                  <option key={op} value={op}>{t(`operators.${op}` as 'operators.contains')}</option>
                ))}
              </select>
              <input
                type="text"
                value={condition.value}
                onChange={(e) =>
                  setGroups((current) =>
                    current.map((g) =>
                      g.id === group.id
                        ? {
                            ...g,
                            conditions: g.conditions.map((c) =>
                              c.id === condition.id ? { ...c, value: e.target.value } : c,
                            ),
                          }
                        : g,
                    ),
                  )
                }
                placeholder={t('valuePlaceholder')}
              />
              <button type="button" onClick={() => removeCondition(group.id, condition.id)} aria-label={t('remove')}>
                ×
              </button>
            </div>
          ))}
        </section>
      ))}

      <div className="crm-search-advanced__actions">
        <Button type="button" variant="secondary" onClick={() => setGroups((g) => [...g, newGroup()])}>
          {t('addGroup')}
        </Button>
        <Button type="button" onClick={executeSearch}>{t('execute')}</Button>
      </div>

      {searchQuery.isLoading && <LoadingState label={t('previewLoading')} />}
      {searchQuery.data && (
        <section className="crm-search-advanced__preview">
          <h2>{t('preview', { count: searchQuery.data.total })}</h2>
          <ul>
            {searchQuery.data.items.slice(0, 5).map((item) => (
              <li key={item.id}>{item.title} — {item.subtitle}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
