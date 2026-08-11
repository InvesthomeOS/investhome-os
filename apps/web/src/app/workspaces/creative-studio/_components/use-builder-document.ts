'use client';

/**
 * Creative Studio Document API hook for Landing/Blog/Email/Proposal/Presentation.
 * Resolves CS project by linked_project_id + document by document_type; persists media Asset IDs.
 *
 * Project restore (last selected + draft linkedProjectId) is opt-in (Landing/Blog); Email/etc stay unchanged.
 */

import { useCallback, useRef, useState } from 'react';

import {
  createCreativeStudioDocument,
  createCreativeStudioProject,
  getCreativeStudioDocument,
  listCreativeStudioDocuments,
  listCreativeStudioProjects,
  saveCreativeStudioDraft,
} from '@/lib/api/creative-studio';
import { fetchProjects, type Project } from '@/lib/api/projects';

import {
  BUILDER_KIND_LABELS,
  deserializeBuilderMediaDraft,
  serializeBuilderMediaDraft,
  type BuilderMediaDocumentType,
  type BuilderMediaDraft,
  type BuilderMediaPersistInput,
} from './builder-media-persistence';
import { withCsBuilderTimeout } from './cs-builder-bootstrap';
import {
  documentTitleForProject,
  resolveCreativeStudioDocument,
  resolveCreativeStudioProject,
} from './cs-document-session';

export type BuilderLoadStatus = 'idle' | 'loading' | 'ready' | 'error';
export type BuilderSaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export type BuilderBootstrapResult =
  | { ok: true; draft: BuilderMediaDraft | null }
  | { ok: false; error: string };

/** Opt-in construction project restore (Landing Page Builder). */
export type BuilderPreferredConstructionProject = {
  loadLastId: () => string | null;
  saveLastId: (projectId: string) => void;
  loadDraftLinkedHint?: () => string | null;
  /** Called after a successful draft save (emergency linkedProjectId hint). */
  onDraftSaved?: (body: Record<string, unknown>) => void;
  resolvePreferredId?: (options: {
    projectIds: string[];
    lastSelectedId?: string | null;
    draftLinkedProjectId?: string | null;
  }) => string | null;
};

export type UseBuilderDocumentResult = {
  loadStatus: BuilderLoadStatus;
  loadError: string | null;
  saveStatus: BuilderSaveStatus;
  constructionProjects: Project[];
  constructionProjectId: string | null;
  csProjectId: string | null;
  csDocumentId: string | null;
  bootstrap: () => Promise<BuilderBootstrapResult>;
  selectConstructionProject: (projectId: string) => Promise<BuilderMediaDraft | null>;
  saveDraft: (input: Omit<BuilderMediaPersistInput, 'documentType'>) => Promise<boolean>;
};

function defaultResolvePreferredId(options: {
  projectIds: string[];
  lastSelectedId?: string | null;
  draftLinkedProjectId?: string | null;
}): string | null {
  const ids = new Set(options.projectIds.filter(Boolean));
  if (!ids.size) return null;
  for (const candidate of [options.lastSelectedId, options.draftLinkedProjectId]) {
    if (typeof candidate === 'string' && ids.has(candidate)) return candidate;
  }
  return null;
}

