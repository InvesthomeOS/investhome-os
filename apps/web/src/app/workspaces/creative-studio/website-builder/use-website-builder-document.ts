'use client';

import { useCallback, useRef, useState } from 'react';

import {
  createCreativeStudioDocument,
  createCreativeStudioProject,
  createCreativeStudioVersion,
  getCreativeStudioDocument,
  listCreativeStudioDocuments,
  listCreativeStudioProjects,
  listCreativeStudioVersions,
  restoreCreativeStudioVersion,
  saveCreativeStudioDraft,
  type CreativeStudioDocument,
  type CreativeStudioProject,
} from '@/lib/api/creative-studio';
import { fetchProjects, type Project } from '@/lib/api/projects';

import type { WbEditorPersistInput, WbDocumentDraft } from './website-builder-persistence';
import {
  isLegacyMigrationDone,
  loadLegacyLocalStorageDraft,
  markLegacyMigrationDone,
  resolveInitialDraft,
  saveEmergencySnapshot,
  serializeWebsiteBuilderDraft,
} from './website-builder-persistence';
import {
  mapApiVersionToWbVersion,
  resolveCreativeStudioProject,
  resolveWebsiteDocument,
  websiteDocumentTitleForProject,
} from './website-builder-session';
import type { WbVersion } from './website-builder-model';

export type WbLoadStatus = 'idle' | 'loading' | 'ready' | 'error';
export type WbSaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export type UseWebsiteBuilderDocumentResult = {
  loadStatus: WbLoadStatus;
  loadError: string | null;
  saveStatus: WbSaveStatus;
  constructionProjects: Project[];
  constructionProjectId: string | null;
  csProjectId: string | null;
  csDocumentId: string | null;
  versions: WbVersion[];
  activeVersionId: string;
  restoring: boolean;
  bootstrap: () => Promise<WebsiteBuilderBootstrapResult>;
  selectConstructionProject: (
    projectId: string,
  ) => Promise<WbDocumentDraft | null>;
  saveDraft: (input: WbEditorPersistInput) => Promise<boolean>;
  createVersion: (
    input: WbEditorPersistInput,
    label: string,
  ) => Promise<WbVersion | null>;
  refreshVersions: () => Promise<WbVersion[]>;
  restoreVersion: (versionId: string) => Promise<WbDocumentDraft | null>;
  setActiveVersionId: (id: string) => void;
};

export type WebsiteBuilderBootstrapResult =
  | { ok: true; draft: WbDocumentDraft | null }
  | { ok: false; error: string };

