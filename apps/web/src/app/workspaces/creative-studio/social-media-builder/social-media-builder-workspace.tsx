'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { ApiError } from '@/lib/api/client';
import { generateCreativeStudioContent } from '@/lib/api/creative-studio';

import {
  BOTTOM_ACTIONS,
  CAMPAIGN_STATUS_TONE,
  DEFAULT_POSTS,
  FLOATING_ACTIONS,
  FORMAT_PRESETS,
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
  applyGeneratedCopyToPost,
  buildSocialGenerateRequest,
  defaultSocialInstruction,
  hasInsufficientContext,
  toGenerationMeta,
  type SocialGenerationMeta,
} from './social-media-builder-generation';
import {
  loadLastConstructionProjectId,
  loadPersistedLinkedProjectIdHint,
  resolvePreferredConstructionProjectId,
  saveEmergencySnapshot,
  saveLastConstructionProjectId,
} from './social-media-builder-persistence';
import { exportSocialPostPng } from './social-media-builder-export';

import {
  SmbLeftRailDrawer,
  SmbLocalRail,
  SmbRightRailDrawer,
  SmbZoomToolbar,
} from './social-media-builder-rail-drawers';

import { CsBottomActionToolbar, CsMediaPickerDialog } from '../_components';
import { useBuilderCoverAsset } from '../_components/use-builder-cover-asset';
import { useBuilderDocument } from '../_components/use-builder-document';
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

  const [hydrated, setHydrated] = useState(false);
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus>('ready');
  const [saved, setSaved] = useState(true);
  const [aiStatus, setAiStatus] = useState<AiStatusKey>('idle');
  const [generating, setGenerating] = useState(false);
  const [generationMeta, setGenerationMeta] = useState<SocialGenerationMeta | null>(null);
  const [leftRailId, setLeftRailId] = useState<SmbLeftRailId>('templates');
  const [rightRailId, setRightRailId] = useState<SmbRightRailId>('content');
  const focus = useCreativeStudioFocusMode({ storageKey: 'social-media-builder' });

  const [posts, setPosts] = useState<SocialPost[]>(DEFAULT_POSTS);
  const [selectedPostId, setSelectedPostId] = useState('p1');
  const [formatPreset, setFormatPreset] = useState<FormatPresetKey>('square');
  const [platforms, setPlatforms] = useState<Set<PlatformKey>>(
    () => new Set(['instagram', 'facebook', 'linkedin', 'x']),
  );
  const [brandLogo, setBrandLogo] = useState(true);
  const [bgMode, setBgMode] = useState<BgMode>('image');
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [selected, setSelected] = useState(true);
  const [floatingMoreOpen, setFloatingMoreOpen] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const filmstripRef = useRef<HTMLDivElement | null>(null);
  const genIdleTimerRef = useRef<number | null>(null);
  const generateAbortRef = useRef(0);

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
    let cancelled = false;
    void (async () => {
      const result = await docApi.bootstrap();
      if (cancelled) return;
      if (result.ok) {
        coverAsset.hydrateMedia(result.draft?.coverImage ?? null, result.draft?.galleryImages ?? []);
        setSaved(Boolean(result.draft));
      }
      setHydrated(true);
    })();
    return () => {
      cancelled = true;
      if (genIdleTimerRef.current != null) window.clearTimeout(genIdleTimerRef.current);
      generateAbortRef.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!hydrated || docApi.loadStatus !== 'ready') return;
    const id = window.setTimeout(() => {
      void (async () => {
        const ok = await docApi.saveDraft({
          linkedProjectId: docApi.constructionProjectId,
          coverImage: coverAsset.coverImage,
        });
        if (ok) setSaved(true);
      })();
    }, 2000);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, docApi.loadStatus, coverAsset.coverImage]);

  useEffect(() => {
    if (!floatingMoreOpen) return;
    function onDocPointer() {
      setFloatingMoreOpen(false);
    }
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') setFloatingMoreOpen(false);
    }
    document.addEventListener('mousedown', onDocPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [floatingMoreOpen]);

  function markDirty() {
    setSaved(false);
  }

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  const persistNow = useCallback(
    async (announce = false) => {
      if (docApi.loadStatus !== 'ready') return;
      const ok = await docApi.saveDraft({
        linkedProjectId: docApi.constructionProjectId,
        coverImage: coverAsset.coverImage,
      });
      if (ok) {
        setSaved(true);
        if (announce) showToast(t('toasts.saved'));
      } else if (announce) {
        showToast(t('toasts.saveFailed'));
      }
    },
    [coverAsset.coverImage, docApi, t],
  );

  async function handleProjectChange(id: string) {
    const draft = await docApi.selectConstructionProject(id);
    coverAsset.hydrateMedia(draft?.coverImage ?? null, draft?.galleryImages ?? []);
    setGenerationMeta(null);
    setSaved(Boolean(draft));
  }

  function patchPost(patch: Partial<SocialPost>) {
    setPosts((prev) =>
      prev.map((p) => (p.id === selectedPost.id ? { ...p, ...patch } : p)),
    );
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
  }

  function selectPost(post: SocialPost) {
    setSelectedPostId(post.id);
    setFormatPreset(post.formatPreset);
    setSelected(true);
  }

  function handleFormatChange(key: FormatPresetKey) {
    setFormatPreset(key);
    const size = resolveFormatSize(key);
    patchPost({ formatPreset: key, width: size.w, height: size.h });
    markDirty();
    const match = posts.find((p) => p.formatPreset === key);
    if (match) setSelectedPostId(match.id);
  }

  function addPost() {
    const next = createPostFromPreset(
      formatPreset,
      posts.length + 1,
      artboardSrc || '',
    );
    setPosts((prev) => [...prev, next]);
    setSelectedPostId(next.id);
    markDirty();
    showToast(t('toasts.postAdded'));
  }

  const runDownload = useCallback(async () => {
    if (!artboardSrc || artboardState !== 'ready') {
      showToast(t('toasts.downloadFailed'));
      return;
    }
    try {
      await exportSocialPostPng({
        width: contentSize.w,
        height: contentSize.h,
        imageUrl: artboardSrc,
        headline: selectedPost.headline,
        caption: selectedPost.caption,
        cta: t('canvas.cta'),
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
    selectedPost.caption,
    selectedPost.headline,
    selectedPost.name,
    t,
  ]);

  function handleFloating(action: FloatingActionKey | 'more') {
    if (action === 'more') {
      setFloatingMoreOpen((v) => !v);
      return;
    }
    if (action === 'delete') {
      coverAsset.clearCover();
      setPosts((prev) =>
        prev.map((p) => (p.id === selectedPost.id ? { ...p, thumbUrl: '' } : p)),
      );
      setSelected(false);
      markDirty();
      void (async () => {
        let ok = false;
        for (let attempt = 0; attempt < 8 && !ok; attempt += 1) {
          ok = await docApi.saveDraft({
            linkedProjectId: docApi.constructionProjectId,
            coverImage: null,
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
    if (action === 'edit') {
      setRightRailId('content');
      return;
    }
    if (action === 'copy') {
      const clone: SocialPost = {
        ...selectedPost,
        id: `p-copy-${Date.now()}`,
        name: `${selectedPost.name} (copy)`,
        status: 'draft',
      };
      setPosts((prev) => [...prev, clone]);
      setSelectedPostId(clone.id);
      markDirty();
      showToast(t('floating.copy'));
      return;
    }
    showToast(t(`floating.${action}`));
  }

  function handleBottomAction(action: BottomActionKey) {
    if (action === 'addComponent') {
      setLeftRailId('components');
      showToast(t('bottomBar.toasts.addComponent'));
      return;
    }
    if (action === 'image') {
      coverAsset.openPicker('cover');
      return;
    }
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function handleApplyTemplate(format: FormatPresetKey, thumbUrl: string) {
    setFormatPreset(format);
    const size = resolveFormatSize(format);
    patchPost({ formatPreset: format, width: size.w, height: size.h, thumbUrl });
    markDirty();
    showToast(t('toasts.templateApplied'));
  }

  function handleInsertComponent(key: string) {
    showToast(t('rails.components.toasts.inserted', { name: t(`rails.components.items.${key}` as 'rails.components.items.text') }));
  }

  function scrollFilmstrip(dir: -1 | 1) {
    const el = filmstripRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 160, behavior: 'smooth' });
  }

  const runAiGenerate = useCallback(
    async (instruction: string) => {
      const built = buildSocialGenerateRequest({
        linkedProjectId: docApi.constructionProjectId,
        instruction,
        coverImage: coverAsset.coverImage,
        galleryImages: coverAsset.galleryImages,
        language: locale,
        platforms,
        formatPreset,
        platform: selectedPost.platform,
        postName: selectedPost.name,
        format: selectedPost.format,
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

      const token = ++generateAbortRef.current;
      setGenerating(true);
      setAiStatus('thinking');
      setCampaignStatus('draft');

      try {
        const response = await generateCreativeStudioContent(built.request);
        if (token !== generateAbortRef.current) return;

        const meta = toGenerationMeta(response);
        setGenerationMeta(meta);

        const copy = applyGeneratedCopyToPost(response.generated_content);
        if (Object.keys(copy).length) {
          setPosts((prev) =>
            prev.map((p) => (p.id === selectedPostId ? { ...p, ...copy } : p)),
          );
          markDirty();
          setRightRailId('content');
        }

        if (hasInsufficientContext(response)) {
          showToast(t('toasts.insufficientContext'));
        } else if (meta.warnings.length) {
          showToast(t('toasts.generationWarning', { warning: meta.warnings[0]! }));
        } else {
          showToast(t('toasts.generated'));
        }

        setAiStatus('completed');
        setCampaignStatus('ready');
        void persistNow();
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
        if (token === generateAbortRef.current) setGenerating(false);
      }
    },
    [
      coverAsset.coverImage,
      coverAsset.galleryImages,
      docApi.constructionProjectId,
      formatPreset,
      locale,
      platforms,
      persistNow,
      selectedPost.format,
      selectedPost.name,
      selectedPost.platform,
      selectedPostId,
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
      formatPreset={formatPreset}
      setFormatPreset={handleFormatChange}
      platforms={platforms}
      togglePlatform={togglePlatform}
      brandLogo={brandLogo}
      setBrandLogo={setBrandLogo}
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

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="smb-workspace-loading">
        <div className="smb-ws">
          <div className="smb-ws__skeleton smb-ws__skeleton--header" />
        </div>
      </main>
    );
  }

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
              }}
            >
              {t('preview')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="smb-send-test"
              onClick={() => showToast(t('toasts.testSent'))}
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
              onClick={() => setPublishOpen(true)}
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
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="smb-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="smb-redo"
                onClick={() => showToast(t('toasts.redo'))}
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
                              {artboardSrc ? (
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
                      }))}
                    />
                  ),
                }}
              >
                <div className="smb-ws__canvas-stage" data-testid="smb-preview-shell">
                  <FocusFitStage engine={ftv} artboardTestId="smb-ftv-artboard">
                    <div
                      className={`smb-ws__artboard${selected ? ' is-selected' : ''}${artboardState !== 'ready' ? ' is-empty' : ''}`}
                      data-testid="smb-artboard"
                      data-image-state={artboardState}
                      onClick={() => setSelected(true)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') setSelected(true);
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      {artboardState === 'ready' && artboardSrc ? (
                        <img
                          className="smb-ws__artboard-img"
                          src={artboardSrc}
                          alt=""
                          data-testid="smb-artboard-img"
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
                        <div className="smb-ws__artboard-overlay" aria-hidden="true" />
                      ) : null}
                      {brandLogo && artboardState === 'ready' ? (
                        <span
                          className="smb-ws__logo-preview"
                          style={{ position: 'absolute', top: '6%', left: '6%', zIndex: 2 }}
                        >
                          IH
                        </span>
                      ) : null}
                      {artboardState === 'ready' ? (
                        <div className="smb-ws__artboard-copy">
                          <strong>{selectedPost.headline}</strong>
                          <p>{selectedPost.caption}</p>
                          <span className="smb-ws__artboard-cta">{t('canvas.cta')}</span>
                        </div>
                      ) : null}
                      {selected ? (
                        <div
                          className="smb-ws__floating-actions"
                          data-testid="smb-floating-actions"
                          onMouseDown={(e) => e.stopPropagation()}
                        >
                          {FLOATING_ACTIONS.map((action) => (
                            <button
                              key={action.key}
                              type="button"
                              className="smb-ws__floating-btn"
                              data-testid={`smb-floating-${action.key}`}
                              onClick={() => handleFloating(action.key)}
                            >
                              <IhIcon name={action.icon} size={11} />
                              {t(`floating.${action.key}`)}
                            </button>
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
                                  onClick={() => {
                                    showToast(t('floating.menu.duplicate'));
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
                onClick={() => {
                  setPublishOpen(false);
                  setCampaignStatus('published');
                  void persistNow();
                  showToast(t('toasts.published'));
                }}
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
            // Persist Asset ID only — never blob:/object: thumb URLs.
            coverAsset.setCoverImage({
              asset_id: ref.asset_id,
              url: ref.asset_id ? null : ref.url ?? null,
              alt: ref.alt ?? null,
              role: 'cover',
            });
            coverAsset.closePicker();
            patchPost({ thumbUrl: '' });
            markDirty();
            showToast(t('toasts.imageChanged'));
          }}
          testId="smb-media-picker-dialog"
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
