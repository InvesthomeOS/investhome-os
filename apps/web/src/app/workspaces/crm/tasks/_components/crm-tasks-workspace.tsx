'use client';

import type { Route } from 'next';
import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter, useSearchParams } from 'next/navigation';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, StatusChip, TextArea } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { completeTask, createTask, fetchActivity, fetchTasks, updateActivity } from '@/workspaces/crm/api/activities';
import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type {
  ActivityListParams,
  CrmActivityPriority,
  CrmActivitySummary,
  CrmTaskStatus,
} from '@/workspaces/crm/types/activities';

import '../tasks.css';

type WorkspaceStatus = 'open' | 'in_progress' | 'completed' | 'cancelled';
type PriorityKey = 'low' | 'medium' | 'high' | 'critical';

type OpsFilters = {
  search: string;
  status: string;
  ownerId: string;
  person: string;
  personId: string | null;
  projectGroup: string;
  priority: string;
  dateFrom: string;
  dateTo: string;
  dueBucket: string;
};

type TaskForm = {
  title: string;
  description: string;
  contactId: string;
  contactLabel: string;
  projectGroup: string;
  agreementId: string;
  ownerId: string;
  dueDate: string;
  priority: PriorityKey;
  status: WorkspaceStatus;
};

const EMPTY_FILTERS: OpsFilters = {
  search: '',
  status: '',
  ownerId: '',
  person: '',
  personId: null,
  projectGroup: '',
  priority: '',
  dateFrom: '',
  dateTo: '',
  dueBucket: '',
};

const EMPTY_FORM: TaskForm = {
  title: '',
  description: '',
  contactId: '',
  contactLabel: '',
  projectGroup: '',
  agreementId: '',
  ownerId: '',
  dueDate: '',
  priority: 'medium',
  status: 'open',
};

const WORKSPACE_STATUSES: WorkspaceStatus[] = ['open', 'in_progress', 'completed', 'cancelled'];
const PRIORITIES: PriorityKey[] = ['low', 'medium', 'high', 'critical'];

function personLabel(item: CrmActivitySummary, unresolved: string): string {
  const name = (item.person_name || item.entity_name || '').trim();
  if (name && !['contact', 'unknown person', 'unknown'].includes(name.toLowerCase())) return name;
  if (item.entity_type === 'contact' && item.entity_id) return unresolved;
  return '—';
}

function projectUnit(item: CrmActivitySummary): string {
  const parts = [item.project_label, item.unit_number ? `Daire ${item.unit_number}` : null].filter(Boolean);
  return parts.join(' · ') || '—';
}

function workspaceStatus(item: CrmActivitySummary): WorkspaceStatus {
  const value = item.workspace_status;
  if (value === 'in_progress' || value === 'completed' || value === 'cancelled') return value;
  return 'open';
}

function priorityKey(value: string | null | undefined): PriorityKey {
  if (value === 'low' || value === 'high' || value === 'critical') return value;
  return 'medium';
}

function formatDate(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

function dueTone(item: CrmActivitySummary): 'overdue' | 'today' | 'done' | 'neutral' {
  const status = workspaceStatus(item);
  if (status === 'completed' || status === 'cancelled') return 'done';
  if (!item.due_date) return 'neutral';
  const due = new Date(item.due_date);
  if (Number.isNaN(due.getTime())) return 'neutral';
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate()).getTime();
  if (dueDay < start) return 'overdue';
  if (dueDay === start) return 'today';
  return 'neutral';
}

function toDuePayload(date: string): string | undefined {
  if (!date) return undefined;
  return `${date}T12:00:00+03:00`;
}

function dateInputValue(value: string | null | undefined): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

