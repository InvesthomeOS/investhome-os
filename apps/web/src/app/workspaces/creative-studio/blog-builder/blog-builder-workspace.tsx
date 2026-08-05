'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  BB_HOME,
  BB_LEFT_RAIL_ICONS,
  BB_LEFT_RAIL_IDS,
  BB_PROJECTS,
  BB_RIGHT_RAIL_ICONS,
  BB_RIGHT_RAIL_IDS,
  BOTTOM_ACTIONS,
  DEFAULT_PAGES,
  DEFAULT_SECTIONS,
  DEFAULT_SEO,
  DEFAULT_TAGS,
  DEVICE_CONTENT,
  DEVICE_TOGGLE,
  FAQ_KEYS,
  FEATURE_GRID_KEYS,
  INLINE_IMAGE_URL,
  getProject,
  reorderPages,
  type BbLeftRailId,
  type BbPage,
  type BbRightRailId,
  type BbSection,
  type BottomActionKey,
  type DevicePreview,
  type ProjectId,
  type PublishStatus,
  type SectionTrayActionKey,
} from './blog-builder-model';

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
  BbLeftRailDrawer,
  BbLocalRail,
  BbRightRailDrawer,
  BbZoomToolbar,
} from './blog-builder-rail-drawers';
import {
  BbSectionOverflowMenu,
  type BbOverflowMenuItem,
} from './bb-section-overflow-menu';

import './blog-builder.css';

