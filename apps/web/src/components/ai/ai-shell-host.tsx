'use client';

import { AiActionPanel } from '@/components/ai/ai-action-panel';
import { AiCopilotPanel } from '@/components/ai/ai-copilot-panel';
import { AiCopilotProvider } from '@/lib/ai/ai-copilot-context';

export function AiShellHost({ children }: { children: React.ReactNode }) {
  return (
    <AiCopilotProvider>
      {children}
      <AiCopilotPanel />
      <AiActionPanel />
    </AiCopilotProvider>
  );
}
