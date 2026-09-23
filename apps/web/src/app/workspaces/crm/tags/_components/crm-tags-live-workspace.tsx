'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, StatusChip, TextArea } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import {
  activateCrmTag,
  createCrmTag,
  deactivateCrmTag,
  fetchCrmTag,
  updateCrmTag,
  type CrmTagDetail,
  type CrmTagItem,
} from '@/workspaces/crm/api/crm';

type DrawerMode = 'detail' | 'create' | 'edit';

type TagForm = {
  name: string;
  description: string;
  status: 'active' | 'inactive';
};

const EMPTY_FORM: TagForm = {
  name: '',
  description: '',
  status: 'active',
};

function formatWhen(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function TagDrawer({
  mode,
  item,
  form,
  canWrite,
  saving,
  onClose,
  onFormChange,
  onSave,
  onEdit,
  onToggleStatus,
}: {
  mode: DrawerMode;
  item: CrmTagDetail | CrmTagItem | null;
  form: TagForm;
  canWrite: boolean;
  saving: boolean;
  onClose: () => void;
  onFormChange: (patch: Partial<TagForm>) => void;
  onSave: () => void;
  onEdit: () => void;
  onToggleStatus: () => void;
}) {
  const t = useTranslations('crm.tags');
  const locale = useLocale();
  const { openContact } = useContactCard();
  const detail = item && 'people' in item ? item : null;
  const isForm = mode === 'create' || mode === 'edit';

  return (
    <aside className="crm-tasks__drawer" role="dialog" aria-label={t('drawer.title')} data-testid="crm-tags-drawer">
      <div className="crm-tasks__drawer-head">
        <h3>{mode === 'create' ? t('create') : mode === 'edit' ? t('edit') : t('drawer.title')}</h3>
        <button type="button" className="crm-tasks__link-btn" onClick={onClose}>
          {t('actions.close')}
        </button>
      </div>
      <div className="crm-tasks__drawer-body">
        {isForm ? (
          <form
            className="crm-tasks__form"
            onSubmit={(event) => {
              event.preventDefault();
              onSave();
            }}
          >
            <Input
              label={t('form.name')}
              value={form.name}
              onChange={(event) => onFormChange({ name: event.target.value })}
              placeholder={t('form.namePlaceholder')}
              required
            />
            <TextArea
              label={t('form.description')}
              value={form.description}
              onChange={(event) => onFormChange({ description: event.target.value })}
              rows={4}
            />
            <Select
              label={t('form.status')}
              value={form.status}
              onChange={(event) => onFormChange({ status: event.target.value as TagForm['status'] })}
            >
              <option value="active">{t('status.active')}</option>
              <option value="inactive">{t('status.inactive')}</option>
            </Select>
            <Button type="submit" size="sm" disabled={saving || !form.name.trim()}>
              {saving ? t('form.saving') : t('form.save')}
            </Button>
          </form>
        ) : item ? (
          <>
            <dl className="crm-tasks__kv">
              <dt>{t('form.name')}</dt>
              <dd>{item.name}</dd>
              <dt>{t('form.description')}</dt>
              <dd>{item.description || '—'}</dd>
              <dt>{t('columns.status')}</dt>
              <dd>{item.status === 'inactive' ? t('status.inactive') : t('status.active')}</dd>
              <dt>{t('columns.people')}</dt>
              <dd>{item.usage_count}</dd>
              <dt>{t('drawer.created')}</dt>
              <dd>{formatWhen(item.created_at, locale)}</dd>
              <dt>{t('drawer.updated')}</dt>
              <dd>{formatWhen(item.updated_at, locale)}</dd>
            </dl>
            <div className="crm-tags__people">
              <h4>{t('drawer.people')}</h4>
              {detail?.people?.length ? (
                <ul>
                  {detail.people.map((person) => (
                    <li key={person.id}>
                      <button type="button" onClick={() => openContact(person.id)}>
                        {person.display_name}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{t('drawer.noPeople')}</p>
              )}
            </div>
            {canWrite ? (
              <div className="crm-tasks__drawer-actions">
                <Button type="button" size="sm" onClick={onEdit}>
                  {t('edit')}
                </Button>
                <Button type="button" size="sm" variant="secondary" onClick={onToggleStatus}>
                  {item.status === 'inactive' ? t('activate') : t('deactivate')}
                </Button>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </aside>
  );
}

export function CrmTagsLiveWorkspace() {
  const t = useTranslations('crm.tags');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canRead, canCreate, has } = useCrmAccess();
  const canWrite = canCreate || has('update');
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mode, setMode] = useState<DrawerMode | null>(null);
  const [form, setForm] = useState<TagForm>(EMPTY_FORM);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchDraft.trim()), 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const tagsQuery = useQuery({
    ...crmQueries.tags({ search: search || undefined, status: status || undefined }),
    enabled: !authLoading && canRead,
  });
  const detailQuery = useQuery({
    queryKey: ['crm', 'tags', 'detail', selectedId],
    queryFn: () => fetchCrmTag(selectedId || ''),
    enabled: Boolean(selectedId) && mode === 'detail' && canRead,
  });

  const items = tagsQuery.data?.items ?? [];
  const stats = tagsQuery.data?.stats ?? { total_tags: 0, tagged_people: 0, untagged_people: 0 };
  const selected = useMemo(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  );
  const drawerItem = detailQuery.data ?? selected;

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2400);
  };

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ['crm', 'tags'] });
    await queryClient.invalidateQueries({ queryKey: ['crm', 'contacts'] });
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim(),
        status: form.status,
      };
      if (!payload.name) throw new Error(t('form.nameRequired'));
      if (mode === 'edit' && selectedId) {
        return updateCrmTag(selectedId, payload);
      }
      return createCrmTag(payload);
    },
    onSuccess: async (result) => {
      await invalidate();
      showToast(mode === 'edit' ? t('toast.updated') : t('toast.created'));
      setSelectedId(result.id);
      setMode('detail');
    },
  });

  const statusMutation = useMutation({
    mutationFn: async () => {
      if (!selectedId || !drawerItem) return null;
      return drawerItem.status === 'inactive' ? activateCrmTag(selectedId) : deactivateCrmTag(selectedId);
    },
    onSuccess: async () => {
      await invalidate();
      showToast(t('toast.statusChanged'));
      setMode('detail');
    },
  });

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setStatus('');
  };

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setSelectedId(null);
    setMode('create');
  };

  const openDetail = (tag: CrmTagItem) => {
    setSelectedId(tag.id);
    setMode('detail');
  };

  const openEdit = () => {
    if (!drawerItem) return;
    setForm({
      name: drawerItem.name,
      description: drawerItem.description || '',
      status: drawerItem.status === 'inactive' ? 'inactive' : 'active',
    });
    setMode('edit');
  };

  if (authLoading || tagsQuery.isLoading) {
    return (
      <div className="crm-tasks crm-tasks--ops crm-tags" data-testid="crm-tags-workspace">
        <div className="crm-tasks__skeleton" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="crm-tasks__skeleton-row" />
          ))}
        </div>
      </div>
    );
  }

  if (!canRead) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (tagsQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={tagsQuery.error.message}
        action={
          <Button type="button" onClick={() => void tagsQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  return (
    <div className="crm-tasks crm-tasks--ops crm-tags" data-testid="crm-tags-workspace">
      {toast ? (
        <div className="crm-tags__toast" role="status" aria-live="polite">
          {toast}
        </div>
      ) : null}

      <header className="crm-tasks__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-tags__kpi-row" aria-label={t('kpis.aria')}>
        <article className="crm-tags__kpi">
          <span>{t('kpis.total')}</span>
          <strong data-testid="crm-tags-total">{stats.total_tags.toLocaleString(locale)}</strong>
        </article>
        <article className="crm-tags__kpi">
          <span>{t('kpis.tagged')}</span>
          <strong data-testid="crm-tags-tagged">{stats.tagged_people.toLocaleString(locale)}</strong>
        </article>
        <article className="crm-tags__kpi">
          <span>{t('kpis.untagged')}</span>
          <strong data-testid="crm-tags-untagged">{stats.untagged_people.toLocaleString(locale)}</strong>
        </article>
      </section>

      <section className="crm-tasks__filters" aria-label={t('filters.aria')}>
        <div className="crm-tasks__search">
          <Input
            label={t('filters.search')}
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder={t('filters.searchPlaceholder')}
          />
        </div>
        <Select
          label={t('filters.status')}
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">{t('filters.anyStatus')}</option>
          <option value="active">{t('status.active')}</option>
          <option value="inactive">{t('status.inactive')}</option>
        </Select>
        <div className="crm-tasks__filter-actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t('filters.clear')}
          </Button>
          {canWrite ? (
            <Button type="button" size="sm" onClick={openCreate}>
              {t('create')}
            </Button>
          ) : null}
        </div>
      </section>

      <div className="crm-tasks__table-wrap" role="region" aria-label={t('table.aria')}>
        {items.length === 0 ? (
          <div className="crm-tasks__empty" data-testid="crm-tags-empty">
            <strong>{t('empty.title')}</strong>
            <p>{t('empty.description')}</p>
          </div>
        ) : (
          <table className="crm-tasks__table crm-tasks__table--ops">
            <thead>
              <tr>
                <th>{t('columns.name')}</th>
                <th>{t('columns.people')}</th>
                <th>{t('columns.status')}</th>
                <th>{t('columns.updated')}</th>
                <th>{t('columns.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((tag) => (
                <tr
                  key={tag.id}
                  className={`crm-tasks__row${selectedId === tag.id ? ' is-selected' : ''}`}
                  onClick={() => openDetail(tag)}
                  data-testid={`tag-row-${tag.id}`}
                >
                  <td>
                    <strong>{tag.name}</strong>
                    {tag.description ? <div className="crm-tags__hint">{tag.description}</div> : null}
                  </td>
                  <td>{tag.usage_count.toLocaleString(locale)}</td>
                  <td>
                    <StatusChip tone={tag.status === 'inactive' ? 'default' : 'success'}>
                      {tag.status === 'inactive' ? t('status.inactive') : t('status.active')}
                    </StatusChip>
                  </td>
                  <td>{formatWhen(tag.updated_at || tag.created_at, locale)}</td>
                  <td>
                    <button
                      type="button"
                      className="crm-tasks__link-btn"
                      onClick={(event) => {
                        event.stopPropagation();
                        openDetail(tag);
                      }}
                    >
                      {t('view')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {mode ? (
        <>
          <button
            type="button"
            className="crm-tasks__drawer-backdrop"
            aria-label={t('actions.close')}
            onClick={() => setMode(null)}
          />
          <TagDrawer
            mode={mode}
            item={drawerItem}
            form={form}
            canWrite={canWrite}
            saving={saveMutation.isPending || statusMutation.isPending}
            onClose={() => setMode(null)}
            onFormChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            onSave={() => void saveMutation.mutate()}
            onEdit={openEdit}
            onToggleStatus={() => void statusMutation.mutate()}
          />
        </>
      ) : null}
    </div>
  );
}
