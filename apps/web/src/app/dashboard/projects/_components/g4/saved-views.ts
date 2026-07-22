export interface ProjectSavedView {
  id: string;
  name: string;
  scope: 'personal' | 'shared';
  filters: {
    search?: string;
    status?: string;
    project_type?: string;
    development_type?: string;
    priority?: string;
    development_stage?: string;
    city?: string;
    assigned_project_manager?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  };
  view?: string;
  layout?: string;
  createdAt: string;
}

const STORAGE_KEY = 'investhome.projects.g4.saved-views.v1';

function readViews(): ProjectSavedView[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ProjectSavedView[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeViews(views: ProjectSavedView[]) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(views));
}

export function listSavedViews(): ProjectSavedView[] {
  return readViews().sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function saveView(
  view: Omit<ProjectSavedView, 'id' | 'createdAt'> & { id?: string },
): ProjectSavedView {
  const views = readViews();
  const next: ProjectSavedView = {
    id: view.id ?? `view-${Date.now()}`,
    name: view.name,
    scope: view.scope,
    filters: view.filters,
    view: view.view,
    layout: view.layout,
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
