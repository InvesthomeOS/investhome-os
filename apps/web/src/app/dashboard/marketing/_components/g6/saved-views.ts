const STORAGE_KEY = 'investhome.marketing.g6.saved-views';

export type MarketingSavedView = {
  id: string;
  name: string;
  view: string;
  layout?: string;
  status?: string;
  search?: string;
  createdAt: string;
};

function readAll(): MarketingSavedView[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as MarketingSavedView[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(items: MarketingSavedView[]) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 40)));
}

export function listSavedViews(): MarketingSavedView[] {
  return readAll();
}

export function saveView(input: Omit<MarketingSavedView, 'id' | 'createdAt'>): MarketingSavedView {
  const item: MarketingSavedView = {
    ...input,
    id: `sv_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    createdAt: new Date().toISOString(),
  };
  const next = [item, ...readAll().filter((v) => v.name !== item.name)];
  writeAll(next);
  return item;
}

export function deleteSavedView(id: string) {
  writeAll(readAll().filter((v) => v.id !== id));
}
