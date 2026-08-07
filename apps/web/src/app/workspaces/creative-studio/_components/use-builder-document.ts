'use client';

/**
 * Creative Studio Document API hook for Landing/Blog/Email/Proposal/Presentation.
 * Resolves CS project by linked_project_id + document by document_type; persists media Asset IDs.
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

export function useBuilderDocument(options: {
  documentType: BuilderMediaDocumentType;
}): UseBuilderDocumentResult {
  const { documentType } = options;
  const kindLabel = BUILDER_KIND_LABELS[documentType];

  const [loadStatus, setLoadStatus] = useState<BuilderLoadStatus>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<BuilderSaveStatus>('idle');
  const [constructionProjects, setConstructionProjects] = useState<Project[]>([]);
  const [constructionProjectId, setConstructionProjectId] = useState<string | null>(null);
  const [csProjectId, setCsProjectId] = useState<string | null>(null);
  const [csDocumentId, setCsDocumentId] = useState<string | null>(null);

  const savingRef = useRef(false);
  const saveGenRef = useRef(0);
  const readyRef = useRef(false);
  const documentIdRef = useRef<string | null>(null);
  const documentTypeRef = useRef(documentType);
  documentTypeRef.current = documentType;

  const applyDocument = useCallback(
    async (document: {
      id: string;
      draft_body_json: Record<string, unknown> | null;
    }) => {
      documentIdRef.current = document.id;
      setCsDocumentId(document.id);
      return deserializeBuilderMediaDraft(
        document.draft_body_json,
        documentTypeRef.current,
      );
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

      return applyDocument(document);
    },
    [applyDocument, kindLabel],
  );

  const bootstrap = useCallback(async (): Promise<BuilderBootstrapResult> => {
    setLoadStatus('loading');
    setLoadError(null);
    readyRef.current = false;
    try {
      const response = await fetchProjects({
        page: 1,
        page_size: 100,
        sort_by: 'project_name',
        sort_order: 'asc',
      });
      const projects = response.items ?? [];
      setConstructionProjects(projects);
      if (!projects.length) {
        throw new Error('No construction projects available');
      }
      const selected = projects[0]!;
      setConstructionProjectId(selected.id);
      const draft = await resolveForConstructionProject(selected);
      readyRef.current = true;
      setLoadStatus('ready');
      setSaveStatus(draft ? 'saved' : 'idle');
      return { ok: true, draft };
    } catch (err) {
      readyRef.current = false;
      const message = err instanceof Error ? err.message : 'Load failed';
      setLoadError(message);
      setLoadStatus('error');
      return { ok: false, error: message };
    }
  }, [resolveForConstructionProject]);

  const selectConstructionProject = useCallback(
    async (projectId: string) => {
      const project = constructionProjects.find((p) => p.id === projectId);
      if (!project) return null;
      setLoadStatus('loading');
      setLoadError(null);
      readyRef.current = false;
      try {
        setConstructionProjectId(projectId);
        const draft = await resolveForConstructionProject(project);
        readyRef.current = true;
        setLoadStatus('ready');
        setSaveStatus(draft ? 'saved' : 'idle');
        return draft;
      } catch (err) {
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
      if (savingRef.current) return false;
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