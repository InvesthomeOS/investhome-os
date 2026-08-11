'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { createPortal } from 'react-dom';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  ASPECT_RATIOS,
  BOTTOM_ACTION_ICONS,
  BOTTOM_COMPONENT_ACTIONS,
  CAMPAIGN_STATUS_TONE,
  DEFAULT_BRIEF,
  DEFAULT_SLIDES,
  FLOATING_ACTION_ICONS,
  FLOATING_ACTIONS,
  PB_HOME,
  PB_LEFT_RAIL_IDS,
  PB_PROJECTS,
  PB_RIGHT_RAIL_IDS,
  aspectClass,
  aspectDims,
  getProject,
  type AspectRatio,
  type BottomActionKey,
  type CampaignStatus,
  type FloatingActionKey,
  type PbSlide,
  type PresentationBrief,
  type ProjectId,
  type ViewMode,
} from './presentation-builder-model';

import {
  PbLeftRailDrawer,
  PbLocalRail,
  PbRightRailDrawer,
  PbZoomToolbar,
  type PbLeftRailId,
  type PbRightRailId,
} from './presentation-builder-rail-drawers';
import {
  loadLastConstructionProjectId,
  loadPersistedLinkedProjectIdHint,
  resolvePreferredConstructionProjectId,
  saveEmergencySnapshot,
  saveLastConstructionProjectId,
} from './presentation-builder-persistence';

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

import './presentation-builder.css';

const AI_PRESENT_INTERVAL_MS = 4200;

