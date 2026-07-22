import { create } from 'zustand';

type GraphUiState = {
  selectedNodeId: string | null;
  searchQuery: string;
  depth: number;
  limit: number;
  centerEntityType: string | null;
  centerEntityId: string | null;
  expandedNodes: Set<string>;
  categoryFilter: string | null;
  typeFilter: string | null;
  setSelectedNodeId: (id: string | null) => void;
  setSearchQuery: (q: string) => void;
  setDepth: (d: number) => void;
  setLimit: (l: number) => void;
  setCenter: (type: string | null, id: string | null) => void;
  markExpanded: (nodeId: string) => void;
  setCategoryFilter: (c: string | null) => void;
  setTypeFilter: (t: string | null) => void;
  reset: () => void;
};

const initialState = {
  selectedNodeId: null as string | null,
  searchQuery: '',
  depth: 2,
  limit: 50,
  centerEntityType: null as string | null,
  centerEntityId: null as string | null,
  expandedNodes: new Set<string>(),
  categoryFilter: null as string | null,
  typeFilter: null as string | null,
};

export const useRelationshipGraphUiStore = create<GraphUiState>((set) => ({
  ...initialState,
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  setDepth: (d) => set({ depth: d }),
  setLimit: (l) => set({ limit: l }),
  setCenter: (type, id) => set({ centerEntityType: type, centerEntityId: id }),
  markExpanded: (nodeId) =>
    set((s) => {
      const next = new Set(s.expandedNodes);
      next.add(nodeId);
      return { expandedNodes: next };
    }),
  setCategoryFilter: (c) => set({ categoryFilter: c }),
  setTypeFilter: (t) => set({ typeFilter: t }),
  reset: () => set({ ...initialState, expandedNodes: new Set() }),
}));

export function getScoreBandColor(score: number): string {
  if (score >= 76) return 'var(--success)';
  if (score >= 51) return 'var(--crm-accent, var(--accent))';
  if (score >= 26) return 'var(--warning)';
  return 'var(--danger)';
}

export function getScoreBandBg(score: number): string {
  if (score >= 76) return 'var(--success-bg)';
  if (score >= 51) return 'color-mix(in srgb, var(--crm-accent, var(--accent)) 15%, transparent)';
  if (score >= 26) return 'var(--warning-bg)';
  return 'var(--danger-bg)';
}
