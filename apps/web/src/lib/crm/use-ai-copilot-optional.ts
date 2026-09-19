'use client';

/** No-op copilot hook so CRM dashboards compile without the AI workspace. */
export function useAiCopilotOptional() {
  return {
    copilotOpen: false,
    openCopilot: (_seedPrompt?: string) => undefined,
    closeCopilot: () => undefined,
    seedPrompt: null as string | null,
    clearSeedPrompt: () => undefined,
  };
}
