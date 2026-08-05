'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import { CsBottomActionToolbar } from '../_components';
import {
  CreativeStudioFocusWorkspace,
  FocusActionDock,
  useCreativeStudioFocusMode,
  type FocusRailItem,
} from '../_components/focus-workspace';

import {
  ARCHITECTURAL_STUDIO_ROUTE,
  AS_HOME,
  BOTTOM_ACTIONS,
  BRIEF_MAX,
  CENTER_TABS,
  DEMO_BRIEF,
  DEMO_FILES,
  DEMO_METRICS,
  DEMO_REFERENCES,
  DEMO_RENDERS,
  DEMO_SPACES,
  FLOOR_PLAN_HIGHLIGHTS,
  FLOW_STEPS,
  OUTPUT_TYPES,
  PREVIEW_3D_BY_VIEW,
  PROJECTS,
  RAIL_ACTIONS,
  RENDER_STYLES,
  STYLE_THUMBS,
  type BottomActionKey,
  type CenterTabId,
  type DetectedSpace,
  type FlowStepId,
  type OutputTypeId,
  type RailActionId,
  type RenderStyleId,
  type ViewMode3d,
} from './architectural-studio-model';

import './architectural-studio.css';

export function ArchitecturalStudioWorkspace() {
  const t = useTranslations('creativeStudio.ds.architecturalStudio');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');

  const focus = useCreativeStudioFocusMode({
    storageKey: 'architectural-studio',
    defaultMode: 'normal',
    persist: false,
  });

  const [project, setProject] = useState<string>(PROJECTS[0].id);
  const [saved, setSaved] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [activeStep, setActiveStep] = useState<FlowStepId>('analyze');
  const [centerTab, setCenterTab] = useState<CenterTabId>('planAnalysis');
  const [brief, setBrief] = useState(DEMO_BRIEF);
  const [spaces, setSpaces] = useState<DetectedSpace[]>(DEMO_SPACES);
  const [selectedSpaceId, setSelectedSpaceId] = useState<string>(DEMO_SPACES[0]!.id);
  const [editingSpaceId, setEditingSpaceId] = useState<string | null>(null);
  const [view3d, setView3d] = useState<ViewMode3d>('isometric');
  const [renderStyle, setRenderStyle] = useState<RenderStyleId>('modern');
  const [interiorStyle, setInteriorStyle] = useState('luxury');
  const [exteriorStyle, setExteriorStyle] = useState('modernArch');
  const [resolution, setResolution] = useState('4k');
  const [camera, setCamera] = useState('natural');
  const [lighting, setLighting] = useState('daylight');
  const [outputType, setOutputType] = useState<OutputTypeId>('image');
  const [aiModel, setAiModel] = useState('investhome-v2');
  const [activeRail, setActiveRail] = useState<RailActionId>('layers');
  const [toast, setToast] = useState<string | null>(null);
  const [dockOverflowOpen, setDockOverflowOpen] = useState(false);

  const activeStepIndex = FLOW_STEPS.findIndex((s) => s.id === activeStep);

  const asRightRail: FocusRailItem[] = useMemo(
    () =>
      RAIL_ACTIONS.map((action) => ({
        id: action.id,
        icon: action.icon,
        labelKey: 'quickActions',
        label: t(`rail.actions.${action.id}`),
      })),
    [t],
  );

  const asLeftRail: FocusRailItem[] = useMemo(
    () => [
      {
        id: 'brief',
        icon: 'sparkles',
        labelKey: 'brief',
        label: t('left.briefTitle'),
      },
      {
        id: 'files',
        icon: 'documents',
        labelKey: 'assets',
        label: t('left.filesTitle'),
      },
    ],
    [t],
  );

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  function handleStep(id: FlowStepId) {
    setActiveStep(id);
    if (id === 'uploadPlan' || id === 'analyze') setCenterTab('planAnalysis');
    if (id === 'model3d') setCenterTab('model3d');
    if (id === 'render') setCenterTab('renderPreview');
    if (id === 'video') setCenterTab('videoPreview');
  }

  function handleGenerate() {
    setGenerating(true);
    showToast(t('toasts.generating'));
    window.setTimeout(() => {
      setGenerating(false);
      showToast(t('toasts.generated'));
    }, 1200);
  }

  function handleSave() {
    setSaved(true);
    showToast(t('toasts.saved'));
  }

  function handleBriefSend() {
    if (!brief.trim()) {
      setBrief(DEMO_BRIEF);
    }
    showToast(t('toasts.briefSent'));
  }

  function handleBottom(action: BottomActionKey) {
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function handleRail(id: RailActionId) {
    setActiveRail(id);
    showToast(t(`rail.toasts.${id}`));
  }

  function patchSpace(id: string, label: string) {
    setSpaces((prev) => prev.map((s) => (s.id === id ? { ...s, label } : s)));
    setSaved(false);
  }

  const showInlineRail = focus.mode === 'normal' && !focus.isFullscreen;

  const leftPanel = (
    <aside className="as-ws__left" aria-label={t('left.aria')} data-testid="as-left">
      <section className="as-ws__card" data-testid="as-brief-card">
        <div className="as-ws__card-head">
          <h2>{t('left.briefTitle')}</h2>
          <span className="as-ws__card-hint" title={t('left.briefHint')}>
            <IhIcon name="alert" size={12} />
          </span>
        </div>
        <label className="sr-only" htmlFor="as-brief">
          {t('left.briefLabel')}
        </label>
        <textarea
          id="as-brief"
          className="as-ws__brief"
          value={brief}
          maxLength={BRIEF_MAX}
          onChange={(e) => {
            setBrief(e.target.value);
            setSaved(false);
          }}
          placeholder={t('left.briefPlaceholder')}
          data-testid="as-brief"
        />
        <div className="as-ws__brief-meta">
          <span>
            {brief.length}/{BRIEF_MAX}
          </span>
          <Button
            variant="primary"
            size="sm"
            onClick={handleBriefSend}
            data-testid="as-brief-send"
          >
            {t('left.briefSend')}
          </Button>
        </div>
      </section>

      <section className="as-ws__card" data-testid="as-refs-card">
        <div className="as-ws__card-head">
          <h2>{t('left.refsTitle')}</h2>
          <button
            type="button"
            className="as-ws__icon-btn"
            aria-label={t('left.refsAdd')}
            onClick={() => showToast(t('toasts.refAdded'))}
            data-testid="as-refs-add"
          >
            <IhIcon name="plus" size={12} />
          </button>
        </div>
        <div className="as-ws__ref-grid">
          {DEMO_REFERENCES.map((ref) => (
            <button
              key={ref.id}
              type="button"
              className="as-ws__ref-thumb"
              onClick={() => showToast(t('toasts.refSelected'))}
              data-testid={`as-ref-${ref.id}`}
              title={ref.label}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={ref.url} alt={ref.label} />
            </button>
          ))}
        </div>
        <button
          type="button"
          className="as-ws__upload-drop"
          onClick={() => showToast(t('toasts.upload'))}
          data-testid="as-refs-drop"
        >
          <span className="as-ws__upload-drop-icon" aria-hidden="true">
            <IhIcon name="inbox" size={20} />
          </span>
          <span>{t('left.refsDrop')}</span>
        </button>
      </section>

      <section className="as-ws__card" data-testid="as-files-card">
        <div className="as-ws__card-head">
          <h2>{t('left.filesTitle')}</h2>
        </div>
        <ul className="as-ws__file-list">
          {DEMO_FILES.map((file) => (
            <li key={file.id} className="as-ws__file-row" data-testid={`as-file-${file.id}`}>
              <span className="as-ws__file-icon" aria-hidden="true">
                <IhIcon name={file.icon} size={13} />
              </span>
              <div>
                <div className="as-ws__file-name">{file.name}</div>
                <div className="as-ws__file-size">
                  {file.ext} · {file.sizeLabel}
                </div>
              </div>
              <button
                type="button"
                className="as-ws__icon-btn"
                aria-label={t('left.fileMenu')}
                onClick={() => showToast(t('toasts.fileMenu'))}
              >
                <IhIcon name="settings" size={12} />
              </button>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );

  const centerPlan = (
    <>
      <div className="as-ws__banner" data-testid="as-analysis-banner">
        <span>{t('center.banner', { count: spaces.length })}</span>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => showToast(t('toasts.editAnalysis'))}
          data-testid="as-edit-analysis"
        >
          {t('center.editAnalysis')}
        </Button>
      </div>

      <div className="as-ws__plan-stage">
        <div className="as-ws__plan-canvas" data-testid="as-plan-canvas">
          <svg
            className="as-ws__plan-svg"
            viewBox="0 0 420 320"
            role="img"
            aria-label={t('center.planAria')}
          >
            <defs>
              <pattern id="as-plan-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path
                  d="M20 0H0V20"
                  fill="none"
                  stroke="#d5e0e4"
                  strokeWidth="0.6"
                />
              </pattern>
            </defs>
            <rect x="0" y="0" width="420" height="320" fill="#f7fafb" />
            <rect x="0" y="0" width="420" height="320" fill="url(#as-plan-grid)" />
            {/* Outer shell */}
            <rect
              x="28"
              y="28"
              width="364"
              height="264"
              fill="#fff"
              stroke="#5a7380"
              strokeWidth="2.4"
            />
            {/* Internal walls — monochrome architectural plate */}
            <path
              d="M204 28V254 M146 154H204 M260 28V106 M260 106H204 M260 154V212 M300 28V106 M300 70H380 M340 70V106 M260 212H340 M340 154V254 M146 254V280 M28 254H146 M300 254H380"
              fill="none"
              stroke="#6a828e"
              strokeWidth="2"
            />
            {/* Door swings */}
            <path
              d="M196 154 A8 8 0 0 1 204 146 M252 106 A8 8 0 0 0 260 114 M146 246 A8 8 0 0 0 154 254"
              fill="none"
              stroke="#8aa0ab"
              strokeWidth="1.2"
            />
            {/* Soft room highlights */}
            {FLOOR_PLAN_HIGHLIGHTS.map((room) => (
              <rect
                key={room.id}
                className={`as-ws__plan-hl${selectedSpaceId === room.id ? ' is-selected' : ''}`}
                x={room.x}
                y={room.y}
                width={room.w}
                height={room.h}
                fill={room.color}
                rx="2"
                onClick={() => setSelectedSpaceId(room.id)}
              >
                <title>{room.label}</title>
              </rect>
            ))}
            {/* Dimension ticks */}
            <path
              d="M28 300H392 M36 296V304 M384 296V304"
              fill="none"
              stroke="#9aafb8"
              strokeWidth="1"
            />
            <text x="210" y="312" textAnchor="middle" fill="#718087" fontSize="9" fontWeight="600">
              A1 · 142.4 m²
            </text>
          </svg>
        </div>

        <div className="as-ws__spaces" data-testid="as-spaces">
          <h3 className="as-ws__spaces-title">
            {t('center.spacesTitle', { count: spaces.length })}
          </h3>
          {spaces.map((space) => (
            <div key={space.id}>
              {editingSpaceId === space.id ? (
                <input
                  className="as-ws__space-edit"
                  value={space.label}
                  autoFocus
                  aria-label={t('center.editLabel')}
                  onChange={(e) => patchSpace(space.id, e.target.value)}
                  onBlur={() => setEditingSpaceId(null)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') setEditingSpaceId(null);
                  }}
                  data-testid={`as-space-edit-${space.id}`}
                />
              ) : (
                <button
                  type="button"
                  className={`as-ws__space-row${selectedSpaceId === space.id ? ' is-selected' : ''}`}
                  onClick={() => setSelectedSpaceId(space.id)}
                  onDoubleClick={() => setEditingSpaceId(space.id)}
                  data-testid={`as-space-${space.id}`}
                >
                  <span
                    className="as-ws__space-dot"
                    style={{ background: space.color }}
                    aria-hidden="true"
                  />
                  <span className="as-ws__space-label">{space.label}</span>
                  <span className="as-ws__space-area">{space.areaM2.toFixed(1)} m²</span>
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="as-ws__metrics" data-testid="as-metrics">
        {DEMO_METRICS.map((metric) => (
          <div key={metric.id} className="as-ws__metric" data-testid={`as-metric-${metric.id}`}>
            <span className="as-ws__metric-icon" aria-hidden="true">
              <IhIcon name={metric.icon} size={18} />
            </span>
            <span className="as-ws__metric-label">{t(`center.metrics.${metric.id}`)}</span>
            <span className="as-ws__metric-value">{metric.value}</span>
          </div>
        ))}
      </div>
    </>
  );

  const centerPlaceholder = (tab: CenterTabId) => (
    <div className="as-ws__placeholder" data-testid={`as-placeholder-${tab}`}>
      <IhIcon name={tab === 'videoPreview' ? 'meeting' : 'projects'} size={24} />
      <h3>{t(`center.tabs.${tab}`)}</h3>
      <p>{t(`center.placeholders.${tab}`)}</p>
      <Button variant="primary" size="sm" onClick={handleGenerate}>
        <IhIcon name="sparkles" size={12} />
        {t('actions.generate')}
      </Button>
    </div>
  );

  const centerPanel = (
    <section className="as-ws__center" aria-label={t('center.aria')} data-testid="as-center">
      <div className="as-ws__tabs" role="tablist" aria-label={t('center.tabsAria')}>
        {CENTER_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={centerTab === tab}
            className={`as-ws__tab${centerTab === tab ? ' is-active' : ''}`}
            onClick={() => setCenterTab(tab)}
            data-testid={`as-tab-${tab}`}
          >
            {t(`center.tabs.${tab}`)}
          </button>
        ))}
      </div>
      <div className="as-ws__center-body">
        {centerTab === 'planAnalysis' ? centerPlan : centerPlaceholder(centerTab)}
      </div>
    </section>
  );

  const rightDetail = (
    <aside className="as-ws__right" aria-label={t('right.aria')} data-testid="as-right">
      <section className="as-ws__card" data-testid="as-preview-3d">
        <div className="as-ws__card-head">
          <h2>{t('right.preview3d')}</h2>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => showToast(t('toasts.fullscreen'))}
            data-testid="as-fullscreen"
          >
            {t('right.fullscreen')}
          </Button>
        </div>
        <div
          className="as-ws__preview-frame"
          data-testid="as-preview-hero"
          role="img"
          aria-label={t('right.previewAria')}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="as-ws__preview-hero" src={PREVIEW_3D_BY_VIEW[view3d]} alt="" />
        </div>
        <div className="as-ws__view-toggle" role="group" aria-label={t('right.viewAria')}>
          {(['isometric', 'plan', 'tour'] as ViewMode3d[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={view3d === mode ? 'is-active' : undefined}
              aria-pressed={view3d === mode}
              onClick={() => setView3d(mode)}
              data-testid={`as-view-${mode}`}
            >
              {t(`right.views.${mode}`)}
            </button>
          ))}
        </div>
      </section>

      <section className="as-ws__card" data-testid="as-quick-renders">
        <div className="as-ws__card-head">
          <h2>{t('right.quickRenders')}</h2>
          <button
            type="button"
            className="as-ws__link-btn"
            onClick={() => showToast(t('toasts.viewAllRenders'))}
          >
            {t('right.viewAll')}
          </button>
        </div>
        <div className="as-ws__render-strip">
          {DEMO_RENDERS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="as-ws__render-thumb"
              title={item.label}
              onClick={() => showToast(t('toasts.renderSelected'))}
              data-testid={`as-render-${item.id}`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={item.url} alt={item.label} />
            </button>
          ))}
        </div>
      </section>

      <section className="as-ws__card" data-testid="as-settings">
        <div className="as-ws__card-head">
          <h2>{t('right.settingsTitle')}</h2>
        </div>

        <div>
          <div className="as-ws__card-hint" style={{ marginBottom: 6 }}>
            {t('right.renderStyle')}
          </div>
          <div className="as-ws__style-grid" role="group" aria-label={t('right.renderStyle')}>
            {RENDER_STYLES.map((style) => (
              <button
                key={style}
                type="button"
                className={`as-ws__style-btn${renderStyle === style ? ' is-active' : ''}`}
                onClick={() => {
                  setRenderStyle(style);
                  setSaved(false);
                }}
                data-testid={`as-style-${style}`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={STYLE_THUMBS[style]} alt="" />
                <span>{t(`right.styles.${style}`)}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="as-ws__fields">
          <div className="as-ws__field">
            <label htmlFor="as-interior">{t('right.interior')}</label>
            <select
              id="as-interior"
              value={interiorStyle}
              onChange={(e) => setInteriorStyle(e.target.value)}
              data-testid="as-interior"
            >
              <option value="luxury">{t('right.options.interior.luxury')}</option>
              <option value="scandi">{t('right.options.interior.scandi')}</option>
              <option value="warm">{t('right.options.interior.warm')}</option>
            </select>
          </div>
          <div className="as-ws__field">
            <label htmlFor="as-exterior">{t('right.exterior')}</label>
            <select
              id="as-exterior"
              value={exteriorStyle}
              onChange={(e) => setExteriorStyle(e.target.value)}
              data-testid="as-exterior"
            >
              <option value="modernArch">{t('right.options.exterior.modernArch')}</option>
              <option value="classic">{t('right.options.exterior.classic')}</option>
              <option value="glass">{t('right.options.exterior.glass')}</option>
            </select>
          </div>
          <div className="as-ws__field">
            <label htmlFor="as-resolution">{t('right.resolution')}</label>
            <select
              id="as-resolution"
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              data-testid="as-resolution"
            >
              <option value="2k">{t('right.options.resolution.r2k')}</option>
              <option value="4k">{t('right.options.resolution.r4k')}</option>
              <option value="8k">{t('right.options.resolution.r8k')}</option>
            </select>
          </div>
          <div className="as-ws__field">
            <label htmlFor="as-camera">{t('right.camera')}</label>
            <select
              id="as-camera"
              value={camera}
              onChange={(e) => setCamera(e.target.value)}
              data-testid="as-camera"
            >
              <option value="natural">{t('right.options.camera.natural')}</option>
              <option value="wide">{t('right.options.camera.wide')}</option>
              <option value="drone">{t('right.options.camera.drone')}</option>
            </select>
          </div>
          <div className="as-ws__field">
            <label htmlFor="as-lighting">{t('right.lighting')}</label>
            <select
              id="as-lighting"
              value={lighting}
              onChange={(e) => setLighting(e.target.value)}
              data-testid="as-lighting"
            >
              <option value="daylight">{t('right.options.lighting.daylight')}</option>
              <option value="golden">{t('right.options.lighting.golden')}</option>
              <option value="night">{t('right.options.lighting.night')}</option>
            </select>
          </div>
        </div>

        <div>
          <div className="as-ws__card-hint" style={{ marginBottom: 6 }}>
            {t('right.outputType')}
          </div>
          <div className="as-ws__output-toggle" role="group" aria-label={t('right.outputType')}>
            {OUTPUT_TYPES.map((item) => (
              <button
                key={item.id}
                type="button"
                className={outputType === item.id ? 'is-active' : undefined}
                aria-pressed={outputType === item.id}
                onClick={() => setOutputType(item.id)}
                data-testid={`as-output-${item.id}`}
              >
                <IhIcon name={item.icon} size={13} />
                {t(`right.outputs.${item.id}`)}
              </button>
            ))}
          </div>
        </div>

        <div className="as-ws__field">
          <label htmlFor="as-model">{t('right.aiModel')}</label>
          <select
            id="as-model"
            value={aiModel}
            onChange={(e) => setAiModel(e.target.value)}
            data-testid="as-model"
          >
            <option value="investhome-v2">{t('right.options.model.v2')}</option>
            <option value="investhome-v1">{t('right.options.model.v1')}</option>
            <option value="fast">{t('right.options.model.fast')}</option>
          </select>
        </div>
      </section>
    </aside>
  );

  const inlineRightRail = showInlineRail ? (
    <nav
      className="cs-fw__rail cs-fw__rail--right"
      data-testid="as-rail"
      aria-label={t('rail.aria')}
    >
      {asRightRail.map((item) => {
        const isActive = activeRail === item.id;
        return (
          <button
            key={item.id}
            type="button"
            className={['cs-fw__rail-btn', isActive ? 'is-active' : '']
              .filter(Boolean)
              .join(' ')}
            data-testid={`as-rail-${item.id}`}
            title={item.label ?? tFocus(`rails.${item.labelKey}`)}
            aria-label={item.label ?? tFocus(`rails.${item.labelKey}`)}
            aria-pressed={isActive}
            onClick={() => handleRail(item.id as RailActionId)}
          >
            <IhIcon name={item.icon} size={16} />
          </button>
        );
      })}
    </nav>
  ) : null;

  const rightPanel = showInlineRail ? (
    <div className="as-ws__right-shell">
      {rightDetail}
      {inlineRightRail}
    </div>
  ) : (
    rightDetail
  );

  const bottomActionToolbar = (
    <CsBottomActionToolbar
      testId="as-bat"
      primary={{
        label: t('bottomBar.actions.addComponent'),
        icon: 'plus',
        onClick: () => handleBottom('addComponent'),
        testId: 'as-action-addComponent',
      }}
      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addComponent').map((action) => ({
        key: action.key,
        icon: action.icon,
        label: t(`bottomBar.actions.${action.key}`),
        onClick: () => handleBottom(action.key),
        testId: `as-action-${action.key}`,
      }))}
    />
  );

  return (
    <main className="dashboard" data-testid="architectural-studio-page">
      <div className="as-ws" data-testid="as-workspace">
        <header className="as-ws__header cs-page-header">
          <div>
            <Link href={AS_HOME as Route} className="as-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="as-ws__breadcrumb">
                <li>
                  <Link href={AS_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="as-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li>
                  <Link href={ARCHITECTURAL_STUDIO_ROUTE as Route}>
                    {tTools('architecturalStudio.title')}
                  </Link>
                </li>
                <li className="as-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="as-ws__breadcrumb-current" aria-current="page">
                  {t('newProduction')}
                </li>
              </ol>
            </nav>
            <h1>
              <span className="as-ws__title-icon" aria-hidden="true">
                <IhIcon name="projects" size={22} />
              </span>
              {tTools('architecturalStudio.title')}
            </h1>
            <p className="as-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="as-ws__header-right">
            <div className="as-ws__header-meta cs-page-header__meta">
              <div className="as-ws__project">
                <Select
                  id="as-project"
                  label={t('project')}
                  value={project}
                  onChange={(e) => setProject(e.target.value)}
                >
                  {PROJECTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </Select>
              </div>
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <StatusChip tone="warning">{t('approvalPending')}</StatusChip>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleSave}
              data-testid="as-save"
            >
              {t('actions.saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => showToast(t('toasts.versions'))}
              data-testid="as-versions"
            >
              {t('actions.versions')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => focus.setMode('preview')}
              data-testid="as-preview"
            >
              {t('actions.preview')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={generating}
              onClick={handleGenerate}
              data-testid="as-generate"
            >
              <IhIcon name="sparkles" size={13} />
              {generating ? t('actions.generating') : t('actions.generate')}
            </Button>
          </div>
        </header>

        <ol className="as-ws__flow" aria-label={t('flow.aria')} data-testid="as-flow">
          {FLOW_STEPS.map((step, index) => {
            const state =
              index < activeStepIndex ? 'is-done' : index === activeStepIndex ? 'is-active' : 'is-future';
            return (
              <li key={step.id} className={`as-ws__flow-item ${state}`}>
                <button
                  type="button"
                  className="as-ws__flow-btn"
                  onClick={() => handleStep(step.id)}
                  data-testid={`as-step-${step.id}`}
                >
                  <span className="as-ws__flow-index">
                    {index < activeStepIndex ? <IhIcon name="check" size={12} /> : index + 1}
                  </span>
                  <span className="as-ws__flow-title">{t(`flow.steps.${step.titleKey}`)}</span>
                  <span className="as-ws__flow-hint">{t(`flow.hints.${step.hintKey}`)}</span>
                </button>
              </li>
            );
          })}
        </ol>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="as-ws__layout"
          leftRail={asLeftRail}
          rightRail={asRightRail}
          onRightRailSelect={(id) => {
            if ((RAIL_ACTIONS.map((a) => a.id) as string[]).includes(id)) {
              handleRail(id as RailActionId);
            }
          }}
          left={leftPanel}
          center={centerPanel}
          right={rightPanel}
        />

        <FocusActionDock
          primary={bottomActionToolbar}
          visible
          pinned
          overflowOpen={dockOverflowOpen}
          onOverflowOpenChange={setDockOverflowOpen}
          testId="as-dock"
        />

        {toast ? (
          <div className="as-ws__toast" role="status" data-testid="as-toast">
            {toast}
          </div>
        ) : null}
      </div>
    </main>
  );
}
