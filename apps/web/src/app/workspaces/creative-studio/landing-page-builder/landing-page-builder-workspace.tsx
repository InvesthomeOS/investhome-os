'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  AB_VARIANTS,
  AI_COMPLETED_WORK,
  AI_PROGRESS_STEPS,
  AI_STATUS_SEQUENCE,
  AWARD_KEYS,
  BENEFIT_KEYS,
  BOTTOM_ACTIONS,
  DEFAULT_BRIEF,
  DEFAULT_PAGES,
  DEFAULT_SCORES,
  DEFAULT_SECTIONS,
  DEVICE_TOGGLE,
  FAQ_KEYS,
  FORM_FIELDS,
  HERO_STATS,
  HERO_TRUST_KEYS,
  LAUNCH_CHECKS,
  LPB_CHAT,
  LPB_HOME,
  LPB_LEFT_RAIL_ICONS,
  LPB_LEFT_RAIL_IDS,
  LPB_PROJECTS,
  LPB_RIGHT_RAIL_ICONS,
  LPB_RIGHT_RAIL_IDS,
  LPB_TEMPLATES,
  MEDIA_KEYS,
  PARTNER_LOGOS,
  PROGRESS_MILESTONES,
  SECTION_ICONS,
  SECTION_TONE,
  TESTIMONIAL_KEYS,
  TIMELINE_KEYS,
  getProject,
  reorderPages,
  type AbVariant,
  type AbVariantId,
  type AiActionKey,
  type AiCompletedWorkKey,
  type AiStatusKey,
  type BottomActionKey,
  type CampaignBrief,
  type CampaignStatus,
  type CampaignType,
  type CtaKey,
  type DevicePreview,
  type LaunchCheckKey,
  type LpbChatMessage,
  type LpbLeftRailId,
  type LpbPage,
  type LpbRightRailId,
  type LpbSection,
  type ProjectId,
  type QuickActionKey,
  type SectionKey,
  type SectionTrayActionKey,
  type TrustElementKey,
} from './landing-page-builder-model';

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

import {
  loadLastConstructionProjectId,
  loadPersistedLinkedProjectIdHint,
  resolvePreferredConstructionProjectId,
  saveEmergencySnapshot,
  saveLastConstructionProjectId,
} from './landing-page-builder-persistence';
import {
  LpbLeftRailDrawer,
  LpbLocalRail,
  LpbRightRailDrawer,
  LpbZoomToolbar,
} from './landing-page-builder-rail-drawers';
import {
  LpbSectionOverflowMenu,
  type LpbOverflowMenuItem,
} from './lpb-section-overflow-menu';

import './landing-page-builder.css';

function visualTemplateForProject(
  projectId: string,
  templates: typeof LPB_PROJECTS,
): (typeof LPB_PROJECTS)[number] {
  let hash = 0;
  const key = projectId || 'default';
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash + key.charCodeAt(i) * (i + 1)) % templates.length;
  }
  return templates[hash] ?? templates[0]!;
}

const ZOOM_DEFAULT = 100;
const DEVICE_CONTENT: Record<'desktop' | 'tablet' | 'mobile' | 'ab', { w: number; h: number }> = {
  desktop: { w: 1440, h: 900 },
  tablet: { w: 768, h: 1024 },
  mobile: { w: 390, h: 844 },
  ab: { w: 1440, h: 900 },
};

