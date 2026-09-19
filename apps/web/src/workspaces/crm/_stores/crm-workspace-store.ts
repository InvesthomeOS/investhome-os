'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type CrmWorkspaceState = {
  sidebarCollapsed: boolean;
  contactTypeFilter: string;
  includeArchived: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setContactTypeFilter: (filter: string) => void;
  setIncludeArchived: (include: boolean) => void;
};

export const useCrmWorkspaceStore = create<CrmWorkspaceState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      contactTypeFilter: 'all',
      includeArchived: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      setContactTypeFilter: (filter) => set({ contactTypeFilter: filter }),
      setIncludeArchived: (include) => set({ includeArchived: include }),
    }),
    {
      name: 'investhome-crm-workspace',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        contactTypeFilter: state.contactTypeFilter,
        includeArchived: state.includeArchived,
      }),
    },
  ),
);
