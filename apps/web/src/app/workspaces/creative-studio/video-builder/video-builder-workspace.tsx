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
  AI_SUGGESTIONS,
  ASPECT_RATIOS,
  ASSET_COUNTS,
  BRAND_KIT,
  CAMPAIGN_STATUS_TONE,
  CANVAS_TABS,
  DEFAULT_BRIEF,
  DEFAULT_SCENES,
  DEFAULT_SCORES,
  EXPORT_FORMAT_OPTIONS,
  EXPORT_OPTIONS,
  EXPORT_RATIO_OPTIONS,
  FPS_OPTIONS,
  LEFT_SECTIONS,
  MUSIC_STYLES,
  PREVIEW_STATUS_CHIPS,
  QUICK_ACTIONS,
  RESOLUTIONS,
  SCENE_META_ICON,
  SCORE_FACTORS,
  VB_HOME,
  VB_PROJECTS,
  VOICES,
  WORKFLOW_STEPS,
  formatTimecode,
  getProject,
  scoreTone,
  totalDuration,
  type AiStatusKey,
  type AspectRatio,
  type CampaignBrief,
  type CampaignStatus,
  type CanvasTab,
  type ExportOptionKey,
  type Fps,
  type LeftSectionKey,
  type ProjectId,
  type QuickActionKey,
  type Resolution,
  type SuggestionKey,
  type VbScene,
  type VideoScores,
} from './video-builder-model';

import { CsBottomActionToolbar } from '../_components';
import {
  CreativeStudioFocusModeSwitcher,
  CreativeStudioFocusWorkspace,
  CS_FOCUS_LEFT_RAIL,
  CS_FOCUS_RIGHT_RAIL,
  FocusCanvasLayout,
  FocusFitStage,
  FocusFitToViewToolbar,
  useCreativeStudioFocusMode,
  useFitToViewEngine,
} from '../_components/focus-workspace';

import './video-builder.css';

const VIDEO_CONTENT_W = 1920;
const VIDEO_CONTENT_H = 1080;

