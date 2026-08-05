'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  ADS_HOME,
  ADS_LEFT_RAIL_ICONS,
  ADS_LEFT_RAIL_IDS,
  ADS_PROJECTS,
  ADS_RIGHT_RAIL_ICONS,
  ADS_RIGHT_RAIL_IDS,
  BOTTOM_ACTIONS,
  CAMPAIGN_STATUS_TONE,
  DEFAULT_ADS,
  FLOATING_ACTIONS,
  FORMAT_PRESETS,
  PLATFORM_OPTIONS,
  aspectThumbClass,
  createAdFromFormat,
  getProject,
  resolveFormatSize,
  type AdCreative,
  type AdFormatKey,
  type AdsLeftRailId,
  type AdsRightRailId,
  type BgMode,
  type BottomActionKey,
  type CampaignStatus,
  type FloatingActionKey,
  type PlatformKey,
  type ProjectId,
} from './ads-builder-model';

import {
  AdsLeftRailDrawer,
  AdsLocalRail,
  AdsRightRailDrawer,
  AdsZoomToolbar,
} from './ads-builder-rail-drawers';

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

import './ads-builder.css';

export function AdsBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  const [hydrated, setHydrated] = useState(false);
  const [projectId, setProjectId] = useState<ProjectId>('temple');
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus>('ready');
  const [saved, setSaved] = useState(true);
  const [leftRailId, setLeftRailId] = useState<AdsLeftRailId>('ads');
  const [rightRailId, setRightRailId] = useState<AdsRightRailId>('content');
  const focus = useCreativeStudioFocusMode({ storageKey: 'ads-builder' });

  const [ads, setAds] = useState<AdCreative[]>(DEFAULT_ADS);
  const [selectedAdId, setSelectedAdId] = useState('a1');
  const [formatPreset, setFormatPreset] = useState<AdFormatKey>('square');
  const [activePlatform, setActivePlatform] = useState<PlatformKey>('facebook');
  const [brandLogo, setBrandLogo] = useState(true);
  const [bgMode, setBgMode] = useState<BgMode>('image');
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [selected, setSelected] = useState(true);
  const [floatingMoreOpen, setFloatingMoreOpen] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const filmstripRef = useRef<HTMLDivElement | null>(null);

  const project = useMemo(() => getProject(projectId), [projectId]);
  const selectedAd = ads.find((a) => a.id === selectedAdId) ?? ads[0]!;
  const contentSize = resolveFormatSize(formatPreset);

  const adsFitPadX = focus.isFullscreen ? 16 : 28;
  const adsFitPadY = focus.isFullscreen ? 16 : 36;

  const ftv = useFitToViewEngine({
    contentWidth: Math.max(1, contentSize.w),
    contentHeight: Math.max(1, contentSize.h),
    enabled: true,
    contentKey: `${formatPreset}-${selectedAd.id}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}-${adsFitPadX}x${adsFitPadY}`,
    canvasType: 'artwork',
    padX: adsFitPadX,
    padY: adsFitPadY,
    cssWidthVar: '--ads-stage-w',
    cssHeightVar: '--ads-stage-h',
  });

  const adsLeftRail: FocusRailItem[] = useMemo(
    () =>
      ADS_LEFT_RAIL_IDS.map((id) => ({
        id,
        icon: ADS_LEFT_RAIL_ICONS[id],
        labelKey: 'brief',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const adsRightRail: FocusRailItem[] = useMemo(
    () =>
      ADS_RIGHT_RAIL_IDS.map((id) => ({
        id,
        icon: ADS_RIGHT_RAIL_ICONS[id],
        labelKey: 'export',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const localLeftItems = useMemo(
    () => adsLeftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [adsLeftRail],
  );
  const localRightItems = useMemo(
    () => adsRightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [adsRightRail],
  );

  useEffect(() => {
    if (ftv.autoFit) ftv.fitToView();
    else ftv.refit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.mode, focus.isFullscreen, formatPreset, selectedAdId, adsFitPadX, adsFitPadY]);

  useEffect(() => {
    setHydrated(true);
  }, []);

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

  function persistNow(announce = false) {
    setSaved(true);
    if (announce) showToast(t('toasts.saved'));
  }

  function patchAd(patch: Partial<AdCreative>) {
    setAds((prev) => prev.map((a) => (a.id === selectedAd.id ? { ...a, ...patch } : a)));
  }

  function selectAd(ad: AdCreative) {
    setSelectedAdId(ad.id);
    setFormatPreset(ad.format);
    setActivePlatform(ad.platform);
    setSelected(true);
  }

  function handlePlatformChange(key: PlatformKey) {
    setActivePlatform(key);
    patchAd({ platform: key });
    markDirty();
  }

  function handleFormatChange(key: AdFormatKey) {
    setFormatPreset(key);
    const size = resolveFormatSize(key);
    patchAd({ format: key, width: size.w, height: size.h });
    markDirty();
    const match = ads.find((a) => a.format === key && a.platform === activePlatform);
    if (match) setSelectedAdId(match.id);
  }

  function addAd() {
    const next = createAdFromFormat(formatPreset, ads.length + 1, project.coverUrl, activePlatform);
    setAds((prev) => [...prev, next]);
    setSelectedAdId(next.id);
    setLeftRailId('ads');
    markDirty();
    showToast(t('toasts.adAdded'));
  }

  function handleFloating(action: FloatingActionKey | 'more') {
    if (action === 'more') {
      setFloatingMoreOpen((v) => !v);
      return;
    }
    if (action === 'delete') {
      setSelected(false);
      showToast(t('floating.delete'));
      return;
    }
    if (action === 'edit') {
      setRightRailId('content');
      showToast(t('floating.edit'));
      return;
    }
    if (action === 'copy') {
      const clone: AdCreative = {
        ...selectedAd,
        id: `a-copy-${Date.now()}`,
        name: `${selectedAd.name} (copy)`,
        status: 'draft',
      };
      setAds((prev) => [...prev, clone]);
      setSelectedAdId(clone.id);
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
    if (action === 'audience') {
      setRightRailId('targeting');
      showToast(t('bottomBar.toasts.audience'));
      return;
    }
    if (action === 'pixel') {
      setRightRailId('pixel');
      showToast(t('bottomBar.toasts.pixel'));
      return;
    }
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function handleApplyTemplate(format: AdFormatKey, thumbUrl: string) {
    setFormatPreset(format);
    const size = resolveFormatSize(format);
    patchAd({ format, width: size.w, height: size.h, thumbUrl });
    markDirty();
    showToast(t('toasts.templateApplied'));
  }

  function handleInsertComponent(key: string) {
    showToast(
      t('rails.components.toasts.inserted', {
        name: t(`rails.components.items.${key}` as 'rails.components.items.text'),
      }),
    );
  }

  function scrollFilmstrip(dir: -1 | 1) {
    const el = filmstripRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 160, behavior: 'smooth' });
  }

  const leftDrawerContent = (
    <AdsLeftRailDrawer
      id={leftRailId}
      ads={ads}
      selectedAdId={selectedAdId}
      onSelectAd={selectAd}
      onAddAd={addAd}
      onInsertComponent={handleInsertComponent}
      onApplyTemplate={handleApplyTemplate}
      onToast={showToast}
    />
  );

  const rightDrawerContent = (
    <AdsRightRailDrawer
      id={rightRailId}
      onSelectTab={setRightRailId}
      ad={selectedAd}
      patchAd={patchAd}
      brandLogo={brandLogo}
      setBrandLogo={setBrandLogo}
      bgMode={bgMode}
      setBgMode={setBgMode}
      markDirty={markDirty}
      onToast={showToast}
    />
  );

  const leftDrawer =
    focus.isFocus || focus.isFullscreen ? (
      leftDrawerContent
    ) : (
      <div className="ads-ws__panel ads-ws__left" aria-label={t('left.aria')} data-testid="ads-left">
        <AdsLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as AdsLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="ads-ws__panel ads-ws__right" aria-label={t('right.aria')} data-testid="ads-right">
        <AdsLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as AdsRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="ads-workspace-loading">
        <div className="ads-ws">
          <div className="ads-ws__skeleton ads-ws__skeleton--header" />
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard" data-testid="ads-workspace-page">
      <div
        className="ads-ws"
        data-testid="ads-workspace"
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
      >
        <header className="ads-ws__header cs-page-header">
          <div className="ads-ws__header-copy cs-page-header__copy">
            <Link href={ADS_HOME as Route} className="ads-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="ads-ws__breadcrumb">
                <li>
                  <Link href={ADS_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="ads-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="ads-ws__breadcrumb-current" aria-current="page">
                  {t('title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="trendingUp" size={20} />
              {t('title')}
            </h1>
            <p className="ads-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="ads-ws__header-actions cs-page-header__actions">
            <div className="ads-ws__save-status" data-testid="ads-save-status">
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <StatusChip tone={CAMPAIGN_STATUS_TONE[campaignStatus]}>
                {t(`status.${campaignStatus}`)}
              </StatusChip>
              <span className="ads-ws__saved-ago">{saved ? t('savedAgo') : t('notSavedYet')}</span>
            </div>
            <Button variant="secondary" size="sm" onClick={() => persistNow(true)} data-testid="ads-save">
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="ads-preview"
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
              data-testid="ads-send-test"
              onClick={() => showToast(t('toasts.testSent'))}
            >
              {t('sendTest')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="ads-download-header"
              onClick={() => showToast(t('toasts.downloaded'))}
            >
              <IhIcon name="inbox" size={12} />
              {t('download')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="ads-publish"
              onClick={() => setPublishOpen(true)}
            >
              {t('publish')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
          </div>
        </header>

        <div className="ads-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="ads-ws__toolbar-left">
            <div className="ads-ws__project">
              <Select
                id="ads-project"
                label={t('fields.project')}
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value as ProjectId);
                  markDirty();
                }}
              >
                {ADS_PROJECTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="ads-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="ads-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="ads-undo"
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="ads-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="ads-redo"
                onClick={() => showToast(t('toasts.redo'))}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
            </div>
          </div>
          <div className="ads-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <AdsZoomToolbar
              engine={ftv}
              canvasLocked={canvasLocked}
              onToggleLock={() => setCanvasLocked((v) => !v)}
              isFullscreen={focus.isFullscreen}
              onToggleFullscreen={focus.toggleFullscreen}
            />
          </div>
        </div>

        <div
          className="ads-ws__ai-status"
          role="status"
          aria-live="polite"
          data-testid="ads-info-banner"
        >
          <span className="ads-ws__ai-status-dot" aria-hidden="true" />
          <span>{t('infoBanner')}</span>
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="ads-ws__layout"
          leftRail={adsLeftRail}
          rightRail={adsRightRail}
          onLeftRailSelect={(id) => {
            if ((ADS_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as AdsLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((ADS_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as AdsRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section
              className="ads-ws__panel ads-ws__center"
              aria-label={t('canvas.aria')}
              data-testid="ads-center"
            >
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="ads-canvas-stage"
                toolbar={
                  <div className="ads-ws__center-head">
                    <div
                      className="ads-ws__platform-tabs"
                      role="group"
                      aria-label={t('canvas.platformsAria')}
                      data-testid="ads-platform-bar"
                    >
                      {PLATFORM_OPTIONS.map((p) => (
                        <button
                          key={p.key}
                          type="button"
                          className={`ads-ws__format-tab${activePlatform === p.key ? ' is-active' : ''}`}
                          aria-pressed={activePlatform === p.key}
                          data-testid={`ads-platform-${p.key}`}
                          onClick={() => handlePlatformChange(p.key)}
                        >
                          <IhIcon name={p.icon} size={12} />
                          {t(`platforms.${p.key}`)}
                        </button>
                      ))}
                    </div>
                    <div
                      className="ads-ws__format-tabs"
                      role="group"
                      aria-label={t('canvas.formatsAria')}
                      data-testid="ads-format-bar"
                    >
                      {FORMAT_PRESETS.map((f) => (
                        <button
                          key={f.key}
                          type="button"
                          className={`ads-ws__format-tab${formatPreset === f.key ? ' is-active' : ''}`}
                          aria-pressed={formatPreset === f.key}
                          data-testid={`ads-format-${f.key}`}
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
                  count: ads.length,
                  testId: 'ads-ad-strip',
                  handleTestId: 'ads-tray-handle',
                  content: (
                    <div className="ads-ws__filmstrip" data-testid="ads-filmstrip">
                      <button
                        type="button"
                        className="ads-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripPrev')}
                        data-testid="ads-filmstrip-prev"
                        onClick={() => scrollFilmstrip(-1)}
                      >
                        <IhIcon name="chevronLeft" size={14} />
                      </button>
                      <div className="ads-ws__page-row" ref={filmstripRef} data-testid="ads-ad-row">
                        {FORMAT_PRESETS.map((f) => {
                          const ad =
                            ads.find((a) => a.format === f.key) ??
                            ads.find((a) => a.id === selectedAdId)!;
                          const isActive = formatPreset === f.key;
                          return (
                            <button
                              key={f.key}
                              type="button"
                              className={`ads-ws__page-card${isActive ? ' is-selected' : ''}`}
                              onClick={() => {
                                const match = ads.find((a) => a.format === f.key);
                                if (match) selectAd(match);
                                else handleFormatChange(f.key);
                              }}
                              data-testid={`ads-strip-${f.key}`}
                            >
                              <div className={`ads-ws__page-thumb ${aspectThumbClass(f.key)}`}>
                                <img src={ad.thumbUrl} alt="" />
                              </div>
                              <strong>{t(`formats.${f.key}`)}</strong>
                            </button>
                          );
                        })}
                        <button
                          type="button"
                          className="ads-ws__page-card ads-ws__page-card--new"
                          data-testid="ads-new-ad"
                          onClick={addAd}
                        >
                          <div className="ads-ws__page-thumb ads-ws__page-thumb--new">
                            <IhIcon name="plus" size={18} />
                          </div>
                          <strong>{t('canvas.newAd')}</strong>
                        </button>
                      </div>
                      <button
                        type="button"
                        className="ads-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripNext')}
                        data-testid="ads-filmstrip-next"
                        onClick={() => scrollFilmstrip(1)}
                      >
                        <IhIcon name="chevronRight" size={14} />
                      </button>
                    </div>
                  ),
                }}
                dock={{
                  testId: 'ads-scene-actions',
                  className: 'ads-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="ads-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      primary={{
                        label: t('bottomBar.actions.addComponent'),
                        icon: 'plus',
                        onClick: () => handleBottomAction('addComponent'),
                        testId: 'ads-action-addComponent',
                      }}
                      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addComponent').map((action) => ({
                        key: action.key,
                        icon: action.icon,
                        label: t(`bottomBar.actions.${action.key}`),
                        onClick: () => handleBottomAction(action.key),
                        testId: `ads-action-${action.key}`,
                      }))}
                    />
                  ),
                }}
              >
                <div className="ads-ws__canvas-stage" data-testid="ads-preview-shell">
                  <FocusFitStage engine={ftv} artboardTestId="ads-ftv-artboard">
                    <div
                      className={`ads-ws__artboard${selected ? ' is-selected' : ''}`}
                      data-testid="ads-artboard"
                      onClick={() => setSelected(true)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') setSelected(true);
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      <img
                        className="ads-ws__artboard-img"
                        src={selectedAd.thumbUrl || project.coverUrl}
                        alt=""
                      />
                      <div className="ads-ws__artboard-overlay" aria-hidden="true" />
                      {brandLogo ? (
                        <span
                          className="ads-ws__logo-preview"
                          style={{ position: 'absolute', top: '6%', left: '6%', zIndex: 2 }}
                        >
                          IH
                        </span>
                      ) : null}
                      <div className="ads-ws__artboard-copy">
                        <strong>{selectedAd.headline}</strong>
                        <p>{selectedAd.description}</p>
                        <span className="ads-ws__artboard-cta">
                          {t(`rails.content.ctaOptions.${selectedAd.cta}`)}
                        </span>
                      </div>
                      {selected ? (
                        <div
                          className="ads-ws__floating-actions"
                          data-testid="ads-floating-actions"
                          onMouseDown={(e) => e.stopPropagation()}
                        >
                          {FLOATING_ACTIONS.map((action) => (
                            <button
                              key={action.key}
                              type="button"
                              className="ads-ws__floating-btn"
                              data-testid={`ads-floating-${action.key}`}
                              onClick={() => handleFloating(action.key)}
                            >
                              <IhIcon name={action.icon} size={11} />
                              {t(`floating.${action.key}`)}
                            </button>
                          ))}
                          <div className="ads-ws__floating-more">
                            <button
                              type="button"
                              className={`ads-ws__floating-btn${floatingMoreOpen ? ' is-active' : ''}`}
                              aria-expanded={floatingMoreOpen}
                              data-testid="ads-floating-more"
                              onClick={() => handleFloating('more')}
                            >
                              ⋯
                            </button>
                            {floatingMoreOpen ? (
                              <div className="ads-ws__floating-menu" role="menu">
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
        <div className="ads-ws__modal" role="dialog" aria-modal="true" data-testid="ads-publish-modal">
          <div className="ads-ws__modal-card">
            <div className="ads-ws__modal-head">
              <div>
                <h2>{t('publishModal.title')}</h2>
                <p>{t('publishModal.subtitle')}</p>
              </div>
              <button
                type="button"
                className="ads-ws__icon-btn"
                aria-label={t('publishModal.close')}
                onClick={() => setPublishOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="ads-ws__modal-actions">
              <Button variant="secondary" size="sm" onClick={() => setPublishOpen(false)}>
                {t('publishModal.close')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setPublishOpen(false);
                  setCampaignStatus('published');
                  persistNow();
                  showToast(t('toasts.published'));
                }}
              >
                {t('publishModal.confirm')}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {toast ? (
        <div className="ads-ws__toast" role="status">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