export function useWebsiteBuilderDocument(): UseWebsiteBuilderDocumentResult {
  const [loadStatus, setLoadStatus] = useState<WbLoadStatus>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<WbSaveStatus>('idle');
  const [constructionProjects, setConstructionProjects] = useState<Project[]>([]);
  const [constructionProjectId, setConstructionProjectId] = useState<string | null>(
    null,
  );
  const [csProjectId, setCsProjectId] = useState<string | null>(null);
  const [csDocumentId, setCsDocumentId] = useState<string | null>(null);
  const [versions, setVersions] = useState<WbVersion[]>([]);
  const [activeVersionId, setActiveVersionId] = useState('');
  const [restoring, setRestoring] = useState(false);

  const savingRef = useRef(false);
  const saveGenRef = useRef(0);
  const readyRef = useRef(false);
  const restoringRef = useRef(false);
  const documentIdRef = useRef<string | null>(null);

  const applyDocument = useCallback(async (document: CreativeStudioDocument) => {
    documentIdRef.current = document.id;
    setCsDocumentId(document.id);
    const resolved = resolveInitialDraft({
      apiDraftBody: document.draft_body_json,
      legacyDraft: loadLegacyLocalStorageDraft(),
      migrationDone: isLegacyMigrationDone(),
    });

    if (resolved.shouldMigrateToApi && resolved.draft) {
      const body = serializeWebsiteBuilderDraft({
        linkedProjectId: resolved.draft.linkedProjectId,
        sections: resolved.draft.sections,
        selectedSectionId: resolved.draft.selectedSectionId,
        metaTitle: resolved.draft.metaTitle,
        metaDesc: resolved.draft.metaDesc,
        slug: resolved.draft.slug,
        publishStatus: resolved.draft.publishStatus,
        language: resolved.draft.language,
        tone: resolved.draft.tone,
        brief: resolved.draft.brief,
        siteGoal: resolved.draft.siteGoal,
        audience: resolved.draft.audience,
        mainMessage: resolved.draft.mainMessage,
        heroTitle: resolved.draft.heroTitle,
        heroBody: resolved.draft.heroBody,
        ctaPrimary: resolved.draft.ctaPrimary,
        ctaSecondary: resolved.draft.ctaSecondary,
        heroImage: resolved.draft.heroImage,
        galleryImages: resolved.draft.galleryImages,
        legacyProjectId: resolved.draft.legacyProjectId,
        device: resolved.draft.device,
        zoom: resolved.draft.zoom,
        splitPreset: resolved.draft.splitPreset,
      });
      await saveCreativeStudioDraft(document.id, body);
      markLegacyMigrationDone();
      saveEmergencySnapshot(body);
    } else if (!resolved.shouldMigrateToApi) {
      markLegacyMigrationDone();
    }

    const listed = await listCreativeStudioVersions(document.id);
    const mapped = listed.items.map(mapApiVersionToWbVersion);
    setVersions(mapped);
    setActiveVersionId(mapped[0]?.id ?? document.current_version_id ?? '');

    return resolved.draft;
  }, []);

  const resolveForConstructionProject = useCallback(
    async (project: Project): Promise<WbDocumentDraft | null> => {
      const { project: csProject } = await resolveCreativeStudioProject({
        linkedProjectId: project.id,
        linkedProjectName: project.project_name,
        listProjects: () => listCreativeStudioProjects(),
        createProject: (input) => createCreativeStudioProject(input),
      });
      setCsProjectId(csProject.id);

      const { document } = await resolveWebsiteDocument({
        csProjectId: csProject.id,
        documentTitle: websiteDocumentTitleForProject(project.project_name),
        listDocuments: (id) => listCreativeStudioDocuments(id),
        createDocument: (id, input) => createCreativeStudioDocument(id, input),
        getDocument: (id) => getCreativeStudioDocument(id),
      });

      return applyDocument(document);
    },
    [applyDocument],
  );

  const bootstrap = useCallback(async (): Promise<WebsiteBuilderBootstrapResult> => {
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

  const saveDraft = useCallback(async (input: WbEditorPersistInput) => {
    const documentId = documentIdRef.current;
    if (!documentId || !readyRef.current || restoringRef.current) return false;
    if (savingRef.current) return false;
    savingRef.current = true;
    const gen = ++saveGenRef.current;
    setSaveStatus('saving');
    try {
      const body = serializeWebsiteBuilderDraft(input);
      await saveCreativeStudioDraft(documentId, body);
      if (gen !== saveGenRef.current) return false;
      saveEmergencySnapshot(body);
      setSaveStatus('saved');
      return true;
    } catch {
      if (gen === saveGenRef.current) setSaveStatus('error');
      return false;
    } finally {
      savingRef.current = false;
    }
  }, []);

  const refreshVersions = useCallback(async () => {
    const documentId = documentIdRef.current;
    if (!documentId) return [];
    const listed = await listCreativeStudioVersions(documentId);
    const mapped = listed.items.map(mapApiVersionToWbVersion);
    setVersions(mapped);
    if (mapped.length && !mapped.some((v) => v.id === activeVersionId)) {
      setActiveVersionId(mapped[0]!.id);
    }
    return mapped;
  }, [activeVersionId]);

  const createVersion = useCallback(
    async (input: WbEditorPersistInput, label: string) => {
      const documentId = documentIdRef.current;
      if (!documentId || !readyRef.current) return null;
      const body = serializeWebsiteBuilderDraft(input);
      await saveCreativeStudioDraft(documentId, body);
      saveEmergencySnapshot(body);
      const version = await createCreativeStudioVersion(documentId, {
        body_json: body,
        label: label.trim() || undefined,
      });
      const mapped = mapApiVersionToWbVersion(version);
      await refreshVersions();
      setActiveVersionId(mapped.id);
      setSaveStatus('saved');
      return mapped;
    },
    [refreshVersions],
  );

  const restoreVersion = useCallback(async (versionId: string) => {
    const documentId = documentIdRef.current;
    if (!documentId || !readyRef.current) return null;
    restoringRef.current = true;
    setRestoring(true);
    try {
      const result = await restoreCreativeStudioVersion(documentId, versionId, {
        create_version: true,
      });
      const fresh = await getCreativeStudioDocument(documentId);
      documentIdRef.current = fresh.id;
      const draft = await applyDocument(fresh);
      setActiveVersionId(versionId);
      if (result.new_version) {
        // history intact — refresh already done in applyDocument
      }
      setSaveStatus('saved');
      return draft;
    } finally {
      restoringRef.current = false;
      setRestoring(false);
    }
  }, [applyDocument]);

  return {
    loadStatus,
    loadError,
    saveStatus,
    constructionProjects,
    constructionProjectId,
    csProjectId,
    csDocumentId,
    versions,
    activeVersionId,
    restoring,
    bootstrap,
    selectConstructionProject,
    saveDraft,
    createVersion,
    refreshVersions,
    restoreVersion,
    setActiveVersionId,
  };
}

export type { CreativeStudioProject };
