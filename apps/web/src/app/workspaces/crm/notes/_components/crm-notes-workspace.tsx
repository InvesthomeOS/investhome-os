'use client';

import type { Route } from 'next';
import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, TextArea } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { createNote, fetchActivity, fetchNotes } from '@/workspaces/crm/api/activities';
import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import { looksLikePayloadDump, noteFingerprint, stripHtml } from '@/workspaces/crm/contact-card/history-html';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { ActivityListParams, CrmActivitySummary } from '@/workspaces/crm/types/activities';

type OpsFilters = {
  search: string;
  ownerId: string;
  person: string;
  personId: string | null;
  projectGroup: string;
  dateFrom: string;
  dateTo: string;
};

type NoteForm = {
  body: string;
  contactId: string;
  contactLabel: string;
  projectGroup: string;
  agreementId: string;
};

const EMPTY_FILTERS: OpsFilters = {
  search: '',
  ownerId: '',
  person: '',
  personId: null,
  projectGroup: '',
  dateFrom: '',
  dateTo: '',
};

const EMPTY_FORM: NoteForm = {
  body: '',
  contactId: '',
  contactLabel: '',
  projectGroup: '',
  agreementId: '',
};

function personLabel(item: CrmActivitySummary, unresolved: string): string {
  const name = (item.person_name || item.entity_name || '').trim();
  if (name && !['contact', 'unknown person', 'unknown', 'kişi', 'kişiler'].includes(name.toLowerCase())) {
    return name;
  }
  if (item.entity_type === 'contact' && item.entity_id) return unresolved;
  return '—';
}

function projectUnit(item: CrmActivitySummary): string {
  const parts = [item.project_label, item.unit_number ? `Daire ${item.unit_number}` : null].filter(Boolean);
  return parts.join(' · ') || '—';
}

function authorLabel(item: CrmActivitySummary): string {
  const name = (item.created_by_name || item.owner_name || item.assigned_user_name || '').trim();
  if (name && !['contact', 'unknown person', 'unknown'].includes(name.toLowerCase())) return name;
  return '—';
}

function sourceLabel(item: CrmActivitySummary): string {
  const raw = (item.source || '').trim();
  if (!raw) return 'CRM';
  if (/^bitrix/i.test(raw)) return 'Bitrix';
  return raw;
}

function noteText(item: Pick<CrmActivitySummary, 'summary' | 'title'>): string {
  const raw = `${item.summary || ''}`.trim() || item.title || '';
  const text = stripHtml(raw.replace(/^(Yorum|Not|Historical Bitrix comment|Tarihsel Bitrix yorumu):\s*/i, ''));
  if (!text || looksLikePayloadDump(text)) return '';
  if (['historical bitrix comment', 'tarihsel bitrix yorumu', 'contact', 'yorum', 'note', 'not'].includes(text.toLowerCase())) {
    return '';
  }
  if (/^\(bitrix yorum satır[ıi].*metin bo[şs]\)$/i.test(text)) return '';
  return text;
}

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

function dedupeNotes(items: CrmActivitySummary[]): CrmActivitySummary[] {
  const seen = new Set<string>();
  const unique: CrmActivitySummary[] = [];
  for (const item of items) {
    const text = noteText(item);
    if (!text) continue;
    const key = noteFingerprint({
      id: item.id,
      entityId: item.entity_id,
      createdAt: item.created_at,
      text,
    });
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(item);
  }
  return unique;
}

