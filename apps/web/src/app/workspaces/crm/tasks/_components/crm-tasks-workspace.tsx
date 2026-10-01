'use client';

import type { Route } from 'next';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, TextArea } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { completeTask, createTask, fetchActivity, fetchTasks, updateActivity } from '@/workspaces/crm/api/activities';
import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type {
  ActivityListParams,
  CrmActivityPriority,
  CrmActivitySummary,
  CrmTaskStatus,
} from '@/workspaces/crm/types/activities';

import '../../contacts/_components/ds/contacts-ds.css';
import '../tasks-ops.css';

type WorkspaceStatus = 'open' | 'in_progress' | 'completed' | 'cancelled';
type PriorityKey = 'low' | 'medium' | 'high' | 'critical';
type SortKey = 'task' | 'person' | 'project' | 'owner' | 'start' | 'due' | 'priority' | 'status';

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
  return '';
}

function projectDisplay(item: CrmActivitySummary): { title: string; subtitle: string | null } {
  const title = [item.project_label, item.unit_number].filter(Boolean).join(' · ');
  return { title, subtitle: null };
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
    day: 'numeric',
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

function displayOwner(name: string | null | undefined): string {
  return String(name || '')
    .replace(/\s*\((?:Demo|demo)\)\s*$/g, '')
    .trim();
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '•';
  const first = parts[0][0] || '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] || '' : '';
  return `${first}${last}`.toLocaleUpperCase('tr-TR');
}

function previewText(value: string | null | undefined): string {
  const text = String(value || '')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text || text.startsWith('{') || text.startsWith('[')) return '';
  return text;
}

function visiblePages(page: number, pages: number): Array<number | 'ellipsis'> {
  if (pages <= 7) return Array.from({ length: pages }, (_, index) => index + 1);
  const wanted = new Set([1, pages, page - 1, page, page + 1]);
  const nums = [...wanted].filter((value) => value >= 1 && value <= pages).sort((a, b) => a - b);
  const next: Array<number | 'ellipsis'> = [];
  for (const value of nums) {
    const last = next[next.length - 1];
    if (typeof last === 'number' && value - last > 1) next.push('ellipsis');
    next.push(value);
  }
  return next;
}

