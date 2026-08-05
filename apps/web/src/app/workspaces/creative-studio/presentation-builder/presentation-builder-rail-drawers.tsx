'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  BRAND_KIT,
  LAYOUT_PRESETS,
  SECTION_PRESETS,
  STYLE_OPTIONS,
  TEMPLATE_PRESETS,
  aspectClass,
  reorderSlides,
  type AspectRatio,
  type PbSlide,
  type PresentationBrief,
} from './presentation-builder-model';
import { PbZoomControls } from './pb-zoom-controls';

export type PbLeftRailId = 'slides' | 'layouts' | 'sections' | 'templates';
export type PbRightRailId = 'theme' | 'brand' | 'animation' | 'notes';

type LocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function PbLocalRail({ side, items, activeId, onSelect }: LocalRailProps) {
  return (
    <div
      className={`pb-ws__local-rail pb-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`pb-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`pb-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`pb-local-rail-${side}-${item.id}`}
          onClick={() => onSelect(item.id)}
        >
          <IhIcon name={item.icon} size={15} />
        </button>
      ))}
    </div>
  );
}

type FieldProps = {
  label: string;
  children: React.ReactNode;
};

function Field({ label, children }: FieldProps) {
  return (
    <label className="pb-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type PbLeftRailDrawerProps = {
  id: PbLeftRailId;
  slides: PbSlide[];
  selectedSlideId: string;
  setSelectedSlideId: (id: string) => void;
  setSlides: (updater: (prev: PbSlide[]) => PbSlide[]) => void;
  aspectRatio: AspectRatio;
  onAddSlide: () => void;
  onDuplicateSlide: (id: string) => void;
  onDeleteSlide: (id: string) => void;
  markDirty: () => void;
  brief: PresentationBrief;
  setBrief: (updater: (prev: PresentationBrief) => PresentationBrief) => void;
};

export function PbLeftRailDrawer(props: PbLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'slides') return <SlidesDrawer {...props} />;
  if (id === 'layouts') return <LayoutsDrawer {...props} />;
  if (id === 'sections') return <SectionsDrawer {...props} />;
  return <TemplatesDrawer {...props} />;
}

function SlidesDrawer({
  slides,
  selectedSlideId,
  setSelectedSlideId,
  setSlides,
  aspectRatio,
  onAddSlide,
  onDuplicateSlide,
  onDeleteSlide,
  markDirty,
}: PbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  const [dragId, setDragId] = useState<string | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuId) return;
    function onDoc(e: MouseEvent) {
      const target = e.target as HTMLElement | null;
      if (target?.closest('[data-pb-slide-menu]')) return;
      setMenuId(null);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [menuId]);

  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-slide-id="${selectedSlideId}"]`);
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [selectedSlideId]);

  return (
    <div className="pb-ws__rail-panel" data-testid="pb-rail-left-slides">
      <div className="pb-ws__rail-panel-head">
        <h2>{t('rails.slides.title')}</h2>
        <StatusChip tone="info">{slides.length}</StatusChip>
      </div>
      <div className="pb-ws__rail-panel-body pb-ws__thumbs-body">
        <div className="pb-ws__thumbs-list" ref={listRef} data-testid="pb-slide-thumbs">
          {slides.map((slide, index) => {
            const selected = selectedSlideId === slide.id;
            return (
              <div
                key={slide.id}
                data-slide-id={slide.id}
                className={`pb-ws__thumb-card${selected ? ' is-selected' : ''}${dragId === slide.id ? ' is-dragging' : ''}`}
                draggable
                onDragStart={() => setDragId(slide.id)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => {
                  if (!dragId) return;
                  setSlides((prev) => reorderSlides(prev, dragId, slide.id));
                  setDragId(null);
                  markDirty();
                }}
                onDragEnd={() => setDragId(null)}
              >
                <button
                  type="button"
                  className="pb-ws__thumb-main"
                  data-testid={`pb-thumb-${slide.id}`}
                  onClick={() => setSelectedSlideId(slide.id)}
                >
                  <span className="pb-ws__thumb-num" aria-hidden="true">
                    {index + 1}
                  </span>
                  <div className={`pb-ws__thumb-preview ${aspectClass(aspectRatio)}`}>
                    <img src={slide.thumbUrl} alt="" />
                  </div>
                  <span className="pb-ws__thumb-title">{t(`slides.${slide.kind}.title`)}</span>
                </button>
                <div className="pb-ws__thumb-overflow" data-pb-slide-menu>
                  <button
                    type="button"
                    className="pb-ws__icon-btn pb-ws__thumb-menu-btn"
                    aria-label={t('rails.slides.moreAria')}
                    aria-expanded={menuId === slide.id}
                    data-testid={`pb-thumb-menu-${slide.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuId((prev) => (prev === slide.id ? null : slide.id));
                    }}
                  >
                    <IhIcon name="quickAction" size={11} />
                  </button>
                  {menuId === slide.id ? (
                    <div className="pb-ws__thumb-menu" role="menu">
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          onDuplicateSlide(slide.id);
                          setMenuId(null);
                        }}
                      >
                        {t('canvas.actions.duplicate')}
                      </button>
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          onDeleteSlide(slide.id);
                          setMenuId(null);
                        }}
                      >
                        {t('canvas.actions.delete')}
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <div className="pb-ws__left-footer">
        <Button
          variant="primary"
          size="md"
          className="pb-ws__generate-btn"
          data-testid="pb-add-slide-drawer"
          onClick={onAddSlide}
        >
          <IhIcon name="plus" size={14} />
          {t('rails.slides.add')}
        </Button>
      </div>
    </div>
  );
}

function LayoutsDrawer({ onAddSlide, markDirty }: PbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  const [active, setActive] = useState<(typeof LAYOUT_PRESETS)[number]>('titleBody');

  return (
    <div className="pb-ws__rail-panel" data-testid="pb-rail-left-layouts">
      <div className="pb-ws__rail-panel-head">
        <h2>{t('rails.layouts.title')}</h2>
      </div>
      <div className="pb-ws__rail-panel-body">
        <p className="pb-ws__muted">{t('rails.layouts.help')}</p>
        <div className="pb-ws__layout-grid">
          {LAYOUT_PRESETS.map((key) => (
            <button
              key={key}
              type="button"
              className={`pb-ws__layout-card${active === key ? ' is-active' : ''}`}
              data-testid={`pb-layout-${key}`}
              onClick={() => {
                setActive(key);
                markDirty();
              }}
            >
              <span className={`pb-ws__layout-wire is-${key}`} aria-hidden="true" />
              <strong>{t(`rails.layouts.items.${key}`)}</strong>
            </button>
          ))}
        </div>
      </div>
      <div className="pb-ws__left-footer">
        <Button variant="secondary" size="md" className="pb-ws__generate-btn" onClick={onAddSlide}>
          <IhIcon name="plus" size={14} />
          {t('rails.layouts.apply')}
        </Button>
      </div>
    </div>
  );
}

function SectionsDrawer({ onAddSlide }: PbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  return (
    <div className="pb-ws__rail-panel" data-testid="pb-rail-left-sections">
      <div className="pb-ws__rail-panel-head">
        <h2>{t('rails.sections.title')}</h2>
      </div>
      <div className="pb-ws__rail-panel-body">
        <p className="pb-ws__muted">{t('rails.sections.help')}</p>
        <div className="pb-ws__section-list">
          {SECTION_PRESETS.map((key, index) => (
            <button
              key={key}
              type="button"
              className="pb-ws__section-row"
              data-testid={`pb-section-${key}`}
              onClick={onAddSlide}
            >
              <span className="pb-ws__section-index">{index + 1}</span>
              <span>
                <strong>{t(`rails.sections.items.${key}`)}</strong>
                <em>{t(`rails.sections.hints.${key}`)}</em>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function TemplatesDrawer({ markDirty }: PbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  const [active, setActive] = useState<(typeof TEMPLATE_PRESETS)[number]>('investorPitch');
  return (
    <div className="pb-ws__rail-panel" data-testid="pb-rail-left-templates">
      <div className="pb-ws__rail-panel-head">
        <h2>{t('rails.templates.title')}</h2>
      </div>
      <div className="pb-ws__rail-panel-body">
        <p className="pb-ws__muted">{t('rails.templates.help')}</p>
        <div className="pb-ws__theme-grid">
          {TEMPLATE_PRESETS.map((key) => (
            <button
              key={key}
              type="button"
              className={`pb-ws__theme-card${active === key ? ' is-active' : ''}`}
              data-testid={`pb-template-${key}`}
              onClick={() => {
                setActive(key);
                markDirty();
              }}
            >
              <span className={`pb-ws__theme-preview is-luxuryModern`} aria-hidden="true" />
              <strong>{t(`rails.templates.items.${key}`)}</strong>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export type PbRightRailDrawerProps = {
  id: PbRightRailId;
  brief: PresentationBrief;
  setBrief: (updater: (prev: PresentationBrief) => PresentationBrief) => void;
  markDirty: () => void;
  speakerNotes: string;
  setSpeakerNotes: (v: string) => void;
  showSlideNumber: boolean;
  setShowSlideNumber: (v: boolean) => void;
  onToast: (msg: string) => void;
};

export function PbRightRailDrawer(props: PbRightRailDrawerProps) {
  const { id } = props;
  if (id === 'theme') return <ThemeDrawer {...props} />;
  if (id === 'brand') return <BrandDrawer {...props} />;
  if (id === 'animation') return <AnimationDrawer />;
  return <NotesDrawer {...props} />;
}

function ThemeDrawer({
  brief,
  setBrief,
  markDirty,
  showSlideNumber,
  setShowSlideNumber,
  onToast,
}: PbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  const swatches = ['#075b75', '#58aebb', '#1e2b33', '#e8eef1', '#c9a227'];

  return (
    <div className="pb-ws__rail-panel" data-testid="pb-rail-right-theme">
      <div className="pb-ws__rail-panel-head">
        <h2>{t('rails.theme.title')}</h2>
      </div>
      <div className="pb-ws__rail-panel-body pb-ws__right-stack">
        <div className="pb-ws__panel-card">
          <p className="pb-ws__section-label">{t('rails.theme.current')}</p>
          <div className="pb-ws__theme-current">
            <strong>
              {STYLE_OPTIONS.includes(brief.style as (typeof STYLE_OPTIONS)[number])
                ? t(`styles.${brief.style}`)
                : t('rails.theme.defaultName')}
            </strong>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onToast(t('rails.theme.changeToast'))}
            >
              {t('rails.theme.change')}
            </Button>
          </div>
        </div>

        <div className="pb-ws__panel-card">
          <p className="pb-ws__section-label">{t('rails.theme.palette')}</p>
          <div className="pb-ws__brand-swatches" aria-hidden="true">
            {swatches.map((c) => (
              <span key={c} style={{ background: c }} />
            ))}
          </div>
        </div>

        <div className="pb-ws__panel-card">
          <div className="pb-ws__section-head">
            <p className="pb-ws__section-label">{t('rails.theme.layout')}</p>
            <button
              type="button"
              className="pb-ws__link-btn"
              onClick={() => onToast(t('rails.theme.seeAllToast'))}
            >
              {t('rails.theme.seeAll')}
            </button>
          </div>
          <div className="pb-ws__layout-grid pb-ws__layout-grid--compact">
            {LAYOUT_PRESETS.slice(0, 4).map((key) => (
              <button key={key} type="button" className="pb-ws__layout-card">
                <span className={`pb-ws__layout-wire is-${key}`} aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>

        <div className="pb-ws__panel-card pb-ws__left-stack">
          <p className="pb-ws__section-label">{t('rails.theme.typography')}</p>
          <Field label={t('rails.theme.headingFont')}>
            <select defaultValue="Inter Display">
              <option>Inter Display</option>
              <option>Söhne</option>
              <option>Playfair Display</option>
            </select>
          </Field>
          <Field label={t('rails.theme.bodyFont')}>
            <select defaultValue="Inter">
              <option>Inter</option>
              <option>Source Sans 3</option>
              <option>IBM Plex Sans</option>
            </select>
          </Field>
        </div>

        <div className="pb-ws__panel-card pb-ws__left-stack">
          <p className="pb-ws__section-label">{t('rails.theme.background')}</p>
          <div className="pb-ws__chip-row">
            {(['color', 'image', 'gradient'] as const).map((key) => (
              <button key={key} type="button" className={`pb-ws__chip${key === 'color' ? ' is-active' : ''}`}>
                {t(`rails.theme.bgTypes.${key}`)}
              </button>
            ))}
          </div>
          <div className="pb-ws__brand-swatches" aria-hidden="true">
            <span style={{ background: '#0b1820' }} />
            <span style={{ background: '#075b75' }} />
            <span style={{ background: '#ffffff' }} />
          </div>
        </div>

        <div className="pb-ws__panel-card">
          <label className="pb-ws__check pb-ws__check--row">
            <span>{t('rails.theme.slideNumber')}</span>
            <input
              type="checkbox"
              checked={showSlideNumber}
              onChange={(e) => {
                setShowSlideNumber(e.target.checked);
                markDirty();
              }}
              data-testid="pb-slide-number-toggle"
            />
          </label>
        </div>

        <Field label={t('brief.style')}>
          <select
            value={STYLE_OPTIONS.includes(brief.style as (typeof STYLE_OPTIONS)[number]) ? brief.style : 'luxuryModern'}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, style: e.target.value }));
              markDirty();
            }}
          >
            {STYLE_OPTIONS.map((style) => (
              <option key={style} value={style}>
                {t(`styles.${style}`)}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </div>
  );
}

function BrandDrawer({ brief, setBrief, markDirty }: PbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  return (
    <div className="pb-ws__rail-panel" data-testid="pb-rail-right-brand">
      <div className="pb-ws__rail-panel-head">
        <h2>{t('rails.brand.title')}</h2>
        <StatusChip tone="success">{t('left.ready')}</StatusChip>
      </div>
      <div className="pb-ws__rail-panel-body pb-ws__left-stack">
        <p className="pb-ws__muted">{t('rails.brand.help')}</p>
        <div className="pb-ws__chip-row">
          {BRAND_KIT.map((key) => (
            <span key={key} className="pb-ws__chip is-good">
              {t(`brandKit.${key}`)}
            </span>
          ))}
        </div>
        <Field label={t('brief.style')}>
          <select
            value={STYLE_OPTIONS.includes(brief.style as (typeof STYLE_OPTIONS)[number]) ? brief.style : 'luxuryModern'}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, style: e.target.value }));
              markDirty();
            }}
          >
            {STYLE_OPTIONS.map((style) => (
              <option key={style} value={style}>
                {t(`styles.${style}`)}
              </option>
            ))}
          </select>
        </Field>
        <div className="pb-ws__brand-swatches" aria-hidden="true">
          <span style={{ background: '#075b75' }} />
          <span style={{ background: '#58aebb' }} />
          <span style={{ background: '#1e2b33' }} />
          <span style={{ background: '#e8eef1' }} />
        </div>
      </div>
    </div>
  );
}

function AnimationDrawer() {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  const presets = ['none', 'fade', 'slide', 'scale', 'stagger'] as const;
  const [active, setActive] = useState<(typeof presets)[number]>('fade');
  return (
    <div className="pb-ws__rail-panel" data-testid="pb-rail-right-animation">
      <div className="pb-ws__rail-panel-head">
        <h2>{t('rails.animation.title')}</h2>
      </div>
      <div className="pb-ws__rail-panel-body">
        <p className="pb-ws__muted">{t('rails.animation.help')}</p>
        <div className="pb-ws__anim-grid">
          {presets.map((key) => (
            <button
              key={key}
              type="button"
              className={`pb-ws__anim-card${active === key ? ' is-active' : ''}`}
              onClick={() => setActive(key)}
            >
              <IhIcon name={key === 'none' ? 'empty' : 'sparkles'} size={14} />
              <span>{t(`rails.animation.presets.${key}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function NotesDrawer({ speakerNotes, setSpeakerNotes }: PbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  return (
    <div className="pb-ws__rail-panel" data-testid="pb-rail-right-notes">
      <div className="pb-ws__rail-panel-head">
        <h2>{t('rails.notes.title')}</h2>
      </div>
      <div className="pb-ws__rail-panel-body pb-ws__left-stack">
        <p className="pb-ws__muted">{t('rails.notes.help')}</p>
        <Field label={t('rails.notes.label')}>
          <textarea
            rows={12}
            value={speakerNotes}
            onChange={(e) => setSpeakerNotes(e.target.value)}
            placeholder={t('rails.notes.placeholder')}
            data-testid="pb-speaker-notes"
          />
        </Field>
      </div>
    </div>
  );
}

export type PbZoomToolbarProps = {
  engine: {
    mode: string;
    zoomPercent: number;
    autoFit: boolean;
    fitToView: () => void;
    actualSize: () => void;
    setPercent: (n: number) => void;
    setAutoFit: (v: boolean) => void;
  };
  canvasLocked: boolean;
  onToggleLock: () => void;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
};

const ZOOM_STEP = 10;
const ZOOM_MIN = 10;
const ZOOM_MAX = 400;

export function PbZoomToolbar({
  engine,
  canvasLocked,
  onToggleLock,
  isFullscreen,
  onToggleFullscreen,
}: PbZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    if (canvasLocked) return;
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="pb-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="pb-zoom-bar"
    >
      <div className="pb-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`pb-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="pb-ftv-fit"
          disabled={canvasLocked}
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
        <button
          type="button"
          className={`pb-ws__fit-btn${engine.mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'actual'}
          data-testid="pb-ftv-actual"
          disabled={canvasLocked}
          onClick={() => engine.actualSize()}
        >
          {t('canvas.fitModes.actual')}
        </button>
      </div>

      <PbZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => {
          if (!canvasLocked) engine.actualSize();
        }}
      />

      <label className="pb-ws__auto-fit" data-testid="pb-auto-fit">
        <input
          type="checkbox"
          checked={engine.autoFit}
          disabled={canvasLocked}
          onChange={(e) => engine.setAutoFit(e.target.checked)}
        />
        <span>{t('canvas.autoFit')}</span>
      </label>

      <button
        type="button"
        className={`pb-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
        aria-pressed={canvasLocked}
        data-testid="pb-lock-canvas"
        onClick={onToggleLock}
      >
        {t('canvas.lockCanvas')}
      </button>

      <button
        type="button"
        className={`pb-ws__fit-btn${isFullscreen ? ' is-active' : ''}`}
        aria-pressed={isFullscreen}
        data-testid="pb-fullscreen-zoom"
        onClick={onToggleFullscreen}
      >
        {t('canvas.fullscreenShort')}
      </button>
    </div>
  );
}
