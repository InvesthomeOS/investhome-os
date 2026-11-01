'use client';

import { useTranslations } from 'next-intl';

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
  const tChrome = useTranslations('investorPortal.chrome');
  const t = useTranslations('investorPortal');
  const investments = getAllInvestments();

  return (
    <div className="inv-task-filters" role="search" aria-label={t('placeholders.filterTasks')}>
      <input
        type="search"
        className="inv-task-filters__search"
        value={filters.search}
        onChange={(e) => onFiltersChange({ search: e.target.value })}
        placeholder={t('placeholders.searchTasks')}
        aria-label={t('placeholders.searchTasks')}
      />

      <select
        className="inv-task-filters__select"
        value={filters.investmentId}
        onChange={(e) => onFiltersChange({ investmentId: e.target.value })}
        aria-label={tChrome('k3132ed40f5')}
      >
        <option value="all">{tChrome('k294eded6ec')}</option>
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
        aria-label={tChrome('kf43653d7fa')}
      >
        <option value="all">{tChrome('k6405179d24')}</option>
        <option value="open">{tChrome('kcf9b77061f')}</option>
        <option value="in_progress">{tChrome('kf61eadaf15')}</option>
        <option value="pending_review">{tChrome('k9aab7ff44f')}</option>
        <option value="overdue">{tChrome('k07217c7719')}</option>
        <option value="completed">{tChrome('k1798b3ba42')}</option>
        <option value="cancelled">{tChrome('ka1bf92eff4')}</option>
      </select>

      <select
        className="inv-task-filters__select"
        value={filters.priority}
        onChange={(e) =>
          onFiltersChange({ priority: e.target.value as TaskFilterState['priority'] })
        }
        aria-label={tChrome('k870c2d046e')}
      >
        <option value="all">{tChrome('kbc6ba0d1bb')}</option>
        <option value="critical">{tChrome('k04b7b26c8c')}</option>
        <option value="high">{tChrome('kb1a5954a48')}</option>
        <option value="medium">{tChrome('kd404968ea9')}</option>
        <option value="low">{tChrome('ka124947cbd')}</option>
      </select>

      <select
        className="inv-task-filters__select"
        value={filters.category}
        onChange={(e) =>
          onFiltersChange({ category: e.target.value as TaskFilterState['category'] })
        }
        aria-label={tChrome('k459a08e4a2')}
      >
        <option value="all">{tChrome('k060be00f4f')}</option>
        <option value="signature">{tChrome('k2f32be1dc7')}</option>
        <option value="document_upload">{tChrome('kf36e1cd7e7')}</option>
        <option value="review">{tChrome('ke29a79fe0c')}</option>
        <option value="compliance">{tChrome('k68f0ae4911')}</option>
        <option value="tax">{tChrome('k9be70f66f8')}</option>
        <option value="distribution">{tChrome('k1d3c457cbe')}</option>
        <option value="general">{tChrome('k9239ee2cda')}</option>
        <option value="accreditation">{tChrome('kf89dc2b3db')}</option>
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
        aria-label={tChrome('kad5a39820d')}
      >
        <option value="dueDate-asc">{tChrome('kb025103ba9')}</option>
        <option value="dueDate-desc">{tChrome('k1918405788')}</option>
        <option value="priority-asc">{tChrome('k886cbff9d9')}</option>
        <option value="title-asc">{tChrome('k44a4597b55')}</option>
        <option value="updatedAt-desc">{tChrome('k5f0500ccf9')}</option>
      </select>
    </div>
  );
}
