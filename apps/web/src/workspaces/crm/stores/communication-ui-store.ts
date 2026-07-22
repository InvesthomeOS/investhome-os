import { create } from 'zustand';

import type { CrmCommFolderKey } from '@/workspaces/crm/types';

type CommunicationUiState = {
  selectedThreadId: string | null;
  selectedFolder: CrmCommFolderKey;
  searchQuery: string;
  composerOpen: boolean;
  panelCollapsed: 'none' | 'folders' | 'conversation';
  setSelectedThreadId: (id: string | null) => void;
  setSelectedFolder: (folder: CrmCommFolderKey) => void;
  setSearchQuery: (query: string) => void;
  setComposerOpen: (open: boolean) => void;
  setPanelCollapsed: (panel: 'none' | 'folders' | 'conversation') => void;
};

export const useCommunicationUiStore = create<CommunicationUiState>((set) => ({
  selectedThreadId: null,
  selectedFolder: 'inbox',
  searchQuery: '',
  composerOpen: false,
  panelCollapsed: 'none',
  setSelectedThreadId: (id) => set({ selectedThreadId: id }),
  setSelectedFolder: (folder) => set({ selectedFolder: folder, selectedThreadId: null }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setComposerOpen: (open) => set({ composerOpen: open }),
  setPanelCollapsed: (panel) => set({ panelCollapsed: panel }),
}));