function sortValue(item: CrmActivitySummary, key: SortKey, unresolved: string): string {
  if (key === 'task') return item.title || '';
  if (key === 'person') return personLabel(item, unresolved);
  if (key === 'project') return projectDisplay(item).title;
  if (key === 'owner') return displayOwner(item.assigned_user_name || item.owner_name);
  if (key === 'start') return item.start_date || '';
  if (key === 'due') return item.due_date || '';
  if (key === 'priority') return priorityKey(item.priority);
  return workspaceStatus(item);
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
  onOpenPerson,
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
  onOpenPerson: (id: string) => void;
}) {
  const t = useTranslations('crm.tasks');
  const locale = useLocale();
  const router = useRouter();
  const unresolved = t('unresolvedIdentity');
  const person = item ? personLabel(item, unresolved) : form.contactLabel || '';
  const project = item ? projectDisplay(item) : { title: '', subtitle: null };
  const purchaseHref =
    item?.agreement_id && item.entity_type === 'contact' && item.entity_id
      ? salesDetailUrl(item.entity_id, item.agreement_id)
      : form.agreementId && form.contactId
        ? salesDetailUrl(form.contactId, form.agreementId)
        : undefined;
  const contactId =
    item?.entity_type === 'contact' && item.entity_id
      ? item.entity_id
      : form.contactId || null;
  const owner = displayOwner(item?.assigned_user_name || item?.owner_name);
  const description = previewText(item?.summary) || t('drawer.noDescription');
  const status = item ? workspaceStatus(item) : form.status;

  return (
    <aside className="crm-ops-drawer" role="dialog" aria-label={t('drawer.title')} data-testid="crm-tasks-drawer">
      <div className="crm-ops-drawer__head">
        <h3>{mode === 'create' ? t('create') : mode === 'edit' ? t('actions.edit') : t('drawer.title')}</h3>
        <button type="button" className="crm-ops-link" onClick={onClose}>
          {t('actions.close')}
        </button>
      </div>
      <div className="crm-ops-drawer__body">
        {mode === 'detail' && item ? (
          <>
            <h4>{item.title}</h4>
            <dl className="crm-ops-kv">
              <dt>{t('drawer.status')}</dt>
              <dd>{t(`workspaceStatus.${status}`)}</dd>
              <dt>{t('drawer.priority')}</dt>
              <dd>{t(`priority.${priorityKey(item.priority)}`)}</dd>
              <dt>{t('table.start')}</dt>
              <dd>{formatDate(item.start_date, locale)}</dd>
              <dt>{t('table.end')}</dt>
              <dd>{formatDate(item.due_date, locale)}</dd>
              <dt>{t('drawer.owner')}</dt>
              <dd>{owner || '—'}</dd>
              <dt>{t('drawer.person')}</dt>
              <dd>{person || '—'}</dd>
              <dt>{t('drawer.project')}</dt>
              <dd>{project.title || '—'}</dd>
              <dt>{t('drawer.created')}</dt>
              <dd>{formatDate(item.created_at, locale)}</dd>
              {item.updated_at ? (
                <>
                  <dt>{t('drawer.updated')}</dt>
                  <dd>{formatDate(item.updated_at, locale)}</dd>
                </>
              ) : null}
            </dl>
            <p className="crm-ops-note">{description}</p>
            <div className="crm-ops-drawer__actions">
              {contactId ? (
                <Button type="button" variant="primary" size="sm" onClick={() => onOpenPerson(contactId)}>
                  {t('actions.openContact')}
                </Button>
              ) : null}
              {purchaseHref ? (
                <Button type="button" variant="secondary" size="sm" onClick={() => router.push(purchaseHref as Route)}>
                  {t('actions.openPurchase')}
                </Button>
              ) : null}
              {canManage && status !== 'completed' ? (
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
            className="crm-ops-form"
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
            <div className="crm-ops-person">
              <Input
                label={t('form.person')}
                value={form.contactLabel}
                onChange={(event) => onPersonQuery(event.target.value)}
                placeholder={t('filters.personPlaceholder')}
              />
              {personSuggestions.length > 0 ? (
                <ul className="crm-ops-suggest">
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
                  {displayOwner(user.full_name) || user.full_name}
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
              {WORKSPACE_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {t(`workspaceStatus.${value}`)}
                </option>
              ))}
            </Select>
            <div className="crm-ops-drawer__actions">
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
  const { openContact } = useContactCard();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<OpsFilters>({
    ...EMPTY_FILTERS,
    status: searchParams.get('status') || 'active',
    dueBucket: searchParams.get('due') || '',
  });
  const [searchDraft, setSearchDraft] = useState('');
  const [personDraft, setPersonDraft] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortKey, setSortKey] = useState<SortKey>('due');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<CrmActivitySummary | null>(null);
  const [mode, setMode] = useState<'detail' | 'create' | 'edit' | null>(null);
  const [form, setForm] = useState<TaskForm>(EMPTY_FORM);
  const [menuId, setMenuId] = useState<string | null>(null);

  const canQuery = !authLoading && canView;

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setPage(1);
      setFilters((prev) => ({ ...prev, search: searchDraft }));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setPage(1);
      setFilters((prev) => ({
        ...prev,
        person: personDraft,
        personId: personDraft.trim() ? prev.personId : null,
      }));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [personDraft]);

  useEffect(() => {
    const close = () => setMenuId(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, []);

  const apiFilters = useMemo<ActivityListParams>(() => {
    const params: ActivityListParams = { page, page_size: pageSize };
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
  }, [filters, page, pageSize]);

  const listQuery = useQuery({
    queryKey: activityQueryKeys.tasks(apiFilters),
    queryFn: () => fetchTasks(apiFilters),
    enabled: canQuery,
  });

  const items = useMemo(() => {
    const rows = [...(listQuery.data?.items ?? [])];
    const unresolved = t('unresolvedIdentity');
    const direction = sortDir === 'asc' ? 1 : -1;
    rows.sort((left, right) => {
      const a = sortValue(left, sortKey, unresolved);
      const b = sortValue(right, sortKey, unresolved);
      return (a.localeCompare(b, locale === 'tr' ? 'tr' : 'en', { numeric: true, sensitivity: 'base' }) || left.id.localeCompare(right.id)) * direction;
    });
    return rows;
  }, [listQuery.data?.items, locale, sortDir, sortKey, t]);

  const counters = listQuery.data?.counters;
  const filteredTotal = listQuery.data?.total ?? 0;
  const pages = listQuery.data?.pages ?? 1;
  const from = filteredTotal ? (page - 1) * pageSize + 1 : 0;
  const to = Math.min(page * pageSize, filteredTotal);
  const headerTotal = counters?.total ?? filteredTotal;
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
        start_date: selected.start_date || detailQuery.data?.start_date,
        due_date: selected.due_date || detailQuery.data?.due_date,
        updated_at: selected.updated_at || detailQuery.data?.updated_at,
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

  const patchFilters = (patch: Partial<OpsFilters>) => {
    setPage(1);
    setFilters((prev) => ({ ...prev, ...patch }));
  };
  const clearFilters = () => {
    setFilters(EMPTY_FILTERS);
    setSearchDraft('');
    setPersonDraft('');
    setPage(1);
  };
  const hasFilters = Boolean(
    searchDraft || personDraft || filters.ownerId || filters.projectGroup || filters.priority || filters.dateFrom || filters.dateTo || filters.dueBucket || (filters.status && filters.status !== 'active'),
  );

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((value) => (value === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDir(key === 'due' || key === 'start' ? 'asc' : 'asc');
  };

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setSelectedId(null);
    setSelectedSnapshot(null);
    setMode('create');
  };

  const openDetail = (item: CrmActivitySummary) => {
    setMenuId(null);
    setSelectedSnapshot(item);
    setSelectedId(item.id);
    setMode('detail');
  };

  const openEdit = (item: CrmActivitySummary) => {
    setMenuId(null);
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

  const shell = (content: ReactNode) => (
    <div className="ctc-ds crm-ops" data-testid="crm-tasks-workspace">
      {content}
    </div>
  );

  if (authLoading) {
    return shell(
      <div className="crm-ops-skeleton" aria-hidden="true">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} />
        ))}
      </div>,
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
    label: [item.project_group_label, item.unit_number].filter(Boolean).join(' · '),
  }));
  const kpiActive = !filters.dueBucket && (filters.status === 'active' || filters.status === 'open');

  return shell(
    <>
      <header className="crm-ops__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-ops__header-tools">
          <span className="crm-ops__count">{t('pagination.total', { count: headerTotal })}</span>
          {canManageTasks ? (
            <Button type="button" size="sm" onClick={openCreate}>
              {t('create')}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="crm-ops-kpis" aria-label={t('kpis.aria')}>
        {(
          [
            { id: 'open', value: counters?.open ?? 0, label: t('kpis.open'), icon: 'check' as IhIconName, active: kpiActive, warn: false, ok: false, onClick: () => patchFilters({ status: 'active', dueBucket: '' }) },
            { id: 'dueToday', value: counters?.today ?? 0, label: t('kpis.dueToday'), icon: 'calendar' as IhIconName, active: filters.dueBucket === 'today', warn: false, ok: false, onClick: () => patchFilters({ status: '', dueBucket: 'today' }) },
            { id: 'overdue', value: counters?.overdue ?? 0, label: t('kpis.overdue'), icon: 'alert' as IhIconName, active: filters.dueBucket === 'overdue', warn: true, ok: false, onClick: () => patchFilters({ status: '', dueBucket: 'overdue' }) },
            { id: 'completed', value: counters?.completed ?? 0, label: t('kpis.completed'), icon: 'check' as IhIconName, active: filters.status === 'completed' && !filters.dueBucket, warn: false, ok: true, onClick: () => patchFilters({ status: 'completed', dueBucket: '' }) },
          ] as const
        ).map((item) => (
          <button
            key={item.id}
            type="button"
            className={`${item.active ? 'is-active' : ''}${item.warn ? ' is-warn' : ''}${item.ok ? ' is-ok' : ''}`}
            onClick={item.onClick}
          >
            <span className="crm-ops-kpis__icon" aria-hidden>
              <IhIcon name={item.icon} size={16} />
            </span>
            <strong>{item.value.toLocaleString(locale)}</strong>
            <span>{item.label}</span>
          </button>
        ))}
      </section>

      <section className="crm-ops-filtercard" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={t('filters.searchPlaceholder')}
        />
        <Select label={t('filters.status')} value={filters.status} onChange={(event) => patchFilters({ status: event.target.value, dueBucket: '' })}>
          <option value="">{t('filters.any')}</option>
          <option value="active">{t('workspaceStatus.active')}</option>
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
              {displayOwner(user.full_name) || user.full_name}
            </option>
          ))}
        </Select>
        <div className="crm-ops-person">
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
            <ul className="crm-ops-suggest">
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
        <div className="crm-ops-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters} disabled={!hasFilters && filters.status === 'active'}>
            {t('filters.clear')}
          </Button>
        </div>
      </section>

      {listQuery.isLoading ? (
        <div className="crm-ops-skeleton" aria-hidden="true">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="crm-ops-empty" data-testid="crm-tasks-empty">
          <strong>{t('emptyTitle')}</strong>
          <p>{t('emptyDescription')}</p>
        </div>
      ) : (
        <section className="crm-ops-tablecard" aria-label={t('table.aria')}>
          <div className="crm-ops-table-wrap">
            <table className="crm-ops-table">
              <thead>
                <tr>
                  {(
                    [
                      ['task', 'is-task'],
                      ['person', 'is-person'],
                      ['project', 'is-project'],
                      ['owner', 'is-owner'],
                      ['start', 'is-date'],
                      ['due', 'is-date'],
                      ['priority', ''],
                      ['status', ''],
                    ] as const
                  ).map(([key, className]) => (
                    <th key={key} className={className || undefined}>
                      <button type="button" className="crm-ops-link" onClick={() => toggleSort(key)}>
                        {t(`table.${key === 'due' ? 'end' : key === 'start' ? 'start' : key}`)}
                        {sortKey === key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                      </button>
                    </th>
                  ))}
                  <th className="is-actions">{t('table.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const status = workspaceStatus(item);
                  const tone = dueTone(item);
                  const person = personLabel(item, t('unresolvedIdentity'));
                  const project = projectDisplay(item);
                  const owner = displayOwner(item.assigned_user_name || item.owner_name);
                  const contactId = item.entity_type === 'contact' ? item.entity_id : null;
                  const purchaseHref = item.agreement_id && contactId ? salesDetailUrl(contactId, item.agreement_id) : undefined;
                  const preview = previewText(item.summary);
                  const priority = priorityKey(item.priority);
                  const hasMore = canManageTasks || Boolean(contactId) || Boolean(purchaseHref);
                  return (
                    <tr
                      key={item.id}
                      className={`crm-ops-row${selectedId === item.id ? ' is-selected' : ''}`}
                      onClick={() => openDetail(item)}
                      data-testid={`crm-task-row-${item.id}`}
                    >
                      <td className="is-task">
                        <div className="crm-ops-task" title={[item.title, preview].filter(Boolean).join('\n')}>
                          <strong>{item.title}</strong>
                          {preview && preview !== item.title ? <small>{preview}</small> : null}
                        </div>
                      </td>
                      <td className="is-person">
                        {person && contactId ? (
                          <div className="crm-ops-personline">
                            <span className="crm-ops-avatar" aria-hidden>
                              {initials(person)}
                            </span>
                            <button
                              type="button"
                              className="crm-ops-link"
                              title={person}
                              onClick={(event) => {
                                event.stopPropagation();
                                openContact(contactId);
                              }}
                            >
                              {person}
                            </button>
                          </div>
                        ) : (
                          person || '—'
                        )}
                      </td>
                      <td className="is-project">
                        {project.title ? (
                          <div className="crm-ops-project" title={project.title}>
                            {purchaseHref ? (
                              <a
                                href={purchaseHref}
                                className="crm-ops-link"
                                onClick={(event) => event.stopPropagation()}
                              >
                                <strong>{project.title}</strong>
                              </a>
                            ) : (
                              <strong>{project.title}</strong>
                            )}
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="is-owner">
                        {owner ? (
                          <div className="crm-ops-owner" title={owner}>
                            <span className="crm-ops-avatar" aria-hidden>
                              {initials(owner)}
                            </span>
                            <span>{owner}</span>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="is-date">
                        <span className="crm-ops-date">{formatDate(item.start_date, locale)}</span>
                      </td>
                      <td className="is-date">
                        <span className={`crm-ops-date is-${tone}`}>{formatDate(item.due_date, locale)}</span>
                      </td>
                      <td>
                        <span className={`crm-ops-badge is-${priority === 'medium' ? 'normal' : priority}`}>
                          {priority === 'critical' ? '! ' : ''}
                          {t(`priority.${priority}`)}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`crm-ops-badge ${
                            status === 'completed' ? 'is-done' : status === 'in_progress' ? 'is-progress' : status === 'cancelled' ? 'is-cancelled' : 'is-open'
                          }`}
                        >
                          {t(`workspaceStatus.${status}`)}
                        </span>
                      </td>
                      <td className="is-actions">
                        <div className="crm-ops-actions">
                          <button
                            type="button"
                            className="crm-ops-action"
                            onClick={(event) => {
                              event.stopPropagation();
                              openDetail(item);
                            }}
                          >
                            {t('actions.open')}
                          </button>
                          {hasMore ? (
                          <div className="crm-ops-more">
                            <button
                              type="button"
                              className="crm-ops-action is-more"
                              aria-label={t('actions.more')}
                              onClick={(event) => {
                                event.stopPropagation();
                                setMenuId((current) => (current === item.id ? null : item.id));
                              }}
                            >
                              …
                            </button>
                            {menuId === item.id ? (
                              <div className="crm-ops-more__panel">
                                {canManageTasks ? (
                                  <button
                                    type="button"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      openEdit(item);
                                    }}
                                  >
                                    {t('actions.edit')}
                                  </button>
                                ) : null}
                                {canManageTasks && status !== 'completed' ? (
                                  <button
                                    type="button"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setMenuId(null);
                                      completeMutation.mutate(item.id);
                                    }}
                                  >
                                    {t('actions.complete')}
                                  </button>
                                ) : null}
                                {contactId ? (
                                  <button
                                    type="button"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setMenuId(null);
                                      openContact(contactId);
                                    }}
                                  >
                                    {t('actions.openContact')}
                                  </button>
                                ) : null}
                                {purchaseHref ? (
                                  <a href={purchaseHref} onClick={(event) => event.stopPropagation()}>
                                    {t('actions.openPurchase')}
                                  </a>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <footer className="crm-ops-pager">
            <p>{t('pager', { total: filteredTotal, from, to })}</p>
            <div>
              <button type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
                ‹
              </button>
              {visiblePages(page, pages).map((item, index) =>
                item === 'ellipsis' ? (
                  <span key={`e${index}`}>…</span>
                ) : (
                  <button
                    key={item}
                    type="button"
                    className={item === page ? 'is-active' : undefined}
                    onClick={() => setPage(item)}
                  >
                    {item}
                  </button>
                ),
              )}
              <button type="button" disabled={page >= pages} onClick={() => setPage((value) => Math.min(pages, value + 1))}>
                ›
              </button>
            </div>
            <label>
              {t('pageSize')}
              <select
                value={pageSize}
                onChange={(event) => {
                  setPageSize(Number(event.target.value));
                  setPage(1);
                }}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </label>
          </footer>
        </section>
      )}

      {mode ? (
        <>
          <button type="button" className="crm-ops-drawer-backdrop" aria-label={t('actions.close')} onClick={() => setMode(null)} />
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
            onOpenPerson={(id) => openContact(id)}
          />
        </>
      ) : null}
    </>,
  );
}
