'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, Dialog, Select, StatusChip, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { ApiError } from '@/lib/api/client';
import {
  generateGptImageDesign,
  generateIdeogramDesign,
  generateSocialDesign,
  getGptImageProviderStatus,
  getIdeogramProviderStatus,
  type GptImageProviderStatus,
  type IdeogramProviderStatus,
} from '@/lib/api/creative-studio';
import { exportDesignToCanva, canvaPreviewPngToObjectUrl, type CanvaExportResult } from '@/lib/api/platform';

import {
  BOTTOM_ACTIONS,
  CAMPAIGN_STATUS_TONE,
  DEFAULT_POSTS,
  FLOATING_ACTIONS,
  FORMAT_PRESETS,
  GENERATION_STATUS_STAGES,
  SMB_HOME,
  SMB_LEFT_RAIL_ICONS,
  SMB_LEFT_RAIL_IDS,
  SMB_PROJECTS,
  SMB_RIGHT_RAIL_ICONS,
  SMB_RIGHT_RAIL_IDS,
  aspectThumbClass,
  createGeneratingPost,
  createPostFromPreset,
  mintCreatePostId,
  resolveFormatSize,
  type AiStatusKey,
  type BgMode,
  type BottomActionKey,
  type CampaignStatus,
  type FloatingActionKey,
  type FormatPresetKey,
  type PlatformKey,
  type SmbLeftRailId,
  type SmbRightRailId,
  type SocialPost,
} from './social-media-builder-model';
import {
  P0_BOTTOM_ACTIONS,
  P0_COMPONENT_KEYS,
  alignElement,
  bringElementForward,
  captionFromElements,
  createButtonElement,
  createImageElement,
  createTextElement,
  duplicateElement,
  ensureUniqueElementIds,
  sendElementBackward,
  type SocialElement,
} from './social-media-builder-elements';
import {
  applyElementPatch,
  canvasShortcutBlockedByTextEdit,
  reflowElementsForFormat,
  sanitizeGeometryPatch,
} from './social-media-builder-layout';
import { defaultSocialInstruction, syncPostCopyFields } from './social-media-builder-generation';
import {
  applyDesignResponseToPosts,
  stampDesignResponseOnPost,
  buildSocialDesignRequest,
  hasDesignInsufficientContext,
  inferDesignMode,
  parseGenerationMetaFromDraft,
  selectedElementToDesignContext,
  serializeGenerationMetaForDraft,
  toDesignGenerationMeta,
  type DesignGenerationMeta,
  type SocialDesignMode,
} from './social-media-builder-design-engine';
import {
  deleteSocialPost,
  hydrateSocialPostsFromDraft,
  hasAppliedCreateResult,
  isInFlightGenerationPost,
  mergeCreateGenerationResult,
  mergeHydratedPostsWithLocal,
  stripInFlightPostsForPersist,
  loadLastConstructionProjectId,
  loadPersistedLinkedProjectIdHint,
  resolvePreferredConstructionProjectId,
  saveEmergencySnapshot,
  saveLastConstructionProjectId,
  serializeSocialPosts,
} from './social-media-builder-persistence';
import { SmbPostCardMore } from './smb-post-overflow-menu';
import { exportSocialPostPng, fetchCanvaLayerImages, renderSocialPostPng, buildCanvaLayersPayload } from './social-media-builder-export';
import { SmbArtboardElements } from './smb-artboard-elements';
import {
  assetUsedByOtherPosts,
  useSmbPostAssetHydration,
} from './social-media-builder-asset-hydration';
import {
  IDEOGRAM_POC_STAGES,
  createFlattenedIdeogramPost,
  parseIdeogramPocSession,
  serializeIdeogramPocSession,
  sessionFromIdeogramResponse,
  type DesignEngineKind,
  type IdeogramPocSession,
  type IdeogramPocVariant,
} from './social-media-builder-ideogram-poc';
import {
  applyArtDirectorVariantToPosts,
  mergeArtDirectorSessionFromResponse,
  parseArtDirectorSession,
  serializeArtDirectorSession,
  type ArtDirectorSession,
  type ArtDirectorVariantKey,
} from './social-media-builder-art-director';
import { applyAiFollowUpEdit } from './social-media-builder-ai-edit';
import {
  GPT_IMAGE_STAGES,
  asFormatPreset,
  createFlattenedGptImagePost,
} from './social-media-builder-gpt-image';

import {
  SmbLeftRailDrawer,
  SmbLocalRail,
  SmbRightRailDrawer,
  SmbZoomToolbar,
} from './social-media-builder-rail-drawers';

import { CsBottomActionToolbar, CsMediaPickerDialog } from '../_components';
import { CsBuilderBootstrapView } from '../_components/cs-builder-bootstrap-view';
import { useBuilderCoverAsset } from '../_components/use-builder-cover-asset';
import { useBuilderDocument } from '../_components/use-builder-document';
import { useCsBuilderHydration } from '../_components/use-cs-builder-hydration';
import {
  CreativeStudioFocusModeSwitcher,
  CreativeStudioFocusWorkspace,
  FocusCanvasLayout,
  FocusFitStage,
  useCreativeStudioFocusMode,
  useFitToViewEngine,
  type FocusRailItem,
} from '../_components/focus-workspace';

import './social-media-builder.css';

function generateErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const status = err.status;
    const detail = (err.message || '').trim();
    if (detail && !/^Request failed with status \d+$/i.test(detail)) {
      return `${status}: ${detail}`;
    }
    if (status === 401) return '401: Unauthorized';
    if (status === 402) return detail || '402: Payment required';
    if (status === 403) return detail || '403: Forbidden';
    if (status === 422) return '422: Invalid generation request';
    if (status === 429) return '429: Rate limited';
    if (status === 500) return '500: Generation server error';
    if (status === 502) return detail || '502: Image provider error';
    return `${status}: ${fallback}`;
  }
  if (err instanceof Error) {
    if (err.name === 'AbortError' || /abort/i.test(err.message)) {
      return `Aborted: ${fallback}`;
    }
    if (/json|schema|malformed/i.test(err.message)) {
      return err.message;
    }
    if (err.message.trim()) return err.message;
  }
  return fallback;
}

function visualTemplateForProject(
  projectId: string,
  templates: typeof SMB_PROJECTS,
): (typeof SMB_PROJECTS)[number] {
  let hash = 0;
  const key = projectId || 'default';
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash + key.charCodeAt(i) * (i + 1)) % templates.length;
  }
  return templates[hash] ?? templates[0]!;
}

