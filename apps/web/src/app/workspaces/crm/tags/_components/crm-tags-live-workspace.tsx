'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
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
type TagForm = { name: string; description: string; status: 'active' | 'inactive' };

const PAGE_SIZES = [10, 25, 50] as const;
const EMPTY_FORM: TagForm = { name: '', description: '', status: 'active' };

const COPY = {
  tr: {
    title: 'Etiketler',
    subtitle: 'Canlı CRM etiketleri — kişi kartlarına bağlı gerçek kayıtlardır.',
    create: 'Yeni Etiket',
    edit: 'Düzenle',
    view: 'Görüntüle',
    more: 'Diğer',
    activate: 'Aktif yap',
    deactivate: 'Pasif yap',
    kpis: 'Etiket özeti',
    total: 'Toplam Etiket',
    tagged: 'Etiketli Kişi',
    untagged: 'Etiketsiz Kişi',
    search: 'Ara',
    searchPh: 'Etiket ara...',
    status: 'Durum',
    all: 'Tümü',
    active: 'Aktif',
    inactive: 'Pasif',
    clear: 'Filtreleri Temizle',
    tag: 'Etiket',
    people: 'Kişi Sayısı',
    updated: 'Son Güncelleme',
    actions: 'İşlem',
    table: 'Etiket listesi',
    empty: 'Henüz etiket yok',
    emptyBody: 'Yeni etiket oluşturarak kişi kayıtlarını gruplandırabilirsiniz.',
    close: 'Kapat',
    detail: 'Etiket detayı',
    created: 'Oluşturulma',
    taggedPeople: 'Etiketli kişiler',
    noPeople: 'Bu etikete bağlı kişi yok.',
    name: 'Etiket adı',
    namePh: 'Etiket adı',
    nameRequired: 'Etiket adı gerekli',
    description: 'Açıklama',
    save: 'Kaydet',
    saving: 'Kaydediliyor…',
    none: '—',
    countLabel: '{count} etiket',
    totalFooter: 'Toplam {count} etiket',
    pageSize: 'Sayfa başına',
    previous: 'Önceki',
    next: 'Sonraki',
    toastCreated: 'Etiket oluşturuldu',
    toastUpdated: 'Etiket güncellendi',
    toastStatus: 'Etiket durumu güncellendi',
    accessDenied: 'Etiketleri görüntüleme yetkiniz yok.',
  },
  en: {
    title: 'Tags',
    subtitle: 'Live CRM tags — real records linked to person cards.',
    create: 'New tag',
    edit: 'Edit',
    view: 'View',
    more: 'More',
    activate: 'Set active',
    deactivate: 'Set inactive',
    kpis: 'Tag summary',
    total: 'Total tags',
    tagged: 'Tagged people',
    untagged: 'Untagged people',
    search: 'Search',
    searchPh: 'Search tags...',
    status: 'Status',
    all: 'All',
    active: 'Active',
    inactive: 'Inactive',
    clear: 'Clear filters',
    tag: 'Tag',
    people: 'People',
    updated: 'Last updated',
    actions: 'Action',
    table: 'Tag list',
    empty: 'No tags yet',
    emptyBody: 'Create a new tag to group person records.',
    close: 'Close',
    detail: 'Tag detail',
    created: 'Created',
    taggedPeople: 'Tagged people',
    noPeople: 'No people are linked to this tag.',
    name: 'Tag name',
    namePh: 'Tag name',
    nameRequired: 'Tag name is required',
    description: 'Description',
    save: 'Save',
    saving: 'Saving…',
    none: '—',
    countLabel: '{count} tags',
    totalFooter: 'Total {count} tags',
    pageSize: 'Per page',
    previous: 'Previous',
    next: 'Next',
    toastCreated: 'Tag created',
    toastUpdated: 'Tag updated',
    toastStatus: 'Tag status updated',
    accessDenied: 'You do not have permission to view tags.',
  },
} as const;

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

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '•';
  return (parts[0][0] || '').toLocaleUpperCase('tr-TR');
}

