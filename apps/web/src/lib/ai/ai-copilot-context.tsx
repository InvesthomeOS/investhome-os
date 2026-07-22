'use client';

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import type { AiActionKind, AiModuleContext } from '@/lib/ai/prompt-library';

export type AiActionPanelState = {
  open: boolean;
  module: AiModuleContext;
  action: AiActionKind | 'executive_summary' | 'email' | 'followup' | 'report' | 'meeting_notes';
  entityLabel?: string;
  entityId?: string;
  seedPrompt?: string;
};

type AiCopilotContextValue = {
  copilotOpen: boolean;
  openCopilot: (seedPrompt?: string) => void;
  closeCopilot: () => void;
  seedPrompt: string | null;
  clearSeedPrompt: () => void;
  actionPanel: AiActionPanelState;
  openActionPanel: (state: Omit<AiActionPanelState, 'open'>) => void;
  closeActionPanel: () => void;
};

const AiCopilotContext = createContext<AiCopilotContextValue | null>(null);

const CLOSED_ACTION: AiActionPanelState = {
  open: false,
  module: 'general',
  action: 'summarize',
};

export function AiCopilotProvider({ children }: { children: ReactNode }) {
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [seedPrompt, setSeedPrompt] = useState<string | null>(null);
  const [actionPanel, setActionPanel] = useState<AiActionPanelState>(CLOSED_ACTION);

  const openCopilot = useCallback((prompt?: string) => {
    if (prompt) setSeedPrompt(prompt);
    setCopilotOpen(true);
  }, []);

  const closeCopilot = useCallback(() => {
    setCopilotOpen(false);
  }, []);

  const clearSeedPrompt = useCallback(() => setSeedPrompt(null), []);

  const openActionPanel = useCallback((state: Omit<AiActionPanelState, 'open'>) => {
    setActionPanel({ ...state, open: true });
  }, []);

  const closeActionPanel = useCallback(() => {
    setActionPanel(CLOSED_ACTION);
  }, []);

  const value = useMemo(
    () => ({
      copilotOpen,
      openCopilot,
      closeCopilot,
      seedPrompt,
      clearSeedPrompt,
      actionPanel,
      openActionPanel,
      closeActionPanel,
    }),
    [
      copilotOpen,
      openCopilot,
      closeCopilot,
      seedPrompt,
      clearSeedPrompt,
      actionPanel,
      openActionPanel,
      closeActionPanel,
    ],
  );

  return <AiCopilotContext.Provider value={value}>{children}</AiCopilotContext.Provider>;
}

export function useAiCopilot(): AiCopilotContextValue {
  const ctx = useContext(AiCopilotContext);
  if (!ctx) {
    throw new Error('useAiCopilot must be used within AiCopilotProvider');
  }
  return ctx;
}

export function useAiCopilotOptional(): AiCopilotContextValue | null {
  return useContext(AiCopilotContext);
}
