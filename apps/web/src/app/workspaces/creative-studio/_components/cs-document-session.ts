/**
 * Creative Studio project/document resolution shared by Website Builder and other builders.
 * Injectable deps keep resolution unit-testable without network.
 */

import type {
  CreativeStudioDocument,
  CreativeStudioDocumentCreate,
  CreativeStudioDocumentType,
  CreativeStudioProject,
  CreativeStudioProjectCreate,
  CreativeStudioVersion,
} from '@/lib/api/creative-studio';

export type ResolveProjectDeps = {
  linkedProjectId: string;
  linkedProjectName: string;
  listProjects: () => Promise<{ items: CreativeStudioProject[]; total: number }>;
  createProject: (input: CreativeStudioProjectCreate) => Promise<CreativeStudioProject>;
};

export type ResolveDocumentDeps = {
  csProjectId: string;
  documentType: CreativeStudioDocumentType;
  documentTitle: string;
  listDocuments: (
    projectId: string,
  ) => Promise<{ items: CreativeStudioDocument[]; total: number }>;
  createDocument: (
    projectId: string,
    input: CreativeStudioDocumentCreate,
  ) => Promise<CreativeStudioDocument>;
  getDocument: (documentId: string) => Promise<CreativeStudioDocument>;
};

/** Match by linked_project_id; create once if missing. */
export async function resolveCreativeStudioProject(
  deps: ResolveProjectDeps,
): Promise<{ project: CreativeStudioProject; created: boolean }> {
  const listed = await deps.listProjects();
  const existing = listed.items.find(
    (item) =>
      item.linked_project_id === deps.linkedProjectId && item.archived_at == null,
  );
  if (existing) {
    return { project: existing, created: false };
  }
  const project = await deps.createProject({
    name: deps.linkedProjectName.trim() || 'Creative Studio project',
    linked_project_id: deps.linkedProjectId,
    status: 'active',
  });
  return { project, created: true };
}

/** Prefer existing document of the given type; create once with stable title. */
export async function resolveCreativeStudioDocument(
  deps: ResolveDocumentDeps,
): Promise<{ document: CreativeStudioDocument; created: boolean }> {
  const listed = await deps.listDocuments(deps.csProjectId);
  const existing = listed.items.find(
    (item) => item.document_type === deps.documentType && item.archived_at == null,
  );
  if (existing) {
    const document = await deps.getDocument(existing.id);
    return { document, created: false };
  }
  const document = await deps.createDocument(deps.csProjectId, {
    title: deps.documentTitle.trim() || deps.documentType,
    document_type: deps.documentType,
    status: 'draft',
    draft_body_json: {},
  });
  return { document, created: true };
}

export function documentTitleForProject(
  projectName: string,
  kindLabel: string,
): string {
  const name = projectName.trim() || 'Project';
  const label = kindLabel.trim() || 'Document';
  return `${name} ${label}`;
}

export type CsDocumentVersion = {
  id: string;
  label: string;
  updatedAt: string;
  comment?: string;
};

export function mapApiVersionToCsVersion(version: CreativeStudioVersion): CsDocumentVersion {
  const label = version.label?.trim() || `v${version.version_number}`;
  return {
    id: version.id,
    label,
    updatedAt: formatVersionDate(version.created_at),
    comment: version.summary ?? undefined,
  };
}

function formatVersionDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  } catch {
    return iso;
  }
}
