'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  AI_PROGRESS_STEPS,
  AI_STATUS_SEQUENCE,
  CAMPAIGN_STATUS_TONE,
  COLLECTIONS,
  DEFAULT_BRIEF,
  DEFAULT_HISTORY,
  DEFAULT_IMAGE_DETAILS,
  DEFAULT_LAYERS,
  DEFAULT_PRINT_EXPORT,
  DEFAULT_VARIATIONS,
  IB_BOTTOM_ACTIONS,
  IB_BOTTOM_ACTION_ICONS,
  IB_FLOATING_ACTIONS,
  IB_HOME,
  IB_LEFT_RAIL_ICONS,
  IB_LEFT_RAIL_IDS,
  IB_PROJECTS,
  IB_RIGHT_RAIL_ICONS,
  IB_RIGHT_RAIL_IDS,
  aspectClass,
  evaluatePrintQuality,
  getProject,
  resolveOutputPixels,
  type AiStatusKey,
  type AspectRatio,
  type CampaignStatus,
  type DigitalPresetKey,
  type IbAiToolKey,
  type IbBgTool,
  type IbBottomAction,
  type IbEditTool,
  type IbFloatingAction,
  type IbLayer,
  type IbLeftRailId,
  type IbRightRailId,
  type IbVariation,
  type ImageBrief,
  type PrintExportState,
  type ProjectId,
} from './image-builder-model';

import {
  IbLeftRailDrawer,
  IbLocalRail,
  IbRightRailDrawer,
  IbZoomToolbar,
} from './image-builder-rail-drawers';

import { CsBottomActionToolbar } from '../_components';
import {
  CreativeStudioFocusModeSwitcher,
  CreativeStudioFocusWorkspace,
  FocusCanvasLayout,
  FocusFitStage,
  useCreativeStudioFocusMode,
  useFitToViewEngine,
  type FocusRailItem,
} from '../_components/focus-workspace';

import './image-builder.css';

