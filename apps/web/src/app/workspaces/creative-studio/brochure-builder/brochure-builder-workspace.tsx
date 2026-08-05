'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  BOTTOM_ACTIONS,
  BRB_HOME,
  BRB_LEFT_RAIL_ICONS,
  BRB_LEFT_RAIL_IDS,
  BRB_PROJECTS,
  BRB_RIGHT_RAIL_ICONS,
  BRB_RIGHT_RAIL_IDS,
  CAMPAIGN_STATUS_TONE,
  DEFAULT_PAGES,
  FLOATING_ACTIONS,
  createPage,
  getProject,
  resolveSpreadSize,
  spreadPartnerIndex,
  type BgMode,
  type BottomActionKey,
  type BrochurePage,
  type BrbLeftRailId,
  type BrbRightRailId,
  type CampaignStatus,
  type FloatingActionKey,
  type MarginPreset,
  type ProjectId,
  type SpreadMode,
} from './brochure-builder-model';

import {
  BrbLeftRailDrawer,
  BrbLocalRail,
  BrbRightRailDrawer,
  BrbZoomToolbar,
} from './brochure-builder-rail-drawers';

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

import './brochure-builder.css';

export function BrochureBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  const [hydrated, setHydrated] = useState(false);
  const [projectId, setProjectId] = useState<ProjectId>('temple');
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus>('ready');
  const [saved, setSaved] = useState(true);
  const [leftRailId, setLeftRailId] = useState<BrbLeftRailId>('pages');
  const [rightRailId, setRightRailId] = useState<BrbRightRailId>('design');
  const focus = useCreativeStudioFocusMode({ storageKey: 'brochure-builder' });

  const [pages, setPages] = useState<BrochurePage[]>(DEFAULT_PAGES);
  const [selectedPageId, setSelectedPageId] = useState(DEFAULT_PAGES[0]!.id);
  const [spreadMode, setSpreadMode] = useState<SpreadMode>('spread');
  const [themeName] = useState('Investhome Premium');
  const [headingFont, setHeadingFont] = useState('Inter Display');
  const [bodyFont, setBodyFont] = useState('Manrope');
  const [bgMode, setBgMode] = useState<BgMode>('image');
  const [margins, setMargins] = useState<MarginPreset>('normal');
  const [pageNumbers, setPageNumbers] = useState(true);
  const [notes, setNotes] = useState('');
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [selected, setSelected] = useState(true);
  const [floatingMoreOpen, setFloatingMoreOpen] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const project = useMemo(() => getProject(projectId), [projectId]);
  const selectedIndex = Math.max(
    0,
    pages.findIndex((p) => p.id === selectedPageId),
  );
  const selectedPage = pages[selectedIndex] ?? pages[0]!;
  const partnerIndex = spreadPartnerIndex(selectedIndex, pages.length);
  const partnerPage =
    spreadMode === 'spread' && partnerIndex != null ? pages[partnerIndex] : null;

  const contentSize = resolveSpreadSize(spreadMode);
  const fitPadX = focus.isFullscreen ? 16 : 28;
  const fitPadY = focus.isFullscreen ? 16 : 36;

  const ftv = useFitToViewEngine({
    contentWidth: Math.max(1, contentSize.w),
    contentHeight: Math.max(1, contentSize.h),
    enabled: true,
    contentKey: `${spreadMode}-${selectedPage.id}-${partnerPage?.id ?? 'none'}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}-${fitPadX}x${fitPadY}`,
    canvasType: 'artwork',
    padX: fitPadX,
    padY: fitPadY,
    cssWidthVar: '--brb-stage-w',
    cssHeightVar: '--brb-stage-h',
  });

  const leftRail: FocusRailItem[] = useMemo(
    () =>
      BRB_LEFT_RAIL_IDS.map((id) => ({
        id,
        icon: BRB_LEFT_RAIL_ICONS[id],
        labelKey: 'brief',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const rightRail: FocusRailItem[] = useMemo(
    () =>
      BRB_RIGHT_RAIL_IDS.map((id) => ({
        id,
        icon: BRB_RIGHT_RAIL_ICONS[id],
        labelKey: 'export',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const localLeftItems = useMemo(
    () => leftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [leftRail],
  );
  const localRightItems = useMemo(
    () => rightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [rightRail],
  );

  useEffect(() => {
    if (ftv.autoFit) ftv.fitToView();
    else ftv.refit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.mode, focus.isFullscreen, spreadMode, selectedPageId, fitPadX, fitPadY]);

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

  function patchPage(patch: Partial<BrochurePage>) {
    setPages((prev) => prev.map((p) => (p.id === selectedPage.id ? { ...p, ...patch } : p)));
  }

  function selectPage(page: BrochurePage) {
    setSelectedPageId(page.id);
    setSelected(true);
  }

  function goPage(dir: -1 | 1) {
    const next = selectedIndex + dir;
    if (next < 0 || next >= pages.length) return;
    setSelectedPageId(pages[next]!.id);
  }

  function addPage() {
    const next = createPage(pages.length + 1, project.coverUrl);
    setPages((prev) => [...prev, next]);
    setSelectedPageId(next.id);
    setLeftRailId('pages');
    markDirty();
    showToast(t('toasts.pageAdded'));
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
      setRightRailId('page');
      showToast(t('floating.edit'));
      return;
    }
    if (action === 'copy') {
      const clone: BrochurePage = {
        ...selectedPage,
        id: `pg-copy-${Date.now()}`,
        name: `${selectedPage.name} (copy)`,
        status: 'draft',
      };
      setPages((prev) => [...prev, clone]);
      setSelectedPageId(clone.id);
      markDirty();
      showToast(t('floating.copy'));
      return;
    }
    showToast(t(`floating.${action}`));
  }

  function handleBottomAction(action: BottomActionKey) {
    if (action === 'addComponent') {
      setLeftRailId('sections');
      showToast(t('bottomBar.toasts.addComponent'));
      return;
    }
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function handleApplyTemplate(thumbUrl: string) {
    patchPage({ thumbUrl });
    markDirty();
    showToast(t('toasts.templateApplied'));
  }

  function handleInsertComponent(key: string) {
    showToast(t('rails.components.toasts.inserted', { name: key }));
  }

  const leftPage =
    spreadMode === 'spread' && partnerPage && selectedIndex % 2 === 1
      ? partnerPage
      : selectedPage;
  const rightPage =
    spreadMode === 'spread'
      ? selectedIndex % 2 === 0
        ? partnerPage
        : selectedPage
      : null;

  const leftDrawerContent = (
    <BrbLeftRailDrawer
      id={leftRailId}
      pages={pages}
      selectedPageId={selectedPageId}
      onSelectPage={selectPage}
      onAddPage={addPage}
      onInsertComponent={handleInsertComponent}
      onApplyTemplate={handleApplyTemplate}
      onToast={showToast}
    />
  );

  const rightDrawerContent = (
    <BrbRightRailDrawer
      id={rightRailId}
      onSelectTab={setRightRailId}
      page={selectedPage}
      patchPage={patchPage}
      themeName={themeName}
      headingFont={headingFont}
      bodyFont={bodyFont}
      setHeadingFont={setHeadingFont}
      setBodyFont={setBodyFont}
      bgMode={bgMode}
      setBgMode={setBgMode}
      margins={margins}
      setMargins={setMargins}
      pageNumbers={pageNumbers}
      setPageNumbers={setPageNumbers}
      notes={notes}
      setNotes={setNotes}
      markDirty={markDirty}
      onToast={showToast}
    />
  );

  const leftDrawer =
    focus.isFocus || focus.isFullscreen ? (
      leftDrawerContent
    ) : (
      <div className="brb-ws__panel brb-ws__left" aria-label={t('left.aria')} data-testid="brb-left">
        <BrbLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as BrbLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="brb-ws__panel brb-ws__right" aria-label={t('right.aria')} data-testid="brb-right">
        <BrbLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as BrbRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="brb-workspace-loading">
        <div className="brb-ws">
          <div className="brb-ws__skeleton brb-ws__skeleton--header" />
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard" data-testid="brb-workspace-page">
      <div
        className="brb-ws"
        data-testid="brb-workspace"
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
      >
        <header className="brb-ws__header cs-page-header">
          <div className="brb-ws__header-copy cs-page-header__copy">
            <Link href={BRB_HOME as Route} className="brb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="brb-ws__breadcrumb">
                <li>
                  <Link href={BRB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="brb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="brb-ws__breadcrumb-current" aria-current="page">
                  {t('title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="documents" size={20} />
              {t('title')}
            </h1>
            <p className="brb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="brb-ws__header-actions cs-page-header__actions">
            <div className="brb-ws__save-status" data-testid="brb-save-status">
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <StatusChip tone={CAMPAIGN_STATUS_TONE[campaignStatus]}>
                {t(`status.${campaignStatus}`)}
              </StatusChip>
              <span className="brb-ws__saved-ago">{saved ? t('savedAgo') : t('notSavedYet')}</span>
            </div>
            <Button variant="secondary" size="sm" onClick={() => persistNow(true)} data-testid="brb-save">
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="brb-preview"
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
              data-testid="brb-export-pdf"
              onClick={() => showToast(t('toasts.pdf'))}
            >
              {t('exportPdf')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="brb-export-pptx"
              onClick={() => showToast(t('toasts.pptx'))}
            >
              {t('exportPptx')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="brb-publish"
              onClick={() => setPublishOpen(true)}
            >
              {t('publish')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
          </div>
        </header>

        <div className="brb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="brb-ws__toolbar-left">
            <div className="brb-ws__project">
              <Select
                id="brb-project"
                label={t('fields.project')}
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value as ProjectId);
                  markDirty();
                }}
              >
                {BRB_PROJECTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="brb-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="brb-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="brb-undo"
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="brb-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="brb-redo"
                onClick={() => showToast(t('toasts.redo'))}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
            </div>
          </div>
          <div className="brb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <BrbZoomToolbar
              engine={ftv}
              canvasLocked={canvasLocked}
              onToggleLock={() => setCanvasLocked((v) => !v)}
              isFullscreen={focus.isFullscreen}
              onToggleFullscreen={focus.toggleFullscreen}
            />
          </div>
        </div>

        <div
          className="brb-ws__ai-status"
          role="status"
          aria-live="polite"
          data-testid="brb-info-banner"
        >
          <span className="brb-ws__ai-status-dot" aria-hidden="true" />
          <span>{t('infoBanner')}</span>
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="brb-ws__layout"
          leftRail={leftRail}
          rightRail={rightRail}
          onLeftRailSelect={(id) => {
            if ((BRB_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as BrbLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((BRB_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as BrbRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section
              className="brb-ws__panel brb-ws__center"
              aria-label={t('canvas.aria')}
              data-testid="brb-center"
            >
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="brb-canvas-stage"
                toolbar={
                  <div className="brb-ws__center-head">
                    <div className="brb-ws__page-nav" data-testid="brb-page-nav" role="group">
                      <button
                        type="button"
                        className="brb-ws__page-nav-btn"
                        aria-label={t('canvas.prevPage')}
                        data-testid="brb-prev-page"
                        disabled={selectedIndex <= 0}
                        onClick={() => goPage(-1)}
                      >
                        <IhIcon name="chevronLeft" size={14} />
                      </button>
                      <span className="brb-ws__page-indicator" data-testid="brb-page-indicator">
                        {selectedIndex + 1} / {pages.length}
                      </span>
                      <button
                        type="button"
                        className="brb-ws__page-nav-btn"
                        aria-label={t('canvas.nextPage')}
                        data-testid="brb-next-page"
                        disabled={selectedIndex >= pages.length - 1}
                        onClick={() => goPage(1)}
                      >
                        <IhIcon name="chevronRight" size={14} />
                      </button>
                    </div>
                    <div
                      className="brb-ws__spread-toggle"
                      role="group"
                      aria-label={t('canvas.spreadAria')}
                      data-testid="brb-spread-toggle"
                    >
                      <button
                        type="button"
                        className={`brb-ws__format-tab${spreadMode === 'single' ? ' is-active' : ''}`}
                        aria-pressed={spreadMode === 'single'}
                        data-testid="brb-view-single"
                        onClick={() => setSpreadMode('single')}
                      >
                        <IhIcon name="documents" size={12} />
                        {t('canvas.views.single')}
                      </button>
                      <button
                        type="button"
                        className={`brb-ws__format-tab${spreadMode === 'spread' ? ' is-active' : ''}`}
                        aria-pressed={spreadMode === 'spread'}
                        data-testid="brb-view-spread"
                        onClick={() => setSpreadMode('spread')}
                      >
                        <IhIcon name="projects" size={12} />
                        {t('canvas.views.spread')}
                      </button>
                    </div>
                  </div>
                }
                dock={{
                  testId: 'brb-scene-actions',
                  className: 'brb-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="brb-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      primary={{
                        label: t('bottomBar.actions.addComponent'),
                        icon: 'plus',
                        onClick: () => handleBottomAction('addComponent'),
                        testId: 'brb-action-addComponent',
                      }}
                      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addComponent').map((action) => ({
                        key: action.key,
                        icon: action.icon,
                        label: t(`bottomBar.actions.${action.key}`),
                        onClick: () => handleBottomAction(action.key),
                        testId: `brb-action-${action.key}`,
                      }))}
                    />
                  ),
                }}
              >
                <div className="brb-ws__canvas-stage" data-testid="brb-preview-shell">
                  <FocusFitStage engine={ftv} artboardTestId="brb-ftv-artboard">
                    <div
                      className={`brb-ws__artboard brb-ws__spread${spreadMode === 'spread' ? ' is-spread' : ' is-single'}${selected ? ' is-selected' : ''}`}
                      data-testid="brb-artboard"
                      data-spread={spreadMode}
                      onClick={() => setSelected(true)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') setSelected(true);
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      <div
                        className="brb-ws__brochure-page"
                        data-testid="brb-page-left"
                        onClick={() => selectPage(leftPage)}
                      >
                        <img src={leftPage.thumbUrl || project.coverUrl} alt="" />
                        <div className="brb-ws__brochure-overlay" aria-hidden="true">
                          <span className="brb-ws__brochure-kicker">{project.name}</span>
                          <strong>{leftPage.name}</strong>
                        </div>
                        {pageNumbers ? (
                          <span className="brb-ws__page-number">
                            {pages.findIndex((p) => p.id === leftPage.id) + 1}
                          </span>
                        ) : null}
                      </div>
                      {spreadMode === 'spread' ? (
                        <div
                          className="brb-ws__brochure-page"
                          data-testid="brb-page-right"
                          onClick={() => {
                            if (rightPage) selectPage(rightPage);
                          }}
                        >
                          {rightPage ? (
                            <>
                              <img src={rightPage.thumbUrl || project.coverUrl} alt="" />
                              <div className="brb-ws__brochure-overlay" aria-hidden="true">
                                <strong>{rightPage.name}</strong>
                              </div>
                              {pageNumbers ? (
                                <span className="brb-ws__page-number">
                                  {pages.findIndex((p) => p.id === rightPage.id) + 1}
                                </span>
                              ) : null}
                            </>
                          ) : (
                            <div className="brb-ws__brochure-empty">{t('canvas.emptySpread')}</div>
                          )}
                        </div>
                      ) : null}

                      {selected ? (
                        <div
                          className="brb-ws__floating-actions"
                          data-testid="brb-floating-actions"
                          onMouseDown={(e) => e.stopPropagation()}
                        >
                          {FLOATING_ACTIONS.map((action) => (
                            <button
                              key={action.key}
                              type="button"
                              className="brb-ws__floating-btn"
                              data-testid={`brb-floating-${action.key}`}
                              onClick={() => handleFloating(action.key)}
                            >
                              <IhIcon name={action.icon} size={11} />
                              {t(`floating.${action.key}`)}
                            </button>
                          ))}
                          <div className="brb-ws__floating-more">
                            <button
                              type="button"
                              className={`brb-ws__floating-btn${floatingMoreOpen ? ' is-active' : ''}`}
                              aria-expanded={floatingMoreOpen}
                              data-testid="brb-floating-more"
                              onClick={() => handleFloating('more')}
                            >
                              ⋯
                            </button>
                            {floatingMoreOpen ? (
                              <div className="brb-ws__floating-menu" role="menu">
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
                                    setRightRailId('design');
                                    setFloatingMoreOpen(false);
                                  }}
                                >
                                  {t('floating.menu.design')}
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
        <div className="brb-ws__modal" role="dialog" aria-modal="true" data-testid="brb-publish-modal">
          <div className="brb-ws__modal-card">
            <div className="brb-ws__modal-head">
              <div>
                <h2>{t('publishModal.title')}</h2>
                <p>{t('publishModal.subtitle')}</p>
              </div>
              <button
                type="button"
                className="brb-ws__icon-btn"
                aria-label={t('publishModal.close')}
                onClick={() => setPublishOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="brb-ws__modal-actions">
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
        <div className="brb-ws__toast" role="status">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
