/**
 * Creative Studio project/document resolution for Website Builder.
 * Delegates to shared cs-document-session helpers; keeps WB-specific wrappers.
 */

import type { CreativeStudioVersion } from '@/lib/api/creative-studio';

import {
  documentTitleForProject,
  resolveCreativeStudioDocument,
  resolveCreativeStudioProject,
  type ResolveDocumentDeps as SharedResolveDocumentDeps,
  type ResolveProjectDeps,
} from '../_components/cs-document-session';
import type { PublishStatus, WbVersion } from './website-builder-model';

export type { ResolveProjectDeps };
export { resolveCreativeStudioProject };

export type ResolveDocumentDeps = Omit<SharedResolveDocumentDeps, 'documentType'>;

/** Prefer existing website document; create once with stable title. */
export async function resolveWebsiteDocument(
  deps: ResolveDocumentDeps,
): Promise<{ document: Awaited<ReturnType<typeof resolveCreativeStudioDocument>>['document']; created: boolean }> {
  return resolveCreativeStudioDocument({
    ...deps,
    documentType: 'website',
  });
}

export function websiteDocumentTitleForProject(projectName: string): string {
  return documentTitleForProject(projectName, 'Website');
}

export function mapApiVersionToWbVersion(version: CreativeStudioVersion): WbVersion {
  const label = version.label?.trim() || `v${version.version_number}`;
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