export function useBuilderDocument(options: {
  documentType: BuilderMediaDocumentType;
  /**
   * When set, restore last selected / draft linkedProjectId instead of always projects[0].
   * Landing/Blog enable this; Email/Proposal/Presentation omit it (unchanged behavior).
   */
  preferredConstructionProject?: BuilderPreferredConstructionProject;
}): UseBuilderDocumentResult {
  const { documentType, preferredConstructionProject } = options;
  const kindLabel = BUILDER_KIND_LABELS[documentType];
  const preferredRef = useRef(preferredConstructionProject);
  preferredRef.current = preferredConstructionProject;

  const [loadStatus, setLoadStatus] = useState<BuilderLoadStatus>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<BuilderSaveStatus>('idle');
  const [constructionProjects, setConstructionProjects] = useState<Project[]>([]);
  const [constructionProjectId, setConstructionProjectId] = useState<string | null>(null);
  const [csProjectId, setCsProjectId] = useState<string | null>(null);
  const [csDocumentId, setCsDocumentId] = useState<string | null>(null);

  const savingRef = useRef(false);
  const saveGenRef = useRef(0);
  const bootGenRef = useRef(0);
  const readyRef = useRef(false);
  const documentIdRef = useRef<string | null>(null);
  const documentTypeRef = useRef(documentType);
  documentTypeRef.current = documentType;

  const applyDocument = useCallback(
    async (
      document: {
        id: string;
        draft_body_json: Record<string, unknown> | null;
      },
      linkedProjectId: string,
    ) => {
      documentIdRef.current = document.id;
      setCsDocumentId(document.id);
      let draft = deserializeBuilderMediaDraft(
        document.draft_body_json,
        documentTypeRef.current,
      );

      // Keep linkedProjectId durable when preferred restore is enabled (LPB/BB).
      if (preferredRef.current && draft && draft.linkedProjectId !== linkedProjectId) {
        draft = { ...draft, linkedProjectId };
        const body = serializeBuilderMediaDraft({
          documentType: documentTypeRef.current,
          linkedProjectId,
          coverImage: draft.coverImage,
          galleryImages: draft.galleryImages,
        });
        await saveCreativeStudioDraft(document.id, body);
        preferredRef.current.onDraftSaved?.(body);
      }

      return draft;
    },
    [],
  );

  const resolveForConstructionProject = useCallback(
    async (project: Project): Promise<BuilderMediaDraft | null> => {
      const { project: csProject } = await resolveCreativeStudioProject({
        linkedProjectId: project.id,
        linkedProjectName: project.project_name,
        listProjects: () => listCreativeStudioProjects(),
        createProject: (input) => createCreativeStudioProject(input),
      });
      setCsProjectId(csProject.id);

      const { document } = await resolveCreativeStudioDocument({
        csProjectId: csProject.id,
        documentType: documentTypeRef.current,
        documentTitle: documentTitleForProject(project.project_name, kindLabel),
        listDocuments: (id) => listCreativeStudioDocuments(id),
        createDocument: (id, input) => createCreativeStudioDocument(id, input),
        getDocument: (id) => getCreativeStudioDocument(id),
      });

      return applyDocument(document, project.id);
    },
    [applyDocument, kindLabel],
  );

  const bootstrap = useCallback(async (): Promise<BuilderBootstrapResult> => {
    const gen = ++bootGenRef.current;
    setLoadStatus('loading');
    setLoadError(null);
    readyRef.current = false;
    try {
      const draft = await withCsBuilderTimeout(
        (async () => {
          const response = await fetchProjects({
            page: 1,
            page_size: 100,
            sort_by: 'project_name',
            sort_order: 'asc',
          });
          const projects = response.items ?? [];
          if (gen === bootGenRef.current) {
            setConstructionProjects(projects);
          }
          if (!projects.length) {
            throw new Error('No construction projects available');
          }

          const preferred = preferredRef.current;
          let selected: Project;
          if (preferred) {
            const resolvePreferred =
              preferred.resolvePreferredId ?? defaultResolvePreferredId;
            const preferredId = resolvePreferred({
              projectIds: projects.map((p) => p.id),
              lastSelectedId: preferred.loadLastId(),
              draftLinkedProjectId: preferred.loadDraftLinkedHint?.() ?? null,
            });
            selected =
              projects.find((p) => p.id === preferredId) ?? projects.at(0)!;
            // Persist immediately so subsequent reloads restore explicit selection
            // instead of re-deriving from list order.
            preferred.saveLastId(selected.id);
          } else {
            selected = projects[0]!;
          }

          if (gen === bootGenRef.current) {
            setConstructionProjectId(selected.id);
          }
          // Empty/new docs resolve as draft=null with ok — never leave loading.
          return resolveForConstructionProject(selected);
        })(),
      );
      if (gen !== bootGenRef.current) {
        return { ok: true, draft };
      }
      readyRef.current = true;
      setLoadStatus('ready');
      setSaveStatus(draft ? 'saved' : 'idle');
      return { ok: true, draft };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Load failed';
      if (gen !== bootGenRef.current) {
        return { ok: false, error: message };
      }
      readyRef.current = false;
      setLoadError(message);
      setLoadStatus('error');
      return { ok: false, error: message };
    }
  }, [resolveForConstructionProject]);

  const selectConstructionProject = useCallback(
    async (projectId: string) => {
      const project = constructionProjects.find((p) => p.id === projectId);
      if (!project) return null;
      const gen = ++bootGenRef.current;
      setLoadStatus('loading');
      setLoadError(null);
      readyRef.current = false;
      try {
        preferredRef.current?.saveLastId(projectId);
        setConstructionProjectId(projectId);
        const draft = await withCsBuilderTimeout(
          resolveForConstructionProject(project),
        );
        if (gen !== bootGenRef.current) return draft;
        readyRef.current = true;
        setLoadStatus('ready');
        setSaveStatus(draft ? 'saved' : 'idle');
        return draft;
      } catch (err) {
        if (gen !== bootGenRef.current) return null;
        readyRef.current = false;
        const message = err instanceof Error ? err.message : 'Load failed';
        setLoadError(message);
        setLoadStatus('error');
        return null;
      }
    },
    [constructionProjects, resolveForConstructionProject],
  );

  const saveDraft = useCallback(
    async (input: Omit<BuilderMediaPersistInput, 'documentType'>) => {
      const documentId = documentIdRef.current;
      if (!documentId || !readyRef.current) return false;

      // Wait out in-flight saves instead of dropping (Sil/clear must not lose to autosave).
      const waitStarted = Date.now();
      while (savingRef.current) {
        if (Date.now() - waitStarted > 15_000) return false;
        await new Promise((resolve) => {
          window.setTimeout(resolve, 40);
        });
      }

      savingRef.current = true;
      const gen = ++saveGenRef.current;
      setSaveStatus('saving');
      try {
        const body = serializeBuilderMediaDraft({
          ...input,
          documentType: documentTypeRef.current,
        });
        await saveCreativeStudioDraft(documentId, body);
        if (gen !== saveGenRef.current) return false;
        preferredRef.current?.onDraftSaved?.(body);
        setSaveStatus('saved');
        return true;
      } catch {
        if (gen === saveGenRef.current) setSaveStatus('error');
        return false;
      } finally {
        savingRef.current = false;
      }
    },
    [],
  );

  return {
    loadStatus,
    loadError,
    saveStatus,
    constructionProjects,
    constructionProjectId,
    csProjectId,
    csDocumentId,
    bootstrap,
    selectConstructionProject,
    saveDraft,
  };
}
