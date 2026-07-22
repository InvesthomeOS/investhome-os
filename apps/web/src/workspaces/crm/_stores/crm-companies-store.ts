'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type CrmCompaniesUiState = {
  search: string;
  statusFilter: string;
  companyTypeFilter: string;
  includeArchived: boolean;
  activeSavedView: string;
  listViewMode: 'table' | 'hierarchy';
  draftFormOpen: boolean;
  setSearch: (value: string) => void;
  setStatusFilter: (value: string) => void;
  setCompanyTypeFilter: (value: string) => void;
  setIncludeArchived: (value: boolean) => void;
  setActiveSavedView: (value: string) => void;
  setListViewMode: (mode: 'table' | 'hierarchy') => void;
  setDraftFormOpen: (open: boolean) => void;
  resetFilters: () => void;
};

export const useCrmCompaniesStore = create<CrmCompaniesUiState>()(
  persist(
    (set) => ({
      search: '',
      statusFilter: '',
      companyTypeFilter: '',
      includeArchived: false,
      activeSavedView: 'all',
      listViewMode: 'table',
      draftFormOpen: false,
      setSearch: (search) => set({ search }),
      setStatusFilter: (statusFilter) => set({ statusFilter }),
      setCompanyTypeFilter: (companyTypeFilter) => set({ companyTypeFilter }),
      setIncludeArchived: (includeArchived) => set({ includeArchived }),
      setActiveSavedView: (activeSavedView) => set({ activeSavedView }),
      setListViewMode: (listViewMode) => set({ listViewMode }),
      setDraftFormOpen: (draftFormOpen) => set({ draftFormOpen }),
      resetFilters: () =>
        set({
          search: '',
          statusFilter: '',
          companyTypeFilter: '',
          includeArchived: false,
          activeSavedView: 'all',
        }),
    }),
    {
      name: 'investhome-crm-companies-ui',
      partialize: (state) => ({
        statusFilter: state.statusFilter,
        companyTypeFilter: state.companyTypeFilter,
        includeArchived: state.includeArchived,
        activeSavedView: state.activeSavedView,
        listViewMode: state.listViewMode,
      }),
    },
  ),
);
