'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  BRAND_COLORS,
  BRB_TEMPLATES,
  FONT_OPTIONS,
  MARGIN_PRESETS,
  PAGE_STATUS_TONE,
  SECTION_KINDS,
  type BgMode,
  type BrochurePage,
  type BrbLeftRailId,
  type BrbRightRailId,
  type MarginPreset,
  type PageStatus,
} from './brochure-builder-model';
import { BrbZoomControls } from './brb-zoom-controls';

type LocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function BrbLocalRail({ side, items, activeId, onSelect }: LocalRailProps) {
  return (
    <div
      className={`brb-ws__local-rail brb-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`brb-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`brb-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`brb-local-rail-${side}-${item.id}`}
          onClick={() => onSelect(item.id)}
        >
          <IhIcon name={item.icon} size={16} />
        </button>
      ))}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="brb-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type BrbLeftRailDrawerProps = {
  id: BrbLeftRailId;
  pages: BrochurePage[];
  selectedPageId: string;
  onSelectPage: (page: BrochurePage) => void;
  onAddPage: () => void;
  onInsertComponent: (key: string) => void;
  onApplyTemplate: (thumbUrl: string) => void;
  onToast: (msg: string) => void;
};

export function BrbLeftRailDrawer(props: BrbLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'pages') return <PagesDrawer {...props} />;
  if (id === 'templates') return <TemplatesDrawer {...props} />;
  if (id === 'sections') return <SectionsDrawer {...props} />;
  if (id === 'assets') return <AssetsDrawer {...props} />;
  if (id === 'texts') return <TextsDrawer {...props} />;
  if (id === 'brand') return <BrandDrawer {...props} />;
  return <LeftSettingsDrawer {...props} />;
}

function PagesDrawer({
  pages,
  selectedPageId,
  onSelectPage,
  onAddPage,
}: BrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      pages.filter((page) => {
        if (!q) return true;
        return page.name.toLowerCase().includes(q) || page.kind.includes(q);
      }),
    [pages, q],
  );

  return (
    <div className="brb-ws__rail-panel" data-testid="brb-rail-left-pages">
      <div className="brb-ws__rail-panel-head">
        <h2>
          {t('rails.pages.title')} ({pages.length})
        </h2>
        <button
          type="button"
          className="brb-ws__icon-btn"
          aria-label={t('rails.pages.add')}
          data-testid="brb-pages-add"
          onClick={onAddPage}
        >
          <IhIcon name="plus" size={12} />
        </button>
      </div>
      <div className="brb-ws__rail-panel-body brb-ws__left-stack">
        <label className="brb-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.pages.search')}
            aria-label={t('rails.pages.search')}
            data-testid="brb-pages-search"
          />
        </label>
        <div className="brb-ws__ad-list brb-ws__page-list" data-testid="brb-page-list">
          {filtered.map((page, index) => (
            <button
              key={page.id}
              type="button"
              className={`brb-ws__ad-card${selectedPageId === page.id ? ' is-selected' : ''}`}
              data-testid={`brb-page-card-${page.id}`}
              onClick={() => onSelectPage(page)}
            >
              <span className="brb-ws__ad-card-thumb brb-ws__page-thumb">
                <img src={page.thumbUrl} alt="" />
              </span>
              <span className="brb-ws__ad-card-meta">
                <strong>
                  <span className="brb-ws__ad-card-index">{index + 1}</span> {page.name}
                </strong>
                <StatusChip tone={PAGE_STATUS_TONE[page.status as PageStatus]}>
                  {t(`pageStatus.${page.status}`)}
                </StatusChip>
              </span>
              <span className="brb-ws__ad-card-menu" aria-hidden="true">
                ⋯
              </span>
            </button>
          ))}
        </div>
        <Button
          variant="secondary"
          size="sm"
          data-testid="brb-pages-new"
          onClick={onAddPage}
        >
          <IhIcon name="plus" size={12} />
          {t('rails.pages.newPage')}
        </Button>
      </div>
    </div>
  );
}

function TemplatesDrawer({ onApplyTemplate }: BrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      BRB_TEMPLATES.filter((tpl) => {
        if (!q) return true;
        return tpl.category.includes(q) || tpl.id.includes(q);
      }),
    [q],
  );

  return (
    <div className="brb-ws__rail-panel" data-testid="brb-rail-left-templates">
      <div className="brb-ws__rail-panel-head">
        <h2>{t('rails.templates.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="brb-ws__rail-panel-body brb-ws__left-stack">
        <label className="brb-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.templates.search')}
            aria-label={t('rails.templates.search')}
          />
        </label>
        <div className="brb-ws__template-row" data-testid="brb-template-grid">
          {filtered.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              className="brb-ws__template"
              data-testid={`brb-template-${tpl.id}`}
              onClick={() => onApplyTemplate(tpl.thumbUrl)}
            >
              <img src={tpl.thumbUrl} alt="" />
              <span>{t(`rails.templates.categories.${tpl.category}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function SectionsDrawer({ onToast }: BrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel" data-testid="brb-rail-left-sections">
      <div className="brb-ws__rail-panel-head">
        <h2>{t('rails.sections.title')}</h2>
      </div>
      <div className="brb-ws__rail-panel-body brb-ws__left-stack">
        <p className="brb-ws__muted">{t('rails.sections.help')}</p>
        <div className="brb-ws__component-grid">
          {SECTION_KINDS.map((item) => (
            <button
              key={item.kind}
              type="button"
              className="brb-ws__component-card"
              data-testid={`brb-section-${item.kind}`}
              onClick={() => onToast(t('rails.sections.toasts.added', { name: t(`pages.${item.kind}`) }))}
            >
              <span className="brb-ws__component-card-icon">
                <IhIcon name={item.icon} size={14} />
              </span>
              <span>{t(`pages.${item.kind}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function AssetsDrawer({ onInsertComponent, onToast }: BrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel" data-testid="brb-rail-left-assets">
      <div className="brb-ws__rail-panel-head">
        <h2>{t('rails.assets.title')}</h2>
      </div>
      <div className="brb-ws__rail-panel-body brb-ws__left-stack">
        <p className="brb-ws__muted">{t('rails.assets.help')}</p>
        {(['image', 'gallery', 'video'] as const).map((key) => (
          <Button
            key={key}
            variant="secondary"
            size="sm"
            onClick={() => {
              onInsertComponent(key);
              onToast(t('rails.components.toasts.inserted', { name: t(`bottomBar.actions.${key}`) }));
            }}
          >
            <IhIcon name="inventory" size={12} />
            {t(`bottomBar.actions.${key}`)}
          </Button>
        ))}
      </div>
    </div>
  );
}

function TextsDrawer({ onInsertComponent, onToast }: BrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel" data-testid="brb-rail-left-texts">
      <div className="brb-ws__rail-panel-head">
        <h2>{t('rails.texts.title')}</h2>
      </div>
      <div className="brb-ws__rail-panel-body brb-ws__left-stack">
        <p className="brb-ws__muted">{t('rails.texts.help')}</p>
        {(['heading', 'text', 'quote'] as const).map((key) => (
          <Button
            key={key}
            variant="secondary"
            size="sm"
            onClick={() => {
              onInsertComponent(key);
              onToast(t('rails.components.toasts.inserted', { name: t(`bottomBar.actions.${key}`) }));
            }}
          >
            <IhIcon name="documents" size={12} />
            {t(`bottomBar.actions.${key}`)}
          </Button>
        ))}
      </div>
    </div>
  );
}

function BrandDrawer({ onToast }: BrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel" data-testid="brb-rail-left-brand">
      <div className="brb-ws__rail-panel-head">
        <h2>{t('rails.brand.title')}</h2>
      </div>
      <div className="brb-ws__rail-panel-body brb-ws__left-stack">
        <p className="brb-ws__muted">{t('rails.brand.help')}</p>
        <p className="brb-ws__section-label">{t('rails.brand.colors')}</p>
        <div className="brb-ws__chip-row">
          {BRAND_COLORS.map((color) => (
            <button
              key={color}
              type="button"
              className="brb-ws__chip"
              style={{
                background: color,
                color: color === '#FFFFFF' ? '#111' : '#fff',
              }}
              onClick={() => onToast(t('rails.brand.colorApplied', { color }))}
            >
              {color}
            </button>
          ))}
        </div>
        <Button variant="secondary" size="sm" onClick={() => onToast(t('rails.brand.kitApplied'))}>
          {t('rails.brand.applyKit')}
        </Button>
      </div>
    </div>
  );
}

function LeftSettingsDrawer({ onToast }: BrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel" data-testid="brb-rail-left-settings">
      <div className="brb-ws__rail-panel-head">
        <h2>{t('rails.leftSettings.title')}</h2>
      </div>
      <div className="brb-ws__rail-panel-body brb-ws__left-stack">
        <p className="brb-ws__muted">{t('rails.leftSettings.help')}</p>
        <label className="brb-ws__toggle-row">
          <span>{t('rails.leftSettings.autoSave')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="brb-ws__toggle-row">
          <span>{t('rails.leftSettings.showGuides')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <Button variant="secondary" size="sm" onClick={() => onToast(t('rails.leftSettings.saved'))}>
          {t('rails.leftSettings.apply')}
        </Button>
      </div>
    </div>
  );
}

export type BrbRightRailDrawerProps = {
  id: BrbRightRailId;
  onSelectTab: (id: BrbRightRailId) => void;
  page: BrochurePage;
  patchPage: (patch: Partial<BrochurePage>) => void;
  themeName: string;
  headingFont: string;
  bodyFont: string;
  setHeadingFont: (v: string) => void;
  setBodyFont: (v: string) => void;
  bgMode: BgMode;
  setBgMode: (v: BgMode) => void;
  margins: MarginPreset;
  setMargins: (v: MarginPreset) => void;
  pageNumbers: boolean;
  setPageNumbers: (v: boolean) => void;
  notes: string;
  setNotes: (v: string) => void;
  markDirty: () => void;
  onToast: (msg: string) => void;
};

export function BrbRightRailDrawer(props: BrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel" data-testid={`brb-rail-right-${props.id}`}>
      <div className="brb-ws__rail-panel-head brb-ws__prop-tabs-head">
        <div className="brb-ws__prop-tabs" role="tablist" aria-label={t('right.aria')}>
          {(['design', 'page', 'interaction', 'notes'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={props.id === tab}
              className={`brb-ws__prop-tab${props.id === tab ? ' is-active' : ''}`}
              data-testid={`brb-prop-tab-${tab}`}
              onClick={() => props.onSelectTab(tab)}
            >
              {t(`rails.labels.${tab}`)}
            </button>
          ))}
        </div>
      </div>
      {props.id === 'design' ? <DesignDrawer {...props} /> : null}
      {props.id === 'page' ? <PageDrawer {...props} /> : null}
      {props.id === 'interaction' ? <InteractionDrawer {...props} /> : null}
      {props.id === 'notes' ? <NotesDrawer {...props} /> : null}
    </div>
  );
}

function DesignDrawer({
  themeName,
  headingFont,
  bodyFont,
  setHeadingFont,
  setBodyFont,
  bgMode,
  setBgMode,
  margins,
  setMargins,
  pageNumbers,
  setPageNumbers,
  markDirty,
  onToast,
}: BrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel-body brb-ws__left-stack" data-testid="brb-design-drawer">
      <p className="brb-ws__section-label">{t('rails.design.theme')}</p>
      <div className="brb-ws__featured brb-ws__theme-card">
        <div className="brb-ws__theme-card-body">
          <strong>{themeName}</strong>
          <span className="brb-ws__muted">{t('rails.design.themeActive')}</span>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onToast(t('rails.design.themeChange'))}
          data-testid="brb-theme-change"
        >
          {t('rails.design.change')}
        </Button>
      </div>

      <p className="brb-ws__section-label">{t('rails.design.palette')}</p>
      <div className="brb-ws__chip-row">
        {BRAND_COLORS.map((color) => (
          <button
            key={color}
            type="button"
            className="brb-ws__chip"
            style={{ background: color, minWidth: '1.75rem', minHeight: '1.75rem' }}
            aria-label={color}
            onClick={() => {
              markDirty();
              onToast(t('rails.brand.colorApplied', { color }));
            }}
          />
        ))}
      </div>

      <Field label={t('rails.design.headingFont')}>
        <select
          value={headingFont}
          onChange={(e) => {
            setHeadingFont(e.target.value);
            markDirty();
          }}
          data-testid="brb-font-heading"
        >
          {FONT_OPTIONS.map((font) => (
            <option key={font} value={font}>
              {font}
            </option>
          ))}
        </select>
      </Field>

      <Field label={t('rails.design.bodyFont')}>
        <select
          value={bodyFont}
          onChange={(e) => {
            setBodyFont(e.target.value);
            markDirty();
          }}
          data-testid="brb-font-body"
        >
          {FONT_OPTIONS.map((font) => (
            <option key={font} value={font}>
              {font}
            </option>
          ))}
        </select>
      </Field>

      <p className="brb-ws__section-label">{t('rails.design.background')}</p>
      <div className="brb-ws__bg-mode" role="group">
        {(['color', 'image', 'gradient'] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            className={bgMode === mode ? 'is-active' : undefined}
            data-testid={`brb-bg-${mode}`}
            onClick={() => {
              setBgMode(mode);
              markDirty();
            }}
          >
            {t(`rails.design.bgModes.${mode}`)}
          </button>
        ))}
      </div>

      <Field label={t('rails.design.margins')}>
        <select
          value={margins}
          onChange={(e) => {
            setMargins(e.target.value as MarginPreset);
            markDirty();
          }}
          data-testid="brb-margins"
        >
          {MARGIN_PRESETS.map((key) => (
            <option key={key} value={key}>
              {t(`rails.design.marginOptions.${key}`)}
            </option>
          ))}
        </select>
      </Field>

      <label className="brb-ws__toggle-row">
        <span>{t('rails.design.pageNumbers')}</span>
        <input
          type="checkbox"
          checked={pageNumbers}
          onChange={(e) => {
            setPageNumbers(e.target.checked);
            markDirty();
          }}
          data-testid="brb-page-numbers"
        />
      </label>
    </div>
  );
}

function PageDrawer({ page, patchPage, markDirty }: BrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel-body brb-ws__left-stack" data-testid="brb-page-drawer">
      <Field label={t('rails.page.name')}>
        <input
          value={page.name}
          onChange={(e) => {
            patchPage({ name: e.target.value });
            markDirty();
          }}
          data-testid="brb-page-name"
        />
      </Field>
      <Field label={t('rails.page.status')}>
        <select
          value={page.status}
          onChange={(e) => {
            patchPage({ status: e.target.value as PageStatus });
            markDirty();
          }}
        >
          {(['ready', 'draft', 'review'] as const).map((status) => (
            <option key={status} value={status}>
              {t(`pageStatus.${status}`)}
            </option>
          ))}
        </select>
      </Field>
      <p className="brb-ws__muted">{t('rails.page.help', { kind: t(`pages.${page.kind}`) })}</p>
    </div>
  );
}

function InteractionDrawer({ markDirty, onToast }: BrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel-body brb-ws__left-stack" data-testid="brb-interaction-drawer">
      <p className="brb-ws__muted">{t('rails.interaction.help')}</p>
      <label className="brb-ws__toggle-row">
        <span>{t('rails.interaction.hotspots')}</span>
        <input type="checkbox" defaultChecked onChange={() => markDirty()} />
      </label>
      <label className="brb-ws__toggle-row">
        <span>{t('rails.interaction.links')}</span>
        <input type="checkbox" defaultChecked onChange={() => markDirty()} />
      </label>
      <label className="brb-ws__toggle-row">
        <span>{t('rails.interaction.qr')}</span>
        <input type="checkbox" onChange={() => markDirty()} />
      </label>
      <Button variant="secondary" size="sm" onClick={() => onToast(t('rails.interaction.applied'))}>
        {t('rails.interaction.apply')}
      </Button>
    </div>
  );
}

function NotesDrawer({ notes, setNotes, markDirty }: BrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');

  return (
    <div className="brb-ws__rail-panel-body brb-ws__left-stack" data-testid="brb-notes-drawer">
      <Field label={t('rails.notes.label')}>
        <textarea
          rows={8}
          value={notes}
          onChange={(e) => {
            setNotes(e.target.value);
            markDirty();
          }}
          placeholder={t('rails.notes.placeholder')}
          data-testid="brb-notes-input"
        />
      </Field>
    </div>
  );
}

export type BrbZoomToolbarProps = {
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

export function BrbZoomToolbar({
  engine,
  canvasLocked,
  onToggleLock,
  isFullscreen,
  onToggleFullscreen,
}: BrbZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.brochureBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    if (canvasLocked) return;
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="brb-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="brb-zoom-bar"
    >
      <div className="brb-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`brb-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="brb-ftv-fit"
          disabled={canvasLocked}
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
        <button
          type="button"
          className={`brb-ws__fit-btn${engine.mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'actual'}
          data-testid="brb-ftv-actual"
          disabled={canvasLocked}
          onClick={() => engine.actualSize()}
        >
          {t('canvas.fitModes.actual')}
        </button>
      </div>

      <BrbZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => {
          if (!canvasLocked) engine.actualSize();
        }}
      />

      <label className="brb-ws__auto-fit" data-testid="brb-auto-fit">
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
        className={`brb-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
        aria-pressed={canvasLocked}
        data-testid="brb-lock-canvas"
        onClick={onToggleLock}
      >
        {t('canvas.lockCanvas')}
      </button>

      <button
        type="button"
        className={`brb-ws__fit-btn${isFullscreen ? ' is-active' : ''}`}
        aria-pressed={isFullscreen}
        data-testid="brb-fullscreen-zoom"
        onClick={onToggleFullscreen}
      >
        {t('canvas.fullscreenShort')}
      </button>
    </div>
  );
}
