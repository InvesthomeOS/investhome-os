'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, Input, LoadingState, Select, StatusChip } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';

import { TAG_COLOR_HEX, type TagColorKey, type TagRecord } from '../tags-model';

const COLOR_KEYS: TagColorKey[] = ['navy', 'cyan', 'green', 'amber', 'rose', 'violet', 'slate'];
const CATEGORY_KEYS = ['lifecycle', 'interest', 'priority', 'source', 'custom'] as const;

function mapColor(raw: string | null | undefined): TagColorKey {
  const value = (raw ?? '').trim().toLowerCase();
  if (COLOR_KEYS.includes(value as TagColorKey)) return value as TagColorKey;
  const hexMatch = Object.entries(TAG_COLOR_HEX).find(([, hex]) => String(hex).toLowerCase() === value);
  if (hexMatch) return hexMatch[0] as TagColorKey;
  return 'slate';
}

function ColorBadge({ color, label }: { color: TagColorKey; label: string }) {
  return (
    <span className="crm-tags__badge" style={{ backgroundColor: TAG_COLOR_HEX[color] }}>
      {label}
    </span>
  );
}

export function CrmTagsLiveWorkspace() {
  const t = useTranslations('crm.tags');
  const tCrm = useTranslations('crm');
  const locale = useLocale();
  const { authLoading, canRead: canView } = useCrmAccess();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [color, setColor] = useState('');

  const tagsQuery = useQuery({
    ...crmQueries.tags(),
    enabled: !authLoading && canView,
  });

  const tags = useMemo<TagRecord[]>(
    () =>
      (tagsQuery.data?.items ?? []).map((item) => ({
        id: item.id,
        name: item.name,
        color: mapColor(item.color),
        usageCount: item.usage_count,
        category: 'custom',
        description: '',
      })),
    [tagsQuery.data?.items],
  );

  const filtered = useMemo(() => {
    return tags.filter((tag) => {
      if (category && tag.category !== category) return false;
      if (color && tag.color !== color) return false;
      if (search) {
        const q = search.trim().toLowerCase();
        if (!tag.name.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [tags, search, category, color]);

  if (authLoading || tagsQuery.isLoading) {
    return (
      <div className="crm-tags" data-testid="crm-tags-workspace">
        <LoadingState label={t('title')} />
      </div>
    );
  }

  if (!canView) {
    return (
      <div className="crm-tags" data-testid="crm-tags-workspace">
        <ErrorState title={tCrm('accessDenied')} message={tCrm('accessDeniedHint')} />
      </div>
    );
  }

  if (tagsQuery.isError) {
    return (
      <div className="crm-tags" data-testid="crm-tags-workspace">
        <ErrorState title={tCrm('loadFailed')} message={tCrm('accessDeniedHint')} />
      </div>
    );
  }

  return (
    <div className="crm-tags" data-testid="crm-tags-workspace">
      <header className="crm-tags__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-tags__toolbar" aria-label={t('filters.aria')}>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('filters.searchPlaceholder')}
          aria-label={t('filters.search')}
        />
        <Select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label={t('filters.category')}
        >
          <option value="">{t('filters.anyCategory')}</option>
          {CATEGORY_KEYS.map((key) => (
            <option key={key} value={key}>
              {t(`categories.${key}`)}
            </option>
          ))}
        </Select>
        <Select value={color} onChange={(e) => setColor(e.target.value)} aria-label={t('filters.color')}>
          <option value="">{t('filters.anyColor')}</option>
          {COLOR_KEYS.map((key) => (
            <option key={key} value={key}>
              {t(`colors.${key}`)}
            </option>
          ))}
        </Select>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title={t('empty.title')} description={t('empty.description')} />
      ) : (
        <ul className="crm-tags__list" aria-label={t('listAria')}>
          {filtered.map((tag) => (
            <li key={tag.id} className="crm-tags__row" data-testid={`tag-row-${tag.id}`}>
              <ColorBadge color={tag.color} label={tag.name} />
              <div className="crm-tags__copy">
                <strong>{tag.name}</strong>
                <em>
                  {t(`categories.${tag.category}`)} · {t('usageCount', { count: tag.usageCount })}
                </em>
              </div>
              <StatusChip tone="default" className="crm-tags__usage">
                {tag.usageCount.toLocaleString(locale)}
              </StatusChip>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
