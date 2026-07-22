'use client';

import type { TaskFilterState, TaskSortState } from '../../_data/messaging-types';
import { getAllInvestments } from '../../_data/investments';

interface TaskFiltersProps {
  filters: TaskFilterState;
  sort: TaskSortState;
  onFiltersChange: (patch: Partial<TaskFilterState>) => void;
  onSortChange: (sort: TaskSortState) => void;
}

export function TaskFilters({
  filters,
  sort,
  onFiltersChange,
  onSortChange,
}: TaskFiltersProps) {
  const investments = getAllInvestments();

  return (
    <div className="inv-task-filters" role="search" aria-label="Filter tasks">
      <input
        type="search"
        className="inv-task-filters__search"
        value={filters.search}
        onChange={(e) => onFiltersChange({ search: e.target.value })}
        placeholder="Search tasks…"
        aria-label="Search tasks"
      />

      <select
        className="inv-task-filters__select"
        value={filters.investmentId}
        onChange={(e) => onFiltersChange({ investmentId: e.target.value })}
        aria-label="Filter by investment"
      >
        <option value="all">All investments</option>
        {investments.map((inv) => (
          <option key={inv.id} value={inv.id}>
            {inv.projectName}
          </option>
        ))}
      </select>

      <select
        className="inv-task-filters__select"
        value={filters.status}
        onChange={(e) =>
          onFiltersChange({ status: e.target.value as TaskFilterState['status'] })
        }
        aria-label="Filter by status"
      >
        <option value="all">All statuses</option>
        <option value="open">Open</option>
        <option value="in_progress">In Progress</option>
        <option value="pending_review">Pending Review</option>
        <option value="overdue">Overdue</option>
        <option value="completed">Completed</option>
        <option value="cancelled">Cancelled</option>
      </select>

      <select
        className="inv-task-filters__select"
        value={filters.priority}
        onChange={(e) =>
          onFiltersChange({ priority: e.target.value as TaskFilterState['priority'] })
        }
        aria-label="Filter by priority"
      >
        <option value="all">All priorities</option>
        <option value="critical">Critical</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>

      <select
        className="inv-task-filters__select"
        value={filters.category}
        onChange={(e) =>
          onFiltersChange({ category: e.target.value as TaskFilterState['category'] })
        }
        aria-label="Filter by category"
      >
        <option value="all">All categories</option>
        <option value="signature">Signature</option>
        <option value="document_upload">Document Upload</option>
        <option value="review">Review</option>
        <option value="compliance">Compliance</option>
        <option value="tax">Tax</option>
        <option value="distribution">Distribution</option>
        <option value="general">General</option>
        <option value="accreditation">Accreditation</option>
      </select>

      <select
        className="inv-task-filters__select"
        value={`${sort.field}-${sort.direction}`}
        onChange={(e) => {
          const [field, direction] = e.target.value.split('-') as [
            TaskSortState['field'],
            TaskSortState['direction'],
          ];
          onSortChange({ field, direction });
        }}
        aria-label="Sort tasks"
      >
        <option value="dueDate-asc">Due date (earliest)</option>
        <option value="dueDate-desc">Due date (latest)</option>
        <option value="priority-asc">Priority</option>
        <option value="title-asc">Title A–Z</option>
        <option value="updatedAt-desc">Recently updated</option>
      </select>
    </div>
  );
}
