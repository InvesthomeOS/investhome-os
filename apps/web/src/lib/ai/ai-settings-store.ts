export type AiResponseLength = 'concise' | 'balanced' | 'detailed';

export type AiWorkspaceSettings = {
  model: string;
  temperature: number;
  language: 'tr' | 'en' | 'auto';
  responseLength: AiResponseLength;
  provider: string;
  allowExternal: boolean;
  shareOrgContext: boolean;
};

const STORAGE_KEY = 'investhome.ai.settings';

export const DEFAULT_AI_SETTINGS: AiWorkspaceSettings = {
  model: 'platform-default',
  temperature: 0.4,
  language: 'auto',
  responseLength: 'balanced',
  provider: 'local',
  allowExternal: false,
  shareOrgContext: true,
};

export function loadAiSettings(): AiWorkspaceSettings {
  if (typeof window === 'undefined') return DEFAULT_AI_SETTINGS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_AI_SETTINGS;
    return { ...DEFAULT_AI_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_AI_SETTINGS;
  }
}

export function saveAiSettings(settings: AiWorkspaceSettings): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}
