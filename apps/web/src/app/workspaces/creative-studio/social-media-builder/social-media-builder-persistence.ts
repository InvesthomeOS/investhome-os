/**
 * Social Media Builder construction-project selection helpers.
 * Mirrors Presentation Builder last-project restore without changing other builders.
 */

export const SMB_LAST_CONSTRUCTION_PROJECT_KEY = 'ih-smb-last-construction-project-id';
export const SMB_EMERGENCY_SNAPSHOT_KEY = 'ih-smb-draft-emergency';

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
    const raw = window.localStorage.getItem(SMB_LAST_CONSTRUCTION_PROJECT_KEY);
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
    window.localStorage.setItem(SMB_LAST_CONSTRUCTION_PROJECT_KEY, id);
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
      window.localStorage.getItem(SMB_EMERGENCY_SNAPSHOT_KEY),
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
      SMB_EMERGENCY_SNAPSHOT_KEY,
      JSON.stringify({ ...draft, savedAt: Date.now() }),
    );
  } catch {
    /* ignore quota */
  }
}
