import { create } from 'zustand';

import type { CrmSearchEntityType, CrmSearchViewMode } from '@/workspaces/crm/types/search';

type CrmSearchStore = {
  paletteOpen: boolean;
  query: string;
  activeEntityTab: CrmSearchEntityType | 'all';
  viewMode: CrmSearchViewMode;
  selectedResultIds: string[];
  filterSidebarOpen: boolean;
  queryBuilderDraft: Record<string, unknown> | null;
  activeGroupIndex: number;
  activeItemIndex: number;
  openPalette: () => void;
  closePalette: () => void;
  togglePalette: () => void;
  setQuery: (query: string) => void;
  setActiveEntityTab: (tab: CrmSearchEntityType | 'all') => void;
  setViewMode: (mode: CrmSearchViewMode) => void;
  setSelectedResultIds: (ids: string[]) => void;
  toggleResultSelection: (id: string) => void;
  clearSelection: () => void;
  setFilterSidebarOpen: (open: boolean) => void;
  setQueryBuilderDraft: (draft: Record<string, unknown> | null) => void;
  setActiveGroupIndex: (index: number) => void;
  setActiveItemIndex: (index: number) => void;
  resetNavigation: () => void;
};

export const useCrmSearchStore = create<CrmSearchStore>((set) => ({
  paletteOpen: false,
  query: '',
  activeEntityTab: 'all',
  viewMode: 'list',
  selectedResultIds: [],
  filterSidebarOpen: true,
  queryBuilderDraft: null,
  activeGroupIndex: 0,
  activeItemIndex: 0,
  openPalette: () => set({ paletteOpen: true }),
  closePalette: () => set({ paletteOpen: false, query: '', activeItemIndex: 0, activeGroupIndex: 0 }),
  togglePalette: () => set((s) => ({ paletteOpen: !s.paletteOpen })),
  setQuery: (query) => set({ query }),
  setActiveEntityTab: (activeEntityTab) => set({ activeEntityTab }),
  setViewMode: (viewMode) => set({ viewMode }),
  setSelectedResultIds: (selectedResultIds) => set({ selectedResultIds }),
  toggleResultSelection: (id) =>
    set((s) => ({
      selectedResultIds: s.selectedResultIds.includes(id)
        ? s.selectedResultIds.filter((x) => x !== id)
        : [...s.selectedResultIds, id],
    })),
  clearSelection: () => set({ selectedResultIds: [] }),
  setFilterSidebarOpen: (filterSidebarOpen) => set({ filterSidebarOpen }),
  setQueryBuilderDraft: (queryBuilderDraft) => set({ queryBuilderDraft }),
  setActiveGroupIndex: (activeGroupIndex) => set({ activeGroupIndex }),
  setActiveItemIndex: (activeItemIndex) => set({ activeItemIndex }),
  resetNavigation: () => set({ activeGroupIndex: 0, activeItemIndex: 0 }),
}));
