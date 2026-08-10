/**
 * Email Builder construction-project selection helpers.
 * Mirrors Blog Builder last-project restore without changing other builders.
 */

export const EB_LAST_CONSTRUCTION_PROJECT_KEY = 'ih-eb-last-construction-project-id';
export const EB_EMERGENCY_SNAPSHOT_KEY = 'ih-eb-draft-emergency';

/** Prefer last explicit selection, then draft/emergency linkedProjectId. */
export function resolvePreferredConstructionProjectId(options: {
  projectIds: string[];
  lastSelectedId?: string | null;
  draftLinkedProjectId?: string | null;
}): string | null {
  const ids = new Set(options.projectIds.filter(Boolean));
  if (!ids.size) return null;
  const candidates = [options.lastSelectedId, options.draftLinkedProjectId];
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && ids.has(candidate)) return candidate;
  }
  return null;
}

export function loadLastConstructionProjectId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(EB_LAST_CONSTRUCTION_PROJECT_KEY);
    return typeof raw === 'string' && raw.trim() ? raw.trim() : null;
  } catch {
    return null;
  }
}

export function saveLastConstructionProjectId(projectId: string): void {
  if (typeof window === 'undefined') return;
  const id = projectId.trim();
  if (!id) return;
  try {
    window.localStorage.setItem(EB_LAST_CONSTRUCTION_PROJECT_KEY, id);
  } catch {
    /* ignore quota */
  }
}

function peekLinkedProjectIdFromSnapshot(raw: string | null): string | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    const linked = (parsed as Record<string, unknown>).linkedProjectId;
    return typeof linked === 'string' && linked.trim() ? linked.trim() : null;
  } catch {
    return null;
  }
}

/** Best-effort linkedProjectId from emergency snapshot (reload before API resolve). */
export function loadPersistedLinkedProjectIdHint(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return peekLinkedProjectIdFromSnapshot(
      window.localStorage.getItem(EB_EMERGENCY_SNAPSHOT_KEY),
    );
  } catch {
    return null;
  }
}

/** Emergency recovery snapshot — linkedProjectId hint + media refs. */
export function saveEmergencySnapshot(draft: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      EB_EMERGENCY_SNAPSHOT_KEY,
      JSON.stringify({ ...draft, savedAt: Date.now() }),
    );
  } catch {
    /* ignore quota */
  }
}