export function ImageBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.imageBuilder');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');

  const [hydrated, setHydrated] = useState(false);
  const [projectId, setProjectId] = useState<ProjectId>('temple');
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus>('ready');
  const [saved, setSaved] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [aiStatus, setAiStatus] = useState<AiStatusKey>('completed');
  const [progressStep, setProgressStep] = useState(-1);
  const [brief, setBrief] = useState<ImageBrief>(DEFAULT_BRIEF);
  const [leftRailId, setLeftRailId] = useState<IbLeftRailId>('generate');
  const [rightRailId, setRightRailId] = useState<IbRightRailId>('aiTools');
  const focus = useCreativeStudioFocusMode({ storageKey: 'image-builder' });

  const [variations, setVariations] = useState<IbVariation[]>(DEFAULT_VARIATIONS);
  const [selectedVariationId, setSelectedVariationId] = useState('v1');
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [printExport, setPrintExport] = useState<PrintExportState>(DEFAULT_PRINT_EXPORT);
  const [digitalPreset, setDigitalPreset] = useState<DigitalPresetKey>('websiteHero');
  const [collection, setCollection] = useState<(typeof COLLECTIONS)[number]>('exteriorRenders');
  const [toast, setToast] = useState<string | null>(null);
  const [floatingMoreOpen, setFloatingMoreOpen] = useState(false);
  const [ctxMenuId, setCtxMenuId] = useState<string | null>(null);
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [selected, setSelected] = useState(true);

  const [model, setModel] = useState('ihVision');
  const [quality, setQuality] = useState('high');
  const [imageCount, setImageCount] = useState(4);
  const [editTool, setEditTool] = useState<IbEditTool>('brush');
  const [variationStrength, setVariationStrength] = useState(55);
  const [variationSeed, setVariationSeed] = useState(DEFAULT_BRIEF.seed);
  const [similarity, setSimilarity] = useState(72);
  const [upscaleFactor, setUpscaleFactor] = useState('2x');
  const [faceEnhance, setFaceEnhance] = useState(true);
  const [sharpen, setSharpen] = useState(false);
  const [bgTool, setBgTool] = useState<IbBgTool>('remove');
  const [textContent, setTextContent] = useState('THE TEMPLE');
  const [textFont, setTextFont] = useState('Inter');
  const [textSize, setTextSize] = useState(32);
  const [textAlign, setTextAlign] = useState('center');
  const [layers, setLayers] = useState<IbLayer[]>(DEFAULT_LAYERS);
  const [selectedLayerId, setSelectedLayerId] = useState('l2');
  const [details] = useState(DEFAULT_IMAGE_DETAILS);
  const [history] = useState(DEFAULT_HISTORY);

  const filmstripRef = useRef<HTMLDivElement | null>(null);
  const genTimerRef = useRef<number[]>([]);

  const project = useMemo(() => getProject(projectId), [projectId]);
  const selectedVariation =
    variations.find((v) => v.id === selectedVariationId) ?? variations[0]!;
  const previewClass = aspectClass(aspectRatio);
  const printValidation = useMemo(
    () => evaluatePrintQuality(printExport, aspectRatio),
    [printExport, aspectRatio],
  );
  const outputPixels = useMemo(
    () => resolveOutputPixels(printExport, aspectRatio),
    [printExport, aspectRatio],
  );
  const [imgContentW, imgContentH] = outputPixels;

  // Local IB padding only — do not change shared FTV defaults.
  // Extra padY keeps selection handles + floating toolbar inside the grey stage.
  const ibFitPadX = focus.isFullscreen ? 16 : 24;
  const ibFitPadY = focus.isFullscreen ? 16 : 32;

  const ftv = useFitToViewEngine({
    contentWidth: Math.max(1, imgContentW),
    contentHeight: Math.max(1, imgContentH),
    enabled: true,
    contentKey: `${aspectRatio}-${selectedVariationId}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}-${ibFitPadX}x${ibFitPadY}`,
    canvasType: 'artwork',
    padX: ibFitPadX,
    padY: ibFitPadY,
    cssWidthVar: '--ib-stage-w',
    cssHeightVar: '--ib-stage-h',
  });

  const ibLeftRail: FocusRailItem[] = useMemo(
    () =>
      IB_LEFT_RAIL_IDS.map((id) => ({
        id,
        icon: IB_LEFT_RAIL_ICONS[id],
        labelKey: 'brief',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const ibRightRail: FocusRailItem[] = useMemo(
    () =>
      IB_RIGHT_RAIL_IDS.map((id) => ({
        id,
        icon: IB_RIGHT_RAIL_ICONS[id],
        labelKey: 'export',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const localLeftItems = useMemo(
    () => ibLeftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [ibLeftRail],
  );
  const localRightItems = useMemo(
    () => ibRightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [ibRightRail],
  );

  useEffect(() => {
    if (ftv.autoFit) ftv.fitToView();
    else ftv.refit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.mode, focus.isFullscreen, aspectRatio, selectedVariationId, ibFitPadX, ibFitPadY]);

  useEffect(() => {
    setHydrated(true);
    return () => {
      genTimerRef.current.forEach((id) => window.clearTimeout(id));
    };
  }, []);

  useEffect(() => {
    if (!floatingMoreOpen && !ctxMenuId) return;
    function onDocPointer() {
      setFloatingMoreOpen(false);
      setCtxMenuId(null);
    }
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        setFloatingMoreOpen(false);
        setCtxMenuId(null);
      }
    }
    document.addEventListener('mousedown', onDocPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [floatingMoreOpen, ctxMenuId]);

  function patchPrint(patch: Partial<PrintExportState>) {
    setPrintExport((prev) => ({ ...prev, ...patch }));
    setSaved(false);
  }

  function markDirty() {
    setSaved(false);
  }

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  function persistNow(announce = false) {
    setSaved(true);
    if (announce) showToast(t('toasts.saved'));
  }

  function clearGenTimers() {
    genTimerRef.current.forEach((id) => window.clearTimeout(id));
    genTimerRef.current = [];
  }

  function handleGenerate() {
    clearGenTimers();
    setGenerating(true);
    setProgressStep(0);
    setAiStatus('thinking');
    setCampaignStatus('draft');
    setLeftRailId('generate');

    AI_STATUS_SEQUENCE.forEach((status, index) => {
      const id = window.setTimeout(() => {
        setAiStatus(status);
        setProgressStep(Math.min(index, AI_PROGRESS_STEPS.length - 1));
        if (status === 'completed') {
          setGenerating(false);
          setProgressStep(AI_PROGRESS_STEPS.length);
          setCampaignStatus('ready');
          setVariations((prev) => [...prev].reverse());
          persistNow();
          showToast(t('toasts.generated'));
        }
      }, 380 * (index + 1));
      genTimerRef.current.push(id);
    });
  }

  function handleAiTool(key: IbAiToolKey) {
    showToast(t(`rails.aiTools.tools.${key}.title`));
  }

  function handleFloating(action: IbFloatingAction | 'more') {
    if (action === 'edit') {
      setLeftRailId('edit');
      showToast(t('floating.edit'));
      return;
    }
    if (action === 'variation') {
      setLeftRailId('variation');
      handleGenerate();
      return;
    }
    if (action === 'upscale') {
      setLeftRailId('upscale');
      showToast(t('toasts.upscaled'));
      return;
    }
    if (action === 'delete') {
      showToast(t('floating.delete'));
      setSelected(false);
      return;
    }
    setFloatingMoreOpen((v) => !v);
  }

  function handleBottomAction(action: IbBottomAction) {
    if (action === 'newImage') {
      setLeftRailId('generate');
      handleGenerate();
      return;
    }
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function scrollFilmstrip(dir: -1 | 1) {
    const el = filmstripRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 160, behavior: 'smooth' });
  }

  const leftDrawerContent = (
    <IbLeftRailDrawer
      id={leftRailId}
      brief={brief}
      setBrief={setBrief}
      aspectRatio={aspectRatio}
      setAspectRatio={setAspectRatio}
      model={model}
      setModel={setModel}
      quality={quality}
      setQuality={setQuality}
      imageCount={imageCount}
      setImageCount={setImageCount}
      editTool={editTool}
      setEditTool={setEditTool}
      variationStrength={variationStrength}
      setVariationStrength={setVariationStrength}
      variationSeed={variationSeed}
      setVariationSeed={setVariationSeed}
      similarity={similarity}
      setSimilarity={setSimilarity}
      upscaleFactor={upscaleFactor}
      setUpscaleFactor={setUpscaleFactor}
      faceEnhance={faceEnhance}
      setFaceEnhance={setFaceEnhance}
      sharpen={sharpen}
      setSharpen={setSharpen}
      bgTool={bgTool}
      setBgTool={setBgTool}
      textContent={textContent}
      setTextContent={setTextContent}
      textFont={textFont}
      setTextFont={setTextFont}
      textSize={textSize}
      setTextSize={setTextSize}
      textAlign={textAlign}
      setTextAlign={setTextAlign}
      layers={layers}
      setLayers={setLayers}
      selectedLayerId={selectedLayerId}
      setSelectedLayerId={setSelectedLayerId}
      generating={generating}
      onGenerate={handleGenerate}
      onToast={showToast}
      markDirty={markDirty}
    />
  );

  const rightDrawerContent = (
    <IbRightRailDrawer
      id={rightRailId}
      layers={layers}
      setLayers={setLayers}
      selectedLayerId={selectedLayerId}
      setSelectedLayerId={setSelectedLayerId}
      details={{
        ...details,
        aspectRatio,
        resolution: `${outputPixels[0]} × ${outputPixels[1]}`,
      }}
      history={history}
      printExport={printExport}
      patchPrint={patchPrint}
      printValidation={printValidation}
      outputPixels={outputPixels}
      digitalPreset={digitalPreset}
      setDigitalPreset={setDigitalPreset}
      collection={collection}
      setCollection={setCollection}
      onAiTool={handleAiTool}
      onDownload={() => {
        setCampaignStatus('exported');
        showToast(t('toasts.downloaded'));
      }}
      onToast={showToast}
      markDirty={markDirty}
    />
  );

  const leftDrawer =
    focus.isFocus || focus.isFullscreen ? (
      leftDrawerContent
    ) : (
      <div className="ib-ws__panel ib-ws__left" aria-label={t('left.aria')} data-testid="ib-left">
        <IbLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as IbLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="ib-ws__panel ib-ws__right" aria-label={t('right.aria')} data-testid="ib-right">
        <IbLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as IbRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="ib-workspace-loading">
        <div className="ib-ws">
          <div className="ib-ws__skeleton" aria-hidden="true" />
        </div>
      </main>
    );
  }

  const coverSrc =
    selectedVariationId === 'v1' ? project.coverUrl : selectedVariation.thumbUrl;

  return (
    <main className="dashboard" data-testid="ib-workspace">
      <div
        className="ib-ws"
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
      >
        <header className="ib-ws__header cs-page-header">
          <div className="ib-ws__header-copy cs-page-header__copy">
            <Link href={IB_HOME as Route} className="ib-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="ib-ws__breadcrumb">
                <li>
                  <Link href={IB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="ib-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="ib-ws__breadcrumb-current" aria-current="page">
                  {tTools('imageStudio.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="design" size={20} />
              {tTools('imageStudio.title')}
            </h1>
            <p className="ib-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="ib-ws__header-meta cs-page-header__meta">
            <StatusChip tone={saved ? 'success' : 'default'}>
              {saved ? t('savedAgo') : t('draft')}
            </StatusChip>
            <StatusChip tone={CAMPAIGN_STATUS_TONE[campaignStatus]}>
              {t(`status.${campaignStatus}`)}
            </StatusChip>
          </div>
        </header>

        <div className="ib-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="ib-ws__toolbar-left">
            <div className="ib-ws__project">
              <Select
                id="ib-project"
                label={t('fields.project')}
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value as ProjectId);
                  markDirty();
                }}
              >
                {IB_PROJECTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div className="ib-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <div className="ib-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="ib-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="ib-undo"
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="ib-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="ib-redo"
                onClick={() => showToast(t('toasts.redo'))}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
              <button
                type="button"
                className={`ib-ws__icon-btn${focus.isFullscreen ? ' is-active' : ''}`}
                aria-label={t('canvas.fullscreen')}
                aria-pressed={focus.isFullscreen}
                data-testid="ib-fullscreen"
                onClick={focus.toggleFullscreen}
              >
                <IhIcon name="target" size={12} />
              </button>
            </div>
            <Button variant="secondary" size="sm" onClick={() => persistNow(true)} data-testid="ib-save">
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="ib-preview"
              onClick={() => showToast(t('toasts.preview'))}
            >
              {t('preview')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="ib-download-toolbar"
              onClick={() => {
                setRightRailId('export');
                setCampaignStatus('exported');
                showToast(t('toasts.downloaded'));
              }}
            >
              {t('download')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={generating}
              data-testid="ib-generate-toolbar"
              onClick={handleGenerate}
            >
              <IhIcon name="sparkles" size={12} />
              {generating ? t('generating') : t('generateToolbar')}
            </Button>
          </div>
        </div>

        <div
          className={`ib-ws__ai-status${generating || aiStatus !== 'idle' ? ' is-live' : ''}`}
          role="status"
          aria-live="polite"
          data-testid="ib-ai-status"
        >
          <span className="ib-ws__ai-status-dot" aria-hidden="true" />
          <span>{aiStatus === 'idle' ? t('aiStatus.idle') : t(`aiStatus.${aiStatus}`)}</span>
          {generating ? (
            <span className="ib-ws__ai-status-progress">
              {progressStep + 1}/{AI_PROGRESS_STEPS.length}
            </span>
          ) : null}
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="ib-ws__layout"
          leftRail={ibLeftRail}
          rightRail={ibRightRail}
          onLeftRailSelect={(id) => {
            if ((IB_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as IbLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((IB_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as IbRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section
              className="ib-ws__panel ib-ws__center"
              aria-label={t('canvas.aria')}
              data-testid="ib-center"
            >
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="ib-canvas-stage"
                toolbar={
                  <div className="ib-ws__center-head">
                    <h2>{t('canvas.title')}</h2>
                    <div
                      className="ib-ws__view-controls"
                      role="toolbar"
                      aria-label={t('canvas.viewAria')}
                    >
                      <IbZoomToolbar
                        engine={ftv}
                        aspectRatio={aspectRatio}
                        onAspectChange={(v) => {
                          setAspectRatio(v);
                          markDirty();
                        }}
                        canvasLocked={canvasLocked}
                        onToggleLock={() => setCanvasLocked((v) => !v)}
                      />
                      <button
                        type="button"
                        className={`ib-ws__icon-btn${focus.isFullscreen ? ' is-active' : ''}`}
                        aria-label={t('canvas.fullscreen')}
                        aria-pressed={focus.isFullscreen}
                        data-testid="ib-fullscreen-canvas"
                        onClick={focus.toggleFullscreen}
                      >
                        <IhIcon name="target" size={12} />
                      </button>
                    </div>
                  </div>
                }
                tray={{
                  label: tFocus('tray.variations'),
                  count: variations.length,
                  testId: 'ib-variations',
                  handleTestId: 'ib-tray-handle',
                  content: (
                    <div className="ib-ws__filmstrip" data-testid="ib-filmstrip">
                      <button
                        type="button"
                        className="ib-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripPrev')}
                        data-testid="ib-filmstrip-prev"
                        onClick={() => scrollFilmstrip(-1)}
                      >
                        <IhIcon name="chevronLeft" size={14} />
                      </button>
                      <div className="ib-ws__variation-row" ref={filmstripRef} data-testid="ib-variation-row">
                        {variations.map((variation) => (
                          <div key={variation.id} className="ib-ws__variation-wrap">
                            <button
                              type="button"
                              className={`ib-ws__variation-card${selectedVariationId === variation.id ? ' is-selected' : ''}`}
                              onClick={() => setSelectedVariationId(variation.id)}
                              onContextMenu={(e) => {
                                e.preventDefault();
                                setCtxMenuId(variation.id);
                              }}
                              data-testid={`ib-variation-${variation.id}`}
                            >
                              <img src={variation.thumbUrl} alt="" />
                              <span>{variation.label}</span>
                            </button>
                            {ctxMenuId === variation.id ? (
                              <div className="ib-ws__ctx-menu" role="menu">
                                <button
                                  type="button"
                                  role="menuitem"
                                  onClick={() => {
                                    setSelectedVariationId(variation.id);
                                    setCtxMenuId(null);
                                    showToast(t('canvas.ctx.select'));
                                  }}
                                >
                                  {t('canvas.ctx.select')}
                                </button>
                                <button
                                  type="button"
                                  role="menuitem"
                                  onClick={() => {
                                    setLeftRailId('variation');
                                    setCtxMenuId(null);
                                    handleGenerate();
                                  }}
                                >
                                  {t('canvas.ctx.vary')}
                                </button>
                                <button
                                  type="button"
                                  role="menuitem"
                                  onClick={() => {
                                    setCtxMenuId(null);
                                    showToast(t('canvas.ctx.download'));
                                  }}
                                >
                                  {t('canvas.ctx.download')}
                                </button>
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                      <button
                        type="button"
                        className="ib-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripNext')}
                        data-testid="ib-filmstrip-next"
                        onClick={() => scrollFilmstrip(1)}
                      >
                        <IhIcon name="chevronRight" size={14} />
                      </button>
                    </div>
                  ),
                }}
                dock={{
                  testId: 'ib-scene-actions',
                  className: 'ib-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="ib-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      primary={{
                        label: t('bottomBar.actions.newImage'),
                        icon: IB_BOTTOM_ACTION_ICONS.newImage,
                        onClick: () => handleBottomAction('newImage'),
                        testId: 'ib-action-newImage',
                      }}
                      actions={IB_BOTTOM_ACTIONS.filter((a) => a !== 'newImage').map((action) => ({
                        key: action,
                        icon: IB_BOTTOM_ACTION_ICONS[action],
                        label: t(`bottomBar.actions.${action}`),
                        onClick: () => handleBottomAction(action),
                        testId: `ib-action-${action}`,
                      }))}
                    />
                  ),
                }}
              >
                <div className="ib-ws__preview-shell" data-testid="ib-preview-shell">
                  <div className="ib-ws__preview-mat" data-testid="ib-preview-mat">
                    <FocusFitStage engine={ftv} artboardTestId="ib-image-preview">
                      <div
                        className={`ib-ws__preview ${previewClass}`}
                        data-locked={canvasLocked ? 'true' : 'false'}
                        onClick={() => setSelected(true)}
                      >
                        <div className="ib-ws__preview-stage">
                          <img src={coverSrc} alt={t('canvas.previewAlt')} />
                        </div>

                        {selected ? (
                          <>
                            <span className="ib-ws__selection" aria-hidden="true">
                              <i className="ib-ws__handle ib-ws__handle--nw" />
                              <i className="ib-ws__handle ib-ws__handle--ne" />
                              <i className="ib-ws__handle ib-ws__handle--sw" />
                              <i className="ib-ws__handle ib-ws__handle--se" />
                              <i className="ib-ws__handle ib-ws__handle--n" />
                              <i className="ib-ws__handle ib-ws__handle--s" />
                              <i className="ib-ws__handle ib-ws__handle--e" />
                              <i className="ib-ws__handle ib-ws__handle--w" />
                            </span>
                            <span className="ib-ws__guide ib-ws__guide--v" aria-hidden="true" />
                            <span className="ib-ws__guide ib-ws__guide--h" aria-hidden="true" />

                            <div
                              className="ib-ws__floating-actions"
                              data-testid="ib-floating-actions"
                              onMouseDown={(e) => e.stopPropagation()}
                            >
                              {IB_FLOATING_ACTIONS.map((action) => (
                                <button
                                  key={action}
                                  type="button"
                                  className="ib-ws__floating-btn"
                                  data-testid={`ib-floating-${action}`}
                                  onClick={() => handleFloating(action)}
                                >
                                  <IhIcon
                                    name={
                                      action === 'edit'
                                        ? 'design'
                                        : action === 'variation'
                                          ? 'sparkles'
                                          : action === 'upscale'
                                            ? 'trendingUp'
                                            : 'alert'
                                    }
                                    size={11}
                                  />
                                  {t(`floating.${action}`)}
                                </button>
                              ))}
                              <div className="ib-ws__floating-more">
                                <button
                                  type="button"
                                  className="ib-ws__floating-btn"
                                  aria-expanded={floatingMoreOpen}
                                  data-testid="ib-floating-more"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setFloatingMoreOpen((v) => !v);
                                  }}
                                >
                                  <IhIcon name="quickAction" size={11} />
                                  {t('floating.more')}
                                </button>
                                {floatingMoreOpen ? (
                                  <div className="ib-ws__floating-menu" role="menu">
                                    <button
                                      type="button"
                                      role="menuitem"
                                      onClick={() => {
                                        setLeftRailId('background');
                                        setFloatingMoreOpen(false);
                                      }}
                                    >
                                      {t('floating.menu.background')}
                                    </button>
                                    <button
                                      type="button"
                                      role="menuitem"
                                      onClick={() => {
                                        setRightRailId('export');
                                        setFloatingMoreOpen(false);
                                      }}
                                    >
                                      {t('floating.menu.export')}
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
                                  </div>
                                ) : null}
                              </div>
                            </div>
                          </>
                        ) : null}

                        <span className="ib-ws__ready-badge" data-testid="ib-ready-badge">
                          {t('canvas.ready')}
                        </span>
                        <div className="ib-ws__preview-caption">
                          <span className="ib-ws__preview-project">{project.featuredLabel}</span>
                          <p>{t('canvas.caption')}</p>
                        </div>
                      </div>
                    </FocusFitStage>
                  </div>
                </div>
              </FocusCanvasLayout>
            </section>
          }
          right={rightDrawer}
        />
      </div>

      {toast ? (
        <div className="ib-ws__toast" role="status" data-testid="ib-toast">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