export function LandingPageBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');
  const tTools = useTranslations('creativeStudio.ds.tools');

  const docApi = useBuilderDocument({
    documentType: 'landing',
    preferredConstructionProject: {
      loadLastId: loadLastConstructionProjectId,
      saveLastId: saveLastConstructionProjectId,
      loadDraftLinkedHint: loadPersistedLinkedProjectIdHint,
      resolvePreferredId: resolvePreferredConstructionProjectId,
      onDraftSaved: saveEmergencySnapshot,
    },
  });
  const [hydrated, setHydrated] = useState(false);
  const [device, setDevice] = useState<DevicePreview>('desktop');
  // Legacy zoom state kept for A/B preview scale fallback; Fit-To-View owns Focus zoom.
  const [zoom] = useState(ZOOM_DEFAULT);
  const [activeStep, setActiveStep] = useState(0);
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus>('draft');
  const [saved, setSaved] = useState(false);
  const [lastSavedLabel, setLastSavedLabel] = useState('');
  const [generating, setGenerating] = useState(false);
  const [aiStatus, setAiStatus] = useState<AiStatusKey>('idle');
  const [progressStep, setProgressStep] = useState(-1);
  const [aiCompleted, setAiCompleted] = useState<Record<AiCompletedWorkKey, boolean>>(() =>
    Object.fromEntries(AI_COMPLETED_WORK.map((k) => [k, true])) as Record<AiCompletedWorkKey, boolean>,
  );
  const [briefInput, setBriefInput] = useState('');
  const [brief, setBrief] = useState<CampaignBrief>(DEFAULT_BRIEF);
  const [sections, setSections] = useState<LpbSection[]>(DEFAULT_SECTIONS);
  const [selectedSectionId, setSelectedSectionId] = useState('s-hero');
  const [pages, setPages] = useState<LpbPage[]>(DEFAULT_PAGES);
  const [selectedPageId, setSelectedPageId] = useState('pg-home');
  const [dragPageId, setDragPageId] = useState<string | null>(null);
  const [floatingMoreId, setFloatingMoreId] = useState<string | null>(null);
  const [chat, setChat] = useState<LpbChatMessage[]>(LPB_CHAT);
  const [leftRailId, setLeftRailId] = useState<LpbLeftRailId>('components');
  const [rightRailId, setRightRailId] = useState<LpbRightRailId>('page');
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [pageName, setPageName] = useState('Home');
  const [pageUrl, setPageUrl] = useState('/home');
  const [contentWidth, setContentWidth] = useState(1200);
  const [showHeader, setShowHeader] = useState(true);
  const [showFooter, setShowFooter] = useState(true);
  const [bgMode, setBgMode] = useState<'color' | 'image' | 'video'>('color');
  const [seoTitle, setSeoTitle] = useState('THE TEMPLE Residences — Investor Landing');
  const [seoDescription, setSeoDescription] = useState(
    'Premium Washington DC investment opportunity for high-intent investors.',
  );
  const [seoKeywords, setSeoKeywords] = useState('real estate, DC, investor, THE TEMPLE');
  const focus = useCreativeStudioFocusMode({ storageKey: 'landing-page-builder' });
  const filmstripRef = useRef<HTMLDivElement | null>(null);
  const floatingMoreRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const [scores, setScores] = useState(DEFAULT_SCORES);
  const [variants, setVariants] = useState<AbVariant[]>(AB_VARIANTS);
  const [activeVariant, setActiveVariant] = useState<AbVariantId>('b');
  const [selectedCta, setSelectedCta] = useState<CtaKey>('scheduleConsultation');
  const [activeTrust, setActiveTrust] = useState<TrustElementKey[]>([
    'testimonials',
    'timeline',
    'progress',
    'faq',
    'partners',
    'awards',
    'media',
    'maps',
  ]);
  const [formFields, setFormFields] = useState([...FORM_FIELDS]);
  const [launchOpen, setLaunchOpen] = useState(false);
  const [launchChecks, setLaunchChecks] = useState<Record<LaunchCheckKey, boolean>>(() =>
    Object.fromEntries(LAUNCH_CHECKS.map((c) => [c.key, c.defaultPass])) as Record<
      LaunchCheckKey,
      boolean
    >,
  );
  const [faqOpen, setFaqOpen] = useState<number | null>(0);
  const [toast, setToast] = useState<string | null>(null);
  const [heroTitle, setHeroTitle] = useState('');
  const [heroBody, setHeroBody] = useState('');
  const [ctaPrimary, setCtaPrimary] = useState('');
  const [ctaSecondary, setCtaSecondary] = useState('');

  const genTimerRef = useRef<number[]>([]);
  const selectedConstruction = useMemo(
    () =>
      docApi.constructionProjects.find((p) => p.id === docApi.constructionProjectId) ?? null,
    [docApi.constructionProjects, docApi.constructionProjectId],
  );
  const project = useMemo(() => {
    const visual = visualTemplateForProject(
      docApi.constructionProjectId || selectedConstruction?.project_name || 'default',
      LPB_PROJECTS,
    );
    if (!selectedConstruction) return visual;
    return {
      ...visual,
      name: selectedConstruction.project_name || visual.name,
      featuredLabel: selectedConstruction.project_name || visual.featuredLabel,
    };
  }, [docApi.constructionProjectId, selectedConstruction]);
  const templateGalleryUrls = useMemo(() => project.galleryUrls, [project.galleryUrls]);
  const coverAsset = useBuilderCoverAsset({
    templateCoverUrl: project.coverUrl,
    templateGalleryUrls,
    linkedProjectId: docApi.constructionProjectId,
    seedFromTemplate: false,
    scopeToLinkedProject: true,
  });
  const deviceSize = DEVICE_CONTENT[device] ?? DEVICE_CONTENT.desktop;
  const ftv = useFitToViewEngine({
    contentWidth: deviceSize.w,
    contentHeight: deviceSize.h,
    enabled: true,
    contentKey: `${device}-${activeVariant}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}`,
    canvasType: 'document',
  });

  useEffect(() => {
    if (focus.isFocus || focus.isFullscreen) {
      if (ftv.autoFit) ftv.fitToView();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.isFocus, focus.isFullscreen, device]);
  const allLaunchPass = LAUNCH_CHECKS.every((c) => launchChecks[c.key] || c.key === 'privacy');

  const lpbLeftRail: FocusRailItem[] = useMemo(
    () =>
      LPB_LEFT_RAIL_IDS.map((id) => ({
        id,
        icon: LPB_LEFT_RAIL_ICONS[id],
        labelKey: 'brief',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const lpbRightRail: FocusRailItem[] = useMemo(
    () =>
      LPB_RIGHT_RAIL_IDS.map((id) => ({
        id,
        icon: LPB_RIGHT_RAIL_ICONS[id],
        labelKey: 'export',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const localLeftItems = useMemo(
    () => lpbLeftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [lpbLeftRail],
  );
  const localRightItems = useMemo(
    () => lpbRightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [lpbRightRail],
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const result = await docApi.bootstrap();
      if (cancelled) return;
      setHeroTitle(t('canvas.heroTitle'));
      setHeroBody(t('canvas.heroBody'));
      setCtaPrimary(t(`cta.options.${selectedCta}`));
      setCtaSecondary(t('cta.options.downloadPackage'));
      if (result.ok) {
        coverAsset.hydrateMedia(
          result.draft?.coverImage ?? null,
          result.draft?.galleryImages ?? [],
        );
        if (result.draft) {
          setSaved(true);
          setLastSavedLabel(t('savedJustNow'));
        } else {
          setLastSavedLabel(t('notSavedYet'));
        }
      } else {
        setLastSavedLabel(t('notSavedYet'));
      }
      setHydrated(true);
    })();
    return () => {
      cancelled = true;
      genTimerRef.current.forEach((id) => window.clearTimeout(id));
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
          galleryImages: coverAsset.galleryImages,
        });
        if (ok) {
          setSaved(true);
          setLastSavedLabel(t('savedJustNow'));
        }
      })();
    }, 2000);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, docApi.loadStatus, coverAsset.coverImage, coverAsset.galleryImages]);

  useEffect(() => {
    if (!floatingMoreId) return;
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        setFloatingMoreId(null);
      }
    }
    document.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('keydown', onKey, true);
    };
  }, [floatingMoreId]);

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
        galleryImages: coverAsset.galleryImages,
      });
      if (ok) {
        setSaved(true);
        setLastSavedLabel(t('savedJustNow'));
        if (announce) showToast(t('toasts.saved'));
      } else if (announce) {
        showToast(t('toasts.saveFailed'));
      }
    },
    [coverAsset.coverImage, coverAsset.galleryImages, docApi, t],
  );

  async function handleProjectChange(id: string) {
    const draft = await docApi.selectConstructionProject(id);
    coverAsset.hydrateMedia(draft?.coverImage ?? null, draft?.galleryImages ?? []);
    setSaved(Boolean(draft));
    setLastSavedLabel(draft ? t('savedJustNow') : t('notSavedYet'));
  }

  function clearGenTimers() {
    genTimerRef.current.forEach((id) => window.clearTimeout(id));
    genTimerRef.current = [];
  }

  function handleGenerate(action: AiActionKey | QuickActionKey | 'entire' = 'entire') {
    clearGenTimers();
    setGenerating(true);
    setProgressStep(0);
    setAiStatus('thinking');
    setActiveStep(1);
    setAiCompleted(
      Object.fromEntries(AI_COMPLETED_WORK.map((k) => [k, false])) as Record<AiCompletedWorkKey, boolean>,
    );

    const campaignMap: Partial<Record<AiActionKey, CampaignType>> = {
      investorLanding: 'investor',
      webinar: 'webinar',
      projectLaunch: 'projectLaunch',
      consultation: 'consultation',
      brochure: 'brochure',
      earlyAccess: 'earlyAccess',
    };

    if (action in campaignMap && campaignMap[action as AiActionKey]) {
      const type = campaignMap[action as AiActionKey]!;
      setBrief((prev) => ({
        ...prev,
        campaignType: type,
        name:
          type === 'investor'
            ? 'The Temple Investor Landing'
            : `${project.featuredLabel} ${t(`templates.types.${type}`)}`,
      }));
    }

    const completeMap: AiCompletedWorkKey[] = [
      'heroGenerated',
      'ctaOptimized',
      'formCreated',
      'seoOptimized',
      'faqGenerated',
      'trustSectionAdded',
    ];

    AI_STATUS_SEQUENCE.forEach((status, index) => {
      const id = window.setTimeout(() => {
        setAiStatus(status);
        setProgressStep(Math.min(index, AI_PROGRESS_STEPS.length - 1));
        if (index < completeMap.length) {
          const doneKey = completeMap[index];
          setAiCompleted((prev) => ({ ...prev, [doneKey]: true }));
        }
        if (status === 'scoringConversion') {
          setScores((prev) => ({
            ...prev,
            overall: Math.min(99, prev.overall + 1),
            ctaStrength: Math.min(99, prev.ctaStrength + 1),
          }));
        }
        if (status === 'completed') {
          setGenerating(false);
          setProgressStep(AI_PROGRESS_STEPS.length);
          setAiCompleted(
            Object.fromEntries(AI_COMPLETED_WORK.map((k) => [k, true])) as Record<
              AiCompletedWorkKey,
              boolean
            >,
          );
          setChat((prev) => [
            ...prev,
            {
              id: `ai-${Date.now()}`,
              role: 'ai',
              textKey:
                action === 'improveCta' || action === 'generateBetterCta'
                  ? 'ctaOptimized'
                  : 'generated',
            },
          ]);
          setActiveStep(2);
          persistNow();
          showToast(t('toasts.generated'));
        }
      }, 450 * (index + 1));
      genTimerRef.current.push(id);
    });

    if (action === 'improveCta' || action === 'generateBetterCta') {
      setSelectedCta('scheduleConsultation');
      setCtaPrimary(t('cta.options.scheduleConsultation'));
    }
    if (action === 'rewriteHeadline') {
      setHeroTitle(t('canvas.heroTitleAlt'));
    }
    if (action === 'improveHero') {
      setHeroBody(t('canvas.heroBodyAlt'));
    }
    if (action === 'generateForm' || action === 'optimizeForm') {
      setFormFields([...FORM_FIELDS]);
      showToast(t('toasts.formGenerated'));
    }
    if (action === 'insertTrust') {
      setActiveTrust(['testimonials', 'timeline', 'progress', 'awards', 'faq', 'partners', 'media', 'maps']);
    }
    if (action === 'generateAlternate') {
      createVariant();
    }
  }

  function sendBrief() {
    const text = briefInput.trim() || t('prompts.investorLanding');
    setBriefInput('');
    setChat((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', text },
      { id: `ai-${Date.now() + 1}`, role: 'ai', textKey: 'briefSummary' },
    ]);
    setLeftRailId('components');
    handleGenerate('investorLanding');
  }

  function selectSection(section: LpbSection) {
    setSelectedSectionId(section.id);
    setFloatingMoreId(null);
  }

  function handleSectionAction(action: SectionTrayActionKey, sectionId = selectedSectionId) {
    const section = sections.find((s) => s.id === sectionId);
    if (!section) return;
    setFloatingMoreId(null);

    if (action === 'edit') {
      selectSection(section);
      showToast(t('toasts.sectionEdit', { section: t(`sections.${section.key}`) }));
      return;
    }
    if (action === 'rewrite') {
      selectSection(section);
      handleGenerate('rewriteHeadline');
      showToast(t('toasts.sectionRewrite', { section: t(`sections.${section.key}`) }));
      return;
    }
    if (action === 'replaceImage') {
      selectSection(section);
      coverAsset.openPicker('cover');
      showToast(t('toasts.sectionReplaceImage'));
      return;
    }
    if (action === 'duplicate') {
      const copy: LpbSection = {
        id: `s-${section.key}-${Date.now()}`,
        key: section.key,
        visible: true,
      };
      setSections((prev) => {
        const idx = prev.findIndex((s) => s.id === section.id);
        const next = [...prev];
        next.splice(idx + 1, 0, copy);
        return next;
      });
      setSelectedSectionId(copy.id);
      setSaved(false);
      showToast(t('toasts.sectionDuplicated'));
      return;
    }
    if (action === 'hide') {
      setSections((prev) =>
        prev.map((s) => (s.id === section.id ? { ...s, visible: !s.visible } : s)),
      );
      setSaved(false);
      showToast(
        section.visible
          ? t('toasts.sectionHidden', { section: t(`sections.${section.key}`) })
          : t('toasts.sectionShown', { section: t(`sections.${section.key}`) }),
      );
      return;
    }
    if (action === 'delete') {
      if (sections.length <= 1) {
        showToast(t('toasts.cannotDeleteLastSection'));
        return;
      }
      setSections((prev) => prev.filter((s) => s.id !== section.id));
      if (selectedSectionId === section.id) {
        const fallback = sections.find((s) => s.id !== section.id);
        if (fallback) setSelectedSectionId(fallback.id);
      }
      setSaved(false);
      showToast(t('toasts.sectionDeleted'));
    }
  }

  function addSection() {
    const id = `s-cta-${Date.now()}`;
    const next: LpbSection = { id, key: 'cta', visible: true };
    setSections((prev) => {
      const idx = prev.findIndex((s) => s.id === selectedSectionId);
      const copy = [...prev];
      copy.splice(idx >= 0 ? idx + 1 : copy.length, 0, next);
      return copy;
    });
    setSelectedSectionId(id);
    setSaved(false);
    showToast(t('toasts.sectionAdded'));
  }

  function addPage() {
    const id = `pg-${Date.now()}`;
    const page: LpbPage = {
      id,
      kind: 'custom',
      thumbUrl: coverAsset.coverDisplayUrl,
    };
    setPages((prev) => [...prev, page]);
    setSelectedPageId(id);
    markDirty();
    showToast(t('toasts.pageAdded'));
  }

  function scrollFilmstrip(dir: -1 | 1) {
    const el = filmstripRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 160, behavior: 'smooth' });
  }

  function handleBottomAction(action: BottomActionKey) {
    if (action === 'addSection') {
      addSection();
      return;
    }
    if (action === 'abTest') {
      setDevice('ab');
      showToast(t(`bottomBar.toasts.${action}`));
      return;
    }
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function createVariant() {
    const nextId = `v-${Date.now()}` as unknown as AbVariantId;
    const tones = ['a', 'b', 'c'] as const;
    const copy: AbVariant = {
      id: nextId,
      label: `${t('ab.newVariant')} ${variants.length + 1}`,
      conversionProb: Number((12 + Math.random() * 8).toFixed(1)),
      noteKey: 'control',
      thumbTone: tones[variants.length % 3],
      whyKey: 'control',
    };
    setVariants((prev) => [...prev, copy]);
    setActiveVariant(copy.id);
    setChat((prev) => [...prev, { id: `ai-${Date.now()}`, role: 'ai', textKey: 'variantCreated' }]);
    showToast(t('toasts.variantCreated'));
  }

  function confirmLaunch() {
    setCampaignStatus('launch');
    setLaunchOpen(false);
    setActiveStep(4);
    showToast(t('toasts.launched'));
  }

  function chatText(msg: LpbChatMessage): string {
    if (msg.text) return msg.text;
    if (!msg.textKey) return '';
    return t(`chat.${msg.textKey}`, {
      project: project.name,
      goal: brief.primaryGoal,
      audience: brief.audience,
      cta: brief.cta,
    });
  }

  function renderTrustExtras() {
    return (
      <div className="lpb-ws__trust-extras">
        {activeTrust.includes('partners') ? (
          <div className="lpb-ws__partners" data-testid="lpb-partners">
            <p className="lpb-ws__trust-eyebrow">{t('canvas.partnersTitle')}</p>
            <div className="lpb-ws__partner-row">
              {PARTNER_LOGOS.map((name) => (
                <span key={name} className="lpb-ws__partner-logo">
                  {name}
                </span>
              ))}
            </div>
          </div>
        ) : null}
        {activeTrust.includes('awards') ? (
          <div className="lpb-ws__awards">
            <p className="lpb-ws__trust-eyebrow">{t('canvas.awardsTitle')}</p>
            <div className="lpb-ws__award-row">
              {AWARD_KEYS.map((key) => (
                <div key={key} className="lpb-ws__award-chip">
                  <IhIcon name="target" size={12} />
                  <span>{t(`canvas.awards.${key}`)}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        {activeTrust.includes('media') ? (
          <div className="lpb-ws__media">
            <p className="lpb-ws__trust-eyebrow">{t('canvas.mediaTitle')}</p>
            <div className="lpb-ws__media-row">
              {MEDIA_KEYS.map((key) => (
                <span key={key} className="lpb-ws__media-chip">
                  {t(`canvas.media.${key}`)}
                </span>
              ))}
            </div>
          </div>
        ) : null}
        {activeTrust.includes('progress') ? (
          <div className="lpb-ws__progress-block">
            <p className="lpb-ws__trust-eyebrow">{t('canvas.progressTitle')}</p>
            <div className="lpb-ws__progress-list">
              {PROGRESS_MILESTONES.map((item) => (
                <div key={item.key} className="lpb-ws__progress-row">
                  <div className="lpb-ws__progress-label">
                    <span>{t(`canvas.progress.${item.key}`)}</span>
                    <strong>{item.pct}%</strong>
                  </div>
                  <div className="lpb-ws__meter" aria-hidden="true">
                    <span style={{ width: `${item.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        {activeTrust.includes('maps') ? (
          <div className="lpb-ws__map-block">
            <p className="lpb-ws__trust-eyebrow">{t('canvas.mapTitle')}</p>
            <div className="lpb-ws__map-preview" aria-hidden="true">
              <span>{t('canvas.mapLabel')}</span>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  function renderPreview() {
    const scale = zoom / 100;
    if (device === 'ab') {
      return (
        <div className="lpb-ws__preview-zoom is-ab" style={{ transform: `scale(${scale})`, transformOrigin: 'top center' }}>
          <div className="lpb-ws__ab-split" data-testid="lpb-ab-preview">
            {['a', 'b'].map((id) => {
              const variant = variants.find((v) => v.id === id) ?? variants[0];
              return (
                <div key={id} className="lpb-ws__ab-pane">
                  <div className="lpb-ws__ab-pane-head">
                    <span>{variant.label}</span>
                    <StatusChip tone={variant.isBest ? 'success' : 'default'}>
                      {variant.conversionProb}%
                    </StatusChip>
                  </div>
                  <div className="lpb-ws__ab-pane-body">
                    <strong>{project.featuredLabel}</strong>
                    <p>{id === 'b' ? ctaPrimary : t('cta.options.requestInfo')}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    return (
      <div
        className={`lpb-ws__preview-zoom is-${device}`}
        style={{ transform: `scale(${scale})`, transformOrigin: 'top center' }}
      >
        <div className={`lpb-ws__preview is-${device}`} data-testid="lpb-live-preview">
          <div className="lpb-ws__browser-chrome" aria-hidden="true">
            <div className="lpb-ws__browser-chrome-dots">
              <span className="lpb-ws__browser-dot lpb-ws__browser-dot--red" />
              <span className="lpb-ws__browser-dot lpb-ws__browser-dot--yellow" />
              <span className="lpb-ws__browser-dot lpb-ws__browser-dot--green" />
            </div>
            <div className="lpb-ws__browser-chrome-address">
              investhome.os/campaigns/{project.slug}
            </div>
          </div>

          <div className="lpb-ws__site-nav">
            <span className="lpb-ws__brand">INVESTHOME</span>
            <div className="lpb-ws__site-links">
              <span>{t('canvas.nav.overview')}</span>
              <span>{t('canvas.nav.roi')}</span>
              <span>{t('canvas.nav.faq')}</span>
              <span>{t('canvas.nav.contact')}</span>
            </div>
          </div>

          {sections
            .filter((s) => s.visible)
            .map((section) => {
              const selected = selectedSectionId === section.id;
              const moreOpen = floatingMoreId === section.id;
              const moreItems: LpbOverflowMenuItem[] = [
                {
                  key: 'rewrite',
                  label: t('sectionActions.rewrite'),
                  onSelect: () => handleSectionAction('rewrite', section.id),
                },
                {
                  key: 'replaceImage',
                  label: t('sectionActions.replaceImage'),
                  onSelect: () => handleSectionAction('replaceImage', section.id),
                },
                {
                  key: 'hide',
                  label: section.visible ? t('sectionActions.hide') : t('sectionActions.show'),
                  onSelect: () => handleSectionAction('hide', section.id),
                },
              ];
              const toolbar = (
                <div className="lpb-ws__section-toolbar" data-testid={`lpb-section-toolbar-${section.id}`}>
                  <button
                    type="button"
                    className="lpb-ws__section-toolbar-btn"
                    title={t('floating.edit')}
                    aria-label={t('floating.edit')}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSectionAction('edit', section.id);
                    }}
                  >
                    <IhIcon name="design" size={12} />
                    {t('floating.edit')}
                  </button>
                  <button
                    type="button"
                    className="lpb-ws__section-toolbar-btn"
                    title={t('floating.duplicate')}
                    aria-label={t('floating.duplicate')}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSectionAction('duplicate', section.id);
                    }}
                  >
                    <IhIcon name="documents" size={12} />
                    {t('floating.duplicate')}
                  </button>
                  <button
                    type="button"
                    className="lpb-ws__section-toolbar-btn"
                    title={t('floating.delete')}
                    aria-label={t('floating.delete')}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSectionAction('delete', section.id);
                    }}
                  >
                    <IhIcon name="alert" size={12} />
                    {t('floating.delete')}
                  </button>
                  <button
                    type="button"
                    className="lpb-ws__section-toolbar-btn"
                    title={t('floating.sectionSettings')}
                    aria-label={t('floating.sectionSettings')}
                    onClick={(e) => {
                      e.stopPropagation();
                      selectSection(section);
                      setRightRailId('page');
                    }}
                  >
                    <IhIcon name="settings" size={12} />
                    {t('floating.sectionSettings')}
                  </button>
                  <button
                    type="button"
                    ref={(el) => {
                      floatingMoreRefs.current[section.id] = el;
                    }}
                    className={`lpb-ws__section-toolbar-btn${moreOpen ? ' is-active' : ''}`}
                    title={t('floating.more')}
                    aria-label={t('floating.more')}
                    aria-expanded={moreOpen}
                    aria-haspopup="menu"
                    data-testid={`lpb-section-more-${section.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      selectSection(section);
                      setFloatingMoreId((prev) => (prev === section.id ? null : section.id));
                    }}
                  >
                    ⋯
                  </button>
                  <LpbSectionOverflowMenu
                    open={moreOpen}
                    anchorRef={{
                      get current() {
                        return floatingMoreRefs.current[section.id] ?? null;
                      },
                    }}
                    items={moreItems}
                    onClose={() => setFloatingMoreId(null)}
                    ariaLabel={t('floating.more')}
                  />
                </div>
              );

              if (section.key === 'hero') {
                return (
                  <div
                    key={section.id}
                    className={`lpb-ws__hero lpb-ws__editable${selected ? ' is-selected' : ''}`}
                    style={{ backgroundImage: `url(${coverAsset.coverDisplayUrl})` }}
                    onClick={() => selectSection(section)}
                    role="presentation"
                  >
                    {toolbar}
                    <div className="lpb-ws__hero-inner">
                      <div className="lpb-ws__hero-kicker">
                        <span className="lpb-ws__hero-badge">{t('canvas.opportunityBadge')}</span>
                        <p className="lpb-ws__hero-eyebrow">
                          {t('canvas.featured', { project: project.featuredLabel })}
                        </p>
                      </div>
                      <h3
                        contentEditable
                        suppressContentEditableWarning
                        onBlur={(e) => setHeroTitle(e.currentTarget.textContent || heroTitle)}
                      >
                        {heroTitle}
                      </h3>
                      <p
                        className="lpb-ws__hero-lead"
                        contentEditable
                        suppressContentEditableWarning
                        onBlur={(e) => setHeroBody(e.currentTarget.textContent || heroBody)}
                      >
                        {heroBody}
                      </p>
                      <p className="lpb-ws__hero-value">{t('canvas.heroValue')}</p>
                      <div className="lpb-ws__hero-stats">
                        {HERO_STATS.map((stat) => (
                          <div key={stat.key} className="lpb-ws__hero-stat">
                            <strong>{stat.value}</strong>
                            <span>{t(`canvas.stats.${stat.key}`)}</span>
                          </div>
                        ))}
                      </div>
                      <div className="lpb-ws__hero-ctas">
                        <button type="button" className="lpb-ws__hero-cta lpb-ws__hero-cta--primary">
                          {ctaPrimary}
                        </button>
                        <button type="button" className="lpb-ws__hero-cta lpb-ws__hero-cta--ghost">
                          {ctaSecondary}
                        </button>
                      </div>
                      <div className="lpb-ws__hero-trust">
                        {HERO_TRUST_KEYS.map((key) => (
                          <span key={key} className="lpb-ws__hero-trust-item">
                            <IhIcon name="check" size={11} />
                            {t(`canvas.heroTrust.${key}`)}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              }

              const tone = SECTION_TONE[section.key] ?? 'light';
              return (
                <div
                  key={section.id}
                  className={`lpb-ws__section-block lpb-ws__editable lpb-ws__section-block--${tone}${selected ? ' is-selected' : ''}`}
                  onClick={() => selectSection(section)}
                  role="presentation"
                >
                  {toolbar}
                  {section.key === 'benefits' ? (
                    <>
                      <h4>{t('canvas.benefitsTitle')}</h4>
                      <p>{t('canvas.benefitsBody')}</p>
                      <div className="lpb-ws__benefits">
                        {BENEFIT_KEYS.map((key) => (
                          <div key={key} className="lpb-ws__benefit">
                            <IhIcon name={SECTION_ICONS.benefits} size={14} />
                            <strong>{t(`canvas.benefits.${key}.title`)}</strong>
                            <span>{t(`canvas.benefits.${key}.body`)}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : null}

                  {section.key === 'roi' ? (
                    <>
                      <div className="lpb-ws__section-kicker">{t('canvas.statsKicker')}</div>
                      <h4>{t('canvas.roiTitle')}</h4>
                      <p>{t('canvas.roiBody')}</p>
                      <div className="lpb-ws__roi-grid">
                        <div className="lpb-ws__roi-card">
                          <strong>12–15%</strong>
                          <span>{t('canvas.roi.irr')}</span>
                        </div>
                        <div className="lpb-ws__roi-card">
                          <strong>1.4×</strong>
                          <span>{t('canvas.roi.equity')}</span>
                        </div>
                        <div className="lpb-ws__roi-card">
                          <strong>36 mo</strong>
                          <span>{t('canvas.roi.hold')}</span>
                        </div>
                      </div>
                    </>
                  ) : null}

                  {section.key === 'timeline' ? (
                    <>
                      <h4>{t('canvas.timelineTitle')}</h4>
                      <p>{t('canvas.timelineBody')}</p>
                      <div className="lpb-ws__timeline">
                        {TIMELINE_KEYS.map((key) => (
                          <div key={key} className="lpb-ws__timeline-item">
                            <span className="lpb-ws__timeline-dot" aria-hidden="true" />
                            <div>
                              <strong>{t(`canvas.timeline.${key}.title`)}</strong>
                              <span>{t(`canvas.timeline.${key}.body`)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : null}

                  {section.key === 'gallery' ? (
                    <>
                      <h4>{t('canvas.galleryTitle')}</h4>
                      <p>{t('canvas.galleryBody')}</p>
                      <div className="lpb-ws__gallery">
                        {coverAsset.galleryDisplayUrls.map((url) => (
                          <img key={url} src={url} alt="" />
                        ))}
                      </div>
                    </>
                  ) : null}

                  {section.key === 'testimonials' ? (
                    <>
                      <h4>{t('canvas.testimonialsTitle')}</h4>
                      <p>{t('canvas.testimonialsBody')}</p>
                      <div className="lpb-ws__testimonials">
                        {TESTIMONIAL_KEYS.map((key) => (
                          <blockquote key={key} className="lpb-ws__testimonial">
                            <div className="lpb-ws__testimonial-stars" aria-hidden="true">
                              ★★★★★
                            </div>
                            <p>{t(`canvas.testimonials.${key}.quote`)}</p>
                            <cite>{t(`canvas.testimonials.${key}.author`)}</cite>
                          </blockquote>
                        ))}
                      </div>
                      {renderTrustExtras()}
                    </>
                  ) : null}

                  {section.key === 'faq' ? (
                    <>
                      <h4>{t('canvas.faqTitle')}</h4>
                      <p>{t('canvas.faqBody')}</p>
                      <div className="lpb-ws__faq">
                        {FAQ_KEYS.map((key, index) => (
                          <div key={key} className="lpb-ws__faq-item">
                            <button
                              type="button"
                              className="lpb-ws__faq-q"
                              aria-expanded={faqOpen === index}
                              onClick={(e) => {
                                e.stopPropagation();
                                setFaqOpen((v) => (v === index ? null : index));
                              }}
                            >
                              <span>{t(`canvas.faq.${key}.q`)}</span>
                              <IhIcon name={faqOpen === index ? 'chevronDown' : 'chevronRight'} size={12} />
                            </button>
                            {faqOpen === index ? (
                              <div className="lpb-ws__faq-a">{t(`canvas.faq.${key}.a`)}</div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </>
                  ) : null}

                  {section.key === 'contact' ? (
                    <>
                      <h4>{t('canvas.formTitle')}</h4>
                      <p>{t('canvas.formBody')}</p>
                      <div className="lpb-ws__form lpb-ws__form--emphasis">
                        {formFields.map((field) => (
                          <div
                            key={field}
                            className={`lpb-ws__form-field${field === 'interest' ? ' lpb-ws__form-field--full' : ''}`}
                          >
                            <label htmlFor={`lpb-field-${field}`}>{t(`forms.fields.${field}`)}</label>
                            {field === 'contactMethod' || field === 'budget' || field === 'timeline' ? (
                              <select id={`lpb-field-${field}`} defaultValue="">
                                <option value="" disabled>
                                  {t('forms.select')}
                                </option>
                                <option value="a">{t(`forms.options.${field}.a`)}</option>
                                <option value="b">{t(`forms.options.${field}.b`)}</option>
                              </select>
                            ) : (
                              <input id={`lpb-field-${field}`} placeholder={t(`forms.fields.${field}`)} />
                            )}
                          </div>
                        ))}
                        <div className="lpb-ws__form-field lpb-ws__form-field--full">
                          <button type="button" className="lpb-ws__hero-cta lpb-ws__hero-cta--primary lpb-ws__hero-cta--xl lpb-ws__form-submit">
                            {ctaPrimary}
                          </button>
                          <span className="lpb-ws__form-reassure">{t('canvas.formReassure')}</span>
                        </div>
                      </div>
                    </>
                  ) : null}

                  {section.key === 'cta' ? (
                    <div className="lpb-ws__cta-band">
                      <span className="lpb-ws__cta-band-kicker">{t('canvas.ctaKicker')}</span>
                      <h4>{t('canvas.ctaTitle')}</h4>
                      <p>{t('canvas.ctaBody')}</p>
                      <div className="lpb-ws__cta-band-actions">
                        <button type="button" className="lpb-ws__hero-cta lpb-ws__hero-cta--primary lpb-ws__hero-cta--xl">
                          {ctaPrimary}
                        </button>
                        <button type="button" className="lpb-ws__hero-cta lpb-ws__hero-cta--ghost">
                          {ctaSecondary}
                        </button>
                      </div>
                      <p className="lpb-ws__cta-band-note">{t('canvas.ctaNote')}</p>
                    </div>
                  ) : null}

                  {section.key === 'footer' ? (
                    <div className="lpb-ws__footer">
                      <strong>INVESTHOME</strong>
                      <span>{t('canvas.footerNote')}</span>
                    </div>
                  ) : null}
                </div>
              );
            })}
        </div>
      </div>
    );
  }


  const leftDrawerContent = (
    <LpbLeftRailDrawer
      id={leftRailId}
      templates={LPB_TEMPLATES}
      onInsertComponent={(key) => showToast(t('rails.components.toasts.inserted', { name: t(`rails.components.items.${key}`) }))}
      onApplyTemplate={(type) => {
        const map: Record<string, AiActionKey> = {
          investor: 'investorLanding',
          webinar: 'webinar',
          projectLaunch: 'projectLaunch',
          consultation: 'consultation',
          brochure: 'brochure',
          earlyAccess: 'earlyAccess',
        };
        handleGenerate(map[type] ?? 'investorLanding');
      }}
      media={coverAsset.media}
      linkedProjectId={docApi.constructionProjectId}
      coverAssetId={coverAsset.coverImage?.asset_id ?? null}
      onSelectMediaAsset={(ref) => {
        coverAsset.setCoverImage(ref);
        markDirty();
        showToast(t('toasts.assetSelected', { name: ref.alt || ref.asset_id || 'asset' }));
      }}
      onToast={showToast}
    />
  );

  const rightDrawerContent = (
    <LpbRightRailDrawer
      id={rightRailId}
      brief={brief}
      setBrief={setBrief}
      pages={pages}
      selectedPageId={selectedPageId}
      scores={scores}
      pageName={pageName}
      setPageName={setPageName}
      pageUrl={pageUrl}
      setPageUrl={setPageUrl}
      contentWidth={contentWidth}
      setContentWidth={setContentWidth}
      showHeader={showHeader}
      setShowHeader={setShowHeader}
      showFooter={showFooter}
      setShowFooter={setShowFooter}
      seoTitle={seoTitle}
      setSeoTitle={setSeoTitle}
      seoDescription={seoDescription}
      setSeoDescription={setSeoDescription}
      seoKeywords={seoKeywords}
      setSeoKeywords={setSeoKeywords}
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
      <div className="lpb-ws__panel lpb-ws__left" aria-label={t('left.aria')} data-testid="lpb-left">
        <LpbLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as LpbLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="lpb-ws__panel lpb-ws__right" aria-label={t('right.aria')} data-testid="lpb-right">
        <LpbLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as LpbRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="lpb-workspace-loading">
        <div className="lpb-ws">
          <div className="lpb-ws__skeleton lpb-ws__skeleton--header" />
          <div className="lpb-ws__skeleton lpb-ws__skeleton--toolbar" />
          <div className="lpb-ws__layout">
            <div className="lpb-ws__skeleton lpb-ws__skeleton--panel" />
            <div className="lpb-ws__skeleton lpb-ws__skeleton--panel lpb-ws__skeleton--center" />
            <div className="lpb-ws__skeleton lpb-ws__skeleton--panel" />
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard" data-testid="lpb-workspace-page">
      <div
        className="lpb-ws"
        data-testid="lpb-workspace"
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
      >
        <header className="lpb-ws__header cs-page-header">
          <div className="lpb-ws__header-copy cs-page-header__copy">
            <Link href={LPB_HOME as Route} className="lpb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="lpb-ws__breadcrumb">
                <li>
                  <Link href={LPB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="lpb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="lpb-ws__breadcrumb-current" aria-current="page">
                  {tTools('landingPages.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="target" size={20} />
              {tTools('landingPages.title')}
            </h1>
            <p className="lpb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="lpb-ws__header-actions cs-page-header__actions">
            <div className="lpb-ws__save-status" data-testid="lpb-save-status">
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <span className="lpb-ws__saved-ago">{lastSavedLabel}</span>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void persistNow(true)}
              data-testid="lpb-save"
              disabled={docApi.saveStatus === 'saving' || docApi.loadStatus !== 'ready'}
            >
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="lpb-preview"
              onClick={() => {
                focus.setMode('preview');
                setCampaignStatus('preview');
                showToast(t('toasts.preview'));
              }}
            >
              {t('preview')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="lpb-share"
              onClick={() => showToast(t('toasts.shared'))}
            >
              {t('share')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="lpb-download-header"
              onClick={() => showToast(t('toasts.downloaded'))}
            >
              <IhIcon name="inbox" size={12} />
              {t('download')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="lpb-create-ai"
              disabled={generating}
              onClick={() => handleGenerate('investorLanding')}
            >
              <IhIcon name="sparkles" size={12} />
              {generating ? t('generating') : t('createWithAi')}
            </Button>
          </div>
        </header>

        <div className="lpb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="lpb-ws__toolbar-left">
            <div className="lpb-ws__project">
              <Select
                id="lpb-project"
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
            <div className="lpb-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="lpb-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="lpb-undo"
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="lpb-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="lpb-redo"
                onClick={() => showToast(t('toasts.redo'))}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
            </div>
          </div>
          <div className="lpb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <LpbZoomToolbar
              engine={ftv}
              canvasLocked={canvasLocked}
              onToggleLock={() => setCanvasLocked((v) => !v)}
              isFullscreen={focus.isFullscreen}
              onToggleFullscreen={focus.toggleFullscreen}
              onPublish={() => setLaunchOpen(true)}
            />
          </div>
        </div>

        <div
          className={`lpb-ws__ai-status${generating || aiStatus !== 'idle' ? ' is-live' : ''}`}
          role="status"
          aria-live="polite"
          data-testid="lpb-ai-status"
        >
          <span className="lpb-ws__ai-status-dot" aria-hidden="true" />
          <span>{aiStatus === 'idle' ? t('aiStatus.idle') : t(`aiStatus.${aiStatus}`)}</span>
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="lpb-ws__layout"
          leftRail={lpbLeftRail}
          rightRail={lpbRightRail}
          onLeftRailSelect={(id) => {
            if ((LPB_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as LpbLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((LPB_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as LpbRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section className="lpb-ws__panel lpb-ws__center" aria-label={t('canvas.aria')} data-testid="lpb-center">
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="lpb-canvas-stage"
                toolbar={
                  <div className="lpb-ws__center-head">
                    <div className="lpb-ws__device-toggle" role="group" aria-label={t('canvas.devicesAria')}>
                      {DEVICE_TOGGLE.map((mode) => (
                        <button
                          key={mode}
                          type="button"
                          className={`lpb-ws__device-btn${device === mode ? ' is-active' : ''}`}
                          aria-pressed={device === mode}
                          aria-label={t(`canvas.devices.${mode}`)}
                          data-testid={`lpb-device-${mode}`}
                          title={t(`canvas.devices.${mode}`)}
                          onClick={() => setDevice(mode)}
                        >
                          <span className={`lpb-ws__device-glyph lpb-ws__device-glyph--${mode}`} aria-hidden="true" />
                        </button>
                      ))}
                    </div>
                  </div>
                }
                tray={{
                  label: t('canvas.stripTitle'),
                  count: pages.length,
                  testId: 'lpb-page-strip',
                  handleTestId: 'lpb-tray-handle',
                  content: (
                    <div className="lpb-ws__filmstrip" data-testid="lpb-filmstrip">
                      <button
                        type="button"
                        className="lpb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripPrev')}
                        data-testid="lpb-filmstrip-prev"
                        onClick={() => scrollFilmstrip(-1)}
                      >
                        <IhIcon name="chevronLeft" size={14} />
                      </button>
                      <div className="lpb-ws__page-row" ref={filmstripRef} data-testid="lpb-page-row">
                        {pages.map((page) => (
                          <button
                            key={page.id}
                            type="button"
                            draggable
                            className={`lpb-ws__page-card${selectedPageId === page.id ? ' is-selected' : ''}${dragPageId === page.id ? ' is-dragging' : ''}`}
                            onClick={() => setSelectedPageId(page.id)}
                            onDragStart={() => setDragPageId(page.id)}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={() => {
                              if (!dragPageId) return;
                              setPages((prev) => reorderPages(prev, dragPageId, page.id));
                              setDragPageId(null);
                              markDirty();
                            }}
                            onDragEnd={() => setDragPageId(null)}
                            data-testid={`lpb-page-${page.id}`}
                          >
                            <div className="lpb-ws__page-thumb">
                              <img src={page.thumbUrl} alt="" />
                            </div>
                            <strong>{t(`pages.${page.kind}`)}</strong>
                          </button>
                        ))}
                        <button
                          type="button"
                          className="lpb-ws__page-card lpb-ws__page-card--new"
                          data-testid="lpb-new-page"
                          onClick={addPage}
                        >
                          <div className="lpb-ws__page-thumb lpb-ws__page-thumb--new">
                            <IhIcon name="plus" size={18} />
                          </div>
                          <strong>{t('canvas.newPage')}</strong>
                        </button>
                      </div>
                      <button
                        type="button"
                        className="lpb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripNext')}
                        data-testid="lpb-filmstrip-next"
                        onClick={() => scrollFilmstrip(1)}
                      >
                        <IhIcon name="chevronRight" size={14} />
                      </button>
                    </div>
                  ),
                }}
                dock={{
                  testId: 'lpb-scene-actions',
                  className: 'lpb-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="lpb-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      primary={{
                        label: t('bottomBar.actions.addSection'),
                        icon: 'plus',
                        onClick: () => handleBottomAction('addSection'),
                        testId: 'lpb-action-addSection',
                      }}
                      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addSection').map((action) => ({
                        key: action.key,
                        icon: action.icon,
                        label: t(`bottomBar.actions.${action.key}`),
                        onClick: () => handleBottomAction(action.key),
                        testId: `lpb-action-${action.key}`,
                      }))}
                    />
                  ),
                }}
              >
                <div className="lpb-ws__canvas-stage" data-testid="lpb-preview-shell">
                  <FocusFitStage engine={ftv} artboardTestId="lpb-live-preview-frame">
                    {renderPreview()}
                  </FocusFitStage>
                </div>
              </FocusCanvasLayout>
            </section>
          }
          right={rightDrawer}
        />
      </div>

      {launchOpen ? (
        <>
          <button
            type="button"
            className="lpb-ws__drawer-backdrop"
            aria-label={t('launch.close')}
            onClick={() => setLaunchOpen(false)}
          />
          <aside className="lpb-ws__drawer" data-testid="lpb-launch-drawer" aria-label={t('launch.title')}>
            <div className="lpb-ws__drawer-head">
              <h2>{t('launch.title')}</h2>
              <button type="button" className="lpb-ws__icon-btn" onClick={() => setLaunchOpen(false)}>
                ✕
              </button>
            </div>
            <div className="lpb-ws__drawer-body">
              <p className="lpb-ws__subtitle cs-page-header__subtitle">{t('launch.subtitle')}</p>
              <div className="lpb-ws__launch-checks">
                {LAUNCH_CHECKS.map((check) => (
                  <label key={check.key} className="lpb-ws__launch-check">
                    <span>
                      <IhIcon name={check.icon} size={12} /> {t(`launch.checks.${check.key}`)}
                    </span>
                    <input
                      type="checkbox"
                      checked={!!launchChecks[check.key]}
                      onChange={(e) =>
                        setLaunchChecks((prev) => ({ ...prev, [check.key]: e.target.checked }))
                      }
                    />
                  </label>
                ))}
              </div>
              <StatusChip tone={allLaunchPass ? 'success' : 'warning'}>
                {allLaunchPass ? t('launch.ready') : t('launch.pending')}
              </StatusChip>
            </div>
            <div className="lpb-ws__drawer-foot">
              <Button variant="secondary" size="sm" onClick={() => setLaunchOpen(false)}>
                {t('launch.close')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!allLaunchPass}
                onClick={confirmLaunch}
                data-testid="lpb-confirm-launch"
              >
                {t('launch.confirm')}
              </Button>
            </div>
          </aside>
        </>
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
            markDirty();
            showToast(t('toasts.assetSelected', { name: ref.alt || ref.asset_id || 'asset' }));
          }}
          testId="lpb-media-picker-dialog"
        />
      ) : null}

      {toast ? (
        <div className="lpb-ws__toast" role="status">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
