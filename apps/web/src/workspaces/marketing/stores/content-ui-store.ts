import { create } from 'zustand';

type ContentViewMode = 'table' | 'grid' | 'pipeline' | 'calendar';

type ContentUiState = {
  viewMode: ContentViewMode;
  selectedIds: string[];
  setViewMode: (mode: ContentViewMode) => void;
  setSelectedIds: (ids: string[]) => void;
  clearSelection: () => void;
};

export const useContentUiStore = create<ContentUiState>((set) => ({
  viewMode: 'table',
  selectedIds: [],
  setViewMode: (viewMode) => set({ viewMode }),
  setSelectedIds: (selectedIds) => set({ selectedIds }),
  clearSelection: () => set({ selectedIds: [] }),
}));
