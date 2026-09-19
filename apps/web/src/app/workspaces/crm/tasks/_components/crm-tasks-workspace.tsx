'use client';

import { FormEvent, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, Input, KpiCard, LoadingState, SegmentedControl, Select, StatusChip, TextArea } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchUsers, type UserRecord } from '@/lib/api/auth';
import { completeTask, createTask, fetchTasks, reopenTask, updateActivity } from '@/workspaces/crm/api/activities';
import { fetchContacts } from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { activityQueries } from '@/workspaces/crm/hooks/use-activities';
import { buildTasksPreview } from '@/workspaces/crm/lib/map-live-workspace';

import {
  TASK_KANBAN_COLUMNS,
  TASK_PRIORITY_ORDER,
  TASK_STATUS_ORDER,
  type TaskAiActionKey,
  type TaskKanbanColumnKey,
  type TaskKpiKey,
  type TaskPriorityKey,
  type TaskRow,
  type TaskStatusKey,
  type TaskViewMode,
  type TaskWorkspacePreview,
} from '../tasks-model';

const AI_ACTIONS: ReadonlyArray<{ key: TaskAiActionKey; icon: IhIconName }> = [
  { key: 'sortByPriority', icon: 'sparkles' },
  { key: 'dueToday', icon: 'clock' },
  { key: 'showOverdue', icon: 'alert' },
  { key: 'createPlan', icon: 'calendar' },
];

const KPI_ICONS: Record<TaskKpiKey, IhIconName> = {
  open: 'check',
  dueToday: 'clock',
  overdue: 'alert',
  completed: 'check',
};

const STATUS_TONE: Record<TaskStatusKey, 'success' | 'warning' | 'info' | 'default' | 'danger'> = {
  open: 'info',
  inProgress: 'warning',
  completed: 'success',
  waiting: 'default',
  cancelled: 'danger',
};

const PRIORITY_TONE: Record<TaskPriorityKey, 'success' | 'warning' | 'info' | 'default' | 'danger'> = {
  low: 'info',
  medium: 'warning',
  high: 'danger',
  critical: 'danger',
};

type FilterKey =
  | 'assignee'
  | 'customer'
  | 'project'
  | 'priority'
  | 'status'
  | 'dueDate'
  | 'tag'
  | 'search';

/** Presentation-only urgency hint derived from existing due labels/tones. */
function dueUrgencyKey(row: TaskRow): 'dueEndToday' | 'hoursLeft3' | 'tomorrow' | null {
  if (row.dueTone === 'today') {
    if (row.dueLabelKey === 'today1500') return 'hoursLeft3';
    return 'dueEndToday';
  }
  if (row.dueLabelKey === 'tomorrow1100') return 'tomorrow';
  return null;
}

