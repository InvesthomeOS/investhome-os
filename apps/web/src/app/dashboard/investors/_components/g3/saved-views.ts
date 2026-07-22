export interface InvestorSavedView {
  id: string;
  name: string;
  scope: 'personal' | 'shared';
  filters: {
    search?: string;
    status?: string;
    investor_type?: string;
    country?: string;
    preferred_investment_model?: string;
    assigned_to?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  };
  columns?: string[];
  createdAt: string;
}

const STORAGE_KEY = 'investhome.investors.g3.saved-views.v1';

function readViews(): InvestorSavedView[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as InvestorSavedView[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeViews(views: InvestorSavedView[]) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(views));
}

export function listSavedViews(): InvestorSavedView[] {
  return readViews().sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function saveView(view: Omit<InvestorSavedView, 'id' | 'createdAt'> & { id?: string }): InvestorSavedView {
  const views = readViews();
  const next: InvestorSavedView = {
    id: view.id ?? `view-${Date.now()}`,
    name: view.name,
    scope: view.scope,
    filters: view.filters,
    columns: view.columns,
    createdAt: new Date().toISOString(),
  };
  const idx = views.findIndex((v) => v.id === next.id);
  if (idx >= 0) views[idx] = next;
  else views.push(next);
  writeViews(views);
  return next;
}

export function deleteSavedView(id: string) {
  writeViews(readViews().filter((v) => v.id !== id));
}