export function BlogBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.blogBuilder');
  const tTools = useTranslations('creativeStudio.ds.tools');

  const [hydrated, setHydrated] = useState(false);
  const [projectId, setProjectId] = useState<ProjectId>('temple');
  const [device, setDevice] = useState<DevicePreview>('desktop');
  const [publishStatus, setPublishStatus] = useState<PublishStatus>('published');
  const [saved, setSaved] = useState(true);
  const [lastSavedLabel, setLastSavedLabel] = useState('');
  const [sections, setSections] = useState<BbSection[]>(DEFAULT_SECTIONS);
  const [selectedSectionId, setSelectedSectionId] = useState('s-title');
  const [pages, setPages] = useState<BbPage[]>(DEFAULT_PAGES);
  const [selectedPageId, setSelectedPageId] = useState('pg-detail');
  const [dragPageId, setDragPageId] = useState<string | null>(null);
  const [floatingMoreId, setFloatingMoreId] = useState<string | null>(null);
  const [leftRailId, setLeftRailId] = useState<BbLeftRailId>('components');
  const [rightRailId, setRightRailId] = useState<BbRightRailId>('post');
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [postTitle, setPostTitle] = useState('');
  const [postSlug, setPostSlug] = useState('washington-dc-yatirim-rehberi');
  const [postSummary, setPostSummary] = useState('');
  const [category, setCategory] = useState('Investment Guide');
  const [tags, setTags] = useState<string[]>([...DEFAULT_TAGS]);
  const [featured, setFeatured] = useState(true);
  const [seoTitle, setSeoTitle] = useState('');
  const [seoDescription, setSeoDescription] = useState('');
  const [seoKeywords, setSeoKeywords] = useState('dc real estate, investment, the temple');
  const [scores] = useState(DEFAULT_SEO);
  const [faqOpen, setFaqOpen] = useState<number | null>(0);
  const [toast, setToast] = useState<string | null>(null);
  const [publishOpen, setPublishOpen] = useState(false);

  const focus = useCreativeStudioFocusMode({ storageKey: 'blog-builder' });
  const filmstripRef = useRef<HTMLDivElement | null>(null);
  const floatingMoreRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const project = useMemo(() => getProject(projectId), [projectId]);
  const deviceSize = DEVICE_CONTENT[device];
  const ftv = useFitToViewEngine({
    contentWidth: deviceSize.w,
    contentHeight: deviceSize.h,
    enabled: true,
    contentKey: `blog-${device}-${selectedPageId}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}`,
    canvasType: 'document',
  });

  const bbLeftRail: FocusRailItem[] = useMemo(
    () =>
      BB_LEFT_RAIL_IDS.map((id) => ({
        id,
        icon: BB_LEFT_RAIL_ICONS[id],
        labelKey: 'brief',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const bbRightRail: FocusRailItem[] = useMemo(
    () =>
      BB_RIGHT_RAIL_IDS.map((id) => ({
        id,
        icon: BB_RIGHT_RAIL_ICONS[id],
        labelKey: 'export',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const localLeftItems = useMemo(
    () => bbLeftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [bbLeftRail],
  );
  const localRightItems = useMemo(
    () => bbRightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [bbRightRail],
  );

  useEffect(() => {
    setHydrated(true);
    setPostTitle(t('canvas.heroTitle'));
    setPostSummary(t('canvas.lead'));
    setSeoTitle(t('seoAssistant.metaTitleValue'));
    setSeoDescription(t('seoAssistant.metaDescriptionValue'));
    setLastSavedLabel(t('savedJustNow'));
    // intentionally once on mount for demo content bootstrap
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (focus.isFocus || focus.isFullscreen) {
      if (ftv.autoFit) ftv.fitToView();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.isFocus, focus.isFullscreen, device]);

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
    return () => document.removeEventListener('keydown', onKey, true);
  }, [floatingMoreId]);

  function markDirty() {
    setSaved(false);
  }

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  function persistNow(announce = false) {
    setSaved(true);
    setLastSavedLabel(t('savedJustNow'));
    if (announce) showToast(t('toasts.saved'));
  }

  function scrollFilmstrip(dir: -1 | 1) {
    filmstripRef.current?.scrollBy({ left: dir * 180, behavior: 'smooth' });
  }

  function addPage() {
    const id = `pg-${Date.now()}`;
    setPages((prev) => [
      ...prev,
      {
        id,
        kind: 'custom',
        thumbUrl:
          'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=400&h=260&q=80',
      },
    ]);
    setSelectedPageId(id);
    markDirty();
    showToast(t('toasts.pageAdded'));
  }

  function selectSection(section: BbSection) {
    setSelectedSectionId(section.id);
    setFloatingMoreId(null);
  }

  function handleSectionAction(action: SectionTrayActionKey, sectionId = selectedSectionId) {
    const section = sections.find((s) => s.id === sectionId);
    if (!section) return;
    setFloatingMoreId(null);

    if (action === 'edit') {
      setRightRailId('post');
      showToast(t('toasts.sectionEdit', { name: section.label }));
      return;
    }
    if (action === 'settings') {
      setRightRailId('style');
      showToast(t('toasts.sectionSettings'));
      return;
    }
    if (action === 'duplicate') {
      const copy: BbSection = {
        id: `s-${Date.now()}`,
        key: section.key,
        label: `${section.label} copy`,
      };
      setSections((prev) => {
        const idx = prev.findIndex((s) => s.id === sectionId);
        const next = [...prev];
        next.splice(idx + 1, 0, copy);
        return next;
      });
      setSelectedSectionId(copy.id);
      markDirty();
      showToast(t('toasts.sectionDuplicated'));
      return;
    }
    if (action === 'delete') {
      if (sections.length <= 1) {
        showToast(t('toasts.cannotDeleteLastSection'));
        return;
      }
      setSections((prev) => prev.filter((s) => s.id !== sectionId));
      setSelectedSectionId((prev) => (prev === sectionId ? sections[0]!.id : prev));
      markDirty();
      showToast(t('toasts.sectionDeleted'));
      return;
    }
    if (action === 'moveUp' || action === 'moveDown') {
      setSections((prev) => {
        const idx = prev.findIndex((s) => s.id === sectionId);
        if (idx < 0) return prev;
        const target = action === 'moveUp' ? idx - 1 : idx + 1;
        if (target < 0 || target >= prev.length) return prev;
        const next = [...prev];
        const [moved] = next.splice(idx, 1);
        next.splice(target, 0, moved!);
        return next;
      });
      markDirty();
    }
  }

  function handleBottomAction(key: BottomActionKey) {
    if (key === 'addSection') {
      const id = `s-${Date.now()}`;
      const section: BbSection = { id, key: 'body', label: 'Section' };
      setSections((prev) => [...prev, section]);
      setSelectedSectionId(id);
      markDirty();
    }
    showToast(t(`bottomBar.toasts.${key}`));
  }

  function confirmPublish() {
    setPublishStatus('published');
    setPublishOpen(false);
    persistNow();
    showToast(t('toasts.published'));
  }

  function renderSectionToolbar(section: BbSection) {
    const moreOpen = floatingMoreId === section.id;
    const idx = sections.findIndex((s) => s.id === section.id);
    const moreItems: BbOverflowMenuItem[] = [
      {
        key: 'moveUp',
        label: t('floating.moveUp'),
        disabled: idx <= 0,
        onSelect: () => handleSectionAction('moveUp', section.id),
      },
      {
        key: 'moveDown',
        label: t('floating.moveDown'),
        disabled: idx >= sections.length - 1,
        onSelect: () => handleSectionAction('moveDown', section.id),
      },
      {
        key: 'duplicate',
        label: t('floating.duplicate'),
        onSelect: () => handleSectionAction('duplicate', section.id),
      },
      {
        key: 'delete',
        label: t('floating.delete'),
        destructive: true,
        onSelect: () => handleSectionAction('delete', section.id),
      },
    ];

    return (
      <div className="bb-ws__section-toolbar" role="toolbar" aria-label={t('floating.more')}>
        <button
          type="button"
          className="bb-ws__section-toolbar-btn"
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
          className="bb-ws__section-toolbar-btn"
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
          className="bb-ws__section-toolbar-btn"
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
          className="bb-ws__section-toolbar-btn"
          title={t('floating.sectionSettings')}
          aria-label={t('floating.sectionSettings')}
          onClick={(e) => {
            e.stopPropagation();
            selectSection(section);
            handleSectionAction('settings', section.id);
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
          className={`bb-ws__section-toolbar-btn${moreOpen ? ' is-active' : ''}`}
          title={t('floating.more')}
          aria-label={t('floating.more')}
          aria-expanded={moreOpen}
          aria-haspopup="menu"
          data-testid={`bb-section-more-${section.id}`}
          onClick={(e) => {
            e.stopPropagation();
            selectSection(section);
            setFloatingMoreId((prev) => (prev === section.id ? null : section.id));
          }}
        >
          ⋯
        </button>
        <BbSectionOverflowMenu
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
  }

  function renderPreview() {
    return (
      <div className="bb-ws__doc" data-testid="bb-live-preview" data-device={device}>
        {sections.map((section) => {
          const selected = selectedSectionId === section.id;
          const toolbar = renderSectionToolbar(section);

          if (section.key === 'header') {
            return (
              <div
                key={section.id}
                className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
                onClick={() => selectSection(section)}
                role="presentation"
              >
                {toolbar}
                <header className="bb-ws__site-header">
                  <strong>INVESTHOME</strong>
                  <nav aria-label={t('canvas.siteNavAria')}>
                    <span>{t('canvas.nav.blog')}</span>
                    <span>{t('canvas.nav.projects')}</span>
                    <span>{t('canvas.nav.about')}</span>
                  </nav>
                  <button type="button" className="bb-ws__site-search" aria-label={t('canvas.search')}>
                    <IhIcon name="search" size={12} />
                  </button>
                </header>
              </div>
            );
          }

          if (section.key === 'meta') {
            return (
              <div
                key={section.id}
                className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
                onClick={() => selectSection(section)}
                role="presentation"
              >
                {toolbar}
                <div className="bb-ws__author-meta">
                  <div className="bb-ws__author">
                    <span className="bb-ws__author-avatar" aria-hidden="true">
                      IH
                    </span>
                    <div>
                      <strong>{t('canvas.author')}</strong>
                      <span>
                        {t('canvas.publishedDate')} · {t('canvas.readingTime', { minutes: '8' })}
                      </span>
                    </div>
                  </div>
                  <div className="bb-ws__share" aria-label={t('canvas.shareAria')}>
                    <button type="button" className="bb-ws__share-btn" aria-label="LinkedIn">
                      in
                    </button>
                    <button type="button" className="bb-ws__share-btn" aria-label="X">
                      𝕏
                    </button>
                    <button type="button" className="bb-ws__share-btn" aria-label="Copy link">
                      ↗
                    </button>
                  </div>
                </div>
              </div>
            );
          }

          if (section.key === 'title') {
            return (
              <div
                key={section.id}
                className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
                onClick={() => selectSection(section)}
                role="presentation"
              >
                {toolbar}
                <div className="bb-ws__doc-title-block">
                  <span className="bb-ws__hero-badge">{t('canvas.heroBadge')}</span>
                  <h2
                    contentEditable
                    suppressContentEditableWarning
                    onBlur={(e) => {
                      setPostTitle(e.currentTarget.textContent || postTitle);
                      markDirty();
                    }}
                  >
                    {postTitle || t('canvas.heroTitle')}
                  </h2>
                </div>
              </div>
            );
          }

          if (section.key === 'lead') {
            return (
              <div
                key={section.id}
                className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
                onClick={() => selectSection(section)}
                role="presentation"
              >
                {toolbar}
                <p className="bb-ws__doc-lead">{postSummary || t('canvas.lead')}</p>
              </div>
            );
          }

          if (section.key === 'cover') {
            return (
              <div
                key={section.id}
                className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
                onClick={() => selectSection(section)}
                role="presentation"
              >
                {toolbar}
                <figure className="bb-ws__doc-cover">
                  <img src={project.coverUrl} alt={t('canvas.heroAlt')} />
                </figure>
              </div>
            );
          }

          if (section.key === 'quote') {
            return (
              <div
                key={section.id}
                className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
                onClick={() => selectSection(section)}
                role="presentation"
              >
                {toolbar}
                <blockquote className="bb-ws__quote">
                  <p>{t('canvas.quote')}</p>
                  <cite>{t('canvas.quoteCite')}</cite>
                </blockquote>
              </div>
            );
          }

          if (section.key === 'cta') {
            return (
              <div
                key={section.id}
                className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
                onClick={() => selectSection(section)}
                role="presentation"
              >
                {toolbar}
                <div className="bb-ws__cta-block">
                  <div>
                    <strong>{t('canvas.ctaTitle')}</strong>
                    <p>{t('canvas.ctaBody')}</p>
                  </div>
                  <Button variant="primary" data-testid="bb-cta-primary">
                    {t('canvas.ctaButton')}
                  </Button>
                </div>
              </div>
            );
          }

          if (section.key === 'faq') {
            return (
              <div
                key={section.id}
                className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
                onClick={() => selectSection(section)}
                role="presentation"
              >
                {toolbar}
                <div className="bb-ws__prose">
                  <h3>{t('canvas.sections.faq')}</h3>
                  <div className="bb-ws__faq">
                    {FAQ_KEYS.map((key, index) => (
                      <div key={key} className={`bb-ws__faq-item${faqOpen === index ? ' is-open' : ''}`}>
                        <button
                          type="button"
                          className="bb-ws__faq-trigger"
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
                          <p className="bb-ws__faq-answer">{t(`canvas.faq.${key}.a`)}</p>
                        ) : null}
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
              className={`bb-ws__doc-section bb-ws__editable${selected ? ' is-selected' : ''}`}
              onClick={() => selectSection(section)}
              role="presentation"
            >
              {toolbar}
              <div className="bb-ws__prose">
                <h3>{t('canvas.sections.whyDc')}</h3>
                <p>{t('canvas.body.whyDc')}</p>
                <div className="bb-ws__callout">
                  <span className="bb-ws__callout-label">{t('canvas.calloutLabel')}</span>
                  <p>{t('canvas.calloutBody')}</p>
                </div>
                <div className="bb-ws__feature-grid">
                  {FEATURE_GRID_KEYS.map((key) => (
                    <div key={key} className="bb-ws__feature-card">
                      <IhIcon name="trendingUp" size={14} />
                      <strong>{t(`canvas.features.${key}.title`)}</strong>
                      <span>{t(`canvas.features.${key}.body`)}</span>
                    </div>
                  ))}
                </div>
                <h3>{t('canvas.sections.neighborhoods')}</h3>
                <p>{t('canvas.body.neighborhoods')}</p>
                <figure className="bb-ws__inline-media">
                  <img src={INLINE_IMAGE_URL} alt={t('canvas.inlineAlt')} />
                  <figcaption>{t('canvas.inlineCaption')}</figcaption>
                </figure>
                <h3>{t('canvas.sections.temple')}</h3>
                <p>{t('canvas.body.temple')}</p>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  const leftDrawerContent = (
    <BbLeftRailDrawer
      id={leftRailId}
      onInsertComponent={(key) =>
        showToast(t('rails.components.toasts.inserted', { name: t(`rails.components.items.${key}`) }))
      }
      onApplyTemplate={() => {
        markDirty();
        showToast(t('toasts.templateApplied'));
      }}
      onToast={showToast}
    />
  );

  const rightDrawerContent = (
    <BbRightRailDrawer
      id={rightRailId}
      onSelectTab={setRightRailId}
      postTitle={postTitle}
      setPostTitle={setPostTitle}
      postSlug={postSlug}
      setPostSlug={setPostSlug}
      postSummary={postSummary}
      setPostSummary={setPostSummary}
      category={category}
      setCategory={setCategory}
      tags={tags}
      setTags={setTags}
      featured={featured}
      setFeatured={setFeatured}
      coverUrl={project.coverUrl}
      publishStatus={publishStatus}
      seoTitle={seoTitle}
      setSeoTitle={setSeoTitle}
      seoDescription={seoDescription}
      setSeoDescription={setSeoDescription}
      seoKeywords={seoKeywords}
      setSeoKeywords={setSeoKeywords}
      scores={scores}
      markDirty={markDirty}
      onToast={showToast}
    />
  );

  const leftDrawer =
    focus.isFocus || focus.isFullscreen ? (
      leftDrawerContent
    ) : (
      <div className="bb-ws__panel bb-ws__left" aria-label={t('left.aria')} data-testid="bb-left">
        <BbLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as BbLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="bb-ws__panel bb-ws__right" aria-label={t('right.aria')} data-testid="bb-right">
        <BbLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as BbRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="bb-workspace-loading">
        <div className="bb-ws">
          <div className="bb-ws__skeleton bb-ws__skeleton--header" />
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard" data-testid="bb-workspace-page">
      <div
        className="bb-ws"
        data-testid="bb-workspace"
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
      >
        <header className="bb-ws__header cs-page-header">
          <div className="bb-ws__header-copy cs-page-header__copy">
            <Link href={BB_HOME as Route} className="bb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="bb-ws__breadcrumb">
                <li>
                  <Link href={BB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="bb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="bb-ws__breadcrumb-current" aria-current="page">
                  {tTools('blogStudio.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="documents" size={20} />
              {tTools('blogStudio.title')}
            </h1>
            <p className="bb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="bb-ws__header-actions cs-page-header__actions">
            <div className="bb-ws__save-status" data-testid="bb-save-status">
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <span className="bb-ws__saved-ago">{lastSavedLabel}</span>
            </div>
            <Button variant="secondary" size="sm" onClick={() => persistNow(true)} data-testid="bb-save">
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="bb-preview"
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
              data-testid="bb-share"
              onClick={() => showToast(t('toasts.shared'))}
            >
              {t('share')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="bb-download-header"
              onClick={() => showToast(t('toasts.downloaded'))}
            >
              <IhIcon name="inbox" size={12} />
              {t('download')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="bb-publish"
              onClick={() => setPublishOpen(true)}
            >
              {t('publish')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
          </div>
        </header>

        <div className="bb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="bb-ws__toolbar-left">
            <div className="bb-ws__project">
              <Select
                id="bb-project"
                label={t('fields.project')}
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value as ProjectId);
                  markDirty();
                }}
              >
                {BB_PROJECTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="bb-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="bb-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="bb-undo"
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="bb-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="bb-redo"
                onClick={() => showToast(t('toasts.redo'))}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
            </div>
          </div>
          <div className="bb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <BbZoomToolbar
              engine={ftv}
              canvasLocked={canvasLocked}
              onToggleLock={() => setCanvasLocked((v) => !v)}
              isFullscreen={focus.isFullscreen}
              onToggleFullscreen={focus.toggleFullscreen}
            />
          </div>
        </div>

        <div className="bb-ws__ai-status" role="status" aria-live="polite" data-testid="bb-info-banner">
          <span className="bb-ws__ai-status-dot" aria-hidden="true" />
          <span>{t('aiStatus.idle')}</span>
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="bb-ws__layout"
          leftRail={bbLeftRail}
          rightRail={bbRightRail}
          onLeftRailSelect={(id) => {
            if ((BB_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as BbLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((BB_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as BbRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section className="bb-ws__panel bb-ws__center" aria-label={t('canvas.aria')} data-testid="bb-center">
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="bb-canvas-stage"
                toolbar={
                  <div className="bb-ws__center-head">
                    <div className="bb-ws__device-toggle" role="group" aria-label={t('canvas.devicesAria')}>
                      {DEVICE_TOGGLE.map((mode) => (
                        <button
                          key={mode}
                          type="button"
                          className={`bb-ws__device-btn${device === mode ? ' is-active' : ''}`}
                          aria-pressed={device === mode}
                          aria-label={t(`canvas.devices.${mode}`)}
                          data-testid={`bb-device-${mode}`}
                          title={t(`canvas.devices.${mode}`)}
                          onClick={() => setDevice(mode)}
                        >
                          <span className={`bb-ws__device-glyph bb-ws__device-glyph--${mode}`} aria-hidden="true" />
                        </button>
                      ))}
                    </div>
                  </div>
                }
                tray={{
                  label: t('canvas.stripTitle'),
                  count: pages.length,
                  testId: 'bb-page-strip',
                  handleTestId: 'bb-tray-handle',
                  content: (
                    <div className="bb-ws__filmstrip" data-testid="bb-filmstrip">
                      <button
                        type="button"
                        className="bb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripPrev')}
                        data-testid="bb-filmstrip-prev"
                        onClick={() => scrollFilmstrip(-1)}
                      >
                        <IhIcon name="chevronLeft" size={14} />
                      </button>
                      <div className="bb-ws__page-row" ref={filmstripRef} data-testid="bb-page-row">
                        {pages.map((page) => (
                          <button
                            key={page.id}
                            type="button"
                            draggable
                            className={`bb-ws__page-card${selectedPageId === page.id ? ' is-selected' : ''}${dragPageId === page.id ? ' is-dragging' : ''}`}
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
                            data-testid={`bb-page-${page.id}`}
                          >
                            <div className="bb-ws__page-thumb">
                              <img src={page.thumbUrl} alt="" />
                            </div>
                            <strong>{t(`pages.${page.kind}`)}</strong>
                          </button>
                        ))}
                        <button
                          type="button"
                          className="bb-ws__page-card bb-ws__page-card--new"
                          data-testid="bb-new-page"
                          onClick={addPage}
                        >
                          <div className="bb-ws__page-thumb bb-ws__page-thumb--new">
                            <IhIcon name="plus" size={18} />
                          </div>
                          <strong>{t('canvas.newPage')}</strong>
                        </button>
                      </div>
                      <button
                        type="button"
                        className="bb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripNext')}
                        data-testid="bb-filmstrip-next"
                        onClick={() => scrollFilmstrip(1)}
                      >
                        <IhIcon name="chevronRight" size={14} />
                      </button>
                    </div>
                  ),
                }}
                dock={{
                  testId: 'bb-scene-actions',
                  className: 'bb-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="bb-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      primary={{
                        label: t('bottomBar.actions.addSection'),
                        icon: 'plus',
                        onClick: () => handleBottomAction('addSection'),
                        testId: 'bb-action-addSection',
                      }}
                      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addSection').map((action) => ({
                        key: action.key,
                        icon: action.icon,
                        label: t(`bottomBar.actions.${action.key}`),
                        onClick: () => handleBottomAction(action.key),
                        testId: `bb-action-${action.key}`,
                      }))}
                    />
                  ),
                }}
              >
                <div className="bb-ws__canvas-stage" data-testid="bb-preview-shell">
                  <FocusFitStage engine={ftv} artboardTestId="bb-ftv-artboard">
                    {renderPreview()}
                  </FocusFitStage>
                </div>
              </FocusCanvasLayout>
            </section>
          }
          right={rightDrawer}
        />
      </div>

      {publishOpen ? (
        <div className="bb-ws__modal" role="dialog" aria-modal="true" data-testid="bb-publish-modal">
          <div className="bb-ws__modal-card">
            <div className="bb-ws__modal-head">
              <div>
                <h2>{t('publishModal.title')}</h2>
                <p>{t('publishModal.subtitle')}</p>
              </div>
              <button
                type="button"
                className="bb-ws__icon-btn"
                aria-label={t('publishModal.close')}
                onClick={() => setPublishOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="bb-ws__modal-actions">
              <Button variant="secondary" size="sm" onClick={() => setPublishOpen(false)}>
                {t('publishModal.close')}
              </Button>
              <Button variant="primary" size="sm" onClick={confirmPublish}>
                {t('publishModal.confirm')}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {toast ? (
        <div className="bb-ws__toast" role="status">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
