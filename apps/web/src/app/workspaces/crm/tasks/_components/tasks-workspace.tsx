'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { activityMutations, activityQueries, activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import type { ActivityListParams, CrmActivitySummary, TaskViewMode } from '@/workspaces/crm/types/activities';
import { CRM_TASK_STATUSES } from '@/workspaces/crm/types/activities';
import { useActivityUiStore } from '@/workspaces/crm/stores/activity-ui-store';

import { ActivityFormModal } from '../../_components/activity-form-modal';

const VIEW_MODES: TaskViewMode[] = ['list', 'kanban', 'calendar', 'my', 'team'];

function TaskRow({
  task,
  onComplete,
}: {
  task: CrmActivitySummary;
  onComplete: (id: string) => void;
}) {
  const t = useTranslations('crm.tasks');
  return (
    <article className="crm-task-row">
      <div>
        <h3>{task.title}</h3>
        {task.due_date && (
          <time dateTime={task.due_date} className="crm-task-row__due">
            {new Date(task.due_date).toLocaleDateString()}
          </time>
        )}
      </div>
      <div className="crm-task-row__actions">
        <StatusChip tone="default">{task.task_status ?? task.status}</StatusChip>
        <StatusChip tone="warning">{task.priority}</StatusChip>
        {task.status !== 'completed' && (
          <Button type="button" variant="secondary" onClick={() => onComplete(task.id)}>
            {t('complete')}
          </Button>
        )}
      </div>
    </article>
  );
}

export function TasksWorkspace() {
  const t = useTranslations('crm.tasks');
  const tCommon = useTranslations('common');
  const { authLoading, canRead: canView, canCreate } = useCrmAccess();
  const queryClient = useQueryClient();
  const { taskViewMode, setTaskViewMode } = useActivityUiStore();

  const [formOpen, setFormOpen] = useState(false);

  const params: ActivityListParams & { my_tasks?: boolean; team_tasks?: boolean } = useMemo(() => {
    if (taskViewMode === 'my') return { my_tasks: true, page_size: 50 };
    if (taskViewMode === 'team') return { team_tasks: true, page_size: 50 };
    return { page_size: 50 };
  }, [taskViewMode]);

  const tasksQuery = useQuery({
    ...activityQueries.tasks(params),
    enabled: !authLoading && canView,
  });
  const widgetsQuery = useQuery({
    ...activityQueries.widgets(),
    enabled: !authLoading && canView,
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => activityMutations.completeTask(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: activityQueryKeys.all });
    },
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (tasksQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (tasksQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={tasksQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void tasksQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const tasks = tasksQuery.data?.items ?? [];
  const widgets = widgetsQuery.data;

  const kanbanColumns = CRM_TASK_STATUSES.map((status) => ({
    status,
    items: tasks.filter((task) => (task.task_status ?? task.status) === status),
  }));

  return (
    <div className="crm-tasks">
      <header className="crm-tasks__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        {canCreate && (
          <Button type="button" onClick={() => setFormOpen(true)}>
            {t('create')}
          </Button>
        )}
      </header>

      {widgets && (
        <section className="crm-tasks__widgets" aria-label={t('widgets')}>
          <div className="crm-dashboard__kpi-row">
            <article className="crm-dashboard__list-item">
              <span className="crm-dashboard__list-item-title">{t('todaysTasks')}</span>
              <span className="crm-dashboard__list-item-meta">{widgets.todays_tasks.length}</span>
            </article>
            <article className="crm-dashboard__list-item">
              <span className="crm-dashboard__list-item-title">{t('overdueTasks')}</span>
              <span className="crm-dashboard__list-item-meta">{widgets.overdue_tasks.length}</span>
            </article>
            <article className="crm-dashboard__list-item">
              <span className="crm-dashboard__list-item-title">{t('upcomingMeetings')}</span>
              <span className="crm-dashboard__list-item-meta">{widgets.upcoming_meetings.length}</span>
            </article>
            <article className="crm-dashboard__list-item">
              <span className="crm-dashboard__list-item-title">{t('followUpsDue')}</span>
              <span className="crm-dashboard__list-item-meta">{widgets.follow_ups_due.length}</span>
            </article>
          </div>
        </section>
      )}

      <nav className="crm-view-tabs" aria-label={t('viewModes')}>
        {VIEW_MODES.map((mode) => (
          <button
            key={mode}
            type="button"
            className={taskViewMode === mode ? 'crm-view-tabs__tab--active' : 'crm-view-tabs__tab'}
            onClick={() => setTaskViewMode(mode)}
          >
            {t(`views.${mode}` as 'views.list')}
          </button>
        ))}
      </nav>

      {tasks.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : taskViewMode === 'kanban' ? (
        <div className="crm-kanban">
          {kanbanColumns.map((column) => (
            <section key={column.status} className="crm-kanban__column">
              <h3>{t(`statuses.${column.status}` as 'statuses.not_started')}</h3>
              {column.items.map((task) => (
                <TaskRow key={task.id} task={task} onComplete={(id) => completeMutation.mutate(id)} />
              ))}
            </section>
          ))}
        </div>
      ) : (
        <div className="crm-tasks__list">
          {tasks.map((task) => (
            <TaskRow key={task.id} task={task} onComplete={(id) => completeMutation.mutate(id)} />
          ))}
        </div>
      )}

      <ActivityFormModal open={formOpen} onClose={() => setFormOpen(false)} mode="task" defaultType="task" />
    </div>
  );
}
