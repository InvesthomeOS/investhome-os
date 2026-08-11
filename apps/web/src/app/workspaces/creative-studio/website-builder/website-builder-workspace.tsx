'use client';

import type { Route } from 'next';
import Link from 'next/link';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
} from 'react';
import { useTranslations } from 'next-intl';

import { Button, SegmentedControl, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  AI_PROGRESS_STEPS,
  AI_STATUS_SEQUENCE,
  ASSET_FILTERS,
  ASSET_FOLDERS,
  ASSET_SORTS,
  BLOCK_LIBRARY,
  type BlockKey,
  CONTEXTUAL_AI_BY_SECTION,
  DEFAULT_SECTIONS,
  normalizeWbSections,
  DEFAULT_SPLIT_PRESET,
  DESIGN_ACCORDIONS,
  DEVICE_ICONS,
  DEVICE_PREVIEWS,
  KEYBOARD_SHORTCUTS,
  MEMORY_CHIPS,
  MEMORY_READY,
  PROJECT_DATA_STATS,
  PUBLISH_CHECKS,
  PUBLISH_QUALITY_CHECK_KEYS,
  PUBLISH_EXPORTS,
  PUBLISH_STATUS_TONE,
  QUICK_AI_ACTIONS,
  RECENT_PROMPTS,
  RIGHT_TABS,
  SECTION_ACTIONS,
  SECTION_ICONS,
  SPLIT_PRESETS,
  SUGGESTED_PROMPTS,
  VERSION_ACTIONS,
  WB_CHAT,
  WB_HOME,
  WB_PROJECTS,
  WORKFLOW_STEPS,
  ZOOM_DEFAULT,
  ZOOM_SEGMENTS,
  ZOOM_MAX,
  ZOOM_MIN,
  ZOOM_STEP,
  type AiActionKey,
  type AiStatusKey,
  type AssetKind,
  type AssetSort,
  type DesignAccordionKey,
  type DevicePreview,
  type EditTarget,
  type LeftSectionKey,
  type MemoryKey,
  type PreviewDevice,
  type PublishCheckKey,
  type PublishStatus,
  type RightTab,
  type SectionActionKey,
  type SplitPanePreset,
  type WbAsset,
  type WbChatMessage,
  type WbProject,
  type WbSection,
  type WbVersion,
} from './website-builder-model';
import type { WbDocumentDraft, WbEditorPersistInput, WbImageRef } from './website-builder-persistence';
import { useWebsiteBuilderDocument } from './use-website-builder-document';
import { useWebsiteBuilderMedia } from './use-website-builder-media';
import { CsBuilderBootstrapView } from '../_components/cs-builder-bootstrap-view';
import { useCsBuilderHydration } from '../_components/use-cs-builder-hydration';
import {
  imageRefFromMediaAsset,
  imageRefFromWbAsset,
  isMediaAssetUuid,
  resolveDisplayUrl,
  resolveGalleryDisplayUrls,
  WB_IMAGE_PLACEHOLDER,
} from './website-builder-media';

import {
  CreativeStudioFocusModeSwitcher,
  CreativeStudioFocusWorkspace,
  FocusCanvasLayout,
  FocusFitStage,
  FocusFitToViewToolbar,
  useCreativeStudioFocusMode,
  useFitToViewEngine,
  type FocusRailItem,
} from '../_components/focus-workspace';
import { CarouselDots, CsBottomActionToolbar, CsStructureGrid } from '../_components';

import {
  WbLeftRailDrawer,
  WbRightRailDrawer,
  type WbLeftRailId,
  type WbRightRailId,
} from './website-builder-rail-drawers';
import { WbSectionToolbar } from './wb-section-overflow-menu';

import './website-builder.css';

const WB_CONTENT_W = 1440;
const WB_CONTENT_H = 900;

const LEFT_SECTIONS: LeftSectionKey[] = [
  'conversation',
  'suggested',
  'memory',
  'context',
  'assets',
  'recent',
];

const USED_IN_LABEL: Record<string, string> = {
  hero: 'Hero',
  gallery: 'Gallery',
  cta: 'Landing Page',
  homepage: 'Homepage',
  landing: 'Landing Page',
  downloads: 'Downloads',
};

function chatMessageText(
  msg: WbChatMessage,
  t: (key: string, values?: Record<string, string | number>) => string,
  projectName: string,
): string {
  if (msg.text) return msg.text;
  if (!msg.textKey) return '';
  const counts: Record<string, number> = {
    welcomePhotos: PROJECT_DATA_STATS.photos,
    welcomePlans: PROJECT_DATA_STATS.plans,
    welcomeBrochures: PROJECT_DATA_STATS.brochures,
  };
  if (msg.textKey in counts) {
    return t(`chat.${msg.textKey}`, { count: counts[msg.textKey] });
  }
  return t(`chat.${msg.textKey}`, { project: projectName });
}

function sectionLabel(section: WbSection, t: (key: string) => string): string {
  return section.customName || t(`sections.${section.key}`);
}

function clampZoom(value: number): number {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(value / ZOOM_STEP) * ZOOM_STEP));
}

function visualTemplateForProject(projectId: string): WbProject {
  let hash = 0;
  for (let i = 0; i < projectId.length; i += 1) {
    hash = (hash + projectId.charCodeAt(i) * (i + 1)) % WB_PROJECTS.length;
  }
  return WB_PROJECTS[hash] ?? WB_PROJECTS[0]!;
}

function buildDisplayProject(
  constructionProjectId: string | null,
  projectName: string,
  city: string,
  slug: string,
): WbProject {
  const visual = visualTemplateForProject(constructionProjectId || projectName || 'default');
  return {
    ...visual,
    name: projectName || visual.name,
    city: city || visual.city,
    slug: slug || visual.slug,
    featuredLabel: projectName || visual.featuredLabel,
  };
}

