import { create } from 'zustand';

import type { MarketingDashboardFilters, MarketingTimeFilter } from '@/workspaces/marketing/schemas/analytics';

type DashboardUiState = {
  editMode: boolean;
  timeFilter: MarketingTimeFilter;
  filters: MarketingDashboardFilters;
  collapsedWidgets: Set<string>;
  setEditMode: (editMode: boolean) => void;
  toggleEditMode: () => void;
  setTimeFilter: (filter: Partial<MarketingTimeFilter>) => void;
  setFilters: (filters: Partial<MarketingDashboardFilters>) => void;
  resetFilters: () => void;
  toggleWidgetCollapse: (key: string) => void;
};

const DEFAULT_TIME_FILTER: MarketingTimeFilter = {
  preset: 'last_30_days',
  timezone: 'UTC',
};

export const useMarketingDashboardStore = create<DashboardUiState>((set) => ({
  editMode: false,
  timeFilter: DEFAULT_TIME_FILTER,
  filters: {},
  collapsedWidgets: new Set(),
  setEditMode: (editMode) => set({ editMode }),
  toggleEditMode: () => set((state) => ({ editMode: !state.editMode })),
  setTimeFilter: (filter) =>
    set((state) => ({ timeFilter: { ...state.timeFilter, ...filter } })),
  setFilters: (filters) =>
    set((state) => ({ filters: { ...state.filters, ...filters } })),
  resetFilters: () => set({ filters: {}, timeFilter: DEFAULT_TIME_FILTER }),
  toggleWidgetCollapse: (key) =>
    set((state) => {
      const next = new Set(state.collapsedWidgets);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return { collapsedWidgets: next };
    }),
}));