function visualTemplateForProject(
  projectId: string,
  templates: typeof PB_PROJECTS,
): (typeof PB_PROJECTS)[number] {
  let hash = 0;
  const key = projectId || 'default';
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash + key.charCodeAt(i) * (i + 1)) % templates.length;
  }
  return templates[hash] ?? templates[0]!;
}
export function PresentationBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tBootstrap = useTranslations('creativeStudio.ds.bootstrap');
  const tCommon = useTranslations('common');

  const docApi = useBuilderDocument({
    documentType: 'presentation',
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
  const [brief, setBrief] = useState<PresentationBrief>(DEFAULT_BRIEF);
  const focus = useCreativeStudioFocusMode({ storageKey: 'presentation-builder' });
  const [slides, setSlides] = useState<PbSlide[]>(DEFAULT_SLIDES);
  const [selectedSlideId, setSelectedSlideId] = useState('sl-1');
  const [viewMode] = useState<ViewMode>('slide');
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [aiPresenting, setAiPresenting] = useState(false);
  const [aiPresentIndex, setAiPresentIndex] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [leftRailId, setLeftRailId] = useState<PbLeftRailId>('slides');
  const [rightRailId, setRightRailId] = useState<PbRightRailId>('theme');
  const [speakerNotes, setSpeakerNotes] = useState(
    'Highlight the investment thesis, keep pace board-ready, and close with a clear next step.',
  );
  const [showSlideNumber, setShowSlideNumber] = useState(true);
  const [floatingMoreOpen, setFloatingMoreOpen] = useState(false);
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [moreMenuPos, setMoreMenuPos] = useState<{ top: number; left: number } | null>(null);
  const floatingMoreRef = useRef<HTMLButtonElement | null>(null);
  const presentTimerRef = useRef<number | null>(null);

  const selectedConstruction = useMemo(
    () =>
      docApi.constructionProjects.find((p) => p.id === docApi.constructionProjectId) ?? null,
    [docApi.constructionProjects, docApi.constructionProjectId],
  );
  const project = useMemo(() => {
    const visualProj = visualTemplateForProject(
      docApi.constructionProjectId || selectedConstruction?.project_name || 'default',
      PB_PROJECTS,
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
  const selectedSlide = slides.find((s) => s.id === selectedSlideId) ?? slides[0]!;
  const selectedIndex = slides.findIndex((s) => s.id === selectedSlide.id);
  const presentSlide = slides[aiPresentIndex] ?? slides[0]!;

  const pbLeftRail: FocusRailItem[] = useMemo(
    () => [
      { id: 'slides', icon: 'projects', labelKey: 'assets', label: t('rails.labels.slides') },
      { id: 'layouts', icon: 'design', labelKey: 'brand', label: t('rails.labels.layouts') },
      { id: 'sections', icon: 'documents', labelKey: 'brief', label: t('rails.labels.sections') },
      { id: 'templates', icon: 'theme', labelKey: 'settings', label: t('rails.labels.templates') },
    ],
    [t],
  );

  const pbRightRail: FocusRailItem[] = useMemo(
    () => [
      { id: 'theme', icon: 'theme', labelKey: 'settings', label: t('rails.labels.theme') },
      { id: 'brand', icon: 'design', labelKey: 'brand', label: t('rails.labels.brand') },
      { id: 'animation', icon: 'activity', labelKey: 'quickActions', label: t('rails.labels.animation') },
      { id: 'notes', icon: 'documents', labelKey: 'score', label: t('rails.labels.notes') },
    ],
    [t],
  );

  const localLeftItems = useMemo(
    () => pbLeftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [pbLeftRail],
  );
  const localRightItems = useMemo(
    () => pbRightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [pbRightRail],
  );

  const dims = aspectDims(aspectRatio);
  const ftv = useFitToViewEngine({
    contentWidth: dims.w,
    contentHeight: dims.h,
    enabled: viewMode === 'slide',
    contentKey: `${aspectRatio}-${selectedSlideId}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}`,
    cssWidthVar: '--pb-stage-w',
    cssHeightVar: '--pb-stage-h',
    canvasType: 'artwork',
  });

  const hydration = useCsBuilderHydration({
    bootstrap: docApi.bootstrap,
    onSuccess: (draft) => {
      coverAsset.hydrateMedia(draft?.coverImage ?? null, draft?.galleryImages ?? []);
      setSaved(Boolean(draft));
    },
  });
  const hydrated = hydration.hydrated;

  useEffect(() => {
    return () => {
      if (presentTimerRef.current) window.clearInterval(presentTimerRef.current);
    };
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
    function onDoc() {
      setFloatingMoreOpen(false);
      setMoreMenuPos(null);
    }
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        if (aiPresenting) {
          setAiPresenting(false);
          return;
        }
        setFloatingMoreOpen(false);
        setMoreMenuPos(null);
      }
    }
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [floatingMoreOpen, aiPresenting]);

  useEffect(() => {
    if (focus.isFocus || focus.isFullscreen) {
      if (ftv.autoFit) ftv.fitToView();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.isFocus, focus.isFullscreen]);

  useEffect(() => {
    if (!aiPresenting) {
      if (presentTimerRef.current) {
        window.clearInterval(presentTimerRef.current);
        presentTimerRef.current = null;
      }
      return;
    }

    presentTimerRef.current = window.setInterval(() => {
      setAiPresentIndex((prev) => {
        if (prev >= slides.length - 1) {
          setAiPresenting(false);
          showToast(t('toasts.aiPresentDone'));
          return prev;
        }
        const next = prev + 1;
        setSelectedSlideId(slides[next]!.id);
        return next;
      });
    }, AI_PRESENT_INTERVAL_MS);

    return () => {
      if (presentTimerRef.current) {
        window.clearInterval(presentTimerRef.current);
        presentTimerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aiPresenting, slides, t]);

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
    const name =
      docApi.constructionProjects.find((p) => p.id === id)?.project_name || project.name;
    setBrief((prev) => ({
      ...prev,
      topic: name + ' ? Investment Deck',
    }));
    setSaved(Boolean(draft));
  }

  function markDirty() {
    setSaved(false);
  }

  function addSlide() {
    const copy: PbSlide = {
      id: `sl-${Date.now()}`,
      kind: 'appendix',
      thumbUrl: coverAsset.coverDisplayUrl,
    };
    setSlides((prev) => [...prev, copy]);
    setSelectedSlideId(copy.id);
    setLeftRailId('slides');
    setSaved(false);
    showToast(t('toasts.slideAdded'));
  }

  function duplicateSlide(id: string) {
    const source = slides.find((s) => s.id === id) ?? selectedSlide;
    const copy: PbSlide = { ...source, id: `sl-${Date.now()}` };
    setSlides((prev) => {
      const idx = prev.findIndex((s) => s.id === source.id);
      const next = [...prev];
      next.splice(idx + 1, 0, copy);
      return next;
    });
    setSelectedSlideId(copy.id);
    setSaved(false);
    showToast(t('toasts.slideDuplicated'));
  }

  function deleteSlide(id: string) {
    if (slides.length <= 1) {
      showToast(t('toasts.cannotDeleteLast'));
      return;
    }
    const fallback = slides.find((s) => s.id !== id);
    setSlides((prev) => prev.filter((s) => s.id !== id));
    if (fallback) setSelectedSlideId(fallback.id);
    setSaved(false);
    showToast(t('toasts.slideDeleted'));
  }

  function handleBottomAction(action: BottomActionKey) {
    if (action === 'addSlide') {
      addSlide();
      return;
    }
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function handleFloatingAction(action: FloatingActionKey) {
    if (action === 'copy') {
      duplicateSlide(selectedSlide.id);
      return;
    }
    if (action === 'delete') {
      deleteSlide(selectedSlide.id);
      return;
    }
    if (action === 'more') {
      const rect = floatingMoreRef.current?.getBoundingClientRect();
      if (rect) {
        setMoreMenuPos({ top: rect.bottom + 6, left: rect.left });
      }
      setFloatingMoreOpen((v) => !v);
      return;
    }
    showToast(t(`floating.toasts.${action}`));
  }

  function startAiPresent() {
    const startIdx = Math.max(0, selectedIndex);
    setAiPresentIndex(startIdx);
    setAiPresenting(true);
    showToast(t('toasts.aiPresentStart'));
  }

  function stopAiPresent() {
    setAiPresenting(false);
    showToast(t('toasts.aiPresentDone'));
  }

  const leftDrawerContent = (
    <PbLeftRailDrawer
      id={leftRailId}
      brief={brief}
      setBrief={setBrief}
      slides={slides}
      selectedSlideId={selectedSlideId}
      setSelectedSlideId={setSelectedSlideId}
      setSlides={setSlides}
      aspectRatio={aspectRatio}
      onAddSlide={addSlide}
      onDuplicateSlide={duplicateSlide}
      onDeleteSlide={deleteSlide}
      markDirty={markDirty}
    />
  );

  const rightDrawerContent = (
    <PbRightRailDrawer
      id={rightRailId}
      brief={brief}
      setBrief={setBrief}
      markDirty={markDirty}
      speakerNotes={speakerNotes}
      setSpeakerNotes={setSpeakerNotes}
      showSlideNumber={showSlideNumber}
      setShowSlideNumber={setShowSlideNumber}
      onToast={showToast}
    />
  );

  const leftDrawer =
    focus.isFocus || focus.isFullscreen ? (
      leftDrawerContent
    ) : (
      <div className="pb-ws__panel pb-ws__left" aria-label={t('left.aria')} data-testid="pb-left">
        <PbLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as PbLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="pb-ws__panel pb-ws__right" aria-label={t('right.aria')} data-testid="pb-right">
        <PbLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as PbRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (hydration.phase !== 'ready') {
    return (
      <CsBuilderBootstrapView
        testId="pb-workspace-loading"
        workspaceClassName="pb-ws"
        homeHref={PB_HOME}
        title={tTools('presentationStudio.title')}
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

  return (
    <main className="dashboard" data-testid="pb-workspace">
      <div
        className="pb-ws"
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
      >
        <header className="pb-ws__header cs-page-header">
          <div className="pb-ws__header-copy cs-page-header__copy">
            <Link href={PB_HOME as Route} className="pb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="pb-ws__breadcrumb">
                <li>
                  <Link href={PB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="pb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="pb-ws__breadcrumb-current" aria-current="page">
                  {tTools('presentationStudio.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="target" size={20} />
              {tTools('presentationStudio.title')}
            </h1>
            <p className="pb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="pb-ws__header-actions cs-page-header__actions">
            <div className="pb-ws__save-status" data-testid="pb-save-status">
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <StatusChip tone={CAMPAIGN_STATUS_TONE[campaignStatus]}>
                {t(`status.${campaignStatus}`)}
              </StatusChip>
              <span className="pb-ws__saved-ago">{saved ? t('savedAgo') : t('notSavedYet')}</span>
            </div>
            <Button variant="secondary" size="sm" onClick={() => void persistNow(true)} data-testid="pb-save" disabled={docApi.saveStatus === 'saving' || docApi.loadStatus !== 'ready'}>
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="pb-preview"
              onClick={() => {
                focus.setMode('preview');
                showToast(t('toasts.preview'));
              }}
            >
              {t('preview')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="pb-start-presentation"
              onClick={startAiPresent}
            >
              {t('startPresentation')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="pb-export-pdf"
              onClick={() => {
                setCampaignStatus('exported');
                showToast(t('toasts.exportedPdf'));
              }}
            >
              {t('exportPdf')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="pb-export-pptx"
              onClick={() => {
                setCampaignStatus('exported');
                showToast(t('toasts.exportedPptx'));
              }}
            >
              {t('exportPptx')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="pb-publish"
              onClick={() => {
                setCampaignStatus('exported');
                showToast(t('toasts.published'));
              }}
            >
              {t('publish')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
          </div>
        </header>

        <div className="pb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="pb-ws__toolbar-left">
            <div className="pb-ws__project">
              <Select
                id="pb-project"
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
            <div className="pb-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="pb-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="pb-undo"
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="pb-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="pb-redo"
                onClick={() => showToast(t('toasts.redo'))}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
            </div>
          </div>
          <div className="pb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <PbZoomToolbar
              engine={ftv}
              canvasLocked={canvasLocked}
              onToggleLock={() => setCanvasLocked((v) => !v)}
              isFullscreen={focus.isFullscreen}
              onToggleFullscreen={focus.toggleFullscreen}
            />
          </div>
        </div>

        <div
          className="pb-ws__ai-status is-live"
          role="status"
          aria-live="polite"
          data-testid="pb-ai-status"
        >
          <span className="pb-ws__ai-status-dot" aria-hidden="true" />
          <span>{t('aiStatus.completed')}</span>
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="pb-ws__layout"
          leftRail={pbLeftRail}
          rightRail={pbRightRail}
          onLeftRailSelect={(id) => {
            if ((PB_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as PbLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((PB_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as PbRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section
              className="pb-ws__panel pb-ws__center"
              aria-label={t('canvas.aria')}
              data-testid="pb-center"
            >
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="pb-canvas-stage"
                toolbar={
                  <div className="pb-ws__center-head">
                    <div
                      className="pb-ws__format-tabs"
                      role="group"
                      aria-label={t('canvas.aspectRatio')}
                      data-testid="pb-aspect-ratio"
                    >
                      {ASPECT_RATIOS.map((ratio) => (
                        <button
                          key={ratio}
                          type="button"
                          className={`pb-ws__format-tab${aspectRatio === ratio ? ' is-active' : ''}`}
                          aria-pressed={aspectRatio === ratio}
                          data-testid={`pb-format-${ratio.replace(':', '-')}`}
                          onClick={() => {
                            setAspectRatio(ratio);
                            markDirty();
                          }}
                        >
                          {ratio}
                        </button>
                      ))}
                    </div>
                  </div>
                }
                dock={{
                  testId: 'pb-scene-actions',
                  className: 'pb-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="pb-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      primary={{
                        label: t('bottomBar.actions.addSlide'),
                        icon: BOTTOM_ACTION_ICONS.addSlide,
                        onClick: () => handleBottomAction('addSlide'),
                        testId: 'pb-action-addSlide',
                      }}
                      actions={BOTTOM_COMPONENT_ACTIONS.map((action) => ({
                        key: action,
                        icon: BOTTOM_ACTION_ICONS[action],
                        label: t(`bottomBar.actions.${action}`),
                        onClick: () => handleBottomAction(action),
                        testId: `pb-action-${action}`,
                      }))}
                    />
                  ),
                }}
              >
                <div className="pb-ws__preview-shell" data-testid="pb-preview-shell">
                  {viewMode === 'slide' ? (
                    <div className="pb-ws__preview-mat" data-testid="pb-preview-mat">
                      <div
                        className="pb-ws__floating-actions"
                        data-testid="pb-floating-actions"
                        onMouseDown={(e) => e.stopPropagation()}
                      >
                        {FLOATING_ACTIONS.map((action) => (
                          <button
                            key={action}
                            type="button"
                            className="pb-ws__floating-btn"
                            ref={action === 'more' ? floatingMoreRef : undefined}
                            aria-expanded={action === 'more' ? floatingMoreOpen : undefined}
                            data-testid={`pb-floating-${action}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleFloatingAction(action);
                            }}
                          >
                            <IhIcon name={FLOATING_ACTION_ICONS[action]} size={11} />
                            {t(`floating.${action}`)}
                          </button>
                        ))}
                      </div>
                      <FocusFitStage engine={ftv} artboardTestId="pb-slide-preview">
                        <div
                          className={`pb-ws__slide-stage ${aspectClass(aspectRatio)}`}
                          data-aspect={aspectRatio}
                        >
                          <div className="pb-ws__slide-canvas">
                            <div className="pb-ws__slide-copy">
                              <span className="pb-ws__slide-badge">{project.featuredLabel}</span>
                              <p className="pb-ws__slide-kicker">{t('canvas.coverKicker')}</p>
                              <h2>
                                {selectedIndex === 0
                                  ? brief.topic
                                  : t(`slides.${selectedSlide.kind}.title`)}
                              </h2>
                              <p className="pb-ws__slide-sub">
                                {selectedIndex === 0
                                  ? t('canvas.coverSubtitle')
                                  : t(`slides.${selectedSlide.kind}.body`)}
                              </p>
                              {selectedIndex === 0 ? (
                                <button type="button" className="pb-ws__slide-cta">
                                  {brief.cta}
                                </button>
                              ) : null}
                            </div>
                            <div className="pb-ws__slide-media">
                              <img
                                src={
                                  selectedIndex === 0
                                    ? coverAsset.coverDisplayUrl
                                    : selectedSlide.thumbUrl
                                }
                                alt={t('canvas.previewAlt')}
                              />
                            </div>
                          </div>
                          {showSlideNumber ? (
                            <span className="pb-ws__slide-count" data-testid="pb-ready-badge">
                              {selectedIndex + 1} / {slides.length}
                            </span>
                          ) : null}
                        </div>
                      </FocusFitStage>
                    </div>
                  ) : (
                    <div className="pb-ws__outline" data-testid="pb-outline-view">
                      {slides.map((slide, index) => (
                        <button
                          key={slide.id}
                          type="button"
                          className={`pb-ws__outline-row${selectedSlideId === slide.id ? ' is-selected' : ''}`}
                          onClick={() => setSelectedSlideId(slide.id)}
                        >
                          <strong>
                            {index + 1}. {t(`slides.${slide.kind}.title`)}
                          </strong>
                          <span>{t(`slides.${slide.kind}.body`)}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </FocusCanvasLayout>
            </section>
          }
          right={rightDrawer}
        />
      </div>

      {floatingMoreOpen && moreMenuPos && typeof document !== 'undefined'
        ? createPortal(
            <div
              className="pb-ws__floating-menu pb-ws__floating-menu--portal"
              role="menu"
              style={{ top: moreMenuPos.top, left: moreMenuPos.left }}
              onMouseDown={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setLeftRailId('layouts');
                  setFloatingMoreOpen(false);
                  showToast(t('bottomBar.toasts.layout'));
                }}
              >
                {t('canvas.actions.changeStyle')}
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  duplicateSlide(selectedSlide.id);
                  setFloatingMoreOpen(false);
                }}
              >
                {t('canvas.actions.duplicate')}
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  coverAsset.openPicker('cover');
                  setFloatingMoreOpen(false);
                }}
              >
                {t('canvas.actions.replaceImage')}
              </button>
            </div>,
            document.body,
          )
        : null}

      {aiPresenting ? (
        <div
          className="pb-ws__ai-present"
          role="dialog"
          aria-modal="true"
          aria-label={t('aiPresent.title')}
          data-testid="pb-ai-present-overlay"
        >
          <div className="pb-ws__ai-present-bar">
            <div className="pb-ws__ai-present-meta">
              <StatusChip tone="info">{t('aiPresent.badge')}</StatusChip>
              <span>
                {aiPresentIndex + 1} / {slides.length}
              </span>
              <strong>{t(`slides.${presentSlide.kind}.title`)}</strong>
            </div>
            <Button variant="secondary" size="sm" data-testid="pb-ai-present-stop" onClick={stopAiPresent}>
              {t('aiPresent.stop')}
            </Button>
          </div>
          <div className={`pb-ws__ai-present-stage ${aspectClass(aspectRatio)}`}>
            <div className="pb-ws__slide-canvas">
              <div className="pb-ws__slide-copy">
                <span className="pb-ws__slide-badge">{project.featuredLabel}</span>
                <p className="pb-ws__slide-kicker">{t('aiPresent.kicker')}</p>
                <h2>
                  {aiPresentIndex === 0 ? brief.topic : t(`slides.${presentSlide.kind}.title`)}
                </h2>
                <p className="pb-ws__slide-sub">
                  {aiPresentIndex === 0
                    ? t('canvas.coverSubtitle')
                    : t(`slides.${presentSlide.kind}.body`)}
                </p>
              </div>
              <div className="pb-ws__slide-media">
                <img src={presentSlide.thumbUrl} alt="" />
              </div>
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
            coverAsset.setCoverImage(ref);
            coverAsset.closePicker();
            if (ref.asset_id) {
              void coverAsset.media.ensureDisplayUrl(ref.asset_id).then((url) => {
                if (!url) return;
                setSlides((prev) =>
                  prev.map((s) => (s.id === selectedSlideId ? { ...s, thumbUrl: url } : s)),
                );
              });
            }
            markDirty();
            showToast(t('toasts.toolbar.replaceImage'));
          }}
          testId="pb-media-picker-dialog"
        />
      ) : null}

      {toast ? (
        <div className="pb-ws__toast" role="status" data-testid="pb-toast">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
