'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type CompanyWorkspaceState = {
  sidebarCollapsed: boolean;
  activityFilter: string;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActivityFilter: (filter: string) => void;
};

export const useCompanyWorkspaceStore = create<CompanyWorkspaceState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      activityFilter: 'all',
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      setActivityFilter: (filter) => set({ activityFilter: filter }),
    }),
    {
      name: 'investhome-company-workspace',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        activityFilter: state.activityFilter,
      }),
    },
  ),
);