function TaskIdentity({
  row,
  checked,
  onCheckedChange,
}: {
  row: TaskRow;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  const t = useTranslations('crm.tasks');
  const title = row.title ?? t(`titles.${row.titleKey}`);
  const description = row.description ?? t(`descriptions.${row.descriptionKey}`);

  return (
    <div className="crm-tasks__task-cell">
      <label className="crm-tasks__checkbox">
        <input
          type="checkbox"
          checked={checked}
          aria-label={t('actions.selectTask', { title })}
          onChange={(e) => onCheckedChange(e.target.checked)}
          onClick={(e) => e.stopPropagation()}
        />
      </label>
      <div className="crm-tasks__task-text">
        <strong title={title}>{title}</strong>
        <span className="crm-tasks__clamp-fade" title={description}>
          {description}
        </span>
      </div>
    </div>
  );
}

function AiNoteCell({ noteKey, noteText }: { noteKey: string; noteText?: string }) {
  const t = useTranslations('crm.tasks');
  const [expanded, setExpanded] = useState(false);
  const note = noteText ?? t(`aiNotes.${noteKey}`);
  const needsToggle = note.length > 36;

  return (
    <div className="crm-tasks__ai-summary">
      <p
        className={
          expanded
            ? 'crm-tasks__ai-note is-expanded'
            : 'crm-tasks__ai-note crm-tasks__clamp-fade'
        }
        title={note}
      >
        {note}
      </p>
      {needsToggle ? (
        <button
          type="button"
          className="crm-tasks__ai-more"
          aria-expanded={expanded}
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
        >
          {expanded ? t('actions.collapse') : t('actions.expand')}
          <IhIcon name="chevronDown" size={11} />
        </button>
      ) : null}
    </div>
  );
}

function DueCell({ row }: { row: TaskRow }) {
  const t = useTranslations('crm.tasks');
  const urgency = dueUrgencyKey(row);

  return (
    <div className="crm-tasks__due-wrap">
      <span className={`crm-tasks__due is-${row.dueTone}`}>
        {row.dueLabel ?? t(`dueLabels.${row.dueLabelKey}`)}
      </span>
      {urgency ? (
        <span className={`crm-tasks__due-urgency is-${urgency}`} title={t(`dueUrgency.${urgency}`)}>
          {t(`dueUrgency.${urgency}`)}
        </span>
      ) : null}
    </div>
  );
}

function RowActions({
  row,
  onEdit,
  onComplete,
  onReopen,
}: {
  row: TaskRow;
  onEdit?: (row: TaskRow) => void;
  onComplete?: (id: string) => void;
  onReopen?: (id: string) => void;
}) {
  const t = useTranslations('crm.tasks');
  const done = row.status === 'completed';

  return (
    <div className="crm-tasks__row-actions">
      <button
        type="button"
        className="crm-tasks__icon-action"
        aria-label={done ? 'Yeniden aç' : t('actions.detail')}
        title={done ? 'Yeniden aç' : t('actions.detail')}
        onClick={() => (done ? onReopen?.(row.id) : onComplete?.(row.id))}
      >
        <IhIcon name="check" size={14} />
      </button>
      <button
        type="button"
        className="crm-tasks__icon-action"
        aria-label={t('actions.edit')}
        title={t('actions.edit')}
        onClick={() => onEdit?.(row)}
      >
        <IhIcon name="settings" size={14} />
      </button>
    </div>
  );
}

function TaskCardView({
  row,
  checked,
  onCheckedChange,
  onEdit,
  onComplete,
  onReopen,
}: {
  row: TaskRow;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  onEdit?: (row: TaskRow) => void;
  onComplete?: (id: string) => void;
  onReopen?: (id: string) => void;
}) {
  const t = useTranslations('crm.tasks');

  return (
    <article
      className={`crm-tasks__card is-priority-${row.priority} is-status-${row.status}`}
      data-testid={`task-card-${row.id}`}
    >
      <header className="crm-tasks__card-header">
        <TaskIdentity row={row} checked={checked} onCheckedChange={onCheckedChange} />
        <StatusChip
          tone={PRIORITY_TONE[row.priority]}
          className={
            row.priority === 'critical'
              ? 'crm-tasks__badge crm-tasks__priority--critical'
              : 'crm-tasks__badge'
          }
        >
          {t(`priority.${row.priority}`)}
        </StatusChip>
      </header>

      <dl className="crm-tasks__card-meta">
        <div>
          <dt>{t('table.customer')}</dt>
          <dd title={row.customer}>{row.customer}</dd>
        </div>
        <div>
          <dt>{t('table.project')}</dt>
          <dd title={row.project}>{row.project}</dd>
        </div>
        <div>
          <dt>{t('table.dueDate')}</dt>
          <dd>
            <DueCell row={row} />
          </dd>
        </div>
        <div>
          <dt>{t('table.assignee')}</dt>
          <dd>
            <span className="crm-tasks__avatar" aria-hidden="true">
              {row.assigneeInitials}
            </span>
            <span title={row.assignee}>{row.assignee}</span>
          </dd>
        </div>
      </dl>

      <div className="crm-tasks__card-ai">
        <AiNoteCell noteKey={row.aiNoteKey} noteText={row.aiNote} />
      </div>

      <footer className="crm-tasks__card-footer">
        <StatusChip tone={STATUS_TONE[row.status]} className="crm-tasks__badge">
          {t(`status.${row.status}`)}
        </StatusChip>
        <RowActions row={row} onEdit={onEdit} onComplete={onComplete} onReopen={onReopen} />
      </footer>
    </article>
  );
}

function KanbanCard({
  row,
  checked,
  onCheckedChange,
}: {
  row: TaskRow;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  const t = useTranslations('crm.tasks');

  return (
    <article
      className={`crm-tasks__kanban-card is-priority-${row.priority}`}
      data-testid={`task-kanban-${row.id}`}
      draggable={false}
    >
      <div className="crm-tasks__kanban-card-top">
        <label className="crm-tasks__checkbox">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => onCheckedChange(e.target.checked)}
            aria-label={t('actions.selectTask', { title: row.title ?? t(`titles.${row.titleKey}`) })}
          />
        </label>
        <StatusChip
          tone={PRIORITY_TONE[row.priority]}
          className={
            row.priority === 'critical'
              ? 'crm-tasks__badge crm-tasks__priority--critical'
              : 'crm-tasks__badge'
          }
        >
          {t(`priority.${row.priority}`)}
        </StatusChip>
      </div>
      <h4 title={row.title ?? t(`titles.${row.titleKey}`)}>{row.title ?? t(`titles.${row.titleKey}`)}</h4>
      <p>
        {row.customer} · {row.project}
      </p>
      <div className="crm-tasks__kanban-card-meta">
        <DueCell row={row} />
        <span className="crm-tasks__avatar" aria-hidden="true" title={row.assignee}>
          {row.assigneeInitials}
        </span>
      </div>
    </article>
  );
}

export function CrmTasksWorkspace({
  preview: previewProp,
  onOpenAi,
}: {
  preview?: TaskWorkspacePreview;
  onOpenAi?: (prompt?: string) => void;
}) {
  const t = useTranslations('crm.tasks');
  const { openContact } = useContactCard();
  const queryClient = useQueryClient();
  const liveQuery = useQuery({
    ...activityQueries.tasks({ page: 1, page_size: 100 }),
    enabled: !previewProp,
  });
  const preview = previewProp ?? buildTasksPreview(liveQuery.data?.items ?? [], liveQuery.data?.total ?? 0);
  const usersQuery = useQuery({
    queryKey: ['crm', 'users', 'task-assignees'],
    queryFn: () => fetchUsers({ status: 'active' }),
  });
  const [view, setView] = useState<TaskViewMode>('list');
  const [aiAction, setAiAction] = useState<TaskAiActionKey | null>(null);
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    assignee: '',
    customer: '',
    project: '',
    priority: '',
    status: '',
    dueDate: '',
    tag: '',
    search: '',
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [checkedIds, setCheckedIds] = useState<Record<string, boolean>>({});
  const [editor, setEditor] = useState<null | { mode: 'create' | 'edit'; row?: TaskRow }>(null);
  const [form, setForm] = useState({
    title: '',
    description: '',
    contactId: '',
    contactLabel: '',
    assigneeId: '',
    dueDate: '',
    priority: 'medium',
  });
  const [contactHits, setContactHits] = useState<Array<{ id: string; display_name: string }>>([]);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['crm'] });
  };

  const completeMutation = useMutation({
    mutationFn: completeTask,
    onSuccess: invalidate,
  });
  const reopenMutation = useMutation({
    mutationFn: reopenTask,
    onSuccess: invalidate,
  });
  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editor?.mode === 'edit' && editor.row) {
        await updateActivity(editor.row.id, {
          title: form.title.trim(),
          description: form.description.trim() || undefined,
          assigned_user_id: form.assigneeId || undefined,
          due_date: form.dueDate ? new Date(form.dueDate).toISOString() : undefined,
          priority: form.priority as 'low' | 'medium' | 'high' | 'critical',
        });
        return;
      }
      if (!form.contactId || !form.title.trim()) return;
      await createTask({
        entity_type: 'contact',
        entity_id: form.contactId,
        activity_type: 'task',
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        assigned_user_id: form.assigneeId || undefined,
        due_date: form.dueDate ? new Date(form.dueDate).toISOString() : undefined,
        task_status: 'not_started',
        priority: form.priority as 'low' | 'medium' | 'high' | 'critical',
      });
    },
    onSuccess: () => {
      setEditor(null);
      invalidate();
    },
  });

  const openEditor = (row?: TaskRow) => {
    if (row) {
      setForm({
        title: row.title ?? '',
        description: row.description ?? '',
        contactId: row.customerId ?? '',
        contactLabel: row.customer,
        assigneeId: row.assigneeId ?? '',
        dueDate: '',
        priority: row.priority,
      });
      setEditor({ mode: 'edit', row });
      return;
    }
    setForm({
      title: '',
      description: '',
      contactId: '',
      contactLabel: '',
      assigneeId: '',
      dueDate: '',
      priority: 'medium',
    });
    setEditor({ mode: 'create' });
  };

  const searchContacts = async (query: string) => {
    setForm((prev) => ({ ...prev, contactLabel: query }));
    if (query.trim().length < 2) {
      setContactHits([]);
      return;
    }
    const result = await fetchContacts({ search: query.trim(), page_size: 8, status: 'active' });
    setContactHits(result.items.map((item) => ({ id: item.id, display_name: item.display_name })));
  };

  const setTaskChecked = (id: string, checked: boolean) => {
    setCheckedIds((prev) => ({ ...prev, [id]: checked }));
  };

  const filteredTasks = useMemo(() => {
    let items = [...preview.tasks];

    if (aiAction === 'sortByPriority') {
      /* Local presentation filter: surface critical tasks (AI bar label = Kritikleri Göster). */
      items = items.filter((task) => task.priority === 'critical');
    } else if (aiAction === 'dueToday') {
      items = items.filter((task) => task.dueTone === 'today');
    } else if (aiAction === 'showOverdue') {
      items = items.filter((task) => task.dueTone === 'overdue');
    }

    return items.filter((row) => {
      if (filters.assignee && row.assignee !== filters.assignee) return false;
      if (filters.customer && row.customer !== filters.customer) return false;
      if (filters.project && row.project !== filters.project) return false;
      if (filters.priority && row.priority !== filters.priority) return false;
      if (filters.status && row.status !== filters.status) return false;
      if (filters.tag && row.tag !== filters.tag) return false;
      if (filters.dueDate === 'today' && row.dueTone !== 'today') return false;
      if (filters.dueDate === 'overdue' && row.dueTone !== 'overdue') return false;
      if (filters.dueDate === 'soon' && row.dueTone !== 'soon') return false;
      if (filters.search) {
        const q = filters.search.trim().toLowerCase();
        const haystack =
          `${row.customer} ${row.project} ${row.assignee} ${row.tag} ${row.titleKey}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [aiAction, filters, preview.tasks]);

  const totalPages = Math.max(1, Math.ceil(preview.totalTasks / pageSize));
  const pageItems = filteredTasks.slice(0, Math.min(pageSize, filteredTasks.length));

  const kanbanGroups = useMemo(() => {
    const groups: Record<TaskKanbanColumnKey, TaskRow[]> = {
      todo: [],
      inProgress: [],
      review: [],
      completed: [],
    };
    for (const task of filteredTasks) {
      groups[task.kanbanColumn].push(task);
    }
    return groups;
  }, [filteredTasks]);

  const clearFilters = () => {
    setFilters({
      assignee: '',
      customer: '',
      project: '',
      priority: '',
      status: '',
      dueDate: '',
      tag: '',
      search: '',
    });
    setPage(1);
  };

  if (!previewProp && liveQuery.isLoading) {
    return <LoadingState />;
  }

  const users = Array.isArray(usersQuery.data)
    ? usersQuery.data
    : ((usersQuery.data as { items?: UserRecord[] } | undefined)?.items ?? []);

  return (
    <div className="crm-tasks" data-testid="crm-tasks-workspace">
      <header className="crm-tasks__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-tasks__kpi-row" aria-label={t('kpis.aria')}>
        {preview.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className="crm-tasks__kpi"
            label={t(`kpis.${kpi.key}`)}
            value={kpi.value}
            hint={t(`kpis.hints.${kpi.hintKey}`)}
            delta={
              kpi.delta
                ? `${kpi.delta} ${kpi.key === 'overdue' ? t('kpis.thisWeek') : t('kpis.thisMonth')}`
                : undefined
            }
            {...(kpi.delta ? { deltaTone: kpi.deltaTone } : {})}
            tone={kpi.key === 'overdue' ? 'warning' : 'default'}
            icon={<IhIcon name={KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <nav className="screenshot-dashboard__intro-ai crm-tasks__ai" aria-label={t('ai.aria')}>
        {AI_ACTIONS.map((action) => (
          <button
            key={action.key}
            type="button"
            className={aiAction === action.key ? 'is-featured' : undefined}
            onClick={() => {
              if (action.key === 'createPlan') {
                onOpenAi?.(t('ai.openPrompt'));
                setAiAction(action.key);
                return;
              }
              setAiAction((prev) => (prev === action.key ? null : action.key));
            }}
          >
            <span className="crm-tasks__ai-icon" aria-hidden="true">
              <IhIcon name={action.icon} size={16} />
            </span>
            <span>{t(`ai.actions.${action.key}`)}</span>
          </button>
        ))}
        <button
          type="button"
          className="screenshot-dashboard__intro-ai-primary"
          onClick={() => onOpenAi?.(t('ai.openPrompt'))}
        >
          <IhIcon name="sparkles" size={15} />
          {t('ai.title')}
        </button>
      </nav>

      <section className="crm-tasks__filters" aria-label={t('filters.aria')}>
        <Select
          label={t('filters.assignee')}
          value={filters.assignee}
          onChange={(e) => setFilters((prev) => ({ ...prev, assignee: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.assignees.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.customer')}
          value={filters.customer}
          onChange={(e) => setFilters((prev) => ({ ...prev, customer: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.customers.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.project')}
          value={filters.project}
          onChange={(e) => setFilters((prev) => ({ ...prev, project: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.projects.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.priority')}
          value={filters.priority}
          onChange={(e) => setFilters((prev) => ({ ...prev, priority: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {TASK_PRIORITY_ORDER.map((priority) => (
            <option key={priority} value={priority}>
              {t(`priority.${priority}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {TASK_STATUS_ORDER.map((status) => (
            <option key={status} value={status}>
              {t(`status.${status}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.dueDate')}
          value={filters.dueDate}
          onChange={(e) => setFilters((prev) => ({ ...prev, dueDate: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="today">{t('filters.dateRanges.today')}</option>
          <option value="soon">{t('filters.dateRanges.soon')}</option>
          <option value="overdue">{t('filters.dateRanges.overdue')}</option>
        </Select>
        <Select
          label={t('filters.tag')}
          value={filters.tag}
          onChange={(e) => setFilters((prev) => ({ ...prev, tag: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.tags.map((tag) => (
            <option key={tag} value={tag}>
              {tag}
            </option>
          ))}
        </Select>
        <Input
          label={t('filters.search')}
          value={filters.search}
          onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
          placeholder={t('filters.searchPlaceholder')}
        />
        <Button variant="secondary" size="sm" onClick={clearFilters}>
          <IhIcon name="refresh" size={13} />
          {t('filters.clear')}
        </Button>
      </section>

      <div className="crm-tasks__layout">
        <div className="crm-tasks__main">
          <div className="crm-tasks__main-toolbar">
            <h2>{t('listTitle')}</h2>
            <div className="crm-tasks__toolbar-actions">
              <Button size="sm" onClick={() => openEditor()}>
                Görev oluştur
              </Button>
              <SegmentedControl
              ariaLabel={t('viewAria')}
              value={view}
              onChange={setView}
              options={[
                { value: 'list', label: t('view.list') },
                { value: 'card', label: t('view.card') },
                { value: 'kanban', label: t('view.kanban') },
              ]}
            />
            </div>
          </div>

          {view === 'list' ? (
            <div className="crm-tasks__table-wrap" role="region" aria-label={t('table.aria')}>
              <table className="crm-tasks__table">
                <thead>
                  <tr>
                    <th scope="col">{t('table.task')}</th>
                    <th scope="col">{t('table.customer')}</th>
                    <th scope="col">{t('table.project')}</th>
                    <th scope="col">{t('table.dueDate')}</th>
                    <th scope="col">{t('table.priority')}</th>
                    <th scope="col">{t('table.assignee')}</th>
                    <th scope="col">{t('table.aiNote')}</th>
                    <th scope="col">{t('table.status')}</th>
                    <th scope="col">{t('table.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((row) => (
                    <tr
                      key={row.id}
                      className={`crm-tasks__row is-priority-${row.priority} is-status-${row.status}`}
                      data-testid={`task-row-${row.id}`}
                      tabIndex={0}
                    >
                      <td>
                        <TaskIdentity
                          row={row}
                          checked={Boolean(checkedIds[row.id])}
                          onCheckedChange={(checked) => setTaskChecked(row.id, checked)}
                        />
                      </td>
                      <td>
                        <button
                          type="button"
                          className="crm-tasks__contact-btn"
                          onClick={() => row.customerId && openContact(row.customerId)}
                          disabled={!row.customerId}
                        >
                          <strong title={row.customer}>{row.customer}</strong>
                        </button>
                      </td>
                      <td>
                        <span className="crm-tasks__project">{row.project}</span>
                      </td>
                      <td>
                        <DueCell row={row} />
                      </td>
                      <td>
                        <StatusChip
                          tone={PRIORITY_TONE[row.priority]}
                          className={
                            row.priority === 'critical'
                              ? 'crm-tasks__badge crm-tasks__priority--critical'
                              : row.priority === 'high'
                                ? 'crm-tasks__badge crm-tasks__priority--high'
                                : 'crm-tasks__badge'
                          }
                        >
                          {t(`priority.${row.priority}`)}
                        </StatusChip>
                      </td>
                      <td>
                        <div className="crm-tasks__rep">
                          <span className="crm-tasks__avatar" aria-hidden="true">
                            {row.assigneeInitials}
                          </span>
                          <span title={row.assignee}>{row.assignee}</span>
                        </div>
                      </td>
                      <td>
                        <AiNoteCell noteKey={row.aiNoteKey} noteText={row.aiNote} />
                      </td>
                      <td>
                        <StatusChip tone={STATUS_TONE[row.status]} className="crm-tasks__badge">
                          {t(`status.${row.status}`)}
                        </StatusChip>
                      </td>
                      <td>
                        <RowActions
                          row={row}
                          onEdit={openEditor}
                          onComplete={(id) => completeMutation.mutate(id)}
                          onReopen={(id) => reopenMutation.mutate(id)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {view === 'card' ? (
            <div className="crm-tasks__grid" role="list" aria-label={t('view.card')}>
              {pageItems.map((row) => (
                <div key={row.id} role="listitem">
                  <TaskCardView
                    row={row}
                    checked={Boolean(checkedIds[row.id])}
                    onCheckedChange={(checked) => setTaskChecked(row.id, checked)}
                    onEdit={openEditor}
                    onComplete={(id) => completeMutation.mutate(id)}
                    onReopen={(id) => reopenMutation.mutate(id)}
                  />
                </div>
              ))}
            </div>
          ) : null}

          {view === 'kanban' ? (
            <div className="crm-tasks__kanban" role="region" aria-label={t('view.kanban')}>
              {TASK_KANBAN_COLUMNS.map((column) => (
                <section key={column} className="crm-tasks__kanban-column">
                  <header>
                    <h3>{t(`kanban.${column}`)}</h3>
                    <span>{kanbanGroups[column].length}</span>
                  </header>
                  <div className="crm-tasks__kanban-list">
                    {kanbanGroups[column].map((row) => (
                      <KanbanCard
                        key={row.id}
                        row={row}
                        checked={Boolean(checkedIds[row.id])}
                        onCheckedChange={(checked) => setTaskChecked(row.id, checked)}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : null}

          <footer className="crm-tasks__pagination" aria-label={t('pagination.aria')}>
            <p>{t('pagination.total', { count: preview.totalTasks })}</p>
            <div className="crm-tasks__page-numbers" role="navigation">
              {Array.from({ length: Math.min(totalPages, 3) }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  className={page === n ? 'is-active' : undefined}
                  onClick={() => setPage(n)}
                  aria-current={page === n ? 'page' : undefined}
                >
                  {n}
                </button>
              ))}
              {totalPages > 4 ? <span className="crm-tasks__page-ellipsis">…</span> : null}
              {totalPages > 3 ? (
                <button
                  type="button"
                  className={page === totalPages ? 'is-active' : undefined}
                  onClick={() => setPage(totalPages)}
                  aria-current={page === totalPages ? 'page' : undefined}
                >
                  {totalPages}
                </button>
              ) : null}
            </div>
            <label className="ih-field crm-tasks__page-size">
              <span className="ih-field__label">{t('pagination.perPage')}</span>
              <select
                className="ih-select"
                value={String(pageSize)}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                aria-label={t('pagination.perPage')}
              >
                <option value="10">10 / {t('pagination.pageUnit')}</option>
                <option value="20">20 / {t('pagination.pageUnit')}</option>
                <option value="40">40 / {t('pagination.pageUnit')}</option>
              </select>
            </label>
          </footer>
        </div>

        <aside className="crm-tasks__rail" aria-label={t('rail.aria')}>
          <section className="crm-tasks__rail-card crm-tasks__rail-card--ai">
            <h3>{t('rail.daySummary')}</h3>
            <dl className="crm-tasks__day-counts">
              <div>
                <dt>{t('rail.open')}</dt>
                <dd>{preview.daySummary.open}</dd>
              </div>
              <div>
                <dt>{t('rail.dueToday')}</dt>
                <dd className="is-warning">{preview.daySummary.dueToday}</dd>
              </div>
              <div>
                <dt>{t('rail.overdue')}</dt>
                <dd className="is-danger">{preview.daySummary.overdue}</dd>
              </div>
            </dl>
            <p className="crm-tasks__assessment">
              {t(`rail.assessments.${preview.daySummary.assessmentKey}`)}
            </p>
            <Button variant="secondary" size="sm">
              {t('rail.viewTaskSummary')}
            </Button>
          </section>

          <section className="crm-tasks__rail-card">
            <h3>{t('rail.todayPriorities')}</h3>
            <ol className="crm-tasks__priority-list">
              {preview.todayPriorities.map((item, index) => (
                <li key={item.id}>
                  <span className="crm-tasks__priority-index" aria-hidden="true">
                    {index + 1}
                  </span>
                  <div>
                    <strong title={item.title ?? t(`titles.${item.titleKey}`)}>
                      {item.title ?? t(`titles.${item.titleKey}`)}
                    </strong>
                    <span>{item.dueLabel ?? t(`dueLabels.${item.dueLabelKey}`)}</span>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className="crm-tasks__rail-card">
            <h3>{t('rail.upcomingDeadlines')}</h3>
            <ul className="crm-tasks__list">
              {preview.upcomingDeadlines.map((item) => (
                <li key={item.id}>
                  <span className="crm-tasks__list-icon" aria-hidden="true">
                    <IhIcon name="clock" size={12} />
                  </span>
                  <div>
                    <strong title={item.title ?? t(`titles.${item.titleKey}`)}>
                      {item.title ?? t(`titles.${item.titleKey}`)}
                    </strong>
                    <span>{item.dueLabel ?? t(`dueLabels.${item.dueLabelKey}`)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-tasks__rail-card crm-tasks__rail-card--ai">
            <h3>{t('rail.aiRecommendations')}</h3>
            <ul className="crm-tasks__recs">
              {preview.aiRecommendations.map((item) => (
                <li key={item.id}>{t(`rail.recommendations.${item.bodyKey}`)}</li>
              ))}
            </ul>
          </section>

          <section className="crm-tasks__rail-card">
            <h3>{t('rail.teamPerformance')}</h3>
            <ul className="crm-tasks__team">
              {preview.teamPerformance.map((member) => {
                const pct =
                  member.total > 0
                    ? Math.round((member.completed / member.total) * 100)
                    : 0;
                return (
                  <li key={member.id}>
                    <div className="crm-tasks__team-head">
                      <strong title={member.name}>{member.name}</strong>
                      <span className="crm-tasks__team-rate">
                        {t('rail.completedRatio', {
                          completed: member.completed,
                          total: member.total,
                        })}
                        <em aria-label={`${pct}%`}>{pct}%</em>
                      </span>
                    </div>
                    <div
                      className="crm-tasks__team-bar"
                      role="progressbar"
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={pct}
                      aria-label={t('rail.completedRatio', {
                        completed: member.completed,
                        total: member.total,
                      })}
                    >
                      <span style={{ width: `${pct}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        </aside>
      </div>
      {editor ? (
        <div className="crm-tasks__editor" role="dialog" aria-modal="true" aria-label={editor.mode === 'create' ? 'Görev oluştur' : 'Görevi düzenle'}>
          <form
            className="crm-tasks__editor-card"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              saveMutation.mutate();
            }}
          >
            <h2>{editor.mode === 'create' ? 'Görev oluştur' : 'Görevi düzenle'}</h2>
            <Input
              label="Başlık"
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              required
            />
            <TextArea
              label="Açıklama"
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
            />
            {editor.mode === 'create' ? (
              <div>
                <Input
                  label="Kişi"
                  value={form.contactLabel}
                  onChange={(e) => void searchContacts(e.target.value)}
                  required
                />
                {contactHits.length ? (
                  <ul className="crm-tasks__contact-hits">
                    {contactHits.map((hit) => (
                      <li key={hit.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setForm((prev) => ({ ...prev, contactId: hit.id, contactLabel: hit.display_name }));
                            setContactHits([]);
                          }}
                        >
                          {hit.display_name}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
            <Select
              label="Atanan"
              value={form.assigneeId}
              onChange={(e) => setForm((prev) => ({ ...prev, assigneeId: e.target.value }))}
            >
              <option value="">—</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name}
                </option>
              ))}
            </Select>
            <Input
              label="Son tarih"
              type="datetime-local"
              value={form.dueDate}
              onChange={(e) => setForm((prev) => ({ ...prev, dueDate: e.target.value }))}
            />
            <Select
              label="Öncelik"
              value={form.priority}
              onChange={(e) => setForm((prev) => ({ ...prev, priority: e.target.value }))}
            >
              {TASK_PRIORITY_ORDER.map((priority) => (
                <option key={priority} value={priority}>
                  {t(`priority.${priority}`)}
                </option>
              ))}
            </Select>
            <div className="crm-tasks__editor-actions">
              <Button type="button" variant="secondary" onClick={() => setEditor(null)}>
                Vazgeç
              </Button>
              <Button type="submit" disabled={saveMutation.isPending}>
                Kaydet
              </Button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
