import { create } from 'zustand';

export type CopilotMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  confidence?: string;
  insufficient_data?: boolean;
  intent?: string | null;
  timestamp: string;
};

type AIUiState = {
  insightCategoryFilter: string | null;
  briefingPeriod: string;
  copilotMessages: CopilotMessage[];
  copilotInput: string;
  setInsightCategoryFilter: (category: string | null) => void;
  setBriefingPeriod: (period: string) => void;
  setCopilotInput: (value: string) => void;
  addCopilotMessage: (message: CopilotMessage) => void;
  clearCopilot: () => void;
};

export const useAIUiStore = create<AIUiState>((set) => ({
  insightCategoryFilter: null,
  briefingPeriod: 'weekly',
  copilotMessages: [],
  copilotInput: '',
  setInsightCategoryFilter: (category) => set({ insightCategoryFilter: category }),
  setBriefingPeriod: (period) => set({ briefingPeriod: period }),
  setCopilotInput: (value) => set({ copilotInput: value }),
  addCopilotMessage: (message) =>
    set((state) => ({ copilotMessages: [...state.copilotMessages, message] })),
  clearCopilot: () => set({ copilotMessages: [], copilotInput: '' }),
}));
