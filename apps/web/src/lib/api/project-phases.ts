import { apiFetch } from '@/lib/api/client';

export type ProjectPhaseRecord = {
  id: string;
  project_id: string;
  name: string;
  display_order: number;
  active: boolean;
  address_line?: string | null;
  city?: string | null;
  region?: string | null;
  postal_code?: string | null;
  unit_count: number;
};

export type PhaseDraft = {
  id?: string;
  name: string;
  display_order: number;
  active: boolean;
  address_line?: string;
};

export async function fetchProjectPhases(
  projectId: string,
  includeInactive = false,
): Promise<ProjectPhaseRecord[]> {
  const query = includeInactive ? '?include_inactive=true' : '';
  return apiFetch<ProjectPhaseRecord[]>(`/inventory/projects/${projectId}/phases${query}`);
}

export async function createProjectPhase(
  projectId: string,
  input: { name: string; display_order: number; active: boolean; address_line?: string },
): Promise<ProjectPhaseRecord> {
  return apiFetch<ProjectPhaseRecord>(`/inventory/projects/${projectId}/phases`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateProjectPhase(
  projectId: string,
  phaseId: string,
  input: { name?: string; display_order?: number; active?: boolean; address_line?: string },
): Promise<ProjectPhaseRecord> {
  return apiFetch<ProjectPhaseRecord>(`/inventory/projects/${projectId}/phases/${phaseId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function reorderProjectPhases(projectId: string, phaseIds: string[]): Promise<ProjectPhaseRecord[]> {
  return apiFetch<ProjectPhaseRecord[]>(`/inventory/projects/${projectId}/phases/reorder`, {
    method: 'PUT',
    body: JSON.stringify({ phase_ids: phaseIds }),
  });
}

export async function saveProjectPhases(projectId: string, drafts: PhaseDraft[]): Promise<void> {
  const existing = await fetchProjectPhases(projectId, true);
  const kept = new Set(drafts.map((draft) => draft.id).filter((id): id is string => Boolean(id)));
  for (const row of existing) {
    if (!kept.has(row.id) && row.active) {
      await updateProjectPhase(projectId, row.id, { active: false });
    }
  }
  const ordered: string[] = [];
  for (const [index, draft] of drafts.entries()) {
    const name = draft.name.trim();
    if (!name) continue;
    if (!draft.id) {
      const created = await createProjectPhase(projectId, {
        name,
        display_order: index,
        active: draft.active,
        address_line: draft.address_line?.trim() || undefined,
      });
      ordered.push(created.id);
    } else {
      await updateProjectPhase(projectId, draft.id, {
        name,
        display_order: index,
        active: draft.active,
        ...(draft.address_line !== undefined ? { address_line: draft.address_line.trim() } : {}),
      });
      ordered.push(draft.id);
    }
  }
  if (ordered.length) await reorderProjectPhases(projectId, ordered);
}
