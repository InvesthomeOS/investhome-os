import { create } from 'zustand';

export type ContactTableDensity = 'compact' | 'comfortable' | 'spacious';

type ContactUiState = {
  selectedIds: string[];
  columnVisibility: Record<string, boolean>;
  density: ContactTableDensity;
  activeSavedViewId: string | null;
  draftStorageKey: string;
  setSelectedIds: (ids: string[]) => void;
  toggleSelected: (id: string) => void;
  clearSelection: () => void;
  setColumnVisibility: (visibility: Record<string, boolean>) => void;
  setDensity: (density: ContactTableDensity) => void;
  setActiveSavedViewId: (id: string | null) => void;
};

export const useContactUiStore = create<ContactUiState>((set, get) => ({
  selectedIds: [],
  columnVisibility: {},
  density: 'comfortable',
  activeSavedViewId: null,
  draftStorageKey: 'crm-contact-draft',
  setSelectedIds: (ids) => set({ selectedIds: ids }),
  toggleSelected: (id) => {
    const current = get().selectedIds;
    set({
      selectedIds: current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    });
  },
  clearSelection: () => set({ selectedIds: [] }),
  setColumnVisibility: (visibility) => set({ columnVisibility: visibility }),
  setDensity: (density) => set({ density }),
  setActiveSavedViewId: (id) => set({ activeSavedViewId: id }),
}));
