'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  AI_PROGRESS_STEPS,
  AI_SOURCES,
  AI_STATUS_SEQUENCE,
  BOTTOM_ACTIONS,
  CAMPAIGN_STATUS_TONE,
  CASH_FLOW_ROWS,
  DEFAULT_BRIEF,
  DEFAULT_FINANCIALS,
  DEFAULT_MARGINS,
  DEFAULT_PAGES,
  DEFAULT_SCORES,
  PRB_HOME,
  PRB_LEFT_RAIL_ICONS,
  PRB_LEFT_RAIL_IDS,
  PRB_PROJECTS,
  PRB_RIGHT_RAIL_ICONS,
  PRB_RIGHT_RAIL_IDS,
  ROI_TABLE_ROWS,
  SOURCES_USES_ROWS,
  buildPages,
  getProject,
  readingMinutes,
  reorderPages,
  ratioClass,
  type AiStatusKey,
  type BottomActionKey,
  type CampaignStatus,
  type DevicePreview,
  type DocumentRatio,
  type ExportQuality,
  type PageMargins,
  type PageOrientation,
  type PrbLeftRailId,
  type PrbPage,
  type PrbRightRailId,
  type ProjectId,
  type ProposalBrief,
  type ProposalScores,
  type ProposalType,
  type QuickActionKey,
  type SignatureState,
  type SuggestionKey,
  type ViewMode,
} from './proposal-builder-model';

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

import {
  PrbLeftRailDrawer,
  PrbLocalRail,
  PrbRightRailDrawer,
  PrbZoomToolbar,
} from './proposal-builder-rail-drawers';

import './proposal-builder.css';

const A4_PAGE_W = 794;
const LETTER_PAGE_W = 816;

