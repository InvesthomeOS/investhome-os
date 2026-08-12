'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { ApiError } from '@/lib/api/client';
import { generateSocialDesign } from '@/lib/api/creative-studio';

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
  createPostFromPreset,
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
  buildSocialDesignRequest,
  hasDesignInsufficientContext,
  inferDesignMode,
  parseGenerationMetaFromDraft,
  selectedElementToDesignContext,
  serializeGenerationMetaForDraft,
  toDesignGenerationMeta,
  type DesignGenerationMeta,
} from './social-media-builder-design-engine';
import {
  hydrateSocialPostsFromDraft,
  loadLastConstructionProjectId,
  loadPersistedLinkedProjectIdHint,
  resolvePreferredConstructionProjectId,
  saveEmergencySnapshot,
  saveLastConstructionProjectId,
  serializeSocialPosts,
} from './social-media-builder-persistence';
import { exportSocialPostPng } from './social-media-builder-export';
import { SmbArtboardElements } from './smb-artboard-elements';

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
  const [elementDisplayUrls, setElementDisplayUrls] = useState<Record<string, string>>({});
  const [aiDesignCollapsed, setAiDesignCollapsed] = useState(false);

  const filmstripRef = useRef<HTMLDivElement | null>(null);
  const genIdleTimerRef = useRef<number | null>(null);
  const genStageTimerRef = useRef<number | null>(null);
  const generateAbortRef = useRef(0);
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

  const selectedPost = posts.find((p) => p.id === selectedPostId) ?? posts[0]!;
  const selectedElement =
    selectedPost.elements.find((el) => el.id === selectedElementId) ?? null;
  const contentSize = resolveFormatSize(formatPreset);
  /** Authenticated Media Library blob only — never Unsplash / template fallback. */
  const artboardSrc =
    coverAsset.coverStatus === 'ready' && coverAsset.coverDisplayUrl
      ? coverAsset.coverDisplayUrl
      : null;
  const artboardState = coverAsset.coverStatus;

  const smbFitPadX = focus.isFullscreen ? 16 : 24;
  const smbFitPadY = focus.isFullscreen ? 16 : 32;

  const ftv = useFitToViewEngine({
    contentWidth: Math.max(1, contentSize.w),
    contentHeight: Math.max(1, contentSize.h),
    enabled: true,
    contentKey: `${formatPreset}-${selectedPost.id}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}-${smbFitPadX}x${smbFitPadY}`,
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

  const applyDraftPosts = useCallback(
    (draft: {
      posts?: Record<string, unknown>[];
      coverImage?: { asset_id?: string | null } | null;
      selectedPostId?: string | null;
      brandLogo?: boolean;
      platforms?: string[];
      linkedProjectId?: string | null;
    } | null) => {
      const coverId = draft?.coverImage?.asset_id ?? null;
      const hydrated = hydrateSocialPostsFromDraft({
        posts: draft?.posts,
        coverAssetId: coverId,
        linkedProjectId: draft?.linkedProjectId ?? docApi.constructionProjectId,
        selectedPostId: draft?.selectedPostId,
      });
      setPosts(
        hydrated.posts.map((p) => ({
          ...p,
          elements: ensureUniqueElementIds(p.elements),
        })),
      );
      setSelectedPostId(hydrated.selectedPostId);
      setHistoryPast([]);
      setHistoryFuture([]);
      setEditingElementId(null);
      const active = hydrated.posts.find((p) => p.id === hydrated.selectedPostId) ?? hydrated.posts[0]!;
      setFormatPreset(active.formatPreset);
      setSelectedElementId(null);
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
        active.coverAssetId || coverId
          ? {
              asset_id: active.coverAssetId || coverId,
              url: null,
              alt: null,
              role: 'cover' as const,
            }
          : null;
      coverAsset.hydrateMedia(coverRef, draft ? [] : []);
      if (draft && 'generationMeta' in draft) {
        setGenerationMeta(
          parseGenerationMetaFromDraft(
            (draft as { generationMeta?: Record<string, unknown> | null }).generationMeta,
          ),
        );
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

  useEffect(() => {
    return () => {
      if (genIdleTimerRef.current != null) window.clearTimeout(genIdleTimerRef.current);
      generateAbortRef.current += 1;
    };
  }, []);

  // Stable key of IMAGE asset IDs — do not depend on posts[] or coverAsset.media object identity.
  const imageAssetIdsKey = useMemo(() => {
    const ids = new Set<string>();
    for (const post of posts) {
      for (const el of post.elements) {
        if (el.type === 'IMAGE' && el.assetId) ids.add(el.assetId);
      }
    }
    return Array.from(ids).sort().join('|');
  }, [posts]);

  const ensureElementDisplayUrl = coverAsset.media.ensureDisplayUrl;

  // Resolve IMAGE element display URLs via scoped Media Library.
  useEffect(() => {
    let cancelled = false;
    const assetIds = imageAssetIdsKey ? imageAssetIdsKey.split('|') : [];
    void (async () => {
      const next: Record<string, string> = {};
      for (const id of assetIds) {
        try {
          const url = await ensureElementDisplayUrl(id);
          if (url) next[id] = url;
        } catch {
          /* skip */
        }
      }
      if (cancelled) return;
      setElementDisplayUrls((prev) => {
        const prevKeys = Object.keys(prev);
        const nextKeys = Object.keys(next);
        if (
          prevKeys.length === nextKeys.length &&
          nextKeys.every((key) => prev[key] === next[key])
        ) {
          return prev;
        }
        return next;
      });
    })();
    return () => {
      cancelled = true;
    };
  }, [imageAssetIdsKey, ensureElementDisplayUrl]);

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
    const active = current.find((p) => p.id === selectedPostId) ?? current[0]!;
    const coverFromPost = active?.coverAssetId
      ? {
          asset_id: active.coverAssetId,
          url: null as string | null,
          alt: null as string | null,
          role: 'cover' as const,
        }
      : coverAsset.coverImage;
    return {
      linkedProjectId: docApi.constructionProjectId,
      coverImage: coverFromPost,
      posts: serializeSocialPosts(
        current.map((p) => ({
          ...p,
          linkedProjectId: docApi.constructionProjectId,
        })),
      ),
      selectedPostId,
      brandLogo,
      platforms: Array.from(platforms),
      generationMeta: serializeGenerationMetaForDraft(generationMeta),
    };
  }, [
    brandLogo,
    coverAsset.coverImage,
    docApi.constructionProjectId,
    generationMeta,
    platforms,
    selectedPostId,
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
    const id = window.setTimeout(() => {
      void (async () => {
        const ok = await docApi.saveDraft(buildPersistPayload());
        if (ok) setSaved(true);
      })();
    }, 2000);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, docApi.loadStatus, coverAsset.coverImage, posts, selectedPostId, brandLogo, platforms]);

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
    const exists = selectedPost.elements.some((el) => el.id === elementId);
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
    const coverRef = post.coverAssetId
      ? { asset_id: post.coverAssetId, url: null, alt: null, role: 'cover' as const }
      : null;
    coverAsset.hydrateMedia(coverRef, []);
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
      coverAssetId: coverAsset.coverImage?.asset_id ?? null,
      linkedProjectId: docApi.constructionProjectId,
      cta: t('canvas.cta'),
    });
    setPosts((prev) => [...prev, next]);
    setSelectedPostId(next.id);
    setSelectedElementId(null);
    markDirty();
    showToast(t('toasts.postAdded'));
  }

  function addElement(el: SocialElement) {
    updateSelectedPost((p) => ({ ...p, elements: [...p.elements, el] }));
    setSelectedElementId(el.id);
    setRightRailId('content');
  }

  const runDownload = useCallback(async () => {
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
    selectedPost.elements,
    selectedPost.name,
    t,
  ]);

  function handleFloating(action: FloatingActionKey | 'more') {
    if (action === 'more') {
      setFloatingMoreOpen(!floatingMoreOpen);
      setAlignMenuOpen(false);
      setLayerMenuOpen(false);
      return;
    }
    if (action === 'edit') {
      if (!selectedElementId) {
        const first = selectedPost.elements[0];
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
      if (selectedElement) {
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

  const runAiGenerate = useCallback(
    async (instruction: string) => {
      // Always read latest canvas — sequential edits must not use a stale snapshot.
      const latestPosts = postsRef.current;
      const latestSelectedPostId = selectedPostIdRef.current;
      const built = buildSocialDesignRequest({
        linkedProjectId: docApi.constructionProjectId,
        instruction,
        posts: latestPosts,
        selectedPostId: latestSelectedPostId,
        selectedElement: selectedElementToDesignContext(
          latestPosts
            .find((p) => p.id === latestSelectedPostId)
            ?.elements.find((el) => el.id === selectedElementIdRef.current) ?? null,
        ),
        coverImage: coverAsset.coverImage,
        galleryImages: coverAsset.galleryImages,
        language: locale,
        platforms,
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
      const inferredMode = inferDesignMode(instruction, latestPosts);
      setGenerating(true);
      setCampaignStatus('draft');
      if (inferredMode === 'create') {
        let stageIdx = 0;
        setAiStatus(GENERATION_STATUS_STAGES[0]!);
        genStageTimerRef.current = window.setInterval(() => {
          stageIdx = Math.min(stageIdx + 1, GENERATION_STATUS_STAGES.length - 1);
          if (token === generateAbortRef.current) {
            setAiStatus(GENERATION_STATUS_STAGES[stageIdx]!);
          }
        }, 900);
      } else {
        setAiStatus('designingCreatives');
      }

      try {
        const response = await generateSocialDesign(built.request);
        if (token !== generateAbortRef.current) return;

        const meta = toDesignGenerationMeta(response);
        setGenerationMeta(meta);

        const applied = applyDesignResponseToPosts(
          response,
          docApi.constructionProjectId,
        );
        if (applied.posts.length) {
          pushHistory();
          setPosts(
            applied.posts.map((p) => ({
              ...p,
              elements: ensureUniqueElementIds(p.elements),
            })),
          );
          if (applied.selectedPostId) setSelectedPostId(applied.selectedPostId);
          setEditingElementId(null);
          // Sync cover from selected post for shared media rail
          const active =
            applied.posts.find((p) => p.id === applied.selectedPostId) ??
            applied.posts[0];
          if (active?.coverAssetId) {
            coverAsset.setCoverImage({
              asset_id: active.coverAssetId,
              url: null,
              alt: null,
              role: 'cover',
            });
          }
          markDirty();
          setRightRailId('content');
        }

        if (hasDesignInsufficientContext(response)) {
          showToast(t('toasts.insufficientContext'));
        } else if (meta.warnings.includes('no_valid_project_media')) {
          showToast(t('toasts.noProjectMedia'));
        } else if (meta.warnings.length) {
          showToast(t('toasts.generationWarning', { warning: meta.warnings[0]! }));
        } else {
          showToast(t('toasts.designed'));
        }

        setAiStatus('completed');
        setCampaignStatus('ready');
        setAiPrompt('');
        const nextPosts = (
          applied.posts.length
            ? applied.posts.map((p) => ({
                ...p,
                elements: ensureUniqueElementIds(p.elements),
              }))
            : postsRef.current
        ).map((p) => ({
          ...p,
          linkedProjectId: docApi.constructionProjectId,
        }));
        const persistPayload = {
          ...buildPersistPayload(),
          generationMeta: serializeGenerationMetaForDraft(meta),
          posts: serializeSocialPosts(nextPosts),
          selectedPostId: applied.selectedPostId ?? selectedPostIdRef.current,
        };
        void docApi.saveDraft(persistPayload);
        genIdleTimerRef.current = window.setTimeout(() => {
          if (token === generateAbortRef.current) setAiStatus('idle');
        }, 1600);
      } catch (err) {
        if (token !== generateAbortRef.current) return;
        setAiStatus('idle');
        setCampaignStatus('failed');
        const message =
          err instanceof ApiError && err.message
            ? err.message
            : t('toasts.generateFailed');
        showToast(message);
      } finally {
        if (genStageTimerRef.current != null) {
          window.clearInterval(genStageTimerRef.current);
          genStageTimerRef.current = null;
        }
        if (token === generateAbortRef.current) setGenerating(false);
      }
    },
    [
      buildPersistPayload,
      coverAsset,
      docApi,
      locale,
      platforms,
      t,
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
        void runAiGenerate(instruction);
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
      coverDisplayUrl={artboardSrc ?? ''}
      onDownload={() => {
        void runDownload();
      }}
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

  function submitAiDesign() {
    const instruction = aiPrompt.trim();
    if (!instruction) {
      showToast(t('toasts.instructionRequired'));
      return;
    }
    void runAiGenerate(instruction);
  }

  const aiDesignCommand = (
    <div
      className={[
        'smb-ws__ai-design',
        focus.isFullscreen ? 'smb-ws__ai-design--fs' : '',
        aiDesignCollapsed && focus.isFullscreen ? 'is-collapsed' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      data-testid="smb-ai-design-command"
      data-fs-ai={focus.isFullscreen ? 'true' : 'false'}
    >
      <div className="smb-ws__ai-design-head">
        <label className="smb-ws__ai-design-label" htmlFor="smb-ai-design-input">
          {t('aiDesign.title')}
        </label>
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
        <div className="smb-ws__ai-design-row">
          <input
            id="smb-ai-design-input"
            className="smb-ws__ai-design-input"
            type="text"
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            placeholder={t('aiDesign.placeholder')}
            data-testid="smb-ai-design-input"
            disabled={generating}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitAiDesign();
              }
            }}
          />
          <Button
            variant="primary"
            size="sm"
            data-testid="smb-ai-design-submit"
            disabled={generating}
            onClick={submitAiDesign}
          >
            <IhIcon name="sparkles" size={12} />
            {generating ? t('aiDesign.generating') : t('aiDesign.submit')}
          </Button>
        </div>
      ) : null}
    </div>
  );

  const previewMode = focus.mode === 'preview';

  return (
    <main className="dashboard" data-testid="smb-workspace-page">
      <div
        className="smb-ws"
        data-testid="smb-workspace"
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
              title={t('toasts.notAvailable')}
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
                          <button
                            key={post.id}
                            type="button"
                            className={`smb-ws__page-card${selectedPostId === post.id ? ' is-selected' : ''}`}
                            onClick={() => selectPost(post)}
                            data-testid={`smb-post-card-${post.id}`}
                          >
                            <div
                              className={`smb-ws__page-thumb ${aspectThumbClass(post.formatPreset)}`}
                            >
                              {selectedPostId === post.id && artboardSrc ? (
                                <img src={artboardSrc} alt="" />
                              ) : (
                                <span className="smb-ws__page-thumb-empty" aria-hidden="true" />
                              )}
                            </div>
                            <strong>{post.name}</strong>
                          </button>
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
                      primary={{
                        label: t('bottomBar.actions.addComponent'),
                        icon: 'plus',
                        onClick: () => handleBottomAction('addComponent'),
                        testId: 'smb-action-addComponent',
                      }}
                      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addComponent').map((action) => ({
                        key: action.key,
                        icon: action.icon,
                        label: t(`bottomBar.actions.${action.key}`),
                        onClick: () => handleBottomAction(action.key),
                        testId: `smb-action-${action.key}`,
                        disabled: !P0_BOTTOM_ACTIONS.has(action.key),
                        priority: P0_BOTTOM_ACTIONS.has(action.key) ? 'high' : 'low',
                      }))}
                    />
                  ),
                }}
              >
                <div className="smb-ws__canvas-stage" data-testid="smb-preview-shell">
                  <FocusFitStage engine={ftv} artboardTestId="smb-ftv-artboard">
                    <div
                      className={`smb-ws__artboard${selectedElementId || artboardState === 'ready' ? ' is-selected' : ''}${artboardState !== 'ready' ? ' is-empty' : ''}`}
                      data-testid="smb-artboard"
                      data-image-state={artboardState}
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
                      {artboardState === 'ready' && artboardSrc ? (
                        <img
                          className="smb-ws__artboard-img"
                          src={artboardSrc}
                          alt=""
                          data-testid="smb-artboard-img"
                          draggable={false}
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
                            artboardState === 'error'
                              ? 'smb-artboard-error'
                              : artboardState === 'loading'
                                ? 'smb-artboard-loading'
                                : 'smb-artboard-empty'
                          }
                          role="status"
                        >
                          <strong>
                            {artboardState === 'error'
                              ? t('canvas.imageError')
                              : artboardState === 'loading'
                                ? t('canvas.imageLoading')
                                : t('canvas.imageEmpty')}
                          </strong>
                          {artboardState === 'empty' || artboardState === 'error' ? (
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
                      {artboardState === 'ready' ? (
                        <div
                          className="smb-ws__artboard-overlay"
                          data-overlay={
                            selectedPost.overlayStrategy ||
                            (typeof generationMeta?.creative_concept?.overlay_region === 'string'
                              ? `localized-${generationMeta.creative_concept.overlay_region}`
                              : 'localized-top')
                          }
                          aria-hidden="true"
                        />
                      ) : null}
                      {brandLogo ? (
                        <span
                          className="smb-ws__logo-preview"
                          style={{ position: 'absolute', top: '6%', left: '6%', zIndex: 2 }}
                        >
                          IH
                        </span>
                      ) : null}
                      <SmbArtboardElements
                        elements={selectedPost.elements}
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
                                        bringElementForward(selectedPost.elements, selectedElementId),
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
                                        sendElementBackward(selectedPost.elements, selectedElementId),
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
                                  disabled={generating}
                                  onClick={() => {
                                    setLeftRailId('ai');
                                    void runAiGenerate(defaultSocialInstruction(selectedPost));
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
          selectedAssetId={coverAsset.coverImage?.asset_id ?? null}
          onSelect={(ref) => {
            coverAsset.setCoverImage({
              asset_id: ref.asset_id,
              url: ref.asset_id ? null : ref.url ?? null,
              alt: ref.alt ?? null,
              role: 'cover',
            });
            updateSelectedPost((p) => ({
              ...p,
              coverAssetId: ref.asset_id,
              thumbUrl: '',
            }));
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

      {toast ? (
        <div className="smb-ws__toast" role="status">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
