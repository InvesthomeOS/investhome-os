'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type MarketingWorkspaceState = {
  sidebarCollapsed: boolean;
  collapsedGroups: Record<string, boolean>;
  campaignStatusFilter: string;
  calendarView: 'month' | 'week' | 'agenda';
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleGroup: (groupKey: string) => void;
  setCampaignStatusFilter: (filter: string) => void;
  setCalendarView: (view: 'month' | 'week' | 'agenda') => void;
};

export const useMarketingWorkspaceStore = create<MarketingWorkspaceState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      collapsedGroups: {},
      campaignStatusFilter: 'all',
      calendarView: 'month',
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleGroup: (groupKey) =>
        set((state) => ({
          collapsedGroups: {
            ...state.collapsedGroups,
            [groupKey]: !state.collapsedGroups[groupKey],
          },
        })),
      setCampaignStatusFilter: (filter) => set({ campaignStatusFilter: filter }),
      setCalendarView: (view) => set({ calendarView: view }),
    }),
    {
      name: 'investhome-marketing-workspace',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        collapsedGroups: state.collapsedGroups,
        campaignStatusFilter: state.campaignStatusFilter,
        calendarView: state.calendarView,
      }),
    },
  ),
);

type MarketingDashboardLayoutState = {
  hiddenWidgets: string[];
  toggleWidget: (key: string) => void;
};

export const useMarketingDashboardLayoutStore = create<MarketingDashboardLayoutState>()(
  persist(
    (set) => ({
      hiddenWidgets: [],
      toggleWidget: (key) =>
        set((state) => ({
          hiddenWidgets: state.hiddenWidgets.includes(key)
            ? state.hiddenWidgets.filter((k) => k !== key)
            : [...state.hiddenWidgets, key],
        })),
    }),
    { name: 'investhome-marketing-dashboard-layout' },
  ),
);

type MarketingFiltersState = {
  audienceType: string;
  segmentType: string;
  setAudienceType: (type: string) => void;
  setSegmentType: (type: string) => void;
};

export const useMarketingFiltersStore = create<MarketingFiltersState>()((set) => ({
  audienceType: 'all',
  segmentType: 'all',
  setAudienceType: (type) => set({ audienceType: type }),
  setSegmentType: (type) => set({ segmentType: type }),
}));
