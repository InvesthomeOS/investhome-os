'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  BOTTOM_ACTIONS,
  DEFAULT_SECTIONS,
  DEVICE_CONTENT,
  DEVICE_TOGGLE,
  EB_HOME,
  EB_LEFT_RAIL_ICONS,
  EB_LEFT_RAIL_IDS,
  EB_PROJECTS,
  EB_RIGHT_RAIL_ICONS,
  EB_RIGHT_RAIL_IDS,
  FEATURE_GRID_KEYS,
  GALLERY_IMAGE_URLS,
  RELATED_POST_KEYS,
  SOCIAL_LINK_KEYS,
  getProject,
  reorderSections,
  type BottomActionKey,
  type DevicePreview,
  type EbLeftRailId,
  type EbRightRailId,
  type EbSection,
  type ProjectId,
  type PublishStatus,
  type SectionTrayActionKey,
} from './email-builder-model';

import { CsBottomActionToolbar, CsMediaPickerDialog } from '../_components';
import { useBuilderCoverAsset } from '../_components/use-builder-cover-asset';
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
  EbLeftRailDrawer,
  EbLocalRail,
  EbRightRailDrawer,
  EbZoomToolbar,
} from './email-builder-rail-drawers';
import {
  EbSectionOverflowMenu,
  type EbOverflowMenuItem,
} from './eb-section-overflow-menu';

import './email-builder.css';