export function SocialMediaBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tBootstrap = useTranslations('creativeStudio.ds.bootstrap');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const docApi = useBuilderDocument({
    documentType: 'social',
    preferredConstructionProject: {
      loadLastId: loadLastConstructionProjectId,
      saveLastId: saveLastConstructionProjectId,
      loadDraftLinkedHint: loadPersistedLinkedProjectIdHint,
      resolvePreferredId: resolvePreferredConstructionProjectId,
      onDraftSaved: saveEmergencySnapshot,
    },
  });

  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus>('ready');
  const [saved, setSaved] = useState(true);
  const [aiStatus, setAiStatus] = useState<AiStatusKey>('idle');
  const [generating, setGenerating] = useState(false);
  const [generationMeta, setGenerationMeta] = useState<DesignGenerationMeta | null>(null);
  const [aiPrompt, setAiPrompt] = useState('');
  const [leftRailId, setLeftRailId] = useState<SmbLeftRailId>('templates');
  const [rightRailId, setRightRailId] = useState<SmbRightRailId>('content');
  const focus = useCreativeStudioFocusMode({ storageKey: 'social-media-builder' });

  const [posts, setPosts] = useState<SocialPost[]>(DEFAULT_POSTS);
  const [selectedPostId, setSelectedPostId] = useState(DEFAULT_POSTS[0]?.id ?? 'p1');
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [editingElementId, setEditingElementId] = useState<string | null>(null);
  const [historyPast, setHistoryPast] = useState<SocialPost[][]>([]);
  const [historyFuture, setHistoryFuture] = useState<SocialPost[][]>([]);
  const [formatPreset, setFormatPreset] = useState<FormatPresetKey>('square');
  const [platforms, setPlatforms] = useState<Set<PlatformKey>>(
    () => new Set(['instagram', 'facebook', 'linkedin', 'x']),
  );
  const [brandLogo, setBrandLogo] = useState(true);
  const [bgMode, setBgMode] = useState<BgMode>('image');
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [floatingMoreOpen, setFloatingMoreOpen] = useState(false);
  const [alignMenuOpen, setAlignMenuOpen] = useState(false);
  const [layerMenuOpen, setLayerMenuOpen] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [elementImagePickerOpen, setElementImagePickerOpen] = useState(false);
  const [aiDesignCollapsed, setAiDesignCollapsed] = useState(false);
  const [designEngine, setDesignEngine] = useState<DesignEngineKind>('native');
  const designEngineRef = useRef<DesignEngineKind>('native');
  const [ideogramStatus, setIdeogramStatus] = useState<IdeogramProviderStatus | null>(null);
  const [gptImageStatus, setGptImageStatus] = useState<GptImageProviderStatus | null>(null);
  const [ideogramSession, setIdeogramSession] = useState<IdeogramPocSession | null>(null);
  const [ideogramError, setIdeogramError] = useState<string | null>(null);
  const ideogramSessionRef = useRef<IdeogramPocSession | null>(null);
  const [artDirectorSession, setArtDirectorSession] = useState<ArtDirectorSession | null>(null);
  const artDirectorSessionRef = useRef<ArtDirectorSession | null>(null);
  const [pilotDesignChosen, setPilotDesignChosen] = useState(false);
  const [postMenuId, setPostMenuId] = useState<string | null>(null);
  const [deletePostId, setDeletePostId] = useState<string | null>(null);
  const [canvaBusy, setCanvaBusy] = useState(false);
  const [canvaPreviewByPostId, setCanvaPreviewByPostId] = useState<
    Record<
      string,
      {
        src: string;
        transferMode: 'editable' | 'png';
        editUrl: string;
        designId: string | null;
      }
    >
  >({});
  const canvaPreviewByPostIdRef = useRef(canvaPreviewByPostId);
  canvaPreviewByPostIdRef.current = canvaPreviewByPostId;

  const filmstripRef = useRef<HTMLDivElement | null>(null);
  const genIdleTimerRef = useRef<number | null>(null);
  const genStageTimerRef = useRef<number | null>(null);
  const generateAbortRef = useRef(0);
  const deletedPostIdsRef = useRef<Set<string>>(new Set());
  const generatingRef = useRef(false);
  const persistEpochRef = useRef(0);
  const createInflightIdRef = useRef<string | null>(null);
  const postsRef = useRef(posts);
  postsRef.current = posts;
  const selectedPostIdRef = useRef(selectedPostId);
  selectedPostIdRef.current = selectedPostId;
  const selectedElementIdRef = useRef(selectedElementId);
  selectedElementIdRef.current = selectedElementId;
  const editingElementIdRef = useRef(editingElementId);
  editingElementIdRef.current = editingElementId;
  const gestureHistoryPushedRef = useRef(false);

  const selectedConstruction = useMemo(
    () =>
      docApi.constructionProjects.find((p) => p.id === docApi.constructionProjectId) ?? null,
    [docApi.constructionProjects, docApi.constructionProjectId],
  );
  const project = useMemo(() => {
    const visualProj = visualTemplateForProject(
      docApi.constructionProjectId || selectedConstruction?.project_name || 'default',
      SMB_PROJECTS,
    );
    if (!selectedConstruction) return visualProj;
    return { ...visualProj, name: selectedConstruction.project_name || visualProj.name };
  }, [docApi.constructionProjectId, selectedConstruction]);

  const coverAsset = useBuilderCoverAsset({
    templateCoverUrl: project.coverUrl,
    linkedProjectId: docApi.constructionProjectId,
    seedFromTemplate: false,
    scopeToLinkedProject: true,
  });

  const selectedPost = useMemo(
    () => posts.find((p) => p.id === selectedPostId) ?? posts[0] ?? null,
    [posts, selectedPostId],
  );
  const hasRealLogoLayer = Boolean(
    selectedPost?.elements.some((el) => el.type === 'IMAGE' && el.role === 'logo' && el.assetId),
  );
  const coverObjectPosition = useMemo(() => {
    const crop = selectedPost?.imageCrop;
    if (crop && typeof crop.object_position === 'string') return crop.object_position;
    if (crop && typeof crop.objectPosition === 'string') return crop.objectPosition;
    const bg = selectedPost?.elements.find(
      (el) => el.type === 'IMAGE' && (el.role === 'background' || el.role === 'cover'),
    );
    if (bg && bg.type === 'IMAGE' && bg.objectPosition) return bg.objectPosition;
    return undefined;
  }, [selectedPost]);
  const selectedElement =
    selectedPost?.elements.find((el) => el.id === selectedElementId) ?? null;
  const contentSize = resolveFormatSize(formatPreset);

  const smbFitPadX = focus.isFullscreen ? 16 : 24;
  const smbFitPadY = focus.isFullscreen ? 16 : 32;

  const ftv = useFitToViewEngine({
    contentWidth: Math.max(1, contentSize.w),
    contentHeight: Math.max(1, contentSize.h),
    enabled: true,
    contentKey: `${formatPreset}-${selectedPost?.id ?? 'empty'}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}-${smbFitPadX}x${smbFitPadY}`,
    canvasType: 'artwork',
    padX: smbFitPadX,
    padY: smbFitPadY,
    cssWidthVar: '--smb-stage-w',
    cssHeightVar: '--smb-stage-h',
  });

  const smbLeftRail: FocusRailItem[] = useMemo(
    () =>
      SMB_LEFT_RAIL_IDS.map((id) => ({
        id,
        icon: SMB_LEFT_RAIL_ICONS[id],
        labelKey: 'brief',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const smbRightRail: FocusRailItem[] = useMemo(
    () =>
      SMB_RIGHT_RAIL_IDS.map((id) => ({
        id,
        icon: SMB_RIGHT_RAIL_ICONS[id],
        labelKey: 'export',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const localLeftItems = useMemo(
    () => smbLeftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [smbLeftRail],
  );
  const localRightItems = useMemo(
    () => smbRightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [smbRightRail],
  );

  useEffect(() => {
    if (ftv.autoFit) ftv.fitToView();
    else ftv.refit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.mode, focus.isFullscreen, formatPreset, selectedPostId, smbFitPadX, smbFitPadY]);

  useEffect(() => {
    if (!focus.isFullscreen) setAiDesignCollapsed(false);
  }, [focus.isFullscreen]);

  useEffect(() => {
    return () => {
      for (const preview of Object.values(canvaPreviewByPostIdRef.current)) {
        if (preview.src.startsWith('blob:')) URL.revokeObjectURL(preview.src);
      }
    };
  }, []);

  const applyDraftPosts = useCallback(
    (draft: {
      posts?: Record<string, unknown>[];
      coverImage?: { asset_id?: string | null } | null;
      selectedPostId?: string | null;
      brandLogo?: boolean;
      platforms?: string[];
      linkedProjectId?: string | null;
      ideogramPoc?: Record<string, unknown> | null;
      artDirector?: Record<string, unknown> | null;
      designProvider?: 'native' | 'ideogram' | 'gpt-image';
    } | null) => {
      const coverId = draft?.coverImage?.asset_id ?? null;
      const hydrated = hydrateSocialPostsFromDraft({
        posts: draft?.posts,
        coverAssetId: coverId,
        linkedProjectId: draft?.linkedProjectId ?? docApi.constructionProjectId,
        selectedPostId: draft?.selectedPostId,
      });
      const incoming = hydrated.posts.filter((p) => !deletedPostIdsRef.current.has(p.id));
      const merged = mergeHydratedPostsWithLocal({
        incoming,
        local: postsRef.current,
        deletedIds: deletedPostIdsRef.current,
        generating: generatingRef.current,
        incomingSelectedPostId: hydrated.selectedPostId,
        localSelectedPostId: selectedPostIdRef.current,
      });
      const nextPosts = merged.posts.map((p) => ({
        ...p,
        elements: ensureUniqueElementIds(p.elements),
      }));
      postsRef.current = nextPosts;
      setPosts(nextPosts);
      const active =
        nextPosts.find((p) => p.id === merged.selectedPostId) ?? nextPosts[0] ?? null;
      const nextSelected = active?.id ?? '';
      selectedPostIdRef.current = nextSelected;
      setSelectedPostId(nextSelected);
      const skipClobber =
        generatingRef.current || nextPosts.some((p) => isInFlightGenerationPost(p));
      if (!skipClobber) {
        setHistoryPast([]);
        setHistoryFuture([]);
        setEditingElementId(null);
        setSelectedElementId(null);
      }
      if (active) setFormatPreset(active.formatPreset);
      if (typeof draft?.brandLogo === 'boolean') setBrandLogo(draft.brandLogo);
      if (Array.isArray(draft?.platforms) && draft.platforms.length) {
        setPlatforms(
          new Set(
            draft.platforms.filter(
              (p): p is PlatformKey =>
                p === 'instagram' || p === 'facebook' || p === 'linkedin' || p === 'x',
            ),
          ),
        );
      }
      const coverRef =
        active?.coverAssetId || coverId
          ? {
              asset_id: active?.coverAssetId || coverId,
              url: null,
              alt: null,
              role: 'cover' as const,
            }
          : null;
      if (!skipClobber) {
        coverAsset.hydrateMedia(coverRef, draft ? [] : []);
      }
      const fromPost = parseGenerationMetaFromDraft(active?.generationMeta);
      if (draft && 'generationMeta' in draft) {
        setGenerationMeta(
          parseGenerationMetaFromDraft(
            (draft as { generationMeta?: Record<string, unknown> | null }).generationMeta,
          ) ?? fromPost,
        );
      } else {
        setGenerationMeta(fromPost);
      }
      if (draft && 'ideogramPoc' in draft) {
        const restored = parseIdeogramPocSession(draft.ideogramPoc);
        ideogramSessionRef.current = restored;
        setIdeogramSession(restored);
      }
      if (draft && 'artDirector' in draft) {
        const restored = parseArtDirectorSession(
          draft.artDirector,
          draft.linkedProjectId ?? docApi.constructionProjectId,
        );
        artDirectorSessionRef.current = restored;
        setArtDirectorSession(restored);
        setPilotDesignChosen(Boolean(restored?.variants.length));
      }
      if (
        draft?.designProvider === 'native' ||
        draft?.designProvider === 'ideogram' ||
        draft?.designProvider === 'gpt-image'
      ) {
        designEngineRef.current = draft.designProvider;
        setDesignEngine(draft.designProvider);
      }
    },
    [coverAsset, docApi.constructionProjectId],
  );

  const hydration = useCsBuilderHydration({
    bootstrap: docApi.bootstrap,
    onSuccess: (draft) => {
      applyDraftPosts(draft);
      setSaved(Boolean(draft));
    },
  });
  const hydrated = hydration.hydrated;

  const postAssets = useSmbPostAssetHydration({
    enabled: hydrated && Boolean(docApi.constructionProjectId),
    posts,
    selectedPostId,
    linkedProjectId: docApi.constructionProjectId,
    ensureDisplayUrl: coverAsset.media.ensureDisplayUrl,
    getCachedDisplayUrl: coverAsset.media.getCachedDisplayUrl,
  });
  /** Authenticated Media Library blob only — never Unsplash / template fallback. */
  const artboardSrc = postAssets.artboardSrc;
  const artboardState =
    selectedPost?.generationLifecycle === 'generating' ||
    selectedPost?.generationLifecycle === 'creating'
      ? 'loading'
      : postAssets.artboardState;
  const elementDisplayUrls = postAssets.displayUrls;
  const canvaPreview =
    selectedPost?.generationLifecycle === 'generating' ||
    selectedPost?.generationLifecycle === 'creating'
      ? undefined
      : canvaPreviewByPostId[selectedPostId];
  const displayArtboardSrc = canvaPreview?.src || artboardSrc;
  const displayArtboardState = canvaPreview?.src ? 'ready' : artboardState;
  const hideOsLayers = Boolean(canvaPreview?.src) && canvaPreview?.transferMode === 'editable';

  function clearCanvaRaster(postId: string) {
    setCanvaPreviewByPostId((prev) => {
      const current = prev[postId];
      if (!current?.src) return prev;
      if (current.src.startsWith('blob:')) URL.revokeObjectURL(current.src);
      return { ...prev, [postId]: { ...current, src: '' } };
    });
  }

  useEffect(() => {
    return () => {
      if (genIdleTimerRef.current != null) window.clearTimeout(genIdleTimerRef.current);
      generateAbortRef.current += 1;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void getIdeogramProviderStatus()
      .then((status) => {
        if (!cancelled) setIdeogramStatus(status);
      })
      .catch(() => {
        if (!cancelled) {
          setIdeogramStatus({
            available: false,
            configured: false,
            enabled: false,
            provider: 'ideogram',
            model: 'V_4_0',
            remix_endpoint: '',
            generate_endpoint: '',
            reason: 'ideogram_status_unavailable',
          });
        }
      });
    void getGptImageProviderStatus()
      .then((status) => {
        if (!cancelled) setGptImageStatus(status);
      })
      .catch(() => {
        if (!cancelled) {
          setGptImageStatus({
            available: false,
            configured: false,
            enabled: false,
            provider: 'gpt-image',
            model: 'gpt-image-2',
            edits_endpoint: '',
            generate_endpoint: '',
            reason: 'gpt_image_status_unavailable',
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function markDirty() {
    setSaved(false);
  }

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  function clonePostsSnapshot(source: SocialPost[] = postsRef.current): SocialPost[] {
    return source.map((p) => ({
      ...p,
      elements: p.elements.map((el) => ({ ...el })),
    }));
  }

  function pushHistory() {
    setHistoryPast((prev) => [...prev.slice(-49), clonePostsSnapshot()]);
    setHistoryFuture([]);
  }

  function undoHistory() {
    setHistoryPast((past) => {
      if (!past.length) return past;
      const prev = past[past.length - 1]!;
      setHistoryFuture((future) => [clonePostsSnapshot(), ...future].slice(0, 50));
      setPosts(clonePostsSnapshot(prev));
      setEditingElementId(null);
      markDirty();
      return past.slice(0, -1);
    });
  }

  function redoHistory() {
    setHistoryFuture((future) => {
      if (!future.length) return future;
      const [next, ...rest] = future;
      setHistoryPast((past) => [...past, clonePostsSnapshot()].slice(-50));
      setPosts(clonePostsSnapshot(next));
      setEditingElementId(null);
      markDirty();
      return rest;
    });
  }

  function beginGestureHistory() {
    if (gestureHistoryPushedRef.current) return;
    gestureHistoryPushedRef.current = true;
    pushHistory();
  }

  function endGestureHistory() {
    gestureHistoryPushedRef.current = false;
  }

  const buildPersistPayload = useCallback(() => {
    const current = postsRef.current;
    const persistable = stripInFlightPostsForPersist(current);
    const latestSelected = selectedPostIdRef.current;
    const persistSelected =
      latestSelected && persistable.some((p) => p.id === latestSelected)
        ? latestSelected
        : persistable[0]?.id ?? null;
    const active = current.find((p) => p.id === latestSelected) ?? persistable[0] ?? current[0] ?? null;
    const coverId = active?.coverAssetId ?? null;
    // Canonical persist: Asset ID only — never blob:/object: display URLs.
    const coverFromPost = coverId
      ? {
          asset_id: coverId,
          url: null as string | null,
          alt: null as string | null,
          role: 'cover' as const,
        }
      : null;
    return {
      linkedProjectId: docApi.constructionProjectId,
      coverImage: coverFromPost,
      posts: serializeSocialPosts(
        persistable.map((p) => ({
          ...p,
          thumbUrl: '',
          linkedProjectId: docApi.constructionProjectId,
        })),
      ),
      selectedPostId: persistSelected,
      brandLogo,
      platforms: Array.from(platforms),
      generationMeta: serializeGenerationMetaForDraft(generationMeta),
      ideogramPoc: serializeIdeogramPocSession(ideogramSessionRef.current),
      artDirector: serializeArtDirectorSession(artDirectorSessionRef.current),
      designProvider: designEngineRef.current,
    };
  }, [
    brandLogo,
    docApi.constructionProjectId,
    generationMeta,
    platforms,
  ]);

  const persistNow = useCallback(
    async (announce = false) => {
      if (docApi.loadStatus !== 'ready') return;
      const ok = await docApi.saveDraft(buildPersistPayload());
      if (ok) {
        setSaved(true);
        if (announce) showToast(t('toasts.saved'));
      } else if (announce) {
        showToast(t('toasts.saveFailed'));
      }
    },
    [buildPersistPayload, docApi, t],
  );

  useEffect(() => {
    if (!hydrated || docApi.loadStatus !== 'ready') return;
    if (generatingRef.current) return;
    const epoch = persistEpochRef.current;
    const id = window.setTimeout(() => {
      void (async () => {
        if (generatingRef.current) return;
        if (epoch !== persistEpochRef.current) return;
        const ok = await docApi.saveDraft(() => {
          if (generatingRef.current) return null;
          if (epoch !== persistEpochRef.current) return null;
          return buildPersistPayload();
        });
        if (ok) setSaved(true);
      })();
    }, 2000);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, docApi.loadStatus, coverAsset.coverImage, posts, selectedPostId, brandLogo, platforms, generating]);

  useEffect(() => {
    if (!floatingMoreOpen && !alignMenuOpen && !layerMenuOpen) return;
    function onDocPointer(event: MouseEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.closest?.('[data-testid="smb-floating-actions"]')) return;
      setFloatingMoreOpen(false);
      setAlignMenuOpen(false);
      setLayerMenuOpen(false);
    }
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        setFloatingMoreOpen(false);
        setAlignMenuOpen(false);
        setLayerMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [floatingMoreOpen, alignMenuOpen, layerMenuOpen]);

  useEffect(() => {
    function onKey(event: globalThis.KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase() ?? '';
      const typing =
        tag === 'input' ||
        tag === 'textarea' ||
        tag === 'select' ||
        Boolean(target?.isContentEditable);
      const editing = Boolean(editingElementIdRef.current);
      const mod = event.metaKey || event.ctrlKey;

      // Text-edit mode owns typing keys. Canvas must not delete/nudge/undo/capture Enter.
      if (canvasShortcutBlockedByTextEdit(editing, event.key)) {
        return;
      }

      if (mod && event.key.toLowerCase() === 'z' && !event.shiftKey) {
        if (typing) return;
        event.preventDefault();
        undoHistory();
        return;
      }
      if ((mod && event.key.toLowerCase() === 'z' && event.shiftKey) || (mod && event.key.toLowerCase() === 'y')) {
        if (typing) return;
        event.preventDefault();
        redoHistory();
        return;
      }

      if (event.key === 'Escape') {
        if (editing) {
          event.preventDefault();
          setEditingElementId(null);
          return;
        }
        if (selectedElementIdRef.current) {
          event.preventDefault();
          setSelectedElementId(null);
        }
        return;
      }

      if (typing || canvasLocked || focus.mode === 'preview') return;
      const selectedId = selectedElementIdRef.current;
      if (!selectedId) return;

      if (event.key === 'Delete' || event.key === 'Backspace') {
        event.preventDefault();
        const post = postsRef.current.find((p) => p.id === selectedPostIdRef.current);
        if (!post) return;
        replaceElements(post.elements.filter((el) => el.id !== selectedId));
        setSelectedElementId(null);
        showToast(t('toasts.elementRemoved'));
        return;
      }

      const arrow =
        event.key === 'ArrowLeft' ||
        event.key === 'ArrowRight' ||
        event.key === 'ArrowUp' ||
        event.key === 'ArrowDown';
      if (!arrow) return;
      event.preventDefault();
      const step = event.shiftKey ? 10 : 1;
      const post = postsRef.current.find((p) => p.id === selectedPostIdRef.current);
      const el = post?.elements.find((e) => e.id === selectedId);
      if (!el) return;
      let dx = 0;
      let dy = 0;
      if (event.key === 'ArrowLeft') dx = -step;
      if (event.key === 'ArrowRight') dx = step;
      if (event.key === 'ArrowUp') dy = -step;
      if (event.key === 'ArrowDown') dy = step;
      patchElement(selectedId, { x: el.x + dx, y: el.y + dy });
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasLocked, focus.mode, t]);

  async function handleProjectChange(id: string) {
    deletedPostIdsRef.current = new Set();
    generateAbortRef.current += 1;
    generatingRef.current = false;
    createInflightIdRef.current = null;
    persistEpochRef.current += 1;
    coverAsset.clearCover();
    const draft = await docApi.selectConstructionProject(id);
    applyDraftPosts(draft);
    setGenerationMeta(null);
    setSaved(Boolean(draft));
  }

  function updateSelectedPost(updater: (post: SocialPost) => SocialPost, opts?: { history?: boolean }) {
    if (opts?.history !== false) pushHistory();
    setPosts((prev) =>
      prev.map((p) => {
        if (p.id !== selectedPostId) return p;
        return syncPostCopyFields(updater(p));
      }),
    );
    markDirty();
  }

  function patchPost(patch: Partial<SocialPost>) {
    updateSelectedPost((p) => ({ ...p, ...patch }));
  }

  function selectElement(elementId: string | null) {
    if (editingElementId && editingElementId !== elementId) {
      setEditingElementId(null);
    }
    if (!elementId) {
      setSelectedElementId(null);
      setEditingElementId(null);
      setAlignMenuOpen(false);
      setLayerMenuOpen(false);
      setFloatingMoreOpen(false);
      return;
    }
    const exists = selectedPost?.elements.some((el) => el.id === elementId);
    if (!exists) {
      setSelectedElementId(null);
      setEditingElementId(null);
      setAlignMenuOpen(false);
      setLayerMenuOpen(false);
      setFloatingMoreOpen(false);
      return;
    }
    setSelectedElementId(elementId);
  }

  function patchElement(
    elementId: string,
    patch: Partial<SocialElement>,
    opts?: { live?: boolean; history?: boolean },
  ) {
    const clean = sanitizeGeometryPatch(patch);
    const live = Boolean(opts?.live);
    if (!live && opts?.history !== false) pushHistory();
    setPosts((prev) =>
      prev.map((p) => {
        if (p.id !== selectedPostId) return p;
        const current = p.elements.find((el) => el.id === elementId);
        if (!current) return p;
        const w = Math.max(1, p.width || contentSize.w);
        const h = Math.max(1, p.height || contentSize.h);
        const textContentChange =
          current.type === 'TEXT' && ('fontSize' in clean || 'content' in clean);
        const liveGeometry = live && !textContentChange;
        const refitText = textContentChange && !('width' in clean && 'height' in clean);
        // Live drag/resize: constrain only the active element — collision resolve on commit would fight the pointer.
        // Live TEXT content edits still refit height and resolve collisions so the box grows as the user types.
        const result = applyElementPatch(current, clean, w, h, {
          refitText: liveGeometry ? false : refitText,
          resolveAll:
            liveGeometry
              ? undefined
              : refitText || 'width' in clean || 'height' in clean || 'y' in clean || 'x' in clean
                ? p.elements
                : undefined,
        });
        const nextElements =
          result.elements ?? p.elements.map((el) => (el.id === elementId ? result.element : el));
        return syncPostCopyFields({ ...p, elements: nextElements });
      }),
    );
    markDirty();
  }

  function replaceElements(elements: SocialElement[], opts?: { history?: boolean }) {
    updateSelectedPost((p) => ({ ...p, elements: ensureUniqueElementIds(elements) }), {
      history: opts?.history !== false,
    });
  }

  function togglePlatform(key: PlatformKey) {
    setPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
    markDirty();
  }

  function selectPost(post: SocialPost) {
    setSelectedPostId(post.id);
    setFormatPreset(post.formatPreset);
    setSelectedElementId(null);
    setGenerationMeta(parseGenerationMetaFromDraft(post.generationMeta));
    // Picker selection follows the post; render uses post-scoped Asset ID hydration.
    // Do not hydrateMedia here — that wipes the shared resolved blob and races A→B→A.
    if (post.coverAssetId) {
      coverAsset.setCoverImage({
        asset_id: post.coverAssetId,
        url: null,
        alt: null,
        role: 'cover',
      });
    } else {
      coverAsset.clearCover();
    }
  }

  function handleFormatChange(key: FormatPresetKey) {
    setFormatPreset(key);
    const size = resolveFormatSize(key);
    updateSelectedPost((p) => ({
      ...p,
      formatPreset: key,
      width: size.w,
      height: size.h,
      elements: reflowElementsForFormat(p.elements, size.w, size.h),
    }));
  }

  function addPost() {
    const next = createPostFromPreset(formatPreset, posts.length + 1, {
      coverAssetId: selectedPost?.coverAssetId ?? null,
      linkedProjectId: docApi.constructionProjectId,
      cta: t('canvas.cta'),
    });
    setPosts((prev) => [...prev, next]);
    setSelectedPostId(next.id);
    setSelectedElementId(null);
    markDirty();
    showToast(t('toasts.postAdded'));
  }

  function confirmDeletePost() {
    const postId = deletePostId;
    if (!postId) return;
    setDeletePostId(null);
    setPostMenuId(null);

    const current = postsRef.current;
    const result = deleteSocialPost(current, postId, selectedPostIdRef.current);
    if (!result.deleted) return;

    // Invalidate in-flight AI / stale hydration so they cannot resurrect the deleted post.
    generateAbortRef.current += 1;
    generatingRef.current = false;
    if (createInflightIdRef.current === postId) createInflightIdRef.current = null;
    persistEpochRef.current += 1;
    deletedPostIdsRef.current = new Set(deletedPostIdsRef.current).add(postId);
    pushHistory();
    postsRef.current = result.posts;
    selectedPostIdRef.current = result.selectedPostId ?? '';
    setPosts(() => result.posts);
    setSelectedPostId(result.selectedPostId ?? '');
    setSelectedElementId(null);
    setEditingElementId(null);
    setFloatingMoreOpen(false);
    setAlignMenuOpen(false);
    setLayerMenuOpen(false);

    const nextActive =
      result.posts.find((p) => p.id === result.selectedPostId) ?? result.posts[0] ?? null;
    if (nextActive) {
      setFormatPreset(nextActive.formatPreset);
      setGenerationMeta(parseGenerationMetaFromDraft(nextActive.generationMeta));
      if (nextActive.coverAssetId) {
        coverAsset.setCoverImage({
          asset_id: nextActive.coverAssetId,
          url: null,
          alt: null,
          role: 'cover',
        });
      } else {
        coverAsset.clearCover();
      }
    } else {
      setGenerationMeta(null);
      coverAsset.clearCover();
    }

    // Shared asset cache is keyed by assetId — do not revoke URLs still used by remaining posts.
    markDirty();

    void (async () => {
      let ok = false;
      const persistPosts = result.posts.map((p) => ({
        ...p,
        thumbUrl: '',
        linkedProjectId: docApi.constructionProjectId,
      }));
      const coverFromPost = nextActive?.coverAssetId
        ? {
            asset_id: nextActive.coverAssetId,
            url: null as string | null,
            alt: null as string | null,
            role: 'cover' as const,
          }
        : null;
      for (let attempt = 0; attempt < 8 && !ok; attempt += 1) {
        ok = await docApi.saveDraft({
          ...buildPersistPayload(),
          coverImage: coverFromPost,
          posts: serializeSocialPosts(persistPosts),
          selectedPostId: result.selectedPostId,
        });
        if (!ok) {
          await new Promise((resolve) => {
            window.setTimeout(resolve, 80);
          });
        }
      }
      if (ok) {
        setSaved(true);
        showToast(t('toasts.postDeleted'));
      } else {
        showToast(t('toasts.saveFailed'));
      }
    })();
  }

  function addElement(el: SocialElement) {
    updateSelectedPost((p) => ({ ...p, elements: [...p.elements, el] }));
    setSelectedElementId(el.id);
    setRightRailId('content');
  }

  const runDownload = useCallback(async () => {
    if (!selectedPost) {
      showToast(t('toasts.downloadFailed'));
      return;
    }
    const hasCover = Boolean(artboardSrc && artboardState === 'ready');
    const hasElements = selectedPost.elements.length > 0;
    if (!hasCover && !hasElements) {
      showToast(t('toasts.downloadFailed'));
      return;
    }
    try {
      await exportSocialPostPng({
        width: contentSize.w,
        height: contentSize.h,
        coverImageUrl: hasCover ? artboardSrc : null,
        elements: selectedPost.elements,
        imageUrlsByAssetId: elementDisplayUrls,
        brandLogo,
        filename: `${selectedPost.name || 'social-post'}.png`,
      });
      showToast(t('toasts.downloaded'));
    } catch {
      showToast(t('toasts.downloadFailed'));
    }
  }, [
    artboardSrc,
    artboardState,
    brandLogo,
    contentSize.h,
    contentSize.w,
    elementDisplayUrls,
    selectedPost,
    t,
  ]);

  const transferCurrentPostToCanva = useCallback(async (): Promise<CanvaExportResult> => {
    if (!selectedPost) {
      throw new ApiError('canva_no_design', 400);
    }
    const hasCover = Boolean(artboardSrc && artboardState === 'ready');
    const hasElements = selectedPost.elements.length > 0;
    if (!hasCover && !hasElements) {
      throw new ApiError('canva_no_design', 400);
    }
    const exportInput = {
      width: contentSize.w,
      height: contentSize.h,
      coverImageUrl: hasCover ? artboardSrc : null,
      elements: selectedPost.elements,
      imageUrlsByAssetId: elementDisplayUrls,
      brandLogo,
      filename: `${selectedPost.name || 'social-post'}.png`,
    };
    const blob = await renderSocialPostPng(exportInput);
    const { layers, imagePlan } = buildCanvaLayersPayload(exportInput);
    const layerImages = await fetchCanvaLayerImages(imagePlan);
    return exportDesignToCanva({
      file: blob,
      filename: `${selectedPost.name || 'social-post'}.png`,
      title: selectedPost.name || 'Social post',
      width: contentSize.w,
      height: contentSize.h,
      linked_project_id: docApi.constructionProjectId,
      layers,
      layerImages,
    });
  }, [
    artboardSrc,
    artboardState,
    brandLogo,
    contentSize.h,
    contentSize.w,
    docApi.constructionProjectId,
    elementDisplayUrls,
    selectedPost,
  ]);

  const storeCanvaResult = useCallback((postId: string, result: CanvaExportResult) => {
    const src = canvaPreviewPngToObjectUrl(result.preview_png_base64);
    setCanvaPreviewByPostId((prev) => {
      const previous = prev[postId];
      if (previous?.src && previous.src !== src && previous.src.startsWith('blob:')) {
        URL.revokeObjectURL(previous.src);
      }
      return {
        ...prev,
        [postId]: {
          src: src || '',
          transferMode: result.transfer_mode === 'editable' ? 'editable' : 'png',
          editUrl: result.edit_url,
          designId: result.design_id ?? null,
        },
      };
    });
    return Boolean(src);
  }, []);

  const showCanvaError = useCallback(
    (err: unknown) => {
      const code = err instanceof ApiError ? err.message : '';
      if (code === 'canva_no_design') {
        showToast(t('toasts.canvaNoDesign'));
      } else if (code === 'canva_not_connected' || code === 'canva_token_refresh_failed') {
        showToast(t('toasts.canvaNotConnected'));
      } else {
        showToast(t('toasts.canvaFailed'));
      }
    },
    [t],
  );

  const runCanvaEngine = useCallback(async () => {
    if (canvaBusy) return;
    if (!selectedPost) {
      showToast(t('toasts.canvaNoDesign'));
      return;
    }
    setCanvaBusy(true);
    try {
      const result = await transferCurrentPostToCanva();
      const hydrated = storeCanvaResult(selectedPost.id, result);
      if (hydrated) {
        showToast(
          result.transfer_mode === 'editable'
            ? t('toasts.canvaReturnedEditable')
            : t('toasts.canvaReturned'),
        );
      } else {
        showToast(t('toasts.canvaPreviewUnavailable'));
      }
    } catch (err) {
      showCanvaError(err);
    } finally {
      setCanvaBusy(false);
    }
  }, [canvaBusy, selectedPost, showCanvaError, storeCanvaResult, t, transferCurrentPostToCanva]);

  const runOpenInCanva = useCallback(async () => {
    if (canvaBusy) return;
    if (!selectedPost) {
      showToast(t('toasts.canvaNoDesign'));
      return;
    }
    const existing = canvaPreviewByPostId[selectedPost.id];
    if (existing?.editUrl) {
      window.open(existing.editUrl, '_blank', 'noopener,noreferrer');
      showToast(
        existing.transferMode === 'editable'
          ? t('toasts.canvaOpenedEditable')
          : t('toasts.canvaOpened'),
      );
      return;
    }
    const tab = window.open('', '_blank');
    if (tab) {
      tab.opener = null;
    }
    setCanvaBusy(true);
    try {
      const result = await transferCurrentPostToCanva();
      storeCanvaResult(selectedPost.id, result);
      if (tab) {
        tab.location.replace(result.edit_url);
      } else {
        window.open(result.edit_url, '_blank', 'noopener,noreferrer');
      }
      showToast(
        result.transfer_mode === 'editable'
          ? t('toasts.canvaOpenedEditable')
          : t('toasts.canvaOpened'),
      );
    } catch (err) {
      tab?.close();
      showCanvaError(err);
    } finally {
      setCanvaBusy(false);
    }
  }, [
    canvaBusy,
    canvaPreviewByPostId,
    selectedPost,
    showCanvaError,
    storeCanvaResult,
    t,
    transferCurrentPostToCanva,
  ]);

  function handleFloating(action: FloatingActionKey | 'more') {
    if (action === 'more') {
      setFloatingMoreOpen(!floatingMoreOpen);
      setAlignMenuOpen(false);
      setLayerMenuOpen(false);
      return;
    }
    if (action === 'edit') {
      if (selectedPostId) clearCanvaRaster(selectedPostId);
      if (!selectedElementId) {
        const first = selectedPost?.elements[0];
        if (first) setSelectedElementId(first.id);
      }
      setRightRailId('content');
      return;
    }
    if (action === 'copy') {
      if (!selectedElement) {
        showToast(t('toasts.selectElement'));
        return;
      }
      const clone = duplicateElement(selectedElement, contentSize.w, contentSize.h);
      addElement(clone);
      showToast(t('floating.copy'));
      return;
    }
    if (action === 'delete') {
      if (selectedElement && selectedPost) {
        replaceElements(selectedPost.elements.filter((el) => el.id !== selectedElement.id));
        setSelectedElementId(null);
        markDirty();
        void persistNow();
        showToast(t('toasts.elementRemoved'));
        return;
      }
      // No element selected → clear cover background (existing Sil behavior).
      coverAsset.clearCover();
      updateSelectedPost((p) => ({ ...p, coverAssetId: null, thumbUrl: '' }));
      void (async () => {
        let ok = false;
        for (let attempt = 0; attempt < 8 && !ok; attempt += 1) {
          ok = await docApi.saveDraft({
            ...buildPersistPayload(),
            coverImage: null,
            posts: serializeSocialPosts(
              postsRef.current.map((p) =>
                p.id === selectedPostId
                  ? { ...p, coverAssetId: null, linkedProjectId: docApi.constructionProjectId }
                  : { ...p, linkedProjectId: docApi.constructionProjectId },
              ),
            ),
          });
          if (!ok) {
            await new Promise((resolve) => {
              window.setTimeout(resolve, 80);
            });
          }
        }
        if (ok) {
          setSaved(true);
          showToast(t('toasts.imageRemoved'));
        } else {
          showToast(t('toasts.saveFailed'));
        }
      })();
      return;
    }
    if (action === 'layer') {
      setLayerMenuOpen(!layerMenuOpen);
      setAlignMenuOpen(false);
      setFloatingMoreOpen(false);
      return;
    }
    if (action === 'align') {
      setAlignMenuOpen(!alignMenuOpen);
      setLayerMenuOpen(false);
      setFloatingMoreOpen(false);
      return;
    }
  }

  function handleBottomAction(action: BottomActionKey) {
    if (!P0_BOTTOM_ACTIONS.has(action)) return;
    if (action === 'addComponent') {
      setLeftRailId('components');
      return;
    }
    if (action === 'text') {
      addElement(createTextElement(contentSize.w, contentSize.h, 'custom'));
      return;
    }
    if (action === 'button') {
      addElement(createButtonElement(contentSize.w, contentSize.h));
      return;
    }
    if (action === 'image') {
      setElementImagePickerOpen(true);
      return;
    }
  }

  function handleApplyTemplate(format: FormatPresetKey) {
    handleFormatChange(format);
    showToast(t('toasts.templateApplied'));
  }

  function handleInsertComponent(key: string) {
    if (!P0_COMPONENT_KEYS.has(key)) return;
    if (key === 'title') {
      addElement(createTextElement(contentSize.w, contentSize.h, 'headline'));
      return;
    }
    if (key === 'text') {
      addElement(createTextElement(contentSize.w, contentSize.h, 'body'));
      return;
    }
    if (key === 'button' || key === 'cta') {
      addElement(createButtonElement(contentSize.w, contentSize.h));
      return;
    }
    if (key === 'image') {
      setElementImagePickerOpen(true);
    }
  }

  function scrollFilmstrip(dir: -1 | 1) {
    const el = filmstripRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 160, behavior: 'smooth' });
  }

  const persistIdeogramSession = useCallback(
    (session: IdeogramPocSession | null) => {
      ideogramSessionRef.current = session;
      setIdeogramSession(session);
      persistEpochRef.current += 1;
      void docApi.saveDraft({
        ...buildPersistPayload(),
        ideogramPoc: serializeIdeogramPocSession(session),
      });
    },
    [buildPersistPayload, docApi],
  );

  const runIdeogramGenerate = useCallback(
    async (instruction: string, options?: { regenerateVariant?: IdeogramPocVariant }) => {
      if (!docApi.constructionProjectId) {
        showToast(t('toasts.projectRequired'));
        return;
      }
      if (ideogramStatus && !ideogramStatus.available) {
        const message = t('toasts.ideogramUnavailable');
        setIdeogramError(message);
        showToast(message);
        return;
      }
      if (generatingRef.current) return;
      const token = ++generateAbortRef.current;
      generatingRef.current = true;
      persistEpochRef.current += 1;
      setIdeogramError(null);
      setGenerating(true);
      setCampaignStatus('draft');
      let stageIdx = 0;
      setAiStatus(IDEOGRAM_POC_STAGES[0]!);
      if (genStageTimerRef.current != null) {
        window.clearInterval(genStageTimerRef.current);
      }
      genStageTimerRef.current = window.setInterval(() => {
        stageIdx = Math.min(stageIdx + 1, IDEOGRAM_POC_STAGES.length - 1);
        if (token === generateAbortRef.current) {
          setAiStatus(IDEOGRAM_POC_STAGES[stageIdx]!);
        }
      }, 900);
      try {
        const previous = ideogramSessionRef.current;
        const response = await generateIdeogramDesign({
          linked_project_id: docApi.constructionProjectId,
          instruction,
          design_provider: 'ideogram',
          language: locale,
          draft: {
            posts: serializeSocialPosts(postsRef.current.filter((p) => !isInFlightGenerationPost(p))),
            selected_post_id: selectedPostIdRef.current,
          },
          session_id: options?.regenerateVariant ? previous?.sessionId ?? null : null,
          regenerate_variant: options?.regenerateVariant ?? null,
        });
        if (token !== generateAbortRef.current) return;
        const next = sessionFromIdeogramResponse(response, instruction, previous);
        persistIdeogramSession(next);
        setAiStatus('completed');
        setCampaignStatus('ready');
        showToast(t('toasts.designed'));
        genIdleTimerRef.current = window.setTimeout(() => {
          if (token === generateAbortRef.current) setAiStatus('idle');
        }, 1600);
      } catch (err) {
        if (token !== generateAbortRef.current) return;
        setAiStatus('idle');
        setCampaignStatus('failed');
        const message = generateErrorMessage(err, t('toasts.ideogramFailed'));
        setIdeogramError(message);
        showToast(message);
      } finally {
        if (genStageTimerRef.current != null) {
          window.clearInterval(genStageTimerRef.current);
          genStageTimerRef.current = null;
        }
        if (token === generateAbortRef.current) {
          generatingRef.current = false;
          setGenerating(false);
        }
      }
    },
    [docApi.constructionProjectId, ideogramStatus, locale, persistIdeogramSession, t],
  );

  const runGptImageGenerate = useCallback(
    async (instruction: string) => {
      if (!docApi.constructionProjectId) {
        showToast(t('toasts.projectRequired'));
        return;
      }
      if (gptImageStatus && !gptImageStatus.available) {
        const message = t('toasts.gptImageUnavailable');
        showToast(message);
        return;
      }
      if (generatingRef.current) return;
      designEngineRef.current = 'gpt-image';
      setDesignEngine('gpt-image');
      const siblingPosts = postsRef.current.filter((p) => !isInFlightGenerationPost(p));
      const createdPostId = mintCreatePostId();
      const token = ++generateAbortRef.current;
      generatingRef.current = true;
      persistEpochRef.current += 1;
      setGenerating(true);
      setCampaignStatus('draft');
      const inflight = createGeneratingPost(formatPreset, siblingPosts.length + 1, {
        linkedProjectId: docApi.constructionProjectId,
        id: createdPostId,
      });
      createInflightIdRef.current = inflight.id;
      const withInflight = [
        ...siblingPosts.map((p) =>
          isInFlightGenerationPost(p) ? { ...p, generationLifecycle: 'error' as const } : p,
        ),
        inflight,
      ];
      postsRef.current = withInflight;
      selectedPostIdRef.current = inflight.id;
      setPosts(withInflight);
      setSelectedPostId(inflight.id);
      setSelectedElementId(null);
      setEditingElementId(null);
      coverAsset.clearCover();
      let stageIdx = 0;
      setAiStatus(GPT_IMAGE_STAGES[0]!);
      if (genStageTimerRef.current != null) {
        window.clearInterval(genStageTimerRef.current);
      }
      genStageTimerRef.current = window.setInterval(() => {
        stageIdx = Math.min(stageIdx + 1, GPT_IMAGE_STAGES.length - 1);
        if (token === generateAbortRef.current) {
          setAiStatus(GPT_IMAGE_STAGES[stageIdx]!);
        }
      }, 900);
      try {
        const response = await generateGptImageDesign({
          linked_project_id: docApi.constructionProjectId,
          instruction,
          design_provider: 'gpt-image',
          campaign_mode: 'project',
          format_preset: formatPreset,
          aspect_ratio: formatPreset === 'portrait' ? '4:5' : formatPreset === 'square' ? '1:1' : undefined,
          language: locale,
          draft: {
            posts: serializeSocialPosts(siblingPosts),
            selected_post_id: selectedPostIdRef.current,
          },
          builder_context: {
            builder: 'social',
            format_preset: formatPreset,
          },
        });
        if (token !== generateAbortRef.current) return;
        const output = response.outputs[0];
        if (!output?.local_asset_id) {
          throw new Error(t('toasts.gptImageFailed'));
        }
        const headline =
          typeof response.brief?.visible_copy === 'object' && response.brief.visible_copy
            ? String((response.brief.visible_copy as Record<string, unknown>).headline || '')
            : '';
        const nextPost = createFlattenedGptImagePost({
          localAssetId: output.local_asset_id,
          linkedProjectId: docApi.constructionProjectId,
          formatPreset: asFormatPreset(response.format_preset || formatPreset),
          instruction,
          model: response.model,
          sessionId: response.session_id,
          campaignContextId: response.campaign_context_id,
          sourceAssetId: response.source_image?.asset_id ?? null,
          headline,
          index: siblingPosts.length + 1,
          canvasWidth: output.canvas_width,
          canvasHeight: output.canvas_height,
        });
        nextPost.id = createdPostId;
        const nextPosts = [...siblingPosts, nextPost];
        pushHistory();
        postsRef.current = nextPosts;
        selectedPostIdRef.current = nextPost.id;
        setPosts(nextPosts);
        setSelectedPostId(nextPost.id);
        setFormatPreset(nextPost.formatPreset);
        createInflightIdRef.current = null;
        coverAsset.setCoverImage({
          asset_id: output.local_asset_id,
          url: null,
          alt: null,
          role: 'cover',
        });
        markDirty();
        persistEpochRef.current += 1;
        void docApi.saveDraft({
          ...buildPersistPayload(),
          posts: serializeSocialPosts(nextPosts),
          selectedPostId: nextPost.id,
          designProvider: 'gpt-image',
        });
        setAiStatus('completed');
        setCampaignStatus('ready');
        setAiPrompt('');
        setPilotDesignChosen(true);
        showToast(t('toasts.designed'));
        genIdleTimerRef.current = window.setTimeout(() => {
          if (token === generateAbortRef.current) setAiStatus('idle');
        }, 1600);
      } catch (err) {
        if (token !== generateAbortRef.current) return;
        setAiStatus('idle');
        setCampaignStatus('failed');
        const inflightId = createInflightIdRef.current ?? createdPostId;
        if (inflightId) {
          const errored = postsRef.current.map((p) =>
            p.id === inflightId
              ? { ...p, generationLifecycle: 'error' as const, name: 'Generation failed' }
              : p,
          );
          postsRef.current = errored;
          setPosts(errored);
          selectedPostIdRef.current = inflightId;
          setSelectedPostId(inflightId);
        }
        showToast(generateErrorMessage(err, t('toasts.gptImageFailed')));
      } finally {
        if (genStageTimerRef.current != null) {
          window.clearInterval(genStageTimerRef.current);
          genStageTimerRef.current = null;
        }
        if (token === generateAbortRef.current) {
          generatingRef.current = false;
          setGenerating(false);
        }
      }
    },
    [
      coverAsset,
      docApi,
      formatPreset,
      gptImageStatus,
      locale,
      t,
    ],
  );

  const selectIdeogramOutput = useCallback(
    (variant: IdeogramPocVariant) => {
      const session = ideogramSessionRef.current;
      const output = session?.outputs.find((row) => row.variant === variant);
      if (!session || !output || !docApi.constructionProjectId) return;
      pushHistory();
      const nextPost = createFlattenedIdeogramPost({
        output,
        session,
        linkedProjectId: docApi.constructionProjectId,
        index: postsRef.current.length + 1,
      });
      const nextPosts = [...postsRef.current.filter((p) => !isInFlightGenerationPost(p)), nextPost];
      postsRef.current = nextPosts;
      selectedPostIdRef.current = nextPost.id;
      setPosts(nextPosts);
      setSelectedPostId(nextPost.id);
      setFormatPreset('square');
      coverAsset.setCoverImage({
        asset_id: output.localAssetId,
        url: null,
        alt: null,
        role: 'cover',
      });
      markDirty();
      persistEpochRef.current += 1;
      void docApi.saveDraft({
        ...buildPersistPayload(),
        posts: serializeSocialPosts(nextPosts),
        selectedPostId: nextPost.id,
        ideogramPoc: serializeIdeogramPocSession(session),
      });
      showToast(t('toasts.ideogramSelected'));
    },
    [buildPersistPayload, coverAsset, docApi, t],
  );

  const runAiGenerate = useCallback(
    async (instruction: string, options?: { mode?: SocialDesignMode; explicit?: boolean }) => {
      designEngineRef.current = 'native';
      setDesignEngine('native');
      // Always read latest canvas — sequential edits must not use a stale snapshot.
      const latestPosts = postsRef.current;
      const latestSelectedPostId = selectedPostIdRef.current;
      const inferredMode = inferDesignMode(instruction, latestPosts, options?.mode, {
        explicit: Boolean(options?.explicit),
      });
      const siblingPosts = latestPosts.filter((p) => !isInFlightGenerationPost(p));
      const createdPostId = inferredMode === 'create' ? mintCreatePostId() : null;
      const generationTargetPostId =
        inferredMode === 'create' ? createdPostId : latestSelectedPostId || null;
      const built = buildSocialDesignRequest({
        linkedProjectId: docApi.constructionProjectId,
        instruction,
        posts: siblingPosts,
        selectedPostId: generationTargetPostId,
        selectedElement: selectedElementToDesignContext(
          inferredMode === 'create'
            ? null
            : latestPosts
                .find((p) => p.id === latestSelectedPostId)
                ?.elements.find((el) => el.id === selectedElementIdRef.current) ?? null,
        ),
        coverImage: inferredMode === 'create' ? null : coverAsset.coverImage,
        galleryImages: inferredMode === 'create' ? [] : coverAsset.galleryImages,
        excludeAssetIds: postAssets.failedAssetIds,
        language: locale,
        platforms,
        mode: options?.mode ?? inferredMode,
        modeExplicit: Boolean(options?.explicit),
        designProvider: 'native',
        formatPreset,
      });

      if (!built.ok) {
        if (built.reason === 'missing_project') {
          showToast(t('toasts.projectRequired'));
        } else {
          showToast(t('toasts.instructionRequired'));
        }
        return;
      }

      if (genIdleTimerRef.current != null) {
        window.clearTimeout(genIdleTimerRef.current);
        genIdleTimerRef.current = null;
      }
      if (genStageTimerRef.current != null) {
        window.clearInterval(genStageTimerRef.current);
        genStageTimerRef.current = null;
      }

      const token = ++generateAbortRef.current;
      generatingRef.current = true;
      persistEpochRef.current += 1;
      setGenerating(true);
      setCampaignStatus('draft');
      if (inferredMode === 'create' && createdPostId) {
        const inflight = createGeneratingPost(formatPreset, siblingPosts.length + 1, {
          linkedProjectId: docApi.constructionProjectId,
          id: createdPostId,
        });
        createInflightIdRef.current = inflight.id;
        const withInflight = [
          ...siblingPosts.map((p) =>
            isInFlightGenerationPost(p)
              ? { ...p, generationLifecycle: 'error' as const }
              : p,
          ),
          inflight,
        ];
        postsRef.current = withInflight;
        selectedPostIdRef.current = inflight.id;
        setPosts(withInflight);
        setSelectedPostId(inflight.id);
        setSelectedElementId(null);
        setEditingElementId(null);
        coverAsset.clearCover();
        let stageIdx = 0;
        setAiStatus(GENERATION_STATUS_STAGES[0]!);
        genStageTimerRef.current = window.setInterval(() => {
          stageIdx = Math.min(stageIdx + 1, GENERATION_STATUS_STAGES.length - 1);
          if (token === generateAbortRef.current) {
            setAiStatus(GENERATION_STATUS_STAGES[stageIdx]!);
          }
        }, 900);
      } else {
        createInflightIdRef.current = null;
        setAiStatus('designingCreatives');
      }

      try {
        const response = await generateSocialDesign(built.request);
        if (token !== generateAbortRef.current) return;

        const meta = toDesignGenerationMeta(response);
        setGenerationMeta(meta);
        const artSession = mergeArtDirectorSessionFromResponse(
          artDirectorSessionRef.current,
          response,
          instruction,
        );
        artDirectorSessionRef.current = artSession;
        setArtDirectorSession(artSession);
        if (inferredMode === 'create') {
          setPilotDesignChosen(!(artSession && artSession.variants.length > 1));
        }

        const applied = applyDesignResponseToPosts(
          response,
          docApi.constructionProjectId,
        );
        const blocked =
          Boolean(meta.warnings.includes('missing_required_facts')) && !(response.ops?.length);
        const inflightId = createInflightIdRef.current ?? createdPostId;
        const merged =
          inferredMode === 'create'
            ? mergeCreateGenerationResult({
                localPosts: postsRef.current,
                appliedPosts: applied.posts,
                inflightId,
                appliedSelectedPostId: applied.selectedPostId,
                deletedIds: deletedPostIdsRef.current,
              })
            : {
                posts: applied.posts,
                selectedPostId: applied.selectedPostId,
                generated:
                  applied.posts.find((p) => p.id === applied.selectedPostId) ??
                  applied.posts[0] ??
                  null,
              };

        if (
          process.env.NODE_ENV !== 'production' &&
          inferredMode === 'create' &&
          createdPostId &&
          merged.generated &&
          (merged.generated.id !== createdPostId || merged.selectedPostId !== createdPostId)
        ) {
          console.error('SMB CREATE postId mismatch', {
            createdPostId,
            generationTargetPostId,
            patchedPostId: merged.generated.id,
            selectedPostId: merged.selectedPostId,
          });
        }

        const nextPosts = merged.posts.map((p) => {
          const unique = {
            ...p,
            elements: ensureUniqueElementIds(p.elements),
            linkedProjectId: p.linkedProjectId || docApi.constructionProjectId,
          };
          if (inferredMode === 'create' && merged.generated && unique.id === merged.generated.id) {
            return stampDesignResponseOnPost(unique, meta);
          }
          return unique;
        });
        const generated = merged.generated
          ? nextPosts.find((p) => p.id === merged.generated?.id) ?? merged.generated
          : null;
        const patchedPostId = generated?.id ?? merged.selectedPostId ?? createdPostId ?? null;
        const createComplete =
          inferredMode !== 'create' || Boolean(generated && hasAppliedCreateResult(generated));

        if (nextPosts.length && !blocked && (inferredMode !== 'create' || createComplete)) {
          pushHistory();
          persistEpochRef.current += 1;
          const selectId = (inferredMode === 'create' ? createdPostId : null) ?? patchedPostId ?? '';
          postsRef.current = nextPosts;
          selectedPostIdRef.current = selectId;
          setPosts(nextPosts);
          if (selectId) setSelectedPostId(selectId);
          createInflightIdRef.current = null;
          setEditingElementId(null);
          const active = nextPosts.find((p) => p.id === selectId) ?? nextPosts[0];
          if (active) setFormatPreset(active.formatPreset);
          if (active?.coverAssetId) {
            coverAsset.setCoverImage({
              asset_id: active.coverAssetId,
              url: null,
              alt: null,
              role: 'cover',
            });
          } else {
            coverAsset.clearCover();
          }
          markDirty();
          setRightRailId('content');
        } else if (inferredMode === 'create' && inflightId) {
          persistEpochRef.current += 1;
          const errored = postsRef.current.map((p) =>
            p.id === inflightId ? { ...p, generationLifecycle: 'error' as const, name: 'Generation failed' } : p,
          );
          postsRef.current = errored;
          setPosts(errored);
          selectedPostIdRef.current = inflightId;
          setSelectedPostId(inflightId);
          createInflightIdRef.current = inflightId;
        }

        if (hasDesignInsufficientContext(response)) {
          showToast(t('toasts.insufficientContext'));
        } else if (meta.warnings.includes('missing_required_facts')) {
          const missingLabels = (meta.missing_facts ?? [])
            .filter((f) => f && typeof f === 'object' && f.required)
            .map((f) => String(f.label || f.key || ''))
            .filter(Boolean);
          showToast(
            t('toasts.missingRequiredFacts', {
              facts: missingLabels.join(', ') || 'required fact',
            }),
          );
        } else if (meta.warnings.includes('no_valid_project_media')) {
          showToast(t('toasts.noProjectMedia'));
        } else if (inferredMode === 'create' && !createComplete && !blocked) {
          showToast(t('toasts.generateFailed'));
          setCampaignStatus('failed');
        } else if (meta.warnings.length) {
          showToast(t('toasts.generationWarning', { warning: meta.warnings[0]! }));
        } else {
          showToast(t('toasts.designed'));
        }

        if (!(inferredMode === 'create' && !createComplete && !blocked)) {
          setAiStatus('completed');
          setCampaignStatus(blocked ? 'failed' : 'ready');
          setAiPrompt('');
        } else {
          setAiStatus('idle');
        }
        const persistSource =
          createComplete || inferredMode !== 'create' ? nextPosts : postsRef.current;
        const persistPosts = stripInFlightPostsForPersist(
          persistSource.map((p) => ({
            ...p,
            linkedProjectId: docApi.constructionProjectId,
          })),
        );
        const persistSelected =
          persistPosts.find((p) => p.id === (patchedPostId ?? merged.selectedPostId ?? ''))?.id ??
          persistPosts[0]?.id ??
          null;
        const persistPayload = {
          ...buildPersistPayload(),
          generationMeta: serializeGenerationMetaForDraft(meta),
          posts: serializeSocialPosts(persistPosts),
          selectedPostId: persistSelected,
        };
        if (createComplete || inferredMode !== 'create') {
          persistEpochRef.current += 1;
          void docApi.saveDraft(persistPayload);
        }
        genIdleTimerRef.current = window.setTimeout(() => {
          if (token === generateAbortRef.current) setAiStatus('idle');
        }, 1600);
      } catch (err) {
        if (token !== generateAbortRef.current) return;
        setAiStatus('idle');
        setCampaignStatus('failed');
        const inflightId = createInflightIdRef.current ?? createdPostId;
        if (inflightId) {
          const errored = postsRef.current.map((p) =>
            p.id === inflightId ? { ...p, generationLifecycle: 'error' as const, name: 'Generation failed' } : p,
          );
          postsRef.current = errored;
          setPosts(errored);
          selectedPostIdRef.current = inflightId;
          setSelectedPostId(inflightId);
        }
        showToast(generateErrorMessage(err, t('toasts.generateFailed')));
      } finally {
        if (genStageTimerRef.current != null) {
          window.clearInterval(genStageTimerRef.current);
          genStageTimerRef.current = null;
        }
        if (token === generateAbortRef.current) {
          generatingRef.current = false;
          setGenerating(false);
        }
      }
    },
    [
      buildPersistPayload,
      coverAsset,
      docApi,
      formatPreset,
      locale,
      platforms,
      postAssets.failedAssetIds,
      t,
      setDesignEngine,
    ],
  );

  const leftDrawerContent = (
    <SmbLeftRailDrawer
      id={leftRailId}
      onInsertComponent={handleInsertComponent}
      onApplyTemplate={handleApplyTemplate}
      onToast={showToast}
      onOpenMediaPicker={() => coverAsset.openPicker('cover')}
      enabledComponentKeys={P0_COMPONENT_KEYS}
      onGenerate={(instruction) => {
        const mode = inferDesignMode(instruction, postsRef.current);
        if (mode === 'edit') {
          void runAiGenerate(instruction, { mode: 'edit', explicit: true });
          return;
        }
        void runGptImageGenerate(instruction);
      }}
      generating={generating}
    />
  );

  const rightDrawerContent = (
    <SmbRightRailDrawer
      id={rightRailId}
      onSelectTab={setRightRailId}
      post={selectedPost}
      patchPost={patchPost}
      selectedElement={selectedElement}
      patchElement={(patch) => {
        if (!selectedElementId) return;
        patchElement(selectedElementId, patch);
      }}
      formatPreset={formatPreset}
      setFormatPreset={handleFormatChange}
      platforms={platforms}
      togglePlatform={togglePlatform}
      brandLogo={brandLogo}
      setBrandLogo={(v) => {
        setBrandLogo(v);
        markDirty();
      }}
      bgMode={bgMode}
      setBgMode={setBgMode}
      markDirty={markDirty}
      onToast={showToast}
      onChangeImage={() => coverAsset.openPicker('cover')}
      coverDisplayUrl={displayArtboardSrc ?? ''}
      onDownload={() => {
        void runDownload();
      }}
      onOpenInCanva={() => {
        void runOpenInCanva();
      }}
      canvaBusy={canvaBusy}
    />
  );

  const leftDrawer =
    focus.isFocus || focus.isFullscreen ? (
      leftDrawerContent
    ) : (
      <div className="smb-ws__panel smb-ws__left" aria-label={t('left.aria')} data-testid="smb-left">
        <SmbLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as SmbLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="smb-ws__panel smb-ws__right" aria-label={t('right.aria')} data-testid="smb-right">
        <SmbLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as SmbRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (hydration.phase !== 'ready') {
    return (
      <CsBuilderBootstrapView
        testId="smb-workspace-loading"
        workspaceClassName="smb-ws"
        homeHref={SMB_HOME}
        title={tTools('socialStudio.title')}
        studioLabel={t('creativeStudio')}
        phase={hydration.phase}
        loadingLabel={tBootstrap('loading')}
        errorTitle={tBootstrap('loadErrorTitle')}
        errorMessage={hydration.error || tBootstrap('loadError')}
        retryLabel={tCommon('retry')}
        onRetry={hydration.retry}
      />
    );
  }

  function selectArtDirectorVariant(variant: ArtDirectorVariantKey) {
    const session = artDirectorSessionRef.current;
    const option = session?.variants.find((row) => row.key === variant);
    if (!session || !option?.post) return;
    const targetId = selectedPostIdRef.current;
    const nextPosts = applyArtDirectorVariantToPosts(postsRef.current, targetId, option).map((p) => ({
      ...p,
      elements: ensureUniqueElementIds(p.elements),
    }));
    const nextSession = { ...session, selectedVariant: variant };
    artDirectorSessionRef.current = nextSession;
    setArtDirectorSession(nextSession);
    setGenerationMeta((prev) => {
      if (!prev) return prev;
      const plan = {
        ...(prev.creative_plan && typeof prev.creative_plan === 'object' ? prev.creative_plan : {}),
        composition: option.composition,
        creative_direction: option.creativeDirection,
        intent: option.campaignType,
      };
      return {
        ...prev,
        creative_plan: plan,
        composition_blueprint:
          option.post?.compositionBlueprint
          ?? prev.composition_blueprint,
      };
    });
    pushHistory();
    persistEpochRef.current += 1;
    postsRef.current = nextPosts;
    setPosts(nextPosts);
    const active = nextPosts.find((p) => p.id === targetId) ?? nextPosts[0];
    if (active?.coverAssetId) {
      coverAsset.setCoverImage({
        asset_id: active.coverAssetId,
        url: null,
        alt: null,
        role: 'cover',
      });
    }
    markDirty();
    setPilotDesignChosen(true);
    showToast(t('toasts.artDirectorSelected', { variant }));
  }

  function selectDesignEngine(next: DesignEngineKind) {
    designEngineRef.current = next;
    setDesignEngine(next);
    if (next !== 'ideogram') setIdeogramError(null);
    persistEpochRef.current += 1;
    void docApi.saveDraft({
      ...buildPersistPayload(),
      designProvider: next,
    });
  }

  function applyLocalFollowUp(instruction: string): boolean {
    const current = selectedPost;
    if (!current) return false;
    const result = applyAiFollowUpEdit(
      current,
      instruction,
      coverAsset.media.items.map((item) => ({
        id: item.id,
        name: item.name,
        tags: item.tags,
        folderCategory: item.folderCategory,
      })),
    );
    if (!result.ok) {
      if (result.reason === 'unrecognized') return false;
      const toastKey =
        result.reason === 'no_headline'
          ? 'toasts.aiEditNoHeadline'
          : result.reason === 'no_price'
            ? 'toasts.aiEditNoPrice'
            : result.reason === 'no_night_asset'
              ? 'toasts.aiEditNoNight'
              : result.reason === 'no_logo'
                ? 'toasts.aiEditNoLogo'
                : 'toasts.aiEditNoText';
      showToast(t(toastKey));
      return true;
    }
    pushHistory();
    if (selectedPostId) clearCanvaRaster(selectedPostId);
    const nextPosts = postsRef.current.map((p) => (p.id === result.post.id ? result.post : p));
    postsRef.current = nextPosts;
    setPosts(nextPosts);
    if (result.post.coverAssetId) {
      coverAsset.setCoverImage({
        asset_id: result.post.coverAssetId,
        url: null,
        alt: null,
        role: 'cover',
      });
    }
    markDirty();
    setAiPrompt('');
    showToast(t('toasts.aiEditApplied'));
    return true;
  }

  function submitAiDesign() {
    const instruction = aiPrompt.trim();
    if (!instruction) {
      showToast(t('toasts.instructionRequired'));
      return;
    }
    const canFollowUp = Boolean(selectedPost && (pilotDesignChosen || artDirectorSession));
    if (canFollowUp) {
      if (applyLocalFollowUp(instruction)) return;
      void runAiGenerate(instruction, { mode: 'edit', explicit: true });
      return;
    }
    void runGptImageGenerate(instruction);
  }

  function regenerateCurrentDesign() {
    const instruction = (artDirectorSessionRef.current?.instruction || aiPrompt).trim();
    if (!instruction) {
      showToast(t('output.variationNeedDesign'));
      return;
    }
    designEngineRef.current = 'native';
    void runAiGenerate(instruction, { mode: 'create', explicit: true });
  }

  function ensureCanvasElementSelected() {
    if (selectedElementId) return true;
    const first = selectedPost?.elements.find((el) => el.type !== 'IMAGE' || el.role === 'logo')
      ?? selectedPost?.elements[0];
    if (!first) {
      showToast(t('toasts.selectElement'));
      return false;
    }
    setSelectedElementId(first.id);
    return true;
  }

  const showVariantChooser =
    Boolean(artDirectorSession && artDirectorSession.variants.length > 0 && !pilotDesignChosen);

  const aiDesignCommand = (
    <div
      className={[
        'smb-ws__ai-design',
        'smb-ws__ai-design--pilot',
        focus.isFullscreen ? 'smb-ws__ai-design--fs' : '',
        aiDesignCollapsed && focus.isFullscreen ? 'is-collapsed' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      data-testid="smb-ai-design-command"
      data-fs-ai={focus.isFullscreen ? 'true' : 'false'}
    >
      <div className="smb-ws__ai-design-head">
        <span className="smb-ws__ai-design-label" id="smb-ai-design-heading">
          {t('aiDesign.title')}
        </span>
        {focus.isFullscreen ? (
          <button
            type="button"
            className="smb-ws__ai-design-toggle"
            data-testid="smb-ai-design-toggle"
            aria-expanded={!aiDesignCollapsed}
            onClick={() => setAiDesignCollapsed((v) => !v)}
          >
            {aiDesignCollapsed ? t('aiDesign.expand') : t('aiDesign.collapse')}
          </button>
        ) : null}
      </div>
      {!aiDesignCollapsed || !focus.isFullscreen ? (
        <>
          <div className="smb-ws__ai-design-row">
            <TextArea
              id="smb-ai-design-input"
              className="smb-ws__ai-design-input smb-ws__ai-design-textarea"
              rows={3}
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder={
                pilotDesignChosen || artDirectorSession
                  ? t('aiDesign.followUpPlaceholder')
                  : t('aiDesign.placeholder')
              }
              data-testid="smb-ai-design-input"
              disabled={generating}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  submitAiDesign();
                }
              }}
            />
          </div>
          <div className="smb-ws__ai-design-actions">
            <Button
              variant="primary"
              size="sm"
              data-testid="smb-ai-design-submit"
              data-ai-workflow={pilotDesignChosen ? 'edit' : 'create'}
              disabled={generating}
              onClick={() => submitAiDesign()}
            >
              <IhIcon name="sparkles" size={12} />
              {generating ? t('aiDesign.generating') : t('aiDesign.submit')}
            </Button>
          </div>
          {artDirectorSession?.selectedAsset ? (
            <span
              className="smb-ws__sr-only"
              data-testid="smb-art-director-selected-asset"
              data-asset-id={artDirectorSession.selectedAsset.assetId}
              data-asset-filename={artDirectorSession.selectedAsset.filename}
              data-asset-category={artDirectorSession.selectedAsset.category ?? ''}
              data-asset-subject={artDirectorSession.selectedAsset.visualSubject ?? ''}
              data-asset-source={artDirectorSession.selectedAsset.source ?? ''}
            />
          ) : null}
          {showVariantChooser ? (
            <div className="smb-ws__art-director" data-testid="smb-art-director-results">
              <p className="smb-ws__art-director-title">{t('aiDesign.resultsTitle')}</p>
              <div className="smb-ws__art-director-grid">
                {artDirectorSession!.variants.map((output) => {
                  const thumbId = output.post?.coverAssetId;
                  const thumbSrc = thumbId
                    ? elementDisplayUrls[thumbId] || coverAsset.media.getCachedDisplayUrl(thumbId)
                    : null;
                  return (
                    <div
                      key={output.key}
                      className={`smb-ws__art-director-card${artDirectorSession!.selectedVariant === output.key ? ' is-active' : ''}`}
                      data-testid={`smb-art-director-option-${output.key}`}
                    >
                      {thumbSrc ? (
                        <img className="smb-ws__art-director-card-img" src={thumbSrc} alt="" />
                      ) : (
                        <span className="smb-ws__art-director-card-ph" aria-hidden="true" />
                      )}
                      <div className="smb-ws__art-director-card-label">
                        {t('aiDesign.designLabel', { letter: output.key })}
                      </div>
                      <div className="smb-ws__art-director-card-actions">
                        <Button
                          variant={artDirectorSession!.selectedVariant === output.key ? 'primary' : 'secondary'}
                          size="sm"
                          data-testid={`smb-art-director-select-${output.key}`}
                          disabled={generating}
                          onClick={() => selectArtDirectorVariant(output.key)}
                        >
                          {t('aiDesign.select')}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          data-testid={`smb-art-director-regen-${output.key}`}
                          disabled={generating}
                          onClick={() => regenerateCurrentDesign()}
                        >
                          {t('aiDesign.regenerate')}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );

  const previewMode = focus.mode === 'preview';

  return (
    <main className="dashboard" data-testid="smb-workspace-page">
      <div
        className="smb-ws"
        data-testid="smb-workspace"
        data-design-engine={designEngine}
        data-design-provider={designEngine}
        data-art-director={designEngine === 'native' ? 'true' : undefined}
        data-selected-variant={artDirectorSession?.selectedVariant}
        data-campaign-type={artDirectorSession?.campaignType || undefined}
        data-selected-asset-id={artDirectorSession?.selectedAsset?.assetId || undefined}
        data-selected-asset-filename={artDirectorSession?.selectedAsset?.filename || undefined}
        data-provenance-source={artDirectorSession?.provenance?.source || undefined}
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
        data-generation-grounded={
          generationMeta == null ? undefined : generationMeta.grounded ? 'true' : 'false'
        }
        data-generation-citations={
          generationMeta == null ? undefined : String(generationMeta.citations.length)
        }
        data-generation-warnings={
          generationMeta == null ? undefined : generationMeta.warnings.join(',')
        }
        data-creative-intent={
          typeof generationMeta?.creative_plan?.intent === 'string'
            ? generationMeta.creative_plan.intent
            : undefined
        }
        data-creative-direction={
          typeof generationMeta?.creative_plan?.creative_direction === 'string'
            ? generationMeta.creative_plan.creative_direction
            : undefined
        }
        data-creative-composition={
          typeof generationMeta?.creative_plan?.composition === 'string'
            ? generationMeta.creative_plan.composition
            : undefined
        }
        data-composition-family={
          typeof generationMeta?.composition_blueprint?.composition_family === 'string'
            ? generationMeta.composition_blueprint.composition_family
            : typeof selectedPost?.compositionFamily === 'string'
              ? selectedPost.compositionFamily
              : undefined
        }
        data-headline-region={
          typeof generationMeta?.composition_blueprint?.headline_region_kind === 'string'
            ? generationMeta.composition_blueprint.headline_region_kind
            : undefined
        }
        data-metric-region={
          typeof generationMeta?.composition_blueprint?.metric_region_kind === 'string'
            ? generationMeta.composition_blueprint.metric_region_kind
            : undefined
        }
        data-cta-placement={
          typeof generationMeta?.composition_blueprint?.cta_placement === 'string'
            ? generationMeta.composition_blueprint.cta_placement
            : undefined
        }
        data-creative-density={
          typeof generationMeta?.creative_plan?.copy_density === 'string'
            ? generationMeta.creative_plan.copy_density
            : undefined
        }
        data-creative-contrast={
          typeof generationMeta?.creative_plan?.contrast_strategy === 'string'
            ? generationMeta.creative_plan.contrast_strategy
            : undefined
        }
        data-creative-cta={
          typeof generationMeta?.creative_plan?.cta_strategy === 'string'
            ? generationMeta.creative_plan.cta_strategy
            : undefined
        }
        data-creative-quality={
          typeof generationMeta?.design_quality?.total === 'number'
            ? String(generationMeta.design_quality.total)
            : undefined
        }
      >
        <header className="smb-ws__header cs-page-header">
          <div className="smb-ws__header-copy cs-page-header__copy">
            <Link href={SMB_HOME as Route} className="smb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="smb-ws__breadcrumb">
                <li>
                  <Link href={SMB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="smb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="smb-ws__breadcrumb-current" aria-current="page">
                  {tTools('socialStudio.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="activity" size={20} />
              {tTools('socialStudio.title')}
            </h1>
            <p className="smb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="smb-ws__header-actions cs-page-header__actions">
            <div className="smb-ws__save-status" data-testid="smb-save-status">
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <StatusChip tone={CAMPAIGN_STATUS_TONE[campaignStatus]}>
                {t(`status.${campaignStatus}`)}
              </StatusChip>
              <span className="smb-ws__saved-ago">{saved ? t('savedAgo') : t('notSavedYet')}</span>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void persistNow(true)}
              data-testid="smb-save"
              disabled={docApi.saveStatus === 'saving' || docApi.loadStatus !== 'ready'}
            >
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="smb-preview"
              onClick={() => {
                focus.setMode('preview');
                setSelectedElementId(null);
              }}
            >
              {t('preview')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="smb-send-test"
              disabled
              title={t('toasts.notAvailable')}
            >
              {t('sendTest')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="smb-download-header"
              onClick={() => {
                void runDownload();
              }}
            >
              <IhIcon name="inbox" size={12} />
              {t('download')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="smb-publish"
              disabled
              title={t('publishUnavailable')}
            >
              {t('publish')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
          </div>
        </header>

        <div className="smb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="smb-ws__toolbar-left">
            <div className="smb-ws__project">
              <Select
                id="smb-project"
                label={t('fields.project')}
                value={docApi.constructionProjectId ?? ''}
                onChange={(e) => {
                  void handleProjectChange(e.target.value);
                }}
              >
                {docApi.constructionProjects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.project_name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="smb-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="smb-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="smb-undo"
                disabled={!historyPast.length}
                onClick={() => undoHistory()}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="smb-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="smb-redo"
                disabled={!historyFuture.length}
                onClick={() => redoHistory()}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
            </div>
          </div>
          <div className="smb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <SmbZoomToolbar
              engine={ftv}
              canvasLocked={canvasLocked}
              onToggleLock={() => setCanvasLocked((v) => !v)}
              isFullscreen={focus.isFullscreen}
              onToggleFullscreen={focus.toggleFullscreen}
            />
          </div>
        </div>

        <div
          className={`smb-ws__ai-status${aiStatus !== 'idle' ? ' is-live' : ''}`}
          role="status"
          aria-live="polite"
          data-testid="smb-info-banner"
        >
          <span className="smb-ws__ai-status-dot" aria-hidden="true" />
          <span>{aiStatus === 'idle' ? t('aiStatus.idle') : t(`aiStatus.${aiStatus}`)}</span>
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="smb-ws__layout"
          leftRail={smbLeftRail}
          rightRail={smbRightRail}
          onLeftRailSelect={(id) => {
            if ((SMB_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as SmbLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((SMB_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as SmbRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section
              className="smb-ws__panel smb-ws__center"
              aria-label={t('canvas.aria')}
              data-testid="smb-center"
            >
              {aiDesignCommand}
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="smb-canvas-stage"
                toolbar={
                  <div className="smb-ws__center-head">
                    {pilotDesignChosen ? (
                      <div
                        className="smb-ws__output-actions"
                        role="group"
                        aria-label={t('canvas.formatsAria')}
                        data-testid="smb-pilot-output"
                      >
                        <Button
                          variant="secondary"
                          size="sm"
                          data-testid="smb-output-story"
                          onClick={() => handleFormatChange('story')}
                        >
                          {t('output.story')}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          data-testid="smb-output-reel"
                          onClick={() => handleFormatChange('reelsCover')}
                        >
                          {t('output.reel')}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          data-testid="smb-output-variation"
                          disabled={generating}
                          onClick={() => regenerateCurrentDesign()}
                        >
                          {t('output.variation')}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          data-testid="smb-output-download"
                          onClick={() => {
                            void runDownload();
                          }}
                        >
                          {t('download')}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          data-testid="smb-output-publish"
                          disabled
                          title={t('output.publishUnavailable')}
                        >
                          {t('publish')}
                        </Button>
                      </div>
                    ) : (
                      <div
                        className="smb-ws__format-tabs"
                        role="group"
                        aria-label={t('canvas.formatsAria')}
                      >
                        {FORMAT_PRESETS.map((f) => (
                          <button
                            key={f.key}
                            type="button"
                            className={`smb-ws__format-tab${formatPreset === f.key ? ' is-active' : ''}`}
                            aria-pressed={formatPreset === f.key}
                            data-testid={`smb-format-${f.key}`}
                            onClick={() => handleFormatChange(f.key)}
                          >
                            {t(`formats.${f.key}`)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                }
                tray={{
                  label: t('canvas.stripTitle'),
                  count: posts.length,
                  testId: 'smb-post-strip',
                  handleTestId: 'smb-tray-handle',
                  content: (
                    <div className="smb-ws__filmstrip" data-testid="smb-filmstrip">
                      <button
                        type="button"
                        className="smb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripPrev')}
                        data-testid="smb-filmstrip-prev"
                        onClick={() => scrollFilmstrip(-1)}
                      >
                        <IhIcon name="chevronLeft" size={14} />
                      </button>
                      <div className="smb-ws__page-row" ref={filmstripRef} data-testid="smb-post-row">
                        {posts.map((post) => (
                          <div
                            key={post.id}
                            className={`smb-ws__page-card${selectedPostId === post.id ? ' is-selected' : ''}${postMenuId === post.id ? ' is-menu-open' : ''}`}
                            data-testid={`smb-post-card-${post.id}`}
                          >
                            <button
                              type="button"
                              className="smb-ws__page-card-hit"
                              onClick={() => selectPost(post)}
                            >
                              <div
                                className={`smb-ws__page-thumb ${aspectThumbClass(post.formatPreset)}`}
                              >
                                {canvaPreviewByPostId[post.id]?.src ? (
                                  <img src={canvaPreviewByPostId[post.id]?.src} alt="" />
                                ) : post.coverAssetId && elementDisplayUrls[post.coverAssetId] ? (
                                  <img src={elementDisplayUrls[post.coverAssetId]} alt="" />
                                ) : selectedPostId === post.id && displayArtboardSrc ? (
                                  <img src={displayArtboardSrc} alt="" />
                                ) : (
                                  <span className="smb-ws__page-thumb-empty" aria-hidden="true" />
                                )}
                              </div>
                              <strong>{post.name}</strong>
                              <span className="smb-ws__page-format">
                                {post.formatPreset === 'portrait'
                                  ? '4:5'
                                  : post.formatPreset === 'landscape'
                                    ? '16:9'
                                    : post.formatPreset === 'story' || post.formatPreset === 'reelsCover'
                                      ? '9:16'
                                      : '1:1'}
                              </span>
                            </button>
                            <SmbPostCardMore
                              postId={post.id}
                              open={postMenuId === post.id}
                              onOpenChange={(open) => setPostMenuId(open ? post.id : null)}
                              ariaLabel={t('canvas.postMore')}
                              items={[
                                {
                                  key: 'delete',
                                  label: t('floating.delete'),
                                  destructive: true,
                                  testId: `smb-post-delete-${post.id}`,
                                  onSelect: () => setDeletePostId(post.id),
                                },
                              ]}
                            />
                          </div>
                        ))}
                        <button
                          type="button"
                          className="smb-ws__page-card smb-ws__page-card--new"
                          data-testid="smb-new-post"
                          onClick={addPost}
                        >
                          <div className="smb-ws__page-thumb smb-ws__page-thumb--new">
                            <IhIcon name="plus" size={18} />
                          </div>
                          <strong>{t('canvas.newPost')}</strong>
                        </button>
                      </div>
                      <button
                        type="button"
                        className="smb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripNext')}
                        data-testid="smb-filmstrip-next"
                        onClick={() => scrollFilmstrip(1)}
                      >
                        <IhIcon name="chevronRight" size={14} />
                      </button>
                    </div>
                  ),
                }}
                dock={{
                  testId: 'smb-scene-actions',
                  className: 'smb-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="smb-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      moreLabel={t('editor.more')}
                      maxVisible={5}
                      primary={{
                        label: t('editor.text'),
                        icon: 'documents',
                        onClick: () => handleBottomAction('text'),
                        testId: 'smb-action-text',
                      }}
                      actions={[
                        {
                          key: 'changeImage',
                          icon: 'inventory',
                          label: t('editor.changeImage'),
                          onClick: () => coverAsset.openPicker('cover'),
                          testId: 'smb-action-change-image',
                          priority: 'high',
                        },
                        {
                          key: 'logo',
                          icon: 'theme',
                          label: t('editor.logo'),
                          onClick: () => {
                            setBrandLogo((v) => !v);
                            markDirty();
                            showToast(brandLogo ? t('toasts.logoRemoved') : t('toasts.logoChanged'));
                          },
                          testId: 'smb-action-logo',
                          priority: 'high',
                        },
                        {
                          key: 'move',
                          icon: 'target',
                          label: t('editor.move'),
                          onClick: () => {
                            if (ensureCanvasElementSelected()) showToast(t('editor.moveHint'));
                          },
                          testId: 'smb-action-move',
                          priority: 'high',
                        },
                        {
                          key: 'resize',
                          icon: 'design',
                          label: t('editor.resize'),
                          onClick: () => {
                            if (ensureCanvasElementSelected()) showToast(t('editor.resizeHint'));
                          },
                          testId: 'smb-action-resize',
                          priority: 'high',
                        },
                        {
                          key: 'undo',
                          icon: 'refresh',
                          label: t('editor.undo'),
                          onClick: () => undoHistory(),
                          testId: 'smb-action-undo',
                          disabled: !historyPast.length,
                          priority: 'high',
                        },
                        {
                          key: 'addComponent',
                          icon: 'plus',
                          label: t('bottomBar.actions.addComponent'),
                          onClick: () => handleBottomAction('addComponent'),
                          testId: 'smb-action-addComponent',
                          priority: 'low',
                        },
                        ...BOTTOM_ACTIONS.filter(
                          (a) => a.key !== 'addComponent' && a.key !== 'text',
                        ).map((action) => ({
                          key: action.key,
                          icon: action.icon,
                          label: t(`bottomBar.actions.${action.key}`),
                          onClick: () => handleBottomAction(action.key),
                          testId: `smb-action-${action.key}`,
                          disabled: !P0_BOTTOM_ACTIONS.has(action.key),
                          priority: 'low' as const,
                        })),
                        {
                          key: 'openInCanva',
                          icon: 'inbox' as const,
                          label: t('openInCanva'),
                          onClick: () => {
                            void runOpenInCanva();
                          },
                          testId: 'smb-open-in-canva',
                          disabled: canvaBusy,
                          priority: 'low' as const,
                        },
                      ]}
                    />
                  ),
                }}
              >
                <div className="smb-ws__canvas-stage" data-testid="smb-preview-shell">
                  <FocusFitStage engine={ftv} artboardTestId="smb-ftv-artboard">
                    <div
                      className={`smb-ws__artboard${selectedElementId || displayArtboardState === 'ready' ? ' is-selected' : ''}${displayArtboardState !== 'ready' ? ' is-empty' : ''}`}
                      data-testid="smb-artboard"
                      data-image-state={displayArtboardState}
                      data-canva-preview={canvaPreview?.src ? 'true' : 'false'}
                      data-generation-lifecycle={selectedPost?.generationLifecycle ?? 'ready'}
                      data-cover-asset-id={selectedPost?.coverAssetId ?? ''}
                      data-selected-post-id={selectedPost?.id ?? ''}
                      data-width={contentSize.w}
                      data-height={contentSize.h}
                      data-text-edit-mode={editingElementId ? 'true' : 'false'}
                      onClick={() => selectElement(null)}
                      role="presentation"
                    >
                      {/*
                        Design-pixel layer: elements stay in format-canonical coords (e.g. 1080²).
                        Fit / Focus / Fullscreen only change ftv.stageSize.scale — never mutate geometry.
                      */}
                      <div
                        className="smb-ws__artboard-design"
                        data-testid="smb-artboard-design"
                        style={{
                          width: contentSize.w,
                          height: contentSize.h,
                          transform: `scale(${ftv.stageSize.scale})`,
                          transformOrigin: 'top left',
                        }}
                      >
                      {displayArtboardState === 'ready' && displayArtboardSrc ? (
                        <img
                          className="smb-ws__artboard-img"
                          src={displayArtboardSrc}
                          alt=""
                          data-testid="smb-artboard-img"
                          data-canva-preview={canvaPreview?.src ? 'true' : 'false'}
                          data-cover-asset-id={selectedPost?.coverAssetId ?? ''}
                          style={coverObjectPosition ? { objectPosition: coverObjectPosition } : undefined}
                          draggable={false}
                          onError={() => {
                            if (canvaPreview?.src) return;
                            if (selectedPost?.coverAssetId) {
                              postAssets.retryAsset(selectedPost.coverAssetId);
                            }
                          }}
                          onPointerDown={(e) => e.stopPropagation()}
                          onClick={(e) => {
                            e.stopPropagation();
                            selectElement(null);
                          }}
                        />
                      ) : (
                        <div
                          className="smb-ws__artboard-fallback"
                          data-testid={
                            displayArtboardState === 'error'
                              ? 'smb-artboard-error'
                              : displayArtboardState === 'loading'
                                ? 'smb-artboard-loading'
                                : 'smb-artboard-empty'
                          }
                          role="status"
                        >
                          <strong>
                            {displayArtboardState === 'error'
                              ? t('canvas.imageError')
                              : displayArtboardState === 'loading'
                                ? t('canvas.imageLoading')
                                : t('canvas.imageEmpty')}
                          </strong>
                          {displayArtboardState === 'empty' || displayArtboardState === 'error' ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              data-testid="smb-artboard-pick-image"
                              onClick={(e) => {
                                e.stopPropagation();
                                coverAsset.openPicker('cover');
                              }}
                            >
                              {t('rails.content.changeImage')}
                            </Button>
                          ) : null}
                        </div>
                      )}
                      {displayArtboardState === 'ready' && !hideOsLayers ? (
                        <div
                          className="smb-ws__artboard-overlay"
                          data-overlay={
                            selectedPost?.overlayStrategy ||
                            (typeof generationMeta?.creative_plan?.overlay_strategy === 'string'
                              ? generationMeta.creative_plan.overlay_strategy
                              : typeof generationMeta?.creative_concept?.overlay_region === 'string'
                                ? `localized-${generationMeta.creative_concept.overlay_region}`
                                : 'localized-top')
                          }
                          aria-hidden="true"
                        />
                      ) : null}
                      {brandLogo && !hideOsLayers && !hasRealLogoLayer ? (
                        <span
                          className="smb-ws__logo-preview"
                          style={{ position: 'absolute', top: '6%', left: '6%', zIndex: 2 }}
                        >
                          IH
                        </span>
                      ) : null}
                      {hideOsLayers ? null : (
                      <SmbArtboardElements
                        elements={selectedPost?.elements ?? []}
                        selectedElementId={previewMode ? null : selectedElementId}
                        editingElementId={previewMode ? null : editingElementId}
                        imageUrlsByAssetId={elementDisplayUrls}
                        canvasLocked={canvasLocked}
                        previewMode={previewMode}
                        canvasWidth={contentSize.w}
                        canvasHeight={contentSize.h}
                        onSelect={selectElement}
                        onPatchElement={(id, patch, opts) =>
                          patchElement(id, patch, {
                            live: opts?.live,
                            history:
                              opts?.history === false || editingElementId === id
                                ? false
                                : opts?.live
                                  ? false
                                  : undefined,
                          })
                        }
                        onBeginEdit={(id) => {
                          pushHistory();
                          setSelectedElementId(id);
                          setEditingElementId(id);
                        }}
                        onEndEdit={() => setEditingElementId(null)}
                        onGestureStart={beginGestureHistory}
                        onGestureEnd={endGestureHistory}
                      />
                      )}
                      </div>
                      {!previewMode && selectedElementId ? (
                        <div
                          className="smb-ws__floating-actions"
                          data-testid="smb-floating-actions"
                          data-align-open={alignMenuOpen ? 'true' : 'false'}
                          data-layer-open={layerMenuOpen ? 'true' : 'false'}
                          onPointerDown={(e) => e.stopPropagation()}
                          onMouseDown={(e) => e.stopPropagation()}
                          onClick={(e) => e.stopPropagation()}
                        >
                          {FLOATING_ACTIONS.map((action) => (
                            <div key={action.key} className="smb-ws__floating-more">
                              <button
                                type="button"
                                className={`smb-ws__floating-btn${
                                  (action.key === 'align' && alignMenuOpen) ||
                                  (action.key === 'layer' && layerMenuOpen)
                                    ? ' is-active'
                                    : ''
                                }`}
                                data-testid={`smb-floating-${action.key}`}
                                onClick={() => handleFloating(action.key)}
                              >
                                <IhIcon name={action.icon} size={11} />
                                {t(`floating.${action.key}`)}
                              </button>
                              {action.key === 'layer' && layerMenuOpen ? (
                                <div className="smb-ws__floating-menu" role="menu" data-testid="smb-layer-menu">
                                  <button
                                    type="button"
                                    role="menuitem"
                                    data-testid="smb-layer-forward"
                                    onClick={() => {
                                      if (!selectedElementId) return;
                                      replaceElements(
                                        bringElementForward(selectedPost?.elements ?? [], selectedElementId),
                                      );
                                      setLayerMenuOpen(false);
                                    }}
                                  >
                                    {t('floating.layerForward')}
                                  </button>
                                  <button
                                    type="button"
                                    role="menuitem"
                                    data-testid="smb-layer-backward"
                                    onClick={() => {
                                      if (!selectedElementId) return;
                                      replaceElements(
                                        sendElementBackward(selectedPost?.elements ?? [], selectedElementId),
                                      );
                                      setLayerMenuOpen(false);
                                    }}
                                  >
                                    {t('floating.layerBackward')}
                                  </button>
                                </div>
                              ) : null}
                              {action.key === 'align' && alignMenuOpen ? (
                                <div className="smb-ws__floating-menu" role="menu" data-testid="smb-align-menu">
                                  {(['left', 'center', 'right', 'top', 'middle', 'bottom'] as const).map(
                                    (mode) => (
                                      <button
                                        key={mode}
                                        type="button"
                                        role="menuitem"
                                        data-testid={`smb-align-${mode}`}
                                        onClick={() => {
                                          if (!selectedElement) return;
                                          const next = alignElement(
                                            selectedElement,
                                            mode,
                                            contentSize.w,
                                            contentSize.h,
                                          );
                                          patchElement(selectedElement.id, {
                                            x: next.x,
                                            y: next.y,
                                            ...(next.type === 'TEXT' ? { align: next.align } : {}),
                                          });
                                          setAlignMenuOpen(false);
                                        }}
                                      >
                                        {t(`floating.alignModes.${mode}`)}
                                      </button>
                                    ),
                                  )}
                                </div>
                              ) : null}
                            </div>
                          ))}
                          <div className="smb-ws__floating-more">
                            <button
                              type="button"
                              className={`smb-ws__floating-btn${floatingMoreOpen ? ' is-active' : ''}`}
                              aria-expanded={floatingMoreOpen}
                              data-testid="smb-floating-more"
                              onClick={() => handleFloating('more')}
                            >
                              ⋯
                            </button>
                            {floatingMoreOpen ? (
                              <div className="smb-ws__floating-menu" role="menu">
                                <button
                                  type="button"
                                  role="menuitem"
                                  data-testid="smb-floating-ai-edit"
                                  disabled={generating || designEngine === 'ideogram'}
                                  onClick={() => {
                                    setLeftRailId('ai');
                                    if (!selectedPost) return;
                                    if (designEngineRef.current === 'ideogram') return;
                                    void runGptImageGenerate(defaultSocialInstruction(selectedPost));
                                    setFloatingMoreOpen(false);
                                  }}
                                >
                                  {t('floating.menu.aiEdit')}
                                </button>
                                <button
                                  type="button"
                                  role="menuitem"
                                  data-testid="smb-floating-duplicate"
                                  onClick={() => {
                                    handleFloating('copy');
                                    setFloatingMoreOpen(false);
                                  }}
                                >
                                  {t('floating.menu.duplicate')}
                                </button>
                                <button
                                  type="button"
                                  role="menuitem"
                                  onClick={() => {
                                    setRightRailId('settings');
                                    setFloatingMoreOpen(false);
                                  }}
                                >
                                  {t('floating.menu.export')}
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </FocusFitStage>
                </div>
              </FocusCanvasLayout>
            </section>
          }
          right={rightDrawer}
        />
      </div>

      {publishOpen ? (
        <div className="smb-ws__modal" role="dialog" aria-modal="true" data-testid="smb-publish-modal">
          <div className="smb-ws__modal-card">
            <div className="smb-ws__modal-head">
              <div>
                <h2>{t('publishModal.title')}</h2>
                <p>{t('publishModal.subtitle')}</p>
              </div>
              <button
                type="button"
                className="smb-ws__icon-btn"
                aria-label={t('publishModal.close')}
                onClick={() => setPublishOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="smb-ws__modal-actions">
              <Button variant="secondary" size="sm" onClick={() => setPublishOpen(false)}>
                {t('publishModal.close')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled
                title={t('toasts.notAvailable')}
              >
                {t('publishModal.confirm')}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {coverAsset.pickerOpen ? (
        <CsMediaPickerDialog
          open={coverAsset.pickerOpen}
          onClose={coverAsset.closePicker}
          media={coverAsset.media}
          linkedProjectId={docApi.constructionProjectId}
          lockLinkedProject
          selectedAssetId={selectedPost?.coverAssetId ?? null}
          onSelect={(ref) => {
            if (!selectedPost) return;
            const prevId = selectedPost.coverAssetId;
            const nextId = ref.asset_id ?? null;
            coverAsset.setCoverImage({
              asset_id: nextId,
              url: nextId ? null : ref.url ?? null,
              alt: ref.alt ?? null,
              role: 'cover',
            });
            updateSelectedPost((p) => ({
              ...p,
              coverAssetId: nextId,
              thumbUrl: '',
            }));
            clearCanvaRaster(selectedPost.id);
            if (prevId && prevId !== nextId && !assetUsedByOtherPosts(prevId, postsRef.current, selectedPost.id)) {
              postAssets.invalidateAsset(prevId);
            }
            coverAsset.closePicker();
            markDirty();
            showToast(t('toasts.imageChanged'));
          }}
          testId="smb-media-picker-dialog"
        />
      ) : null}

      {elementImagePickerOpen ? (
        <CsMediaPickerDialog
          open={elementImagePickerOpen}
          onClose={() => setElementImagePickerOpen(false)}
          media={coverAsset.media}
          linkedProjectId={docApi.constructionProjectId}
          lockLinkedProject
          selectedAssetId={null}
          onSelect={(ref) => {
            if (!ref.asset_id) return;
            const el = createImageElement(contentSize.w, contentSize.h, ref.asset_id);
            addElement(el);
            setElementImagePickerOpen(false);
            showToast(t('toasts.imageChanged'));
          }}
          testId="smb-element-media-picker-dialog"
        />
      ) : null}

      <Dialog
        open={Boolean(deletePostId)}
        onClose={() => setDeletePostId(null)}
        title={t('deleteConfirm.title')}
        footer={
          <>
            <Button
              type="button"
              variant="secondary"
              data-testid="smb-post-delete-cancel"
              onClick={() => setDeletePostId(null)}
            >
              {t('deleteConfirm.cancel')}
            </Button>
            <Button
              type="button"
              variant="danger"
              data-testid="smb-post-delete-confirm"
              onClick={confirmDeletePost}
            >
              {t('deleteConfirm.confirm')}
            </Button>
          </>
        }
      >
        <p data-testid="smb-post-delete-message">{t('deleteConfirm.message')}</p>
      </Dialog>

      {toast ? (
        <div className="smb-ws__toast" role="status">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