function TagDrawer({
  mode,
  item,
  form,
  canWrite,
  saving,
  copy,
  locale,
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
  copy: (typeof COPY)['tr'];
  locale: string;
  onClose: () => void;
  onFormChange: (patch: Partial<TagForm>) => void;
  onSave: () => void;
  onEdit: () => void;
  onToggleStatus: () => void;
}) {
  const { openContact } = useContactCard();
  const detail = item && 'people' in item ? item : null;
  const isForm = mode === 'create' || mode === 'edit';

  return (
    <aside className="crm-ops-drawer" role="dialog" aria-label={copy.detail} data-testid="crm-tags-drawer">
      <div className="crm-ops-drawer__head">
        <div>
          <h2>{mode === 'create' ? copy.create : mode === 'edit' ? copy.edit : copy.detail}</h2>
          {item && !isForm ? <p>{item.name}</p> : null}
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={onClose}>
          {copy.close}
        </Button>
      </div>
      <div className="crm-ops-drawer__body">
        {isForm ? (
          <form
            className="crm-ops-form"
            onSubmit={(event) => {
              event.preventDefault();
              onSave();
            }}
          >
            <Input
              label={copy.name}
              value={form.name}
              onChange={(event) => onFormChange({ name: event.target.value })}
              placeholder={copy.namePh}
              required
            />
            <TextArea
              label={copy.description}
              value={form.description}
              onChange={(event) => onFormChange({ description: event.target.value })}
              rows={4}
            />
            <Select
              label={copy.status}
              value={form.status}
              onChange={(event) => onFormChange({ status: event.target.value as TagForm['status'] })}
            >
              <option value="active">{copy.active}</option>
              <option value="inactive">{copy.inactive}</option>
            </Select>
            <Button type="submit" size="sm" disabled={saving || !form.name.trim()}>
              {saving ? copy.saving : copy.save}
            </Button>
          </form>
        ) : item ? (
          <>
            <section className="crm-ops-section">
              <dl className="crm-ops-kv">
                <dt>{copy.name}</dt>
                <dd>{item.name}</dd>
                <dt>{copy.description}</dt>
                <dd>{item.description || copy.none}</dd>
                <dt>{copy.status}</dt>
                <dd>{item.status === 'inactive' ? copy.inactive : copy.active}</dd>
                <dt>{copy.people}</dt>
                <dd>{item.usage_count.toLocaleString(locale)}</dd>
                <dt>{copy.created}</dt>
                <dd>{formatWhen(item.created_at, locale)}</dd>
                <dt>{copy.updated}</dt>
                <dd>{formatWhen(item.updated_at, locale)}</dd>
              </dl>
            </section>
            <section className="crm-ops-section">
              <h2>{copy.taggedPeople}</h2>
              {detail?.people?.length ? (
                <ul className="crm-ops-peoplelist">
                  {detail.people.map((person) => (
                    <li key={person.id}>
                      <button type="button" onClick={() => openContact(person.id)}>
                        {person.display_name}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="crm-ops-muted">{copy.noPeople}</p>
              )}
            </section>
          </>
        ) : (
          <LoadingState />
        )}
      </div>
      {item && !isForm && canWrite ? (
        <div className="crm-ops-drawer__actions">
          <Button type="button" size="sm" onClick={onEdit}>
            {copy.edit}
          </Button>
          <Button type="button" size="sm" variant="secondary" onClick={onToggleStatus}>
            {item.status === 'inactive' ? copy.activate : copy.deactivate}
          </Button>
        </div>
      ) : null}
    </aside>
  );
}

export function CrmTagsLiveWorkspace() {
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const copy = COPY[locale];
  const { authLoading, canRead, canCreate, has } = useCrmAccess();
  const canWrite = canCreate || has('update');
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZES)[number]>(25);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mode, setMode] = useState<DrawerMode | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [form, setForm] = useState<TagForm>(EMPTY_FORM);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPage(1);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const tagsQuery = useQuery({
    ...crmQueries.tags({ search: search || undefined, status: status || undefined }),
    enabled: !authLoading && canRead,
    placeholderData: keepPreviousData,
  });
  const detailQuery = useQuery({
    queryKey: ['crm', 'tags', 'detail', selectedId],
    queryFn: () => fetchCrmTag(selectedId || ''),
    enabled: Boolean(selectedId) && mode === 'detail' && canRead,
  });

  const items = tagsQuery.data?.items ?? [];
  const stats = tagsQuery.data?.stats ?? { total_tags: 0, tagged_people: 0, untagged_people: 0 };
  const pages = Math.max(1, Math.ceil(items.length / pageSize));
  const currentPage = Math.min(page, pages);
  const pageItems = items.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const selected = useMemo(() => items.find((item) => item.id === selectedId) ?? null, [items, selectedId]);
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
      if (!payload.name) throw new Error(copy.nameRequired);
      if (mode === 'edit' && selectedId) return updateCrmTag(selectedId, payload);
      return createCrmTag(payload);
    },
    onSuccess: async (result) => {
      await invalidate();
      showToast(mode === 'edit' ? copy.toastUpdated : copy.toastCreated);
      setSelectedId(result.id);
      setMode('detail');
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (tag?: CrmTagItem | CrmTagDetail | null) => {
      const current = tag ?? drawerItem;
      if (!current) return null;
      return current.status === 'inactive' ? activateCrmTag(current.id) : deactivateCrmTag(current.id);
    },
    onSuccess: async () => {
      await invalidate();
      showToast(copy.toastStatus);
      if (mode) setMode('detail');
    },
  });

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setStatus('');
    setPage(1);
  };

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setSelectedId(null);
    setMenuId(null);
    setMode('create');
  };

  const openDetail = (tag: CrmTagItem) => {
    setSelectedId(tag.id);
    setMenuId(null);
    setMode('detail');
  };

  const openEdit = (tag?: CrmTagItem | CrmTagDetail | null) => {
    const current = tag ?? drawerItem;
    if (!current) return;
    setSelectedId(current.id);
    setForm({
      name: current.name,
      description: current.description || '',
      status: current.status === 'inactive' ? 'inactive' : 'active',
    });
    setMenuId(null);
    setMode('edit');
  };

  if (authLoading || (tagsQuery.isLoading && !tagsQuery.data)) {
    return <LoadingState />;
  }
  if (!canRead) {
    return <ErrorState title={copy.title} message={copy.accessDenied} />;
  }
  if (tagsQuery.isError) {
    return <ErrorState title={copy.title} message={tagsQuery.error.message} />;
  }

  return (
    <div className="crm-ops crm-ops--tags" data-testid="crm-tags-workspace">
      {toast ? (
        <div className="crm-ops-toast" role="status" aria-live="polite">
          {toast}
        </div>
      ) : null}

      <header className="crm-ops__header">
        <div className="crm-ops__title">
          <span className="crm-ops__title-icon" aria-hidden>
            <IhIcon name="sparkles" size={18} />
          </span>
          <div>
            <h1>{copy.title}</h1>
            <p>{copy.subtitle}</p>
          </div>
        </div>
        {canWrite ? (
          <div className="crm-ops__header-tools">
            <Button type="button" size="sm" onClick={openCreate}>
              {copy.create}
            </Button>
          </div>
        ) : null}
      </header>

      <section className="crm-ops-kpis" aria-label={copy.kpis}>
        <div className="crm-ops-kpi is-sky">
          <span className="crm-ops-kpis__icon" aria-hidden>
            <IhIcon name="documents" size={16} />
          </span>
          <strong data-testid="crm-tags-total">{stats.total_tags.toLocaleString(locale)}</strong>
          <span>{copy.total}</span>
        </div>
        <div className="crm-ops-kpi is-mint">
          <span className="crm-ops-kpis__icon" aria-hidden>
            <IhIcon name="users" size={16} />
          </span>
          <strong data-testid="crm-tags-tagged">{stats.tagged_people.toLocaleString(locale)}</strong>
          <span>{copy.tagged}</span>
        </div>
        <div className="crm-ops-kpi is-purple">
          <span className="crm-ops-kpis__icon" aria-hidden>
            <IhIcon name="user" size={16} />
          </span>
          <strong data-testid="crm-tags-untagged">{stats.untagged_people.toLocaleString(locale)}</strong>
          <span>{copy.untagged}</span>
        </div>
      </section>

      <section className="crm-ops-filtercard" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.searchPh}
        />
        <Select
          label={copy.status}
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{copy.all}</option>
          <option value="active">{copy.active}</option>
          <option value="inactive">{copy.inactive}</option>
        </Select>
        <div className="crm-ops-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {copy.clear}
          </Button>
          {canWrite ? (
            <Button type="button" size="sm" onClick={openCreate}>
              {copy.create}
            </Button>
          ) : null}
        </div>
      </section>

      <section className="crm-ops-tablecard" aria-label={copy.table}>
        <div className="crm-ops-tablecard__head">
          <strong>{copy.countLabel.replace('{count}', String(items.length.toLocaleString(locale)))}</strong>
        </div>
        {items.length === 0 ? (
          <div className="crm-ops-empty" data-testid="crm-tags-empty">
            <strong>{copy.empty}</strong>
            <p>{copy.emptyBody}</p>
          </div>
        ) : (
          <div className="crm-ops-table-wrap">
            <table className="crm-ops-table">
              <thead>
                <tr>
                  <th>{copy.tag}</th>
                  <th>{copy.people}</th>
                  <th>{copy.status}</th>
                  <th>{copy.updated}</th>
                  <th>{copy.actions}</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((tag) => (
                  <tr
                    key={tag.id}
                    className="crm-ops-row"
                    data-testid={`tag-row-${tag.id}`}
                    onClick={() => openDetail(tag)}
                  >
                    <td>
                      <div className="crm-ops-company">
                        <span className="crm-ops-logo" aria-hidden>
                          {initials(tag.name)}
                        </span>
                        <div>
                          <strong>{tag.name}</strong>
                          {tag.description ? <div className="crm-ops-tagdesc">{tag.description}</div> : null}
                        </div>
                      </div>
                    </td>
                    <td>
                      <Link
                        href={`/workspaces/crm/contacts?tag=${tag.id}` as Route}
                        className="crm-ops-countlink"
                        onClick={(event) => event.stopPropagation()}
                      >
                        {tag.usage_count.toLocaleString(locale)}
                      </Link>
                    </td>
                    <td>
                      <span className={`crm-ops-badge ${tag.status === 'inactive' ? 'is-inactive' : 'is-active'}`}>
                        {tag.status === 'inactive' ? copy.inactive : copy.active}
                      </span>
                    </td>
                    <td>{formatWhen(tag.updated_at || tag.created_at, locale)}</td>
                    <td>
                      <div className="crm-ops-actions">
                        <button
                          type="button"
                          className="crm-ops-action"
                          onClick={(event) => {
                            event.stopPropagation();
                            openDetail(tag);
                          }}
                        >
                          {copy.view}
                        </button>
                        {canWrite ? (
                          <div className="crm-ops-more">
                            <button
                              type="button"
                              className="crm-ops-action"
                              aria-label={copy.more}
                              onClick={(event) => {
                                event.stopPropagation();
                                setMenuId((current) => (current === tag.id ? null : tag.id));
                              }}
                            >
                              ⋯
                            </button>
                            {menuId === tag.id ? (
                              <div className="crm-ops-more__panel">
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    openEdit(tag);
                                  }}
                                >
                                  {copy.edit}
                                </button>
                                <button
                                  type="button"
                                  disabled={statusMutation.isPending}
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    setMenuId(null);
                                    setSelectedId(tag.id);
                                    void statusMutation.mutate(tag);
                                  }}
                                >
                                  {tag.status === 'inactive' ? copy.activate : copy.deactivate}
                                </button>
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="crm-ops-pager">
          <span>{copy.totalFooter.replace('{count}', String(items.length.toLocaleString(locale)))}</span>
          <div>
            <span>{copy.pageSize}</span>
            {PAGE_SIZES.map((size) => (
              <button
                key={size}
                type="button"
                className={pageSize === size ? 'is-active' : undefined}
                onClick={() => {
                  setPageSize(size);
                  setPage(1);
                }}
              >
                {size}
              </button>
            ))}
            <Button variant="secondary" size="sm" disabled={currentPage <= 1} onClick={() => setPage((value) => value - 1)}>
              {copy.previous}
            </Button>
            <button type="button" className="is-active" disabled>
              {currentPage}
            </button>
            <Button variant="secondary" size="sm" disabled={currentPage >= pages} onClick={() => setPage((value) => value + 1)}>
              {copy.next}
            </Button>
          </div>
        </div>
      </section>

      {mode ? (
        <>
          <button type="button" className="crm-ops-drawer-backdrop" aria-label={copy.close} onClick={() => setMode(null)} />
          <TagDrawer
            mode={mode}
            item={drawerItem}
            form={form}
            canWrite={canWrite}
            saving={saveMutation.isPending || statusMutation.isPending}
            copy={copy}
            locale={locale}
            onClose={() => setMode(null)}
            onFormChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            onSave={() => void saveMutation.mutate()}
            onEdit={() => openEdit()}
            onToggleStatus={() => void statusMutation.mutate()}
          />
        </>
      ) : null}
    </div>
  );
}