export function EmailBuilderWorkspace() {
  const t = useTranslations('creativeStudio.ds.emailBuilder');
  const tTools = useTranslations('creativeStudio.ds.tools');

  const [hydrated, setHydrated] = useState(false);
  const [projectId, setProjectId] = useState<ProjectId>('temple');
  const [device, setDevice] = useState<DevicePreview>('desktop');
  const [publishStatus, setPublishStatus] = useState<PublishStatus>('draft');
  const [saved, setSaved] = useState(true);
  const [lastSavedLabel, setLastSavedLabel] = useState('');
  const [sections, setSections] = useState<EbSection[]>(DEFAULT_SECTIONS);
  const [selectedSectionId, setSelectedSectionId] = useState('s-hero');
  const [dragSectionId, setDragSectionId] = useState<string | null>(null);
  const [floatingMoreId, setFloatingMoreId] = useState<string | null>(null);
  const [leftRailId, setLeftRailId] = useState<EbLeftRailId>('components');
  const [rightRailId, setRightRailId] = useState<EbRightRailId>('content');
  const [canvasLocked, setCanvasLocked] = useState(false);
  const [subject, setSubject] = useState('');
  const [senderName, setSenderName] = useState('Investhome');
  const [senderEmail, setSenderEmail] = useState('hello@investhome.com');
  const [replyTo, setReplyTo] = useState('advisors@investhome.com');
  const [previewText, setPreviewText] = useState('');
  const [linkType, setLinkType] = useState('url');
  const [linkUrl, setLinkUrl] = useState('https://investhome.com');
  const [heading, setHeading] = useState('');
  const [bodyCopy, setBodyCopy] = useState('');
  const [toast, setToast] = useState<string | null>(null);
  const [publishOpen, setPublishOpen] = useState(false);

  const focus = useCreativeStudioFocusMode({ storageKey: 'email-builder' });
  const filmstripRef = useRef<HTMLDivElement | null>(null);
  const floatingMoreRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const project = useMemo(() => getProject(projectId), [projectId]);
  const coverAsset = useBuilderCoverAsset({ templateCoverUrl: project.coverUrl });
  const deviceSize = DEVICE_CONTENT[device];
  const ftv = useFitToViewEngine({
    contentWidth: deviceSize.w,
    contentHeight: deviceSize.h,
    enabled: true,
    contentKey: `email-${device}-${selectedSectionId}-${focus.mode}-${focus.isFullscreen ? 'fs' : 'win'}`,
    canvasType: 'document',
  });

  const ebLeftRail: FocusRailItem[] = useMemo(
    () =>
      EB_LEFT_RAIL_IDS.map((id) => ({
        id,
        icon: EB_LEFT_RAIL_ICONS[id],
        labelKey: 'brief',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const ebRightRail: FocusRailItem[] = useMemo(
    () =>
      EB_RIGHT_RAIL_IDS.map((id) => ({
        id,
        icon: EB_RIGHT_RAIL_ICONS[id],
        labelKey: 'export',
        label: t(`rails.labels.${id}`),
      })),
    [t],
  );

  const localLeftItems = useMemo(
    () => ebLeftRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [ebLeftRail],
  );
  const localRightItems = useMemo(
    () => ebRightRail.map((i) => ({ id: i.id, icon: i.icon, label: i.label ?? i.id })),
    [ebRightRail],
  );

  useEffect(() => {
    setHydrated(true);
    setSubject(t('canvas.subjectValue'));
    setPreviewText(t('canvas.previewValue'));
    setHeading(t('canvas.headline'));
    setBodyCopy(t('canvas.lead'));
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

  function sectionLabel(section: EbSection) {
    return t(`canvas.sections.${section.key}`);
  }

  function addSection() {
    const id = `s-${Date.now()}`;
    const section: EbSection = {
      id,
      key: 'cta',
      label: 'Section',
      thumbUrl:
        'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=400&h=260&q=80',
    };
    setSections((prev) => [...prev, section]);
    setSelectedSectionId(id);
    markDirty();
    showToast(t('toasts.sectionAdded'));
  }

  function selectSection(section: EbSection) {
    setSelectedSectionId(section.id);
    setFloatingMoreId(null);
  }

  function handleSectionAction(action: SectionTrayActionKey, sectionId = selectedSectionId) {
    const section = sections.find((s) => s.id === sectionId);
    if (!section) return;
    setFloatingMoreId(null);

    if (action === 'edit') {
      setRightRailId('content');
      showToast(t('toasts.sectionEdit', { name: sectionLabel(section) }));
      return;
    }
    if (action === 'settings') {
      setRightRailId('settings');
      showToast(t('toasts.sectionSettings'));
      return;
    }
    if (action === 'duplicate') {
      const copy: EbSection = {
        id: `s-${Date.now()}`,
        key: section.key,
        label: `${section.label} copy`,
        thumbUrl: section.thumbUrl,
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
      addSection();
      return;
    }
    showToast(t(`bottomBar.toasts.${key}`));
  }

  function confirmPublish() {
    setPublishStatus('published');
    setPublishOpen(false);
    persistNow();
    showToast(t('toasts.published'));
  }

  function renderSectionToolbar(section: EbSection) {
    const moreOpen = floatingMoreId === section.id;
    const idx = sections.findIndex((s) => s.id === section.id);
    const moreItems: EbOverflowMenuItem[] = [
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
      <div className="eb-ws__section-toolbar" role="toolbar" aria-label={t('floating.more')}>
        <button
          type="button"
          className="eb-ws__section-toolbar-btn"
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
          className="eb-ws__section-toolbar-btn"
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
          className="eb-ws__section-toolbar-btn"
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
          className="eb-ws__section-toolbar-btn"
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
          className={`eb-ws__section-toolbar-btn${moreOpen ? ' is-active' : ''}`}
          title={t('floating.more')}
          aria-label={t('floating.more')}
          aria-expanded={moreOpen}
          aria-haspopup="menu"
          data-testid={`eb-section-more-${section.id}`}
          onClick={(e) => {
            e.stopPropagation();
            selectSection(section);
            setFloatingMoreId((prev) => (prev === section.id ? null : section.id));
          }}
        >
          ⋯
        </button>
        <EbSectionOverflowMenu
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

  function sectionShell(section: EbSection, children: React.ReactNode) {
    const selected = selectedSectionId === section.id;
    return (
      <div
        key={section.id}
        className={`eb-ws__doc-section eb-ws__editable${selected ? ' is-selected' : ''}`}
        onClick={() => selectSection(section)}
        role="presentation"
      >
        {renderSectionToolbar(section)}
        {children}
      </div>
    );
  }

  function renderPreview() {
    return (
      <div
        className="eb-ws__doc eb-ws__email-frame eb-ws__email-doc"
        data-testid="eb-live-preview"
        data-device={device}
      >
        {sections.map((section) => {
          if (section.key === 'header') {
            return sectionShell(
              section,
              <header className="eb-ws__site-header">
                <strong>INVESTHOME</strong>
                <nav aria-label={t('canvas.emailNavAria')}>
                  <span>{t('canvas.nav.home')}</span>
                  <span>{t('canvas.nav.projects')}</span>
                  <span>{t('canvas.nav.contact')}</span>
                </nav>
              </header>,
            );
          }

          if (section.key === 'hero') {
            return sectionShell(
              section,
              <div className="eb-ws__hero" style={{ backgroundImage: `url(${coverAsset.coverDisplayUrl})` }}>
                <div className="eb-ws__hero-inner">
                  <span className="eb-ws__hero-badge">{t('canvas.eyebrow')}</span>
                  <h3>{heading || t('canvas.headline')}</h3>
                  <p className="eb-ws__hero-lead">{bodyCopy || t('canvas.heroLead')}</p>
                  <div className="eb-ws__hero-ctas">
                    <button type="button" className="eb-ws__hero-cta eb-ws__hero-cta--primary">
                      {t('canvas.cta')}
                    </button>
                  </div>
                </div>
              </div>,
            );
          }

          if (section.key === 'features') {
            return sectionShell(
              section,
              <div className="eb-ws__prose" style={{ padding: '20px 24px' }}>
                <h3>{t('canvas.whyTitle')}</h3>
                <div className="eb-ws__feature-grid">
                  {FEATURE_GRID_KEYS.map((key) => (
                    <div key={key} className="eb-ws__feature-card">
                      <IhIcon name="trendingUp" size={14} />
                      <strong>{t(`canvas.features.${key}.title`)}</strong>
                      <span>{t(`canvas.features.${key}.body`)}</span>
                    </div>
                  ))}
                </div>
              </div>,
            );
          }

          if (section.key === 'cta') {
            return sectionShell(
              section,
              <div className="eb-ws__cta-block">
                <div>
                  <strong>{t('canvas.ctaTitle')}</strong>
                  <p>{t('canvas.ctaBody')}</p>
                </div>
                <Button variant="primary" data-testid="eb-cta-primary">
                  {t('canvas.cta')}
                </Button>
              </div>,
            );
          }

          if (section.key === 'gallery') {
            return sectionShell(
              section,
              <div className="eb-ws__prose" style={{ padding: '16px 24px 24px' }}>
                <h3>{t('canvas.galleryTitle')}</h3>
                <div className="eb-ws__gallery">
                  {GALLERY_IMAGE_URLS.map((url) => (
                    <img key={url} src={url} alt={t('canvas.galleryAlt')} />
                  ))}
                </div>
              </div>,
            );
          }

          if (section.key === 'blog') {
            return sectionShell(
              section,
              <div className="eb-ws__prose" style={{ padding: '16px 24px 24px' }}>
                <h3>{t('canvas.blogTitle')}</h3>
                <div className="eb-ws__feature-grid">
                  {RELATED_POST_KEYS.map((key) => (
                    <div key={key} className="eb-ws__feature-card">
                      <IhIcon name="documents" size={14} />
                      <strong>{t(`canvas.related.${key}.title`)}</strong>
                      <span>{t(`canvas.related.${key}.body`)}</span>
                    </div>
                  ))}
                </div>
              </div>,
            );
          }

          if (section.key === 'footer') {
            return sectionShell(
              section,
              <footer className="eb-ws__footer" style={{ padding: '20px 24px' }}>
                <p>{t('canvas.footerAddress')}</p>
                <p>
                  <button type="button" className="eb-ws__share-btn">
                    {t('canvas.unsubscribe')}
                  </button>
                </p>
                <div className="eb-ws__share" aria-label={t('canvas.socialAria')}>
                  {SOCIAL_LINK_KEYS.map((key) => (
                    <button
                      key={key}
                      type="button"
                      className="eb-ws__share-btn"
                      aria-label={t(`canvas.social.${key}`)}
                    >
                      {t(`canvas.social.${key}`)}
                    </button>
                  ))}
                </div>
              </footer>,
            );
          }

          if (section.key === 'divider') {
            return sectionShell(
              section,
              <hr style={{ margin: '12px 24px', border: 0, borderTop: '1px solid #e8eef0' }} />,
            );
          }

          if (section.key === 'spacer') {
            return sectionShell(section, <div style={{ height: 32 }} aria-hidden="true" />);
          }

          if (section.key === 'html') {
            return sectionShell(
              section,
              <div className="eb-ws__prose" style={{ padding: '16px 24px' }}>
                <code>{t('canvas.htmlBlock')}</code>
              </div>,
            );
          }

          if (section.key === 'social') {
            return sectionShell(
              section,
              <div className="eb-ws__share" style={{ padding: '16px 24px' }} aria-label={t('canvas.socialAria')}>
                {SOCIAL_LINK_KEYS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className="eb-ws__share-btn"
                    aria-label={t(`canvas.social.${key}`)}
                  >
                    {t(`canvas.social.${key}`)}
                  </button>
                ))}
              </div>,
            );
          }

          return sectionShell(
            section,
            <div className="eb-ws__prose" style={{ padding: '16px 24px' }}>
              <p>{sectionLabel(section)}</p>
            </div>,
          );
        })}
      </div>
    );
  }

  const leftDrawerContent = (
    <EbLeftRailDrawer
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
    <EbRightRailDrawer
      id={rightRailId}
      onSelectTab={setRightRailId}
      subject={subject}
      setSubject={setSubject}
      senderName={senderName}
      setSenderName={setSenderName}
      senderEmail={senderEmail}
      setSenderEmail={setSenderEmail}
      replyTo={replyTo}
      setReplyTo={setReplyTo}
      previewText={previewText}
      setPreviewText={setPreviewText}
      coverUrl={coverAsset.coverDisplayUrl}
      onChangeCover={() => coverAsset.openPicker('cover')}
      onRemoveCover={() => {
        coverAsset.clearCover();
        markDirty();
        showToast(t('toasts.imageRemoved'));
      }}
      linkType={linkType}
      setLinkType={setLinkType}
      linkUrl={linkUrl}
      setLinkUrl={setLinkUrl}
      heading={heading}
      setHeading={setHeading}
      bodyCopy={bodyCopy}
      setBodyCopy={setBodyCopy}
      publishStatus={publishStatus}
      markDirty={markDirty}
      onToast={showToast}
    />
  );

  const leftDrawer =
    focus.isFocus || focus.isFullscreen ? (
      leftDrawerContent
    ) : (
      <div className="eb-ws__panel eb-ws__left" aria-label={t('left.aria')} data-testid="eb-left">
        <EbLocalRail
          side="left"
          items={localLeftItems}
          activeId={leftRailId}
          onSelect={(id) => setLeftRailId(id as EbLeftRailId)}
        />
        {leftDrawerContent}
      </div>
    );

  const rightDrawer =
    focus.isFocus || focus.isFullscreen ? (
      rightDrawerContent
    ) : (
      <div className="eb-ws__panel eb-ws__right" aria-label={t('right.aria')} data-testid="eb-right">
        <EbLocalRail
          side="right"
          items={localRightItems}
          activeId={rightRailId}
          onSelect={(id) => setRightRailId(id as EbRightRailId)}
        />
        {rightDrawerContent}
      </div>
    );

  if (!hydrated) {
    return (
      <main className="dashboard" data-testid="eb-workspace-loading">
        <div className="eb-ws">
          <div className="eb-ws__skeleton eb-ws__skeleton--header" />
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard" data-testid="eb-workspace-page">
      <div
        className="eb-ws"
        data-testid="eb-workspace"
        data-cs-workspace-mode={focus.mode}
        data-cs-fullscreen={focus.isFullscreen ? 'true' : 'false'}
      >
        <header className="eb-ws__header cs-page-header">
          <div className="eb-ws__header-copy cs-page-header__copy">
            <Link href={EB_HOME as Route} className="eb-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="eb-ws__breadcrumb">
                <li>
                  <Link href={EB_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="eb-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="eb-ws__breadcrumb-current" aria-current="page">
                  {tTools('emailStudio.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="inbox" size={20} />
              {tTools('emailStudio.title')}
            </h1>
            <p className="eb-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="eb-ws__header-actions cs-page-header__actions">
            <div className="eb-ws__save-status" data-testid="eb-save-status">
              <StatusChip tone={saved ? 'success' : 'default'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <span className="eb-ws__saved-ago">{lastSavedLabel}</span>
            </div>
            <Button variant="secondary" size="sm" onClick={() => persistNow(true)} data-testid="eb-save">
              {t('saveDraft')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="eb-preview"
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
              data-testid="eb-send-test"
              onClick={() => showToast(t('toasts.testSent'))}
            >
              {t('sendTest')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              data-testid="eb-download-header"
              onClick={() => showToast(t('toasts.downloaded'))}
            >
              <IhIcon name="inbox" size={12} />
              {t('download')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              data-testid="eb-publish"
              onClick={() => setPublishOpen(true)}
            >
              {t('publish')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
          </div>
        </header>

        <div className="eb-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div className="eb-ws__toolbar-left">
            <div className="eb-ws__project">
              <Select
                id="eb-project"
                label={t('fields.project')}
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value as ProjectId);
                  markDirty();
                }}
              >
                {EB_PROJECTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="eb-ws__toolbar-icons" role="group" aria-label={t('toolbarAria')}>
              <button
                type="button"
                className="eb-ws__icon-btn"
                aria-label={t('undo')}
                data-testid="eb-undo"
                onClick={() => showToast(t('toasts.undo'))}
              >
                <IhIcon name="refresh" size={12} />
              </button>
              <button
                type="button"
                className="eb-ws__icon-btn"
                aria-label={t('redo')}
                data-testid="eb-redo"
                onClick={() => showToast(t('toasts.redo'))}
              >
                <IhIcon name="arrowRight" size={12} />
              </button>
            </div>
          </div>
          <div className="eb-ws__toolbar-right">
            <CreativeStudioFocusModeSwitcher mode={focus.mode} setMode={focus.setMode} />
            <EbZoomToolbar
              engine={ftv}
              canvasLocked={canvasLocked}
              onToggleLock={() => setCanvasLocked((v) => !v)}
              isFullscreen={focus.isFullscreen}
              onToggleFullscreen={focus.toggleFullscreen}
            />
          </div>
        </div>

        <div className="eb-ws__ai-status" role="status" aria-live="polite" data-testid="eb-info-banner">
          <span className="eb-ws__ai-status-dot" aria-hidden="true" />
          <span>{t('aiStatus.idle')}</span>
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="eb-ws__layout"
          leftRail={ebLeftRail}
          rightRail={ebRightRail}
          onLeftRailSelect={(id) => {
            if ((EB_LEFT_RAIL_IDS as string[]).includes(id)) {
              setLeftRailId(id as EbLeftRailId);
            }
          }}
          onRightRailSelect={(id) => {
            if ((EB_RIGHT_RAIL_IDS as string[]).includes(id)) {
              setRightRailId(id as EbRightRailId);
            }
          }}
          left={leftDrawer}
          center={
            <section className="eb-ws__panel eb-ws__center" aria-label={t('canvas.aria')} data-testid="eb-center">
              <FocusCanvasLayout
                isFullscreen={focus.isFullscreen}
                stageTestId="eb-canvas-stage"
                toolbar={
                  <div className="eb-ws__center-head">
                    <div className="eb-ws__device-toggle" role="group" aria-label={t('canvas.devicesAria')}>
                      {DEVICE_TOGGLE.map((mode) => (
                        <button
                          key={mode}
                          type="button"
                          className={`eb-ws__device-btn${device === mode ? ' is-active' : ''}`}
                          aria-pressed={device === mode}
                          aria-label={t(`canvas.devices.${mode}`)}
                          data-testid={`eb-device-${mode}`}
                          title={t(`canvas.devices.${mode}`)}
                          onClick={() => setDevice(mode)}
                        >
                          <span className={`eb-ws__device-glyph eb-ws__device-glyph--${mode}`} aria-hidden="true" />
                        </button>
                      ))}
                    </div>
                  </div>
                }
                tray={{
                  label: t('canvas.stripTitle'),
                  count: sections.length,
                  testId: 'eb-section-strip',
                  handleTestId: 'eb-tray-handle',
                  content: (
                    <div className="eb-ws__filmstrip" data-testid="eb-filmstrip">
                      <button
                        type="button"
                        className="eb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripPrev')}
                        data-testid="eb-filmstrip-prev"
                        onClick={() => scrollFilmstrip(-1)}
                      >
                        <IhIcon name="chevronLeft" size={14} />
                      </button>
                      <div className="eb-ws__page-row" ref={filmstripRef} data-testid="eb-section-row">
                        {sections.map((section) => (
                          <button
                            key={section.id}
                            type="button"
                            draggable
                            className={`eb-ws__page-card${selectedSectionId === section.id ? ' is-selected' : ''}${dragSectionId === section.id ? ' is-dragging' : ''}`}
                            onClick={() => selectSection(section)}
                            onDragStart={() => setDragSectionId(section.id)}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={() => {
                              if (!dragSectionId) return;
                              setSections((prev) => reorderSections(prev, dragSectionId, section.id));
                              setDragSectionId(null);
                              markDirty();
                            }}
                            onDragEnd={() => setDragSectionId(null)}
                            data-testid={`eb-section-card-${section.id}`}
                          >
                            <div className="eb-ws__page-thumb">
                              <img src={section.thumbUrl} alt="" />
                            </div>
                            <strong>{sectionLabel(section)}</strong>
                          </button>
                        ))}
                        <button
                          type="button"
                          className="eb-ws__page-card eb-ws__page-card--new"
                          data-testid="eb-new-section"
                          onClick={addSection}
                        >
                          <div className="eb-ws__page-thumb eb-ws__page-thumb--new">
                            <IhIcon name="plus" size={18} />
                          </div>
                          <strong>{t('canvas.newSection')}</strong>
                        </button>
                      </div>
                      <button
                        type="button"
                        className="eb-ws__filmstrip-nav"
                        aria-label={t('canvas.filmstripNext')}
                        data-testid="eb-filmstrip-next"
                        onClick={() => scrollFilmstrip(1)}
                      >
                        <IhIcon name="chevronRight" size={14} />
                      </button>
                    </div>
                  ),
                }}
                dock={{
                  testId: 'eb-scene-actions',
                  className: 'eb-ws__scene-actions',
                  primary: (
                    <CsBottomActionToolbar
                      testId="eb-bat"
                      ariaLabel={t('canvas.toolbarAria')}
                      primary={{
                        label: t('bottomBar.actions.addSection'),
                        icon: 'plus',
                        onClick: () => handleBottomAction('addSection'),
                        testId: 'eb-action-addSection',
                      }}
                      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addSection').map((action) => ({
                        key: action.key,
                        icon: action.icon,
                        label: t(`bottomBar.actions.${action.key}`),
                        onClick: () => handleBottomAction(action.key),
                        testId: `eb-action-${action.key}`,
                      }))}
                    />
                  ),
                }}
              >
                <div className="eb-ws__canvas-stage" data-testid="eb-preview-shell">
                  <FocusFitStage engine={ftv} artboardTestId="eb-ftv-artboard">
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
        <div className="eb-ws__modal" role="dialog" aria-modal="true" data-testid="eb-publish-modal">
          <div className="eb-ws__modal-card">
            <div className="eb-ws__modal-head">
              <div>
                <h2>{t('publishModal.title')}</h2>
                <p>{t('publishModal.subtitle')}</p>
              </div>
              <button
                type="button"
                className="eb-ws__icon-btn"
                aria-label={t('publishModal.close')}
                onClick={() => setPublishOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="eb-ws__modal-actions">
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

      {coverAsset.pickerOpen ? (
        <CsMediaPickerDialog
          open={coverAsset.pickerOpen}
          onClose={coverAsset.closePicker}
          media={coverAsset.media}
          selectedAssetId={coverAsset.coverImage?.asset_id ?? null}
          onSelect={(ref) => {
            coverAsset.setCoverImage(ref);
            coverAsset.closePicker();
            markDirty();
            showToast(t('toasts.imageChanged'));
          }}
          testId="eb-media-picker-dialog"
        />
      ) : null}

      {toast ? (
        <div className="eb-ws__toast" role="status">
          {toast}
        </div>
      ) : null}
    </main>
  );
}
