import { create } from 'zustand';

import type { ActivityListParams, CalendarViewMode, TaskViewMode } from '@/workspaces/crm/types/activities';

type ActivityUiState = {
  selectedActivityId: string | null;
  selectedIds: string[];
  taskViewMode: TaskViewMode;
  calendarViewMode: CalendarViewMode;
  filters: ActivityListParams;
  filterLogic: 'and' | 'or';
  detailPanelOpen: boolean;
  setSelectedActivityId: (id: string | null) => void;
  setSelectedIds: (ids: string[]) => void;
  toggleSelectedId: (id: string) => void;
  clearSelection: () => void;
  setTaskViewMode: (mode: TaskViewMode) => void;
  setCalendarViewMode: (mode: CalendarViewMode) => void;
  setFilters: (filters: ActivityListParams) => void;
  resetFilters: () => void;
  setFilterLogic: (logic: 'and' | 'or') => void;
  setDetailPanelOpen: (open: boolean) => void;
};

const DEFAULT_FILTERS: ActivityListParams = {
  page: 1,
  page_size: 25,
  sort_by: 'created_at',
  sort_dir: 'desc',
};

export const useActivityUiStore = create<ActivityUiState>((set, get) => ({
  selectedActivityId: null,
  selectedIds: [],
  taskViewMode: 'list',
  calendarViewMode: 'week',
  filters: DEFAULT_FILTERS,
  filterLogic: 'and',
  detailPanelOpen: false,
  setSelectedActivityId: (id) => set({ selectedActivityId: id, detailPanelOpen: Boolean(id) }),
  setSelectedIds: (ids) => set({ selectedIds: ids }),
  toggleSelectedId: (id) => {
    const current = get().selectedIds;
    set({
      selectedIds: current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    });
  },
  clearSelection: () => set({ selectedIds: [] }),
  setTaskViewMode: (mode) => set({ taskViewMode: mode }),
  setCalendarViewMode: (mode) => set({ calendarViewMode: mode }),
  setFilters: (filters) => set({ filters: { ...get().filters, ...filters } }),
  resetFilters: () => set({ filters: DEFAULT_FILTERS, filterLogic: 'and' }),
  setFilterLogic: (logic) => set({ filterLogic: logic }),
  setDetailPanelOpen: (open) => set({ detailPanelOpen: open }),
}));
