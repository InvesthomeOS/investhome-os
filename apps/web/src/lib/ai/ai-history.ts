/**
 * Session / local AI history.
 * Limitation: no dedicated platform AI history API yet — persists in localStorage per org+user.
 */

export type AiHistoryEntry = {
  id: string;
  title: string;
  prompt: string;
  response: string;
  module?: string;
  action?: string;
  source: 'copilot' | 'action' | 'prompt';
  createdAt: string;
  placeholder?: boolean;
};

const STORAGE_PREFIX = 'investhome.ai.history';

function storageKey(orgId: string | null | undefined, userId: string | null | undefined): string {
  return `${STORAGE_PREFIX}:${orgId || 'org'}:${userId || 'user'}`;
}

export function loadAiHistory(orgId?: string | null, userId?: string | null): AiHistoryEntry[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(storageKey(orgId, userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as AiHistoryEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveAiHistory(
  entries: AiHistoryEntry[],
  orgId?: string | null,
  userId?: string | null,
): void {
  if (typeof window === 'undefined') return;
  const capped = entries.slice(0, 100);
  localStorage.setItem(storageKey(orgId, userId), JSON.stringify(capped));
}

export function appendAiHistory(
  entry: Omit<AiHistoryEntry, 'id' | 'createdAt'> & { id?: string; createdAt?: string },
  orgId?: string | null,
  userId?: string | null,
): AiHistoryEntry[] {
  const next: AiHistoryEntry = {
    id: entry.id ?? crypto.randomUUID(),
    createdAt: entry.createdAt ?? new Date().toISOString(),
    title: entry.title,
    prompt: entry.prompt,
    response: entry.response,
    module: entry.module,
    action: entry.action,
    source: entry.source,
    placeholder: entry.placeholder,
  };
  const existing = loadAiHistory(orgId, userId);
  const merged = [next, ...existing];
  saveAiHistory(merged, orgId, userId);
  return merged;
}

export function clearAiHistory(orgId?: string | null, userId?: string | null): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(storageKey(orgId, userId));
}

export function groupHistoryByDate(
  entries: AiHistoryEntry[],
  locale: string,
): { dateLabel: string; dateKey: string; items: AiHistoryEntry[] }[] {
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  const groups = new Map<string, AiHistoryEntry[]>();

  for (const entry of entries) {
    const d = new Date(entry.createdAt);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const list = groups.get(key) ?? [];
    list.push(entry);
    groups.set(key, list);
  }

  return [...groups.entries()]
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([dateKey, items]) => ({
      dateKey,
      dateLabel: new Intl.DateTimeFormat(intlLocale, { dateStyle: 'medium' }).format(
        new Date(items[0].createdAt),
      ),
      items,
    }));
}