export function WebsiteBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.websiteBuilder');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tCommon = useTranslations('common');
  const tBootstrap = useTranslations('creativeStudio.ds.bootstrap');

  const docApi = useWebsiteBuilderDocument();
  const mediaApi = useWebsiteBuilderMedia({
    linkedProjectId: docApi.constructionProjectId,
    // constructionProjectId is set only after Document API bootstrap completes.
    enabled: Boolean(docApi.constructionProjectId) && docApi.loadStatus === 'ready',
  });
  const { ensureDisplayUrl, search: searchMedia, refresh: refreshMedia } = mediaApi;
  const contentDefaultsAppliedRef = useRef(false);
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const [restoreConfirmId, setRestoreConfirmId] = useState<string | null>(null);

  const [device, setDevice] = useState<DevicePreview>('desktop');
  const [splitPreset, setSplitPreset] = useState<SplitPanePreset>(DEFAULT_SPLIT_PRESET);
  const [zoom, setZoom] = useState(ZOOM_DEFAULT);
  const [activeStep, setActiveStep] = useState(1);
  const [rightTab, setRightTab] = useState<RightTab>('properties');
  const [assetFilter, setAssetFilter] = useState<'all' | AssetKind>('all');
  const [assetFolder, setAssetFolder] = useState<(typeof ASSET_FOLDERS)[number]>('all');
  const [assetSort, setAssetSort] = useState<AssetSort>('recent');
  const [assetQuery, setAssetQuery] = useState('');
  const [selectedAssets, setSelectedAssets] = useState<string[]>([]);
  const [previewAssetId, setPreviewAssetId] = useState<string | null>(null);
  const [brief, setBrief] = useState('');
  const [saved, setSaved] = useState(false);
  const [lastSavedLabel, setLastSavedLabel] = useState('');
  const [generating, setGenerating] = useState(false);
  const [aiStatus, setAiStatus] = useState<AiStatusKey>('idle');
  const [publishStatus, setPublishStatus] = useState<PublishStatus>('draft');
  const [sections, setSections] = useState<WbSection[]>(DEFAULT_SECTIONS);
  const [selectedSectionId, setSelectedSectionId] = useState('s-hero');
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null);
  const [compareVersionId, setCompareVersionId] = useState<string | null>(null);
  const [versionComment, setVersionComment] = useState('');
  const [metaTitle, setMetaTitle] = useState('Investhome | THE TEMPLE Residences');
  const [metaDesc, setMetaDesc] = useState(
    'Premium U.S. real-estate investment opportunities by Investhome — featuring THE TEMPLE Residences.',
  );
  const [slug, setSlug] = useState('the-temple-residences');
  const [tone, setTone] = useState('luxury');
  const [language, setLanguage] = useState('tr');
  const [chat, setChat] = useState<WbChatMessage[]>(WB_CHAT);
  const [openLeft, setOpenLeft] = useState<Record<LeftSectionKey, boolean>>({
    conversation: true,
    suggested: true,
    memory: true,
    context: true,
    assets: true,
    recent: false,
  });
  const focus = useCreativeStudioFocusMode({ storageKey: 'website-builder' });
  const ftv = useFitToViewEngine({
    contentWidth: WB_CONTENT_W,
    contentHeight: WB_CONTENT_H,
    enabled: true,
    contentKey: `wb-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}`,
    canvasType: 'document',
    // Document preview fills stage height; keep a thin side matte only.
    padX: 8,
    padY: 0,
  });
  const [dragSectionId, setDragSectionId] = useState<string | null>(null);
  const [dropTargetId, setDropTargetId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [toast, setToast] = useState<string | null>(null);
  const [reusedAssets, setReusedAssets] = useState<string[]>([]);
  const [historyPast, setHistoryPast] = useState<WbSection[][]>([]);
  const [historyFuture, setHistoryFuture] = useState<WbSection[][]>([]);
  const [heroImage, setHeroImage] = useState<WbImageRef | null>(null);
  const [galleryImages, setGalleryImages] = useState<WbImageRef[]>([]);
  const [resolvedHeroUrl, setResolvedHeroUrl] = useState<string | null>(null);
  const [resolvedGalleryUrls, setResolvedGalleryUrls] = useState<Record<string, string>>({});
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishChecks, setPublishChecks] = useState<Record<PublishCheckKey, boolean>>(() =>
    Object.fromEntries(PUBLISH_CHECKS.map((c) => [c.key, c.defaultPass])) as Record<
      PublishCheckKey,
      boolean
    >,
  );
  const [publishOverride, setPublishOverride] = useState(false);

  const [sectionMoreOpenId, setSectionMoreOpenId] = useState<string | null>(null);
  const [focusLeftRailId, setFocusLeftRailId] = useState<WbLeftRailId>('brief');
  const [focusRightRailId, setFocusRightRailId] = useState<WbRightRailId>('score');
  const [railGroups, setRailGroups] = useState<Record<string, boolean>>({
    'brief-goal': true,
    'assets-images': true,
    'brand-logo': true,
    'settings-view': true,
    'adv-seo': true,
  });
  const [siteGoal, setSiteGoal] = useState(
    'Premium investor homepage that converts qualified leads for THE TEMPLE.',
  );
  const [audience, setAudience] = useState(
    'High-net-worth investors evaluating U.S. residential opportunities.',
  );
  const [mainMessage, setMainMessage] = useState(
    'Refined Washington DC residences with institutional-grade investment clarity.',
  );
  const [railSuggestions, setRailSuggestions] = useState([
    {
      id: 's1',
      title: 'Strengthen hero CTA contrast',
      severity: 'high' as const,
      category: 'Hero',
      explanation: 'Primary CTA competes with secondary — increase emphasis on Schedule a Call.',
    },
    {
      id: 's2',
      title: 'Add floor-plan proof near gallery',
      severity: 'medium' as const,
      category: 'Gallery',
      explanation: 'Investors expect plan previews within two scrolls of hero.',
    },
    {
      id: 's3',
      title: 'Tighten meta description length',
      severity: 'low' as const,
      category: 'SEO',
      explanation: 'Meta description is slightly long for SERP truncation.',
    },
  ]);

  const [aiQuality, setAiQuality] = useState({
    overall: 78,
    seo: 82,
    accessibility: 80,
    performance: 76,
    content: 84,
    updatedAt: 'Just now',
  });
  const [heroTitle, setHeroTitle] = useState('');
  const [heroBody, setHeroBody] = useState('');
  const [ctaPrimary, setCtaPrimary] = useState('');
  const [ctaSecondary, setCtaSecondary] = useState('');
  const [progressStep, setProgressStep] = useState(-1);
  const [deviceAnimating, setDeviceAnimating] = useState(false);
  const [navMenuOpen, setNavMenuOpen] = useState(false);
  const [galleryIndex, setGalleryIndex] = useState(0);
  const [faqOpenIndex, setFaqOpenIndex] = useState<number | null>(null);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [openAccordions, setOpenAccordions] = useState<Record<DesignAccordionKey, boolean>>({
    hero: true,
    typography: false,
    buttons: false,
    background: false,
    overlay: false,
    animation: false,
    spacing: false,
    seo: false,
    accessibility: false,
    advanced: false,
  });

  const canvasStageRef = useRef<HTMLDivElement>(null);
  const scrollPreserveRef = useRef(0);
  const genTimerRef = useRef<number[]>([]);

  const selectedConstruction = useMemo(
    () =>
      docApi.constructionProjects.find((p) => p.id === docApi.constructionProjectId) ?? null,
    [docApi.constructionProjects, docApi.constructionProjectId],
  );

  const project = useMemo(() => {
    const city = [selectedConstruction?.city, selectedConstruction?.state]
      .filter(Boolean)
      .join(', ');
    return buildDisplayProject(
      docApi.constructionProjectId,
      selectedConstruction?.project_name ?? '',
      city,
      selectedConstruction?.slug ?? '',
    );
  }, [docApi.constructionProjectId, selectedConstruction]);

  const versions = docApi.versions;
  const activeVersionId = docApi.activeVersionId;
  const selectedSection = sections.find((s) => s.id === selectedSectionId) ?? sections[0];
  const activeVersion: WbVersion =
    versions.find((v) => v.id === activeVersionId) ??
    versions[0] ?? {
      id: '',
      label: '—',
      status: 'draft',
      updatedAt: '—',
      noteKey: 'initial',
    };
  const libraryAssets = mediaApi.assets;
  const previewAsset = libraryAssets.find((a) => a.id === previewAssetId) ?? null;
  const selectedPrimaryAsset = useMemo(() => {
    const id = selectedAssets[0];
    return id ? libraryAssets.find((a) => a.id === id) ?? null : null;
  }, [libraryAssets, selectedAssets]);
  const heroCover =
    resolveDisplayUrl({
      ref: heroImage,
      resolvedAssetUrl: resolvedHeroUrl,
      templateUrl: project.coverUrl,
      placeholderUrl: WB_IMAGE_PLACEHOLDER,
    }) || WB_IMAGE_PLACEHOLDER;
  const galleryUrls = (() => {
    const resolved = resolveGalleryDisplayUrls({
      refs: galleryImages,
      resolvedByAssetId: resolvedGalleryUrls,
      templateUrls: project.galleryUrls,
      placeholderUrl: WB_IMAGE_PLACEHOLDER,
    });
    return resolved.length ? resolved : project.galleryUrls;
  })();
  const splitPanes = SPLIT_PRESETS[splitPreset];
  const allQualityChecksPass = PUBLISH_QUALITY_CHECK_KEYS.every((k) => publishChecks[k]);
  const canPublish = allQualityChecksPass || publishOverride;

  const contextualAiActions = useMemo(() => {
    const keys = CONTEXTUAL_AI_BY_SECTION[selectedSection?.key ?? 'default'] ?? CONTEXTUAL_AI_BY_SECTION.default;
    return QUICK_AI_ACTIONS.filter((action) => keys.includes(action.key));
  }, [selectedSection?.key]);

  const wbLeftRail: FocusRailItem[] = useMemo(
    () => [
      { id: 'brief', icon: 'documents', labelKey: 'brief', label: t('rails.labels.brief') },
      { id: 'assets', icon: 'inventory', labelKey: 'assets', label: t('rails.labels.assets') },
      { id: 'brand', icon: 'design', labelKey: 'brand', label: t('rails.labels.brand') },
      { id: 'settings', icon: 'settings', labelKey: 'settings', label: t('rails.labels.settings') },
      { id: 'advanced', icon: 'sparkles', labelKey: 'advanced', label: t('rails.labels.advanced') },
    ],
    [t],
  );
  const wbRightRail: FocusRailItem[] = useMemo(
    () => [
      { id: 'score', icon: 'trendingUp', labelKey: 'score', label: t('rails.labels.score') },
      {
        id: 'suggestions',
        icon: 'sparkles',
        labelKey: 'suggestions',
        label: t('rails.labels.suggestions'),
      },
      {
        id: 'quickActions',
        icon: 'quickAction',
        labelKey: 'quickActions',
        label: t('rails.labels.quickActions'),
      },
      { id: 'export', icon: 'inbox', labelKey: 'export', label: t('rails.labels.export') },
      { id: 'history', icon: 'clock', labelKey: 'history', label: t('rails.labels.history') },
    ],
    [t],
  );

  function toggleRailGroup(key: string) {
    setRailGroups((prev) => ({ ...prev, [key]: !(prev[key] ?? false) }));
  }

  function toggleSelectedAsset(id: string) {
    setSelectedAssets((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function renderSectionToolbar(section: WbSection, variant: 'default' | 'hero' = 'default') {
    return (
      <WbSectionToolbar
        sectionId={section.id}
        open={sectionMoreOpenId === section.id}
        onOpenChange={(open) => setSectionMoreOpenId(open ? section.id : null)}
        onEdit={() => {
          setSectionMoreOpenId(null);
          selectSection(section, variant === 'hero' ? 'hero' : 'section');
        }}
        onAdd={() => {
          setSectionMoreOpenId(null);
          addSectionAfter(section);
        }}
        onAi={() => {
          setSectionMoreOpenId(null);
          setSelectedSectionId(section.id);
          handleGenerate('section');
        }}
        labels={{
          edit: t('sectionActions.edit'),
          add: t('sectionActions.add'),
          ai: t('sectionActions.ai'),
          more: t('sectionActions.more'),
        }}
        variant={variant}
        moreItems={[
          {
            key: 'edit',
            label: t('sectionActions.edit'),
            onSelect: () => selectSection(section, variant === 'hero' ? 'hero' : 'section'),
          },
          {
            key: 'duplicate',
            label: t('sectionActions.duplicate'),
            onSelect: () => duplicateSection(section),
          },
          {
            key: 'up',
            label: t('sectionActions.moveUp'),
            disabled: sections.findIndex((s) => s.id === section.id) <= 0,
            onSelect: () => moveSection(section.id, -1),
          },
          {
            key: 'down',
            label: t('sectionActions.moveDown'),
            disabled:
              sections.findIndex((s) => s.id === section.id) >= sections.length - 1,
            onSelect: () => moveSection(section.id, 1),
          },
          {
            key: 'hide',
            label: t('sectionActions.hide'),
            onSelect: () => hideSection(section.id),
          },
          {
            key: 'settings',
            label: t('sectionActions.settings'),
            onSelect: () => {
              selectSection(section, variant === 'hero' ? 'hero' : 'section');
              setRightTab('properties');
            },
          },
          {
            key: 'delete',
            label: t('sectionActions.delete'),
            destructive: true,
            disabled: sections.length <= 1,
            onSelect: () => deleteSection(section.id),
          },
        ]}
      />
    );
  }

  const completedProgressSteps = useMemo(() => {
    if (progressStep < 0) return 0;
    return Math.min(progressStep + 1, AI_PROGRESS_STEPS.length);
  }, [progressStep]);

  const filteredAssets = useMemo(() => {
    const q = assetQuery.trim().toLowerCase();
    const list = libraryAssets.filter((a) => {
      if (assetFilter !== 'all' && a.kind !== assetFilter) return false;
      if (assetFolder !== 'all' && a.folder !== assetFolder) return false;
      if (!q) return true;
      return (
        a.titleKey.toLowerCase().includes(q) ||
        a.filename.toLowerCase().includes(q) ||
        a.kind.includes(q) ||
        a.tags.some((tag) => tag.includes(q)) ||
        a.folder.includes(q)
      );
    });
    return [...list].sort((a, b) => {
      if (assetSort === 'name') return a.filename.localeCompare(b.filename);
      if (assetSort === 'type') return a.kind.localeCompare(b.kind);
      return b.id.localeCompare(a.id);
    });
  }, [assetFilter, assetFolder, assetQuery, assetSort, libraryAssets]);

  const aiContextCounts = useMemo(() => {
    const brandKit = libraryAssets.filter((a) => a.kind === 'brand').length;
    const crm = 86; // demo dataset row count
    const photos = PROJECT_DATA_STATS.photos;
    const floorPlans = PROJECT_DATA_STATS.plans;
    const brochures = PROJECT_DATA_STATS.brochures;
    const investorDocs = libraryAssets.filter((a) =>
      ['investorDeck', 'word', 'powerpoint', 'documents'].includes(a.kind),
    ).length;
    return { brandKit, crm, photos, floorPlans, brochures, investorDocs };
  }, [libraryAssets]);

  const deviceOptions = useMemo(
    () =>
      DEVICE_PREVIEWS.map((d) => ({
        value: d,
        label: (
          <span className="wb-ws__device-label">
            <IhIcon name={DEVICE_ICONS[d]} size={13} />
            <span>{t(`canvas.device.${d}`)}</span>
          </span>
        ),
      })),
    [t],
  );

  const pushHistory = useCallback(
    (next: WbSection[]) => {
      setHistoryPast((prev) => [...prev.slice(-24), sections]);
      setHistoryFuture([]);
      setSections(next);
    },
    [sections],
  );

  const undo = useCallback(() => {
    setHistoryPast((past) => {
      if (!past.length) return past;
      const prev = past[past.length - 1];
      setHistoryFuture((f) => [sections, ...f]);
      setSections(prev);
      return past.slice(0, -1);
    });
  }, [sections]);

  const redo = useCallback(() => {
    setHistoryFuture((future) => {
      if (!future.length) return future;
      const [next, ...rest] = future;
      setHistoryPast((p) => [...p, sections]);
      setSections(next);
      return rest;
    });
  }, [sections]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2200);
  }, []);

  const buildPersistInput = useCallback((): WbEditorPersistInput => {
    return {
      linkedProjectId: docApi.constructionProjectId,
      sections,
      selectedSectionId,
      metaTitle,
      metaDesc,
      slug,
      publishStatus,
      language,
      tone,
      brief,
      siteGoal,
      audience,
      mainMessage,
      heroTitle,
      heroBody,
      ctaPrimary,
      ctaSecondary,
      heroImage,
      galleryImages,
      device,
      zoom,
      splitPreset,
    };
  }, [
    docApi.constructionProjectId,
    sections,
    selectedSectionId,
    metaTitle,
    metaDesc,
    slug,
    publishStatus,
    language,
    tone,
    brief,
    siteGoal,
    audience,
    mainMessage,
    heroTitle,
    heroBody,
    ctaPrimary,
    ctaSecondary,
    heroImage,
    galleryImages,
    device,
    zoom,
    splitPreset,
  ]);

  const applyDraftToEditor = useCallback(
    (draft: WbDocumentDraft | null, options?: { applyContentDefaults?: boolean }) => {
      if (!draft) {
        if (options?.applyContentDefaults !== false) {
          contentDefaultsAppliedRef.current = false;
        }
        return;
      }
      setSelectedSectionId(draft.selectedSectionId || 's-hero');
      if (draft.device) setDevice(draft.device);
      setLanguage(draft.language || 'tr');
      setTone(draft.tone || 'luxury');
      setPublishStatus(draft.publishStatus || 'draft');
      setSections(normalizeWbSections(draft.sections));
      setMetaTitle(draft.metaTitle);
      setMetaDesc(draft.metaDesc);
      setSlug(draft.slug);
      if (typeof draft.zoom === 'number') setZoom(clampZoom(draft.zoom));
      if (draft.splitPreset) setSplitPreset(draft.splitPreset);
      setBrief(draft.brief);
      setSiteGoal(draft.siteGoal);
      setAudience(draft.audience);
      setMainMessage(draft.mainMessage);
      setHeroTitle(draft.heroTitle);
      setHeroBody(draft.heroBody);
      setCtaPrimary(draft.ctaPrimary);
      setCtaSecondary(draft.ctaSecondary);
      setHeroImage(draft.heroImage);
      setGalleryImages(draft.galleryImages ?? []);
      const hasContent = Boolean(
        draft.heroTitle.trim() ||
          draft.heroBody.trim() ||
          draft.ctaPrimary.trim() ||
          draft.ctaSecondary.trim(),
      );
      contentDefaultsAppliedRef.current = hasContent;
    },
    [],
  );

  const persistNow = useCallback(
    async (markSaved = true) => {
      if (docApi.loadStatus !== 'ready') return;
      const ok = await docApi.saveDraft(buildPersistInput());
      if (ok && markSaved) {
        setSaved(true);
        setLastSavedLabel(t('savedJustNow'));
        showToast(t('toasts.saved'));
      } else if (!ok) {
        setSaved(false);
        showToast(t('toasts.saveFailed'));
      }
    },
    [buildPersistInput, docApi, showToast, t],
  );

  const focusLeftDrawer = (
    <WbLeftRailDrawer
      id={focusLeftRailId}
      project={project}
      brief={brief}
      setBrief={setBrief}
      language={language}
      setLanguage={setLanguage}
      tone={tone}
      setTone={setTone}
      ctaPrimary={ctaPrimary}
      setCtaPrimary={setCtaPrimary}
      ctaSecondary={ctaSecondary}
      setCtaSecondary={setCtaSecondary}
      goal={siteGoal}
      setGoal={setSiteGoal}
      audience={audience}
      setAudience={setAudience}
      mainMessage={mainMessage}
      setMainMessage={setMainMessage}
      openGroups={railGroups}
      toggleGroup={toggleRailGroup}
      selectedAssets={selectedAssets}
      toggleAsset={toggleSelectedAsset}
      libraryAssets={libraryAssets}
      onUploadAsset={openUploadPicker}
      uploadingAsset={mediaApi.uploading}
      mediaStatus={mediaApi.status}
      onRetryMedia={() => {
        void refreshMedia(assetQuery);
      }}
      device={device === 'split' ? 'desktop' : device}
      setDevice={(d) => setDevice(d)}
      metaTitle={metaTitle}
      setMetaTitle={setMetaTitle}
      metaDesc={metaDesc}
      setMetaDesc={setMetaDesc}
      slug={slug}
      setSlug={setSlug}
    />
  );

  const focusRightDrawer = (
    <WbRightRailDrawer
      id={focusRightRailId}
      project={project}
      scores={{
        overall: aiQuality.overall,
        seo: aiQuality.seo,
        brand: 86,
        readability: aiQuality.content,
        mobile: aiQuality.accessibility,
        performance: aiQuality.performance,
        conversion: 74,
      }}
      suggestions={railSuggestions}
      onApplySuggestion={(id) => {
        setRailSuggestions((prev) => prev.filter((s) => s.id !== id));
        showToast(t('rails.suggestions.apply'));
      }}
      onDismissSuggestion={(id) =>
        setRailSuggestions((prev) => prev.filter((s) => s.id !== id))
      }
      onApplyAll={() => {
        setRailSuggestions([]);
        showToast(t('rails.suggestions.applyAll'));
      }}
      onQuickAction={(key) => {
        if (key === 'addSection' && selectedSection) addSectionAfter(selectedSection);
        else if (key === 'hero') handleGenerate('hero');
        else if (key === 'rewrite') handleGenerate('section');
        else if (key === 'seo') handleGenerate('seo');
        else handleGenerate('entire');
      }}
      onPreview={() => focus.setMode('preview')}
      onPublish={() => setPublishOpen(true)}
      onSaveVersion={() => {
        void (async () => {
          try {
            const label = versionComment.trim() || `v${versions.length + 1}`;
            const created = await docApi.createVersion(buildPersistInput(), label);
            if (created) {
              setVersionComment('');
              setSaved(true);
              setLastSavedLabel(t('savedJustNow'));
              showToast(t('toasts.versionCreated', { label: created.label }));
            }
          } catch {
            showToast(t('toasts.saveFailed'));
          }
        })();
      }}
      publishStatus={publishStatus}
      versions={versions}
      activeVersionId={activeVersionId}
      onRestoreVersion={(id) => {
        setRestoreConfirmId(id);
      }}
    />
  );

  const hydration = useCsBuilderHydration({
    bootstrap: docApi.bootstrap,
    onSuccess: (draft) => {
      applyDraftToEditor(draft, { applyContentDefaults: true });
      if (draft) {
        setSaved(true);
        setLastSavedLabel(t('savedJustNow'));
      } else {
        setLastSavedLabel(t('notSavedYet'));
      }
    },
  });
  const hydrated = hydration.hydrated;

  useEffect(() => {
    if (!hydrated) return;
    const id = window.setInterval(() => {
      setGalleryIndex((idx) => (idx + 1) % Math.max(galleryUrls.length, 1));
    }, 4200);
    return () => window.clearInterval(id);
  }, [hydrated, galleryUrls.length]);

  // Resolve auth-gated Media Library blobs for hero / gallery refs — only after hydrate.
  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    void (async () => {
      const assetId = heroImage?.asset_id;
      if (!assetId || !isMediaAssetUuid(assetId)) {
        if (!cancelled) setResolvedHeroUrl(null);
        return;
      }
      const url = await ensureDisplayUrl(assetId);
      if (!cancelled) setResolvedHeroUrl(url);
    })();
    return () => {
      cancelled = true;
    };
  }, [hydrated, heroImage?.asset_id, ensureDisplayUrl]);

  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    void (async () => {
      const next: Record<string, string> = {};
      for (const ref of galleryImages) {
        if (!ref.asset_id || !isMediaAssetUuid(ref.asset_id)) continue;
        const url = await ensureDisplayUrl(ref.asset_id);
        if (url) next[ref.asset_id] = url;
      }
      if (!cancelled) setResolvedGalleryUrls(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [hydrated, galleryImages, ensureDisplayUrl]);

  // On-demand library preview thumb only — never mass-warm project media binaries.
  useEffect(() => {
    if (!hydrated || !previewAssetId) return;
    void ensureDisplayUrl(previewAssetId);
  }, [hydrated, previewAssetId, ensureDisplayUrl]);

  // Debounced Media Library search from the assets panel query.
  useEffect(() => {
    if (!hydrated) return;
    const id = window.setTimeout(() => {
      void searchMedia(assetQuery);
    }, 320);
    return () => window.clearTimeout(id);
  }, [assetQuery, hydrated, searchMedia]);

  useEffect(() => {
    if (!hydrated || docApi.loadStatus !== 'ready') return;
    if (contentDefaultsAppliedRef.current) return;
    setHeroTitle(t('site.heroTitle'));
    setHeroBody(t('site.heroBody', { project: project.name, city: project.city }));
    setCtaPrimary(t('site.ctaInvest'));
    setCtaSecondary(t('site.ctaExplore'));
    contentDefaultsAppliedRef.current = true;
  }, [hydrated, docApi.loadStatus, project.name, project.city, t]);

  // Conservative API autosave (debounced) — after load, not during restore.
  useEffect(() => {
    if (!hydrated || docApi.loadStatus !== 'ready' || docApi.restoring) return;
    const id = window.setTimeout(() => {
      void (async () => {
        const ok = await docApi.saveDraft(buildPersistInput());
        if (ok) {
          setSaved(true);
          setLastSavedLabel(t('savedJustNow'));
        }
      })();
    }, 2000);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    hydrated,
    docApi.loadStatus,
    docApi.restoring,
    sections,
    selectedSectionId,
    language,
    tone,
    publishStatus,
    metaTitle,
    metaDesc,
    slug,
    brief,
    siteGoal,
    audience,
    mainMessage,
    heroTitle,
    heroBody,
    ctaPrimary,
    ctaSecondary,
    heroImage,
    galleryImages,
  ]);

  useEffect(() => {
    function onKey(e: globalThis.KeyboardEvent) {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === 's') {
        e.preventDefault();
        void persistNow(true);
      }
      if (mod && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      }
      if (mod && e.key.toLowerCase() === 'z' && e.shiftKey) {
        e.preventDefault();
        redo();
      }
      if (mod && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        showToast(t('toasts.preview'));
      }
      if (!mod && !e.altKey && !e.shiftKey && ['1', '2', '3', '4'].includes(e.key)) {
        const target = e.target as HTMLElement | null;
        if (
          target &&
          (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
        ) {
          return;
        }
        const map: Record<string, DevicePreview> = {
          '1': 'desktop',
          '2': 'tablet',
          '3': 'mobile',
          '4': 'split',
        };
        changeDevice(map[e.key]);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [persistNow, undo, redo, showToast, t]);

  useEffect(() => {
    return () => {
      genTimerRef.current.forEach((id) => window.clearTimeout(id));
    };
  }, []);

  function changeDevice(next: DevicePreview) {
    if (canvasStageRef.current) {
      scrollPreserveRef.current = canvasStageRef.current.scrollTop;
    }
    setDeviceAnimating(true);
    setDevice(next);
    window.setTimeout(() => setDeviceAnimating(false), 280);
    requestAnimationFrame(() => {
      if (canvasStageRef.current) {
        canvasStageRef.current.scrollTop = scrollPreserveRef.current;
      }
    });
  }

  function adjustZoom(delta: number) {
    setZoom((z) => clampZoom(z + delta));
  }

  function fitToScreen() {
    const stage = canvasStageRef.current;
    if (!stage) {
      setZoom(ZOOM_DEFAULT);
      return;
    }
    const stageW = stage.clientWidth - 16;
    const natural =
      device === 'mobile' ? 390 : device === 'tablet' ? 768 : device === 'split' ? stageW * 0.62 : stageW;
    const next = clampZoom(Math.floor((stageW / Math.max(natural, 1)) * 100));
    setZoom(Math.min(100, next));
  }

  function createVersion(noteKey: WbVersion['noteKey'], comment?: string) {
    const label =
      comment?.trim() ||
      t(`versionNotes.${noteKey}`) ||
      `v${versions.length + 1}`;
    void (async () => {
      try {
        const created = await docApi.createVersion(buildPersistInput(), label);
        if (created) {
          setPublishStatus('draft');
          setSaved(true);
          setLastSavedLabel(t('savedJustNow'));
        }
      } catch {
        showToast(t('toasts.saveFailed'));
      }
    })();
  }

  function handleGenerate(
    kind: 'entire' | 'section' | 'hero' | 'generic' | 'seo' | 'images' | 'a11y' | 'translate' = 'entire',
  ) {
    genTimerRef.current.forEach((id) => window.clearTimeout(id));
    genTimerRef.current = [];
    setGenerating(true);
    setAiStatus('analyzing');
    setProgressStep(-1);
    setOpenLeft((prev) => ({ ...prev, conversation: true }));

    const assetReuse = filteredAssets.slice(0, 3).map((a) => a.id);
    setReusedAssets(assetReuse);

    AI_PROGRESS_STEPS.forEach((_, stepIndex) => {
      const progressTimer = window.setTimeout(() => {
        setProgressStep(stepIndex);
      }, 340 * (stepIndex + 1));
      genTimerRef.current.push(progressTimer);
    });

    AI_STATUS_SEQUENCE.forEach((status, index) => {
      const timer = window.setTimeout(() => {
        setAiStatus(status);
        if (index === AI_STATUS_SEQUENCE.length - 1) {
          setGenerating(false);
          setProgressStep(AI_PROGRESS_STEPS.length - 1);

          // (req 12) Auto-update AI quality card after generation finishes.
          setAiQuality((prev) => {
            const clamp = (n: number) => Math.max(0, Math.min(100, n));
            const delta =
              kind === 'entire'
                ? { seo: 10, accessibility: 10, performance: 8, content: 12 }
                : kind === 'hero'
                  ? { seo: 4, accessibility: 2, performance: 4, content: 12 }
                  : kind === 'seo'
                    ? { seo: 14, accessibility: 4, performance: 8, content: 2 }
                    : kind === 'a11y'
                      ? { seo: 2, accessibility: 14, performance: 4, content: 4 }
                      : kind === 'images'
                        ? { seo: 2, accessibility: 2, performance: 6, content: 14 }
                        : kind === 'translate'
                          ? { seo: 2, accessibility: 2, performance: 2, content: 8 }
                          : kind === 'section'
                            ? { seo: 4, accessibility: 2, performance: 4, content: 10 }
                            : { seo: 2, accessibility: 2, performance: 2, content: 6 };

            const seo = clamp(prev.seo + delta.seo);
            const accessibility = clamp(prev.accessibility + delta.accessibility);
            const performance = clamp(prev.performance + delta.performance);
            const content = clamp(prev.content + delta.content);
            const overall = Math.round((seo + accessibility + performance + content) / 4);
            return { ...prev, seo, accessibility, performance, content, overall, updatedAt: 'Just now' };
          });

          const note =
            kind === 'hero'
              ? 'heroRegen'
              : kind === 'seo'
                ? 'seoPass'
                : kind === 'entire'
                  ? 'galleryExpand'
                  : 'luxuryTone';
          createVersion(note as WbVersion['noteKey'], t(`aiStatus.${status}`));
          setSaved(true);
          setLastSavedLabel(t('savedJustNow'));
          setChat((prev) => [
            ...prev,
            {
              id: `m-${Date.now()}`,
              role: 'ai',
              textKey: 'aiVersion',
            },
          ]);
          showToast(t('toasts.generated'));
        }
      }, 380 * (index + 1));
      genTimerRef.current.push(timer);
    });
  }

  function runQuickAi(key: AiActionKey) {
    if (
      key === 'entireSite' ||
      key === 'improveSection' ||
      key === 'currentSection' ||
      key === 'generateHero' ||
      key === 'newCta' ||
      key === 'changeBackground'
    ) {
      handleGenerate(key === 'generateHero' ? 'hero' : key === 'newCta' ? 'section' : 'entire');
    } else if (key === 'rewrite') handleGenerate('section');
    else if (key === 'images' || key === 'generateImage') handleGenerate('images');
    else if (key === 'seo' || key === 'seoOptimize') handleGenerate('seo');
    else if (key === 'a11y' || key === 'a11yCheck') handleGenerate('a11y');
    else if (key === 'translate') handleGenerate('translate');
    else if (key === 'responsiveOptimize') handleGenerate('entire');
    else if (key === 'performanceAnalysis') handleGenerate('seo');
    else handleGenerate('generic');
  }

  function handleProjectChange(id: string) {
    void (async () => {
      setSaved(false);
      contentDefaultsAppliedRef.current = false;
      const next = docApi.constructionProjects.find((p) => p.id === id);
      const draft = await docApi.selectConstructionProject(id);
      applyDraftToEditor(draft);
      if (!draft && next) {
        setSlug(next.slug || next.project_name.toLowerCase().replace(/\s+/g, '-'));
        setMetaTitle(`Investhome | ${next.project_name}`);
        setMetaDesc(
          `Premium U.S. real-estate investment opportunities by Investhome — featuring ${next.project_name}.`,
        );
        setHeroImage(null);
        setGalleryImages([]);
        setResolvedHeroUrl(null);
        setResolvedGalleryUrls({});
      }
      if (draft) {
        setSaved(true);
        setLastSavedLabel(t('savedJustNow'));
      } else {
        setLastSavedLabel(t('notSavedYet'));
      }
    })();
  }

  function reorderGalleryImages() {
    if (!galleryImages.length) {
      const list = [...galleryUrls];
      if (!list.length) return;
      const [first, ...rest] = list;
      setGalleryImages(
        [...rest, first].map((url) => ({
          asset_id: null,
          url,
          role: 'gallery',
        })),
      );
      return;
    }
    setGalleryImages((prev) => {
      if (prev.length < 2) return prev;
      const [first, ...rest] = prev;
      return [...rest, first!];
    });
  }

  function moveSection(id: string, dir: -1 | 1) {
    pushHistory(
      (() => {
        const idx = sections.findIndex((s) => s.id === id);
        if (idx < 0) return sections;
        const target = idx + dir;
        if (target < 0 || target >= sections.length) return sections;
        const copy = [...sections];
        const [item] = copy.splice(idx, 1);
        copy.splice(target, 0, item);
        return copy;
      })(),
    );
  }

  function reorderSections(fromId: string, toId: string) {
    if (fromId === toId) return;
    const from = sections.findIndex((s) => s.id === fromId);
    const to = sections.findIndex((s) => s.id === toId);
    if (from < 0 || to < 0) return;
    const copy = [...sections];
    const [item] = copy.splice(from, 1);
    copy.splice(to, 0, item);
    pushHistory(copy);
  }

  function duplicateSection(section: WbSection) {
    const copy: WbSection = {
      ...section,
      id: `${section.id}-copy-${Date.now()}`,
      customName: section.customName ? `${section.customName} (copy)` : undefined,
    };
    const idx = sections.findIndex((s) => s.id === section.id);
    const next = [...sections];
    next.splice(idx + 1, 0, copy);
    pushHistory(next);
    setSelectedSectionId(copy.id);
  }

  // Adds a new blank instance of the same section type right after the current one.
  function addSectionAfter(section: WbSection) {
    const idx = sections.findIndex((s) => s.id === section.id);
    if (idx < 0) return;
    const next: WbSection = {
      id: `s-${section.key}-${Date.now()}`,
      key: section.key,
      visible: true,
    };
    const updated = [...sections];
    updated.splice(idx + 1, 0, next);
    pushHistory(updated);
    setSelectedSectionId(next.id);
    setEditTarget(section.key === 'hero' ? 'hero' : 'section');
    setRightTab('properties');
  }

  function insertBlockFromLibrary(blockKey: BlockKey) {
    const id = `s-${blockKey}-${Date.now()}`;
    const key: WbSection['key'] =
      blockKey === 'statistics'
        ? 'investment'
        : blockKey === 'maps'
          ? 'location'
          : blockKey === 'video'
            ? 'gallery'
            : blockKey === 'testimonials' ||
                blockKey === 'partners' ||
                blockKey === 'timeline' ||
                blockKey === 'pricing'
              ? 'about'
              : (blockKey as WbSection['key']);
    pushHistory([
      ...sections,
      {
        id,
        key,
        visible: true,
        customName: t(`blocks.items.${blockKey}`),
      },
    ]);
    setSelectedSectionId(id);
    showToast(t('bottomBar.toasts.blockAdded', { name: t(`blocks.items.${blockKey}`) }));
  }

  function hideSection(id: string) {
    pushHistory(sections.map((s) => (s.id === id ? { ...s, visible: !s.visible } : s)));
  }

  function deleteSection(id: string) {
    if (sections.length <= 1) return;
    const next = sections.filter((s) => s.id !== id);
    pushHistory(next);
    if (selectedSectionId === id) setSelectedSectionId(next[0]?.id ?? '');
  }

  function selectSection(section: WbSection, target: EditTarget = 'section') {
    setSelectedSectionId(section.id);
    setEditTarget(target);
    setRightTab('properties');
  }

  function runSectionAction(section: WbSection, action: SectionActionKey) {
    setSelectedSectionId(section.id);
    switch (action) {
      case 'edit':
        selectSection(section, section.key === 'hero' ? 'hero' : 'section');
        break;
      case 'duplicate':
        duplicateSection(section);
        break;
      case 'delete':
        deleteSection(section.id);
        break;
      case 'rewrite':
        handleGenerate('section');
        break;
      case 'replaceImage':
        setOpenLeft((prev) => ({ ...prev, assets: true }));
        showToast(t('toasts.replaceImage'));
        break;
      case 'move':
        moveSection(section.id, 1);
        break;
      case 'hide':
        hideSection(section.id);
        break;
      case 'preview':
        showToast(t('toasts.sectionPreview', { section: sectionLabel(section, t) }));
        break;
      default:
        break;
    }
  }

  function insertMemory(key: MemoryKey) {
    const label = t(`memory.${key}`);
    const token = `@${label}`;
    setBrief((prev) => (prev.trim() ? `${prev.trim()} ${token}` : token));
    setOpenLeft((prev) => ({ ...prev, conversation: true }));
    showToast(t('toasts.memoryInserted', { memory: label }));
  }

  function sendBrief() {
    const text = brief.trim() || t('prompts.premiumSite');
    setChat((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', text },
      { id: `a-${Date.now()}`, role: 'ai', textKey: 'aiCommand' },
    ]);
    setBrief('');
    handleGenerate('entire');
  }

  function toggleAsset(id: string) {
    setSelectedAssets((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function applyAssetToPreview(asset: WbAsset) {
    const raw = mediaApi.getRawAsset(asset.id);
    if (raw) {
      const sync = String(raw.sync_status || '').toLowerCase();
      if (raw.archived_at || sync === 'missing' || sync === 'error') {
        showToast(t('toasts.assetNotSelectable'));
        return;
      }
    }
    const ref = imageRefFromWbAsset(asset, selectedSection?.key === 'gallery' ? 'gallery' : 'hero');
    if (ref && (asset.kind === 'images' || asset.kind === 'logos')) {
      if (selectedSection?.key === 'gallery') {
        setGalleryImages((prev) =>
          [ref, ...prev.filter((r) => {
            if (ref.asset_id && r.asset_id) return r.asset_id !== ref.asset_id;
            return r.url !== ref.url;
          })].slice(0, 12),
        );
        if (ref.asset_id) {
          void ensureDisplayUrl(ref.asset_id).then((url) => {
            if (url) setResolvedGalleryUrls((prev) => ({ ...prev, [ref.asset_id!]: url }));
          });
        }
        showToast(t('toasts.imageReplaced'));
      } else {
        setHeroImage(ref);
        if (ref.asset_id) {
          void ensureDisplayUrl(ref.asset_id).then((url) => {
            setResolvedHeroUrl(url);
          });
        } else {
          setResolvedHeroUrl(null);
        }
        const hero = sections.find((s) => s.key === 'hero');
        if (hero) selectSection(hero, 'image');
        showToast(t('toasts.imageReplaced'));
      }
      setSelectedAssets([asset.id]);
      setPreviewAssetId(asset.id);
      setSaved(false);
      return;
    }
    if (asset.kind === 'pdf' || asset.kind === 'documents' || asset.tags.includes('brochure')) {
      const briefRef = `[${asset.filename}]`;
      setBrief((prev) => (prev.trim() ? `${prev.trim()} ${briefRef}` : briefRef));
      setOpenLeft((prev) => ({ ...prev, conversation: true }));
      showToast(t('toasts.assetReferenced', { file: asset.filename }));
    }
  }

  function onAssetDragStart(e: DragEvent, asset: WbAsset) {
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('application/wb-asset', asset.id);
    e.dataTransfer.setData('text/plain', asset.id);
  }

  function onPreviewDragOver(e: DragEvent) {
    if (e.dataTransfer.types.includes('application/wb-asset') || e.dataTransfer.types.includes('text/plain')) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    }
  }

  function onPreviewDrop(e: DragEvent) {
    e.preventDefault();
    const id = e.dataTransfer.getData('application/wb-asset') || e.dataTransfer.getData('text/plain');
    const asset = libraryAssets.find((a) => a.id === id);
    if (asset) applyAssetToPreview(asset);
  }

  function onChatDragOver(e: DragEvent) {
    if (e.dataTransfer.types.includes('application/wb-asset')) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    }
  }

  function onChatDrop(e: DragEvent) {
    e.preventDefault();
    const id = e.dataTransfer.getData('application/wb-asset') || e.dataTransfer.getData('text/plain');
    const asset = libraryAssets.find((a) => a.id === id);
    if (!asset) return;
    const ref = `[${asset.filename}]`;
    setBrief((prev) => (prev.trim() ? `${prev.trim()} ${ref}` : ref));
    showToast(t('toasts.assetReferenced', { file: asset.filename }));
  }

  async function handleUploadFile(file: File | null | undefined) {
    if (!file || mediaApi.uploading) return;
    const accepted =
      !file.size
        ? false
        : /^(image\/jpeg|image\/png|image\/webp|image\/gif)$/i.test(file.type) ||
          /\.(jpe?g|png|gif|webp)$/i.test(file.name);
    if (!accepted) {
      showToast(t('toasts.uploadFailed'));
      return;
    }
    const uploaded = await mediaApi.uploadImage(file);
    if (!uploaded) {
      showToast(t('toasts.uploadFailed'));
      return;
    }
    const ref = imageRefFromMediaAsset(uploaded, selectedSection?.key === 'gallery' ? 'gallery' : 'hero');
    setSelectedAssets([uploaded.id]);
    setPreviewAssetId(uploaded.id);
    if (selectedSection?.key === 'gallery') {
      setGalleryImages((prev) => [ref, ...prev].slice(0, 12));
      const url = await ensureDisplayUrl(uploaded.id);
      if (url) setResolvedGalleryUrls((prev) => ({ ...prev, [uploaded.id]: url }));
    } else {
      setHeroImage(ref);
      const url = await ensureDisplayUrl(uploaded.id);
      setResolvedHeroUrl(url);
      const hero = sections.find((s) => s.key === 'hero');
      if (hero) selectSection(hero, 'image');
    }
    setSaved(false);
    showToast(t('toasts.uploadSucceeded', { file: uploaded.filename }));
  }

  function openUploadPicker() {
    if (mediaApi.uploading) return;
    uploadInputRef.current?.click();
  }

  function onStructureDragStart(e: DragEvent, id: string) {
    setDragSectionId(id);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);
  }

  function onStructureDragOver(e: DragEvent, id: string) {
    e.preventDefault();
    setDropTargetId(id);
  }

  function onStructureDrop(e: DragEvent, id: string) {
    e.preventDefault();
    const from = e.dataTransfer.getData('text/plain') || dragSectionId;
    if (from) reorderSections(from, id);
    setDragSectionId(null);
    setDropTargetId(null);
  }

  function commitRename(id: string) {
    if (!renameValue.trim()) {
      setRenamingId(null);
      return;
    }
    pushHistory(
      sections.map((s) => (s.id === id ? { ...s, customName: renameValue.trim() } : s)),
    );
    setRenamingId(null);
  }

  function handleVersionAction(action: (typeof VERSION_ACTIONS)[number]) {
    const current = versions.find((v) => v.id === activeVersionId);
    if (!current) return;
    switch (action) {
      case 'restore':
        setRestoreConfirmId(current.id);
        break;
      case 'compare':
        setCompareVersionId((prev) => (prev === current.id ? null : current.id));
        break;
      case 'rename':
        showToast(t('toasts.versionRenameLocal'));
        break;
      case 'duplicate':
      case 'branch':
        void (async () => {
          try {
            const label =
              action === 'branch'
                ? `${current.label}-branch`
                : `${current.label}-copy`;
            const created = await docApi.createVersion(buildPersistInput(), label);
            if (created) {
              showToast(t('toasts.versionCreated', { label: created.label }));
            }
          } catch {
            showToast(t('toasts.saveFailed'));
          }
        })();
        break;
      case 'comment':
        if (!versionComment.trim()) break;
        void (async () => {
          try {
            const created = await docApi.createVersion(
              buildPersistInput(),
              versionComment.trim(),
            );
            if (created) {
              setVersionComment('');
              showToast(t('toasts.versionCreated', { label: created.label }));
            }
          } catch {
            showToast(t('toasts.saveFailed'));
          }
        })();
        break;
      default:
        break;
    }
  }

  async function confirmRestoreVersion(versionId: string) {
    setRestoreConfirmId(null);
    try {
      const draft = await docApi.restoreVersion(versionId);
      applyDraftToEditor(draft);
      const version = versions.find((v) => v.id === versionId);
      showToast(t('toasts.restored', { version: version?.label ?? versionId }));
      setSaved(true);
      setLastSavedLabel(t('savedJustNow'));
    } catch {
      showToast(t('toasts.saveFailed'));
    }
  }

  function confirmPublish() {
    if (!canPublish) return;
    setPublishStatus('approved');
    setPublishOpen(false);
    setActiveStep(4);
    showToast(t('toasts.publishReady'));
  }

  function renderQuickAiPanel() {
    return (
      <div className="wb-ws__quick-ai" data-testid="wb-quick-ai">
        <p className="wb-ws__section-label">{t('right.quickAi')}</p>
        <p className="wb-ws__reused-note" style={{ marginBottom: 4 }}>
          {t('aiActions.contextFor', { section: sectionLabel(selectedSection, t) })}
        </p>
        {contextualAiActions.map((action) => (
          <button
            key={action.key}
            type="button"
            className="wb-ws__quick-ai-card"
            disabled={generating}
            onClick={() => runQuickAi(action.key)}
          >
            <IhIcon name={action.icon} size={14} />
            <span>{t(`aiActions.items.${action.key}`)}</span>
          </button>
        ))}
      </div>
    );
  }

  function renderAiProgress() {
    if (!generating && progressStep < 0) return null;
    return (
      <div className="wb-ws__ai-progress" data-testid="wb-ai-progress" aria-live="polite">
        {AI_PROGRESS_STEPS.map((step, index) => {
          const done = index < completedProgressSteps;
          const active = generating && index === progressStep;
          return (
            <div
              key={step}
              className={`wb-ws__ai-progress-step${done ? ' is-done' : ''}${active ? ' is-active' : ''}`}
            >
              <span className="wb-ws__ai-progress-check" aria-hidden="true">
                {done ? '✓' : ''}
              </span>
              <span>{t(`aiProgress.${step}`)}</span>
            </div>
          );
        })}
      </div>
    );
  }

  function renderCopilotStage() {
    if (!generating && aiStatus === 'idle') return null;
    const stage =
      aiStatus === 'publishingReady'
        ? 'Completed'
        : ['analyzing', 'readingBrochure'].includes(aiStatus)
          ? 'Thinking'
          : 'Working';

    return (
      <div className="wb-ws__copilot-stage" aria-live="polite">
        <span className="wb-ws__copilot-stage-dot" aria-hidden="true" />
        <span className="wb-ws__copilot-stage-label">{stage}</span>
        <span className="wb-ws__copilot-stage-meta">{t(`aiStatus.${aiStatus}`)}</span>
      </div>
    );
  }

  function renderDesignAccordions() {
    return (
      <div className="wb-ws__design-accordion" data-testid="wb-design-accordions">
        {DESIGN_ACCORDIONS.map((key) => {
          const open = openAccordions[key];
          return (
            <div key={key} className={`wb-ws__design-acc-item${open ? ' is-open' : ''}`}>
              <button
                type="button"
                className="wb-ws__design-acc-trigger"
                aria-expanded={open}
                onClick={() => setOpenAccordions((prev) => ({ ...prev, [key]: !prev[key] }))}
              >
                <span>{t(`accordions.${key}`)}</span>
                <IhIcon name={open ? 'chevronDown' : 'chevronRight'} size={12} />
              </button>
              {open ? (
                <div className="wb-ws__design-acc-body">
                  {key === 'hero' ? (
                    <>
                      <div className="wb-ws__prop">
                        <label htmlFor="wb-acc-hero-title">{t('fields.heroTitle')}</label>
                        <input
                          id="wb-acc-hero-title"
                          value={heroTitle}
                          onChange={(e) => setHeroTitle(e.target.value)}
                        />
                      </div>
                      <div className="wb-ws__prop">
                        <label htmlFor="wb-acc-hero-body">{t('fields.heroBody')}</label>
                        <textarea
                          id="wb-acc-hero-body"
                          value={heroBody}
                          onChange={(e) => setHeroBody(e.target.value)}
                        />
                      </div>
                    </>
                  ) : null}
                  {key === 'typography' ? (
                    <div className="wb-ws__prop">
                      <label>{t('fields.typography')}</label>
                      <span>{t('options.typography')}</span>
                    </div>
                  ) : null}
                  {key === 'buttons' ? (
                    <>
                      <div className="wb-ws__prop">
                        <label htmlFor="wb-acc-cta-primary">{t('fields.ctaPrimary')}</label>
                        <input
                          id="wb-acc-cta-primary"
                          value={ctaPrimary}
                          onChange={(e) => setCtaPrimary(e.target.value)}
                        />
                      </div>
                      <div className="wb-ws__prop">
                        <label htmlFor="wb-acc-cta-secondary">{t('fields.ctaSecondary')}</label>
                        <input
                          id="wb-acc-cta-secondary"
                          value={ctaSecondary}
                          onChange={(e) => setCtaSecondary(e.target.value)}
                        />
                      </div>
                    </>
                  ) : null}
                  {key === 'background' ? (
                    <div className="wb-ws__prop">
                      <label>{t('fields.heroMedia')}</label>
                      <span>{t('options.coverFromProject')}</span>
                    </div>
                  ) : null}
                  {key === 'overlay' ? (
                    <div className="wb-ws__prop">
                      <label>{t('accordions.overlayHint')}</label>
                      <span>{t('options.layout')}</span>
                    </div>
                  ) : null}
                  {key === 'animation' ? (
                    <div className="wb-ws__prop">
                      <label>{t('accordions.animationHint')}</label>
                      <span>{t('options.spacing')}</span>
                    </div>
                  ) : null}
                  {key === 'spacing' ? (
                    <div className="wb-ws__prop">
                      <label>{t('fields.spacing')}</label>
                      <span>{t('options.spacing')}</span>
                    </div>
                  ) : null}
                  {key === 'seo' ? (
                    <>
                      <div className="wb-ws__prop">
                        <label htmlFor="wb-acc-meta-title">{t('fields.metaTitle')}</label>
                        <input
                          id="wb-acc-meta-title"
                          value={metaTitle}
                          onChange={(e) => setMetaTitle(e.target.value)}
                        />
                      </div>
                      <div className="wb-ws__prop">
                        <label htmlFor="wb-acc-meta-desc">{t('fields.metaDescription')}</label>
                        <textarea
                          id="wb-acc-meta-desc"
                          value={metaDesc}
                          onChange={(e) => setMetaDesc(e.target.value)}
                        />
                      </div>
                    </>
                  ) : null}
                  {key === 'accessibility' ? (
                    <div className="wb-ws__prop">
                      <label>{t('fields.accessibility')}</label>
                      <span>{t('options.a11y')}</span>
                    </div>
                  ) : null}
                  {key === 'advanced' ? (
                    <>
                      <div className="wb-ws__prop">
                        <label htmlFor="wb-acc-slug">{t('fields.slug')}</label>
                        <input id="wb-acc-slug" value={slug} onChange={(e) => setSlug(e.target.value)} />
                      </div>
                      <div className="wb-ws__prop">
                        <label>{t('fields.theme')}</label>
                        <span>{t('options.theme')}</span>
                      </div>
                    </>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    );
  }

  function renderPreview(mode: PreviewDevice, keySuffix = '') {
    const scale = zoom / 100;
    return (
      <div
        className={`wb-ws__preview-zoom is-${mode}`}
        style={{ transform: `scale(${scale})`, transformOrigin: 'top center' }}
        key={`${mode}${keySuffix}`}
      >
        <div
          className={`wb-ws__preview is-${mode}`}
          data-testid={keySuffix ? undefined : 'wb-live-preview'}
          onDragOver={onPreviewDragOver}
          onDrop={onPreviewDrop}
        >
          <div className="wb-ws__browser-chrome" aria-hidden="true">
            <div className="wb-ws__browser-chrome-dots">
              <span className="wb-ws__browser-dot wb-ws__browser-dot--red" />
              <span className="wb-ws__browser-dot wb-ws__browser-dot--yellow" />
              <span className="wb-ws__browser-dot wb-ws__browser-dot--green" />
            </div>
            <div className="wb-ws__browser-chrome-address">investhome.os/{project.slug}</div>
          </div>

          <div className="wb-ws__site-nav">
            <span className="wb-ws__brand">INVESTHOME</span>
            <div className="wb-ws__site-links">
              <span
                role="button"
                tabIndex={0}
                className={navMenuOpen ? 'is-active' : ''}
                onClick={(e) => {
                  e.stopPropagation();
                  setNavMenuOpen((v) => !v);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setNavMenuOpen((v) => !v);
                  }
                }}
              >
                {t('site.nav.projects')} ▾
              </span>
              <span>{t('site.nav.invest')}</span>
              <span>{t('site.nav.about')}</span>
              <span>{t('site.nav.contact')}</span>
            </div>
            {navMenuOpen ? (
              <div className="wb-ws__site-menu" role="menu">
                <span role="menuitem">{t('site.nav.projects')}</span>
                <span role="menuitem">{t('site.nav.invest')}</span>
                <span role="menuitem">{t('site.nav.about')}</span>
                <span role="menuitem">{t('site.nav.contact')}</span>
              </div>
            ) : null}
          </div>

          {sections
            .filter((s) => s.visible)
            .map((section) => {
              if (section.key === 'hero') {
                return (
                  <div
                    key={section.id}
                    className={`wb-ws__hero wb-ws__editable${selectedSectionId === section.id ? ' is-selected' : ''}${editTarget === 'hero' || editTarget === 'image' ? ' is-editing' : ''}`}
                    style={{ backgroundImage: `url(${heroCover})` }}
                    onClick={() => selectSection(section, 'hero')}
                    role="presentation"
                  >
                    {renderSectionToolbar(section, 'hero')}
                    <div className="wb-ws__hero-inner">
                      <p className="wb-ws__hero-eyebrow">
                        {t('site.featured', { project: project.featuredLabel })}
                      </p>
                      <h3
                        className={`wb-ws__editable-text${editTarget === 'text' ? ' is-editing' : ''}`}
                        contentEditable
                        suppressContentEditableWarning
                        onClick={(e) => {
                          e.stopPropagation();
                          selectSection(section, 'text');
                        }}
                        onBlur={(e) => setHeroTitle(e.currentTarget.textContent || heroTitle)}
                      >
                        {heroTitle || t('site.heroTitle')}
                      </h3>
                      <p
                        className={`wb-ws__editable-text${editTarget === 'text' ? ' is-editing' : ''}`}
                        contentEditable
                        suppressContentEditableWarning
                        onClick={(e) => {
                          e.stopPropagation();
                          selectSection(section, 'text');
                        }}
                        onBlur={(e) => setHeroBody(e.currentTarget.textContent || heroBody)}
                      >
                        {heroBody ||
                          t('site.heroBody', { project: project.name, city: project.city })}
                      </p>
                      <div className="wb-ws__hero-ctas">
                        <button
                          type="button"
                          className={`wb-ws__hero-cta wb-ws__hero-cta--primary wb-ws__editable${editTarget === 'button' ? ' is-editing' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            selectSection(section, 'button');
                          }}
                        >
                          {ctaPrimary || t('site.ctaInvest')}
                        </button>
                        <button
                          type="button"
                          className={`wb-ws__hero-cta wb-ws__hero-cta--ghost wb-ws__editable${editTarget === 'button' ? ' is-editing' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            selectSection(section, 'button');
                          }}
                        >
                          {ctaSecondary || t('site.ctaExplore')}
                        </button>
                      </div>
                      <div className="wb-ws__stats">
                        {project.stats.map((stat) => (
                          <div key={stat.labelKey} className="wb-ws__stat">
                            <strong>{stat.value}</strong>
                            <span>{t(`site.stats.${stat.labelKey}`)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={section.id}
                  className={`wb-ws__section-block wb-ws__editable${selectedSectionId === section.id ? ' is-selected' : ''}${editTarget === 'section' && selectedSectionId === section.id ? ' is-editing' : ''}`}
                  onClick={() => selectSection(section, 'section')}
                  role="presentation"
                >
                  {renderSectionToolbar(section)}
                  <h4>{sectionLabel(section, t)}</h4>
                  <p>{t(`sectionCopy.${section.key}`, { project: project.name })}</p>
                  {section.key === 'gallery' ? (
                    <div className="wb-ws__gallery-carousel">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        key={galleryUrls[galleryIndex % galleryUrls.length]}
                        src={galleryUrls[galleryIndex % galleryUrls.length]}
                        alt=""
                        width={600}
                        height={338}
                        className={`wb-ws__editable${editTarget === 'image' ? ' is-editing' : ''}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          selectSection(section, 'image');
                        }}
                      />
                      <CarouselDots
                        count={galleryUrls.length}
                        activeIndex={galleryIndex % galleryUrls.length}
                        onSelect={setGalleryIndex}
                        ariaLabel={t('sections.gallery')}
                        getLabel={(idx) => t('site.gallerySlide', { index: idx + 1 })}
                        className="wb-ws__gallery-dots"
                        size="md"
                      />
                    </div>
                  ) : null}
                  {section.key === 'amenities' ? (
                    <div className="wb-ws__preview-video">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={galleryUrls[1] || galleryUrls[0]}
                        alt=""
                        width={600}
                        height={200}
                        style={{ width: '100%', aspectRatio: '16/9', objectFit: 'cover', opacity: videoPlaying ? 1 : 0.8 }}
                      />
                      {!videoPlaying ? (
                        <button
                          type="button"
                          className="wb-ws__preview-video-play"
                          onClick={(e) => {
                            e.stopPropagation();
                            setVideoPlaying(true);
                          }}
                        >
                          ▶ {t('site.playVideo')}
                        </button>
                      ) : (
                        <div className="wb-ws__faq-body" style={{ padding: 10, background: '#0b1929', color: '#fff' }}>
                          {t('site.videoPlaying')}
                        </div>
                      )}
                    </div>
                  ) : null}
                  {section.key === 'faq' ? (
                    <div className="wb-ws__faq-list" style={{ display: 'grid', gap: 6, marginTop: 10 }}>
                      {[0, 1].map((idx) => (
                        <div key={idx} className="wb-ws__faq-item">
                          <button
                            type="button"
                            className="wb-ws__faq-trigger"
                            aria-expanded={faqOpenIndex === idx}
                            onClick={(e) => {
                              e.stopPropagation();
                              setFaqOpenIndex((prev) => (prev === idx ? null : idx));
                            }}
                          >
                            <span>{t(`site.faq.q${idx + 1}`, { project: project.name })}</span>
                            <IhIcon name={faqOpenIndex === idx ? 'chevronDown' : 'chevronRight'} size={12} />
                          </button>
                          {faqOpenIndex === idx ? (
                            <div className="wb-ws__faq-body">{t(`site.faq.a${idx + 1}`)}</div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
        </div>
      </div>
    );
  }

  function renderAssetCard(asset: WbAsset) {
    const selected = selectedAssets.includes(asset.id);
    const reused = reusedAssets.includes(asset.id);
    return (
      <div
        key={asset.id}
        className={`wb-ws__asset${selected ? ' is-selected' : ''}${reused ? ' is-reused' : ''}`}
        draggable
        onDragStart={(e) => onAssetDragStart(e, asset)}
      >
        <div className="wb-ws__asset-actions">
          <button
            type="button"
            className="wb-ws__asset-action"
            onClick={() => setPreviewAssetId(asset.id)}
          >
            {t('assets.actions.preview')}
          </button>
          <button type="button" className="wb-ws__asset-action" onClick={() => applyAssetToPreview(asset)}>
            {t('assets.actions.use')}
          </button>
          <button
            type="button"
            className="wb-ws__asset-action"
            onClick={() => {
              applyAssetToPreview(asset);
              showToast(t('toasts.imageReplaced'));
            }}
          >
            {t('assets.actions.replace')}
          </button>
          <button
            type="button"
            className="wb-ws__asset-action"
            onClick={() => {
              const ref = `[${asset.filename}]`;
              setBrief((prev) => (prev.trim() ? `${prev.trim()} ${ref}` : ref));
              setOpenLeft((prev) => ({ ...prev, conversation: true }));
              showToast(t('toasts.assetReferenced', { file: asset.filename }));
            }}
          >
            {t('assets.actions.addToAi')}
          </button>
        </div>
        <button
          type="button"
          className="wb-ws__asset-main"
          aria-pressed={selected}
          onClick={(e) => {
            if (e.metaKey || e.ctrlKey || e.shiftKey) toggleAsset(asset.id);
            else {
              setSelectedAssets([asset.id]);
              setPreviewAssetId(asset.id);
            }
          }}
          onDoubleClick={() => applyAssetToPreview(asset)}
        >
          <div className="wb-ws__asset-thumb">
            {asset.thumbUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={asset.thumbUrl} alt="" width={120} height={90} />
            ) : (
              <IhIcon name="documents" size={18} />
            )}
            {selected ? (
              <span className="wb-ws__asset-check" aria-hidden="true">
                ✓
              </span>
            ) : null}
          </div>
          <span className="wb-ws__asset-title">{asset.filename}</span>
          <span className="wb-ws__asset-meta">
            {asset.fileType}
            {asset.resolution ? ` · ${asset.resolution}` : ` · ${asset.meta}`}
          </span>
          <span className="wb-ws__asset-tags">
            {asset.tags.slice(0, 2).map((tag) => (
              <span key={tag} className="wb-ws__tag">
                {tag}
              </span>
            ))}
          </span>
          {asset.usedIn?.length ? (
            <span className="wb-ws__asset-used">
              {asset.usedIn.map((u) => (
                <span key={u} className="wb-ws__used-badge">
                  ✓ {t('assets.usedIn', { place: USED_IN_LABEL[u] || u })}
                </span>
              ))}
            </span>
          ) : (
            <span className="wb-ws__asset-unused">{t('assets.notUsed')}</span>
          )}
          <span className="wb-ws__asset-updated">{t('assets.updated', { when: asset.updatedAt })}</span>
        </button>
      </div>
    );
  }

  if (hydration.phase !== 'ready') {
    return (
      <CsBuilderBootstrapView
        testId={
          hydration.phase === 'error' ? 'wb-workspace-page' : 'wb-workspace-loading'
        }
        workspaceClassName="wb-ws"
        homeHref={WB_HOME}
        title={tTools('websiteBuilder.title')}
        studioLabel={t('creativeStudio')}
        phase={hydration.phase}
        loadingLabel={tBootstrap('loading')}
        errorTitle={t('loadErrorTitle')}
        errorMessage={hydration.error || t('loadError')}
        retryLabel={tCommon('retry')}
        onRetry={hydration.retry}
      />
    );
  }

  const saveChipTone =
    docApi.saveStatus === 'error'
      ? 'danger'
      : docApi.saveStatus === 'saving'
        ? 'warning'
        : saved || docApi.saveStatus === 'saved'
          ? 'success'
          : 'warning';
  const saveChipLabel =
    docApi.saveStatus === 'saving'
      ? t('saving')
      : docApi.saveStatus === 'error'
        ? t('saveFailed')
        : saved || docApi.saveStatus === 'saved'
          ? t('saved')
          : t('approvalPending');

  return (
    <main className="dashboard" data-testid="wb-workspace-page">
      <div className="wb-ws" data-testid="wb-workspace" data-cs-workspace-mode={focus.mode} data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}>
        {/* Always mounted so focus-mode Assets rail "Yeni Varlık Yükle" can trigger the picker. */}
        <input
          ref={uploadInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          hidden
          aria-hidden="true"
          tabIndex={-1}
          data-testid="wb-upload-input"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = '';
            void handleUploadFile(file);
          }}
        />
        <header className="wb-ws__header cs-page-header">
          <div>
            <Link href={WB_HOME as Route} className="wb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="wb-ws__breadcrumb">
                <li>
                  <Link href={WB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="wb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="wb-ws__breadcrumb-current" aria-current="page">
                  {tTools('websiteBuilder.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <span className="cs-ds__title-icon" aria-hidden="true">
                <IhIcon name="design" size={22} />
              </span>
              {tTools('websiteBuilder.title')}
            </h1>
            <p className="wb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <StatusChip tone="info">{t('badge')}</StatusChip>
        </header>

        <div className="wb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="wb-ws__toolbar-left">
            <div className="wb-ws__project">
              <Select
                id="wb-project"
                label={t('fields.project')}
                value={docApi.constructionProjectId ?? ''}
                onChange={(e) => handleProjectChange(e.target.value)}
              >
                {docApi.constructionProjects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.project_name}
                  </option>
                ))}
              </Select>
            </div>
            <StatusChip tone={PUBLISH_STATUS_TONE[publishStatus]}>
              {t(`status.${publishStatus}`)}
            </StatusChip>
            <StatusChip tone={saveChipTone}>{saveChipLabel}</StatusChip>
            <span className="wb-ws__saved-meta">{lastSavedLabel}</span>
          </div>
          <div className="wb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void persistNow(true)}
              disabled={docApi.saveStatus === 'saving'}
              data-testid="wb-save"
            >
              {docApi.saveStatus === 'saving' ? t('saving') : t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setRightTab('publishing');
                void docApi.refreshVersions();
              }}
              data-testid="wb-versions"
            >
              {t('versions')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="wb-preview"
              onClick={() => showToast(t('toasts.preview'))}
            >
              {t('preview')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setPublishOpen(true);
              }}
              data-testid="wb-publish"
            >
              {t('publish')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={generating}
              data-testid="wb-generate"
              onClick={() => handleGenerate('entire')}
            >
              <IhIcon name="sparkles" size={13} />
              {generating ? t('generating') : t('generate')}
            </Button>
          </div>
        </div>

        <div
          className={`wb-ws__ai-status${generating || aiStatus !== 'idle' ? ' is-live' : ''}`}
          role="status"
          aria-live="polite"
          data-testid="wb-ai-status"
        >
          <span className="wb-ws__ai-status-dot" aria-hidden="true" />
          <span>{aiStatus === 'idle' ? t('aiStatus.idle') : t(`aiStatus.${aiStatus}`)}</span>
          {reusedAssets.length > 0 ? (
            <span className="wb-ws__ai-status-meta">
              {t('aiStatus.reusing', { count: reusedAssets.length })}
            </span>
          ) : null}
        </div>

        <ol className="wb-ws__steps" aria-label={t('stepsAria')}>
          {WORKFLOW_STEPS.map((id, index) => (
            <li key={id}>
              <button
                type="button"
                className={`wb-ws__step${index === activeStep ? ' is-active' : ''}${index < activeStep ? ' is-done' : ''}`}
                onClick={() => setActiveStep(index)}
              >
                <span className="wb-ws__step-index">{index + 1}</span>
                <span>{t(`steps.${id}`)}</span>
              </button>
            </li>
          ))}
        </ol>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="wb-ws__layout"
          leftRail={wbLeftRail}
          rightRail={wbRightRail}
          onLeftRailSelect={(id) => {
            if (
              id === 'brief' ||
              id === 'assets' ||
              id === 'brand' ||
              id === 'settings' ||
              id === 'advanced'
            ) {
              setFocusLeftRailId(id);
            }
          }}
          onRightRailSelect={(id) => {
            if (
              id === 'score' ||
              id === 'suggestions' ||
              id === 'quickActions' ||
              id === 'export' ||
              id === 'history'
            ) {
              setFocusRightRailId(id);
            }
          }}
          left={
            focus.isFocus || focus.isFullscreen ? (
              focusLeftDrawer
            ) : (
            <aside className="wb-ws__panel wb-ws__left" aria-label={t('ai.aria')}>
            <div className="wb-ws__panel-head">
              <h2>{t('ai.title')}</h2>
              <StatusChip tone="info">{t('ai.brandKitReady')}</StatusChip>
            </div>
            <div className="wb-ws__panel-body wb-ws__left-stack">
              <div className="wb-ws__data-ready" data-testid="wb-data-ready">
                <div className="wb-ws__data-ready-row">
                  <span>{t('dataReady.brandKit')}</span>
                  <span>✓</span>
                </div>
                <div className="wb-ws__data-ready-row">
                  <span>{t('dataReady.crm')}</span>
                  <span>✓</span>
                </div>
                <div className="wb-ws__data-ready-row">
                  <span>{t('dataReady.photos')}</span>
                  <span>{PROJECT_DATA_STATS.photos}</span>
                </div>
                <div className="wb-ws__data-ready-row">
                  <span>{t('dataReady.plans')}</span>
                  <span>{PROJECT_DATA_STATS.plans}</span>
                </div>
                <div className="wb-ws__data-ready-row">
                  <span>{t('dataReady.brochures')}</span>
                  <span>{PROJECT_DATA_STATS.brochures}</span>
                </div>
                <div className="wb-ws__data-ready-row">
                  <span>{t('dataReady.project')}</span>
                  <span>✓</span>
                </div>
              </div>
              {LEFT_SECTIONS.map((sectionKey) => {
                const open = openLeft[sectionKey];
                return (
                  <section key={sectionKey} className="wb-ws__collapse">
                    <button
                      type="button"
                      className="wb-ws__collapse-trigger"
                      aria-expanded={open}
                      onClick={() =>
                        setOpenLeft((prev) => ({ ...prev, [sectionKey]: !prev[sectionKey] }))
                      }
                    >
                      <span>{t(`ai.sections.${sectionKey}`)}</span>
                      <IhIcon name={open ? 'chevronDown' : 'chevronRight'} size={12} />
                    </button>

                    {open && sectionKey === 'conversation' ? (
                      <div className="wb-ws__collapse-body">
                        <div className="wb-ws__chat">
                          {chat.map((msg) => (
                            <div key={msg.id} className={`wb-ws__msg wb-ws__msg--${msg.role}`}>
                              {chatMessageText(msg, t, project.name)}
                            </div>
                          ))}
                          {renderCopilotStage()}
                          {renderAiProgress()}
                        </div>
                        <div
                          className="wb-ws__chat-input"
                          onDragOver={onChatDragOver}
                          onDrop={onChatDrop}
                        >
                          <label className="sr-only" htmlFor="wb-chat">
                            {t('ai.inputLabel')}
                          </label>
                          <textarea
                            id="wb-chat"
                            value={brief}
                            onChange={(e) => setBrief(e.target.value)}
                            placeholder={t('ai.placeholder')}
                            rows={3}
                            onKeyDown={(e: KeyboardEvent<HTMLTextAreaElement>) => {
                              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                                e.preventDefault();
                                sendBrief();
                              }
                            }}
                          />
                          <Button variant="secondary" size="sm" onClick={sendBrief}>
                            {t('ai.send')}
                          </Button>
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'suggested' ? (
                      <div className="wb-ws__collapse-body">
                        <div className="wb-ws__prompts">
                          {SUGGESTED_PROMPTS.map((key) => (
                            <button
                              key={key}
                              type="button"
                              className="wb-ws__prompt"
                              onClick={() => {
                                setBrief(t(`prompts.${key}`));
                                setOpenLeft((prev) => ({ ...prev, conversation: true }));
                              }}
                            >
                              {t(`prompts.${key}`)}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'memory' ? (
                      <div className="wb-ws__collapse-body">
                        <div className="wb-ws__memory" aria-label={t('ai.memoryAria')}>
                          {MEMORY_CHIPS.map((key) => {
                            const ready = MEMORY_READY.includes(key);
                            return (
                              <button
                                key={key}
                                type="button"
                                className={`wb-ws__chip${ready ? ' is-ready' : ''}`}
                                title={ready ? t('memory.ready') : t('memory.pending')}
                                onClick={() => insertMemory(key)}
                              >
                                {ready ? <IhIcon name="check" size={10} /> : null}
                                {t(`memory.${key}`)}
                                <span className="wb-ws__chip-state">
                                  {ready ? t('memory.loaded') : t('memory.notLoaded')}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'context' ? (
                      <div className="wb-ws__collapse-body">
                        <div className="wb-ws__ai-context">
                          <div className="wb-ws__ai-context-row">
                            <span className="wb-ws__ai-context-check" aria-hidden="true">
                              ✓
                            </span>
                            <span>{t('memory.brand')}</span>
                            <span>{aiContextCounts.brandKit}</span>
                          </div>
                          <div className="wb-ws__ai-context-row">
                            <span className="wb-ws__ai-context-check" aria-hidden="true">
                              ✓
                            </span>
                            <span>{t('memory.crm')}</span>
                            <span>{aiContextCounts.crm}</span>
                          </div>
                          <div className="wb-ws__ai-context-row">
                            <span className="wb-ws__ai-context-check" aria-hidden="true">
                              ✓
                            </span>
                            <span>{t('memory.photos')}</span>
                            <span>{aiContextCounts.photos}</span>
                          </div>
                          <div className="wb-ws__ai-context-row">
                            <span className="wb-ws__ai-context-check" aria-hidden="true">
                              ✓
                            </span>
                            <span>{t('memory.floorPlans')}</span>
                            <span>{aiContextCounts.floorPlans}</span>
                          </div>
                          <div className="wb-ws__ai-context-row">
                            <span className="wb-ws__ai-context-check" aria-hidden="true">
                              ✓
                            </span>
                            <span>{t('memory.brochures')}</span>
                            <span>{aiContextCounts.brochures}</span>
                          </div>
                          <div className="wb-ws__ai-context-row">
                            <span className="wb-ws__ai-context-check" aria-hidden="true">
                              ✓
                            </span>
                            <span>{t('memory.investorDocs')}</span>
                            <span>{aiContextCounts.investorDocs}</span>
                          </div>
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'assets' ? (
                      <div className="wb-ws__collapse-body">
                        <div className="wb-ws__asset-tools">
                          <input
                            className="wb-ws__asset-search"
                            value={assetQuery}
                            onChange={(e) => setAssetQuery(e.target.value)}
                            placeholder={t('assets.search')}
                            aria-label={t('assets.search')}
                          />
                          <div
                            className="wb-ws__asset-filters"
                            role="tablist"
                            aria-label={t('assets.filtersAria')}
                          >
                            {ASSET_FILTERS.map((key) => (
                              <button
                                key={key}
                                type="button"
                                role="tab"
                                aria-selected={assetFilter === key}
                                className={`wb-ws__asset-filter${assetFilter === key ? ' is-active' : ''}`}
                                onClick={() => setAssetFilter(key)}
                              >
                                {t(`assets.kinds.${key}`)}
                              </button>
                            ))}
                          </div>
                          <div className="wb-ws__asset-meta-row">
                            <label className="wb-ws__inline-label">
                              <span>{t('assets.folder')}</span>
                              <select
                                value={assetFolder}
                                onChange={(e) =>
                                  setAssetFolder(e.target.value as (typeof ASSET_FOLDERS)[number])
                                }
                              >
                                {ASSET_FOLDERS.map((folder) => (
                                  <option key={folder} value={folder}>
                                    {t(`assets.folders.${folder}`)}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <label className="wb-ws__inline-label">
                              <span>{t('assets.sort')}</span>
                              <select
                                value={assetSort}
                                onChange={(e) => setAssetSort(e.target.value as AssetSort)}
                              >
                                {ASSET_SORTS.map((sort) => (
                                  <option key={sort} value={sort}>
                                    {t(`assets.sorts.${sort}`)}
                                  </option>
                                ))}
                              </select>
                            </label>
                          </div>
                          <div
                            className="wb-ws__drop"
                            onDragOver={(e) => e.preventDefault()}
                            onClick={() => openUploadPicker()}
                            onDrop={(e) => {
                              e.preventDefault();
                              const file = e.dataTransfer.files?.[0];
                              void handleUploadFile(file);
                            }}
                          >
                            {mediaApi.uploading ? t('toasts.uploading') : t('assets.drop')}
                          </div>
                          {selectedAssets.length > 0 ? (
                            <p className="wb-ws__asset-selection">
                              {t('assets.selected', { count: selectedAssets.length })}
                            </p>
                          ) : null}

                          {selectedPrimaryAsset ? (
                            <div className="wb-ws__asset-usage" aria-label="Asset usage">
                              <p className="wb-ws__asset-usage-title">Used in</p>
                              <div className="wb-ws__asset-usage-list">
                                {(
                                  [
                                    ['hero', 'Hero'],
                                    ['gallery', 'Gallery'],
                                    ['homepage', 'Homepage'],
                                    ['landing', 'Landing Page'],
                                    ['downloads', 'Downloads'],
                                  ] as const
                                ).map(([key, label]) => {
                                  const used = selectedPrimaryAsset.usedIn ?? [];
                                  const isUsed =
                                    key === 'landing' ? used.includes('landing') || used.includes('cta') : used.includes(key);
                                  return (
                                    <div key={key} className="wb-ws__asset-usage-row">
                                      <span>{label}</span>
                                      <span className={`wb-ws__asset-usage-mark${isUsed ? ' is-on' : ''}`}>
                                        {isUsed ? '✓' : '—'}
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          ) : null}
                          <div className="wb-ws__asset-grid">{filteredAssets.map(renderAssetCard)}</div>
                          {previewAsset ? (
                            <div
                              className="wb-ws__asset-preview"
                              role="dialog"
                              aria-label={t('assets.preview')}
                            >
                              <div className="wb-ws__asset-preview-head">
                                <strong>{previewAsset.filename}</strong>
                                <button
                                  type="button"
                                  className="wb-ws__icon-btn"
                                  aria-label={t('assets.closePreview')}
                                  onClick={() => setPreviewAssetId(null)}
                                >
                                  ×
                                </button>
                              </div>
                              <div className="wb-ws__asset-preview-body">
                                {previewAsset.thumbUrl ? (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img src={previewAsset.thumbUrl} alt="" />
                                ) : (
                                  <IhIcon name="documents" size={28} />
                                )}
                              </div>
                              <p className="wb-ws__asset-meta">
                                {previewAsset.fileType} · {previewAsset.meta} ·{' '}
                                {previewAsset.tags.join(', ')}
                              </p>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => applyAssetToPreview(previewAsset)}
                              >
                                {t('assets.insert')}
                              </Button>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ) : null}

                    {open && sectionKey === 'recent' ? (
                      <div className="wb-ws__collapse-body">
                        <div className="wb-ws__prompts">
                          {RECENT_PROMPTS.map((key) => (
                            <button
                              key={key}
                              type="button"
                              className="wb-ws__prompt"
                              onClick={() => setBrief(t(`prompts.${key}`))}
                            >
                              {t(`prompts.${key}`)}
                            </button>
                          ))}
                        </div>
                        <div className="wb-ws__refs">
                          <div className="wb-ws__ref-row">
                            <span>{t('ai.uploadedRefs')}</span>
                            <span>3</span>
                          </div>
                          <div className="wb-ws__ref-row">
                            <span>{t('ai.attachedFiles')}</span>
                            <span>5</span>
                          </div>
                          <div className="wb-ws__ref-row">
                            <span>{t('ai.prevGens')}</span>
                            <span>{versions.length}</span>
                          </div>
                        </div>
                        <p className="wb-ws__shortcuts-note">{t('shortcuts.title')}</p>
                        <ul className="wb-ws__shortcuts">
                          {KEYBOARD_SHORTCUTS.map((item) => (
                            <li key={item.actionKey}>
                              <kbd>{item.keys}</kbd>
                              <span>{t(`shortcuts.${item.actionKey}`)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </section>
                );
              })}
            </div>
          </aside>
            )
          }
          center={
            <section className="wb-ws__panel wb-ws__center" aria-label={t('canvas.aria')}>
            <FocusCanvasLayout
              isFullscreen={focus.isFullscreen}
              keepBottomChrome
              stageTestId="wb-canvas-stage"
              toolbar={
            <div className="wb-ws__canvas-bar">
              <div className="wb-ws__canvas-bar-inner">
                <div className="wb-ws__canvas-bar-group">
                  <button
                    type="button"
                    className="wb-ws__icon-btn"
                    aria-label={t('canvas.undo')}
                    onClick={undo}
                  >
                    <IhIcon name="chevronLeft" size={12} />
                  </button>
                  <button
                    type="button"
                    className="wb-ws__icon-btn"
                    aria-label={t('canvas.redo')}
                    onClick={redo}
                  >
                    <IhIcon name="chevronRight" size={12} />
                  </button>
                </div>

                <span className="wb-ws__canvas-bar-divider" aria-hidden="true" />

                <SegmentedControl
                  className="wb-ws__device-seg"
                  ariaLabel={t('canvas.deviceAria')}
                  value={device}
                  onChange={(v) => changeDevice(v)}
                  options={deviceOptions}
                />

                <span className="wb-ws__canvas-bar-divider" aria-hidden="true" />

                <div className="wb-ws__zoom" data-testid="wb-zoom" role="group" aria-label={t('canvas.zoomAria')}>
                  <FocusFitToViewToolbar engine={ftv} className="wb-ws__ftv-toolbar" />
                  <button
                    type="button"
                    className={`wb-ws__fit-btn${focus.isFullscreen ? ' is-active' : ''}`}
                    aria-label={t('canvas.fullscreen')}
                    aria-pressed={focus.isFullscreen}
                    data-testid="wb-fullscreen"
                    onClick={focus.toggleFullscreen}
                  >
                    {t('canvas.fullscreenShort')}
                  </button>
                </div>

                <span className="wb-ws__canvas-bar-divider" aria-hidden="true" />

                <div className="wb-ws__canvas-bar-group">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setRightTab('publishing');
                      showToast(t('toasts.historyOpened'));
                    }}
                  >
                    <IhIcon name="clock" size={12} />
                    {t('canvas.history')}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    data-testid="wb-canvas-preview"
                    onClick={() => showToast(t('toasts.preview'))}
                  >
                    {t('preview')}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    data-testid="wb-canvas-publish"
                    onClick={() => {
                      setPublishOpen(true);
                    }}
                  >
                    {t('publish')}
                  </Button>
                </div>
              </div>
            </div>
              }
              tray={{
                label: tFocus('tray.structure'),
                count: sections.length,
                countLabel: t('structure.pageSections', { count: sections.length }),
                testId: 'wb-structure-tray',
                handleTestId: 'wb-tray-handle',
                content: (
                  <CsStructureGrid
                    testId="wb-structure-grid"
                    className="wb-ws__structure-grid"
                    ariaLabel={t('structure.title')}
                    items={sections.map((section) => {
                      const label = sectionLabel(section, t);
                      const displayLabel = !section.visible
                        ? `${label} · ${t('structure.hidden')}`
                        : label;
                      return {
                        id: section.id,
                        label: displayLabel,
                        icon: SECTION_ICONS[section.key],
                        selected: selectedSectionId === section.id,
                        dropTarget: dropTargetId === section.id,
                        dragging: dragSectionId === section.id,
                        muted: Boolean(section.collapsed) || !section.visible,
                        testId: `wb-structure-card-${section.id}`,
                        labelNode:
                          renamingId === section.id ? (
                            <input
                              className="cs-structure-grid__rename"
                              value={renameValue}
                              autoFocus
                              aria-label={t('structureActions.rename')}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => setRenameValue(e.target.value)}
                              onBlur={() => commitRename(section.id)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') commitRename(section.id);
                                if (e.key === 'Escape') setRenamingId(null);
                              }}
                            />
                          ) : undefined,
                        onSelect: () => selectSection(section),
                        onDoubleClick: () => {
                          setRenamingId(section.id);
                          setRenameValue(label);
                          selectSection(section);
                        },
                        onDragStart: (e) => onStructureDragStart(e, section.id),
                        onDragOver: (e) => onStructureDragOver(e, section.id),
                        onDrop: (e) => onStructureDrop(e, section.id),
                        onDragEnd: () => {
                          setDragSectionId(null);
                          setDropTargetId(null);
                        },
                      };
                    })}
                    addTestId="wb-structure-add"
                    addLabel={t('rails.quick.addSection')}
                    onAdd={() => {
                      if (selectedSection) addSectionAfter(selectedSection);
                      else showToast(t('bottomBar.toasts.addComponent'));
                    }}
                  />
                ),
              }}
              dock={{
                testId: 'wb-scene-actions',
                className: 'wb-ws__scene-actions',
                primary: (
                  <CsBottomActionToolbar
                    testId="wb-bat"
                    ariaLabel={t('bottomBar.toolbarAria')}
                    primary={{
                      label: t('bottomBar.actions.addComponent'),
                      icon: 'plus',
                      onClick: () => {
                        if (selectedSection) addSectionAfter(selectedSection);
                        else showToast(t('bottomBar.toasts.addComponent'));
                      },
                      testId: 'wb-action-addComponent',
                    }}
                    actions={BLOCK_LIBRARY.map((block, index) => ({
                      key: block.key,
                      icon: block.icon,
                      label: t(`blocks.items.${block.key}`),
                      onClick: () => insertBlockFromLibrary(block.key),
                      testId: `wb-action-${block.key}`,
                      priority: index >= 7 ? 'low' : 'normal',
                    }))}
                  />
                ),
              }}
            >
            <div
              className={`wb-ws__canvas-stage${deviceAnimating ? ' is-device-switch' : ''}`}
              ref={canvasStageRef}
            >
              <FocusFitStage engine={ftv} artboardTestId="wb-ftv-artboard">
              {device === 'split' ? (
                <div
                  className="wb-ws__split"
                  data-testid="wb-live-preview"
                  data-panes={splitPanes.length}
                  data-preset={splitPreset}
                >
                  {splitPanes.map((pane) => renderPreview(pane.device, `-${pane.id}`))}
                </div>
              ) : (
                renderPreview(device)
              )}
              </FocusFitStage>
              {device === 'split' ? (
                <div className="wb-ws__split-presets" role="group" aria-label={t('canvas.splitPresetAria')}>
                  {(Object.keys(SPLIT_PRESETS) as SplitPanePreset[]).map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      className={`wb-ws__split-preset${splitPreset === preset ? ' is-active' : ''}`}
                      onClick={() => setSplitPreset(preset)}
                    >
                      {t(`canvas.splitPresets.${preset}`)}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            </FocusCanvasLayout>
          </section>
          }
          right={
            focus.isFocus || focus.isFullscreen ? (
              focusRightDrawer
            ) : (
            <aside className="wb-ws__panel wb-ws__right" aria-label={t('right.aria')}>
            <div className="wb-ws__tabs" role="tablist" aria-label={t('right.tabsAria')}>
              {RIGHT_TABS.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={rightTab === tab}
                  className={`wb-ws__tab${rightTab === tab ? ' is-active' : ''}`}
                  onClick={() => setRightTab(tab)}
                >
                  {t(`right.tabs.${tab}`)}
                </button>
              ))}
            </div>
            <div className="wb-ws__panel-body">
              {(rightTab === 'properties' || rightTab === 'language') && (
                <div className="wb-ws__props">
                  {renderQuickAiPanel()}

                  {editTarget ? (
                    <div className="wb-ws__edit-context">
                      <p className="wb-ws__section-label">{t(`editTarget.${editTarget}`)}</p>
                      {editTarget === 'text' || editTarget === 'hero' ? (
                        <>
                          <div className="wb-ws__prop">
                            <label htmlFor="wb-hero-title">{t('fields.heroTitle')}</label>
                            <input
                              id="wb-hero-title"
                              value={heroTitle}
                              onChange={(e) => setHeroTitle(e.target.value)}
                            />
                          </div>
                          <div className="wb-ws__prop">
                            <label htmlFor="wb-hero-body">{t('fields.heroBody')}</label>
                            <textarea
                              id="wb-hero-body"
                              value={heroBody}
                              onChange={(e) => setHeroBody(e.target.value)}
                            />
                          </div>
                        </>
                      ) : null}
                      {editTarget === 'button' ? (
                        <>
                          <div className="wb-ws__prop">
                            <label htmlFor="wb-cta-primary">{t('fields.ctaPrimary')}</label>
                            <input
                              id="wb-cta-primary"
                              value={ctaPrimary}
                              onChange={(e) => setCtaPrimary(e.target.value)}
                            />
                          </div>
                          <div className="wb-ws__prop">
                            <label htmlFor="wb-cta-secondary">{t('fields.ctaSecondary')}</label>
                            <input
                              id="wb-cta-secondary"
                              value={ctaSecondary}
                              onChange={(e) => setCtaSecondary(e.target.value)}
                            />
                          </div>
                        </>
                      ) : null}
                      {editTarget === 'image' ? (
                        <div className="wb-ws__prop">
                          <label>{t('fields.heroMedia')}</label>
                          <span>{t('options.coverFromProject')}</span>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setOpenLeft((prev) => ({ ...prev, assets: true }));
                              showToast(t('toasts.replaceImage'));
                            }}
                          >
                            {t('sectionActions.replaceImage')}
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  {rightTab === 'properties' && selectedSection ? (
                    <>
                      {selectedSection.key === 'hero' ? (
                        <>
                          <p className="wb-ws__section-label">{t('right.blockActions.hero.title')}</p>
                          <div className="wb-ws__ai-actions">
                            <Button variant="secondary" size="sm" onClick={() => handleGenerate('hero')}>
                              {t('right.blockActions.hero.rewriteHero')}
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => runQuickAi('newCta')}
                              disabled={generating}
                            >
                              {t('right.blockActions.hero.generateCta')}
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => {
                                selectSection(selectedSection, 'image');
                                setOpenLeft((prev) => ({ ...prev, assets: true }));
                                showToast(t('toasts.replaceImage'));
                              }}
                              disabled={generating}
                            >
                              {t('right.blockActions.hero.replaceBackground')}
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => runQuickAi('seoOptimize')}
                              disabled={generating}
                            >
                              {t('right.blockActions.hero.improveSeo')}
                            </Button>
                          </div>
                        </>
                      ) : null}

                      {selectedSection.key === 'gallery' ? (
                        <>
                          <p className="wb-ws__section-label">{t('right.blockActions.gallery.title')}</p>
                          <div className="wb-ws__ai-actions">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => {
                                selectSection(selectedSection, 'image');
                                setOpenLeft((prev) => ({ ...prev, assets: true }));
                                showToast(t('toasts.replaceImage'));
                              }}
                              disabled={generating}
                            >
                              {t('right.blockActions.gallery.addImages')}
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => runQuickAi('generateImage')}
                              disabled={generating}
                            >
                              {t('right.blockActions.gallery.aiImageSelection')}
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => reorderGalleryImages()}
                              disabled={generating || !galleryUrls.length}
                            >
                              {t('right.blockActions.gallery.reorder')}
                            </Button>
                          </div>
                        </>
                      ) : null}

                      {selectedSection.key === 'cta' ? (
                        <>
                          <p className="wb-ws__section-label">{t('right.blockActions.cta.title')}</p>
                          <div className="wb-ws__ai-actions">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleGenerate('section')}
                              disabled={generating}
                            >
                              {t('right.blockActions.cta.improveConversion')}
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => runQuickAi('rewrite')}
                              disabled={generating}
                            >
                              {t('right.blockActions.cta.rewriteButton')}
                            </Button>
                          </div>
                        </>
                      ) : null}
                    </>
                  ) : null}

                  <p className="wb-ws__section-label">{t('right.general')}</p>
                  <div className="wb-ws__prop">
                    <label htmlFor="wb-lang">{t('fields.language')}</label>
                    <select
                      id="wb-lang"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                    >
                      <option value="tr">{t('options.language.tr')}</option>
                      <option value="en">{t('options.language.en')}</option>
                      <option value="bi">{t('options.language.bi')}</option>
                    </select>
                  </div>
                  <div className="wb-ws__prop">
                    <label htmlFor="wb-tone">{t('fields.tone')}</label>
                    <select id="wb-tone" value={tone} onChange={(e) => setTone(e.target.value)}>
                      <option value="luxury">{t('options.tone.luxury')}</option>
                      <option value="investor">{t('options.tone.investor')}</option>
                      <option value="corporate">{t('options.tone.corporate')}</option>
                      <option value="simple">{t('options.tone.simple')}</option>
                    </select>
                  </div>
                  <div className="wb-ws__prop">
                    <label>{t('fields.project')}</label>
                    <span>{project.name}</span>
                  </div>
                  <div className="wb-ws__prop">
                    <label>{t('fields.section')}</label>
                    <span>{sectionLabel(selectedSection, t)}</span>
                  </div>
                  <div className="wb-ws__prop">
                    <label>{t('fields.masterBrand')}</label>
                    <span>Investhome</span>
                  </div>
                  <div className="wb-ws__prop">
                    <label>{t('fields.theme')}</label>
                    <span>{t('options.theme')}</span>
                  </div>
                  <div className="wb-ws__prop">
                    <label>{t('fields.colors')}</label>
                    <div className="wb-ws__color-row">
                      <span className="wb-ws__swatch wb-ws__swatch--navy" />
                      <span className="wb-ws__swatch wb-ws__swatch--cyan" />
                      <span className="wb-ws__swatch wb-ws__swatch--ink" />
                      <span className="wb-ws__swatch wb-ws__swatch--surface" />
                    </div>
                  </div>
                </div>
              )}

              {rightTab === 'design' ? (
                <div className="wb-ws__props">
                  {renderQuickAiPanel()}
                  {renderDesignAccordions()}
                </div>
              ) : null}

              {rightTab === 'seo' ? (
                <div className="wb-ws__props">
                  <p className="wb-ws__section-label">{t('right.seo')}</p>
                  <div className="wb-ws__prop">
                    <label htmlFor="wb-meta-title">{t('fields.metaTitle')}</label>
                    <input
                      id="wb-meta-title"
                      value={metaTitle}
                      onChange={(e) => setMetaTitle(e.target.value)}
                    />
                  </div>
                  <div className="wb-ws__prop">
                    <label htmlFor="wb-meta-desc">{t('fields.metaDescription')}</label>
                    <textarea
                      id="wb-meta-desc"
                      value={metaDesc}
                      onChange={(e) => setMetaDesc(e.target.value)}
                    />
                  </div>
                  <div className="wb-ws__prop">
                    <label htmlFor="wb-slug">{t('fields.slug')}</label>
                    <input id="wb-slug" value={slug} onChange={(e) => setSlug(e.target.value)} />
                  </div>
                  <div className="wb-ws__prop">
                    <label>{t('fields.openGraph')}</label>
                    <span>{t('options.openGraph', { project: project.name })}</span>
                  </div>
                  <div className="wb-ws__prop">
                    <label htmlFor="wb-keywords">{t('fields.keywords')}</label>
                    <input
                      id="wb-keywords"
                      defaultValue="investhome, temple residences, us real estate"
                    />
                  </div>
                </div>
              ) : null}

              {rightTab === 'publishing' ? (
                <div className="wb-ws__props">
                  <p className="wb-ws__section-label">{t('right.publishing')}</p>
                  <div className="wb-ws__publish-card">
                    <div className="wb-ws__publish-row">
                      <span>{t('fields.status')}</span>
                      <StatusChip tone={PUBLISH_STATUS_TONE[publishStatus]}>
                        {t(`status.${publishStatus}`)}
                      </StatusChip>
                    </div>
                    <div className="wb-ws__publish-row">
                      <span>{t('fields.version')}</span>
                      <span>
                        {activeVersion.label} — {t(`status.${activeVersion.status}`)}
                      </span>
                    </div>
                    <div className="wb-ws__publish-row">
                      <span>{t('fields.updated')}</span>
                      <span>{activeVersion.updatedAt}</span>
                    </div>
                    <Button variant="primary" size="sm" onClick={() => setPublishOpen(true)}>
                      {t('publish')}
                    </Button>
                  </div>

                  <p className="wb-ws__section-label">{t('right.exports')}</p>
                  <div className="wb-ws__export-list">
                    {PUBLISH_EXPORTS.map((key) => (
                      <button key={key} type="button" className="wb-ws__export-btn">
                        {t(`exports.${key}`)}
                        <IhIcon name="arrowRight" size={11} />
                      </button>
                    ))}
                  </div>

                  <p className="wb-ws__section-label">{t('right.versions')}</p>
                  {restoreConfirmId ? (
                    <div className="wb-ws__publish-card" role="alertdialog" aria-label={t('restoreConfirmTitle')}>
                      <p>
                        {t('restoreConfirm', {
                          version:
                            versions.find((v) => v.id === restoreConfirmId)?.label ??
                            restoreConfirmId,
                        })}
                      </p>
                      <div className="wb-ws__version-actions">
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={docApi.restoring}
                          onClick={() => void confirmRestoreVersion(restoreConfirmId)}
                        >
                          {t('confirmRestore')}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setRestoreConfirmId(null)}
                        >
                          {tCommon('cancel')}
                        </Button>
                      </div>
                    </div>
                  ) : null}
                  <div className="wb-ws__version-list">
                    {versions.map((version) => (
                      <button
                        key={version.id}
                        type="button"
                        className={`wb-ws__version-row${activeVersionId === version.id ? ' is-active' : ''}${compareVersionId === version.id ? ' is-compare' : ''}`}
                        onClick={() => docApi.setActiveVersionId(version.id)}
                      >
                        <span>
                          {version.label}
                          <span className="wb-ws__version-meta">
                            {' '}
                            · {version.comment || t(`versionNotes.${version.noteKey}`)}
                          </span>
                          {version.comment ? (
                            <span className="wb-ws__version-comment">{version.comment}</span>
                          ) : null}
                        </span>
                        <span className="wb-ws__version-meta">{version.updatedAt}</span>
                      </button>
                    ))}
                  </div>
                  <div className="wb-ws__version-comment-box">
                    <label className="sr-only" htmlFor="wb-version-comment">
                      {t('versionActions.comment')}
                    </label>
                    <input
                      id="wb-version-comment"
                      value={versionComment}
                      onChange={(e) => setVersionComment(e.target.value)}
                      placeholder={t('versionLabelPlaceholder')}
                    />
                  </div>
                  <div className="wb-ws__version-actions">
                    <button
                      type="button"
                      className="wb-ws__block-chip"
                      onClick={() => {
                        void (async () => {
                          try {
                            const label =
                              versionComment.trim() || `v${versions.length + 1}`;
                            const created = await docApi.createVersion(
                              buildPersistInput(),
                              label,
                            );
                            if (created) {
                              setVersionComment('');
                              showToast(
                                t('toasts.versionCreated', { label: created.label }),
                              );
                            }
                          } catch {
                            showToast(t('toasts.saveFailed'));
                          }
                        })();
                      }}
                    >
                      {t('createVersion')}
                    </button>
                    {VERSION_ACTIONS.map((key) => (
                      <button
                        key={key}
                        type="button"
                        className="wb-ws__block-chip"
                        onClick={() => handleVersionAction(key)}
                      >
                        {t(`versionActions.${key}`)}
                      </button>
                    ))}
                  </div>
                  {compareVersionId ? (
                    <p className="wb-ws__compare-note">
                      {t('versionActions.compareNote', {
                        a: activeVersion.label,
                        b: versions.find((v) => v.id === compareVersionId)?.label ?? '',
                      })}
                    </p>
                  ) : null}
                </div>
              ) : null}

              {rightTab === 'quickAi' ? (
                <div className="wb-ws__props">
                  {renderQuickAiPanel()}
                  {reusedAssets.length > 0 ? (
                    <p className="wb-ws__reused-note">
                      {t('aiStatus.reusing', { count: reusedAssets.length })} —{' '}
                      {reusedAssets
                        .map((id) => {
                          const a = libraryAssets.find((x) => x.id === id);
                          return a ? a.filename : id;
                        })
                        .join(', ')}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          </aside>
            )
          }
        />

        {publishOpen ? (
          <div
            className="wb-ws__publish-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="wb-publish-title"
            data-testid="wb-publish-drawer"
          >
            <div className="wb-ws__publish-drawer-backdrop" onClick={() => setPublishOpen(false)} />
            <div className="wb-ws__publish-drawer-panel">
              <div className="wb-ws__publish-drawer-head">
                <h2 id="wb-publish-title">{t('publishChecklist.title')}</h2>
                <button
                  type="button"
                  className="wb-ws__icon-btn"
                  aria-label={t('publishChecklist.close')}
                  onClick={() => setPublishOpen(false)}
                >
                  ×
                </button>
              </div>
              <p className="wb-ws__publish-drawer-lead">{t('publishChecklist.lead')}</p>

              <div className="wb-ws__publish-quality-top">
                {allQualityChecksPass ? (
                  <div className="wb-ws__publish-ready" data-testid="wb-publish-ready">
                    <IhIcon name="check" size={14} />
                    {t('publishChecklist.ready')} · {aiQuality.overall}/100
                  </div>
                ) : (
                  <div className="wb-ws__publish-ready wb-ws__publish-ready--pending">
                    <IhIcon name="sparkles" size={14} />
                    Quality score · {aiQuality.overall}/100
                  </div>
                )}

                <div className="wb-ws__ai-quality-card" data-testid="wb-ai-quality-card">
                  <div className="wb-ws__ai-quality-head">
                    <span>AI Quality</span>
                    <strong>{aiQuality.overall}/100</strong>
                  </div>
                  <div className="wb-ws__ai-quality-grid" role="group" aria-label="AI quality metrics">
                    <div className="wb-ws__ai-quality-metric">
                      <span>SEO</span>
                      <strong>{aiQuality.seo}</strong>
                    </div>
                    <div className="wb-ws__ai-quality-metric">
                      <span>Accessibility</span>
                      <strong>{aiQuality.accessibility}</strong>
                    </div>
                    <div className="wb-ws__ai-quality-metric">
                      <span>Performance</span>
                      <strong>{aiQuality.performance}</strong>
                    </div>
                    <div className="wb-ws__ai-quality-metric">
                      <span>Content</span>
                      <strong>{aiQuality.content}</strong>
                    </div>
                  </div>
                </div>
              </div>

              <ul className="wb-ws__publish-checks">
                {PUBLISH_CHECKS.filter((c) => PUBLISH_QUALITY_CHECK_KEYS.includes(c.key)).map((check) => (
                  <li key={check.key}>
                    <button
                      type="button"
                      className={`wb-ws__publish-check${publishChecks[check.key] ? ' is-pass' : ' is-fail'}`}
                      onClick={() =>
                        setPublishChecks((prev) => ({
                          ...prev,
                          [check.key]: !prev[check.key],
                        }))
                      }
                    >
                      <IhIcon name={check.icon} size={14} />
                      <span>{t(`publishChecklist.items.${check.key}`)}</span>
                      <StatusChip tone={publishChecks[check.key] ? 'success' : 'warning'}>
                        {publishChecks[check.key]
                          ? t('publishChecklist.pass')
                          : t('publishChecklist.fail')}
                      </StatusChip>
                    </button>
                  </li>
                ))}
              </ul>
              <label className="wb-ws__publish-override">
                <input
                  type="checkbox"
                  checked={publishOverride}
                  onChange={(e) => setPublishOverride(e.target.checked)}
                />
                <span>{t('publishChecklist.override')}</span>
              </label>
              <div className="wb-ws__publish-drawer-actions">
                <Button variant="secondary" size="sm" onClick={() => setPublishOpen(false)}>
                  {t('publishChecklist.close')}
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!canPublish}
                  onClick={confirmPublish}
                  data-testid="wb-publish-confirm"
                >
                  {allQualityChecksPass ? t('publishChecklist.confirmReady') : t('publishChecklist.confirm')}
                </Button>
              </div>
              {!allQualityChecksPass && !publishOverride ? (
                <p className="wb-ws__publish-blocked">{t('publishChecklist.blocked')}</p>
              ) : null}
            </div>
          </div>
        ) : null}

        {restoreConfirmId ? (
          <div className="wb-ws__toast wb-ws__toast--confirm" role="alertdialog" aria-label={t('restoreConfirmTitle')}>
            <p>
              {t('restoreConfirm', {
                version:
                  versions.find((v) => v.id === restoreConfirmId)?.label ?? restoreConfirmId,
              })}
            </p>
            <div className="wb-ws__version-actions">
              <Button
                variant="primary"
                size="sm"
                disabled={docApi.restoring}
                onClick={() => void confirmRestoreVersion(restoreConfirmId)}
              >
                {t('confirmRestore')}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setRestoreConfirmId(null)}>
                {tCommon('cancel')}
              </Button>
            </div>
          </div>
        ) : null}
        {toast ? (
          <div className="wb-ws__toast" role="status" aria-live="polite">
            {toast}
          </div>
        ) : null}
      </div>
    </main>
  );
}