export function ProposalBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');

  const [hydrated, setHydrated] = useState(false);
  const [projectId, setProjectId] = useState<ProjectId>('temple');
  const [activeStep, setActiveStep] = useState(0);
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus>('ready');
  const [saved, setSaved] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [aiStatus, setAiStatus] = useState<AiStatusKey>('completed');
  const [progressStep, setProgressStep] = useState(-1);
  const [brief, setBrief] = useState<ProposalBrief>(DEFAULT_BRIEF);
  const [financials, setFinancials] = useState(DEFAULT_FINANCIALS);
  const [leftRailId, setLeftRailId] = useState<PrbLeftRailId>('content');
  const [rightRailId, setRightRailId] = useState<PrbRightRailId>('page');
  const focus = useCreativeStudioFocusMode({ storageKey: 'proposal-builder' });
  const [scores, setScores] = useState<ProposalScores>(DEFAULT_SCORES);
  const [appliedSuggestions, setAppliedSuggestions] = useState<Set<SuggestionKey>>(new Set());
  const [pages, setPages] = useState<PrbPage[]>(DEFAULT_PAGES);
  const [selectedPageId, setSelectedPageId] = useState('pg-1');
  const [viewMode, setViewMode] = useState<ViewMode>('document');
  const [docRatio, setDocRatio] = useState<DocumentRatio>('a4');
  const [orientation, setOrientation] = useState<PageOrientation>('portrait');
  const [margins, setMargins] = useState<PageMargins>(DEFAULT_MARGINS);
  const [bgColor, setBgColor] = useState(true);
  const [bgImage, setBgImage] = useState(false);
  const [showHeader, setShowHeader] = useState(false);
  const [showFooter, setShowFooter] = useState(false);
  const [devicePreview, setDevicePreview] = useState<DevicePreview>('desktop');
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [floatingMoreOpen, setFloatingMoreOpen] = useState(false);
  const [aiInstructions, setAiInstructions] = useState(
    'Lead with investment thesis. Keep financial tables board-ready. Prefer navy/cyan brand accents.',
  );
  const [exportQuality, setExportQuality] = useState<ExportQuality>('high');
  const [includeNotes, setIncludeNotes] = useState(true);
  const [includeWatermark, setIncludeWatermark] = useState(false);
  const [includePageNumbers, setIncludePageNumbers] = useState(true);
  const [showMoreTypes, setShowMoreTypes] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [signatureState, setSignatureState] = useState<SignatureState>('draft');
  const [enabledSources, setEnabledSources] = useState<Set<string>>(
    () => new Set(AI_SOURCES.slice(0, 12)),
  );
  const filmstripRef = useRef<HTMLDivElement | null>(null);
  const genTimerRef = useRef<number[]>([]);

  const project = useMemo(() => getProject(projectId), [projectId]);
  const selectedPage = pages.find((p) => p.id === selectedPageId) ?? pages[0]!;
  const selectedIndex = pages.findIndex((p) => p.id === selectedPage.id);
  const minutes = readingMinutes(pages.length);
  const completeness = Math.min(
    100,
    Math.round((pages.filter((p) => p.status === 'ready').length / pages.length) * 100),
  );

  const baseAspect = docRatio === 'letter' ? 8.5 / 11 : 210 / 297;
  const pageAspect = orientation === 'landscape' ? 1 / baseAspect : baseAspect;
  const pageContentW =
    orientation === 'landscape'
      ? Math.round((docRatio === 'letter' ? LETTER_PAGE_W : A4_PAGE_W) / baseAspect)
      : docRatio === 'letter'
        ? LETTER_PAGE_W
        : A4_PAGE_W;
  const pageContentH = pageContentW / pageAspect;
  const ftvEnabled = viewMode === 'document' && (focus.isFocus || focus.isFullscreen || focus.isNormal);
  const ftv = useFitToViewEngine({
    contentWidth: pageContentW,
    contentHeight: pageContentH,
    enabled: ftvEnabled,
    contentKey: `${docRatio}-${orientation}-${selectedPageId}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}-${devicePreview}`,
    cssWidthVar: '--prb-stage-w',
    cssHeightVar: '--prb-stage-h',
    canvasType: 'artwork',
  });

  const prbLeftRail: FocusRailItem[] = useMemo(
    () =>
      PRB_LEFT_RAIL_IDS.map((id) => ({
        id,
        icon: PRB_LEFT_RAIL_ICONS[id],
        labelKey: 'brief',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const prbRightRail: FocusRailItem[] = useMemo(
    () =>
      PRB_RIGHT_RAIL_IDS.map((id) => ({
        id,
        icon: PRB_RIGHT_RAIL_ICONS[id],
        labelKey: 'export',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const localLeftItems = useMemo(
    () => prbLeftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [prbLeftRail],
  );
  const localRightItems = useMemo(
    () => prbRightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [prbRightRail],
  );

  useEffect(() => {
    setHydrated(true);
    return () => {
      genTimerRef.current.forEach((id) => window.clearTimeout(id));
    };
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

  useEffect(() => {
    if (focus.isFocus || focus.isFullscreen) {
      if (ftv.autoFit) ftv.fitToView();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- enter Focus/FS should re-fit
  }, [focus.isFocus, focus.isFullscreen]);

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  function markDirty() {
    setSaved(false);
  }

  function persistNow(announce = false) {
    setSaved(true);
    if (announce) showToast(t('toasts.saved'));
  }

  function clearGenTimers() {
    genTimerRef.current.forEach((id) => window.clearTimeout(id));
    genTimerRef.current = [];
  }

  function applyProposalType(type: ProposalType) {
    const nextPages = buildPages(type);
    setBrief((prev) => ({ ...prev, proposalType: type }));
    setPages(nextPages);
    setSelectedPageId(nextPages[0]?.id ?? 'pg-1');
    markDirty();
  }

  function handleGenerate(action: QuickActionKey | 'entire' | 'variation' = 'entire') {
    clearGenTimers();
    setGenerating(true);
    setProgressStep(0);
    setAiStatus('thinking');
    setActiveStep(2);
    setCampaignStatus('draft');
    markDirty();

    AI_STATUS_SEQUENCE.forEach((status, index) => {
      const id = window.setTimeout(() => {
        setAiStatus(status);
        setProgressStep(Math.min(index, AI_PROGRESS_STEPS.length - 1));
        if (status === 'optimizing') {
          setScores((prev) => ({
            ...prev,
            overall: Math.min(99, prev.overall + 1),
          }));
        }
        if (status === 'completed') {
          setGenerating(false);
          setProgressStep(AI_PROGRESS_STEPS.length);
          setCampaignStatus('ready');
          setActiveStep(4);
          setPages((prev) =>
            prev.map((p) => ({
              ...p,
              status: 'ready' as const,
            })),
          );
          if (action === 'shorten') {
            setPages((prev) => prev.slice(0, Math.max(10, prev.length - 3)));
          }
          if (action === 'expand') {
            setPages((prev) => {
              const extra: PrbPage = {
                id: `pg-${Date.now()}`,
                kind: 'attachments',
                thumbUrl: project.coverUrl,
                status: 'ready',
              };
              return [...prev, extra];
            });
          }
          persistNow();
          showToast(action === 'variation' ? t('toasts.variation') : t('toasts.generated'));
        }
      }, 380 * (index + 1));
      genTimerRef.current.push(id);
    });
  }

  function applySuggestion(key: SuggestionKey) {
    setAppliedSuggestions((prev) => new Set(prev).add(key));
    setScores((prev) => ({
      ...prev,
      overall: Math.min(99, prev.overall + 1),
    }));
    showToast(t(`suggestions.${key}`));
  }

  function addPage() {
    const copy: PrbPage = {
      id: `pg-${Date.now()}`,
      kind: 'attachments',
      thumbUrl: project.coverUrl,
      status: 'draft',
    };
    setPages((prev) => [...prev, copy]);
    setSelectedPageId(copy.id);
    markDirty();
    showToast(t('toasts.pageAdded'));
  }

  function duplicatePage() {
    const copy: PrbPage = {
      ...selectedPage,
      id: `pg-${Date.now()}`,
    };
    setPages((prev) => {
      const idx = prev.findIndex((p) => p.id === selectedPage.id);
      const next = [...prev];
      next.splice(idx + 1, 0, copy);
      return next;
    });
    setSelectedPageId(copy.id);
    markDirty();
    showToast(t('toasts.pageDuplicated'));
  }

  function deletePage() {
    if (pages.length <= 1) {
      showToast(t('toasts.cannotDeleteLast'));
      return;
    }
    setPages((prev) => prev.filter((p) => p.id !== selectedPage.id));
    const fallback = pages.find((p) => p.id !== selectedPage.id);
    if (fallback) setSelectedPageId(fallback.id);
    markDirty();
    showToast(t('toasts.pageDeleted'));
  }

  function handleBottomAction(action: BottomActionKey) {
    if (action === 'addSection') {
      addPage();
      setLeftRailId('content');
      return;
    }
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function scrollFilmstrip(dir: -1 | 1) {
    const el = filmstripRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 220, behavior: 'smooth' });
  }

  function goPage(dir: -1 | 1) {
    const next = selectedIndex + dir;
    if (next < 0 || next >= pages.length) return;
    setSelectedPageId(pages[next]!.id);
  }

  function renderDocumentBody() {
    const kind = selectedPage.kind;
    const title = selectedIndex === 0 ? brief.topic : t(`pages.${kind}.title`);
    const body =
      selectedIndex === 0 ? t('canvas.coverSubtitle') : t(`pages.${kind}.body`);

    if (kind === 'cover') {
      return (
        <div className="prb-ws__doc-page prb-ws__doc-page--cover" data-testid="prb-doc-cover">
          <div className="prb-ws__doc-cover-hero">
            <img src={selectedPage.thumbUrl} alt={t('canvas.previewAlt')} />
            <div className="prb-ws__doc-cover-overlay">
              <p className="prb-ws__doc-kicker">{t('canvas.coverKicker')}</p>
              <h2 className="prb-ws__doc-title">{project.name}</h2>
              <p className="prb-ws__doc-subtitle">{title}</p>
              <p className="prb-ws__doc-subtitle">{body}</p>
            </div>
            <div className="prb-ws__doc-cover-brand" aria-hidden="true">
              INVESTHOME
            </div>
          </div>
        </div>
      );
    }

    if (kind === 'financialSummary' || kind === 'roiIrr') {
      return (
        <div className="prb-ws__doc-page" data-testid="prb-doc-financial">
          <div className="prb-ws__doc-header">
            <span className="prb-ws__doc-brand">Investhome OS</span>
            <div className="prb-ws__doc-meta">
              {selectedIndex + 1} / {pages.length}
            </div>
          </div>
          <p className="prb-ws__doc-kicker">{t(`pages.${kind}.title`)}</p>
          <h2 className="prb-ws__doc-title">{title}</h2>
          <p className="prb-ws__doc-subtitle">{body}</p>
          <table className="prb-ws__doc-table">
            <thead>
              <tr>
                <th>{t('financial.metric')}</th>
                <th>{t('financial.value')}</th>
              </tr>
            </thead>
            <tbody>
              {ROI_TABLE_ROWS.map((row) => (
                <tr key={row.label}>
                  <td>{row.label}</td>
                  <td className="num">{row.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    if (kind === 'cashFlow' || kind === 'paymentSchedule') {
      return (
        <div className="prb-ws__doc-page" data-testid="prb-doc-cashflow">
          <div className="prb-ws__doc-header">
            <span className="prb-ws__doc-brand">Investhome OS</span>
            <div className="prb-ws__doc-meta">
              {selectedIndex + 1} / {pages.length}
            </div>
          </div>
          <p className="prb-ws__doc-kicker">{t(`pages.${kind}.title`)}</p>
          <h2 className="prb-ws__doc-title">{title}</h2>
          <p className="prb-ws__doc-subtitle">{body}</p>
          <table className="prb-ws__doc-table">
            <thead>
              <tr>
                <th>{t('financial.year')}</th>
                <th>{t('financial.noi')}</th>
                <th>{t('financial.distribution')}</th>
              </tr>
            </thead>
            <tbody>
              {CASH_FLOW_ROWS.map((row) => (
                <tr key={row.year}>
                  <td>{row.year}</td>
                  <td className="num">{row.noi}</td>
                  <td className="num">{row.distribution}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    if (kind === 'sourcesUses' || kind === 'investmentStructure') {
      return (
        <div className="prb-ws__doc-page" data-testid="prb-doc-sources">
          <div className="prb-ws__doc-header">
            <span className="prb-ws__doc-brand">Investhome OS</span>
            <div className="prb-ws__doc-meta">
              {selectedIndex + 1} / {pages.length}
            </div>
          </div>
          <p className="prb-ws__doc-kicker">{t(`pages.${kind}.title`)}</p>
          <h2 className="prb-ws__doc-title">{title}</h2>
          <p className="prb-ws__doc-subtitle">{body}</p>
          <table className="prb-ws__doc-table">
            <thead>
              <tr>
                <th>{t('financial.item')}</th>
                <th>{t('financial.sources')}</th>
                <th>{t('financial.uses')}</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES_USES_ROWS.map((row) => (
                <tr key={row.item}>
                  <td>{row.item}</td>
                  <td className="num">{row.sources}</td>
                  <td className="num">{row.uses}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    return (
      <div className="prb-ws__doc-page" data-testid="prb-doc-generic">
        <div className="prb-ws__doc-header">
          <span className="prb-ws__doc-brand">Investhome OS</span>
          <div className="prb-ws__doc-meta">
            {selectedIndex + 1} / {pages.length}
          </div>
        </div>
        <p className="prb-ws__doc-kicker">{t(`proposalTypes.${brief.proposalType}`)}</p>
        <h2 className="prb-ws__doc-title">{title}</h2>
        <p className="prb-ws__doc-subtitle">{body}</p>
        {(kind === 'projectOverview' || kind === 'location' || kind === 'whyUs') && (
          <div className="prb-ws__doc-hero">
            <img src={selectedPage.thumbUrl} alt="" />
          </div>
        )}
        <div className="prb-ws__doc-body">
          <p className="prb-ws__doc-subtitle">{t('canvas.pageNarrative')}</p>
        </div>
      </div>
    );
  }

  const leftDrawerContent = (
    <PrbLeftRailDrawer
      id={leftRailId}
      brief={brief}
      setBrief={setBrief}
      financials={financials}
      setFinancials={setFinancials}
      aiInstructions={aiInstructions}
      setAiInstructions={setAiInstructions}
      showMoreTypes={showMoreTypes}
      setShowMoreTypes={setShowMoreTypes}
      pages={pages}
      selectedPageId={selectedPageId}
      setSelectedPageId={setSelectedPageId}
      setPages={setPages}
      enabledSources={enabledSources}
      setEnabledSources={setEnabledSources}
      onApplyType={applyProposalType}
      onAddPage={addPage}
      onGenerate={() => handleGenerate('entire')}
      generating={generating}
      markDirty={markDirty}
      onToast={showToast}
    />
  );

  const rightDrawerContent = (
    <PrbRightRailDrawer
      id={rightRailId}
      scores={scores}
      pages={pages}
      minutes={minutes}
      completeness={completeness}
      appliedSuggestions={appliedSuggestions}
      onApplySuggestion={applySuggestion}
      onQuickAction={(key) => handleGenerate(key)}
      signatureState={signatureState}
      setSignatureState={setSignatureState}
      exportQuality={exportQuality}
      setExportQuality={setExportQuality}
      includeNotes={includeNotes}
      setIncludeNotes={setIncludeNotes}
      includeWatermark={includeWatermark}
      setIncludeWatermark={setIncludeWatermark}
      includePageNumbers={includePageNumbers}
      setIncludePageNumbers={setIncludePageNumbers}
      docRatio={docRatio}
      setDocRatio={(r) => {
        setDocRatio(r);
        markDirty();
      }}
      orientation={orientation}
      setOrientation={(o) => {
        setOrientation(o);
        markDirty();
      }}
      margins={margins}
      setMargins={setMargins}
      bgColor={bgColor}
      setBgColor={setBgColor}
      bgImage={bgImage}
      setBgImage={setBgImage}
      showHeader={showHeader}
      setShowHeader={setShowHeader}
      showFooter={showFooter}
      setShowFooter={setShowFooter}
      onDownload={() => {
        setCampaignStatus('exported');
        showToast(t('toasts.downloaded'));
      }}
      onToast={showToast}
    />
  );

  const leftDrawer =
    focus.isFocus || focus.isFullscreen ? (
      leftDrawerContent
    ) : (
      <div className="prb-ws__panel prb-ws__left" aria-label={t('left.aria')} data-testid="prb-left">
        <PrbLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as PrbLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="prb-ws__panel prb-ws__right" aria-label={t('right.aria')} data-testid="prb-right">
        <PrbLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as PrbRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="prb-workspace-loading">
        <div className="prb-ws">
          <div className="prb-ws__skeleton" aria-hidden="true" />
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard" data-testid="prb-workspace">
      <div
        className="prb-ws"
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
      >
        <header className="prb-ws__header cs-page-header">
          <div className="prb-ws__header-copy cs-page-header__copy">
            <Link href={PRB_HOME as Route} className="prb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="prb-ws__breadcrumb">
                <li>
                  <Link href={PRB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="prb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="prb-ws__breadcrumb-current" aria-current="page">
                  {tTools('proposalStudio.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="documents" size={20} />
              {tTools('proposalStudio.title')}
            </h1>
            <p className="prb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="prb-ws__header-actions cs-page-header__actions">
            <div className="prb-ws__save-status" data-testid="prb-save-status">
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <span className="prb-ws__saved-ago">{saved ? t('savedAgo') : t('unsaved')}</span>
            </div>
            <Button variant="secondary" size="sm" onClick={() => persistNow(true)} data-testid="prb-save">
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="prb-preview"
              onClick={() => {
                focus.setMode('preview');
                setActiveStep(4);
                showToast(t('toasts.preview'));
              }}
            >
              {t('preview')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="prb-share"
              onClick={() => showToast(t('toasts.shared'))}
            >
              {t('share')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="prb-download-header"
              onClick={() => {
                setCampaignStatus('exported');
                setRightRailId('export');
                showToast(t('toasts.downloaded'));
              }}
            >
              <IhIcon name="inbox" size={12} />
              {t('download')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="prb-create-ai"
              disabled={generating}
              onClick={() => handleGenerate('entire')}
            >
              <IhIcon name="sparkles" size={12} />
              {t('createWithAi')}
            </Button>
          </div>
        </header>

        <div className="prb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="prb-ws__toolbar-left">
            <div className="prb-ws__project">
              <Select
                id="prb-project"
                label={t('fields.project')}
                value={projectId}
                onChange={(e) => {
                  const id = e.target.value as ProjectId;
                  setProjectId(id);
                  setBrief((prev) => ({
                    ...prev,
                    topic: `${getProject(id).name} — Investor Proposal`,
                  }));
                  markDirty();
                }}
              >
                {PRB_PROJECTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="prb-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="prb-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="prb-undo"
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="prb-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="prb-redo"
                onClick={() => showToast(t('toasts.redo'))}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
            </div>
          </div>
          <div className="prb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <PrbZoomToolbar
              engine={ftv}
              canvasLocked={canvasLocked}
              onToggleLock={() => setCanvasLocked((v) => !v)}
              isFullscreen={focus.isFullscreen}
              onToggleFullscreen={focus.toggleFullscreen}
            />
            <StatusChip tone={CAMPAIGN_STATUS_TONE[campaignStatus]}>
              {t(`status.${campaignStatus}`)}
            </StatusChip>
          </div>
        </div>

        <div
          className={`prb-ws__ai-status${generating || aiStatus !== 'idle' ? ' is-live' : ''}`}
          role="status"
          aria-live="polite"
          data-testid="prb-ai-status"
        >
          <span className="prb-ws__ai-status-dot" aria-hidden="true" />
          <span>{aiStatus === 'idle' ? t('aiStatus.idle') : t(`aiStatus.${aiStatus}`)}</span>
          {generating ? (
            <span className="prb-ws__ai-status-progress">
              {progressStep + 1}/{AI_PROGRESS_STEPS.length}
            </span>
          ) : null}
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="prb-ws__layout"
          leftRail={prbLeftRail}
          rightRail={prbRightRail}
          onLeftRailSelect={(id) => {
            if ((PRB_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as PrbLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((PRB_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as PrbRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section
              className="prb-ws__panel prb-ws__center"
              aria-label={t('canvas.aria')}
              data-testid="prb-center"
            >
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="prb-canvas-stage"
                toolbar={
                  <div className="prb-ws__center-head">
                    <div className="prb-ws__view-controls" role="toolbar" aria-label={t('canvas.viewAria')}>
                      <div className="prb-ws__device-toggle" role="group" aria-label={t('canvas.deviceAria')}>
                        <button
                          type="button"
                          className={`prb-ws__device-btn${devicePreview === 'mobile' ? ' is-active' : ''}`}
                          aria-pressed={devicePreview === 'mobile'}
                          aria-label={t('canvas.previewMobile')}
                          data-testid="prb-preview-mobile"
                          title={t('canvas.previewMobile')}
                          onClick={() => setDevicePreview('mobile')}
                        >
                          <span className="prb-ws__device-glyph prb-ws__device-glyph--mobile" aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          className={`prb-ws__device-btn${devicePreview === 'desktop' ? ' is-active' : ''}`}
                          aria-pressed={devicePreview === 'desktop'}
                          aria-label={t('canvas.previewDesktop')}
                          data-testid="prb-preview-desktop"
                          title={t('canvas.previewDesktop')}
                          onClick={() => setDevicePreview('desktop')}
                        >
                          <span className="prb-ws__device-glyph prb-ws__device-glyph--desktop" aria-hidden="true" />
                        </button>
                      </div>
                      <div className="prb-ws__view-toggle" role="group" aria-label={t('canvas.viewsLabel')}>
                        <button
                          type="button"
                          className={`prb-ws__view-btn${viewMode === 'document' ? ' is-active' : ''}`}
                          onClick={() => setViewMode('document')}
                          data-testid="prb-view-document"
                        >
                          {t('canvas.views.document')}
                        </button>
                        <button
                          type="button"
                          className={`prb-ws__view-btn${viewMode === 'outline' ? ' is-active' : ''}`}
                          onClick={() => setViewMode('outline')}
                          data-testid="prb-view-outline"
                        >
                          {t('canvas.views.outline')}
                        </button>
                      </div>
                    </div>
                  </div>
                }
                tray={{
                  label: tFocus('tray.pages'),
                  count: pages.length,
                  testId: 'prb-page-strip',
                  handleTestId: 'prb-tray-handle',
                  content: (
                    <div className="prb-ws__filmstrip" data-testid="prb-filmstrip">
                      <button
                        type="button"
                        className="prb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripPrev')}
                        data-testid="prb-filmstrip-prev"
                        onClick={() => scrollFilmstrip(-1)}
                      >
                        <IhIcon name="chevronLeft" size={14} />
                      </button>
                      <div className="prb-ws__slide-row" ref={filmstripRef} data-testid="prb-page-row">
                        {pages.map((page, index) => (
                          <button
                            key={page.id}
                            type="button"
                            draggable
                            className={`prb-ws__slide-card${selectedPageId === page.id ? ' is-selected' : ''}${dragId === page.id ? ' is-dragging' : ''}`}
                            onClick={() => setSelectedPageId(page.id)}
                            onDragStart={() => setDragId(page.id)}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={() => {
                              if (!dragId) return;
                              setPages((prev) => reorderPages(prev, dragId, page.id));
                              setDragId(null);
                              markDirty();
                            }}
                            onDragEnd={() => setDragId(null)}
                            data-testid={`prb-page-${page.id}`}
                          >
                            <div
                              className={`prb-ws__slide-thumb ${ratioClass(docRatio)}${orientation === 'landscape' ? ' is-landscape' : ''}`}
                            >
                              <img src={page.thumbUrl} alt="" />
                              <span className="prb-ws__slide-num">{index + 1}</span>
                            </div>
                            <strong>{t(`pages.${page.kind}.title`)}</strong>
                          </button>
                        ))}
                        <button
                          type="button"
                          className="prb-ws__slide-card prb-ws__slide-card--new"
                          data-testid="prb-new-page"
                          onClick={addPage}
                        >
                          <div
                            className={`prb-ws__slide-thumb ${ratioClass(docRatio)} prb-ws__slide-thumb--new`}
                          >
                            <IhIcon name="plus" size={18} />
                          </div>
                          <strong>{t('canvas.newPage')}</strong>
                        </button>
                      </div>
                      <button
                        type="button"
                        className="prb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripNext')}
                        data-testid="prb-filmstrip-next"
                        onClick={() => scrollFilmstrip(1)}
                      >
                        <IhIcon name="chevronRight" size={14} />
                      </button>
                      <button
                        type="button"
                        className="prb-ws__filmstrip-delete"
                        aria-label={t('canvas.actions.delete')}
                        data-testid="prb-filmstrip-delete"
                        onClick={deletePage}
                      >
                        <IhIcon name="alert" size={14} />
                      </button>
                    </div>
                  ),
                }}
                dock={{
                  testId: 'prb-scene-actions',
                  className: 'prb-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="prb-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      primary={{
                        label: t('bottomBar.actions.addSection'),
                        icon: 'plus',
                        onClick: () => handleBottomAction('addSection'),
                        testId: 'prb-action-addSection',
                      }}
                      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addSection').map((action) => ({
                        key: action.key,
                        icon: action.icon,
                        label: t(`bottomBar.actions.${action.key}`),
                        onClick: () => handleBottomAction(action.key),
                        testId: `prb-action-${action.key}`,
                      }))}
                    />
                  ),
                }}
              >
                <div className="prb-ws__preview-shell" data-testid="prb-preview-shell">
                  {viewMode === 'document' ? (
                    <div
                      className={`prb-ws__preview-mat${devicePreview === 'mobile' ? ' is-mobile' : ''}`}
                      data-testid="prb-preview-mat"
                    >
                      <FocusFitStage engine={ftv} artboardTestId="prb-page-preview">
                        <div
                          className={`prb-ws__slide-stage ${ratioClass(docRatio)}${orientation === 'landscape' ? ' is-landscape' : ''}`}
                          data-ratio={docRatio}
                          data-orientation={orientation}
                          style={{
                            ['--prb-margin-t' as string]: `${margins.top}px`,
                            ['--prb-margin-b' as string]: `${margins.bottom}px`,
                            ['--prb-margin-l' as string]: `${margins.left}px`,
                            ['--prb-margin-r' as string]: `${margins.right}px`,
                          }}
                        >
                          <div className="prb-ws__section-toolbar" data-testid="prb-section-toolbar">
                            <button
                              type="button"
                              className="prb-ws__section-toolbar-btn"
                              onClick={() => showToast(t('toasts.toolbar.edit'))}
                            >
                              <IhIcon name="design" size={12} />
                              {t('floating.edit')}
                            </button>
                            <button
                              type="button"
                              className="prb-ws__section-toolbar-btn"
                              onClick={duplicatePage}
                            >
                              <IhIcon name="documents" size={12} />
                              {t('floating.duplicate')}
                            </button>
                            <button
                              type="button"
                              className="prb-ws__section-toolbar-btn"
                              onClick={deletePage}
                            >
                              <IhIcon name="alert" size={12} />
                              {t('floating.delete')}
                            </button>
                            <button
                              type="button"
                              className="prb-ws__section-toolbar-btn"
                              onClick={() => setRightRailId('page')}
                            >
                              <IhIcon name="marketing" size={12} />
                              {t('floating.pageSettings')}
                            </button>
                            <div className="prb-ws__section-toolbar-more">
                              <button
                                type="button"
                                className="prb-ws__section-toolbar-btn"
                                aria-label={t('floating.more')}
                                aria-expanded={floatingMoreOpen}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setFloatingMoreOpen((v) => !v);
                                }}
                              >
                                <IhIcon name="quickAction" size={12} />
                              </button>
                              {floatingMoreOpen ? (
                                <div className="prb-ws__section-toolbar-menu" role="menu">
                                  <button
                                    type="button"
                                    role="menuitem"
                                    onClick={() => {
                                      handleGenerate('rewriteAll');
                                      setFloatingMoreOpen(false);
                                    }}
                                  >
                                    {t('canvas.actions.rewrite')}
                                  </button>
                                  <button
                                    type="button"
                                    role="menuitem"
                                    onClick={() => {
                                      showToast(t('toasts.toolbar.replaceImage'));
                                      setFloatingMoreOpen(false);
                                    }}
                                  >
                                    {t('canvas.actions.replaceImage')}
                                  </button>
                                  <button
                                    type="button"
                                    role="menuitem"
                                    onClick={() => {
                                      showToast(t('toasts.toolbar.changeStyle'));
                                      setFloatingMoreOpen(false);
                                    }}
                                  >
                                    {t('canvas.actions.changeStyle')}
                                  </button>
                                </div>
                              ) : null}
                            </div>
                          </div>
                          <div className="prb-ws__slide-canvas">{renderDocumentBody()}</div>
                          {includePageNumbers ? (
                            <span className="prb-ws__slide-count" data-testid="prb-ready-badge">
                              {selectedIndex + 1} / {pages.length}
                            </span>
                          ) : null}
                        </div>
                      </FocusFitStage>
                      <div className="prb-ws__page-nav" data-testid="prb-page-nav">
                        <button
                          type="button"
                          className="prb-ws__page-nav-btn"
                          aria-label={t('canvas.prevPage')}
                          disabled={selectedIndex <= 0}
                          onClick={() => goPage(-1)}
                        >
                          <IhIcon name="chevronLeft" size={12} />
                        </button>
                        <span>
                          {selectedIndex + 1} / {pages.length}
                        </span>
                        <button
                          type="button"
                          className="prb-ws__page-nav-btn"
                          aria-label={t('canvas.nextPage')}
                          disabled={selectedIndex >= pages.length - 1}
                          onClick={() => goPage(1)}
                        >
                          <IhIcon name="chevronRight" size={12} />
                        </button>
                        <button
                          type="button"
                          className="prb-ws__page-nav-btn"
                          aria-label={t('canvas.gridView')}
                          onClick={() => setViewMode((v) => (v === 'outline' ? 'document' : 'outline'))}
                        >
                          <IhIcon name="executive" size={12} />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="prb-ws__outline" data-testid="prb-outline-view">
                      {pages.map((page, index) => (
                        <button
                          key={page.id}
                          type="button"
                          className={`prb-ws__outline-row${selectedPageId === page.id ? ' is-selected' : ''}`}
                          onClick={() => setSelectedPageId(page.id)}
                        >
                          <strong>
                            {index + 1}. {t(`pages.${page.kind}.title`)}
                          </strong>
                          <span>{t(`pages.${page.kind}.body`)}</span>
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

      {toast ? (
        <div className="prb-ws__toast" role="status" data-testid="prb-toast">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
