'use client';

import { useMemo, useState } from 'react';

import {
  DEFAULT_TASK_FILTERS,
  DEFAULT_TASK_SORT,
  filterTasks,
  sortTasks,
} from '../../_data/messaging-calculations';
import type { TaskFilterState, TaskSortState } from '../../_data/messaging-types';
import { SectionHeader } from '../section-header';
import { useMessagingState } from '../../_state/messaging-state';
import { TaskFilters } from './task-filters';
import { TaskKpiRow } from './task-kpi-row';
import { TaskTable } from './task-table';

export function TaskDashboard() {
  const { tasks, tasksSummary } = useMessagingState();
  const [filters, setFilters] = useState<TaskFilterState>(DEFAULT_TASK_FILTERS);
  const [sort, setSort] = useState<TaskSortState>(DEFAULT_TASK_SORT);

  const filtered = useMemo(
    () => sortTasks(filterTasks(tasks, filters), sort),
    [tasks, filters, sort],
  );

  const openCount = tasks.filter(
    (t) => t.status === 'open' || t.status === 'in_progress' || t.status === 'overdue',
  ).length;

  return (
    <div className="investor-page inv-tasks-page">
      <h1 className="investor-page__title">Tasks</h1>
      <p className="investor-page__subtitle">
        Action items and deadlines requiring your attention.
      </p>

      <TaskKpiRow summary={tasksSummary} />

      <SectionHeader
        title="Task List"
        subtitle={`${openCount} open · ${filtered.length} shown`}
      />

      <TaskFilters
        filters={filters}
        sort={sort}
        onFiltersChange={(patch) => setFilters((prev) => ({ ...prev, ...patch }))}
        onSortChange={setSort}
      />

      <TaskTable tasks={filtered} />
    </div>
  );
}