function statusToApi(status: WorkspaceStatus): { task_status: CrmTaskStatus; status: 'planned' | 'in_progress' | 'completed' | 'cancelled' } {
  if (status === 'in_progress') return { task_status: 'in_progress', status: 'in_progress' };
  if (status === 'completed') return { task_status: 'completed', status: 'completed' };
  if (status === 'cancelled') return { task_status: 'cancelled', status: 'cancelled' };
  return { task_status: 'not_started', status: 'planned' };
}

function TaskDrawer({
  item,
  mode,
  form,
  canManage,
  users,
  projects,
  purchases,
  personSuggestions,
  saving,
  completing,
  onClose,
  onEdit,
  onComplete,
  onSave,
  onFormChange,
  onPersonQuery,
  onPickPerson,
}: {
  item: CrmActivitySummary | null;
  mode: 'detail' | 'create' | 'edit';
  form: TaskForm;
  canManage: boolean;
  users: Array<{ id: string; full_name: string }>;
  projects: Array<{ id: string; label: string }>;
  purchases: Array<{ id: string; label: string }>;
  personSuggestions: Array<{ id: string; display_name: string }>;
  saving: boolean;
  completing: boolean;
  onClose: () => void;
  onEdit: () => void;
  onComplete: () => void;
  onSave: () => void;
  onFormChange: (patch: Partial<TaskForm>) => void;
  onPersonQuery: (value: string) => void;
  onPickPerson: (id: string, name: string) => void;
}) {
  const t = useTranslations('crm.tasks');
  const locale = useLocale();
  const router = useRouter();
  const unresolved = t('unresolvedIdentity');
  const person = item ? personLabel(item, unresolved) : form.contactLabel || '—';
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
    <aside className="crm-tasks__drawer" role="dialog" aria-label={t('drawer.title')} data-testid="crm-tasks-drawer">
      <div className="crm-tasks__drawer-head">
        <h3>{mode === 'create' ? t('create') : mode === 'edit' ? t('actions.edit') : t('drawer.title')}</h3>
        <button type="button" className="crm-tasks__link-btn" onClick={onClose}>
          {t('actions.close')}
        </button>
      </div>
      <div className="crm-tasks__drawer-body">
        {mode === 'detail' && item ? (
          <>
            <h4>{item.title}</h4>
            <dl className="crm-tasks__kv">
              <dt>{t('drawer.person')}</dt>
              <dd>{person}</dd>
              <dt>{t('drawer.project')}</dt>
              <dd>{item.project_label || '—'}</dd>
              <dt>{t('drawer.unit')}</dt>
              <dd>{item.unit_number || '—'}</dd>
              <dt>{t('drawer.owner')}</dt>
              <dd>{item.assigned_user_name || item.owner_name || '—'}</dd>
              <dt>{t('drawer.created')}</dt>
              <dd>{formatDate(item.created_at, locale)}</dd>
              <dt>{t('drawer.due')}</dt>
              <dd>{formatDate(item.due_date, locale)}</dd>
              <dt>{t('drawer.priority')}</dt>
              <dd>{t(`priority.${priorityKey(item.priority)}`)}</dd>
              <dt>{t('drawer.status')}</dt>
              <dd>{t(`workspaceStatus.${workspaceStatus(item)}`)}</dd>
              <dt>{t('drawer.source')}</dt>
              <dd>
                {[item.source, item.source_task_status, item.source_priority].filter(Boolean).join(' · ') || 'CRM'}
              </dd>
            </dl>
            <section>
              <h4>{t('drawer.description')}</h4>
              <p>{item.summary || t('drawer.noDescription')}</p>
            </section>
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
              {canManage && workspaceStatus(item) !== 'completed' ? (
                <Button type="button" size="sm" onClick={onComplete} disabled={completing}>
                  {t('actions.complete')}
                </Button>
              ) : null}
              {canManage ? (
                <Button type="button" variant="secondary" size="sm" onClick={onEdit}>
                  {t('actions.edit')}
                </Button>
              ) : null}
            </div>
          </>
        ) : (
          <form
            className="crm-tasks__form"
            onSubmit={(event) => {
              event.preventDefault();
              onSave();
            }}
          >
            <Input
              label={t('form.title')}
              value={form.title}
              onChange={(event) => onFormChange({ title: event.target.value })}
              required
            />
            <TextArea
              label={t('form.description')}
              value={form.description}
              onChange={(event) => onFormChange({ description: event.target.value })}
              rows={4}
            />
            <div className="crm-tasks__person-field">
              <Input
                label={t('form.person')}
                value={form.contactLabel}
                onChange={(event) => onPersonQuery(event.target.value)}
                placeholder={t('filters.personPlaceholder')}
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
            <Select
              label={t('form.owner')}
              value={form.ownerId}
              onChange={(event) => onFormChange({ ownerId: event.target.value })}
            >
              <option value="">{t('filters.any')}</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name}
                </option>
              ))}
            </Select>
            <Input
              label={t('form.due')}
              type="date"
              value={form.dueDate}
              onChange={(event) => onFormChange({ dueDate: event.target.value })}
            />
            <Select
              label={t('form.priority')}
              value={form.priority}
              onChange={(event) => onFormChange({ priority: event.target.value as PriorityKey })}
            >
              {PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {t(`priority.${priority}`)}
                </option>
              ))}
            </Select>
            <Select
              label={t('form.status')}
              value={form.status}
              onChange={(event) => onFormChange({ status: event.target.value as WorkspaceStatus })}
            >
              {WORKSPACE_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {t(`workspaceStatus.${status}`)}
                </option>
              ))}
            </Select>
            <div className="crm-tasks__drawer-actions">
              <Button type="submit" size="sm" disabled={saving || !form.title.trim()}>
                {saving ? t('form.saving') : t('form.save')}
              </Button>
            </div>
          </form>
        )}
      </div>
    </aside>
  );
}