export function VideoBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.videoBuilder');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');

  const [hydrated, setHydrated] = useState(false);
  const [projectId, setProjectId] = useState<ProjectId>('temple');
  const [activeStep, setActiveStep] = useState(2);
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus>('draft');
  const [saved, setSaved] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [aiStatus, setAiStatus] = useState<AiStatusKey>('completed');
  const [progressStep, setProgressStep] = useState(-1);
  const [brief, setBrief] = useState<CampaignBrief>(DEFAULT_BRIEF);
  const [openLeft, setOpenLeft] = useState<LeftSectionKey>('brief');
  const focus = useCreativeStudioFocusMode({ storageKey: 'video-builder' });
  const ftv = useFitToViewEngine({
    contentWidth: VIDEO_CONTENT_W,
    contentHeight: VIDEO_CONTENT_H,
    enabled: true,
    contentKey: `video-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}`,
    canvasType: 'artwork',
  });
  const [scores, setScores] = useState<VideoScores>(DEFAULT_SCORES);
  const [appliedSuggestions, setAppliedSuggestions] = useState<Set<SuggestionKey>>(new Set());
  const [scenes, setScenes] = useState<VbScene[]>(DEFAULT_SCENES);
  const [selectedSceneId, setSelectedSceneId] = useState('sc-1');
  const [canvasTab, setCanvasTab] = useState<CanvasTab>('generate');
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [resolution, setResolution] = useState<Resolution>('1080');
  const [fps, setFps] = useState<Fps>('30');
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(5);
  const [headline, setHeadline] = useState('');
  const [toast, setToast] = useState<string | null>(null);
  const [selectedVoice, setSelectedVoice] = useState<(typeof VOICES)[number]>('luxury');
  const [selectedMusic, setSelectedMusic] = useState<(typeof MUSIC_STYLES)[number]>('cinematic');
  const [exportFormat, setExportFormat] = useState<ExportOptionKey>('mp4');
  const [exportRatio, setExportRatio] = useState<ExportOptionKey>('16:9');
  const [scoreOpen, setScoreOpen] = useState(false);
  const scoreWrapRef = useRef<HTMLDivElement | null>(null);

  const genTimerRef = useRef<number[]>([]);
  const project = useMemo(() => getProject(projectId), [projectId]);
  const duration = totalDuration(scenes);
  const aspectClass =
    aspectRatio === '9:16' ? 'is-916' : aspectRatio === '1:1' ? 'is-11' : aspectRatio === '4:5' ? 'is-45' : '';

  useEffect(() => {
    setHydrated(true);
    setHeadline(t('canvas.headline'));
    return () => {
      genTimerRef.current.forEach((id) => window.clearTimeout(id));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!scoreOpen) return;
    function onDocPointer(event: MouseEvent) {
      if (!scoreWrapRef.current?.contains(event.target as Node)) setScoreOpen(false);
    }
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') setScoreOpen(false);
    }
    document.addEventListener('mousedown', onDocPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [scoreOpen]);

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

  function handleGenerate(action: QuickActionKey | 'entire' | 'regenerate' = 'entire') {
    clearGenTimers();
    setGenerating(true);
    setProgressStep(0);
    setAiStatus('thinking');
    setActiveStep(2);
    setCanvasTab('generate');

    AI_STATUS_SEQUENCE.forEach((status, index) => {
      const id = window.setTimeout(() => {
        setAiStatus(status);
        setProgressStep(Math.min(index, AI_PROGRESS_STEPS.length - 1));
        if (status === 'optimizing') {
          setScores((prev) => ({
            ...prev,
            overall: Math.min(99, prev.overall + 1),
            hookStrength: Math.min(99, prev.hookStrength + 1),
          }));
        }
        if (status === 'completed') {
          setGenerating(false);
          setProgressStep(AI_PROGRESS_STEPS.length);
          if (action === 'makeLuxury' || action === 'makeCinematic') {
            setHeadline(t('canvas.headlineAlt'));
          }
          if (action === 'tiktokVersion' || action === 'instagramReel') {
            setAspectRatio('9:16');
          }
          if (action === 'youtubeVersion') {
            setAspectRatio('16:9');
          }
          persistNow();
          showToast(t('toasts.generated'));
        }
      }, 400 * (index + 1));
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

  function addScene() {
    const copy: VbScene = {
      id: `sc-${Date.now()}`,
      kind: 'amenities',
      durationSec: 6,
      thumbUrl: project.coverUrl,
    };
    setScenes((prev) => [...prev, copy]);
    setSelectedSceneId(copy.id);
    showToast(t('toasts.sceneAdded'));
  }

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="vb-workspace-loading">
        <div className="vb-ws">
          <div className="vb-ws__skeleton" aria-hidden="true" />
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard" data-testid="vb-workspace">
      <div className="vb-ws" data-cs-workspace-mode={focus.mode} data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}>
        <header className="vb-ws__header cs-page-header">
          <div>
            <Link href={VB_HOME as Route} className="vb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="vb-ws__breadcrumb">
                <li>
                  <Link href={VB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="vb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="vb-ws__breadcrumb-current" aria-current="page">
                  {tTools('videoStudio.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="meeting" size={22} />
              {tTools('videoStudio.title')}
            </h1>
            <p className="vb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="vb-ws__header-meta cs-page-header__meta">
            <StatusChip tone="info">{t('badge')}</StatusChip>
            <StatusChip tone={saved ? 'success' : 'default'}>{saved ? t('saved') : t('draft')}</StatusChip>
            <StatusChip tone={CAMPAIGN_STATUS_TONE[campaignStatus]}>
              {t(`status.${campaignStatus}`)}
            </StatusChip>
          </div>
        </header>

        <div className="vb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="vb-ws__toolbar-left">
            <div className="vb-ws__project">
              <Select
                id="vb-project"
                label={t('fields.project')}
                value={projectId}
                onChange={(e) => {
                  const id = e.target.value as ProjectId;
                  setProjectId(id);
                  setBrief((prev) => ({ ...prev, project: getProject(id).name }));
                }}
              >
                {VB_PROJECTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div className="vb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <Button variant="secondary" size="sm" onClick={() => persistNow(true)} data-testid="vb-save">
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="vb-export"
              onClick={() => showToast(t('toasts.exported'))}
            >
              {t('export')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="vb-publish"
              onClick={() => {
                setCampaignStatus('scheduled');
                setActiveStep(4);
                showToast(t('toasts.scheduled'));
              }}
            >
              {t('publishSchedule')}
            </Button>
          </div>
        </div>

        <div
          className={`vb-ws__ai-status${generating || aiStatus !== 'idle' ? ' is-live' : ''}`}
          role="status"
          aria-live="polite"
          data-testid="vb-ai-status"
        >
          <span className="vb-ws__ai-status-dot" aria-hidden="true" />
          <span>{aiStatus === 'idle' ? t('aiStatus.idle') : t(`aiStatus.${aiStatus}`)}</span>
          {generating ? (
            <span className="vb-ws__ai-status-progress">
              {progressStep + 1}/{AI_PROGRESS_STEPS.length}
            </span>
          ) : null}
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="vb-ws__layout"
          leftRail={CS_FOCUS_LEFT_RAIL}
          rightRail={CS_FOCUS_RIGHT_RAIL}
          onLeftRailSelect={(id) => {
            const map: Record<string, LeftSectionKey> = {
              brief: 'brief',
              assets: 'assets',
              brand: 'brand',
              settings: 'voiceMusic',
              advanced: 'advanced',
            };
            if (map[id]) setOpenLeft(map[id]);
          }}
          left={
            <aside className="vb-ws__panel vb-ws__left" aria-label={t('left.aria')} data-testid="vb-left">
            <div className="vb-ws__panel-head">
              <h2>{t('left.title')}</h2>
              <StatusChip tone="info">{t('left.ready')}</StatusChip>
            </div>
            <div className="vb-ws__panel-body vb-ws__left-stack">
              {LEFT_SECTIONS.map((sectionKey) => {
                const open = openLeft === sectionKey;
                return (
                  <section key={sectionKey} className={`vb-ws__collapse${open ? ' is-open' : ''}`}>
                    <button
                      type="button"
                      className="vb-ws__collapse-trigger"
                      aria-expanded={open}
                      onClick={() => setOpenLeft(sectionKey)}
                      data-testid={`vb-left-${sectionKey}`}
                    >
                      <span className="vb-ws__collapse-trigger-text">
                        <span className="vb-ws__collapse-title">{t(`left.sections.${sectionKey}`)}</span>
                        {!open ? (
                          <span className="vb-ws__collapse-summary">
                            {t(`left.summaries.${sectionKey}`)}
                          </span>
                        ) : null}
                      </span>
                      <IhIcon name={open ? 'chevronDown' : 'chevronRight'} size={12} />
                    </button>

                    {open && sectionKey === 'brief' ? (
                      <div className="vb-ws__collapse-body" data-testid="vb-brief">
                        <div className="vb-ws__field-grid">
                          {(
                            [
                              ['videoType', brief.videoType],
                              ['project', brief.project],
                              ['audience', brief.audience],
                              ['duration', brief.duration],
                              ['language', brief.language],
                              ['tone', brief.tone],
                              ['cta', brief.cta],
                            ] as const
                          ).map(([key, value]) => (
                            <label key={key} className="vb-ws__field">
                              <span>{t(`brief.fields.${key}`)}</span>
                              <input
                                value={value}
                                onChange={(e) =>
                                  setBrief((prev) => ({ ...prev, [key]: e.target.value }))
                                }
                              />
                            </label>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'assets' ? (
                      <div className="vb-ws__collapse-body" data-testid="vb-assets">
                        <div className="vb-ws__asset-counts">
                          {ASSET_COUNTS.map((asset) => (
                            <div key={asset.key} className="vb-ws__asset-count">
                              <strong>{asset.count}</strong>
                              <span>{t(`assets.counts.${asset.key}`)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'brand' ? (
                      <div className="vb-ws__collapse-body" data-testid="vb-brand">
                        <div className="vb-ws__chip-row">
                          {BRAND_KIT.map((key) => (
                            <span key={key} className="vb-ws__chip is-good">
                              {t(`brandKit.${key}`)}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'voiceMusic' ? (
                      <div className="vb-ws__collapse-body" data-testid="vb-voice-music">
                        <p className="vb-ws__section-label">{t('voiceMusic.voice')}</p>
                        <div className="vb-ws__chip-row">
                          {VOICES.map((key) => (
                            <button
                              key={key}
                              type="button"
                              className={`vb-ws__chip${selectedVoice === key ? ' is-active' : ''}`}
                              onClick={() => setSelectedVoice(key)}
                            >
                              {t(`voices.${key}`)}
                            </button>
                          ))}
                        </div>
                        <p className="vb-ws__section-label">{t('voiceMusic.music')}</p>
                        <div className="vb-ws__chip-row">
                          {MUSIC_STYLES.map((key) => (
                            <button
                              key={key}
                              type="button"
                              className={`vb-ws__chip${selectedMusic === key ? ' is-active' : ''}`}
                              onClick={() => setSelectedMusic(key)}
                            >
                              {t(`music.${key}`)}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'advanced' ? (
                      <div className="vb-ws__collapse-body" data-testid="vb-advanced">
                        <div className="vb-ws__field-grid">
                          <label className="vb-ws__field">
                            <span>{t('canvas.aspectRatio')}</span>
                            <select
                              value={aspectRatio}
                              onChange={(e) => setAspectRatio(e.target.value as AspectRatio)}
                            >
                              {ASPECT_RATIOS.map((ratio) => (
                                <option key={ratio} value={ratio}>
                                  {ratio}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="vb-ws__field">
                            <span>{t('canvas.resolution')}</span>
                            <select
                              value={resolution}
                              onChange={(e) => setResolution(e.target.value as Resolution)}
                            >
                              {RESOLUTIONS.map((r) => (
                                <option key={r} value={r}>
                                  {r === '4k' ? '4K' : `${r}p`}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="vb-ws__field">
                            <span>{t('canvas.fps')}</span>
                            <select value={fps} onChange={(e) => setFps(e.target.value as Fps)}>
                              {FPS_OPTIONS.map((f) => (
                                <option key={f} value={f}>
                                  {f} FPS
                                </option>
                              ))}
                            </select>
                          </label>
                        </div>
                      </div>
                    ) : null}
                  </section>
                );
              })}
            </div>
            <div className="vb-ws__left-footer">
              <Button
                variant="primary"
                size="md"
                className="vb-ws__generate-btn"
                disabled={generating}
                data-testid="vb-generate"
                onClick={() => handleGenerate('entire')}
              >
                <IhIcon name="sparkles" size={14} />
                {generating ? t('generating') : t('generate')}
              </Button>
            </div>
          </aside>
          }
          center={
            <section className="vb-ws__panel vb-ws__center" aria-label={t('canvas.aria')}>
            <FocusCanvasLayout
              isFullscreen={focus.isFullscreen}
              stageTestId="vb-canvas-stage"
              toolbar={
            <>
            <div className="vb-ws__top-controls">
              <ol className="vb-ws__steps" aria-label={t('stepsAria')}>
                {WORKFLOW_STEPS.map((id, index) => (
                  <li key={id}>
                    <button
                      type="button"
                      className={`vb-ws__step${index === activeStep ? ' is-active' : ''}${index < activeStep ? ' is-done' : ''}`}
                      onClick={() => setActiveStep(index)}
                    >
                      <span className="vb-ws__step-index">{index + 1}</span>
                      <span>{t(`steps.${id}`)}</span>
                    </button>
                  </li>
                ))}
              </ol>
              <div className="vb-ws__tabs" role="tablist" aria-label={t('canvas.tabsAria')}>
                {CANVAS_TABS.map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    role="tab"
                    aria-selected={canvasTab === tab}
                    className={`vb-ws__tab${canvasTab === tab ? ' is-active' : ''}`}
                    onClick={() => setCanvasTab(tab)}
                  >
                    {t(`canvas.tabs.${tab}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="vb-ws__preview-toolbar" role="toolbar" aria-label={t('canvas.toolbarAria')}>
                <span className="vb-ws__tech-chip">{aspectRatio}</span>
                <span className="vb-ws__tech-chip">
                  {resolution === '4k' ? '4K' : `${resolution}p`}
                </span>
                <span className="vb-ws__tech-chip">{fps} FPS</span>
                <FocusFitToViewToolbar engine={ftv} className="vb-ws__ftv-toolbar" />
                <div className="vb-ws__status-chips" data-testid="vb-status-chips">
                  {PREVIEW_STATUS_CHIPS.map((chip) => (
                    <span key={chip} className="vb-ws__status-chip">
                      <span className="vb-ws__status-chip-dot" aria-hidden="true" />
                      {t(`canvas.statusChips.${chip}`)}
                    </span>
                  ))}
                </div>
                <button
                  type="button"
                  className={`vb-ws__fit-btn${focus.isFullscreen ? ' is-active' : ''}`}
                  aria-label={t('canvas.fullscreen')}
                  aria-pressed={focus.isFullscreen}
                  data-testid="vb-fullscreen"
                  onClick={focus.toggleFullscreen}
                >
                  {t('canvas.fullscreenShort')}
                </button>
              </div>
            </>
              }
              tray={{
                label: tFocus('tray.scenes'),
                count: scenes.length,
                testId: 'vb-timeline',
                handleTestId: 'vb-tray-handle',
                content: (
              <>
              <div className="vb-ws__scene-row" data-testid="vb-scene-row">
                {scenes.map((scene, index) => (
                  <button
                    key={scene.id}
                    type="button"
                    className={`vb-ws__scene-card${selectedSceneId === scene.id ? ' is-selected' : ''}`}
                    onClick={() => setSelectedSceneId(scene.id)}
                    data-testid={`vb-scene-${scene.id}`}
                  >
                    <div className="vb-ws__scene-thumb">
                      <img src={scene.thumbUrl} alt="" />
                      <span className="vb-ws__scene-duration">{formatTimecode(scene.durationSec)}</span>
                    </div>
                    <strong>
                      {index + 1}. {t(`scenes.${scene.kind}.title`)}
                    </strong>
                    {scene.meta && scene.meta.length > 0 ? (
                      <span className="vb-ws__scene-meta" aria-label={t(`scenes.${scene.kind}.title`)}>
                        {scene.meta.map((metaKey) => (
                          <span
                            key={metaKey}
                            className="vb-ws__scene-meta-icon"
                            title={t(`sceneMeta.${metaKey}`)}
                          >
                            <IhIcon name={SCENE_META_ICON[metaKey]} size={10} />
                          </span>
                        ))}
                      </span>
                    ) : null}
                  </button>
                ))}
              </div>
              <button type="button" className="vb-ws__add-scene" onClick={addScene} data-testid="vb-add-scene">
                <IhIcon name="sparkles" size={12} />
                {t('canvas.actions.addScene')}
              </button>
              </>
                ),
              }}
              dock={{
                testId: 'vb-scene-actions',
                className: 'vb-ws__scene-actions',
                primary: (
                  <CsBottomActionToolbar
                    testId="vb-bat"
                    ariaLabel={t('canvas.toolbarAria')}
                    primary={{
                      label: t('canvas.actions.regenerate'),
                      icon: 'sparkles',
                      onClick: () => handleGenerate('regenerate'),
                      testId: 'vb-action-regenerate',
                    }}
                    actions={[
                      {
                        key: 'editScene',
                        icon: 'design',
                        label: t('canvas.actions.editScene'),
                        onClick: () => showToast(t('toasts.editScene')),
                        testId: 'vb-action-edit',
                      },
                      {
                        key: 'replaceMedia',
                        icon: 'documents',
                        label: t('canvas.actions.replaceMedia'),
                        onClick: () => showToast(t('toasts.replaceMedia')),
                        testId: 'vb-action-replace',
                      },
                      ...(['makeCinematic', 'makeLuxury', 'lifestyleScene'] as const).map((key) => {
                        const quick = QUICK_ACTIONS.find((a) => a.key === key)!;
                        return {
                          key,
                          icon: quick.icon,
                          label: t(`quickActions.${key}`),
                          onClick: () => handleGenerate(key),
                          testId: `vb-action-${key}`,
                          priority: 'low' as const,
                        };
                      }),
                    ]}
                  />
                ),
              }}
            >
            <div className="vb-ws__preview-shell">
              <div className="vb-ws__ai-sources" data-testid="vb-ai-sources">
                <p className="vb-ws__ai-sources-title">{t('aiSources.title')}</p>
                <div className="vb-ws__ai-sources-list">
                  {AI_SOURCES.map((key) => (
                    <span key={key} className="vb-ws__ai-source-chip">
                      <span className="vb-ws__ai-source-check" aria-hidden="true">
                        ✓
                      </span>
                      {t(`aiSources.items.${key}`)}
                    </span>
                  ))}
                </div>
              </div>

              <FocusFitStage engine={ftv} artboardTestId="vb-video-preview">
              <div className={`vb-ws__player ${aspectClass}`}>
                <img src={project.coverUrl} alt={t('canvas.previewAlt')} />
                <div className="vb-ws__player-overlay">
                  <span className="vb-ws__player-badge">{project.featuredLabel}</span>
                  <h2>{headline || t('canvas.headline')}</h2>
                  <button type="button" className="vb-ws__player-cta">
                    {brief.cta || t('canvas.cta')}
                  </button>
                </div>
                <div className="vb-ws__player-controls">
                  <div className="vb-ws__player-progress" aria-hidden="true">
                    <span style={{ width: `${(currentTime / Math.max(1, duration)) * 100}%` }} />
                  </div>
                  <div className="vb-ws__player-controls-row">
                    <div className="vb-ws__player-controls-left">
                      <button
                        type="button"
                        className="vb-ws__player-btn vb-ws__player-btn--play"
                        aria-label={playing ? t('canvas.pause') : t('canvas.play')}
                        onClick={() => {
                          setPlaying((p) => !p);
                          setCurrentTime((ct) => (ct >= duration ? 0 : Math.min(duration, ct + 3)));
                        }}
                      >
                        <IhIcon name={playing ? 'check' : 'meeting'} size={13} />
                      </button>
                      <span className="vb-ws__player-time">
                        {formatTimecode(currentTime)} / {formatTimecode(duration)}
                      </span>
                    </div>
                    <span className="vb-ws__player-meta">{aspectRatio}</span>
                  </div>
                </div>
              </div>
              </FocusFitStage>
            </div>
            </FocusCanvasLayout>
          </section>
          }
          right={
            <aside className="vb-ws__panel vb-ws__right" aria-label={t('right.aria')} data-testid="vb-right">
            <div className="vb-ws__panel-head">
              <h2>{t('right.title')}</h2>
              <StatusChip tone={scoreTone(scores.overall)}>{t('right.excellent')}</StatusChip>
            </div>
            <div className="vb-ws__panel-body vb-ws__right-stack">
              <div className="vb-ws__panel-card vb-ws__score-hero-card" data-testid="vb-overall-score">
                <div className="vb-ws__score-wrap" ref={scoreWrapRef}>
                  <button
                    type="button"
                    className="vb-ws__score-trigger"
                    aria-expanded={scoreOpen}
                    aria-haspopup="dialog"
                    aria-label={t('right.scoreExplainAria')}
                    data-testid="vb-score-trigger"
                    onClick={() => setScoreOpen(true)}
                    onMouseEnter={() => setScoreOpen(true)}
                    onFocus={() => setScoreOpen(true)}
                  >
                    <div
                      className="vb-ws__score-ring"
                      style={{ ['--score' as string]: scores.overall }}
                      aria-label={t('right.overallScore')}
                    >
                      <strong>{scores.overall}</strong>
                      <span>/ 100</span>
                    </div>
                  </button>
                  {scoreOpen ? (
                    <div
                      className="vb-ws__score-popover"
                      role="dialog"
                      aria-label={t('right.scoreExplainAria')}
                      data-testid="vb-score-popover"
                    >
                      {SCORE_FACTORS.map((factor) => (
                        <div
                          key={factor.key}
                          className={`vb-ws__score-factor is-${factor.tone}`}
>
                          <span aria-hidden="true">{factor.tone === 'good' ? '✓' : '△'}</span>
                          <span>{t(`right.scoreFactors.${factor.key}`)}</span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div>
                  <p className="vb-ws__score-hero-title">{t('right.overallScore')}</p>
                </div>
              </div>

              <div className="vb-ws__panel-card" data-testid="vb-suggestions">
                <p className="vb-ws__section-label">{t('right.suggestionsTitle')}</p>
                <div className="vb-ws__suggestions">
                  {AI_SUGGESTIONS.map((key) => (
                    <div key={key} className="vb-ws__suggestion-card">
                      <span>{t(`suggestions.${key}`)}</span>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={appliedSuggestions.has(key)}
                        onClick={() => applySuggestion(key)}
                      >
                        {appliedSuggestions.has(key) ? t('right.applied') : t('right.apply')}
                      </Button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="vb-ws__panel-card" data-testid="vb-quick-actions">
                <p className="vb-ws__section-label">{t('right.quickActionsTitle')}</p>
                <div className="vb-ws__quick-grid">
                  {QUICK_ACTIONS.map((action) => (
                    <button
                      key={action.key}
                      type="button"
                      className="vb-ws__quick-btn"
                      onClick={() => handleGenerate(action.key)}
                    >
                      <IhIcon name={action.icon} size={13} />
                      <span>{t(`quickActions.${action.key}`)}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="vb-ws__panel-card" data-testid="vb-export">
                <p className="vb-ws__section-label">{t('right.exportTitle')}</p>
                <div className="vb-ws__export-groups">
                  <div className="vb-ws__export-group">
                    <span className="vb-ws__export-group-label">{t('right.exportFormat')}</span>
                    <div className="vb-ws__export-grid">
                      {EXPORT_FORMAT_OPTIONS.map((key) => (
                        <button
                          key={key}
                          type="button"
                          className={`vb-ws__export-chip${exportFormat === key ? ' is-selected' : ''}`}
                          aria-pressed={exportFormat === key}
                          onClick={() => {
                            setExportFormat(key);
                            showToast(t(`right.exports.${key}`));
                          }}
                        >
                          {t(`right.exports.${key}`)}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="vb-ws__export-group">
                    <span className="vb-ws__export-group-label">{t('right.exportRatio')}</span>
                    <div className="vb-ws__export-grid">
                      {EXPORT_RATIO_OPTIONS.map((key) => (
                        <button
                          key={key}
                          type="button"
                          className={`vb-ws__export-chip${exportRatio === key ? ' is-selected' : ''}`}
                          aria-pressed={exportRatio === key}
                          onClick={() => {
                            setExportRatio(key);
                            showToast(t(`right.exports.${key}`));
                          }}
                        >
                          {t(`right.exports.${key}`)}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="vb-ws__export-grid">
                    {EXPORT_OPTIONS.filter((key) => key === 'gif').map((key) => (
                      <button
                        key={key}
                        type="button"
                        className="vb-ws__export-chip"
                        onClick={() => showToast(t(`right.exports.${key}`))}
                      >
                        {t(`right.exports.${key}`)}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="vb-ws__export-actions">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => showToast(t('toasts.shared'))}
                  >
                    {t('right.share')}
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      setCampaignStatus('scheduled');
                      showToast(t('toasts.scheduled'));
                    }}
                  >
                    {t('right.schedulePublish')}
                  </Button>
                </div>
              </div>
            </div>
          </aside>
          }
        />
      </div>

      {toast ? (
        <div className="vb-ws__toast" role="status" data-testid="vb-toast">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
