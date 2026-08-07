/**
 * Creative Studio project/document resolution for Website Builder.
 * Injectable deps keep resolution unit-testable without network.
 */

import type {
  CreativeStudioDocument,
  CreativeStudioDocumentCreate,
  CreativeStudioProject,
  CreativeStudioProjectCreate,
  CreativeStudioVersion,
} from '@/lib/api/creative-studio';

import type { PublishStatus, WbVersion } from './website-builder-model';

export type ResolveProjectDeps = {
  linkedProjectId: string;
  linkedProjectName: string;
  listProjects: () => Promise<{ items: CreativeStudioProject[]; total: number }>;
  createProject: (input: CreativeStudioProjectCreate) => Promise<CreativeStudioProject>;
};

export type ResolveDocumentDeps = {
  csProjectId: string;
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
    name: deps.linkedProjectName.trim() || 'Website project',
    linked_project_id: deps.linkedProjectId,
    status: 'active',
  });
  return { project, created: true };
}

/** Prefer existing website document; create once with stable title. */
export async function resolveWebsiteDocument(
  deps: ResolveDocumentDeps,
): Promise<{ document: CreativeStudioDocument; created: boolean }> {
  const listed = await deps.listDocuments(deps.csProjectId);
  const existing = listed.items.find(
    (item) => item.document_type === 'website' && item.archived_at == null,
  );
  if (existing) {
    const document = await deps.getDocument(existing.id);
    return { document, created: false };
  }
  const document = await deps.createDocument(deps.csProjectId, {
    title: deps.documentTitle.trim() || 'Website',
    document_type: 'website',
    status: 'draft',
    draft_body_json: {},
  });
  return { document, created: true };
}

export function websiteDocumentTitleForProject(projectName: string): string {
  const name = projectName.trim() || 'Project';
  return `${name} Website`;
}

export function mapApiVersionToWbVersion(version: CreativeStudioVersion): WbVersion {
  const label =
    version.label?.trim() ||
    `v${version.version_number}`;
  return {
    id: version.id,
    label,
    status: 'draft' as PublishStatus,
    updatedAt: formatVersionDate(version.created_at),
    noteKey: 'initial',
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