export function CrmTasksWorkspace() {
  const t = useTranslations('crm.tasks');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canRead: canView, canManageTasks } = useCrmAccess();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<OpsFilters>({
    ...EMPTY_FILTERS,
    status: searchParams.get('status') || '',
    dueBucket: searchParams.get('due') || '',
  });
  const [searchDraft, setSearchDraft] = useState('');
  const [personDraft, setPersonDraft] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<CrmActivitySummary | null>(null);
  const [mode, setMode] = useState<'detail' | 'create' | 'edit' | null>(null);
  const [form, setForm] = useState<TaskForm>(EMPTY_FORM);

  const canQuery = !authLoading && canView;

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
    if (filters.status) params.workspace_status = filters.status;
    if (filters.priority) params.priority = filters.priority as CrmActivityPriority;
    if (filters.dateFrom) params.due_from = `${filters.dateFrom}T00:00:00+03:00`;
    if (filters.dateTo) params.due_to = `${filters.dateTo}T23:59:59+03:00`;
    if (filters.dueBucket) params.due_bucket = filters.dueBucket;
    return params;
  }, [filters]);

  const listQuery = useInfiniteQuery({
    queryKey: activityQueryKeys.tasks(apiFilters),
    queryFn: ({ pageParam = 1 }) => fetchTasks({ ...apiFilters, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => (lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined),
    enabled: canQuery,
  });

  const items = useMemo(() => listQuery.data?.pages.flatMap((page) => page.items) ?? [], [listQuery.data]);
  const counters = listQuery.data?.pages[0]?.counters;
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
      }
    : null;

  const projectsQuery = useQuery({
    queryKey: ['crm', 'agreements', 'task-projects'],
    queryFn: () => fetchAgreements({ page: 1, page_size: 1 }),
    enabled: canQuery,
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'task-filter'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: canQuery,
  });
  const personSuggestQuery = useQuery({
    ...contactQueries.list({ search: personDraft.trim() || form.contactLabel.trim(), page: 1, page_size: 8 }),
    enabled: canQuery && (personDraft.trim().length >= 2 || (mode !== 'detail' && form.contactLabel.trim().length >= 2 && !form.contactId)),
  });
  const purchasesQuery = useQuery({
    queryKey: ['crm', 'agreements', 'task-purchases', form.contactId],
    queryFn: () => fetchAgreements({ contact_id: form.contactId, page: 1, page_size: 20 }),
    enabled: canQuery && Boolean(form.contactId) && mode !== 'detail' && mode !== null,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['crm'] });
  };

  const completeMutation = useMutation({
    mutationFn: completeTask,
    onSuccess: invalidate,
  });
  const saveMutation = useMutation({
    mutationFn: async () => {
      const mapped = statusToApi(form.status);
      if (mode === 'edit' && selectedId) {
        await updateActivity(selectedId, {
          title: form.title.trim(),
          description: form.description.trim() || undefined,
          assigned_user_id: form.ownerId || undefined,
          due_date: toDuePayload(form.dueDate),
          priority: form.priority,
          task_status: mapped.task_status,
          status: mapped.status,
          entity_type: form.contactId ? 'contact' : undefined,
          entity_id: form.contactId || undefined,
          related_entity_type: form.agreementId ? 'transaction' : undefined,
          related_entity_id: form.agreementId || undefined,
          metadata_json: {
            task_links: {
              contact_id: form.contactId || null,
              project_group: form.projectGroup || null,
              agreement_id: form.agreementId || null,
            },
          },
        });
        return;
      }
      await createTask({
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        contact_id: form.contactId || undefined,
        project_group: form.projectGroup || undefined,
        agreement_id: form.agreementId || undefined,
        assigned_user_id: form.ownerId || undefined,
        due_date: toDuePayload(form.dueDate),
        priority: form.priority,
        task_status: mapped.task_status,
      });
    },
    onSuccess: () => {
      setMode(null);
      setSelectedId(null);
      setSelectedSnapshot(null);
      setForm(EMPTY_FORM);
      invalidate();
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

  const openEdit = (item: CrmActivitySummary) => {
    setSelectedSnapshot(item);
    setSelectedId(item.id);
    setForm({
      title: item.title,
      description: item.summary || '',
      contactId: item.entity_type === 'contact' ? item.entity_id : '',
      contactLabel: personLabel(item, ''),
      projectGroup: item.project_group || '',
      agreementId: item.agreement_id || '',
      ownerId: item.assigned_user_id || item.owner_id || '',
      dueDate: dateInputValue(item.due_date),
      priority: priorityKey(item.priority),
      status: workspaceStatus(item),
    });
    setMode('edit');
  };

  if (authLoading) {
    return (
      <div className="crm-tasks crm-tasks--ops" data-testid="crm-tasks-workspace">
        <div className="crm-tasks__skeleton" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="crm-tasks__skeleton-row" />
          ))}
        </div>
      </div>
    );
  }

  if (!canView) {
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
    <div className="crm-tasks crm-tasks--ops" data-testid="crm-tasks-workspace">
      <header className="crm-tasks__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-tasks__header-actions">
          <span className="crm-tasks__count">{t('pagination.total', { count: total })}</span>
          {canManageTasks ? (
            <Button type="button" size="sm" onClick={openCreate}>
              {t('create')}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="crm-tasks__counters" aria-label={t('kpis.aria')}>
        {(
          [
            ['open', counters?.open ?? 0, () => patchFilters({ status: 'active', dueBucket: '' })],
            ['dueToday', counters?.today ?? 0, () => patchFilters({ status: '', dueBucket: 'today' })],
            ['overdue', counters?.overdue ?? 0, () => patchFilters({ status: '', dueBucket: 'overdue' })],
            ['completed', counters?.completed ?? 0, () => patchFilters({ status: 'completed', dueBucket: '' })],
          ] as const
        ).map(([key, value, onClick]) => (
          <button
            key={key}
            type="button"
            className={`crm-tasks__counter${key === 'overdue' ? ' is-warn' : ''}${
              (key === 'open' && (filters.status === 'open' || filters.status === 'active') && !filters.dueBucket) ||
              (key === 'completed' && filters.status === 'completed') ||
              (key === 'dueToday' && filters.dueBucket === 'today') ||
              (key === 'overdue' && filters.dueBucket === 'overdue')
                ? ' is-active'
                : ''
            }`}
            onClick={onClick}
          >
            <strong>{value}</strong>
            <span>{t(`kpis.${key}`)}</span>
          </button>
        ))}
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
        <Select label={t('filters.status')} value={filters.status} onChange={(event) => patchFilters({ status: event.target.value })}>
          <option value="">{t('filters.any')}</option>
          {WORKSPACE_STATUSES.map((status) => (
            <option key={status} value={status}>
              {t(`workspaceStatus.${status}`)}
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
        <Select
          label={t('filters.priority')}
          value={filters.priority}
          onChange={(event) => patchFilters({ priority: event.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {t(`priority.${priority}`)}
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
          <div className="crm-tasks__empty" data-testid="crm-tasks-empty">
            <strong>{t('emptyTitle')}</strong>
            <p>{t('emptyDescription')}</p>
          </div>
        ) : (
          <table className="crm-tasks__table crm-tasks__table--ops">
            <thead>
              <tr>
                <th>{t('table.task')}</th>
                <th>{t('table.person')}</th>
                <th>{t('table.project')}</th>
                <th>{t('table.owner')}</th>
                <th>{t('table.dueDate')}</th>
                <th>{t('table.priority')}</th>
                <th>{t('table.status')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const status = workspaceStatus(item);
                const tone = dueTone(item);
                return (
                  <tr
                    key={item.id}
                    className={`crm-tasks__row${selectedId === item.id ? ' is-selected' : ''}${tone === 'overdue' ? ' is-overdue' : ''}`}
                    onClick={() => openDetail(item)}
                    data-testid={`crm-task-row-${item.id}`}
                  >
                    <td>
                      <strong>{item.title}</strong>
                    </td>
                    <td>{personLabel(item, t('unresolvedIdentity'))}</td>
                    <td>{projectUnit(item)}</td>
                    <td>{item.assigned_user_name || item.owner_name || '—'}</td>
                    <td>
                      <span className={`crm-tasks__due is-${tone}`}>{formatDate(item.due_date, locale)}</span>
                    </td>
                    <td>
                      <StatusChip tone={item.priority === 'critical' || item.priority === 'high' ? 'danger' : 'info'}>
                        {t(`priority.${priorityKey(item.priority)}`)}
                      </StatusChip>
                    </td>
                    <td>
                      <StatusChip
                        tone={status === 'cancelled' ? 'danger' : status === 'completed' ? 'success' : status === 'in_progress' ? 'warning' : 'info'}
                      >
                        {t(`workspaceStatus.${status}`)}
                      </StatusChip>
                    </td>
                  </tr>
                );
              })}
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
          <TaskDrawer
            item={selectedDetail}
            mode={mode}
            form={form}
            canManage={canManageTasks}
            users={users}
            projects={projects}
            purchases={purchases}
            personSuggestions={mode === 'detail' ? [] : personSuggestions}
            saving={saveMutation.isPending}
            completing={completeMutation.isPending}
            onClose={() => setMode(null)}
            onEdit={() => selected && openEdit(selected)}
            onComplete={() => selected && completeMutation.mutate(selected.id)}
            onSave={() => void saveMutation.mutate()}
            onFormChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            onPersonQuery={(value) => setForm((prev) => ({ ...prev, contactLabel: value, contactId: '' }))}
            onPickPerson={(id, name) => setForm((prev) => ({ ...prev, contactId: id, contactLabel: name }))}
          />
        </>
      ) : null}
    </div>
  );
}
