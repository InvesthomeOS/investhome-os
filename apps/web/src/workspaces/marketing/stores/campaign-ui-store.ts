import { create } from 'zustand';

export type CampaignViewMode = 'table' | 'card' | 'timeline' | 'calendar';

type CampaignUiState = {
  selectedIds: string[];
  viewMode: CampaignViewMode;
  activeSavedView: string;
  columnVisibility: Record<string, boolean>;
  wizardStep: number;
  draftStorageKey: string;
  setSelectedIds: (ids: string[]) => void;
  toggleSelected: (id: string) => void;
  clearSelection: () => void;
  setViewMode: (mode: CampaignViewMode) => void;
  setActiveSavedView: (key: string) => void;
  setColumnVisibility: (visibility: Record<string, boolean>) => void;
  setWizardStep: (step: number) => void;
  resetWizard: () => void;
};

export const useCampaignUiStore = create<CampaignUiState>((set, get) => ({
  selectedIds: [],
  viewMode: 'table',
  activeSavedView: 'all',
  columnVisibility: {},
  wizardStep: 0,
  draftStorageKey: 'marketing-campaign-wizard-draft',
  setSelectedIds: (ids) => set({ selectedIds: ids }),
  toggleSelected: (id) => {
    const current = get().selectedIds;
    set({
      selectedIds: current.includes(id) ? current.filter((x) => x !== id) : [...current, id],
    });
  },
  clearSelection: () => set({ selectedIds: [] }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setActiveSavedView: (key) => set({ activeSavedView: key }),
  setColumnVisibility: (visibility) => set({ columnVisibility: visibility }),
  setWizardStep: (step) => set({ wizardStep: step }),
  resetWizard: () => set({ wizardStep: 0 }),
}));