function NoteDrawer({
  item,
  mode,
  form,
  canCreate,
  projects,
  purchases,
  personSuggestions,
  saving,
  onClose,
  onSave,
  onFormChange,
  onPersonQuery,
  onPickPerson,
}: {
  item: CrmActivitySummary | null;
  mode: 'detail' | 'create';
  form: NoteForm;
  canCreate: boolean;
  projects: Array<{ id: string; label: string }>;
  purchases: Array<{ id: string; label: string }>;
  personSuggestions: Array<{ id: string; display_name: string }>;
  saving: boolean;
  onClose: () => void;
  onSave: () => void;
  onFormChange: (patch: Partial<NoteForm>) => void;
  onPersonQuery: (value: string) => void;
  onPickPerson: (id: string, name: string) => void;
}) {
  const t = useTranslations('crm.notes');
  const locale = useLocale();
  const router = useRouter();
  const unresolved = t('unresolvedIdentity');
  const person = item ? personLabel(item, unresolved) : form.contactLabel || '—';
  const body = item ? noteText(item) : '';
  const purchaseHref =
    item?.agreement_id && item.entity_type === 'contact' && item.entity_id
      ? salesDetailUrl(item.entity_id, item.agreement_id)
      : form.agreementId && form.contactId
        ? salesDetailUrl(form.contactId, form.agreementId)
        : undefined;
  const contactHref =
    item?.entity_type === 'contact' && item.entity_id
      ? `/workspaces/crm/contacts/${item.entity_id}`
      : form.contactId
        ? `/workspaces/crm/contacts/${form.contactId}`
        : undefined;

  return (
    <aside className="crm-tasks__drawer" role="dialog" aria-label={t('drawer.title')} data-testid="crm-notes-drawer">
      <div className="crm-tasks__drawer-head">
        <h3>{mode === 'create' ? t('create') : t('drawer.title')}</h3>
        <button type="button" className="crm-tasks__link-btn" onClick={onClose}>
          {t('actions.close')}
        </button>
      </div>
      <div className="crm-tasks__drawer-body">
        {mode === 'detail' && item ? (
          <>
            <p className="crm-notes__body">{body || t('drawer.empty')}</p>
            <dl className="crm-tasks__kv">
              <dt>{t('drawer.author')}</dt>
              <dd>{authorLabel(item)}</dd>
              <dt>{t('drawer.when')}</dt>
              <dd>{formatWhen(item.created_at, locale)}</dd>
              <dt>{t('drawer.person')}</dt>
              <dd>{person}</dd>
              <dt>{t('drawer.project')}</dt>
              <dd>{projectUnit(item)}</dd>
              <dt>{t('drawer.source')}</dt>
              <dd>{sourceLabel(item)}</dd>
            </dl>
            <div className="crm-tasks__drawer-actions">
              {contactHref ? (
                <Button type="button" variant="primary" size="sm" onClick={() => router.push(contactHref as Route)}>
                  {t('actions.openContact')}
                </Button>
              ) : null}
              {purchaseHref ? (
                <Button type="button" variant="secondary" size="sm" onClick={() => router.push(purchaseHref as Route)}>
                  {t('actions.openPurchase')}
                </Button>
              ) : null}
            </div>
          </>
        ) : canCreate ? (
          <form
            className="crm-tasks__form"
            onSubmit={(event) => {
              event.preventDefault();
              onSave();
            }}
          >
            <TextArea
              label={t('form.body')}
              value={form.body}
              onChange={(event) => onFormChange({ body: event.target.value })}
              rows={6}
              required
            />
            <div className="crm-tasks__person-field">
              <Input
                label={t('form.person')}
                value={form.contactLabel}
                onChange={(event) => onPersonQuery(event.target.value)}
                placeholder={t('filters.personPlaceholder')}
                required
              />
              {personSuggestions.length > 0 ? (
                <ul className="crm-tasks__suggest">
                  {personSuggestions.map((contact) => (
                    <li key={contact.id}>
                      <button type="button" onClick={() => onPickPerson(contact.id, contact.display_name)}>
                        {contact.display_name}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <Select
              label={t('form.project')}
              value={form.projectGroup}
              onChange={(event) => onFormChange({ projectGroup: event.target.value })}
            >
              <option value="">{t('filters.any')}</option>
              {projects.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.label}
                </option>
              ))}
            </Select>
            <Select
              label={t('form.purchase')}
              value={form.agreementId}
              onChange={(event) => onFormChange({ agreementId: event.target.value })}
            >
              <option value="">{t('filters.any')}</option>
              {purchases.map((purchase) => (
                <option key={purchase.id} value={purchase.id}>
                  {purchase.label}
                </option>
              ))}
            </Select>
            <Button type="submit" size="sm" disabled={saving || !form.body.trim() || !form.contactId}>
              {saving ? t('form.saving') : t('form.save')}
            </Button>
          </form>
        ) : null}
      </div>
    </aside>
  );
}

export function CrmNotesWorkspace() {
  const t = useTranslations('crm.notes');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canRead, canCreate } = useCrmAccess();
  const canQuery = canRead && !authLoading;
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<OpsFilters>(EMPTY_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [personDraft, setPersonDraft] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<CrmActivitySummary | null>(null);
  const [mode, setMode] = useState<'detail' | 'create' | null>(null);
  const [form, setForm] = useState<NoteForm>(EMPTY_FORM);

  useEffect(() => {
    const timer = window.setTimeout(() => setFilters((prev) => ({ ...prev, search: searchDraft })), 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({
        ...prev,
        person: personDraft,
        personId: personDraft.trim() ? prev.personId : null,
      }));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [personDraft]);

  const apiFilters = useMemo<ActivityListParams>(() => {
    const params: ActivityListParams = { page: 1, page_size: 40 };
    if (filters.search.trim()) params.search = filters.search.trim();
    if (filters.personId) params.entity_id = filters.personId;
    else if (filters.person.trim()) params.contact_search = filters.person.trim();
    if (filters.projectGroup) params.project_group = filters.projectGroup;
    if (filters.ownerId) params.assigned_user_id = filters.ownerId;
    if (filters.dateFrom) params.date_from = `${filters.dateFrom}T00:00:00+03:00`;
    if (filters.dateTo) params.date_to = `${filters.dateTo}T23:59:59+03:00`;
    return params;
  }, [filters]);

  const listQuery = useInfiniteQuery({
    queryKey: activityQueryKeys.notes(apiFilters),
    queryFn: ({ pageParam = 1 }) => fetchNotes({ ...apiFilters, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => (lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined),
    enabled: canQuery,
  });

  const items = useMemo(
    () => dedupeNotes(listQuery.data?.pages.flatMap((page) => page.items) ?? []),
    [listQuery.data],
  );
  const total = listQuery.data?.pages[0]?.total ?? items.length;
  const selected =
    items.find((item) => item.id === selectedId) ??
    (selectedSnapshot?.id === selectedId ? selectedSnapshot : null);
  const detailQuery = useQuery({
    queryKey: activityQueryKeys.detail(selectedId || ''),
    queryFn: () => fetchActivity(selectedId || ''),
    enabled: Boolean(selectedId) && mode === 'detail',
  });
  const selectedDetail = selected
    ? {
        ...selected,
        summary: detailQuery.data?.description || detailQuery.data?.summary || selected.summary,
        person_name: selected.person_name || detailQuery.data?.person_name,
        project_label: selected.project_label || detailQuery.data?.project_label,
        project_group: selected.project_group || detailQuery.data?.project_group,
        unit_number: selected.unit_number || detailQuery.data?.unit_number,
        agreement_id: selected.agreement_id || detailQuery.data?.agreement_id,
        source: selected.source || detailQuery.data?.source,
        created_by_name: selected.created_by_name || detailQuery.data?.created_by_name,
      }
    : null;

  const projectsQuery = useQuery({
    queryKey: ['crm', 'agreements', 'note-projects'],
    queryFn: () => fetchAgreements({ page: 1, page_size: 1 }),
    enabled: canQuery,
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'note-filter'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: canQuery,
  });
  const personSuggestQuery = useQuery({
    ...contactQueries.list({ search: personDraft.trim() || form.contactLabel.trim(), page: 1, page_size: 8 }),
    enabled:
      canQuery &&
      (personDraft.trim().length >= 2 || (mode === 'create' && form.contactLabel.trim().length >= 2 && !form.contactId)),
  });
  const purchasesQuery = useQuery({
    queryKey: ['crm', 'agreements', 'note-purchases', form.contactId],
    queryFn: () => fetchAgreements({ contact_id: form.contactId, page: 1, page_size: 20 }),
    enabled: canQuery && Boolean(form.contactId) && mode === 'create',
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body = form.body.trim();
      if (!body || !form.contactId) throw new Error(t('form.personRequired'));
      await createNote({
        title: body.split('\n')[0].slice(0, 120),
        description: body,
        contact_id: form.contactId,
        project_group: form.projectGroup || undefined,
        agreement_id: form.agreementId || undefined,
      });
    },
    onSuccess: () => {
      setMode(null);
      setSelectedId(null);
      setSelectedSnapshot(null);
      setForm(EMPTY_FORM);
      void queryClient.invalidateQueries({ queryKey: ['crm'] });
    },
  });

  const patchFilters = (patch: Partial<OpsFilters>) => setFilters((prev) => ({ ...prev, ...patch }));
  const clearFilters = () => {
    setFilters(EMPTY_FILTERS);
    setSearchDraft('');
    setPersonDraft('');
  };

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setSelectedId(null);
    setSelectedSnapshot(null);
    setMode('create');
  };

  const openDetail = (item: CrmActivitySummary) => {
    setSelectedSnapshot(item);
    setSelectedId(item.id);
    setMode('detail');
  };

  if (authLoading) {
    return (
      <div className="crm-tasks crm-tasks--ops crm-notes" data-testid="crm-notes-workspace">
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

  if (listQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={listQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void listQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const users = usersQuery.data?.items ?? [];
  const projects = projectsQuery.data?.project_groups ?? [];
  const personSuggestions = personSuggestQuery.data?.items ?? [];
  const purchases = (purchasesQuery.data?.items ?? []).map((item) => ({
    id: item.id,
    label: [item.project_group_label, item.unit_number ? `Daire ${item.unit_number}` : null].filter(Boolean).join(' · '),
  }));

  return (
    <div className="crm-tasks crm-tasks--ops crm-notes" data-testid="crm-notes-workspace">
      <header className="crm-tasks__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-tasks__header-actions">
          <span className="crm-tasks__count">{t('pagination.total', { count: total })}</span>
          {canCreate ? (
            <Button type="button" size="sm" onClick={openCreate}>
              {t('create')}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="crm-tasks__filters" aria-label={t('filters.aria')}>
        <div className="crm-tasks__search">
          <Input
            label={t('filters.search')}
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder={t('filters.searchPlaceholder')}
          />
        </div>
        <div className="crm-tasks__person-field">
          <Input
            label={t('filters.person')}
            value={personDraft}
            onChange={(event) => {
              setPersonDraft(event.target.value);
              patchFilters({ personId: null });
            }}
            placeholder={t('filters.personPlaceholder')}
          />
          {personDraft.trim().length >= 2 && !filters.personId && personSuggestions.length > 0 ? (
            <ul className="crm-tasks__suggest">
              {personSuggestions.map((contact) => (
                <li key={contact.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setPersonDraft(contact.display_name);
                      patchFilters({ person: contact.display_name, personId: contact.id });
                    }}
                  >
                    {contact.display_name}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <Select
          label={t('filters.project')}
          value={filters.projectGroup}
          onChange={(event) => patchFilters({ projectGroup: event.target.value })}
        >
          <option value="">{t('filters.allProjects')}</option>
          {projects.map((group) => (
            <option key={group.id} value={group.id}>
              {group.label}
            </option>
          ))}
        </Select>
        <Select label={t('filters.owner')} value={filters.ownerId} onChange={(event) => patchFilters({ ownerId: event.target.value })}>
          <option value="">{t('filters.allOwners')}</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </Select>
        <Input
          label={t('filters.dateFrom')}
          type="date"
          value={filters.dateFrom}
          onChange={(event) => patchFilters({ dateFrom: event.target.value })}
        />
        <Input
          label={t('filters.dateTo')}
          type="date"
          value={filters.dateTo}
          onChange={(event) => patchFilters({ dateTo: event.target.value })}
        />
        <div className="crm-tasks__filter-actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t('filters.clear')}
          </Button>
        </div>
      </section>

      <div className="crm-tasks__table-wrap" role="region" aria-label={t('table.aria')}>
        {listQuery.isLoading ? (
          <div className="crm-tasks__skeleton" aria-hidden="true">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={index} className="crm-tasks__skeleton-row" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="crm-tasks__empty" data-testid="crm-notes-empty">
            <strong>{t('emptyTitle')}</strong>
            <p>{t('emptyDescription')}</p>
          </div>
        ) : (
          <table className="crm-tasks__table crm-tasks__table--ops">
            <thead>
              <tr>
                <th>{t('table.when')}</th>
                <th>{t('table.note')}</th>
                <th>{t('table.person')}</th>
                <th>{t('table.project')}</th>
                <th>{t('table.author')}</th>
                <th>{t('table.source')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className={`crm-tasks__row${selectedId === item.id ? ' is-selected' : ''}`}
                  onClick={() => openDetail(item)}
                  data-testid={`crm-note-row-${item.id}`}
                >
                  <td>{formatWhen(item.created_at, locale)}</td>
                  <td>
                    <span className="crm-notes__preview">{noteText(item)}</span>
                  </td>
                  <td>{personLabel(item, t('unresolvedIdentity'))}</td>
                  <td>{projectUnit(item)}</td>
                  <td>{authorLabel(item)}</td>
                  <td>{sourceLabel(item)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {listQuery.hasNextPage ? (
          <div className="crm-tasks__load-more">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void listQuery.fetchNextPage()}
              disabled={listQuery.isFetchingNextPage}
            >
              {listQuery.isFetchingNextPage ? tCommon('loading') : t('loadMore')}
            </Button>
          </div>
        ) : null}
      </div>

      {mode ? (
        <>
          <button type="button" className="crm-tasks__drawer-backdrop" aria-label={t('actions.close')} onClick={() => setMode(null)} />
          <NoteDrawer
            item={selectedDetail}
            mode={mode}
            form={form}
            canCreate={canCreate}
            projects={projects}
            purchases={purchases}
            personSuggestions={mode === 'detail' ? [] : personSuggestions}
            saving={saveMutation.isPending}
            onClose={() => setMode(null)}
            onSave={() => void saveMutation.mutate()}
            onFormChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            onPersonQuery={(value) => setForm((prev) => ({ ...prev, contactLabel: value, contactId: '', agreementId: '' }))}
            onPickPerson={(id, name) => setForm((prev) => ({ ...prev, contactId: id, contactLabel: name, agreementId: '' }))}
          />
        </>
      ) : null}
    </div>
  );
}
